# A temporary fake crawler (client)
# Author: Jin Huang
# Initial date: 10/09/2019

# Import useful libs
import socket


receive_size = 1024

# Load tne fake data from JSON
data = ""

# Set up the 1st port and hostname
# Crawler sends the metadata, balancer receives
PORT_1 = 12345
HOSTNAME_1 = '127.0.0.1'

# Set up the 2nd port and hostname
# Balancer sends the URLs, crawler receives
PORT_2 = 23456
HOSTNAME_2 = '127.0.0.2'

# Socket 2: crawler listens
sock_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address_2 = (HOSTNAME_2, PORT_2)
print("Listening on {}:{}".format(HOSTNAME_2, PORT_2))
sock_2.bind(server_address_2)
sock_2.listen(1)

# Socket 2: crawler accepts
connection_2, client_address_2 = sock_2.accept()

# Socket 2: crawler receives
try:
    print("Connection from", client_address_2)

    while True:
        urls = connection_2.recv(receive_size)

        if urls:
            pass
        else:
            print("No more data...")
            break

except Exception as e:
    print str(e)

"""
The crawler uses the URLs and starts crawling
And blablabla
"""
# Socket 1: crawler connects
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_1:
    sock_1.connect((HOSTNAME_1, PORT_1))

    # Socket 1: crawler sends
    sock_1.sendall(data)
