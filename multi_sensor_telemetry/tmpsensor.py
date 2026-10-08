if __package__:
    from .sensor_base import BackgroundSensor
    from .i2c import import_smbus, LockedSMBus
else:
    from sensor_base import BackgroundSensor
    from i2c import import_smbus, LockedSMBus


class TMPSensor(BackgroundSensor):
    def __init__(self, addr, bus=None, reg=0x00, interval=0.5, channel=1, max_age=None):
        super().__init__(addr=addr, interval=interval, max_age=max_age)
        self.reg = reg
        self.channel = channel
        self._owns_bus = bus is None
        if bus is None:
            smbus = import_smbus()
            bus = LockedSMBus(smbus.SMBus(channel))
        self.bus = bus

    def start(self):
        with self._lifecycle_lock:
            if self._owns_bus and self.bus is None:
                smbus = import_smbus()
                self.bus = LockedSMBus(smbus.SMBus(self.channel))
            super().start()

    def read_once(self):
        temp_data = self.bus.read_i2c_block_data(self.addr, self.reg, 2)
        temp = ((temp_data[0] << 8) + (temp_data[1] & 0b11110000)) >> 4
        if temp > 2047:
            temp -= 4096
        return temp * 0.0625

    def stop(self, timeout=2.0):
        with self._lifecycle_lock:
            super().stop(timeout=timeout)
            if self._owns_bus and self.bus is not None:
                self.bus.close()
                self.bus = None
