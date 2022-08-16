import sys
import threading
import traceback
from socket import socket ,AF_INET, SOCK_STREAM
import os

# from common import FILE_DOWNLOAD_PORT
from rudp_server import RudpServerSocket
#list message
message_recv = []

SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 50000
#Setting Variables
CONNECT_MESSAGE = "<connect>"
CONNECT_MESSAGE_ACK = "<connected>"
DISCONNECT_MESSAGE = "<disconnect>"
GET_USERS_MESSAGE = "<get_users>"
SEND_MESSAGE_DIRECT = "<send_message>"
SEND_MESSAGE_ALL = "<send_message_all>"
GET_FILE_LIST = "<get_file_list>"
DOWNLOAD_MESSAGE = "<download>"
STOP_MESSAGE = "<stop>"
CONTINUE_MESSAGE = "<continue>"
SIZE = "<size>"
RECEIVED_FILES_DIR = "received_files"

#List of possible responses
AVAILABLE_REQUESTS = ["continue", "help", "stop", "download", "send", "sendall", "getusers", "getfilelist", "disconnect"]

MAXIMAL_MESSAGE_SIZE = 500

connection_open = True

client_name = ""
#The function of connecting, opening a connection and sending a message to the Server.
#The function returns an ACK message.
def connect(name):
    global client_socket
    global client_name
    client_name = name
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((SERVER_ADDRESS, SERVER_PORT))
    client_socket.send((CONNECT_MESSAGE + f"<{name}>").encode())
    ack = client_socket.recv(MAXIMAL_MESSAGE_SIZE).decode()
    if ack == CONNECT_MESSAGE_ACK:
        threading.Thread(target=recv_and_print, args=(client_socket,)).start()
    return ack

#The function receives a response from the Client handles the message and sends to the Server
def process_request(request):
    global connection_open
    request_parts = request.split()
    command = request_parts[0]
    if command not in AVAILABLE_REQUESTS:
        print(f"{command} is not a valid command, press help for available commands")

    server_message = ""

    if command == "send":
        name = request_parts[1]
        message = " ".join(request_parts[2:])
        server_message = f"{SEND_MESSAGE_DIRECT}<{name}><{message}>"
    elif command == "sendall":
        message = " ".join(request_parts[1:])
        server_message = f"{SEND_MESSAGE_ALL}<{message}>"
    elif command == "getusers":
        server_message = GET_USERS_MESSAGE
    elif command == "getfilelist":
        server_message = GET_FILE_LIST
    elif command == "disconnect":
        server_message = DISCONNECT_MESSAGE
    elif command == "download":
        file_name = request_parts[1]
        server_message = f"{DOWNLOAD_MESSAGE}<{file_name}>"
    elif command == "stop":
        job_id = request_parts[1]
        server_message = f"{STOP_MESSAGE}<{job_id}>"
    elif command == "continue":
        file_name = request_parts[1]
        server_message = f"{CONTINUE_MESSAGE}<{file_name}>"
    client_socket.send(server_message.encode())
    if command == "disconnect":
           connection_open = False
           client_socket.close()


#Gets the file every time a different half
def download_file(file_name, file_size, port, part_one):
    global client_name
    sock = RudpServerSocket()
    sock.bind(SERVER_ADDRESS, port)
    print(f"Bound, waiting for {file_name} of size {file_size}")

    received_files_dir_path = os.path.join(RECEIVED_FILES_DIR, client_name)
    if not os.path.isdir(received_files_dir_path):
        os.mkdir(received_files_dir_path)

    content_length = file_size // 2 if part_one else file_size - file_size // 2
    content = sock.recv(content_length)

    print("writing file")

    download_path = f"{os.path.join(received_files_dir_path, file_name)}_part{1 if part_one else 2}"
    with open(download_path, "wb") as output:
        output.write(content)

    print("done writing file")
    if part_one:
        message_recv.append("done writing file")

#combine the two parts of the file
def combine_parts(file_name):
    global client_name
    received_files_dir_path = os.path.join(RECEIVED_FILES_DIR, client_name)
    combined_path = os.path.join(received_files_dir_path, file_name)
    part1_path = f"{combined_path}_part1"
    part2_path = f"{combined_path}_part2"

    with open(part1_path, "rb") as part1, open(part2_path, "rb") as part2, open(combined_path, "wb") as combined:
        combined.write(part1.read())
        combined.write(part2.read())

    os.remove(part1_path)
    os.remove(part2_path)

    print(f"Combined files into {combined_path}", file=sys.stderr)

#The function is waiting to receive messages from the Server,
# and if it has received a message related to the files then it handles them
def recv_and_print(sock):
    global connection_open
    while connection_open:
        try:
            server_response = sock.recv(MAXIMAL_MESSAGE_SIZE).decode()
            message_recv.append(server_response)
            print(server_response, file=sys.stderr)
            if server_response.startswith(SIZE):
                file_name_end = server_response.find(">", len(SIZE) + 1)
                file_name = server_response[len(SIZE) + 1: file_name_end]
                file_size_end = server_response.find(">", file_name_end + 1)
                file_size = int(server_response[file_name_end + 2: file_size_end])
                job_id_end = server_response.find(">", file_size_end + 1)
                job_id = int(server_response[file_size_end + 2: job_id_end])
                part = server_response[job_id_end + 2: -1]
                part_one = part == "1"
                print(f"job_id = {job_id}")
                try:
                    download_file(file_name, file_size, job_id, part_one)
                    if not part_one:
                        combine_parts(file_name)
                except Exception:
                    traceback.print_exc()
        except OSError:
            connection_open = True


