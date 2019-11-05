# Author: Sophia Abraham
# Simulating socket communication between balancer and crawler
# Based off of https://stackabuse.com/basic-socket-programming-in-python/

import socket

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
