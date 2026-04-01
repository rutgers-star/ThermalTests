import random

class FakeHeaterTank:
    def __init__(self, tamb = 25.0, t0 = 25.0, K = 0.5, tau = 60.0, dt = 1.0, noiseSTD = 0.05):
        self.tamb = tamb
        self.T = t0
        self.K = K
        self.tau = tau
        self.dt = dt
        self.noiseSTD = noiseSTD
        
    def step(self, duty):
        duty = max(0.0, min(duty, 100.0))
        dutyFrac = duty / 100.0
        
        dTdt = -(self.T - self.tamb) / self.tau + self.K * dutyFrac
        
        self.T += dTdt * self.dt
        
        measuredT = self.T + random.gauss(0.0, self.noiseSTD)
        return measuredT