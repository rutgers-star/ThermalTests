"""Threaded TMP100 telemetry with optional simulated sensors."""
from .tmpsensor import TMPSensor
from .fake_tmpsensor import FakeTMPSensor
from .multi_tmpsensor import MultiTMPSensors

MultiTMP100 = MultiTMPSensors
__all__ = ["TMPSensor", "FakeTMPSensor", "MultiTMPSensors", "MultiTMP100"]
