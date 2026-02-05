from pid_controller import PIDController
from fake_heater_tank import FakeHeaterTank
from thermal_controller import ThermalController

def main():
    
    dt = 1.0
    totalTime = 1000.0
    setpoint = 40.0
    
    Kp = 4.0
    Ki = 0.1
    Kd = 10.0
    
    pid = PIDController(Kp, Ki, Kd, dt)
    tank = FakeHeaterTank(tamb = 25.0, t0 = 25.0, K = 0.4, tau = 80.0, dt = dt)
    controller = ThermalController(pid, tank, setpoint, dt, totalTime)
    
    controller.start()
    controller.write_csv("thermal_log.csv")
    
    print("time temp_C duty_%")
    for t, temp, duty in controller.history[0:10]:
        print(f"{t:4.0f} {temp:6.2f} {duty:6.1f}")
        
    print("... (full log in thermal_log.csv)")
    
if __name__ == "__main__":
    main()