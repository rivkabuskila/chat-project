import random
from socket import *
from zlib import crc32

from common import ACK, CHUNK_SIZE, PACKET_LOSING_PROBABILITY
import math
# Class of fast relibal udp
# In this department we implemented according to protocol back n
# We additionally used crc to verify the correctness of the packets
# A detailed explanation appears in the pdf
SERVER_ADDRESS = "127.0.0.1"

class RudpServerSocket:
    def __init__(self):
        self._sock = socket(AF_INET, SOCK_DGRAM)
        self._sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._sock.settimeout(5)

        self._last_consecutive_packet_index = -1

    def bind(self, addr, port):
        self._sock.bind((addr, port))

    def recv(self, bufsize):
        """
        Expect To get a buffer of length bufsize, or timeout.
        """
        # print(f"Expecting {math.ceil(bufsize / CHUNK_SIZE)} packets")
        packets = [b""] * math.ceil(bufsize / CHUNK_SIZE)
        received_bytes = 0

        while received_bytes < bufsize:
            full_message, addr = self._sock.recvfrom(bufsize)
            crc = int.from_bytes(full_message[:4], "little")
            index = int.from_bytes(full_message[4:8], "little", signed=True)

            if random.random() < PACKET_LOSING_PROBABILITY:
                # Lose packet
                # print(f"Losing packet at index {index}")
                continue

            if index == self._last_consecutive_packet_index + 1:
                self._last_consecutive_packet_index += 1

            message = full_message[8:]
            # print(f"Got index: {index}, message: {message}")

            if crc32(message) == crc:
                # print(f"Acking {self._last_consecutive_packet_index}")

                if index < len(packets) and packets[index] == b"":
                    packets[index] = message
                    received_bytes += len(message)
                    # print(f"received_bytes={received_bytes}, packets={packets}")

                ack_message = ACK + self._last_consecutive_packet_index.to_bytes(4, "little", signed=True)
                self._sock.sendto(ack_message, addr)

        print(f"Final content = {b''.join(packets)}")
        return b"".join(packets)


def main():
    sock = RudpServerSocket()
    sock.bind(SERVER_ADDRESS, 8888)
    content = sock.recv(53)


if __name__ == '__main__':
    main()
