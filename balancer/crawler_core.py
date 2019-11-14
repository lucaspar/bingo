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
    # url_list = ['https://en.wikipedia.org/wiki/Main_Page']
    # new_urls = deque(url_list)

    blacklisted_urls = set()  # good list of blacklisted urls
    blacklisted_domains = set()
    processed_urls = set()
    foreign_urls = set()
    # broken_urls = set()
    local_urls = set()
    rp = urllib.robotparser.RobotFileParser()
    # Trick rp library - fake an access to robots.txt from their POV
    rp.last_checked = True

    # TODO: download blacklisted URLs and domains from S3

    # load blacklisted urls and domains
    # with open('../../blacklisted_urls.txt', 'r') as f:
    #     blacklisted_urls = set(f.read().split())
    blacklisted_urls = set()

    print('# of blacklisted urls:', len(blacklisted_urls))

    # with open('../../blacklisted_domains.txt', 'r') as f:
    #     blacklisted_domains = set(f.read().split())
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
        url_list = []  # from balancer
        new_urls = []  # for balancer
        balancer_metadata = {}  # metadata for balancer (including new_urls)

        while len(url_list) < URL_LIST_THRESHOLD:
            try:
                # https://stackoverflow.com/questions/2719017/how-to-set-timeout-on-pythons-socket-recv-method
                if url_list:
                    ready = select.select([sock], [], [], SOCKET_TIMEOUT_SECONDS)[0]
                else:
                    ready = True
                # recv the size (number of bytes) of the payload
                if ready:
                    # Maybe
                    # https://stackoverflow.com/questions/17667903/python-socket-receive-large-amount-of-data
                    data = sock.recv(receive_size)
                    # print(data)
                    data = struct.unpack('>I', data)[0]
                    # print(data)
                else:
                    print('Socket timeout')
                    break
                # data = sock.recv(receive_size)
                # print(data )
                # ack the size of the payload
                # sock.sendall(data)

                # receive the url using the size of the payload
                # url = sock.recv(int(data.decode()))
                url = sock.recv(data)
                # ack the url
                # sock.sendall(url)

                # decode from bytestream to string, then append to url_list
                # swap comments if using url_list instead of one at a time
                # url_list += url.decode()
                url_list.append(url.decode())

                # print(data, url.decode())
                # print(url_list)
                # TODO: termination condition
                # break  # TODO
                # as is, this will continue to go forever

            except Exception as e:
                # print(str(e))
                print(traceback.format_exc())

        # new_urls = deque(url_list)

        # TODO: submit found URLs to balancer; request new URLs from it.
        # while len(new_urls):
        for url in url_list:

            # remove URL from queue
            # url = new_urls.popleft()
            processed_urls.add(url)
            print("Processing", url)

            # setup proxy and make request
            try:
                # bp = BingoProxy(concurrency=concurrency, timeout=timeout)

                # Czech if can crawl
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
                # TODO: What metadata should be sent to the balancer if website is good and robots says we cant scrape to avoid resending?
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
                #   If `absolute` is not a valid URL: TODO - use regex - ('^(?:[a-z]+:)?//', 'i') to see if abs or rel
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

                # check if new url has never been seen or blacklisted
                # if (absolute not in new_urls) and \
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
        # sys.exit()
        # Get the size of the metdata and send to the balancer
        print("sending the size of the metadata")
        # sock.sendall(str(len(balancer_data)).encode())  # uncomment for comm
        # TODO: What if `balancer_data` contains unicode???
        sock.sendall(struct.pack('>I', len(balancer_data)))
        # TODO: send metadata to balancer
        print("sending the metadata")
        sock.sendall(balancer_data.encode())  # uncomment for comm

#             new_urls_data = json.dumps(new_urls)
#             sock.sendall(struct.pack('>I', len(new_urls_data)))
#             # TODO: send metadata to balancer
#             print("sending the new urls")
#             sock.sendall(new_urls_data.encode())

#             print("URLs:\t\tNew:{}\tLocal: {}\tForeign: {}\tProcessed: {}"\
#                 .format(len(new_urls), len(local_urls), len(foreign_urls), len(processed_urls)))
# sock.close() #uncomment for comm