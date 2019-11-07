# Creat the indexers that can read the files from a shared volume
# and update the inverted index entries.
# Author: Jin Huang
# Initial version date: 11/07/2019

# Import necessary libraries
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import socket
import boto3
import json
import re
import os
import time

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

        :return:N/A
        """

        s3_obj = self.s3.Object(self.BUCKET_NAME, file_key)

        return s3_obj.get()['Body'].read().decode('utf-8')


    def save_to_mongo(self):
        """

        :return:
        """
        pass



    def text_processing(self, s3_key_list):
        """

        :return:
        """

        if self.debug:
            print("[INFO] This is for debugging.")
            nb_doc = self.nb_test_doc

        else:
            print("[INFO] Processing all the files in S3 bucket.")
            nb_doc = len(s3_doc_key_list)

        for i in range(nb_doc):
            test_file_key = s3_key_list[i]
            file = self.load_s3_doc(file_key=test_file_key)
            print(file)

            # TODO: Put text processing here.


    # TODO: Do we need to remove the processed files from S3???
    def update_s3_file(self):
        """

        :return:
        """

        pass








###############################################
# Main function
###############################################
if __name__ == '__main__':
    bingo_indexer = indexer()

    print("Getting key list from S3...")
    s3_doc_key_list = bingo_indexer.fetch_s3_obj()
    # print(s3_doc_key_list) # Confirmed

    print("Processing the document.")

















