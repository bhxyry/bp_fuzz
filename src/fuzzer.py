import configparser
import logging as log
import time
from qemu import QEMU
from GDB import GDB
from uart import UART
import queue
from binaryanalyzer import BinaryAnalyzer
from InputGeneration import InputGeneration
from pc_sampling import PCSampling
import os
import matplotlib.pyplot as plt


class Fuzzer:

    def __init__(self, config: configparser):
        self.binaryanalyzer = BinaryAnalyzer(
            config["output"]["output_directory"], config["SUT"]["cfg_file_path"]
        )
        self.stop_queue = queue.Queue()

        pc_enabled = config.has_section("PC_sampling") and config["PC_sampling"].getboolean("enabled", fallback=False)
        if pc_enabled:
            pc_config = config["PC_sampling"]
            sample_interval = pc_config.getint("sample_interval", fallback=10000)
            sample_file = os.path.join(
                config["output"]["output_directory"],
                pc_config.get("output_file", fallback="pc_samples.bin"),
            )
            plugin_path = pc_config.get(
                "plugin_path",
                fallback="dependencies/pc_sampling/pc_sampling.so",
            )
            self.qemu = QEMU(
                config["SUT"]["file_path"],
                config["SUT"]["machine"],
                plugin_path=plugin_path,
                plugin_args={
                    "sample_interval": str(sample_interval),
                    "out_file": sample_file,
                },
            )
            self.pc_sampling = PCSampling(sample_file, self.binaryanalyzer)
        else:
            self.qemu = QEMU(config["SUT"]["file_path"], config["SUT"]["machine"])
            self.pc_sampling = None

        self.gdb = GDB(self.stop_queue)
        self.uart = UART(self.stop_queue)

        self.max_input_length = int(config["SUT"]["max_input_length"])

        self.max_breakpoints = int(config["Fuzzer"]["max_breakpoints"])
        self.until_rotate_breakpoints = int(
            config["Fuzzer"]["until_rotate_breakpoints"]
        )
        seeds_directory = config["Fuzzer"]["seed_directory"]
        if seeds_directory == "":
            seeds_directory = None
        self.input_generate = InputGeneration(
            config["output"]["output_directory"],
            seeds_directory,
            self.max_input_length,
        )

        self.data = []
        self.blocks_cover = []
        self.coverage_curve = []

        self.before_fuzz(config)

        self.start_fuzz(config)

        # self.after_fuzz(config)

    def before_fuzz(self, config: configparser):
        # before fuzzing
        self.binaryanalyzer.build_dominator_tree()

    def start_fuzz(self, config: configparser):
        # start fuzzing
        self.qemu.start()
        if self.pc_sampling:
            self.pc_sampling.start()

        self.gdb.connect(config["SUT"]["file_path"])

        self.uart.connect()

        # time.sleep(1)
        self.gdb.continue_run()
        # self.gdb.interrupt()
        # time.sleep(100)

        stop_time = config["Fuzzer"].getint("total_time") + int(time.time())
        inputs_until_breakpoints_rotating = 0
        start_time = int(time.time())
        try:
            while int(time.time()) < stop_time:
                # log.info(self.stop_queue.qsize())
                response = self.gdb.wait_for_stop()
                # log.info(response)
                if response["reason"] == "input request":

                    if inputs_until_breakpoints_rotating == 0:

                        self.input_generate.choose_new_baseline_input()
                        self.set_breakpoints()

                    inputs_until_breakpoints_rotating = (
                        inputs_until_breakpoints_rotating + 1
                    ) % self.until_rotate_breakpoints

                    data = self.input_generate.generate_input()

                    # self.data.append(data)
                    # data = b"hhfisdacasdasadscdsadcasdcsdadcasScdsasdcdsacacacasc\n"
                    self.blocks_cover.append(
                        len(self.binaryanalyzer.covered_basic_block)
                    )
                    # 2. 限制长度（bytes）
                    if len(data) > self.max_input_length:
                        data = data[: self.max_input_length]
                    self.uart.send_input(data)

                elif response["reason"] == "breakpoint-hit":
                    hit_addr = response["payload"]["frame"]["addr"]
                    addr = int(hit_addr, 16)

                    self.gdb.remove_breakpoint_id(addr)

                    self.input_generate.report_address_reach(
                        data,
                        addr,
                        int(time.time()) - start_time,
                    )
                    log.info(f"Breakpoint hit at {hit_addr}")
                    self.binaryanalyzer.update_covered_info(addr)

                    current_time = int(time.time()) - start_time
                    current_blocks = len(self.binaryanalyzer.covered_basic_block)
                    self.coverage_curve.append((current_time, current_blocks))

                    self.gdb.continue_run()

            log.info("time end")

        except KeyboardInterrupt:
            pass
        finally:
            output_path = config["output"]["output_directory"]

            self.uart.disconnect()
            self.qemu.stop()
            self.gdb.disconnect()

            if self.pc_sampling:
                self.pc_sampling.stop()
                log.info(
                    f"PC sampling: {self.pc_sampling.sample_count} samples, "
                    f"{self.pc_sampling.covered_via_sampling} new BBs discovered"
                )

            self.binaryanalyzer.display_cover_info(output_path)
            self.plot_coverage_curve_input(output_path)
            self.plot_coverage_curve_time(output_path)

    def set_breakpoints(self):
        # log.info(self.gdb.stop_queue.qsize())
        self.gdb.interrupt()
        # log.info(self.gdb.stop_queue.qsize())
        if self.gdb.stop_queue.qsize() > 0:
            for i in range(self.gdb.stop_queue.qsize()):
                log.info(self.gdb.stop_queue.get())
        if self.max_breakpoints <= 0:
            return
        self.gdb.remove_breakpoint()
        addrs = self.binaryanalyzer.random_breakpoint(self.max_breakpoints)
        for addr in addrs:
            self.gdb.set_breakpoint(f"0x{addr:x}")
            # log.info(self.gdb.stop_queue.qsize())

        if len(addrs) == 0:
            raise KeyboardInterrupt

        log.info(f"Redistribute all {len(addrs)} breakpoints")

        self.gdb.continue_run()

    def plot_coverage_curve_time(self, path):
        times = [t for t, _ in self.coverage_curve]
        blocks = [b for _, b in self.coverage_curve]

        plt.figure()
        plt.step(times, blocks, where="post")

        plt.xlabel("Time (s)")
        plt.ylabel("Covered Basic Blocks")
        plt.title("Coverage vs Time")

        # plt.grid(True)
        plt.savefig(
            os.path.join(
                path,
                "coverage-time.png",
            ),
            dpi=300,
        )
        plt.close()

    def plot_coverage_curve_input(self, path):
        y = self.blocks_cover
        x = list(range(1, len(self.blocks_cover) + 1))
        plt.figure()
        plt.plot(x, y)

        plt.xlabel("Number of Inputs")
        plt.ylabel("Total Covered Basic Blocks")
        plt.title("Coverage Growth Curve")

        # plt.ylim(top=len(self.binaryanalyzer.basic_block_addr)+3)
        plt.savefig(
            os.path.join(
                path,
                "coverage-input.png",
            ),
            dpi=300,
        )
        plt.close()
