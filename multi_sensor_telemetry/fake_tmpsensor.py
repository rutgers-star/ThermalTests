import threading
import time
import random

class FakeTMPSensor:
    """
    Fake temperature sensor for offline testing & PoC.
    Simulates temperature readings around a baseline (default: 70°F)
    with small random fluctuations each read.
    """
    def __init__(self, addr=0x00, reg=0x00, interval=0.5, baseline=70.0):
        self.addr = addr
        self.reg = reg
        self.interval = interval
        self.baseline = baseline

        self._buffer = []
        self._latest = None
        self._running = False
        self._thread = None

    def read_once(self):
        """
        Simulate a single sensor reading.
        Fluctuates randomly around baseline by ±1°F.
        """
        fake_temp = self.baseline + random.uniform(-1.0, 1.0)
        return round(fake_temp, 3)

    def _loop(self):
        """
        Background thread loop that continuously reads values.
        """
        while self._running:
            value = self.read_once()
            self._latest = value
            self._buffer.append(value)
            print(f"[FakeTMP] {value}")
            time.sleep(self.interval)

    def start(self):
        """
        Start continuous background reading.
        """
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        """
        Stop background reading.
        """
        self._running = False
        if self._thread:
            self._thread.join()

    def get_buffer(self):
        """
        Return a safe snapshot of the internal buffer.
        """
        return list(self._buffer)

    def get_latest(self):
        """
        Return the most recent reading.
        """
        return self._latest
