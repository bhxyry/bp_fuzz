from pygdbmi.gdbcontroller import GdbController
import logging as log
import queue
import threading
import os


class GDB:

    def __init__(self, stop_queue: queue.Queue):
        self.gdb = GdbController(["gdb", "--nx", "--quiet", "--interpreter=mi3"])
        self.stop_queue = stop_queue
        self.running = True

        self.t = threading.Thread(target=self._listener_loop, daemon=True)
        self.t.start()

    def _listener_loop(self):
        while self.running:
            try:
                responses = self.gdb.get_gdb_response(timeout_sec=0.1)

            except Exception as e:
                # log.error(f"GDB read error: {e}")
                continue

            for r in responses:
                # log.info(f"{r}")
                self._handle_response(r)

    def _handle_response(self, r):
        rtype = r.get("type")

        if rtype == "notify":
            self._handle_notify(r)

        elif rtype in ("console", "log", "output"):
            pass
            # log.info(f"[GDB]{r.get("payload")}")

    def _handle_notify(self, r):
        message = r.get("message")
        payload = r.get("payload", {})

        if message == "stopped":
            reason = payload.get("reason")

            event = {"reason": reason, "payload": payload}

            self.stop_queue.put(event)

    def wait_for_stop(self):
        try:
            msg = self.stop_queue.get(timeout=5)
        except queue.Empty:
            log.error("stop queue is empty!")
        return msg

    def connect(self):
        self.gdb.write("-gdb-set mi-async on", read_response=False)
        self.gdb.write(
            "-file-exec-and-symbols example/fuzz-deadbeef.elf", read_response=False
        )

        self.gdb.write("-target-select remote localhost:1234", read_response=False)
        log.info("gdb connected!")

    def continue_run(self):
        log.info("continue exec!")
        self.gdb.write("-exec-continue", read_response=False)

    def disconnect(self):
        log.info("GDB Exit")
        try:
            self.gdb.write("-gdb-exit", read_response=False)
        except:
            pass

    def set_breakpoint(self, addr: str):
        log.info(f"set breakpoint at {addr}")
        self.gdb.write(f"-break-insert *{addr}", read_response=False)

    def interrupt(self):
        self.gdb.write("-exec-interrupt", read_response=False)
        log.info("gdb interrupt!")
