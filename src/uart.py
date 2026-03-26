import socket
import time
import logging as log


class UART:
    def __init__(self):
        self.sock = None

    def connect(self):
        self.sock = socket.socket()
        self.sock.connect(("localhost", 4444))
        log.info("UART connected!")

    def wait_for_output(self):
        buffer = b""
        while not buffer.endswith(b"\n"):
            buffer += self.sock.recv(1)
        log.info("receive:%s", buffer)

    def send_input(self, data):
        if isinstance(data, str):
            data = data.encode()

        self.sock.sendall(data)
        log.info("data send!")

    def disconnect(self):
        if self.sock is None:
            return

        self.sock.close()
        log.info("serial disconnect!")
