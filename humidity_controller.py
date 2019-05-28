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
import Adafruit_DHT
import sqlite3
import webpage.app as app
import multiprocessing as mp

HUMIDITY_SETPOINT = 90

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
    curs.execute("SELECT * FROM temps")
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
    # Parse command line parameters.
    #sensor_args = { '11': Adafruit_DHT.DHT11,
    #                '22': Adafruit_DHT.DHT22,
    #                '2302': Adafruit_DHT.AM2302 }
    #if len(sys.argv) == 3 and sys.argv[1] in sensor_args:
    #    sensor = sensor_args[sys.argv[1]]
    #    pin = sys.argv[2]
    #else:
    #    print('Usage: sudo ./Adafruit_DHT.py [11|22|2302] <GPIO pin number>')
    #    print('Example: sudo ./Adafruit_DHT.py 2302 4 - Read from an AM2302 connected to GPIO pin #4')
    #    sys.exit(1)

    # We hard code the pins for our humidity controller application.
    sensor = Adafruit_DHT.DHT11
    pin = 4

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
            # Try to grab a sensor reading.  Use the read_retry method which will retry up
            # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
              humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

              if humidity is not None and temperature is not None and humidity < 110:
                  print('Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(temperature, humidity))
                  add_data(temperature, humidity, HUMIDITY_SETPOINT, dbconn, curs)
                  last_read_time = time.time()
              else:
                  print('Failed to get reading. Try again!')

              if humidity > HUMIDITY_SETPOINT + HYSTERESIS/2:
                relay_off()
              if humidity < HUMIDITY_SETPOINT - HYSTERESIS/2:
                relay_on()

    except KeyboardInterrupt:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
