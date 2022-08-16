from socket import *
from zlib import crc32

from common import ACK, CHUNK_SIZE, TIMEOUT, WINDOW_SIZE
# Class of fast relibal udp
# In this department we implemented according to protocol back n
# We additionally used crc to verify the correctness of the packets
# A detailed explanation appears in the pdf
SERVER_ADDRESS = "127.0.0.1"

class RudpClientSocket:
    def __init__(self):
        self._sock = socket(AF_INET, SOCK_DGRAM)
        self._sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._sock.settimeout(TIMEOUT)

    def connect(self, addr, port):
        self._sock.connect((addr, port))

    def _send_packet(self, message, index):
        # print(f"Sending index: {index}, message: {message}")

        crc = crc32(message).to_bytes(4, "little")
        index_bytes = index.to_bytes(4, "little", signed=True)
        full_message = crc + index_bytes + message
        self._sock.send(full_message)

    def _wait_for_ack(self):
        message = self._sock.recv(len(ACK) + 4)
        ack, index = message[:len(ACK)], int.from_bytes(message[len(ACK):len(ACK) + 4], "little", signed=True)

        if ack == ACK:
            return index
        else:
            return None

    def send_stream(self, stream, stop_event=None):
        packets = [stream[i: i + CHUNK_SIZE] for i in range(0, len(stream), CHUNK_SIZE)]
        last_packet_sent_index = -1
        last_packet_acked_index = -1

        done_sending = False
        while not done_sending:
            if last_packet_sent_index - last_packet_acked_index < WINDOW_SIZE and last_packet_sent_index < len(packets) - 1:
                # send new packet
                last_packet_sent_index += 1
                self._send_packet(packets[last_packet_sent_index], last_packet_sent_index)
            else:
                # wait for ack
                try:
                    acked_index = self._wait_for_ack()
                    # print(f"Received ack for index {acked_index}")
                    if acked_index == last_packet_acked_index + 1:
                        last_packet_acked_index += 1
                except timeout:
                    # print(f"Got timeout, resetting to {last_packet_acked_index}")
                    last_packet_sent_index = last_packet_acked_index

                if last_packet_acked_index == len(packets) - 1:
                    done_sending = True

                if stop_event and stop_event.is_set():
                    print("Sending stopped")
                    done_sending = True


def main():
    sock = RudpClientSocket()
    sock.connect(SERVER_ADDRESS, 8888)
    content = "This type has a single value. There is a single object with this value. This object is accessed through the built-in name None. It is used to signify the absence of a value in many situations, e.g., it is returned from functions that don’t explicitly return anything. Its truth value is false.".encode()
    sock.send_stream(content[:53])


if __name__ == '__main__':
    main()
