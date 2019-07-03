#!/usr/bin/python
# -*- coding: utf-8 -*-

# BEGIN_COPYRIGHT
#
# The MIT License (MIT)
#
# Copyright (c) 2018 Holger Kupke
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
#
# END_COPYRIGHT

from __future__ import print_function
import os, sys, time, signal
import htu21d.htu21d as htu

def idle(secs):
    os.system('setterm -cursor off')
    print()
    for i in range(secs):
        print('\rIdle: {0:>4}s'.format(secs - i), end='')
        sys.stdout.flush()
        time.sleep(1)
    print('\r', end='')
    os.system('setterm -cursor on')

def signal_handler(signum, frame):
    os.system('setterm -cursor on')

    print("\rInterrupted by user.")
    print("Bye.")

    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)

    print("Interface to Digital-Humidity-Sensor (HTU21D-F)")
    print("Copyright 2018 Holger Kupke.\n")

    sensor = htu.HTU21D()

    while True:
        print('Reading sensor...')

        t = sensor.read_temperature()
        h = sensor.read_humidity()
        d = sensor.dewpoint(t, h)

        print('Temperature: {0:0.2f}°C   '.format(t) + 'Humidity: {0:0.2f}%   '.format(h) + 'Dew Point: {0:0.2f}°C'.format(d))

        idle(10)

if __name__ == "__main__":
    main()
