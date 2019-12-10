#!/usr/bin/env python
import re
import os
import sys
import nltk
import time
import boto3
import pprint
import random
import logging
import traceback
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient
import prometheus_client as prom
from colorlog import ColoredFormatter
from nltk.stem import WordNetLemmatizer
from collections import defaultdict, abc
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import sent_tokenize, word_tokenize

# download NLTK dependencies
nltk_deps = ['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger']
for d in nltk_deps:
    nltk.download(d)

# setup metrics
prom_processed_files = prom.Counter(
    name='bingo_indexer_processed_files_total',
    documentation='Total number of indexed HTML documents',
    labelnames=['doc', 'url']
)


def config_logging():
    """Configure logging format and handler."""

    FORMAT = os.environ.get(
        "LOGGING_FORMAT",
        '%(log_color)s[%(asctime)s] %(module)-12s %(funcName)s(): %(message)s %(reset)s'
    )

    LOG_LEVEL = logging.DEBUG
    stream = logging.StreamHandler()
    stream.setLevel(LOG_LEVEL)
    stream.setFormatter(ColoredFormatter(FORMAT))

    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)
    logger.addHandler(stream)

    return logger


class indexer(object):

    def __init__(self):

        # setup logging and get env variables
        self.logger = logging.getLogger(__name__)
        self.BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
        self.II_DB_HOST = os.environ.get('INVERTED_INDEX_HOST', 'localhost')
        self.II_DB_NAME = os.environ.get('INVERTED_INDEX_NAME', 'inverted_index')
        self.II_DB_PORT = int(os.environ.get('INVERTED_INDEX_PORT', 27017))

        # other params
        self.LOCK_TTL = 60                      # TTL for indexing lock for S3 objects
        self.processing_batch_size = 1          # number of objects for processing batch
        self.s3_client = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.bucket = self.s3_resource.Bucket(self.BUCKET_NAME)

        # establish connection
        self.ii_client, self.ii_db = self._create_ii_conn()


    def run(self, daemon=True):
        """Run autonomously."""
        while True:

            s3_objects = self._fetch_s3_obj()           # fetch
            doc_words = self._process_text(s3_objects)  # process
            ii = self._create_inverted_index(doc_words) # index
            self._update_inverted_index(ii)             # store

            if not daemon:
                break

    def _acquire_object_lock(self, key):
        """Attempts to lock S3 object for indexer."""

        obj_head = self.s3_client.head_object(Bucket=self.BUCKET_NAME, Key=key)
        metadata = obj_head["Metadata"]

        # lock object
        if 'indexing_lock' not in metadata or \
            float(metadata['indexing_lock']) + self.LOCK_TTL < time.time():

            metadata["indexing_lock"] = str(time.time())
            self.s3_client.copy_object(
                Bucket=self.BUCKET_NAME,
                Key=key,
                Metadata=metadata,
                MetadataDirective='REPLACE',
                CopySource=self.BUCKET_NAME + '/' + key,
            )

            return True

        return False


    def _fetch_s3_obj(self):
        """
        Get the documents from S3.
        Returns:
            List of document keys in S3.
        """

        file_key_list = list()

        # get object keys to fetch
        for obj_summary in self.bucket.objects.all():
            if self._acquire_object_lock(obj_summary.key):
                file_key_list.append(obj_summary.key)
                if len(file_key_list) >= self.processing_batch_size:
                    break

        # no objects available, just wait a while
        if len(file_key_list) == 0:
            sleep_time = self.LOCK_TTL / 4
            self.logger.warning("There are no documents in S3. Sleeping for {}s...".format(sleep_time))
            time.sleep(sleep_time)

        # objects available
        else:
            self.logger.debug("Processing {} objects from S3.".format(len(file_key_list)))

        return file_key_list


    def _load_s3_html(self, file_key):
        """
        Loads HTML file from S3 to memory.
        Args:
            file_key: file identifier in storage.
        Returns:
            The decoded file contents.
        """
        s3_obj = self.s3_resource.Object(self.BUCKET_NAME, file_key)
        url = s3_obj.metadata['url'] if 'url' in s3_obj.metadata else ''
        htmldoc = s3_obj.get()['Body'].read().decode('utf-8')

        return url, htmldoc


    def _remove_s3_object(self, file_key):
        """Deletes object from S3."""
        return self.s3_resource.Object(self.BUCKET_NAME, file_key).delete()


    def _create_ii_conn(self):
        """
        Set up connection with MongoDB.
        Returns:
            The setup client and DB from MongoDB
        """
        client = MongoClient(self.II_DB_HOST, self.II_DB_PORT)
        db = client[self.II_DB_NAME]
        self.logger.info("Connected to Inverted Index DB!")

        return client, db


    def _get_wordnet_pos(self, word):
        """Maps POS tag to first character lemmatize() accepts."""
        tag = nltk.pos_tag([word])[0][1][0].upper()
        tag_dict = {"J": wordnet.ADJ,
                    "N": wordnet.NOUN,
                    "V": wordnet.VERB,
                    "R": wordnet.ADV}

        return tag_dict.get(tag, wordnet.NOUN)


    def _process_text(self, s3_key_list):
        """
        Args:
            s3_key_list: The keys from S3 bucket.
        Returns:
            processed text/word list
        """

        punctuations = ")?:!.,;(;,'#$%&1234567890-=^~@+*[]\{\}<>/_"
        doc_tokens = dict()

        for file_key in s3_key_list:

            file_words = []
            url, doc = self._load_s3_html(file_key=file_key)

            document = BeautifulSoup(doc, features="html.parser").findAll(text=True)
            text = ''
            blacklist = [
                '[document]', 'noscript', 'header', 'html',
                'meta', 'head', 'input', 'script', 'style',
            ]

            for t in document:
                if t.parent.name not in blacklist:
                    t = t.strip()
                    if len(t) > 0:
                        text += t + ' '

            doc_sentences = nltk.sent_tokenize(text)

            # stemming & lemmatizing
            wordnet_lem = WordNetLemmatizer()
            for sentence in doc_sentences:

                sentence = sentence.rstrip()                    # trimming
                sentence = re.sub('[\W_]+', ' ', sentence)      # removing unknown characters
                sentence_words = nltk.word_tokenize(sentence)   # tokenizing

                # removing stopwords
                swords = stopwords.words('english')
                best_words = [ w for w in sentence_words if w not in swords ]

                # lemmatizing
                for idx, word in enumerate(best_words):
                    pos = self._get_wordnet_pos(word)
                    best_words[idx] = wordnet_lem.lemmatize(word, pos=pos)

                file_words += best_words

            doc_tokens[url] = file_words

            # remove file from S3
            # self._remove_s3_object(file_key=file_key)
            self.logger.debug("Processed doc removed from storage: {}".format(url))
            label_dict = { 'doc': file_key, 'url': url }
            prom_processed_files.labels(**label_dict).inc()


        return doc_tokens


    def _create_inverted_index(self, doc_words):
        """
        Create inverted index for a set of processed documents.
        Args:
            doc_words: tokens grouped by document.
        Returns:
            inverted index
        """
        # creates default structure
        dd = lambda: defaultdict(lambda: 0)
        inverted_index = defaultdict(dd)

        # populate inverted index
        for doc, tokens in doc_words.items():
            for tk in tokens:
                inverted_index[tk][doc] += 1

        self.logger.info("Inverted index length: {}".format(len(inverted_index)))

        return inverted_index


    def _update(self, d, u):
        for k, v in u.items():
            if isinstance(v, abc.Mapping):
                d[k] = self._update(self, d.get(k, {}), v)
            else:
                d[k] = v
        return d


    def _update_inverted_index(self, inverted_index):
        """Save inverted index into MongoDB."""
        self.logger.info("Updating inverted index...")
        index = self.ii_db.index
        while True:
            try:
                current_ii = index.find_one({})
                self.logger.info(type(current_ii))
                self.logger.info(current_ii.keys())
                if len(current_ii) == 0:
                    current_ii = dict()
                current_ii = self._update(current_ii, inverted_index)

                result = index.update_one({}, current_ii, upsert=True)
                self.logger.debug('One post: {}'.format(result.inserted_id))
                break
            except Exception as err:
                self.logger.error('Error updating inverted index: {}'.format(err))
                time.sleep(30)
                continue


if __name__ == '__main__':

    # load dotenv
    dotenv_path = sys.argv[1] if len(sys.argv) > 1 else '.env'
    load_dotenv(dotenv_path=dotenv_path)
    logger = config_logging()

    # start up the server to expose the metrics
    prom.start_http_server(9090)

    # run indexer
    while True:
        try:
            bingo_indexer = indexer()
            bingo_indexer.run()
        except Exception as err:
            logger.critical('RIP Indexer: {}'.format(traceback.format_exc()))
            time.sleep(5)
            continue
