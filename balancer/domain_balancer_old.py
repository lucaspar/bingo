# Build a domain load balancer (server) to communicate with crawler
# Author: Jin Huang
# Initial date: 10/09/2019
# Edited/restart: 10/20/2019
# Ref: Sophia's code XD

# Import useful libs
import socket
import redis
import ast
import random
import threading
import time

#######################################
# Define some parameters
#######################################
nb_crawler = 1
nb_urls = 1 # initial
receive_size = 1024
thresh_url = 0

# Set up the port and hostname
PORT = 23456
HOSTNAME = '127.0.0.1'

#######################################
# Define the functions
#######################################
def tmp_create_domain(redis_conn):
    """
    A tmp function, just make some initial domains and save them into redis

    :return: NA
    """

    # Create domain list
    init_domain = {
                   "https://www.wikipedia.org":{"status" : "000", "timestamp":"000"},
                   "https://www.nd.edu": {"status": "000", "timestamp": "000"},
                   "https://www.quora.com": {"status": "000", "timestamp": "000"}
                   }

    # Save the data into redis
    for key in init_domain:
        value = init_domain.get(key, {})
        print(key, init_domain.get(key, {}))

        redis_conn.hmset(key, value)


def balanced_domain_from_redis(urls):
    """
    Fetch the domain from redis database and balancing

    :return:
    """
    # TODO: reminder-Use URL lib to parse the URL domains

    pass

def process_metadata_str(metadata_str):
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

def check_redis_and_save_data(redis_conn, data):
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
        if redis_conn.exists(key):
            pass
        else:
            redis_conn.hmset(key, value)

def one_new_client(sock):
    """
    Function to run in a separate thread for each connected client
    (Lucas' code from github)

    :param
        sock: A socket
    :return:
        NA
    """
    print("Started a new client")

    try:
        while True:
            letter = sock.recv(1).decode()
            print("Received", letter)
            new_letter = random.choice(alphabet)
            time.sleep(2)
            print("Sending", new_letter)
            sock.send(new_letter.encode())
    except:
        sock.close()

#######################################
# Main
#######################################
# Socket connection: balancer starts to listen
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (HOSTNAME, PORT)
print("Listening on {}:{}".format(HOSTNAME, PORT))
sock.bind(server_address)
sock.listen(1)

# Socket connection: balancer accepts
connection, client_address = sock.accept()
print("Connection accepted.")

# Build the redis database and save sample
conn = redis.Redis('localhost')
tmp_create_domain(redis_conn=conn)
print("[INFO] Data saved into redis.")

while True:
    try:
        th = threading.Thread(target=one_new_client, args=(connection, client_address))
        th.start()

    except:
        sock.close()


    # TODO: Update the nb of URLs according to the data size in redis
    nb_total_url = len(conn.keys())

    # TODO: How to decide the rules for nb of URLs sending to each crawler??
    if nb_total_url <= thresh_url:
        pass
    else:
        pass

    #TODO: Only randomly select a portion of URLs for balancing
    random_urls = None

    # Get balanced URLs
    # TODO: URL balancing
    balanced_urls = balanced_domain_from_redis(urls=random_urls)

    # Socket connection: balancer sending the URLs
    # sock.sendall(balanced_urls)
    """
    Now just randomly get only one URL and send it to the crawler.
    """
    one_random_url = conn.randomkey()
    print(one_random_url)

    # Get the size of data and send it to the crawler.
    print("Sending the size of data")
    connection.sendall(str(len(one_random_url)).encode())

    # Send the URL to the crawler
    print("Sending the URL...")
    connection.sendall(one_random_url)

    # Socket connection: balancer receives metadata
    try:
        total_data = b''

        # Receive the size of the data first
        print("Receiving the size of the crawler data.")
        data_size_str = connection.recv(receive_size)
        data_size = int(data_size_str)

        # Receive the metadata and decode
        str_metadata = connection.recv(data_size)
        total_data += str_metadata
        str_metadata_decode = total_data.decode()

        print(str_metadata_decode)

        # Organize the raw data received and deduplicate
        print("Processing data and remove duplicates...")
        metadata = process_metadata_str(ast.literal_eval(str_metadata_decode))

        # Compare the data with that in Redis and decide whether to save
        print("Saving metadata into Redis database...")
        check_redis_and_save_data(redis_conn=conn,
                                  data=metadata)

    except Exception as e:
        print(str(e))
        break
