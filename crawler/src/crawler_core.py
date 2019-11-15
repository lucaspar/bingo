# Author: Sophia Abraham
from urllib.parse import urlsplit, urljoin
from bingo_proxy import BingoProxy
from dotenv import load_dotenv
from collections import deque
from bs4 import BeautifulSoup
import requests
import socket
import select
import boto3
import json
import re
import os
import hashlib
import urllib.robotparser
from urllib.parse import urlparse
import time
import struct
import traceback
import sys

# Sophia : Code establish communication between client and server to request and send URLS
PORT = 23456
HOSTNAME = '127.0.0.1'

# receive_size = 1024
receive_size = 4

url_list = []


def store_in_s3(bucket, file_name, data):
    '''
    Creates a new object in S3

     :params:
         bucket:     S3 bucket reference
         file_name:  identifier string
         data:       serializable data for storing
     :return:
         list: a list of available proxies
    '''

    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, file_name)
    # res = obj.put(Body=json.dumps(data))
    res = obj.put(Body=data)
    # access more info with res['ResponseMetadata']
    return bool(res)


def make_dict(err):
    return {
        'status': err,
        'timestamp': time.time(),
    }


def get_robots_txt_url(url):
    # https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url
    parsed_uri = urlparse(url)
    robots_url = '{uri.scheme}://{uri.netloc}/robots.txt'.format(uri=parsed_uri)
    return robots_url


if __name__ == "__main__":
   
    blacklisted_urls = set()  # good list of blacklisted urls
    blacklisted_domains = set()
    processed_urls = set()
    foreign_urls = set()
    # broken_urls = set()
    local_urls = set()
    rp = urllib.robotparser.RobotFileParser()
    # Trick rp library - fake an access to robots.txt from their POV
    rp.last_checked = True

    load blacklisted urls and domains
    with open('../../blacklisted_urls.txt', 'r') as f:
        blacklisted_urls = set(f.read().split())
    blacklisted_urls = set()

    print('# of blacklisted urls:', len(blacklisted_urls))

    with open('../../blacklisted_domains.txt', 'r') as f:
        blacklisted_domains = set(f.read().split())
    blacklisted_domains = set()

    print('# of blacklisted domains:', len(blacklisted_domains))

    # load environment variables
    load_dotenv(dotenv_path='../.env.example')
    bucket_name = os.getenv("S3_BUCKET_NAME")
    concurrency = int(os.getenv("CR_REQUESTS_CONCURRENCY", default=1))
    timeout = int(os.getenv("CR_REQUESTS_TIMEOUT", default=20))
    print("Concurrency", concurrency, "Timeout", timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOSTNAME, PORT))
    # socket.setblocking(0)

    bp = BingoProxy(concurrency=concurrency, timeout=timeout)

    # TODO: rename me
    URL_LIST_THRESHOLD = 10
    SOCKET_TIMEOUT_SECONDS = 3

    while True:
        # url_list = []  # from balancer
        new_urls = []  # for balancer
        balancer_metadata = {}  # metadata for balancer (including new_urls)

        try:
            data = sock.recv(receive_size)
            print(data)
            data = struct.unpack('>I', data)[0]
            urls = sock.recv(data)
            url_list = json.loads(urls.decode())
            print('got some urls: ' + str(url_list))

        except Exception as e:
            # print(str(e))
            print(traceback.format_exc())

        for url in url_list:
            
            processed_urls.add(url)
            print("Processing", url)

            # setup proxy and make request
            try:

                try:
                    robots_url = get_robots_txt_url(url)
                    response = bp.request(robots_url).next()
                    rp.parse(response.text)
                    if not rp.can_fetch('*', url):
                        continue  # Cannot fetch
                    # Otherwise can fetch
                except requests.exceptions.HTTPError as err:
                    # https://github.com/python/cpython/blob/3.7/Lib/urllib/robotparser.py
                    if err.code in (401, 403):
                        continue  # Cannot fetch
                    elif err.code >= 400 and err.code < 500:
                        pass  # Can fetch
                    else:
                        continue  # Cannot fetch
                response = bp.request(url).next()
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                # Hash the URL using SHA1 algorithm, use as file name
                url_hash = hashlib.sha1(url.encode()).hexdigest()
                # store_in_s3(bucket_name, url_hash, soup.prettify().encode('utf-8'))
                balancer_metadata[url] = make_dict(response.status_code)  # sending successful crawls as well

            # catch http request errors
            except requests.exceptions.HTTPError as err:
                # Create dictionary with url, error and timestamp
                balancer_metadata[url] = make_dict(err.response.status_code)
                # broken_urls.add(url)
                continue

            # some other unknown error
            except Exception as err:
                # print(err)
                print(traceback.format_exc())
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

                # check if new url has never been seen or blacklisted
                if (absolute not in new_urls) and \
                        (absolute not in processed_urls) and \
                        (absolute not in blacklisted_urls):

                    # check domain too
                    domain = urlparse(absolute).netloc

                    if domain not in blacklisted_domains:
                        new_urls.append(absolute)  # TODO

        # create a JSON object to send metadata to balancer
        balancer_metadata['new_urls'] = new_urls
        balancer_data = json.dumps(balancer_metadata)
        print("[INFO] This are the balancer_data")
        print(balancer_data)
        # Get the size of the metdata and send to the balancer
        print("sending the size of the metadata")
        sock.sendall(struct.pack('>I', len(balancer_data)))
        print("sending the metadata")
        sock.sendall(balancer_data.encode()) 
