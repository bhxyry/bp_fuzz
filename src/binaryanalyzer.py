import angr
import logging as log
import random


class BinaryAnalyzer:
    def __init__(self, file_path, entry_function):

        self.project = angr.Project(file_path, auto_load_libs=False)
        self.entry_function = entry_function

        self.cfg = None
        self.basic_block_addr = []
        self.entry_addr = None

    def generate_cfg(self, output_directory):
        symbol = self.project.loader.find_symbol(self.entry_function)

        if symbol is None:
            raise ValueError(f"{self.entry_function} is not fund!")
        self.entry_addr = symbol.rebased_addr

        self.cfg = self.project.analyses.CFGFast(
            normalize=True, function_starts=[self.entry_addr]
        )

        func = self.cfg.functions.get(self.entry_addr)
        if func is None:
            raise ValueError(f"{self.entry_function} is not fund!")
        blocks = []
        for block in func.blocks:
            blocks.append(block.addr + 1)
        self.basic_block_addr = sorted(set(blocks))
        with open(f"{output_directory}/basic_blocks.txt", "w") as f:
            for addr in self.basic_block_addr:
                f.write(f"0x{addr:x}\n")
        log.info("binary analyzer complete!")

    def random_breakpoint(self, num):
        if self.cfg is None:
            raise Exception("cfg is not generated yet!")

        if num <= 0:
            return []

        return random.sample(self.basic_block_addr, num)
