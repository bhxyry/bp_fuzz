import socket
import time


class UART:
    def __init__(self):
        self.sock = None

    def connect(self):
        self.sock = socket.socket()
        self.sock.connect(("localhost", 4444))
        print("UART connected!")

    def wait_for_output(self):
        data = self.sock.recv(1024)
        print("receive:", data)

    def send_input(self, data):
        if isinstance(data, str):
            data = bytes.fromhex(data)

        self.sock.send(data)
