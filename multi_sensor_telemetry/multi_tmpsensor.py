from tmpsensor import TMPSensor
from fake_tmpsensor import FakeTMPSensor
import threading
import csv
import os
import smbus

class MultiTMPSensors:

    def __init__(self, use_fake=False):
        self.use_fake = use_fake
        self._sensors = []
        self._bus = None

    def get_addrs(self):
        addrs = []
        bus = smbus.SMBus(1)
        for addr in range(0x48, 0x50):
            try:
                bus.read_i2c_block_data(addr, 0x00, 2)
                addrs.append(addr)
            except (OSError, IOError):
                pass
        bus.close()
        return addrs

    def get_sensors(self):
        return list(self._sensors)

    def start(self):
        if not self._sensors:
            if self.use_fake:
                for addr in range(0x48, 0x4C):
                    self._sensors.append(FakeTMPSensor(addr=addr, reg=0x00, interval=0.5, baseline=70.0))
            else:
                addrs = self.get_addrs()
                self._bus = smbus.SMBus(1)
                for addr in addrs:
                    self._sensors.append(TMPSensor(addr=addr, bus=self._bus, reg=0x00, interval=0.5))
        for s in self._sensors:
            s.start()

    def stop(self):
        sensors = list(self._sensors)
        self._sensors = []
        for s in sensors:
            s.stop()
        if self._bus is not None:
            try:
                self._bus.close()
            except Exception:
                pass
            self._bus = None

    def get_latest(self):
        out = {}
        for s in self._sensors:
            t = s.get_latest()
            if t is not None:
                out[hex(s.addr)] = t
        return out

    def write_csv(self, rows, filename=None):
        if filename is None:
            filename = "multi_tmp100_log.csv"
        if not rows:
            return
        write_header = not os.path.exists(filename) or os.path.getsize(filename) == 0
        with open(filename, "a", newline="") as f:
            if isinstance(rows[0], dict):
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                if write_header:
                    w.writeheader()
                w.writerows(rows)
            else:
                w = csv.writer(f)
                w.writerows(rows)
