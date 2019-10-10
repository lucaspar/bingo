# Build a domain load balancer (server) to communicate with crawler
# Author: Jin Huang
# Initial date: 10/09/2019
# Ref: Sophia's code XD

# Import useful libs
import socket

# Define some parameters

# Set up the communication with the client
PORT = 23456
HOSTNAME = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (HOSTNAME, PORT)
print("Listening on {}:{}".format(HOSTNAME, PORT))
sock.bind(server_address)
sock.listen(1)

while True:
    connection, client_address = sock.accept()

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
