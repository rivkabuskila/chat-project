import traceback
import time
import random
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import threading
import os

# from common import FILE_DOWNLOAD_PORT
from rudp_client import RudpClientSocket

SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 50000
CLIENT_BACKLOG = 15
MAXIMAL_MESSAGE_SIZE = 500
MAXIMAL_FILE_SIZE = 64 * 1024
#Setting Variables
FILE_DIRECTORY = "files"
CONNECT_MESSAGE = "<connect>"
DISCONNECT_MESSAGE = "<disconnect>"
GET_USERS_MESSAGE = "<get_users>"
SEND_MESSAGE_DIRECT = "<send_message>"
SEND_MESSAGE_ALL = "<send_message_all>"
GET_FILE_LIST = "<get_file_list>"
DOWNLOAD_MESSAGE = "<download>"
CONTINUE_MESSAGE = "<continue>"
STOP_DOWNLOAD = "<stop>"
#List of connected
users = {}
users_lock = threading.Lock()
#Identify the connected by thread name
user_name = threading.local()

send_file_stop_events = {}
send_file_stop_events_lock = threading.Lock()


def download_half_file(file_name, part_one, client_socket):
    file_path = os.path.join(FILE_DIRECTORY, file_name)

    if not os.path.isfile(file_path):
        response = f"<File> <{file_name}> does not exist on the server>"
    elif os.path.getsize(file_path) > MAXIMAL_FILE_SIZE:
        response = f"<File> <{file_name}> is too big to send"
    else:
        job_id = random.randint(10000, 60000)
        file_size = os.path.getsize(file_path)
        response = f"<size><{file_name}><{file_size}><{job_id}><{1 if part_one else 2}>"
        stop_event = threading.Event()
        send_file_thread = threading.Thread(target=send_file, args=(file_name, stop_event, file_size, job_id, part_one, client_socket, user_name.val))
        with send_file_stop_events_lock:
            send_file_stop_events[job_id] = stop_event
        send_file_thread.start()

    return response

#Divide the file in two and download the two parts and send
def send_file(file_name, stop_event, file_size, port, part_one, client_socket, username):
    sock = RudpClientSocket()
    time.sleep(1)
    sock.connect(SERVER_ADDRESS, port)

    content = b''
    with open(os.path.join(FILE_DIRECTORY, file_name), "rb") as file_input:
        print(f"Sending {file_name}, part {1 if part_one else 2}")
        content = file_input.read()
        half_content = content[:file_size // 2] if part_one else content[file_size // 2:]
        sock.send_stream(half_content, stop_event)

    if not part_one:
        print("Sending last byte message")
        last_byte = str(content[-1])
        client_socket.send(f"User <{username}> downloaded 100% out of file. Last byte is: {last_byte}.".encode())

#The purpose of the function is to handle,
# the messages that the client requests from the server
def handle_message(message, client_socket):
    response = ""
    is_client_connected = True
    dest_sockets = []
    if message.startswith(CONNECT_MESSAGE) and message[len(CONNECT_MESSAGE)] == "<" and message[-1] == ">":
        client_name = message[len(CONNECT_MESSAGE) + 1: -1]
        print(f"client {client_name} connecting")
        with users_lock:
            if client_name in users:
                response = "<user_name_exists>"
            else:
                users[client_name] = client_socket
                user_name.val = client_name
                response = "<connected>"
                mes = f"client {client_name} connected"
                if len(users) > 1:
                    for key, value in users.items():
                        if key != client_name:
                            value.send(mes.encode())
    elif message == DISCONNECT_MESSAGE:
        print(f"client {user_name.val} disconnecting")
        with users_lock:
            users.pop(user_name.val)
        response = "<disconnected>"
        mes = f"client {user_name.val} disconnect"
        for key, value in users.items():
                if key != user_name.val:
                    value.send(mes.encode())
        is_client_connected = False
    elif message == GET_USERS_MESSAGE:
        response = "<users_lst>"
        response = response + "<" + str(len(users)) + ">"
        for user in users:
            response += f"<{user}>"
        response += "<end>"
    elif message.startswith(SEND_MESSAGE_DIRECT):
        name_end = message.find(">", len(SEND_MESSAGE_DIRECT) + 1)
        dest_name = message[len(SEND_MESSAGE_DIRECT) + 1: name_end]
        if dest_name in users:
            dest_sockets.append(users[dest_name])
            send_name=""
            for key, value in users.items():
                if client_socket == value:
                    send_name = key
            direct_message = send_name + ">" + message[name_end+1:len(message)]

            response = f"<msg_lst><1><{direct_message}><end>"
        else:
            response = f"Couldn't find user {dest_name}"
            dest_sockets.append(client_socket)
    elif message.startswith(SEND_MESSAGE_ALL):
        send_name = ""
        for key, value in users.items():
            if client_socket == value:
                send_name = key
        broadcast_message = message[message.find(">", 1) + 1:len(message)]
        broadcast_message = send_name + ">" + broadcast_message
        print(broadcast_message)
        response = f"<msg_lst><1><{broadcast_message}><end>"
        list_user = []
        for key, value in users.items():
            if key != user_name:
                list_user.append(value)
        dest_sockets = list_user
    elif message == GET_FILE_LIST:
        file_list = []
        if os.path.isdir(FILE_DIRECTORY):
            file_list = os.listdir(FILE_DIRECTORY)
        response = "<file_lst>"
        for f in file_list:
            response += f"<{f}>"
        response += "<end>"
    elif message.startswith(DOWNLOAD_MESSAGE):
        file_name = message[len(DOWNLOAD_MESSAGE) + 1: -1]
        response = download_half_file(file_name, True, client_socket)
    elif message.startswith(CONTINUE_MESSAGE):
        file_name = message[len(DOWNLOAD_MESSAGE) + 1: -1]
        response = download_half_file(file_name, False, client_socket)
    elif message.startswith(STOP_DOWNLOAD):
        job_id = int(message[len(STOP_DOWNLOAD) + 1: -1])
        print(f"Stopping {job_id}")
        send_file_stop_events[job_id].set()
        with send_file_stop_events_lock:
            send_file_stop_events.pop(job_id)
    else:
        response = message.upper()

    return response, is_client_connected, dest_sockets

#The function gets socket and address and handles each client
def handle_client(client_socket, client_address):
    is_client_connected = True
    try:
     while is_client_connected:
        message = client_socket.recv(MAXIMAL_MESSAGE_SIZE).decode().strip()
        print(f"Got message from {client_address}: {message}")
        try:
            response, is_client_connected, dest_sockets = handle_message(message, client_socket)
            print(f"Sending response {response}")
            if dest_sockets:
                if response.startswith("<msg_lst>"):
                    for sock in dest_sockets:
                        if sock != client_socket:
                         sock.send(response.encode())
                else:
                 for sock in dest_sockets:
                    sock.send(response.encode())
            else:
                client_socket.send(response.encode())
        except Exception:
            traceback.print_exc()
            response = "Couldn't understand your message"
            client_socket.send(response.encode())

    except:
       is_client_connected = False
       users.pop(user_name.val)
       response = "<disconnected>"
       client_socket.send(response.encode())

#The function opens a connection and starts listening to customers
def serve():
    print("Creating server socket")
    server_socket = socket(AF_INET, SOCK_STREAM)
    print("Binding socket")
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind((SERVER_ADDRESS, SERVER_PORT))
    print("Listening on socket")
    server_socket.listen(CLIENT_BACKLOG)
    return server_socket

#The main function that runs the Server
def main():
    server_socket = None
    try:
        server_socket = serve()

        while True:
            print("Accepting connection from client")
            client_socket, client_address = server_socket.accept()
            print(f"Got connection from {client_address}, Starting new thread")
            threading.Thread(target=handle_client, args=(client_socket, client_address)).start()
    finally:
        if server_socket:
            server_socket.close()


if __name__ == '__main__':
    main()
