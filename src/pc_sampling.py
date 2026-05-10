import logging as log
import os
import struct


class PCSampling:
    def __init__(self, read_fd: int, binary_analyzer):
        self._read_fd = read_fd
        self.binary_analyzer = binary_analyzer
        self.sample_count = 0
        self._new_coverage_addr = 0

    def start(self):
        os.set_blocking(self._read_fd, False)

    def stop(self):
        if self._read_fd >= 0:
            os.close(self._read_fd)
            self._read_fd = -1

    def check_and_process(self):
        """Read all available samples from pipe, update coverage.
        Returns True if new coverage was discovered."""
        self._new_coverage_addr = 0

        while True:
            try:
                data = os.read(self._read_fd, 65536)
                if not data:
                    break
                self._process_samples(data)
            except BlockingIOError:
                break
            except OSError:
                break

        if self._new_coverage_addr != 0:
            return self._new_coverage_addr
        return 0

    def _process_samples(self, data: bytes):
        chunk_size = 8
        complete_len = (len(data) // chunk_size) * chunk_size

        for i in range(0, complete_len, chunk_size):
            pc = struct.unpack("<Q", data[i : i + chunk_size])[0]
            self.sample_count += 1
            bb = self.binary_analyzer.pc_to_bb(pc)
            if bb is not None:
                if bb not in self.binary_analyzer.covered_basic_block:
                    log.info(f"\033[36mpc sample {hex(pc)} hit {hex(bb)}\033[0m")
                    self.binary_analyzer.covered_basic_block.add(bb)
                    self._new_coverage_addr = bb
