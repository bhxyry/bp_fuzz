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

    def continue_run(self):
        log.info("continue exec!")
        return self.gdb.write("-exec-continue", read_response=True)

    def disconnect(self):
        log.info("GDB Exit")
        try:
            self.gdb.write("-gdb-exit")
        except:
            pass

    def set_breakpoint(self, addr: str):
        log.info(f"set breakpoint at {addr}")
        self.gdb.write(f"-break-insert *{addr}")

    def interrupt(self):
        log.info("execute interrupt")
        self.gdb.write("-exec-interrupt")
