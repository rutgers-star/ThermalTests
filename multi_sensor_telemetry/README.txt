Multi-Sensor Telemetry (TMP100)

Threaded telemetry for up to four TI TMP100 sensors on I2C bus 1 (0x48-0x4F).
Temperatures are in degrees C.


COMMAND LINE
Run from this directory:

  python main.py --list                      scan for sensors, print addresses, exit
  python main.py                             stream every sensor found, one row per second
  python main.py --interval 5                one row every 5 seconds
  python main.py --csv run1.csv --rows 100   log 100 rows, then stop
  python main.py --single --address 0x4f     read one address only
  python main.py --fake                      simulated sensors, no I2C

--fake works with every other flag, so all modes run on a laptop.
--rows defaults to 0, meaning run until Ctrl-C.
Sensors always sample at 0.5s; --interval only controls how often rows are
printed and logged.

From the repository root the package form is equivalent:

  python -m multi_sensor_telemetry.main --fake --rows 5


LIBRARY USE
From the repository root:

    from multi_sensor_telemetry import MultiTMP100
    import time

    m = MultiTMP100(use_fake=True)   # omit use_fake on the Raspberry Pi
    try:
        m.start()
        time.sleep(0.6)
        temps = m.get_latest()       # {"0x48": temperature_c, ...}
        status = m.get_status()      # per address: temperature, timestamp, age, valid, error
    finally:
        m.stop()


READING VALIDITY  (important for PID control)
get_latest() returns None for a sensor that has not sampled yet, hit a read
error, been stopped, or whose last good sample is older than max_age.
MultiTMPSensors.get_latest() omits those addresses entirely.

A PID consumer must handle a missing address. Do not hold the last known
temperature indefinitely: a disconnected sensor would otherwise look healthy.

max_age defaults to max(1.0, 3 * interval); pass max_age to a sensor or to
MultiTMPSensors to override it. Freshness uses a monotonic clock, while
status timestamps are Unix seconds. A successful read clears a previous error.
get_buffer() returns history and says nothing about current validity.


SHUTDOWN
Sampling waits are interruptible, so stop() normally returns at once. If a
hardware read is still blocked past the timeout, stop() raises TimeoutError and
keeps the worker and bus open; retry stop() once the read returns. Python
cannot cancel a blocked hardware call. Lifecycle calls should come from one
owning thread.


CSV
Each row is a timestamp plus one column per sensor address, written
immediately. Invalid readings are left blank. The existing header is checked
before appending: if the sensor set changed, write_csv raises ValueError and
the CLI stops. Use a new filename for a different set of sensors.


SETUP
Laptop:       python -m venv .venv && .venv\Scripts\activate
              python main.py --fake
Raspberry Pi: sudo apt install python3-venv
              python3 -m venv .venv
              source .venv/bin/activate
              python -m pip install -r requirements.txt
              python main.py

Tests (from the repository root, no hardware needed):

  python -B -m unittest discover -s multi_sensor_telemetry/tests -v

Real I2C discovery, conversion timing, and wiring still need a Raspberry Pi.

requirements.txt installs smbus2 on Linux. Fake mode and tests use only the
standard library; pip skips smbus2 on Windows and macOS. Real sensor access
also requires I2C enabled and permission to access /dev/i2c-1 on the Pi.
