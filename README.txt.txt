chatserver.py and chatclient.py are the 2 main files involved in this project. The server runs on the 127.0.0.1 ip address. If configuration parameters or user typed connection parameters are incorrect then system notifes user about that otherwise it starts server/ connects client with the server.
I have defined 2 classes chatserver and chatclient. The classes have appropriate functions implemented.

list of functions implemented with their respective descriptions:
ChatServer Functions:
load_channels() -- checks if the configuration file exists and reads it line by line. It validates the format and requirements for each line and stores the channel information in the channels dictionary. If any errors are encountered, the server process will exit immediately with status code 1.

Shutdown() -- closes all connections and exits from server

process_server_commands()-- Listens server commands: /mute, /kick , /shutdown and /empty and executes them
empty_channel()-- Empties the specified channel

start()- Starts threads for each chanell and processing server commands

accept_connections()--In an infinite loop, the method accepts incoming connections and starts a new thread to handle each client using the handle_client method.

send_server_msg() --  sends server messages to clients in a channel, excluding a specific client if needed

handle_client() --manage client connections, including placing clients in the waiting queue, moving them to the channel when there's room, and handling client messages and commands, Checks if the username is already in the channel, announces the client joining the channel, Sets a timeout of 100 seconds for receiving messages. Executes the commands : /quit,/list,/switch , /send and /whisper. Removes the client from the channel and queue.

main() – Runs the server


ChatClient Functions:
receive_msgs() – receives the messages from the server and prints on stdout

checks if client provide connection parameters are correct. If incorrect prints why it is incorrect otherwise it connects clients to the server

Tests 
First test : Test of configuration file:
1. I have loaded correct configuration file.
2. I have deleted configuration file
3. I have loaded incorrect configuration file with : same channel name, same channel port, capacity less than 5, port more than 65535 and ephemeral ports(port within 1024-65535 range).
Second test : test server
1) if server was able to run 3 channels in parallel
2) chatclient and connect it with chatserver
3) on adding 6 users when 5 was limit
4) connecting user on incorrect channel
5) connecting user on incorrect port
6) afk user for more than 100 seconds
7) On the commands /Whisper,/Mute,/empty,/kick,/shutdown,/quit,/list/, /switch/, /send.
8) On memory leak



Resources referenced:
https://www.tutorialspoint.com/socket-programming-with-multi-threading-in-python
https://docs.python.org/3/library/datetime.html
https://www.geeksforgeeks.org/simple-chat-room-using-python/
https://pythonprogramming.net/server-chatroom-sockets-tutorial-python-3/
https://docs.python.org/3/library/sys.html
https://www.youtube.com/watch?v=3UOyky9sEQY*
*this helped me understand how to set up the socket and prepare the client/server before additional command functionality was created







 
