THERMAL PID CONTROLLER PROJECT
==============================

This project simulates a heater controller by a PID controller in Python.

Files:
main.py - runs the program
pid_controller.py - PID logic
fake_heater_tank.py - simulated heater
thermal_controller.py - control loop + CSV output

Run:
python main.py

Output:
thermal_log.csv (time, temperature, duty)

Change target and tuning in main.py:
setpoint
Kp, Ki, Kd

Real data:
Replace FakeHeaterTank with real temperature readings from a sensor and pass those values into the PID update.

Purpose:
Learn PID control before using real hardware.