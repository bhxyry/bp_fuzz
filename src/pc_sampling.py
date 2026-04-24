import logging as log
import os
import struct
import threading
import time


class PCSampling:
    def __init__(
        self, sample_file: str, binary_analyzer, poll_interval: float = 0.5
    ):
        self.sample_file = sample_file
        self.binary_analyzer = binary_analyzer
        self.poll_interval = poll_interval
        self._running = False
        self._thread = None
        self._read_offset = 0
        self.sample_count = 0
        self.covered_via_sampling = 0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _reader_loop(self):
        while self._running and not os.path.exists(self.sample_file):
            time.sleep(0.1)

        while self._running:
            try:
                with open(self.sample_file, "rb") as f:
                    f.seek(self._read_offset)
                    data = f.read()
                    if data:
                        self._process_samples(data)
            except FileNotFoundError:
                pass
            except Exception as e:
                log.error(f"PC sampling read error: {e}")

            time.sleep(self.poll_interval)

    def _process_samples(self, data: bytes):
        chunk_size = 8  # uint64_t
        complete_len = (len(data) // chunk_size) * chunk_size

        for i in range(0, complete_len, chunk_size):
            pc = struct.unpack("<Q", data[i : i + chunk_size])[0]
            self.sample_count += 1
            bb = self.binary_analyzer.pc_to_bb(pc)
            if bb is not None:
                if bb not in self.binary_analyzer.covered_basic_block:
                    self.covered_via_sampling += 1
                    self.binary_analyzer.covered_basic_block.add(bb)

        self._read_offset += complete_len
