import socket
import time
import logging as log
import queue
import threading
import struct


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
        i = 1
        while self.state:
            try:
                buffer = b""

                while not buffer.endswith(b"\n"):
                    buffer += self.sock.recv(1)

                # log.info("receive:%s", buffer)
                if buffer == b"Input:\n":
                    event = {
                        "reason": "input request",
                        "payload": f"{i}",
                        "time": time.time(),
                    }
                    self.stop_queue.put(event)
                i += 1
            except OSError:
                break

    def send_input(self, data):
        # 1. 统一类型
        if isinstance(data, str):
            data = data.encode()

        length = len(data)
        # 小端4字节（STM32 Cortex-M3 默认小端）
        self.sock.sendall(struct.pack("<I", length))
        # 4. 发送
        self.sock.sendall(data)
        # log.info(f"[data send]: {data}")

    def disconnect(self):
        if self.sock is None:
            return
        self.state = False
        self.sock.close()
        log.info("serial disconnect!")
