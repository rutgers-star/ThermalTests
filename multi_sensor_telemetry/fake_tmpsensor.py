import random

if __package__:
    from .sensor_base import BackgroundSensor
else:
    from sensor_base import BackgroundSensor


class FakeTMPSensor(BackgroundSensor):
    """Simulated TMP100 for laptop/venv testing. Values are in °C."""

    def __init__(self, addr=0x00, interval=0.5, baseline=21.0, max_age=None):
        super().__init__(addr=addr, interval=interval, max_age=max_age)
        self.baseline = baseline

    def read_once(self):
        return round(self.baseline + random.uniform(-1.0, 1.0), 3)
