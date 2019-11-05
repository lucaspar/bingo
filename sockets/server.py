#!/usr/bin/env python
import sys
import time
import socket
import random
import threading

alphabet = list('abcdefghijklmnopqrstuvwxyz'.upper())
host = '0.0.0.0'
port = 13000

# function to run in a separate thread for each connected client
def on_new_client(sock, addr):

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

if __name__ == "__main__":

    s = socket.socket()

    print('Server started!')

    # enable socket address reusage
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(5)

    # open a new thread for every accepted connection
    try:
        print('Waiting for clients...')
        while True:
            c, addr = s.accept()
            print('New connection from', addr)
            th = threading.Thread(target=on_new_client, args=(c, addr))
            th.start()

    # on exception, close socket
    except:
        s.close()
