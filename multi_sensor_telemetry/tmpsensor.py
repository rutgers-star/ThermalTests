import threading
import time
import smbus

class TMPSensor:
    def __init__(self, addr, bus=None, reg=0x00, interval=0.5):
        self.addr = addr
        self.reg = reg
        self.interval = interval
        self.bus = bus if bus is not None else smbus.SMBus(1)
        self._buffer = []
        self._latest = None 
        self._running = False
        self._thread = None

    def read_once(self):
        tempData = self.bus.read_i2c_block_data(self.addr, self.reg, 2)
        temp = ((tempData[0] << 8) + (tempData[1] & 0b11110000)) >> 4
        if temp > 2047:
            temp -= 4096
        temp *= 0.0625
        return temp
    
    def _loop(self):
        while self._running:
            value = self.read_once()
            self._latest = value
            print(value)
            self._buffer.append(value)
            time.sleep(self.interval)

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def get_buffer(self):
        return list(self._buffer)

    def get_latest(self):
        return self._latest
    
<<<<<<< HEAD
=======
    ## only prints one value
>>>>>>> 456571bab87a6c49926cd22ae34cf054a86068e7
