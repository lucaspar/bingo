# A temporary fake crawler (client)
# Author: Jin Huang
# Initial date: 10/09/2019

# Import useful libs
import socket
import json

receive_size = 1024

# Load the fake data from JSON
json_path = "/Users/kiyoshi/Desktop/2019_Fall/OS/project/bingo/balancer/fake_metadata.json"

with open(json_path) as json_file:
    data = json.load(json_file)

# Encode the data into bytes
data_str = json.dumps(data)

# Set up the 1st port and hostname
# Crawler sends the metadata, balancer receives
PORT = 12345
HOSTNAME = '127.0.0.1'

# Socket connection: crawler connects
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOSTNAME, PORT))

    while True:
        # Socket connection: crawler receives
        try:
            total_data = ""

            while True:
                # Receive the URLs and decode
                urls = sock.recv(receive_size)
                urls_decode = urls.decode()

                if urls:
                    total_data += urls
                else:
                    print("No more data.")
                    break

        except Exception as e:
            print(str(e))

        # XXXXXX

        # Socket connection: crawler sends
        sock.sendall(data_str.encode())



