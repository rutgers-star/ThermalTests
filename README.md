# ThermalTests

Software test, telemetry, and control prototyping for the SPICEsat thermal testbench.

Work done by Systems Integration & Test.

## Hardware required

- Raspberry Pi 4 (Linux / Raspberry Pi OS)
- TMP-series I²C temperature sensors (TMP100 / TMP102; ADD0/ADD1 select the address)
- Heater patch / resistive heater (PWM through GPIO)

## Multi-sensor telemetry

From `multi_sensor_telemetry/`:

```text
python main.py --fake              # four simulated sensors (works in a venv)
python main.py --fake --single     # one simulated sensor
python main.py                     # scan 0x48-0x4F on I2C bus 1 (Pi)
python main.py --single --address 0x4f
```

`--fake` uses only the Python standard library. For real reads on the Pi, create a normal virtual environment and run `python -m pip install -r multi_sensor_telemetry/requirements.txt` from the repository root. This installs `smbus2` on Linux. Enable I2C and ensure access to `/dev/i2c-1`; `--system-site-packages` is not required.

Temperatures are in °C.
