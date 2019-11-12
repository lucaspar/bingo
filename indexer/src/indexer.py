# Creat the indexers that can read the files from a shared volume
# and update the inverted index entries.
# Author: Jin Huang
# Initial version date: 11/07/2019

# Import necessary libraries
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import boto3
import re
import os
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import SnowballStemmer
from sklearn.feature_extraction.stop_words import ENGLISH_STOP_WORDS
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import random
import pymongo
from pymongo import MongoClient
from collections import defaultdict

class indexer(object):
    def __init__(self):
        # Load env variables
        load_dotenv(dotenv_path='../.env')

        self.BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
        self.AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.CONCURRENCY = int(os.getenv("CR_REQUESTS_CONCURRENCY"))
        self.TIME_OUT = int(os.getenv("CR_REQUESTS_TIMEOUT"))

        self.s3 = boto3.resource('s3')

        # Set other parameters
        self.debug = True
        self.nb_test_doc = 1

        # MongoDB set up
        self.mongo_host = 'localhost'
        self.mongo_port = 12345
        self.db_name = 'inverted_index'


    def fetch_s3_obj(self):
        """
        Get the documents from S3.

        :return: A list for all the keys of the documents in S3.
        """

        bucket = self.s3.Bucket(self.BUCKET_NAME)
        print("[INFO] Connected to our bucket!")

        file_key_list = []

        for bucket_object in bucket.objects.all():
            file_key_list.append(bucket_object.key)

        return file_key_list


    def load_s3_doc(self, file_key):
        """
        Load the document from S3

        :return: The opened file.
        """

        s3_obj = self.s3.Object(self.BUCKET_NAME, file_key)

        return s3_obj.get()['Body'].read().decode('utf-8')


    # TODO: Update s3 file status with processed/not processed
    def check_s3_file(self):
        """

        :return:
        """

        pass


    def build_mongo_connection(self):
        """
        Set up connection with MongoDB.

        :return: The setup client and DB from MongoDB
        """
        print("[INFO] Setting up connection of MongoDB.")

        client = MongoClient(self.mongo_host, self.mongo_port)
        db = client[self.db_name]

        return client, db



    def text_processing(self, s3_key_list):
        """
        s3_key_list: The keys from S3 bucket.

        :return:
        """

        if self.debug:
            print("[Debug info] This is for debugging.")
            nb_doc = self.nb_test_doc

        else:
            print("[INFO] Processing all the files in S3 bucket.")
            nb_doc = len(s3_doc_key_list)

        for i in range(nb_doc):
            # Get the keys for the files.
            if self.debug:
                file_key = s3_key_list[random.choice(range(len(s3_key_list)))]
            else:
                file_key = s3_key_list[i]

            file = self.load_s3_doc(file_key=file_key)
            # print(file) # Confirmed

            """
            Text processing:
                Lower case, remove numbers and diacritics;
                Remove punctuation and whitespaces
                Tokenization
            """
            st = ""

            document = BeautifulSoup(file, features="html.parser").get_text()
            doc_words = word_tokenize(document)

            for line in doc_words:
                line = (line.rstrip())
                if line:
                    if re.match("^[A-Za-z]*$", line):
                        # if (line not in stop and len(line)>1):
                        st = st + " " + line

            # Remove stop words
            st_lower = st.lower()
            word_list = st_lower.split(' ')
            filtered_list = [word for word in word_list if word not in stopwords.words('english')]

            if self.debug:
                print(st_lower[:200])
                print("[Debug Info] Number of words in original document: %d " % len(word_list))
                print("[Debug Info] Number of words after removing stop words: %d" % len(filtered_list))

            # Stemming
            stem_list = []

            stem = SnowballStemmer(language='english')
            for word in filtered_list:
                stem_list.append(stem.stem(word))

            if self.debug:
                print("[Debug info] Words after stemming:")
                for word in stem_list:
                    print(word)


            # Lemmatization
            # TODO: How to choose the pos for different words??
            result_list = []

            lemmatizer = WordNetLemmatizer()
            for word in stem_list:
                result_list.append(lemmatizer.lemmatize(word, pos="v"))

                if self.debug:
                    print (word, lemmatizer.lemmatize(word, pos="v"))

        if self.debug:
            print(result_list)

        return result_list


    def create_inverted_index(self, text):
        """
        Create inverted index for the processed text.

        :return: inverted index
        """



        index = defaultdict(list)

        for i, tokens in enumerate(text):
            for token in tokens:
                # if self.debug:
                #     print(token)

                index[token].append(i)


        # if self.debug:
        #     print(index)

        return index


    def save_to_mongo(self, database, data):
        """
        Save inverted index into MongoDB.

        :return: N/A
        """

        posts = database.posts
        result = posts.insert_one(data)

        print('One post: {0}'.format(result.inserted_id))



###############################################
# Main function
###############################################
if __name__ == '__main__':
    bingo_indexer = indexer()

    print("[INFO] Getting key list from S3...")
    s3_doc_key_list = bingo_indexer.fetch_s3_obj()
    # print(s3_doc_key_list) # Confirmed

    print("[INFO] Start text processing")
    result_list = bingo_indexer.text_processing(s3_key_list=s3_doc_key_list)

    print("[INFO] Creating inverted index (TODO)")
    index = bingo_indexer.create_inverted_index(text=result_list)

    print("[INFO] Creating MongoDB.")
    mongo_client, mongo_db = bingo_indexer.build_mongo_connection()

    print("[INFO] Saving inverted index into MongoDB.")
    bingo_indexer.save_to_mongo(database=mongo_db, data=index)

    # Retrieve the data for debugging
    if bingo_indexer.debug:
        pass




















