
import os
import sys
import socket
import threading
from datetime import datetime, timedelta
import time


class ChatServer:

    def __init__(self, config_file):
        self.config_file = config_file
        self.channels = {}
        self.muted = {}


    def load_channels(self):
        if not os.path.isfile(self.config_file):
            print(f"Configuration file '{self.config_file}' not found.")
            sys.exit(1)
        #reading through config files
        with open(self.config_file, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()

            if len(parts) != 4 or parts[0].lower() != 'channel':
                print(f"Invalid configuration")
                sys.exit(1)

            channel_name = parts[1]
            if channel_name[0].isdigit():
                print(f"Channel name cannot begin with a number")
                sys.exit(1)

            try:
                channel_port = int(parts[2])
            except ValueError:
                print(f"Invalid channel port: {parts[2]}")
                sys.exit(1)

            if(channel_port>=1024 and channel_port<=65535):
                print("Ephemeral ports are invalid")
                sys.exit(1)
            elif(channel_port>65535):
                print("invalid port Number Greater than 65535")
                sys.exit(1)
            try:
                channel_capacity = int(parts[3])
                if channel_capacity < 5:
                    raise ValueError
            except ValueError:
                print(f"Invalid channel capacity: {parts[3]}")
                sys.exit(1)

            if channel_name in self.channels:
                print(f"Duplicate channel name: {channel_name}")
                sys.exit(1)

            for existing_channel in self.channels.values():
                if existing_channel['port'] == channel_port:
                    print(f"Duplicate channel port: {channel_port}")
                    sys.exit(1)

            self.channels[channel_name] = {
                            'port': channel_port,
                            'capacity': channel_capacity,
                            'clients': [],  # List of active clients in the channel
                            'queue': [],    # List of clients waiting to join the channel
                            'lock': threading.Lock()  # Lock to manage access to the clients and queue lists
                        }
     #shutdown funtionality
    def shutdown(self):
        for channel_name, channel_info in self.channels.items():
            for client_socket, _, _ in channel_info['clients']:
                client_socket.close()

        print("[Server message] The server is shutting down.")
        sys.exit(0)

    def process_server_commands(self):
        while True:
            #Everything taken from stdin should have whitespace stripped from both sides before being evaluated as a chat message or a command.
            command = input().strip()
            #shutdown command
            if command == "/shutdown":
                self.shutdown()
            #mute command
            if command.startswith("/mute"):
                try:
                    _, channel_user, mute_time = command.split(" ", 2)
                    channel_name, username = channel_user.split(":", 1)
                    mute_time = int(mute_time)

                    if mute_time <= 0:
                        raise ValueError("Invalid mute time.")

                    # mute logic implemented in the server_command_handler() function

                    if channel_name in self.channels:
                        channel_info = self.channels[channel_name]
                        with channel_info['lock']:
                            user_in_channel = any(user[1] == username for user in channel_info['clients'])
                            user_in_queue = any(user[1] == username for user in channel_info['queue'])

                        if user_in_channel or user_in_queue:
                            mute_end_time = datetime.now() + timedelta(seconds=mute_time)
                            self.muted[username] = mute_end_time

                            current_time = datetime.now().strftime("%H:%M:%S")
                            print(f"[Server message ({current_time}) ] Muted {username} for {mute_time} seconds.")
                            server_msg = f"[Server message ({current_time}) ] You have been muted for {mute_time} seconds."
                            client_msg = f"[Server message ({current_time}) ] {username} has been muted for {mute_time} seconds."

                            # Send the mute messages to the appropriate clients
                            for client, user, _ in channel_info['clients']:
                                if user == username:
                                    client.send(server_msg.encode('utf-8'))
                                else:
                                    client.send(client_msg.encode('utf-8'))
                        else:
                            current_time = datetime.now().strftime("%H:%M:%S")
                            print(f"[Server message ({current_time})] {username} is not here.")
                    else:
                        current_time = datetime.now().strftime("%H:%M:%S")
                        print(f"[Server message ({current_time}) ] {channel_name} does not exist.")

                except ValueError as e:
                    current_time = datetime.now().strftime("%H:%M:%S")
                    print(f"[Server message ({current_time}) ] {e}")


            if command.startswith('/empty'):
                self.empty_channel(command)


            if command.startswith('/kick '):
                parts = command.split(':')
                channel_name = parts[0][6:]
                username = parts[1]

                if channel_name not in self.channels:
                    print(f"[Server message ({time.strftime('%H:%M:%S')}) ] {channel_name} does not exist.")
                    continue

                channel_info = self.channels[channel_name]

                kicked_user = None
                with channel_info['lock']:
                    for client, user, _ in channel_info['clients']:
                        if user == username:
                            kicked_user = client
                            channel_info['clients'].remove((client, user, _))
                            break

                if kicked_user is not None:
                    kicked_user.send(f"[Server message ({time.strftime('%H:%M:%S')}) ] {username} has left the channel.".encode('utf-8'))
                    kicked_user.close()
                    print(f"[Server message ({time.strftime('%H:%M:%S')}) ] Kicked {username}.")
                else:
                    print(f"[Server message ({time.strftime('%H:%M:%S')}) ] {username} is not in {channel_name}.")
    
    def empty_channel(self, command):
        _, channel_name = command.split(' ', 1)
        channel_name = channel_name.strip()

        if channel_name not in self.channels:
            print(f"[Server message ({datetime.now().strftime('%H:%M:%S')}) ] {channel_name} does not exist.")
            return

        with self.channels[channel_name]['lock']:
            for client_socket, username, addr in self.channels[channel_name]['clients']:
                client_socket.close()
                self.channels[channel_name]['clients'].remove((client_socket, username, addr))
                self.channels.pop(username, None)
                self.channels[channel_name]['muted'].pop(username, None)


        print(f"[Server message ({datetime.now().strftime('%H:%M:%S')}) ] {channel_name} has been emptied.")



    def start(self):

        # Start a new thread for processing server commands
        server_command_thread = threading.Thread(target=self.process_server_commands)
        server_command_thread.daemon = True
        server_command_thread.start()

        for channel_name, channel_info in self.channels.items():
            channel_info['clients'] = []
            channel_info['queue'] = []
            channel_info['lock'] = threading.Lock()
            channel_thread = threading.Thread(target=self.accept_connections, args=(channel_name,))
            channel_thread.start()



    
    def accept_connections(self, channel_name):
        channel_port = self.channels[channel_name]['port']
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", channel_port))
        server_socket.listen(5)

        print(f"Channel '{channel_name}' started on port {channel_port}")

        while True:
            client_socket, addr = server_socket.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr, channel_name))
            client_thread.start()
    
    

    
    def send_server_msg(self, channel_name, msg, exclude_client=None):
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_msg = f"[Server message ({timestamp}) ] {msg}"
        with self.channels[channel_name]['lock']:
            for client in self.channels[channel_name]['clients']:
                if client != exclude_client:
                    client['socket'].sendall(formatted_msg.encode())


    def handle_client(self, client_socket, addr, channel_name):
        channel_info = self.channels[channel_name]
        channel_info['muted'] = {}
        username = None
        client_removed = False


        try:
            # Receive the client's username
            username = client_socket.recv(1024).decode('utf-8')
            # Check if the username is already in the channel
            with channel_info['lock']:
                if any(user[1] == username for user in channel_info['clients']):
                    current_time = datetime.now().strftime("%H:%M:%S")
                    error_msg = f"[Server message ({current_time}) ] Cannot connect to the {channel_name} channel."
                    client_socket.send(error_msg.encode('utf-8'))
                    client_socket.close()
                    return

                # Add the client to the waiting queue
                channel_info['queue'].append((client_socket, username, addr))


            # Send the welcome message to the client
            current_time = datetime.now().strftime("%H:%M:%S")
            welcome_msg = f"[Server message ({current_time}) ] Welcome to the {channel_name} channel, {username}."
            client_socket.send(welcome_msg.encode('utf-8'))




            while True:
                # Check if the client is at the front of the queue and if there is room in the channel
                with channel_info['lock']:
                    if channel_info['queue'][0] == (client_socket, username, addr) and len(channel_info['clients']) < channel_info['capacity']:
                        channel_info['clients'].append((client_socket, username, addr))
                        channel_info['queue'].pop(0)
                        break

                    queue_position = channel_info['queue'].index((client_socket, username, addr))
                    msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] You are in the waiting queue and there are {queue_position} user(s) ahead of you."
                    client_socket.send(msg.encode('utf-8'))

                time.sleep(1)

            # Announce the client joining the channel
            join_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {username} has joined the channel."
            print(join_msg)
            for client, _, _ in channel_info['clients']:
                if client != client_socket:
                    client.send(join_msg.encode('utf-8'))

            # Main loop for receiving and forwarding messages
            while True:
                try:
                    # Set a timeout of 100 seconds for receiving messages
                    client_socket.settimeout(100)
                    msg = client_socket.recv(1024).decode('utf-8')
                    client_socket.settimeout(None)

                    if not msg:
                        break

                    # Check if the client is muted
                    with channel_info['lock']:
                        if username in channel_info['muted']:
                            remaining_time = int(channel_info['muted'][username] - time.time())
                            if remaining_time > 0:
                                mute_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] You are still muted for {remaining_time} seconds."
                                client_socket.send(mute_msg.encode('utf-8'))
                                continue
                            else:
                                del channel_info['muted'][username]
                    #quit command
                    if msg == '/quit':
                        quit_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {username} has left the channel."
                        print(quit_msg)
                        with channel_info['lock']:
                            for client, _, _ in channel_info['clients']:
                                if client != client_socket:
                                    client.send(quit_msg.encode('utf-8'))
                        break
                    #list command
                    elif msg == '/list':
                        list_msg = []
                        for channel in self.channels:
                            current = len(self.channels[channel]['clients'])
                            capacity = self.channels[channel]['capacity']
                            queue_length = len(self.channels[channel]['queue'])
                            list_msg.append(f"[ Channel ] {channel} {current}/{capacity}/{queue_length}")
                        client_socket.send('\n'.join(list_msg).encode('utf-8'))

                    elif msg.startswith('/switch '):
                        new_channel_name = msg.split(' ')[1]

                        if new_channel_name not in self.channels:
                            error_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {new_channel_name} does not exist."
                            client_socket.send(error_msg.encode('utf-8'))
                        else:
                            new_channel_info = self.channels[new_channel_name]
                            with new_channel_info['lock']:
                                if any(user[1] == username for user in new_channel_info['clients']) or \
                                        any(user[1] == username for user in new_channel_info['queue']):
                                    error_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] Cannot switch to the {new_channel_name} channel."
                                    client_socket.send(error_msg.encode('utf-8'))
                                else:
                                    # Remove the client from the current channel or queue
                                    with channel_info['lock']:
                                        if (client_socket, username, addr) in channel_info['clients']:
                                            channel_info['clients'].remove((client_socket, username, addr))
                                            leave_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {username} has left the channel."
                                            print(leave_msg)
                                            for client, _, _ in channel_info['clients']:
                                                client.send(leave_msg.encode('utf-8'))

                                        if (client_socket, username, addr) in channel_info['queue']:
                                            channel_info['queue'].remove((client_socket, username, addr))

                                    # Add the client to the new channel's waiting queue
                                    new_channel_info['queue'].append((client_socket, username, addr))

                                    # Update the channel_name variable for the new channel
                                    channel_name = new_channel_name
                                    channel_info = self.channels[channel_name]

                    elif msg.startswith('/send '):
                        parts = msg.split(' ')
                        target_username = parts[1]
                        file_path = ' '.join(parts[2:])

                        if not os.path.exists(file_path):
                            error_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {file_path} does not exist."
                            client_socket.send(error_msg.encode('utf-8'))

                        target_socket = None
                        with channel_info['lock']:
                            for client, user, _ in channel_info['clients']:
                                if user == target_username:
                                    target_socket = client
                                    break

                        if target_socket is None:
                            error_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {target_username} is not here."
                            client_socket.send(error_msg.encode('utf-8'))

                        elif os.path.exists(file_path):
                            success_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] You sent {file_path} to {target_username}."
                            client_socket.send(success_msg.encode('utf-8'))

                            server_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {username} sent {file_path} to {target_username}."
                            print(server_msg)

                            self.send_file(client_socket, target_socket, file_path)
                    
                    
                    
                    if msg.startswith('/whisper '):
                        whisper_parts = msg.split(maxsplit=2)
                        if len(whisper_parts) >= 3:
                            target_username, whisper_msg = whisper_parts[1], whisper_parts[2]
                            target_client = None

                            with channel_info['lock']:
                                for client, user, _ in channel_info['clients']:
                                    if user == target_username:
                                        target_client = client
                                        break

                            if target_client:
                                whisper_msg = f"[ {username} whispers to you: ({time.strftime('%H:%M:%S')}) ] {whisper_msg}"
                                target_client.send(whisper_msg.encode('utf-8'))
                            else:
                                not_here_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {target_username} is not here."
                                client_socket.send(not_here_msg.encode('utf-8'))

                            print(f"[ {username} whispers to {target_username}: ({time.strftime('%H:%M:%S')}) ] {whisper_msg}")

                        else:
                            # Invalid whisper command, do nothing
                            pass
                    else:
                        formatted_msg = f"[ {username} ({time.strftime('%H:%M:%S')}) ] {msg}"
                        print(formatted_msg)
                        for client, _, _ in channel_info['clients']:
                            if client != client_socket:
                                client.send(formatted_msg.encode('utf-8'))

                except socket.timeout:
                    # Handle AFK clients (idle)
                    afk_msg = f"[Server message ({time.strftime('%H:%M:%S')}) ] {username} went AFK."
                    print(afk_msg)
                    with channel_info['lock']:
                        for client, _, _ in channel_info['clients']:
                            if client != client_socket:
                                client.send(afk_msg.encode('utf-8'))
                    break

                except Exception as e:
                    print(f"Error handling client {username} at {addr}: {e}")
                    break



            # Remove the client from the channel and queue
            with channel_info['lock']:
                channel_info['clients'].remove((client_socket, username, addr))
                if (client_socket, username, addr) in channel_info['queue']:
                    channel_info['queue'].remove((client_socket, username, addr))

            client_socket.close()
        except Exception as e:
            if not client_removed:
                channel_name = self.channels.get(username)
                if channel_name:
                    channel_info = self.channels[channel_name]
                    with channel_info['lock']:
                        channel_info['clients'].remove((client_socket, username, addr))
            print(f"Error handling client {username} at {addr}: {str(e)}")


def main(config_file):
    server = ChatServer(config_file)
    server.load_channels()
    server.start()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Server is properly called with the following format: python3 chatserver.py <configfile>")
        sys.exit(1)

    config_file = sys.argv[1]
    main(config_file)