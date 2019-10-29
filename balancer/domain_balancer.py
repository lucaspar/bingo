# Build a domain load balancer
# Author: Jin Huang
# Initial date: 10/29/2019

# Import useful libs
import socket
import redis
import ast
import random
import threading
import time



class domain_balancer(object):
    def __init__(self):
        self.nb_crawler = 1
        self.nb_urls_init = 1
        self.receive_size = 1024
        self.thresh_url = 0

        self.PORT = 23456
        self.HOSTNAME = '127.0.0.1'
        self.redis_conn = redis.Redis('localhost')

    def tmp_create_domain(self):
        """
        A tmp function, just make some initial domains and save them into redis

        :return: NA
        """

        # Create domain list
        init_domain = {
            "https://www.wikipedia.org": {"status": "000", "timestamp": "000"},
            "https://www.nd.edu": {"status": "000", "timestamp": "000"},
            "https://www.quora.com": {"status": "000", "timestamp": "000"}
        }

        # Save the data into redis
        for key in init_domain:
            value = init_domain.get(key, {})
            print(key, init_domain.get(key, {}))

            self.redis_conn.hmset(key, value)

    def process_metadata_str(self, metadata_str):
        """
        :parameter
            metadata_str: the decoded metadata received from the crawler
        :return:
            A metadata dictionary after de-duplication.
        """
        result = {}

        for key, value in metadata_str.items():
            if value not in result.values():
                result[key] = value

        return result

    def check_redis_and_save_data(self, conn, data):
        """
        Write URLs to the URL Map with some metadata (see below).
        If URL already exists, do nothing.

        :parameter:
            data: de-duplicated metadata
        :return:
            N/A
        """
        for key in data:
            value = data.get(key, {})

            # Check whether this key exists in redis
            if conn.exists(key):
                pass
            else:
                conn.hmset(key, value)

    def get_socket_connection(self):
        """

        :return:
        """
        # Socket connection: balancer starts to listen
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.HOSTNAME, self.PORT)
        print("Listening on {}:{}".format(self.HOSTNAME, self.PORT))
        sock.bind(server_address)
        sock.listen(1)

        # Socket connection: balancer accepts
        connection, client_address = sock.accept()
        print("Connection accepted.")

        return connection, client_address

    def get_balanced_urls(self):
        """

        :return:
        """

        # TODO: Update the nb of URLs according to the data size in redis
        nb_total_url = len(self.redis_conn.keys())

        # TODO: How to decide the rules for nb of URLs sending to each crawler??
        if nb_total_url <= self.thresh_url:
            pass
        else:
            pass

        # TODO: Only randomly select a portion of URLs for balancing
        random_urls = None

        # Get balanced URLs
        # TODO: Put URL balancing function here
        balanced_urls = None

        return balanced_urls

    def get_one_url_for_test(self):
        """
        A test function, only get one random URL for testing.
        :return:
        """
        return(self.redis_conn.randomkey())


    def create_one_thread(self, sock, conn):
       """

       :param sock:
       :return:
       """

       print("A new thread started!")

       try:
           while True:
               # Get the URL list
               # TODO: Use the get_balanced_urls function in the future
               #url_list = self.get_balanced_urls()
               url_list = self.get_one_url_for_test()

               # Get the size of data and send it to the crawler.
               print("Sending the size of data")
               conn.sendall(str(len(url_list)).encode())

               # Then send the URL to the crawler
               print("Sending the URL...")
               conn.sendall(url_list)

               # Socket connection: balancer receives metadata
               try:
                   # Receive the size of the data first
                   print("Receiving the size of the crawler data.")
                   data_size_str = conn.recv(self.receive_size)
                   data_size = int(data_size_str)

                   # Receive the metadata and decode
                   total_data = conn.recv(data_size)
                   str_metadata_decode = total_data.decode()
                   print(str_metadata_decode)

                   # Organize the raw data received and deduplicate
                   print("Processing data and remove duplicates...")
                   metadata = self.process_metadata_str(ast.literal_eval(str_metadata_decode))

                   # Compare the data with that in Redis and decide whether to save
                   print("Saving metadata into Redis database...")
                   self.check_redis_and_save_data(conn=self.redis_conn, data=metadata)

               except Exception as e:
                   print(str(e))
                   break

       except:
           sock.close()



###############################################
# Main function
###############################################
if __name__ == '__main__':
    balancer = domain_balancer()

    # Connect to the socket: listen and accept
    sock_conn, sock_add = balancer.get_socket_connection()

    # Build the redis database and save sample
    balancer.tmp_create_domain()
    print("[INFO] Data saved into redis.")

    # Make multi-thread for socket communication
    while True:
        try:
            th = threading.Thread(target=balancer.create_one_thread,
                                  args=(sock_conn, sock_add))
            th.start()

        except:
            break


