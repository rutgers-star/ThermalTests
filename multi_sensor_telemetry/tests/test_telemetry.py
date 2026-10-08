import contextlib
import csv
import io
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from multi_sensor_telemetry import FakeTMPSensor, MultiTMPSensors, TMPSensor
from multi_sensor_telemetry import main
from multi_sensor_telemetry.sensor_base import BackgroundSensor

ROOT = Path(__file__).resolve().parents[2]


def wait_for(predicate):
    deadline = time.monotonic() + 1
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("Timed out waiting for worker")
        time.sleep(0.005)


class TelemetryTests(unittest.TestCase):
    def test_csv_schema_validation_and_key_order(self):
        manager = MultiTMPSensors(use_fake=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log.csv"
            manager.write_csv([{"timestamp": "first", "0x48": 21, "0x49": 22}], path)
            manager.write_csv([{"0x49": 24, "0x48": 23, "timestamp": "second"}], path)
            original = path.read_bytes()
            for rows in (
                [{"timestamp": "third", "0x49": 25}],
                [{"timestamp": "third", "0x48": 25, "0x4a": 26}],
                [{"timestamp": "third", "0x48": 25, "0x49": 26, "0x4a": 27}],
                [{"timestamp": "third", "0x48": 25, "0x49": 26},
                 {"timestamp": "fourth", "0x49": 27}],
            ):
                with self.assertRaisesRegex(ValueError, "CSV columns"):
                    manager.write_csv(rows, path)
                self.assertEqual(path.read_bytes(), original)
            with path.open(newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1], {"timestamp": "second", "0x48": "23", "0x49": "24"})

    def test_owned_bus_reopens_on_restart(self):
        buses, channels = [], []
        class Bus:
            closed = False
            close_count = 0
            def read_i2c_block_data(self, *args):
                if self.closed:
                    raise OSError("bus closed")
                return [21, 0]
            def close(self):
                self.closed = True
                self.close_count += 1
        def open_bus(channel):
            channels.append(channel)
            bus = Bus()
            buses.append(bus)
            return bus
        with patch("multi_sensor_telemetry.tmpsensor.import_smbus",
                   return_value=SimpleNamespace(SMBus=open_bus)):
            sensor = TMPSensor(0x48, channel=3, interval=.01)
            for _ in range(2):
                try:
                    sensor.start()
                    sensor.start()
                    wait_for(lambda: sensor.get_latest() == 21)
                    self.assertIsNone(sensor.get_status()["error"])
                finally:
                    sensor.stop()
                sensor.stop()
                self.assertTrue(buses[-1].closed)
                self.assertEqual(buses[-1].close_count, 1)
            self.assertEqual(channels, [3, 3])

    def test_borrowed_bus_is_preserved_on_restart(self):
        class Bus:
            def read_i2c_block_data(self, *args):
                return [21, 0]
            def close(self):
                raise AssertionError("Borrowed bus must not be closed")
        bus = Bus()
        sensor = TMPSensor(0x48, bus=bus, interval=.01)
        for _ in range(2):
            try:
                sensor.start()
                wait_for(lambda: sensor.get_latest() == 21)
                self.assertIs(sensor.bus, bus)
            finally:
                sensor.stop()

    def test_failure_invalidates_and_recovery_restores(self):
        class Sensor(BackgroundSensor):
            fail = False
            def read_once(self):
                if self.fail:
                    raise OSError("disconnected")
                return 21.0
        s = Sensor(0x48, interval=.01)
        s.start()
        try:
            wait_for(lambda: s.get_latest() == 21)
            timestamp = s.get_status()["timestamp"]
            s.fail = True
            wait_for(lambda: s.get_status()["error"] is not None)
            self.assertIsNone(s.get_latest())
            self.assertGreaterEqual(s.get_status()["timestamp"], timestamp)
            s.fail = False
            wait_for(lambda: s.get_status()["valid"])
        finally:
            s.stop()
        self.assertIsNone(s.get_latest())

    def test_stale_reading(self):
        s = FakeTMPSensor(interval=10, max_age=.02)
        s.start()
        try:
            wait_for(lambda: s.get_status()["timestamp"] is not None)
            time.sleep(.03)
            self.assertIsNone(s.get_latest())
            self.assertFalse(s.get_status()["valid"])
        finally:
            s.stop()

    def test_long_interval_stops_promptly_and_restarts(self):
        s = FakeTMPSensor(interval=30)
        for _ in range(2):
            s.start()
            wait_for(lambda: s.get_latest() is not None)
            worker = s._thread
            s.stop(timeout=.5)
            self.assertFalse(worker.is_alive())

    def test_blocked_read_retains_worker_and_bus(self):
        entered, release = threading.Event(), threading.Event()
        class Bus:
            closed = False
            def read_i2c_block_data(self, *args):
                entered.set()
                release.wait(5)
                return [0x15, 0]
            def close(self):
                self.closed = True
        bus = Bus()
        sensor = TMPSensor(0x48, bus=bus)
        manager = MultiTMPSensors()
        manager._sensors = [sensor]
        manager._bus = bus
        sensor.start()
        self.assertTrue(entered.wait(1))
        try:
            with patch.object(sensor, "stop", side_effect=TimeoutError("blocked")):
                with self.assertRaises(TimeoutError):
                    manager.stop()
            self.assertFalse(bus.closed)
            self.assertEqual(manager.get_sensors(), [sensor])
            with self.assertRaises(TimeoutError):
                sensor.stop(timeout=.01)
            self.assertTrue(sensor._thread.is_alive())
            with self.assertRaises(RuntimeError):
                sensor.start()
        finally:
            release.set()
            manager.stop()
        self.assertTrue(bus.closed)

    def test_csv_failure_stops_workers(self):
        manager = MultiTMPSensors(use_fake=True, interval=.01)
        workers = []
        def broken_write(*args):
            workers.extend(s._thread for s in manager.get_sensors())
            raise OSError("disk failure")
        args = SimpleNamespace(interval=.01, fake=True, channel=1, csv="unused", rows=1)
        with patch.object(main, "MultiTMPSensors", return_value=manager), \
             patch.object(manager, "write_csv", side_effect=broken_write), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                main._run_multi(args)
        self.assertEqual(len(workers), 4)
        self.assertTrue(all(not t.is_alive() for t in workers))

    def test_cli_and_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            for single in (False, True):
                output = Path(directory) / ("single.csv" if single else "multi.csv")
                command = [sys.executable, "-B", "-m", "multi_sensor_telemetry.main",
                           "--fake", "--interval", ".01", "--rows", "12", "--csv", str(output)]
                if single:
                    command += ["--single", "--address", "0x4f"]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                with output.open() as f:
                    rows = list(csv.DictReader(f))
                self.assertEqual(len(rows), 12)
                self.assertEqual(len(rows[0]), 2 if single else 5)
                self.assertTrue(all(all(row.values()) for row in rows))
                if single:
                    self.assertIn("0x4f", rows[0])
            result = subprocess.run([sys.executable, "-B", str(ROOT / "multi_sensor_telemetry/main.py"),
                                     "--fake", "--list"], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("0x4b", result.stdout)

    def test_package_import(self):
        result = subprocess.run([sys.executable, "-B", "-c",
            "from multi_sensor_telemetry import MultiTMP100; m=MultiTMP100(use_fake=True); m.start(); m.stop()"],
            cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_temperature_decode(self):
        class Bus:
            def read_i2c_block_data(self, *args):
                return self.data
        bus = Bus()
        sensor = TMPSensor(0x48, bus=bus)
        for raw, expected in [(0x1900, 25), (0xFFC0, -.25), (0xC900, -55), (0x7D00, 125)]:
            bus.data = [raw >> 8, raw & 255]
            self.assertEqual(sensor.read_once(), expected)

    def test_invalid_intervals(self):
        for interval in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                FakeTMPSensor(interval=interval)
            with self.assertRaises(ValueError):
                MultiTMPSensors(interval=interval)
            with self.assertRaises(ValueError):
                MultiTMPSensors(max_age=interval)

    def test_scan_message_lists_probed_addresses(self):
        class Bus:
            def read_i2c_block_data(self, *args):
                raise OSError(121, "Remote I/O error")
            def close(self):
                pass
        smbus = SimpleNamespace(SMBus=lambda channel: Bus())
        with patch("multi_sensor_telemetry.multi_tmpsensor.import_smbus", return_value=smbus):
            with self.assertRaises(RuntimeError) as caught:
                MultiTMPSensors(addresses=[0x4F]).start()
            self.assertIn("scanned 0x4f", str(caught.exception))
            with self.assertRaises(RuntimeError) as caught:
                MultiTMPSensors().start()
            self.assertIn("0x48, 0x49", str(caught.exception))

    def test_stop_timeout_reports_cleanly(self):
        manager = MultiTMPSensors(use_fake=True, interval=.01)
        args = SimpleNamespace(interval=.01, fake=True, channel=1, csv=None, rows=1)
        with patch.object(main, "MultiTMPSensors", return_value=manager), \
             patch.object(manager, "stop", side_effect=TimeoutError("read has not stopped")), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main._run_multi(args)
        self.assertIn("read has not stopped", str(caught.exception))
        for sensor in manager.get_sensors():
            sensor.request_stop()


if __name__ == "__main__":
    unittest.main()
