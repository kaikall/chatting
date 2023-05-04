import sys
import socket
import threading

def receive_msgs(client_socket):
    while True:
        try:
            msg = client_socket.recv(1024).decode('utf-8')
            print(msg)
        except:
            print("An error occurred. Closing the connection.")
            client_socket.close()
            break

def main():
    if len(sys.argv) != 3:
        print("Client properly started with following format: python3 chatclient.py <port> <username>")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Invalid port number")
        sys.exit(1)

    if(port < 1 or port > 65535):
        print("Invalid port number")
        sys.exit(1)

    username = sys.argv[2]

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect(("127.0.0.1", port))
    except:
        print("Failed to connect to the server.")
        sys.exit(1)

    client_socket.send(username.encode('utf-8'))

    receive_thread = threading.Thread(target=receive_msgs, args=(client_socket,))
    receive_thread.start()

    while True:
        msg = input()
        client_socket.send(msg.encode('utf-8'))

if __name__ == "__main__":
    main()