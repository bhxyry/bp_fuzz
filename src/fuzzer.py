from qemu import QEMU
from GDB import GDB
from uart import UART


def fuzz_loop():

    qemu = QEMU("example/fuzz-deadbeef.elf")
    qemu.start()

    gdb = GDB()
    gdb.connect()

    uart = UART()
    uart.connect()

    gdb.continue_run()
    try:
        while True:

            uart.wait_for_output()

            data = "deadbeef\n"
            uart.send_input(data)

            uart.wait_for_output()

    except KeyboardInterrupt:
        qemu.stop()
        gdb.disconnect()
        uart.disconnect()


if __name__ == "__main__":
    fuzz_loop()
