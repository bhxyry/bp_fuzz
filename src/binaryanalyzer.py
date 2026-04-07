import angr
import logging as log
import random
import networkx as nx


class BinaryAnalyzer:
    def __init__(self, file_path, entry_function):

        self.project = angr.Project(file_path, auto_load_libs=False)
        self.entry_function = entry_function

        self.cfg = None
        self.basic_block_addr = set()
        self.covered_basic_block = set()
        self.entry_addr = None

        self.dom_tree = None

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
            blocks.append(block.addr - 1)
        self.basic_block_addr = sorted(set(blocks))
        with open(f"{output_directory}/basic_blocks.txt", "w") as f:
            f.write("-----basic blocks-----\n")
            for addr in self.basic_block_addr:
                f.write(f"0x{addr:x}\n")
        log.info("binary analyzer complete!")

    def random_breakpoint(self, num):
        if self.cfg is None:
            raise Exception("cfg is not generated yet!")

        if num <= 0:
            return []

        return random.sample(self.basic_block_addr, num)

    def _build_cfg_networkx(self):
        G = nx.DiGraph()

        func = self.cfg.functions.get(self.entry_addr)
        if func is None:
            raise Exception("function no found")

        for node in func.graph.nodes():
            src = node.addr

            for succ in func.graph.successors(node):
                if succ is None:
                    continue
                dst = succ.addr
                # print(f"-----------------0x{src+1:x}-0x{dst+1:x}-----------------\n")
                G.add_edge(src - 1, dst - 1)

        return G

    def build_dominator_tree(self):
        G = self._build_cfg_networkx()

        start = self.entry_addr - 1
        # print(hex(start))
        idom = nx.immediate_dominators(G, start)

        self.dom_tree = nx.DiGraph()

        for node, dom in idom.items():
            if node == dom:
                continue
            self.dom_tree.add_edge(dom, node)
            # print(hex(node))

        log.info("Dominator Tree complete!")

    def update_covered_info(self, node):
        ancestors = nx.ancestors(self.dom_tree, node)
        self.covered_basic_block.update(ancestors)
        self.covered_basic_block.add(node)

    def display_cover_info(self, output_directory):
        with open(f"{output_directory}/basic_blocks.txt", "a") as f:
            f.write("-----covered basic blocks info-----\n")
            total = len(self.basic_block_addr)
            covered = len(self.covered_basic_block)
            f.write(f"total:{total}\n")
            f.write(f"covered:{covered}\n")

            for node in sorted(self.covered_basic_block):
                f.write(f"0x{node:x}\n")

            print("-----covered basic blocks info-----\n")
            print(f"total:{total}\n")
            print(f"covered:{covered}\n")
