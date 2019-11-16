#!/usr/bin/env python
from urllib.parse import urlsplit, urljoin, urlparse
from bingo_proxy import BingoProxy
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import urllib.robotparser
import traceback
import requests
import logging
import hashlib
import socket
import pprint
import struct
import boto3
import json
import time
import os


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


def get_robots_file_url(doc_url):
    """
    Args:
        doc_url: an URL
    Returns
        URL for the robots.txt file of the doc_url's domain.
    """
    parsed_uri = urlparse(doc_url)
    robots_url = '{uri.scheme}://{uri.netloc}/robots.txt'.format(uri=parsed_uri)
    return robots_url


def get_balancer_info():
    """
    Returns
        Balancer's hostname and port.
    """
    env = os.environ.get("ENVIRONMENT", "local")
    host =  os.environ.get("BALANCER_HOST_AWS") if env == "aws" else \
            os.environ.get("BALANCER_HOST_LOCAL")
    port = int(os.environ.get("BALANCER_PORT"))

    assert host and port, "Could not load balancer's hostname and port from environment."

    return host, port


def load_blacklist():
    """
    Loads blacklisted domains and URLs.

    Returns
        Set of blacklisted Domains
        Set of blacklisted URLs
    """

    with open('blacklisted_domains.txt', 'r') as f:
        b_domains = set(f.read().split())

    with open('blacklisted_urls.txt', 'r') as f:
        b_urls = set(f.read().split())

    print('Blacklisted domains and URLs: {} and {}'.format(len(b_domains), len(b_urls)))

    return b_domains, b_urls


if __name__ == "__main__":


    # load environment variables
    load_dotenv(dotenv_path='../.env')
    # print("Loaded environment variables:\n", pprint.pformat(os.environ))
    concurrency = int(os.getenv("CR_REQUESTS_CONCURRENCY", default=1))
    timeout = int(os.getenv("CR_REQUESTS_TIMEOUT", default=20))

    # robots.txt parser
    robot_parser = urllib.robotparser.RobotFileParser()
    robot_parser.last_checked = True

    # load blacklisted urls and domains
    b_domains, b_urls = load_blacklist()

    # connect to balancer
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(get_balancer_info())
            break
        except:
            time.sleep(5)
            continue

    url_list = []
    processed_urls = set()
    bp = BingoProxy(concurrency=concurrency, timeout=timeout)

    # balancer loop
    while True:

        new_urls = []
        balancer_metadata = {}

        try:
            # receive an integer
            data_size = sock.recv(4)
            print("Receiving {} bytes from balancer".format(data_size))
            big_endian_unsigned = ">I"
            data_size = struct.unpack(big_endian_unsigned, data_size)[0]
            urls = sock.recv(data_size)
            url_list = json.loads(urls.decode())
            print('got some urls: ' + str(url_list))

        except Exception as e:
            print(traceback.format_exc())

        for url in url_list:

            processed_urls.add(url)
            print("Processing", url)

            # setup proxy and make request
            try:

                try:
                    robots_url = get_robots_file_url(url)
                    response = bp.request(robots_url).next()
                    robot_parser.parse(response.text)
                    if not robot_parser.can_fetch('*', url):
                        continue  # Cannot fetch
                    # Otherwise can fetch

                except requests.exceptions.HTTPError as err:
                    if err.response.status_code in (401, 403):
                        continue  # Cannot fetch
                    elif err.response.status_code >= 400 and err.response.status_code < 500:
                        pass  # Can fetch
                    else:
                        continue  # Cannot fetch

                response = bp.request(url).next()
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                # store to S3 bucket if in AWS
                if os.environ.get("ENVIRONMENT", "local") == "aws":
                    url_hash = hashlib.sha1(url.encode()).hexdigest()
                    store_in_s3(os.getenv("S3_BUCKET_NAME"), url_hash, soup.prettify().encode('utf-8'))

                balancer_metadata[url] = make_dict(response.status_code)  # sending successful crawls as well

            except requests.exceptions.HTTPError as err:
                # Create dictionary with url, error and timestamp
                balancer_metadata[url] = make_dict(err.response.status_code)
                # broken_urls.add(url)
                continue

            except Exception as err:
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

                # cases in which the URL will be discarded:
                known_schem = ["http", "https"]
                known_exten = ["html", "php", "jsp", "aspx"]
                last_words = absolute_parts.path.split('/')[-1].split('.')
                if absolute_parts.scheme not in known_schem or \
                        len(last_words) > 1 and (last_words[-1] not in known_exten):
                    continue

                # check if new url has never been seen or blacklisted
                if (absolute not in new_urls) and \
                        (absolute not in processed_urls) and \
                        (absolute not in b_urls):

                    # check domain too
                    domain = urlparse(absolute).netloc

                    if domain not in b_domains:
                        new_urls.append(absolute)

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
