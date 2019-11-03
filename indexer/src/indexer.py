# Creat the indexers that can read the files from a shared volume
# and update the inverted index entries.
# Author: Jin Huang
# Initial version date: 11/03/2019

# Import necessary libraries
from urllib.parse import urlsplit, urljoin
from bingo_proxy import BingoProxy
from dotenv import load_dotenv
from collections import deque
from bs4 import BeautifulSoup
import requests
import socket
import boto3
import json
import re
import os
import hashlib
import urllib.robotparser
from urllib.parse import urlparse
import time

# define some parameters


# set up and fetch the file from S3
