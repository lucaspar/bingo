# Build a domain load balancer
# Author: Jin Huang
# Initial date: 10/29/2019

# Import useful libs
import socket
# import redis
import ast
import random
import threading
import struct
from urllib.parse import urlparse
from collections import Counter
import sys
import json
import pickle
import traceback


class domain_balancer(object):
    def __init__(self):
        self.nb_crawler = 2
        self.nb_urls_init = 1
        self.receive_size = 4
        self.thresh_url = 0
        self.nb_url_increase = 0

        self.PORT = 23456
        self.HOSTNAME = '127.0.0.1'
#         self.redis_conn = redis.Redis('localhost')
#         self.all_redis_keys = self.redis_conn.keys()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tmp_create_domain(self):
        """
        A tmp function, just make some initial domains and save them into redis

        :return: NA
        """

        # Create domain list
        # TODO: we will need more initial domains in the future!!!
        init_domain = {
            "https://www.wikipedia.org": {"status": "000", "timestamp": "000"},
            "https://www.nd.edu": {"status": "000", "timestamp": "000"},
            "https://www.quora.com": {"status": "000", "timestamp": "000"}
        }

        # Save the data into redis
        for key in init_domain:
            value = init_domain.get(key, {})
            print(key, init_domain.get(key, {}))

#             self.redis_conn.hmset(key, value)



    def process_metadata_str(self, metadata_str):
        """
        Process the metadata from the crawler:
            For the processed URLs: Remove the duplications
            For the new URLs: Generate the metadata and save into redis

        :parameter
            metadata_str: the decoded metadata received from the crawler

        :return:
            A metadata dictionary after de-duplication.
        """
        result = {}

        for key, value in metadata_str.items():
            # Deal with the new URLs
            if key == "new_urls":
                # Assign the empty status and time stamp for the new urls
                for url in value:
                    result[url] = {"status": "000", "timestamp": "000"}

            # Deal with the processed URLs
            else:
                if value not in result.values():
                    result[key] = value

        return result


    def check_redis_and_save_data(self, conn, data):
        """
        Write URLs to the URL Map with some metadata (see below).
        If URL already exists, do nothing.

        :parameter:
            data: de-duplicated metadata

        :return: N/A
        """

        for key in data:
            value = data.get(key, {})

            # Check whether this key exists in redis
            if conn.exists(key):
                pass
            else:
                conn.hmset(key, value)


    def get_socket_listen(self):
        """
        Socket listening.

        :return: NA
        """
        # Socket connection: balancer starts to listen
        server_address = (self.HOSTNAME, self.PORT)
        print("Listening on {}:{}".format(self.HOSTNAME, self.PORT))
        self.sock.bind(server_address)
        self.sock.listen(1)


    def get_socket_acceptance(self):
        """
        Socket accepting.

        :return: NA
        """

        # Socket connection: balancer accepts
        connection, client_address = self.sock.accept()
        print("Connection accepted.")

        return connection, client_address


    def get_balanced_urls(self):
        """
        Balancing the domains and distribute them to the crawlers.

        :return: The balanced URLs
        """

        # TODO: Update the nb of URLs according to the data size in redis
        nb_total_url = len(self.all_redis_keys)
        print("!!!!! Number of total URL is %d" % nb_total_url) # Confirmed!


        if nb_total_url <= self.thresh_url:
            print("We need more URLs...")
            pass

        else:
            # TODO: How to decide the rules for nb of URLs sending to each crawler??
            nb_url_single_crawler = self.nb_urls_init + self.nb_url_increase


        domain_url_list = []
        domain_list = []

        for url in self.all_redis_keys:
            url = url.decode()
            parsed_uri = urlparse(url)
            domain_result = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)

            # Get the list for the domains and URLs
            domain_url_list.append((domain_result, url))
            domain_list.append(domain_result)

        # Sort them to make sure they are both in a same order
        domain_url_list.sort()
        domain_list.sort(key=lambda x: x[0])
        print("Confirming the domain list...")
        print(domain_list)

        # Count the number of domains
        counts = Counter(domain_list)
        print("There are %d different domains." % len(counts.keys()))

        # Get some URLs from each domain
        return_key_list = []

        for i in range(len(counts.keys())):
            for n in range(nb_url_single_crawler):
                one_random_key = domain_url_list[random.randint(0, len(domain_list)-1)]
                return_key_list.append(one_random_key)
                # Remove the key from redis after getting it
                self.redis_conn.delete(one_random_key[1])

        balanced_urls = []

        for i in range(len(return_key_list)):
            balanced_urls.append(return_key_list[i][1])

        # print(balanced_urls)
        # sys.exit(0)

        return balanced_urls


    def get_one_url_for_test(self):
        """
        A test function, only get one random URL for testing.

        :return: A random URL from Redis
        """
        return(self.redis_conn.randomkey())



    def create_one_thread(self, conn, add):
       """

       :param sock:
       :return:
       """
       print("A new thread started!")

       try:
           while True:
               # Get the URL list: Use the get_balanced_urls function
               url_list = self.get_balanced_urls()

               # This is for testing and debugging....
               # url_list = self.get_one_url_for_test()
               print("This is testing multiple URLs...")
               print(url_list)
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
                   data_size_str = conn.recv(self.receive_size)
                   data_size = struct.unpack('>I', data_size_str)[0]

                   # Receive the metadata and decode
                   total_data = conn.recv(data_size)
                   str_metadata_decode = total_data.decode()
                   print("!!!! Checking the received metadata.")
                   print(str_metadata_decode)

                   # Organize the raw data received and deduplicate
                   print("Processing data and remove duplicates...")
                   metadata = self.process_metadata_str(ast.literal_eval(str_metadata_decode))
                   print("!!!! Checking the processed data")
                   print(metadata)

                   # Compare the data with that in Redis and decide whether to save
                   print("Saving metadata into Redis database...")
#                    self.check_redis_and_save_data(conn=self.redis_conn, data=metadata)
                   print()

               except Exception as e:
                   print(str(e))
                   continue


       except Exception as e:
           print(str(e))
           print(traceback.format_exc())
           conn.close(),



###############################################
# Main function
###############################################
if __name__ == '__main__':
    balancer = domain_balancer()

    # Connect to the socket: listen
    balancer.get_socket_listen()

    # Build the redis database and save sample
    balancer.tmp_create_domain()
    print("[INFO] Data saved into redis.")

    # Make multi-thread for socket communication
    while True:
        try:
            # Get socket acceptance.
            sock_conn, sock_add = balancer.get_socket_acceptance()

            th = threading.Thread(target=balancer.create_one_thread,
                                  args=(sock_conn, sock_add))
            th.start()

        except:
            break
