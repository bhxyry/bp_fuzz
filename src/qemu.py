import subprocess
import time
import logging as log
import signal
import socket


class QEMU:
    def __init__(self, elf, machine, plugin_path=None, plugin_args=None, pipe_write_fd=None):
        self.elf = elf
        self.process = None
        self.machine = machine
        self.plugin_path = plugin_path
        self.plugin_args = plugin_args or {}
        self.pipe_write_fd = pipe_write_fd

    def start(self):
        if self.process is not None:
            log.info("qemu already running")

        cmd = [
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
        ]
        popen_kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if self.plugin_path:
            plugin_str = self.plugin_path
            for k, v in self.plugin_args.items():
                plugin_str += f",{k}={v}"
            if self.pipe_write_fd is not None:
                plugin_str += f",pipe_fd={self.pipe_write_fd}"
                popen_kwargs["pass_fds"] = [self.pipe_write_fd]
            cmd.extend(["-plugin", plugin_str])

        self.process = subprocess.Popen(cmd, **popen_kwargs)
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
