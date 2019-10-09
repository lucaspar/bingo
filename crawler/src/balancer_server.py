#Author: Sophia Abraham 
#Simulating socket communication between balancer and crawler 
#Based off of https://stackabuse.com/basic-socket-programming-in-python/ 

import socket 

#create the socket 
socket_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 

#acquire the local hostname 
local_hostname = socket.gethostname()

#get the full hostname 
local_full = socket.getfqdn()

#get the IP address 
ip_address = socket.gethostbyname(local_hostname) 

#printing the hostname, domain name and IP address 
print("Working on" + str(local_hostname) + str(local_full) + "with" + str(ip_address))

#bind the socket to port 23456 
server_address = (ip_address, 23456)
print("Starting up on %s port %s", server_address) 
socket_1.bind(server_address) 

#Listen for incoming connections 
socket_1.listen(1) 

while True: 
    #wait for a connection 
    print("Awaiting a connection") 
    connection, client_address=socket_1.accept()

    try: 
        #show who connected 
        print("Connection from", client_address) 

        #receive the data in small chunks and print it 
        while True: 
            data = connection.recv(100) 
            if data: 
                #print the data ouput 
                print(str(data)) 
            else: 
                #once all data is printed quit the loop 
                print("No more data...") 
                break 
    finally: 
        #Close the connection 
        connection.close()


