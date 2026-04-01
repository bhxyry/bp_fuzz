import configparser
import argparse
import os
import pathlib
import logging as log
import pygdbmi
import time
import random
from qemu import QEMU
from GDB import GDB
from uart import UART
import queue
from binaryanalyzer import BinaryAnalyzer


class Fuzzer:

    def __init__(self, config: configparser):
        self.binaryanalyzer = BinaryAnalyzer(
            config["SUT"]["file_path"], config["SUT"]["entry_function"]
        )
        self.stop_queue = queue.Queue()
        self.qemu = QEMU(config["SUT"]["file_path"], config["SUT"]["machine"])
        self.gdb = GDB(self.stop_queue)
        self.uart = UART(self.stop_queue)
        self.max_breakpoints = int(config["SUT"]["max_breakpoints"])
        self.until_rotate_breakpoints = int(config["SUT"]["until_rotate_breakpoints"])

        self.before_fuzz(config)

        self.start_fuzz(config)

        # self.after_fuzz(config)

    def before_fuzz(self, config: configparser):
        # before fuzzing
        self.binaryanalyzer.generate_cfg(config["output"]["output_directory"])

    def start_fuzz(self, config: configparser):
        # start fuzzing
        self.qemu.start()

        self.gdb.connect()

        self.uart.connect()

        time.sleep(1)
        self.gdb.continue_run()
        # self.gdb.interrupt()
        # time.sleep(1)

        stop_time = config["Fuzzer"].getint("total_time") + int(time.time())
        inputs_until_breakpoints_rotating = 0
        try:
            while int(time.time()) < stop_time:
                response = self.gdb.wait_for_stop()

                if response["reason"] == "input request":

                    if inputs_until_breakpoints_rotating == 0:
                        self.gdb.interrupt()
                        self.set_breakpoints()
                        self.gdb.continue_run()

                    inputs_until_breakpoints_rotating = (
                        inputs_until_breakpoints_rotating + 1
                    ) % self.max_breakpoints

                    data = "deadbeef\n"
                    self.uart.send_input(data)
                elif response["reason"] == "breakpoint-hit":
                    hit_addr = response["payload"]["frame"]["addr"]
                    log.info(f"Breakpoint hit at {hit_addr}")
                    self.gdb.continue_run()
        finally:
            self.qemu.stop()
            self.gdb.disconnect()
            self.uart.disconnect()

    def set_breakpoints(self):
        if self.max_breakpoints <= 0:
            return

        addrs = self.binaryanalyzer.random_breakpoint(self.max_breakpoints)
        for addr in addrs:
            self.gdb.set_breakpoint(f"0x{addr:x}")

        log.info(f"Redistribute all {self.max_breakpoints} breakpoints")
