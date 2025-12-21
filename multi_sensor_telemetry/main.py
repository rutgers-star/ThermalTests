import argparse
from tmpsensor import TMPSensor
from fake_tmpsensor import FakeTMPSensor
import smbus
import RPi.GPIO as GPIO
import time


def main():

    ADDRESS = 0x4f
    TEMP_REG = 0x00
    CONFIG_REG = 0x01
    TLOW_REG = 0x10
    HIGH_REG = 0x11
    CHANNEL = 1

    bus = smbus.SMBus(CHANNEL)
    bus.write_byte_data(ADDRESS, 0x01, 0b1100000)

    testtmp = TMPSensor(addr=0x4f, bus = None, reg = 0x00, interval=0.5)
    testtmp.start()

    testfake = FakeTMPSensor(addr=0x00, reg=0x00, interval=0.5, baseline=70.0)
    testfake.start()
    
    parser = argparse.ArgumentParser()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        testtmp.stop()
        testfake.stop()