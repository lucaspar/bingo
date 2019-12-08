#!/usr/bin/env python
from colorlog import ColoredFormatter
from urllib.parse import urlparse
from collections import Counter
from dotenv import load_dotenv
import threading
import traceback
import logging
import pprint
import struct
import random
import socket
import redis
import json
import time
import ast
import sys
import os


class DomainBalancer(object):

    def __init__(self):

        self._config_logging()

        self.MIN_URLS_SEND = 1          # send this many urls per crawler at least
        self.MAX_URLS_SEND = 20         # send this many urls per crawler at most
        self.EXPECTED_NB_CRAWLERS = 10  # expected number of crawlers (just as reference, not updated!!)
        while True:
            try:
                self.redis_conn = redis.Redis(
                    host=os.environ.get("URL_MAP_HOST"),
                    decode_responses=True
                )
                self.redis_conn.ping()
                self.logger.info("Balancer connected to URL Map!")
                break
            except:
                self.logger.warning("URL Map seems to be offline. Retrying...")
                time.sleep(5)

        self.PORT = int(os.environ.get("BALANCER_PORT"))
        self.HOST = socket.gethostname()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self._bootstrap_url_map()


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

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(LOG_LEVEL)
        self.logger.addHandler(stream)


    def _bootstrap_url_map(self):
        """
        Save first domains to URL Map for bootstrap.
        """

        # initial URL list
        initial_url_list = {
            "https://en.wikipedia.org/wiki/Main_Page": {
                "status": "",
                "timestamp": ""
            },
            "https://www.nd.edu": {
                "status": "",
                "timestamp": ""
            },
            "http://cnn.com/": {
                "status": "",
                "timestamp": ""
            }
        }

        # Save the data into redis
        for k, v in initial_url_list.items():
            self.redis_conn.hmset(k, v)


    def _process_url_metadata(self, url_meta):
        """
        Process the metadata from the crawler.
        For the processed URLs: Remove duplicates
        For the new URLs: Generate metadata

        Args:
            url_meta: the decoded metadata received from the crawler
        Returns:
            A metadata dictionary after de-duplication.
        """
        result = {}

        for k, v in url_meta.items():
            if k == "new_urls":
                for url in v:
                    result[url] = {"status": "", "timestamp": ""}
            else:
                result[k] = v

        return result


    def _update_url_map(self, conn, data):
        """
        Updates URL Map with new data.

        Args:
            conn: URL Map (Redis) connection
            data: de-duplicated metadata
        """
        for k, v in data.items():
            conn.hmset(k, v)


    def start_listening(self):
        """
        Starts listening for crawler connections.
        """
        self.sock.bind((self.HOST, self.PORT))
        self.sock.listen(1)
        self.logger.debug("Listening on {}:{}".format(self.HOST, self.PORT))


    def stop_listening(self):
        """
        Closes socket connection.
        """
        self.sock.close()


    def _accept_connection(self):
        """
        Accepts new connection.

        Returns:
            new socket for connection
            client address
        """
        connection, client_address = self.sock.accept()
        self.logger.debug("Connection accepted.")

        return connection, client_address


    def _get_domain_from_url(self, url):
        """Returns the domain of a URL."""
        # url = url.decode()
        parsed_uri = urlparse(url)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return domain


    def _rr_domains(self, domain_sets, min_qty):
        """Round Robin set of domains for URL balancing."""
        balanced_urls = []
        while len(domain_sets) > 0:
            domains = domain_sets.keys()
            for d in list(domains):
                url = domain_sets[d].pop()
                balanced_urls.append(url)               # add to balanced
                expname = 'lock_' + url
                self.redis_conn.setex(expname, 60, url) # add expiring lock to key
                if len(domain_sets[d]) == 0:
                    del domain_sets[d]                  # delete domain entry if empty
                if len(balanced_urls) >= min_qty:
                    return balanced_urls                # got enough URLs to send

        self.logger.warning("Did not get ideal qty of URLs: {} / {}".format(len(balanced_urls), min_qty))

        return balanced_urls


    def _get_balanced_urls(self):
        """
        Balancing the domains and distribute them to the crawlers.

        Returns:
            The balanced URLs
        """

        urlmap_size = self.redis_conn.dbsize()
        self.logger.debug("URL Map has {} URLs".format(urlmap_size))

        # loosely avoid race conditions in the beginning with a sleep
        time.sleep(random.random() * 5)

        if urlmap_size == 0:
            self.logger.error("URL Map is empty -- nothing to balance!")
            time.sleep(5)
            return []

        else:
            # decide how many urls to send to a crawler
            # nb_urls_send is an ideal number: the actual quantity may be
            # less if there are not enough urls available for balancing
            max_distributed_urls = urlmap_size / self.EXPECTED_NB_CRAWLERS
            increment = min(self.MAX_URLS_SEND, max_distributed_urls)
            nb_urls_send = int(self.MIN_URLS_SEND + increment)
            self.logger.debug("Sending at most {} URLs to crawlers".format(nb_urls_send))

        # ==== BALANCING ALGORITHM ====
        # for candidate in self.redis_conn.scan_iter(match='userinfo_*'):

        # 1. Get a set of candidate urls ( len(set) >> nb_urls_send ) without locks related
        SCALING_FACTOR = 3
        candidate_set = set()
        for candidate in self.redis_conn.scan_iter():
            # ignore locks
            if candidate.startswith('lock_'):
                continue
            lock_name = 'lock_' + candidate
            if self.redis_conn.exists(lock_name) and self.redis_conn.ttl(lock_name) > 0:
                self.logger.debug("Found a URL in use, skipping...")
                continue
            candidate_set.add(candidate)
            if len(candidate_set) > nb_urls_send * SCALING_FACTOR:
                break

        # 2. Group URL domains in sets
        domain_sets = dict()
        for url in candidate_set:
            domain = self._get_domain_from_url(url)
            if domain not in domain_sets:
                domain_sets[domain] = set()
            domain_sets[domain].add(url)
        self.logger.debug("Got URLs for {} unique domains".format(len(domain_sets)))

        # 3. Round-robin among domain sets popping urls from them
        balanced_urls = self._rr_domains(domain_sets, min_qty=nb_urls_send)
        self.logger.debug("Sending {} URLs to crawler".format(len(balanced_urls)))

        # ==== BALANCING ALGORITHM END ====

        # # OLD BALANCING ALGORITHM:
        # domain_url_list = []
        # domain_list = []

        # for url in self.redis_conn.keys():
        #     url = url.decode()
        #     parsed_uri = urlparse(url)
        #     domain_result = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)

        #     # Get the list for the domains and URLs
        #     domain_url_list.append((domain_result, url))
        #     domain_list.append(domain_result)

        # # Sort them to make sure they are both in a same order
        # domain_url_list.sort()
        # domain_list.sort(key=lambda x: x[0])

        # # Count the number of domains
        # domain_count = Counter(domain_list)
        # self.logger.debug("There are {} different domains.".format(len(domain_count.keys())))

        # # Get some URLs from each domain
        # return_key_list = []
        # for i in range(len(domain_count.keys())):
        #     for _ in range(nb_urls_send):
        #         one_random_key = domain_url_list[random.randint(0, len(domain_list)-1)]
        #         return_key_list.append(one_random_key)
        #         # Remove the key from redis after getting it (???)
        #         self.redis_conn.delete(one_random_key[1])

        # balanced_urls = []

        # for i in range(len(return_key_list)):
        #     balanced_urls.append(return_key_list[i][1])

        # - - - - - - -

        return balanced_urls


    def _release_locks(self, metadata):
        """Release url expiration locks."""
        keys = [ 'lock_' + k for k in metadata.keys() ]
        self.redis_conn.delete(*keys)
        self.logger.debug("Released locks for {} URLs".format(len(keys)))


    def crawler_talk(self, conn):
        """
        Message exchanges between the balancer and a crawler.

        Args:
            conn: socket opened with crawler
        """
        self.logger.info("A new crawler has connected!")

        while True:

            try:

                # balance the url list
                url_list = []
                while len(url_list) < 1:

                    url_list = self._get_balanced_urls()
                    self.logger.debug("Balanced URLs:\n{}".format(pprint.pformat(url_list)))
                    url_list = json.dumps(url_list).encode()

                # send the size and the list to the crawler
                self.logger.debug("Sending a URL list of {} bytes".format(len(url_list)))
                conn.sendall(struct.pack('>I', len(url_list)))
                conn.sendall(url_list)

                # receive the size of incoming data
                data_size = conn.recv(4)
                data_size = struct.unpack('>I', data_size)[0]
                self.logger.debug("Received size of {} from crawler".format(data_size))

                # receive the metadata
                total_data = conn.recv(data_size)
                str_metadata_decode = total_data.decode()
                self.logger.debug("Received metadata: {}".format(str_metadata_decode))

                # process metadata and update URL Map
                metadata = self._process_url_metadata(ast.literal_eval(str_metadata_decode))
                self._release_locks(metadata)
                self.logger.debug("Saving metadata to URL Map: {}".format(pprint.pformat(metadata)))
                self._update_url_map(conn=self.redis_conn, data=metadata)

            except:
                self.logger.error(traceback.format_exc())
                conn.close()
                break


if __name__ == '__main__':

    # load environment variables
    dotenv_path = sys.argv[1] if len(sys.argv) > 1 else '.env'
    load_dotenv(dotenv_path=dotenv_path)

    # create the balancer
    balancer = DomainBalancer()
    balancer.start_listening()
    connected_crawlers = []

    # accept a new connection and start a thread
    while True:

        try:

            cc = {}
            cc['conn'], _ = balancer._accept_connection()
            cc['thread'] = threading.Thread(daemon=True, target=balancer.crawler_talk, args=(cc['conn'],))
            cc['thread'].start()
            connected_crawlers.append(cc)

        except KeyboardInterrupt:

            # no need to stop running threads, as they have the daemon flag
            # stop incoming connections
            balancer.logger.info("KEYBOARD INTERRUPT :: finishing gracefully.")
            balancer.stop_listening()
            exit()

        except:
            balancer.logger.critical("Fatal error in Balancer:\n\n{}".format(traceback.format_exc()))
            break
