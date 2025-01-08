import socket

target_host = "0.0.0.0"
target_port = 9999

# creating a socket object
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connecting the client to the server
client.connect((target_host, target_port))

request = client.send(b"GET / HTTP/1.1\r\nHost: google.com\r\n\r\n")

print(f"[*] Sent: {request}")

# recieve some data
response = client.recv(4096)

print (response)