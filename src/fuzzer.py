import configparser
import argparse
import os
import pathlib
import logging as log
import time
from qemu import QEMU
from GDB import GDB
from uart import UART
from binaryanalyzer import BinaryAnalyzer


def uniquify(path):
    counter = 0

    new_path = path

    while True:
        new_path = path + "-" + str(counter)
        counter += 1
        if not os.path.exists(new_path):
            return new_path

    return path


def create_output_directory(output_directory_base: str) -> str:
    output_directory = uniquify(output_directory_base + "/trial")
    pathlib.Path(output_directory).mkdir(parents=True, exist_ok=True)
    return output_directory


def setup_log(output_directory: str, loglevel: str):
    logger = log.getLogger()
    formatter = log.Formatter(
        "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s "
        "%(funcName)s()] %(message)s"
    )

    file_logger = log.FileHandler(os.path.join(output_directory, "out.log"))
    file_logger.setLevel(loglevel)
    file_logger.setFormatter(formatter)
    logger.addHandler(file_logger)

    stdout_logger = log.StreamHandler()
    stdout_logger.setLevel(loglevel)
    stdout_logger.setFormatter(formatter)
    logger.addHandler(stdout_logger)

    log.root.setLevel(loglevel)


def before_fuzzing(config: configparser):
    # before fuzzing
    binaryanalyzer = BinaryAnalyzer(
        config["SUT"]["file_path"], config["SUT"]["entry_function"]
    )
    binaryanalyzer.generate_cfg()


def start_fuzzing(config: configparser):
    # start fuzzing
    qemu = QEMU(config["SUT"]["file_path"], config["SUT"]["machine"])
    qemu.start()
    gdb = GDB()
    gdb.connect()

    uart = UART()
    uart.connect()

    single_run_timeout = config["Fuzzer"].getint("single_run_timeout")
    stop_time = config["Fuzzer"].getint("stop_time") + int(time.time())

    stop_reason, stop_info = None, None
    while int(time.time()) < stop_time:
        if stop_reason is None:
            gdb.continue_run()

        stop_reason, stop_info = gdb.wait_for_stop(single_run_timeout)

    try:
        while True:

            uart.wait_for_output()

            data = "deadbeef\n"
            uart.send_input(data)

            uart.wait_for_output()

    except KeyboardInterrupt:
        qemu.stop()
        gdb.disconnect()
        uart.disconnect()


def fuzz_loop():
    paser = argparse.ArgumentParser()
    paser.add_argument(
        "--config", required=True, type=str, help="Path to a config file."
    )
    args = paser.parse_args()

    if not os.path.isfile(args.config):
        raise Exception(f"Config file at {args.config} does not exist")

    config = configparser.ConfigParser()
    config.read(args.config)

    output_directory = create_output_directory(config["output"]["output_directory"])
    config["output"]["output_directory"] = output_directory

    setup_log(config["output"]["output_directory"], config["log"]["log_level"])

    before_fuzzing(config)

    start_fuzzing(config)

    # after fuzzing


if __name__ == "__main__":
    fuzz_loop()
