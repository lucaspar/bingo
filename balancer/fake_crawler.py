# A temporary fake crawler (client)
# Author: Jin Huang
# Initial date: 10/09/2019

# Import useful libs
import socket

# Set up the communication with the server
PORT = 23456
HOSTNAME = '127.0.0.1'

# TODO: Add a random URL list.
url_list = ""

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOSTNAME, PORT))
    s.sendall(url_list)
    data = s.recv(1024)

print('Received', repr(data))