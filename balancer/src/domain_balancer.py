#!/usr/bin/env python
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
import ast
import os


class DomainBalancer(object):

    def __init__(self):

        load_dotenv(dotenv_path='../.env')
        # print("Loaded environment variables:\n", pprint.pformat(os.environ))

        self.nb_urls_init = 1
        self.nb_url_increase = 0
        self.thresh_url = 0

        self.PORT = int(os.environ.get("BALANCER_PORT"))
        self.HOST = os.environ.get("BALANCER_HOST")
        self.redis_conn = redis.Redis('localhost')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


    def bootstrap_url_map(self):
        """
        Save first domains to URL Map for bootstrap.
        """

        # Create domain list
        init_domain = {
            "https://www.wikipedia.org":    {"status": "", "timestamp": ""},
            "https://www.nd.edu":           {"status": "", "timestamp": ""},
            "https://www.quora.com":        {"status": "", "timestamp": ""}
        }

        # Save the data into redis
        for k, v in init_domain.items():
            self.redis_conn.hmset(k, v)


    def process_url_metadata(self, url_meta):
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


    def update_url_map(self, conn, data):
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
        print("Listening on {}:{}".format(self.HOST, self.PORT))


    def accept_connection(self):
        """
        Accepts new connection.

        Returns:
            new socket for connection
            client address
        """
        connection, client_address = self.sock.accept()
        print("Connection accepted.")

        return connection, client_address


    def get_balanced_urls(self):
        """
        Balancing the domains and distribute them to the crawlers.

        Returns:
            The balanced URLs
        """

        nb_total_url = len(self.redis_conn.keys())
        print("URL Map has {} URLs".format(nb_total_url))

        if nb_total_url == 0:
            print("URL Map is empty -- nothing to balance!")
            pass

        else:
            # TODO: How to decide the rules for nb of URLs sending to each crawler??
            nb_url_single_crawler = self.nb_urls_init + self.nb_url_increase


        domain_url_list = []
        domain_list = []

        for url in self.redis_conn.keys():
            url = url.decode()
            parsed_uri = urlparse(url)
            domain_result = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)

            # Get the list for the domains and URLs
            domain_url_list.append((domain_result, url))
            domain_list.append(domain_result)

        # Sort them to make sure they are both in a same order
        domain_url_list.sort()
        domain_list.sort(key=lambda x: x[0])

        # Count the number of domains
        domain_count = Counter(domain_list)

        print("LP: Check the value of this")
        print(pprint.pformat(domain_count))
        print("There are {} different domains.".format(len(domain_count.keys())))

        # Get some URLs from each domain
        return_key_list = []
        for i in range(len(domain_count.keys())):
            for _ in range(nb_url_single_crawler):
                one_random_key = domain_url_list[random.randint(0, len(domain_list)-1)]
                return_key_list.append(one_random_key)
                # Remove the key from redis after getting it
                self.redis_conn.delete(one_random_key[1])

        balanced_urls = []

        for i in range(len(return_key_list)):
            balanced_urls.append(return_key_list[i][1])

        return balanced_urls


    def crawler_talk(self, conn):
        """
        Message exchanges between the balancer and a crawler.

        Args:
            conn: socket opened with crawler
        """
        print("A new thread started!")

        try:
            while True:
                # Get the URL list: Use the get_balanced_urls function
                url_list = self.get_balanced_urls()

                # This is for testing and debugging....
                print("Balanced URLs:\n{}".format(pprint.pformat(url_list)))
                url_list = json.dumps(url_list).encode()

                # Get the size of data and send it to the crawler.
                print("Sending the size of data")
                conn.sendall(struct.pack('>I', len(url_list)))

                # Then send the URL to the crawler
                print("Sending the URL...")
                conn.sendall(url_list)

                # Socket connection: balancer receives metadata
                try:

                    # Receive the size of the data first
                    print("Receiving the size of the crawler data.")
                    data_size = conn.recv(4)
                    data_size = struct.unpack('>I', data_size)[0]

                    # Receive the metadata and decode
                    total_data = conn.recv(data_size)
                    str_metadata_decode = total_data.decode()
                    print("!!!! Checking the received metadata.")
                    print(str_metadata_decode)

                    # Organize the raw data received and deduplicate
                    print("Processing data and remove duplicates...")
                    metadata = self.process_url_metadata(ast.literal_eval(str_metadata_decode))
                    print("!!!! Checking the processed data")
                    print(metadata)

                    # Compare the data with that in Redis and decide whether to save
                    print("Saving metadata into Redis database...")
                    self.update_url_map(conn=self.redis_conn, data=metadata)

                except Exception as e:
                    print(str(e))
                    continue


        except Exception as e:
            print(traceback.format_exc())
            conn.close(),


if __name__ == '__main__':

    # create the balancer
    balancer = DomainBalancer()

    # start URL Map and listen for connections
    balancer.bootstrap_url_map()
    balancer.start_listening()

    # accept a new connection and start a thread
    while True:
        try:
            sock_conn, _ = balancer.accept_connection()
            th = threading.Thread(target=balancer.crawler_talk, args=(sock_conn,))
            th.start()
        except KeyboardInterrupt:
            break
        except:
            continue
