import math
import threading
import time
from collections import deque


def positive(name, value):
    """Validate a user-supplied duration; returns it so callers can assign inline."""
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


class BackgroundSensor:
    def __init__(self, addr, interval=0.5, max_buffer=2048, max_age=None):
        self.addr = addr
        self.interval = positive("interval", interval)
        self.max_age = max(1.0, 3 * interval) if max_age is None else positive("max_age", max_age)
        self._buffer = deque(maxlen=max_buffer)
        self._latest = None
        self._timestamp = None
        self._monotonic = None
        self._error = None
        self._thread = None
        self._stop_event = threading.Event()
        self._stop_event.set()
        self._data_lock = threading.Lock()
        self._lifecycle_lock = threading.RLock()

    def read_once(self):
        raise NotImplementedError

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                value = self.read_once()
                with self._data_lock:
                    self._latest = value
                    self._timestamp = time.time()
                    self._monotonic = time.monotonic()
                    self._error = None
                    self._buffer.append(value)
            except Exception as exc:
                with self._data_lock:
                    self._error = str(exc) or type(exc).__name__
            self._stop_event.wait(self.interval)

    def start(self):
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                if self._stop_event.is_set():
                    raise RuntimeError("Previous sensor worker is still stopping")
                return
            with self._data_lock:
                self._latest = self._timestamp = self._monotonic = self._error = None
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name=f"sensor-{hex(self.addr)}"
            )
            self._thread.start()

    def request_stop(self):
        self._stop_event.set()

    def stop(self, timeout=2.0):
        with self._lifecycle_lock:
            self.request_stop()
            if self._thread is not None:
                self._thread.join(timeout=timeout)
                if self._thread.is_alive():
                    raise TimeoutError(f"Sensor {hex(self.addr)} read has not stopped")
                self._thread = None

    def get_buffer(self):
        with self._data_lock:
            return list(self._buffer)

    def get_status(self):
        """Atomic status; timestamp is Unix seconds of the last successful read."""
        with self._data_lock:
            age = None if self._monotonic is None else time.monotonic() - self._monotonic
            valid = (not self._stop_event.is_set() and self._error is None
                     and age is not None and age <= self.max_age)
            return {"temperature": self._latest if valid else None,
                    "timestamp": self._timestamp, "age": age,
                    "valid": valid, "error": self._error}

    def get_latest(self):
        """Return None before sampling, after failure/stop, or once data is stale."""
        return self.get_status()["temperature"]
