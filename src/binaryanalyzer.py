import angr
import logging as log


class BinaryAnalyzer:
    def __init__(self, file_path, entry_function):

        self.project = angr.Project(file_path, auto_load_libs=False)
        self.entry_function = entry_function

        self.cfg = None
        self.basic_block_addr = []
        self.entry_addr = None

    def generate_cfg(self):
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
            blocks.append(block.addr)
        self.basic_block_addr = sorted(set(blocks))
        log.info("binary analyzer complete!")
