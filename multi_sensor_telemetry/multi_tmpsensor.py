import csv

if __package__:
    from .fake_tmpsensor import FakeTMPSensor
    from .i2c import LockedSMBus, import_smbus
    from .sensor_base import positive
    from .tmpsensor import TMPSensor
else:
    from fake_tmpsensor import FakeTMPSensor
    from i2c import LockedSMBus, import_smbus
    from sensor_base import positive
    from tmpsensor import TMPSensor

TEMP_REG = 0x00
CONFIG_REG = 0x01
CONFIG_12BIT = 0b1100000
SCAN_START = 0x48
SCAN_END = 0x50
FAKE_END = 0x4C


class MultiTMPSensors:
    def __init__(self, use_fake=False, channel=1, interval=0.5, addresses=None, max_age=None):
        self.use_fake = use_fake
        self.channel = channel
        self.interval = positive("interval", interval)
        self.addresses = None if addresses is None else list(addresses)
        self.max_age = None if max_age is None else positive("max_age", max_age)
        self._sensors = []
        self._bus = None

    def _scanned(self):
        if self.addresses is not None:
            return list(self.addresses)
        return list(range(SCAN_START, FAKE_END if self.use_fake else SCAN_END))

    def get_addrs(self):
        if self.use_fake:
            return self._scanned()
        if self._bus is None:
            smbus = import_smbus()
            self._bus = LockedSMBus(smbus.SMBus(self.channel))
        addrs = []
        for addr in self._scanned():
            try:
                self._bus.read_i2c_block_data(addr, TEMP_REG, 2)
                addrs.append(addr)
            except (OSError, IOError):
                pass
        return addrs

    def get_sensors(self):
        return list(self._sensors)

    def start(self):
        if not self._sensors:
            if self.use_fake:
                for addr in self.get_addrs():
                    self._sensors.append(
                        FakeTMPSensor(addr=addr, interval=self.interval, max_age=self.max_age)
                    )
            else:
                addrs = self.get_addrs()
                if not addrs:
                    self.stop()
                    raise RuntimeError(
                        f"No TMP100 sensors found on I2C bus {self.channel} "
                        f"(scanned {', '.join(hex(a) for a in self._scanned())})."
                    )
                for addr in addrs:
                    try:
                        self._bus.write_byte_data(addr, CONFIG_REG, CONFIG_12BIT)
                    except (OSError, IOError):
                        continue
                    self._sensors.append(
                        TMPSensor(addr=addr, bus=self._bus, reg=TEMP_REG, interval=self.interval, max_age=self.max_age)
                    )
                if not self._sensors:
                    self.stop()
                    raise RuntimeError(
                        f"Found TMP100-like addresses on bus {self.channel} but could not configure any."
                    )
        for sensor in self._sensors:
            sensor.start()

    def stop(self):
        # Signal every worker before joining any; retain resources on timeout.
        for sensor in self._sensors:
            sensor.request_stop()
        errors = []
        for sensor in self._sensors:
            try:
                sensor.stop()
            except TimeoutError as exc:
                errors.append(exc)
        if errors:
            raise errors[0]
        if self._bus is not None:
            self._bus.close()
            self._bus = None
        self._sensors = []

    def get_status(self):
        return {hex(sensor.addr): sensor.get_status() for sensor in self._sensors}

    def get_latest(self):
        out = {}
        for sensor in self._sensors:
            reading = sensor.get_latest()
            if reading is not None:
                out[hex(sensor.addr)] = round(reading, 3)
        return out

    def write_csv(self, rows, filename=None):
        if filename is None:
            filename = "multi_tmp100_log.csv"
        if not rows:
            return
        with open(filename, "a+", newline="") as f:
            f.seek(0)
            header = next(csv.reader(f), None)
            if isinstance(rows[0], dict):
                fields = list(rows[0]) if header is None else header
                if len(fields) != len(set(fields)) or any(
                    not isinstance(row, dict) or set(row) != set(fields) for row in rows
                ):
                    raise ValueError(
                        "CSV columns do not match the log header; use a new log file "
                        "when the sensor set changes."
                    )
                f.seek(0, 2)
                writer = csv.DictWriter(f, fieldnames=fields)
                if header is None:
                    writer.writeheader()
                writer.writerows(rows)
            else:
                f.seek(0, 2)
                csv.writer(f).writerows(rows)
