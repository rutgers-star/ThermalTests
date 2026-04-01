class PIDController:
    def __init__(self, Kp, Ki, Kd, dt, uMin = 0, uMax = 100):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.uMin = uMin
        self.uMax = uMax
        
        self.integral = 0.0
        self.prevError = 0.0
    
    def reset(self):
        self.integral = 0.0
        self.prevError = 0.0
    
    def update(self, setpoint, measured):
        error = setpoint - measured
        P = self.Kp * error
        self.integral += error * self.dt
        I = self.Ki * self.integral
        D = self.Kd * (error - self.prevError) / self.dt
        
        output = P + I + D
        output = max(self.uMin, min(output, self.uMax))
        
        self.prevError = error
        return output