# A temporary fake crawler (client)
# Author: Jin Huang
# Initial date: 10/09/2019

# Import useful libs
import socket


data = ""

# Set up the 1st set of port and hostname: balancer receive info
PORT_1 = 12345
HOSTNAME_1 = '127.0.0.1'

# Set up the port and hostname: crawler receive info
PORT_2 = 23456
HOSTNAME_2 = '127.0.0.2'

# Set up the socket
sock_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address_2 = (HOSTNAME_2, PORT_2)
print("Listening on {}:{}".format(HOSTNAME_2, PORT_2))
sock_2.bind(server_address_2)
sock_2.listen(1)

# Set up the socket: step 2- crawler connect
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOSTNAME, PORT))

    # Set up the socket: step 4- crawler starts sending
    s.sendall(data)
    data = s.recv(1024)

print('Received', repr(data))