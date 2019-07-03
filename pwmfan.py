import wiringpi
import time
import sys

wiringpi.pwmSetMode(0) # PWM_MODE_MS = 0

wiringpi.wiringPiSetupGpio()

wiringpi.pinMode(18, 2)      # pwm only works on GPIO port 18

wiringpi.pwmSetClock(6)  # this parameters correspond to 25kHz
wiringpi.pwmSetRange(128)

wiringpi.pwmWrite(18, 0)   # minimum RPM
time.sleep(1)


if len(sys.argv) < 2:
  print("Not enough args. Pass the period in seconds and the fan on duty cycle from 0-100 to run. Now exiting.")
  sys.exit()

period = int(sys.argv[1])
duty = int(sys.argv[2])


while True:
  time.sleep((100 - duty) / 100.0 * period)
  wiringpi.pwmWrite(18, 350)  # maximum RPM
  time.sleep(duty/100.0 * period)
  wiringpi.pwmWrite(18, 0)


#for i in range(102):
#  wiringpi.pwmWrite(18, i*10)  # maximum RPM
#  time.sleep(0.4)
#  print i*10

wiringpi.pwmWrite(18, 0)
