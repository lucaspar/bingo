#!/usr/bin/env python
import re
import os
import sys
import nltk
import time
import boto3
import pprint
import logging
import traceback
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient
from collections import defaultdict
from colorlog import ColoredFormatter
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import sent_tokenize, word_tokenize

# download NLTK dependencies
nltk_deps = ['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger']
for d in nltk_deps:
    nltk.download(d)


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
        self.nb_file_fetch = 5
        self.s3 = boto3.resource('s3')
        self.bucket = self.s3.Bucket(self.BUCKET_NAME)

        # establish connection
        self.ii_client, self.ii_db = self._create_ii_conn()


    def run(self, daemon=True):
        """Run autonomously."""
        while True:

            s3_objects = self._fetch_s3_obj()           # fetch
            tokens = self._process_text(s3_objects)     # process
            index = self._create_inverted_index(tokens) # index
            self._update_inverted_index(index)          # store

            if not daemon:
                break


    def _fetch_s3_obj(self):
        """
        Get the documents from S3.
        Returns:
            List of document keys in S3.
        """

        file_key_list = []

        # Check the number of files in the S3
        # TODO: How to prevent more than one indexer to
        #  fetch the list at the same time.
        for bucket_object in self.bucket.objects.all():
            file_key_list.append(bucket_object.key)

        self.logger.debug("There are {} files in S3.".format(len(file_key_list)))

        # TODO: How to decide the number of files we should fetch??
        if (len(file_key_list)) >= self.nb_file_fetch:
            file_key_list_return = file_key_list[0:self.nb_file_fetch]
            return file_key_list_return

        elif (len(file_key_list) <= self.nb_file_fetch) and (len(file_key_list) > 0):
            file_key_list_return = file_key_list[0]
            return file_key_list_return

        self.logger.warn("There are no documents in S3. Nothing to do...")
        time.sleep(10)
        return []


    def _load_s3_html(self, file_key):
        """
        Loads HTML file from S3 to memory.
        Args:
            file_key: file identifier in storage.
        Returns:
            The decoded file contents.
        """
        s3_obj = self.s3.Object(self.BUCKET_NAME, file_key)
        htmldoc = s3_obj.get()['Body'].read().decode('utf-8')

        return htmldoc


    def _remove_s3_object(self, file_key):
        """Deletes object from S3."""
        return self.s3.Object(self.BUCKET_NAME, file_key).delete()


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
        result_list = []

        for file_key in (s3_key_list):
            file_word_list = []

            self.logger.debug("Processing {}...".format(file_key))
            file = self._load_s3_html(file_key=file_key)

            document = BeautifulSoup(file, features="html.parser").findAll(text=True)
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
            self.logger.debug("Sentences in file: {}".format(len(doc_sentences)))

            # stemming & lemmatizing
            wordnet_lem = WordNetLemmatizer()

            # tokenizing
            # TODO: LUCAS -- WHY 5:10 ??
            for one_sentence in doc_sentences[5:10]:
                one_sentence = one_sentence.rstrip()
                sentence_words = nltk.word_tokenize(one_sentence)

                for word in sentence_words:
                    word = word.lower()
                    word = ''.join([i for i in word if not i.isdigit()])

                    # removing punctuation
                    if word and word in punctuations:
                        try:
                            sentence_words.remove(word)
                        except ValueError:
                            self.logger.debug('Failed removing word {}'.format(word))
                            continue

                # removing stopwords
                filtered_list = [word for word in sentence_words if word not in stopwords.words('english')]

                # lemmatizing
                for idx, word in enumerate(filtered_list):
                    pos = self._get_wordnet_pos(word)
                    sentence_words[idx] = wordnet_lem.lemmatize(word, pos=pos)

                file_word_list += sentence_words

            # remove duplicates
            new_list = list(set(file_word_list))
            result_list.append(new_list)

            # remove file from S3
            # self._remove_s3_object(file_key=file_key)
            self.logger.debug("Processed doc removed from storage: {}".format(file_key))


        return result_list


    def _create_inverted_index(self, tokens):
        """
        Create inverted index for the processed text.
        Returns:
            inverted index
        """
        inverted_index = defaultdict(list)

        for i, tokens in enumerate(tokens):
            for token in tokens:
                inverted_index[token].append(i)
        self.logger.info("Created inverted index with length {}".format(len(inverted_index)))

        return inverted_index


    def _update_inverted_index(self, data):
        """Save inverted index into MongoDB."""
        posts = self.ii_db.posts
        try:
            result = posts.insert_one(data)
            self.logger.debug('One post: {0}'.format(result.inserted_id))
        except Exception as err:
            self.logger.error('Something went wrong: {}'.format(err))


if __name__ == '__main__':

    # load dotenv
    dotenv_path = sys.argv[1] if len(sys.argv) > 1 else '.env'
    load_dotenv(dotenv_path=dotenv_path)
    logger = config_logging()

    # run indexer
    while True:
        try:
            bingo_indexer = indexer()
            bingo_indexer.run()
        except Exception as err:
            logger.critical('RIP Indexer: {}'.format(traceback.format_exc()))
            time.sleep(5)
            continue
