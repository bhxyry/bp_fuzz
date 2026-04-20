from pygdbmi.gdbcontroller import GdbController
import logging as log
import queue
import threading
import time


class GDB:

    def __init__(self, stop_queue: queue.Queue):
        self.gdb = GdbController(["gdb", "--nx", "--quiet", "--interpreter=mi3"])
        self.stop_queue = stop_queue

        # 同步响应对列消息
        self._result_queue: queue.Queue[dict] = queue.Queue()
        self.interrupt_queue = queue.Queue()
        self.running = True

        # 写锁，防止监听线程和主线程同时操作 gdbmi IO
        self._write_lock = threading.Lock()
        self._token = 0
        self._token_lock = threading.Lock()

        self.breakpoints: dict[int, str] = {}

        self.t = threading.Thread(target=self._listener_loop, daemon=True)
        self.t.start()

    def _next_token(self):
        with self._token_lock:
            self._token += 1
            return self._token

    def _send(self, cmd: str, timeout: int = 5) -> dict:
        token = self._next_token()
        full_cmd = f"{token}{cmd}"
        with self._write_lock:
            self.gdb.write(full_cmd, read_response=False, timeout_sec=0)

        end = time.time() + timeout

        while time.time() < end:
            try:
                r = self._result_queue.get(timeout=0.05)
                if r.get("token") == token:
                    if r.get("message") == "error":
                        # log.info(f"{r}")
                        raise RuntimeError(f"GDB error: {r['payload']['msg']}")
                    return r
                else:
                    self._result_queue.put(r)

            except queue.Empty:
                continue

        raise TimeoutError(f"No response for: {full_cmd}")

    def _listener_loop(self):
        while self.running:
            try:
                responses = self.gdb.get_gdb_response(
                    timeout_sec=0.1, raise_error_on_timeout=False
                )

            except Exception as e:
                # log.error(f"GDB read error: {e}")
                continue

            for r in responses:
                # log.info(f"GDB response: {r}")
                self._dispatch(r)

    def _dispatch(self, r):
        rtype = r.get("type")

        if rtype == "notify":
            self._handle_notify(r)

        elif rtype == "result":
            self._result_queue.put(r)

        elif rtype in ("console", "log", "output"):
            pass
            # log.info(f"[GDB]{r.get("payload")}")

    def _handle_notify(self, r):
        message = r.get("message")
        payload = r.get("payload") or {}

        if message == "stopped":
            reason = payload.get("reason", "unknown")

            event = {"reason": reason, "payload": payload, "time": time.time()}
            if reason == "signal-received":
                self.interrupt_queue.put(event)

            elif reason == "breakpoint-hit":
                # log.info(f"{event}")
                self.stop_queue.put(event)

    def wait_for_interrupt(self, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            try:
                # log.info(self.stop_queue.qsize())
                msg = self.interrupt_queue.get()
                # log.info(self.stop_queue.qsize())
                return
            except queue.Empty:
                continue

    def wait_for_stop(self):
        try:

            msg = self.stop_queue.get(timeout=5)
            return msg
        except queue.Empty:
            log.error("stop queue is empty!")
            return None

    def connect(self, elf_path: str, gdb_server: str = "localhost:1234"):
        self._send("-gdb-set mi-async on")
        self._send(f"-file-exec-and-symbols {elf_path}")
        self._send(f"-target-select remote {gdb_server}")
        log.info("gdb connected!")

    def continue_run(self):
        self._send("-exec-continue --all")
        # log.info("continue exec!")

    def disconnect(self):
        try:
            self._send("-gdb-exit", timeout=3)
        except:
            pass
        self.running = False
        log.info("GDB Exit")

    def set_breakpoint(self, addr: str):

        r = self._send(f"-break-insert *{addr}")
        bp_id: str = r["payload"]["bkpt"]["number"]

        self.breakpoints[int(addr, 16)] = bp_id

        # log.info(f"set breakpoint {bp_id} at {addr}")

    def interrupt(self):
        # interrupt 不等响应，它本身会触发 stopped notify
        with self._write_lock:
            self.gdb.write("-exec-interrupt", read_response=False)

        self.wait_for_interrupt()

        # log.info("gdb interrupt!")

    def remove_breakpoint(self) -> None:
        # breadkpoint id is returned by gdb if we set_breakpoint
        for addr, bp_id in list(self.breakpoints.items()):
            self._send(f"-break-delete {bp_id}")
            self.breakpoints.pop(addr, None)
            # log.info(f"Breakpoint {bp_id} removed.")

    def remove_breakpoint_id(self, addr: int):
        bp_id = self.breakpoints.get(addr)

        if bp_id is None:
            log.warning(f"No breakpoint at {addr}")
            return

        self._send(f"-break-delete {bp_id}")
        self.breakpoints.pop(addr)

        # log.info(f"Breakpoint {bp_id} at {addr} removed.")
