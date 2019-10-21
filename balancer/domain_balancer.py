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

    # TODO: Save the data into redis (How???)

def get_domain_from_redis():
    """
    Fetch the domain from redis database

    :return:
    """

    pass

def receive_data_and_organize():
    """

    :return:
    """

    pass

def get_balanced_urls():
    """

    :return:
    """

    pass


#######################################
# Main
#######################################
# Set up the 1st set of port and hostname: balancer receive info
PORT_1 = 12345
HOSTNAME_1 = '127.0.0.1'

# Set up the port and hostname: crawler receive info
PORT_2 = 23456
HOSTNAME_2 = '127.0.0.2'

# Set up the socket
sock_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address_1 = (HOSTNAME_1, PORT_1)
print("Listening on {}:{}".format(HOSTNAME_1, PORT_1))
sock_1.bind(server_address_1)
sock_1.listen(1)

# Call the function to make initial redis database
tmp_create_domain()

# Keep the socket open all the time
while True:
    # Get the first URLs from the database
    # TODO: get data from redis database (HOW???)


    # Set up the socket
    connection, client_address = sock_1.accept()

    try:
        print("Connection from", client_address)
        while True:
            data = connection.recv(100)
            if data:
                print(str(data))
            else:
                print("No more data...")
                break
    finally:
        connection.close()
