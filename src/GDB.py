from pygdbmi.gdbcontroller import GdbController


class GDB:

    def __init__(self):
        self.gdb = GdbController(["gdb", "--nx", "--quiet", "--interpreter=mi3"])

    def connect(self):
        self.gdb.write("-file-exec-and-symbols example/fuzz-deadbeef.elf")

        self.gdb.write("-target-select remote localhost:1234")
        print("gdb connected!")

        self.gdb.write("-gdb-set target-async on")

    def set_breakpoint(self):
        pass

    def continue_run(self):
        print("continue exec!")
        self.gdb.write("-exec-continue")

    def disconnect(self):
        print("GDB Exit")
        try:
            self.gdb.write("-gdb-exit")
        except:
            pass
