# Multi-Sensor Telemetry Backend (TMP100 Network)

## Repository Structure

.
├── main.py # Orchestration / CLI
├── tmpsensor.py # TMPSensor class (real sensor)
├── fake_tmpsensor.py # FakeTMPSensor class (simulated data)
├── multi_tmpsensor.py # MultiTMPSensors class (manages multiple sensors)
└── README.md # Project documentation