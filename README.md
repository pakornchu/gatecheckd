# gatecheckd
Sliding gate position check using VL53L0X sensor

## Hardware
* Raspberry Pi with I2C headers
* Adafruit VL53L0X Time of Flight Distance Sensor

## Software
* Python 3
* CircuitPython, adafruit-circuitpython-vl53l0x from PIP
* i2c-tools for determining sensor address

## Other services
* Sentry for error tracking
* Telegram bot API

## How it works
Daemon obtains range reading from sensor every specific time and issue state change notification after CFSLOT repeating readings.
