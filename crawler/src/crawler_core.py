#!/usr/bin/env python
from urllib.parse import urlsplit, urljoin, urlparse
from colorlog import ColoredFormatter
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
import sys
import os


class Crawler(object):

    def __init__(self):

        # setup logging
        self._config_logging()

        # setup robots.txt parser
        self.robot_parser = urllib.robotparser.RobotFileParser()
        self.robot_parser.last_checked = True

        # load blacklisted urls and domains
        self.b_domains, self.b_urls = self._load_blacklist()
        self.sock_balancer = None

        # connect to balancer
        self._restart_connection()

        # setup proxy
        concurrency = int(os.getenv("CR_REQUESTS_CONCURRENCY", default=1))
        timeout = int(os.getenv("CR_REQUESTS_TIMEOUT", default=20))
        self.bp = BingoProxy(concurrency=concurrency, timeout=timeout)

        # initialize other variables
        self.url_list = []
        self.processed_urls = set()


    def _restart_connection(self):
        '''
        Restarts socket connection with balancer.
        '''
        if self.sock_balancer:
            self.sock_balancer.close()
            time.sleep(5)
        self.sock_balancer = self._connect_to_balancer()


    def _are_robots_allowed(self, url):
        '''
        Check robots.txt of URL domain if it's allowed to crawl.

        Args:
            url: URL to be fetched which domain will be verified for .
        Returns:
            True if robots.txt allows crawling or if it was not found.
        '''

        try:
            parsed_uri = urlparse(url)
            robots_url = '{uri.scheme}://{uri.netloc}/robots.txt'.format(uri=parsed_uri)
            response = self.bp.request(robots_url).next()
            self.robot_parser.parse(response.text)
            return self.robot_parser.can_fetch('*', url)

        except requests.exceptions.HTTPError as err:
            if err.response.status_code in (401, 403):
                return False
            elif err.response.status_code >= 400 and err.response.status_code < 500:
                return True
            else:
                return False


    def _request_document(self, url):
        '''
        Requests HTML document.

        Args:
            url: document location as URL string
        Returns:
            soup: BeautifulSoup object
            meta: request metadata to be saved
        '''

        try:

            response = self.bp.request(url).next()
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # store to S3 bucket if in AWS
            if os.environ.get("ENVIRONMENT", "local") == "aws":
                url_hash = hashlib.sha1(url.encode()).hexdigest()
                self._store_in_s3(os.getenv("S3_BUCKET_NAME"), \
                    url_hash, soup.prettify().encode('utf-8'))

            meta = self._make_dict(response.status_code)
            return soup, meta

        except requests.exceptions.HTTPError as err:
            # save url, error, and timestamp
            meta = self._make_dict(err.response.status_code)
            self.logger.debug("HTTP Request failed: [{}] {}".format(
                err.response.status_code, url))

            return None, meta

        except Exception as err:
            self.logger.error(traceback.format_exc())
            return None, None


    def _extract_anchors(self,
                      url,
                      soup,
                      known_schem=["http", "https"],
                      known_exten=["html", "php", "jsp", "aspx"]):
        '''
        Returns list of absolute URLs present in a document.

        Args:
            url: URL of document (used to turn relative URLs into abolute).
            soup: BeautifulSoup object of the document analyzed.
            known_schem: known schemas to include (http|https|ws|file|...)
            known_exten: known file extensions to include, except empty extensions
        Returns:
            set of URLs found in document
        '''

        new_anchors = set()
        if not soup:
            return new_anchors

        # for all anchors in document
        for link in soup.find_all('a'):

            # no hyperlink in anchor
            if "href" not in link.attrs:
                continue

            anchor = link.attrs["href"]
            absolute = ""

            # turn relative urls into absolute
            if anchor.startswith('/'):              # root of domain
                url_parts = urlsplit(url)
                base_url = "{0.scheme}://{0.netloc}".format(url_parts)
                absolute = urljoin(base_url, anchor)

            elif not anchor.startswith('http'):     # relative to current path
                url_parts = urlsplit(url)
                path = url[:url.rfind('/') + 1] if '/' in url_parts.path else url
                absolute = urljoin(path, anchor)

            else:                                   # already absolute
                absolute = anchor

            absolute_parts = urlsplit(absolute)
            last_words = absolute_parts.path.split('/')[-1].split('.')

            # unknown scheme
            if len(known_schem) > 0 and \
                absolute_parts.scheme not in known_schem:
                continue

            # unknown extension
            if len(known_exten) > 0 and len(last_words) > 1 and \
                    (last_words[-1] not in known_exten):
                continue

            # add as new url if it's new and not blacklisted
            if absolute not in new_anchors          and \
                absolute not in self.processed_urls and \
                absolute not in self.b_urls         and \
                urlparse(absolute).netloc not in self.b_domains:

                new_anchors.add(absolute)

        return new_anchors


    def start(self):
        '''
        Starts crawling.
        '''
        try:

            # crawler-balancer communication loop
            while True:

                new_urls = set()
                url_meta = {}
                url_list = self._recv_balanced_urls()

                # for each URL, request the document and extract more URLs
                for url in url_list:

                    self.processed_urls.add(url)
                    self.logger.debug("Processing {}".format(url))

                    # check robots.txt
                    if not self._are_robots_allowed(url):
                        continue

                    soup, url_meta[url] = self._request_document(url)
                    new_urls.update(set(self._extract_anchors(url, soup)))

                # send the url metadata size and content
                url_meta['new_urls'] = list(new_urls)
                data_for_balancer = json.dumps(url_meta)
                self.logger.debug("Sending data to balancer: {}".format(pprint.pformat(data_for_balancer)))
                self.sock_balancer.sendall(struct.pack('>I', len(data_for_balancer)))
                self.sock_balancer.sendall(data_for_balancer.encode())

        except:
            self.logger.critical(traceback.format_exc())
            self._restart_connection()


    def _recv_balanced_urls(self):
        '''
        Receives URLs from Balancer.
        '''

        try:

            # receive size of url metadata
            url_meta_recv_size = self.sock_balancer.recv(4)
            self.logger.debug("Receiving {} bytes from balancer".format(url_meta_recv_size))
            big_endian_unsigned = ">I"
            url_meta_recv_size = struct.unpack(big_endian_unsigned, url_meta_recv_size)[0]

            # receive url metadata
            url_meta_recv = self.sock_balancer.recv(url_meta_recv_size)
            url_list = json.loads(url_meta_recv.decode())
            self.logger.info('Received URLs from Balancer: {}'.format(pprint.pformat(url_list)))

            return url_list

        except Exception:
            self.logger.critical(traceback.format_exc())
            self._restart_connection()


    def _connect_to_balancer(self):
        '''
        Connects to balancer

        Returns:
            Socket with open connection.
        '''
        while True:
            try:
                sock_balancer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock_balancer.connect(self._get_balancer_info())
                self.logger.info("Connected to balancer!")
                break
            except ConnectionRefusedError:
                self.logger.warn("Balancer seems down. Trying again...")
            except Exception:
                self.logger.error(traceback.format_exc())
            time.sleep(5)

        return sock_balancer


    def _store_in_s3(self, bucket, file_name, data):
        '''
        Creates a new object in S3

        Args:
            bucket:     S3 bucket name
            file_name:  identifier string for new object
            data:       serializable data for storing
        Returns:
            a list of available proxies
        '''

        s3 = boto3.resource('s3')
        obj = s3.Object(bucket, file_name)
        res = obj.put(Body=data)
        # access more info with res['ResponseMetadata']

        if res:
            self.logger.info("Document {} stored in S3".format(file_name))
        else:
            self.logger.warn("Document {} S3 storing has failed".format(file_name))

        return bool(res)


    def _make_dict(self, err):
        return {
            'status': err,
            'timestamp': time.time(),
        }


    def _get_balancer_info(self):
        """
        Returns
            Balancer's hostname and port.
        """
        host = os.environ.get("BALANCER_HOST")
        port = int(os.environ.get("BALANCER_PORT", 23456))

        assert host and port, "Could not load balancer's hostname and port from environment."

        return host, port


    def _load_blacklist(self):
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

        self.logger.info('Loaded {} blacklisted domains and {} URLs'.format(len(b_domains), len(b_urls)))

        return b_domains, b_urls


    def _config_logging(self, demo=False):
        """
        Configure logging format and handler.
        """

        # get formatting string
        FORMAT = os.environ.get(
            "LOGGING_FORMAT",
            '%(log_color)s[%(asctime)s] %(module)-12s %(funcName)s(): %(message)s %(reset)s'
        )

        # set
        LOG_LEVEL = logging.DEBUG
        stream = logging.StreamHandler()
        stream.setLevel(LOG_LEVEL)
        stream.setFormatter(ColoredFormatter(FORMAT))

        self.logger = logging.getLogger('main')
        self.logger.setLevel(LOG_LEVEL)
        self.logger.addHandler(stream)

        # usage
        if demo:

            # levels
            self.logger.critical('Protocol critical')
            self.logger.error('Protocol error')
            self.logger.warning('Protocol warning')
            self.logger.debug('Protocol debug')
            self.logger.info('Protocol info')

            # other data
            a_list = list('a list')
            a_dict = {
                'some_key': 'some_value',
                'some_list': a_list,
            }
            self.logger.info('A dictionary: %s', pprint.pformat(a_dict))
            self.logger.info('A list: %s', pprint.pformat(a_list))


if __name__ == "__main__":

    # env vars and logging
    dotenv_path = sys.argv[1] if len(sys.argv) > 1 else '.env'
    load_dotenv(dotenv_path=dotenv_path)

    # initialize crawler and recreate it if needed
    crawler = None
    while True:
        try:
            crawler = Crawler()
            crawler.start()
        except KeyboardInterrupt:
            if crawler:
                crawler.logger.info("KEYBOARD INTERRUPT :: finishing gracefully.")
                crawler.sock_balancer.close()
            exit()
        except:
            continue
