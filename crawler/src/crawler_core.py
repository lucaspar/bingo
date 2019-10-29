# Author: Sophia Abraham 

'''
need to configure with aws credentials for this to work 
terminal commands : 
- sudo apt install awscli 
- aws configure 
    > AWS ACCESS KEY 
    > AWS SECRET KEY 
    > DEFAULT REGION : us-east-1 
    > OUTPUT : None 
'''

import re
import requests
from bs4 import BeautifulSoup
from collections import deque
from urllib.parse import urlsplit, urljoin
from bingo_proxy import bingo_proxy 
import socket
import boto3 
import json 

'''
# Sophia - In case we want to remove configuring from the terminal  
AWS_SERVER_PUBLIC_KEY = 'AKIAYPX2GXWYT3BV57BF'
AWS_SERVER_SECRET_KEY = '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'

# Sophia - create a session: 

session = boto3.Session(
    aws_access_key_id= AWS_SERVER_PUBLIC_KEY, 
    aws_secret_access_key= AWS_SERVER_SECRET_KEY,
)
 
# s3 = session.resource('s3')
'''

bucket_name = 'bingo-crawling'

url = "https://en.wikipedia.org/wiki/Main_Page"
new_urls = deque([url])
processed_urls = set()
foreign_urls = set()
broken_urls = set()
local_urls = set()

bingo = bingo_proxy()
proxy_list = bingo.retrieve_proxy_ips()
random = bingo.random_proxy(proxy_list) 
proxy = proxy_list[random]
# Sophia : Code establish communication between client and server to request and send URLS
PORT = 23456
HOSTNAME = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (HOSTNAME, PORT)
sock.bind(server_address)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock: 
     sock.connect((HOST, PORT))
     sock.sendall()



# Function to save to S3 
def save_files_to_s3(bucket, file_name, data): 
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, file_name)
    obj.put(Body=json.dumps(data))

# TODO: submit found URLs to balancer; request new URLs from it.
while len(new_urls):

    # remove URL from queue
    url = new_urls.popleft()
    processed_urls.add(url)
    print("Processing %s" % url)

    # make request
    try:
        # TODO: rotating the proxies? 
        response = requests.get(url, proxies = {"https" : proxy['ip'] + ':' + proxy['port'] , "http": proxy['ip'] + ':' + proxy['port'] })
        soup = BeautifulSoup(response.text, "lxml")
        print(type(soup))
        print(proxy)
        print(response)
        save_files_to_s3(bucket_name, soup.title.string, str(soup))
    except(requests.exceptions.MissingSchema,
           requests.exceptions.ConnectionError,
           requests.exceptions.InvalidURL,
           requests.exceptions.InvalidSchema):
        # TODO: add http code to send balancer
        broken_urls.add(url)
        continue

    # split url into parts
    url_parts = urlsplit(url)
    base_url = "{0.scheme}://{0.netloc}".format(url_parts)
    path = url[:url.rfind('/') + 1] if '/' in url_parts.path else url

    for link in soup.find_all('a'):

        # no hyperlink
        if "href" not in link.attrs:
            continue
        anchor = link.attrs["href"]

        # turn relative urls into absolute
        if anchor.startswith('/'):
            absolute = urljoin(base_url, anchor)
        elif not anchor.startswith('http'):
            absolute = urljoin(path, anchor)
        else:
            absolute = anchor

        absolute_parts = urlsplit(absolute)

        # Cases in which the URL will be discarded:
        #   If `absolute` is not a valid URL : TODO
        #   If `absolute_parts.scheme` is not known (http/https)
        #   If `absolute` has a file extension and it is not of interest
        known_schem = ["http", "https"]
        known_exten = ["html", "php", "jsp", "aspx"]
        last_words = absolute_parts.path.split('/')[-1].split('.')
        if absolute_parts.scheme not in known_schem or \
            len(last_words) > 1 and (last_words[-1] not in known_exten):
            continue

        # differ local and foreign urls (other domain/subdomain)
        if url_parts.netloc == absolute_parts.netloc:
            local_urls.add(absolute)
        else:
            foreign_urls.add(absolute)

        # check if new url has never been seen
        if (absolute not in new_urls) and \
            (absolute not in processed_urls):
            new_urls.append(absolute)

    print("URLs:\t\tNew:{}\tLocal: {}\tForeign: {}\tProcessed: {}"\
        .format(len(new_urls), len(local_urls), len(foreign_urls), len(processed_urls)))
