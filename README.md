# ThermalTests

Software test, telemetry, and control prototyping for the SPICEsat thermal testbench.

Work done by Systems Integration & Test.

## Hardware required

- Raspberry Pi 4 (Linux / Raspberry Pi OS)
- TMP-series I²C temperature sensors (TMP100 / TMP102; ADD0/ADD1 select the address)
- Heater patch / resistive heater (PWM through GPIO)

---

# Setting up on a Raspberry Pi, step by step

Follow these in order. Steps 1–5 are a one-time setup; after that you only need Step 7.

Want to run it on a laptop with no sensors? Skip to
[Running without any hardware](#running-without-any-hardware).

## Step 1 — Turn the Pi OFF

Unplug the power. **Never move wires while the Pi is on.**

## Step 2 — Wire up the sensors

Every sensor shares the same four Pi pins. Wire them all in parallel:

| Sensor pin | Goes to Pi pin | What it is |
| --- | --- | --- |
| V+ (or VCC) | pin **1** | 3.3 volts (power) |
| GND | pin **6** | ground |
| SDA | pin **3** | data |
| SCL | pin **5** | clock |

Pin 1 is the corner pin closest to the SD card slot. The odd numbers (1, 3, 5) are all
in the same row.

Each sensor needs its **own address**, chosen with its ADD0 and ADD1 pins. Two sensors
sharing an address will not both show up. Both pins to GND gives `0x48`; both to 3.3 V
gives `0x4f`. The usable range is `0x48`–`0x4f`.

## Step 3 — Power on and enable I2C

Plug the Pi back in, open a terminal, and run:

```bash
sudo raspi-config
```

Then: **Interface Options** → **I2C** → **Yes** → **OK** → **Finish**.

Reboot so the change takes effect:

```bash
sudo reboot
```

## Step 4 — Check the Pi can see your sensors

**4a. Do you already have the I2C tool?**

```bash
i2cdetect -V
```

If that prints a version number, skip ahead. If it says `command not found`:

```bash
sudo apt install -y i2c-tools
```

**4b. Is I2C actually switched on?**

```bash
ls /dev/i2c-*
```

`/dev/i2c-1` means yes. `No such file or directory` means Step 3 did not take — repeat
it and make sure you reboot.

**4c. Find your sensors.**

```bash
i2cdetect -y 1
```

Every sensor you wired should appear as a number between `48` and `4f`:

```text
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
40: -- -- -- -- -- -- -- -- 48 49 4a 4b -- -- -- --
```

If a sensor is missing here, the software will not find it either. Fix the wiring
before going on.

## Step 5 — Install the software

```bash
git clone https://github.com/rutgers-star/ThermalTests.git
cd ThermalTests
```

```bash
sudo apt install -y python3-venv
```

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
python -m pip install -r multi_sensor_telemetry/requirements.txt
```

That installs `smbus2`, the only third-party dependency. A plain virtual environment is
enough — you do **not** need `--system-site-packages`.

## Step 6 — Confirm the software sees the same sensors

```bash
cd multi_sensor_telemetry
python main.py --list
```

```text
Found 4 TMP100 sensor(s) on I2C bus 1:
  0x48
  0x49
  0x4a
  0x4b
```

This list should match what `i2cdetect` showed in Step 4c. If it does, everything below
will work.

## Step 7 — Stream live temperatures

```bash
python main.py
```

One row per second, one column per sensor:

```text
{'0x48': 21.438, '0x49': 20.812, '0x4a': 21.125, '0x4b': 20.938}
```

Press **Ctrl-C** to stop.

## Step 8 — Log a run to CSV

```bash
python main.py --csv run1.csv --interval 5
```

That writes a row every 5 seconds to `run1.csv` until you press Ctrl-C:

```text
timestamp,0x48,0x49,0x4a,0x4b
2026-10-13T14:02:11.431,21.438,20.812,21.125,20.938
```

To stop automatically after a set number of rows, add `--rows`:

```bash
python main.py --csv run1.csv --interval 5 --rows 720   # one hour at 5 s
```

### Coming back later

The virtual environment has to be activated each time you open a new terminal:

```bash
cd ThermalTests && source .venv/bin/activate
cd multi_sensor_telemetry && python main.py
```

---

## Running without any hardware

Add `--fake` to any command and the code uses four simulated sensors and never touches
I2C. This works on Windows, macOS, and Linux, and needs no `pip install` at all —
simulation mode is pure standard library.

```bash
python main.py --fake --list
python main.py --fake
python main.py --fake --csv test.csv --rows 10 --interval 0.5
```

Run the test suite the same way, from the repository root:

```bash
python -B -m unittest discover -s multi_sensor_telemetry/tests -v
```

---

## All the options

```text
--list                scan 0x48-0x4F, print what was found, exit
--fake                use simulated sensors, no I2C
--single              read one address instead of scanning
--address 0x4f        which address --single uses (default 0x4f)
--channel 1           I2C bus number (default 1)
--interval 5          seconds between printed/logged rows (default 1.0)
--csv [FILE]          append rows to a CSV log
--rows 100            stop after N rows (default 0 = until Ctrl-C)
```

Sensors always sample at 0.5 s internally; `--interval` only changes how often rows are
printed and logged.

---

## If it does not work

| What you see | What to do |
| --- | --- |
| `i2cdetect` shows no numbers | Turn the Pi off and recheck the four wires. A loose wire is the most common cause. |
| `i2cdetect` shows fewer sensors than you wired | Two sensors are probably set to the same address. Change one with its ADD0/ADD1 pins. |
| `No such file or directory: /dev/i2c-1` | I2C is not enabled. Redo Step 3, including the reboot. |
| `ModuleNotFoundError: smbus2` | The virtual environment is not active. Run `source .venv/bin/activate`. |
| `PermissionError` on `/dev/i2c-1` | Your user is not in the `i2c` group. Run `sudo usermod -aG i2c $USER`, then log out and back in. |
| `No TMP100 sensors found on I2C bus 1` | The software scanned but nothing answered. Check Step 4c first — if `i2cdetect` is empty too, it is the wiring. |
| An address disappears mid-run | That sensor stopped responding or went stale. See below. |

### About missing addresses

`get_latest()` deliberately **omits** a sensor that has errored, been stopped, or whose
last good reading is older than `max_age`. A disconnected sensor disappears from the
output instead of repeating its last temperature forever, so the PID controller can
never act on a frozen reading. In the CSV, that address is left blank for those rows.

---

## Using it from your own code

This is how the PID controller consumes it. Run from the repository root:

```python
from multi_sensor_telemetry import MultiTMP100
import time

m = MultiTMP100()            # add use_fake=True to run with no hardware
try:
    m.start()
    time.sleep(0.6)
    temps  = m.get_latest()  # {"0x48": 21.4, ...}  invalid sensors omitted
    status = m.get_status()  # temperature, timestamp, age, valid, error
finally:
    m.stop()
```

Temperatures are in °C. See `multi_sensor_telemetry/README.txt` for the full API notes,
shutdown semantics, and CSV behaviour.
