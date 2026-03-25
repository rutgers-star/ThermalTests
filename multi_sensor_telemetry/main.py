import argparse
from multi_tmpsensor import MultiTMPSensors
from tmpsensor import TMPSensor
from fake_tmpsensor import FakeTMPSensor
import smbus
import RPi.GPIO as GPIO
import time

'''main.py --single --address 0x4f  main.py --single --fake'''
def main():

    TEMP_REG = 0x00
    CONFIG_REG = 0x01
    TLOW_REG = 0x10
    HIGH_REG = 0x11
    CHANNEL = 1

    parser = argparse.ArgumentParser()
    parser.add_argument("--address", type=lambda x: int(x, 0), default=0x4f, help="I2C address of sensor (e.g. 0x4f or 79)")
    parser.add_argument("--fake", action="store_true", help="Use fake sensors")
    parser.add_argument("--single", action="store_true", help="Run single TMPSensor + FakeTMPSensor instead of MultiTMPSensors")
    args = parser.parse_args()
    ADDRESS = args.address

    if args.single:
        if not args.fake:
            bus = smbus.SMBus(CHANNEL)
            bus.write_byte_data(ADDRESS, CONFIG_REG, 0b1100000)
            testtmp = TMPSensor(addr=ADDRESS, bus=bus, reg=TEMP_REG, interval=0.5)
            testtmp.start()
        testfake = FakeTMPSensor(addr=0x00, reg=TEMP_REG, interval=0.5, baseline=70.0)
        testfake.start()
        try:
            while True:
                if not args.fake:
                    print("real:", testtmp.get_latest(), "fake:", testfake.get_latest())
                else:
                    print("fake:", testfake.get_latest())
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            if not args.fake:
                testtmp.stop()
                bus.close()
            testfake.stop()
    else:
        if not args.fake:
            bus = smbus.SMBus(CHANNEL)
            bus.write_byte_data(ADDRESS, CONFIG_REG, 0b1100000)
            bus.close()
        m = MultiTMPSensors(use_fake=args.fake)
        m.start()
        try:
            while True:
                print(m.get_latest())
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            m.stop()


if __name__ == "__main__":
    main()
