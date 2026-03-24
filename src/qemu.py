import subprocess
import time


class QEMU:
    def __init__(self, elf):
        self.elf = elf
        self.process = None

    def start(self):
        if self.process is not None:
            print("qemu already running")

        self.process = subprocess.Popen(
            [
                "qemu-system-arm",
                "-M",
                "stm32vldiscovery",
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
        print("qemu started")

        time.sleep(1)

    def stop(self):
        if self.process is None:
            return

        print("qemu stopped")
        self.process.terminate()

        try:
            self.process.wait(timeout=3)
        except TimeoutError:
            self.process.kill()

        self.process = None
