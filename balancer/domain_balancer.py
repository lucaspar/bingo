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
nb_urls = 0
receive_size = 1024

# Set up the 1st set of port and hostname: balancer receive info
PORT_1 = 12345
HOSTNAME_1 = '127.0.0.1'

# Set up the 2nd set of port and hostname: crawler receive info
PORT_2 = 23456
HOSTNAME_2 = '127.0.0.2'

#######################################
# Define the functions
#######################################
def tmp_create_domain():
    """
    A tmp function, just make some initial domains and save them into redis

    :return: a domain list, not important anyways so dont be too serious!
    """

    # Create domain list
    init_domain = {{"url": "https://www.wikipedia.org",
                    "status" : "000",
                    "timestamp":"000"},
                   {"url": "https://www.nd.edu",
                    "status": "000",
                    "timestamp": "000"},
                   {"url": "https://www.quora.com",
                    "status": "000",
                    "timestamp": "000"}}

    # Save the data into redis
    conn = redis.Redis('localhost')
    conn.hmset("sample_domain", init_domain)

    # Only return the keys
    data = conn.hget("sample_domain")

    return data

def balanced_domain_from_redis(urls):
    """
    Fetch the domain from redis database and balancing

    :return:
    """
    # TODO: Put the code here for balancing the domains
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
# Keep the socket open all the time
while True:
    # Socket 2: Balancer connect
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_2:
        sock_2.connect((HOSTNAME_2, PORT_2))

        # Get the URLs from the redis database
        urls = tmp_create_domain()
        print(urls)

        #TODO: Only randomly select a portion of URLs for balancing
        #TODO: How to define the nb of URLs need to choose for a time?
        random_urls = None

        # Get balanced URLs
        balanced_urls = balanced_domain_from_redis(urls=random_urls)

        # Socket 2: balancer sends
        sock_2.sendall(balanced_urls)

    # Socket 1: balancer listens
    sock_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address_1 = (HOSTNAME_1, PORT_1)
    print("Listening on {}:{}".format(HOSTNAME_1, PORT_1))
    sock_1.bind(server_address_1)
    sock_1.listen(1)

    # Socket 1: balancer accepts
    connection_1, client_address_1 = sock_1.accept()

    # Socket 1: balancer receives metadata
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_1:
        sock_1.connect((HOSTNAME_1, PORT_1))

        try:
            print("Connection from", client_address_1)

            while True:
                str_metadata = connection_1.recv(receive_size)

                # Organize the raw data received and deduplicate
                metadata = process_metadata_str(str_metadata)

                # Compare the data with that in Redis and decide whether to save
                check_data_with_redis(metadata)

        except Exception as e:
            print(e)






