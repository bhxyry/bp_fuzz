from pygdbmi.gdbcontroller import GdbController
import logging as log
import queue


class GDB:

    def __init__(self):
        self.gdb = GdbController(["gdb", "--nx", "--quiet", "--interpreter=mi3"])

    def connect(self):
        self.gdb.write("-file-exec-and-symbols example/fuzz-deadbeef.elf")

        self.gdb.write("-target-select remote localhost:1234")
        log.info("gdb connected!")

        self.gdb.write("-gdb-set target-async on")

    def set_breakpoint(self):
        pass

    def continue_run(self):
        log.info("continue exec!")
        self.gdb.write("-exec-continue")

    def disconnect(self):
        log.info("GDB Exit")
        try:
            self.gdb.write("-gdb-exit")
        except:
            pass

    def wait_for_stop(self, timeout):
        try:
            msg = self.gdb.get_gdb_response(timeout_sec=timeout)
        except queue.Empty:
            msg = ("timed out", None)
        return msg
