import csv

class ThermalController:
    
    def __init__(self, pid, tank, setpoint, dt = 1.0, totalTime = 500.0):
        self.pid = pid
        self.tank = tank
        self.setpoint = setpoint
        self.dt = dt
        self.totalTime = totalTime
        self.time = 0.0
        self.history = []
        
    def run_step(self):
        
        measuredTemp = self.tank.T
        
        duty = self.pid.update(self.setpoint, measuredTemp)
        
        measuredTemp = self.tank.step(duty)
        
        self.time += self.dt
        
        self.history.append((self.time, measuredTemp, duty))
        
        return measuredTemp, duty
    
    def start(self):
        steps = int(self.totalTime / self.dt)
        for _ in range(steps):
            self.run_step()
            
    def write_csv(self, filename = "thermal_log.csv"):
        with open(filename, "w", newline = "") as f:
            writer = csv.writer(f)
            writer.writerow(["time_sec", "temp_C", "duty_percent"])
            for t, temp, duty in self.history:
                writer.writerow([t, temp, duty])