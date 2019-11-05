#!/usr/bin/env python
import sys
import time
import random
import socket

alphabet = list('abcdefghijklmnopqrstuvwxyz'.upper())
host = '0.0.0.0'
port = 13000

if __name__ == "__main__":

    sock = None
    try:

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Socket created :)")
        sock.connect((host, port))
        print("Connected to the server!")

        # keep sending letters until client dies
        while True:
            letter = random.choice(alphabet)
            time.sleep(2)
            print("Sending", letter)
            sock.send(letter.encode())
            new_letter = sock.recv(1).decode()
            print("Received", new_letter)

    # keyboard interrupt, close socket
    except KeyboardInterrupt:
        print("I'll now die peacefully :)")
        sock.close()

    # socket error or any other unknown exception
    except (socket.error, Exception) as err:
        print("Tragic! Client failed with error", err)
