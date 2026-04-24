import bisect
import logging as log
import random
import networkx as nx


class BinaryAnalyzer:
    def __init__(self, output_directory, cfg_file_path):

        self.cfg: nx.DiGraph = nx.read_adjlist(
            cfg_file_path, nodetype=hex_int, create_using=nx.DiGraph
        )
        self.cfg.remove_node(-1)

        self.basic_block_addr: set = set(self.cfg.nodes())
        self.covered_basic_block = set()

        output_path = f"{output_directory}/basic_blocks.txt"
        with open(output_path, "w") as f:
            f.write("-----basic blocks-----\n")
            for addr in sorted(self.basic_block_addr):
                f.write(f"0x{addr:x}\n")

        self.dom_tree = None

    # def generate_cfg(self, output_directory):
    #     symbol = self.project.loader.find_symbol(self.entry_function)

    #     if symbol is None:
    #         raise ValueError(f"{self.entry_function} is not found!")
    #     self.entry_addr = symbol.rebased_addr

    #     # CFGEmulated 替代已弃用的 CFGAccurate
    #     self.cfg = self.project.analyses.CFGEmulated(
    #         starts=[self.entry_addr],
    #         normalize=True,
    #         call_depth=5,  # 控制分析深度，避免无限展开
    #     )

    #     main_object = self.project.loader.main_object
    #     blocks = set()

    #     for node in self.cfg.graph.nodes():
    #         # 过滤无效地址和外部节点
    #         if node.addr is None or node.addr <= 0:
    #             continue
    #         # 只保留主二进制范围内的基本块
    #         if main_object.contains_addr(node.addr):
    #             blocks.add(node.addr)

    #     self.basic_block_addr = blocks

    #     output_path = f"{output_directory}/basic_blocks.txt"
    #     with open(output_path, "w") as f:
    #         f.write("-----basic blocks-----\n")
    #         for addr in sorted(blocks):
    #             f.write(f"0x{addr:x}\n")

    #     log.info(f"binary analyzer complete! found {len(blocks)} basic blocks.")

    def random_breakpoint(self, num):
        if self.cfg is None:
            raise Exception("cfg is not generated yet!")

        if num <= 0:
            return []
        remain = list(self.basic_block_addr - self.covered_basic_block)
        return random.sample(remain, min(num, len(remain)))

    def build_dominator_tree(self):
        # 找入口点：入度为 0 的节点
        entry_candidates = [n for n, d in self.cfg.in_degree() if d == 0]

        if len(entry_candidates) == 0:
            raise ValueError("CFG 中没有找到入口点（无入度为0的节点，可能存在环）")
        if len(entry_candidates) > 1:
            log.warning(f"发现多个入口候选: {[hex(n) for n in entry_candidates]}")

        start = entry_candidates[0]
        log.info(f"CFG 入口点: 0x{start:x}")

        idom = nx.immediate_dominators(self.cfg, start)

        self.dom_tree = nx.DiGraph()
        for node, dom in idom.items():
            if node == dom:
                continue
            self.dom_tree.add_edge(dom, node)

        log.info("Dominator Tree complete!")

    def update_covered_info(self, node):
        # ancestors = nx.ancestors(self.dom_tree, node)
        # self.covered_basic_block.update(ancestors)
        self.covered_basic_block.add(node)

    def pc_to_bb(self, pc: int) -> int | None:
        if not hasattr(self, "_sorted_bb_addrs"):
            self._sorted_bb_addrs = sorted(self.basic_block_addr)

        idx = bisect.bisect_right(self._sorted_bb_addrs, pc) - 1
        if idx < 0:
            return None
        bb_addr = self._sorted_bb_addrs[idx]
        if pc - bb_addr <= 4096:
            return bb_addr
        return None

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


class hex_int(int):
    def __new__(cls, value, *args, **kwargs):
        # value 是字符串，比如 "-0x1", "0x8000380"

        if value[-1] == "L":
            value = value[0:-1]  # 去掉长整型后缀 "L"（Python2遗留）

        negative = value.startswith("-")
        stripped = value.lstrip("-")  # "-0x1"  → "0x1"
        if stripped.startswith(("0x", "0X")):
            stripped = stripped[2:]  # "0x1"   → "1"

        result = super().__new__(cls, stripped, base=16)  # "1" → int(1)
        return -result if negative else result  # → -1
