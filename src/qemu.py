import subprocess
import time
import logging as log
import signal


class QEMU:
    def __init__(self, elf, machine):
        self.elf = elf
        self.process = None
        self.machine = machine

    def start(self):
        if self.process is not None:
            log.info("qemu already running")

        self.process = subprocess.Popen(
            [
                "qemu-system-arm",
                "-M",
                self.machine,
                "-kernel",
                self.elf,
                "-gdb",
                "tcp::1234",
                "-S",
                "-serial",
                "tcp::4444,server,nowait",
                "-nographic",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("qemu started")

        time.sleep(1)

    def stop(self):
        if self.process is None:
            return

        log.info("qemu exit!")
        self.process.terminate()

        try:
            self.process.wait(timeout=3)
        except TimeoutError:
            self.process.kill()

        self.process = None

    def interrupt(self):
        self.process.send_signal(signal.SIGINT)

        log.info("qemu stopped!")
