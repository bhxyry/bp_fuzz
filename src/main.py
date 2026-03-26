import configparser
import argparse
import os
import pathlib
import logging as log
from fuzzer import Fuzzer


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


def main():
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

    fuzzer = Fuzzer(config)


if __name__ == "__main__":
    main()
