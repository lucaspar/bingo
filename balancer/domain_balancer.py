# Build a domain load balancer (server) to communicate with crawler
# Author: Jin Huang
# Initial date: 10/09/2019
# Edited/restart: 10/20/2019
# Ref: Sophia's code XD

# Import useful libs
import socket
import redis

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

    :return:
    """
    #TODO: Receive the metadata string, organize and deduplicate

    pass

def check_data_with_redis(data):
    """

    :return:
    """

    pass


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
    connection.sendall(str(len(one_random_url)))

    # Send the URL to the crawler
    print("Sending the URL...")
    connection.sendall(one_random_url)

    # Socket connection: balancer receives metadata
    try:
        total_data = b''

        while True:
            # Receive the metadata and decode
            str_metadata = connection.recv(receive_size)

            if str_metadata:
                total_data += str_metadata
            else:
                str_metadata_decode = total_data.decode()

                print("No more data.")
                break

        """
        # Organize the raw data received and deduplicate
        metadata = process_metadata_str(total_data)

        # Compare the data with that in Redis and decide whether to save
        check_data_with_redis(metadata)
        """

    except Exception as e:
        print("nnn")
        print(str(e))
