#!/usr/bin/env python
#

# The MIT License (MIT)
#
# Copyright (c) 2015-2017 Massimo Gaggero, 2018 Holger Kupke
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import io
import time
import math
import fcntl
import logging
import sys

# RPI-2/3 IC2 default bus
I2C_BUS                   = 1

# RPI I2C slave address
I2C_SLAVE                 = 0x0703

# HTU21D-F default address
HTU21D_I2CADDR            = 0x40

# HTU21D-F operation modes
HTU21D_HOLDMASTER         = 0x00
HTU21D_NOHOLDMASTER       = 0x10

# HTU21D-F Commands
HTU21D_TRIGGERTEMPCMD     = 0xE3  # Trigger Temperature Measurement
HTU21D_TRIGGERHUMIDITYCMD = 0xE5  # Trigger Humidity Measurement
HTU21D_WRITEUSERREGCMD    = 0xE6  # Write user register
HTU21D_READUSERCMD        = 0xE7  # Read user register
HTU21D_SOFTRESETCMD       = 0xFE  # Soft reset

HTU21D_MAX_MEASURING_TIME = 0.1   # Sec

class HTU21DException(Exception):
    pass

class HTU21DBusProtocol(object):
    def __init__(self, busnum = I2C_BUS, address = HTU21D_I2CADDR):
        self._busnum  = busnum
        self._address = address

        self._device_name = '/dev/i2c-{}'.format(self._busnum)

        self._read_handler  = None
        self._write_handler = None

    def open(self):
        self._read_handler  = io.open(self._device_name, 'rb', buffering=0)
        self._write_handler = io.open(self._device_name, 'wb', buffering=0)

        fcntl.ioctl(self._read_handler,  I2C_SLAVE, self._address)
        fcntl.ioctl(self._write_handler, I2C_SLAVE, self._address)

        time.sleep(HTU21D_MAX_MEASURING_TIME)

    def to_bytes(self, n, length=1, endianess='big'):
        s = bytearray([n])
        return s if endianess == 'big' else s[::-1]

    def send_command(self, command):
        self._write_handler.write(self.to_bytes(command))

    def read_bytes(self, len):
        msb, lsb, chsum = self._read_handler.read(len)
        if sys.version_info < (3, 0):
            # Python 2 needs to convert this from string to bytes.
            msb = ord(msb)
            lsb = ord(lsb)
            chsum = ord(chsum)
        return msb, lsb, chsum

    def close(self):
        self._read_handler.close()
        self._write_handler.close()

class HTU21D(object):
    def __init__(self, busnum=I2C_BUS, address=HTU21D_I2CADDR, mode=HTU21D_NOHOLDMASTER):
        self._logger = logging.getLogger(__name__)

        # Check that mode is valid.
        if mode not in [HTU21D_HOLDMASTER, HTU21D_NOHOLDMASTER]:
            raise ValueError('Unexpected mode value {0}.  Set mode to one of HTU21D_HOLDMASTER, HTU21D_NOHOLDMASTER'.format(mode))

        self._busnum  = busnum
        self._address = address
        self._mode    = mode

        # Create I2C device.
        self._htu_handler = HTU21DBusProtocol(self._busnum, self._address)

    def crc_check(self, msb, lsb, crc):
        remainder = ((msb << 8) | lsb) << 8
        remainder |= crc
        divsor = 0x988000

        for i in range(0, 16):
            if remainder & 1 << (23 - i):
                remainder ^= divsor
            divsor >>= 1

        if remainder == 0:
            return True
        else:
            return False

    def reset(self):
        """Reboots the sensor switching the power off and on again."""
        self._htu_handler.open()

        self._htu_handler.send_command(HTU21D_SOFTRESETCMD & 0xFF)
        time.sleep(HTU21D_MAX_MEASURING_TIME)
        self._htu_handler.close()

        return

    def read_raw_temp(self):
        """Reads the raw temperature from the sensor."""
        self._htu_handler.open()

        self._htu_handler.send_command((HTU21D_TRIGGERTEMPCMD | self._mode) & 0xFF)
        time.sleep(HTU21D_MAX_MEASURING_TIME)

        msb, lsb, chsum = self._htu_handler.read_bytes(3)

        self._htu_handler.close()

        if self.crc_check(msb, lsb, chsum) is False:
            raise HTU21DException("CRC Exception")

        raw = (msb << 8) + lsb
        raw &= 0xFFFC
        self._logger.debug('Raw temp 0x{0:X} ({1})'.format(raw & 0xFFFF, raw))

        return raw

    def read_raw_humidity(self):
        """Reads the raw relative humidity from the sensor."""
        self._htu_handler.open()

        self._htu_handler.send_command((HTU21D_TRIGGERHUMIDITYCMD | self._mode) & 0xFF)
        time.sleep(HTU21D_MAX_MEASURING_TIME)
        msb, lsb, chsum = self._htu_handler.read_bytes(3)

        self._htu_handler.close()

        if self.crc_check(msb, lsb, chsum) is False:
            raise HTU21DException("CRC Exception")

        raw = (msb << 8) + lsb
        raw &= 0xFFFC
        self._logger.debug('Raw relative humidity 0x{0:04X} ({1})'.format(raw & 0xFFFF, raw))

        return raw

    def read_temperature(self):
        """Gets the temperature in degrees celsius."""
        v_raw_temp = self.read_raw_temp()
        v_real_temp = float(v_raw_temp)/65536 * 175.72
        v_real_temp -= 46.85
        self._logger.debug('Temperature {0:.2f} C'.format(v_real_temp))
        return v_real_temp

    def read_humidity(self):
        """Gets the relative humidity."""
        v_raw_hum = self.read_raw_humidity()
        v_real_hum = float(v_raw_hum)/65536 * 125
        v_real_hum -= 6
        self._logger.debug('Relative Humidity {0:.2f} %'.format(v_real_hum))
        return v_real_hum

    def dewpoint(self, t=-100, h=-100):
        """Calculates the dew point temperature."""
        if t == -100:
            t = self.read_temperature()

        if h == -100:
            h = self.read_humidity()

        if t >= 0.0:
            a = 7.5
            b = 237.3
        else:
            a = 7.6
            b = 240.7

        sdd = 6.1078 * (10**((a*t)/(b+t)))
        dd  = (h/100*sdd)
        v   = math.log10(dd/6.1078)
        dp  = b*v/(a-v)

        self._logger.debug('Dew Point {0:.2f} C'.format(dp))
        return dp
