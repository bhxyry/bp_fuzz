import socket
import time
import logging as log
import queue
import threading


class UART:
    def __init__(self, stop_queue: queue.Queue):
        self.sock = None
        self.stop_queue = stop_queue
        self.state = True

        self.t = threading.Thread(target=self.wait_for_output, daemon=True)

    def connect(self):
        self.sock = socket.socket()
        self.sock.connect(("localhost", 4444))
        log.info("UART connected!")

        self.t.start()

    def wait_for_output(self):
        while self.state:
            try:
                buffer = b""

                while not buffer.endswith(b"\n"):
                    buffer += self.sock.recv(1)

                log.info("receive:%s", buffer)

                if buffer == b"Input:\n":
                    event = {"reason": "input request", "payload": None}
                    self.stop_queue.put(event)
            except OSError:
                break

    def send_input(self, data):
        if isinstance(data, str):
            data = data.encode()

        self.sock.sendall(data)
        log.info(f"[data send]:{data}")

    def disconnect(self):
        if self.sock is None:
            return
        self.state = False
        self.sock.close()
        log.info("serial disconnect!")
