# BasicHeaterTest.py
# Read temperature from TMP100 and control heater accordingly
import smbus
import RPi.GPIO as GPIO
import time

# I2C channel 1 is connected to the GPIO pins
CHANNEL = 1

# TMP100 address defaults to 0x48 when ADD0 and ADD1 = 0
# Change this according to the TMP100 documentation
ADDRESS = 0x4f

# Define register locations
TEMP_REG = 0b00
CONFIG_REG = 0b01
TLOW_REG = 0b10
THIGH_REG = 0b11

# Initialize I2C (SMBus)
bus = smbus.SMBus(CHANNEL)

# Configure TMP100 via config register
bus.write_byte_data(ADDRESS, 0x01, 0b1100000)

# Define heater control
HEATER_PIN = 22 # Change this according to how the heater control is connected
LOW_TEMP = 20  # C
HIGH_TEMP = 24 # C
GPIO.setmode(GPIO.BOARD)
GPIO.setup(HEATER_PIN, GPIO.OUT)

# TMP100 temperature read
def readTempC(addr, reg):
  # Read temp data (2 bytes)
  tempData = bus.read_i2c_block_data(addr, reg, 2)  

  # Convert raw data to correct 12-bit format
  temp = ((tempData[0] << 8) + (tempData[1] & 0b11110000)) >> 4

  # Overflow check
  if (temp > 2047):
    temp -= 4096

  # Convert temp level to degrees C
  temp *= 0.0625 
  return temp

# Perform test
def main():
  while(True):
    temp = readTempC(ADDRESS, TEMP_REG)
    print(temp)

    if (temp >= HIGH_TEMP):
      GPIO.output(HEATER_PIN, GPIO.LOW)
    elif (temp <= LOW_TEMP):
      GPIO.output(HEATER_PIN, GPIO.HIGH)
    time.sleep(0.05)

# Run main function
if __name__ == "__main__":
  main()
