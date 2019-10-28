# A temporary fake crawler (client)
# Author: Jin Huang
# Initial date: 10/09/2019

# Import useful libs
import socket
import json

receive_size = 1024

# Load the fake data from JSON
json_path = "fake_metadata.json"

with open(json_path) as json_file:
    data = json.load(json_file)

# Encode the data into bytes
data_str = json.dumps(data)

# Set up the 1st port and hostname
# Crawler sends the metadata, balancer receives
PORT = 23456
HOSTNAME = '127.0.0.1'

# Socket connection: crawler connects
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOSTNAME, PORT))

    while True:
        # Socket connection: crawler receives
        total_data = b''

        try:
            # Receive the size of the URL
            print("Receiving the size of the URL.")
            url_size_str = sock.recv(receive_size)
            url_size = int(url_size_str)
            print("Size of the URL is %d" % url_size)

            # Receive the URLs and decode
            print("Receiving the URLs.")
            urls = sock.recv(url_size)
            # print(type(urls), urls)
            total_data += urls
            total_data_decode = total_data.decode()


        except Exception as e:
            print(str(e))

        # Socket connection: crawler sends
        # Same as the balancer, get the size of the data first
        print("Sending the size of data")
        sock.sendall(str(len(data_str)).encode())

        # Then, send the whole data to the balancer
        print("Sending metadata.")
        sock.sendall(data_str.encode())



