#!/usr/bin/python
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import sys
import time
import RPi.GPIO as GPIO
import htu21d.htu21d as htu
import sqlite3
import webpage.app as app
import multiprocessing as mp

HUMIDITY_SETPOINT = 95

HYSTERESIS = 4

RELAY_PIN_BCM = 23

dbconn = sqlite3.connect('/home/pi/datalog.db')
curs = dbconn.cursor()


def add_data (temp, hum, setpoint, dbconn, curs):
    curs.execute("INSERT INTO temps values(datetime('now'),"
                 "(?), (?), (?))", (temp, hum, setpoint))
    while True:
        try:
            dbconn.commit()
            break
        except sqlite3.OperationalError:
            time.sleep(0.1)
            print("deferred")

def get_rows(curs):
    curs.execute("select * from (select * from temps order by timestamp DESC limit 1000) order by timestamp ASC;")
    rows = curs.fetchall()
    #print(rows)
    return rows

def main():
    queue = mp.Queue()
    p = mp.Process(target=app.launch_app, args=(queue,))
    p.start()


    # Set up Relay Output.
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN_BCM, GPIO.OUT)

    def relay_on():
        GPIO.output(RELAY_PIN_BCM, True)

    def relay_off():
        GPIO.output(RELAY_PIN_BCM, False)

    sensor = htu.HTU21D()

    # Signal to the outside world that the program has started.
    relay_on()
    time.sleep(2)
    relay_off()

    last_read_time = 0

    try:
        while True:
          if queue.empty():
            queue.put(get_rows(curs))

          if time.time() > last_read_time + 2:
              temperature = sensor.read_temperature()
              humidity = sensor.read_humidity()
              dewpoint = sensor.dewpoint(temperature, humidity)

              if humidity is not None and temperature is not None:
                  print('Temp={0:0.1f}*  Humidity={1:0.1f}% Dewpoint={1:0.1f}*'.format(temperature, humidity, dewpoint))
                  add_data(temperature, humidity, HUMIDITY_SETPOINT, dbconn, curs)
                  last_read_time = time.time()

              if humidity > HUMIDITY_SETPOINT + HYSTERESIS/2:
                relay_off()
              if humidity < HUMIDITY_SETPOINT - HYSTERESIS/2:
                relay_on()

    except KeyboardInterrupt:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
