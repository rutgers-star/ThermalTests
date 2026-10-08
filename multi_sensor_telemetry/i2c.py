import threading


def import_smbus():
    try:
        import smbus2
        return smbus2
    except ImportError as e:
        raise ImportError(
            "Real sensors require Linux and smbus2. Install with "
            "python -m pip install -r multi_sensor_telemetry/requirements.txt "
            "from the repository root. "
            "Use --fake for laptop/venv testing."
        ) from e


class LockedSMBus:
    """Serialize SMBus access so multiple sensor threads can share one bus."""

    def __init__(self, bus, lock=None):
        self._bus = bus
        self._lock = lock or threading.Lock()

    def read_i2c_block_data(self, addr, reg, n):
        with self._lock:
            return self._bus.read_i2c_block_data(addr, reg, n)

    def write_byte_data(self, addr, reg, val):
        with self._lock:
            return self._bus.write_byte_data(addr, reg, val)

    def close(self):
        self._bus.close()
