# Author: Sophia Abraham
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

# Sophia : Code establish communication between client and server to request and send URLS
# PORT = 23456
# HOSTNAME = '127.0.0.1'

# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# server_address = (HOSTNAME, PORT)
# sock.bind(server_address)

# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#     sock.connect((HOST, PORT))
#     sock.sendall()

def store_in_s3(bucket, file_name, data):
    """
    Creates a new object in S3

    :params:
        bucket:     S3 bucket reference
        file_name:  identifier string
        data:       serializable data for storing
    :return:
        list: a list of available proxies
    """
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, file_name)
    res = obj.put(Body=json.dumps(data))
    # access more info with res['ResponseMetadata']
    return bool(res)


if __name__ == "__main__":

    url_list = ['https://en.wikipedia.org/wiki/Main_Page', 'https://www.yahoo.com/', 'https://cnn.com']
    new_urls = deque(url_list)
    processed_urls = set()
    foreign_urls = set()
    broken_urls = set()
    local_urls = set()

    # load environment variables
    load_dotenv(dotenv_path='../.env')
    bucket_name = os.getenv("S3_BUCKET_NAME")
    concurrency = int(os.getenv("CR_REQUESTS_CONCURRENCY", default=1))
    timeout     = int(os.getenv("CR_REQUESTS_TIMEOUT", default=20))
    print("Concurrency", concurrency, "Timeout", timeout)

    # TODO: submit found URLs to balancer; request new URLs from it.
    while len(new_urls):

        # remove URL from queue
        url = new_urls.popleft()
        processed_urls.add(url)
        print("Processing", url)

        # setup proxy and make request
        try:
            bp = BingoProxy(concurrency=concurrency, timeout=timeout)
            responses = bp.request(url)
            response = responses.next()
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            # Hash the URL using SHA1 algorithm, use as file name
            url_hash = hashlib.sha1(url.encode()).hexdigest()
            store_in_s3(bucket_name, url_hash, str(soup))

        # catch http request errors
        except requests.exceptions.HTTPError as err:
            # TODO: add http code to send balancer
            #       Access it with: err.response.status_code
            broken_urls.add(url)
            continue

        # some other unknown error
        except Exception as err:
            print(err)
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
