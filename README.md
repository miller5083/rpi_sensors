
Stefan Süss
www.sysstem.at
rpi_sensors.py - Version 0.1

This script tries to combine all the known methods to read sensors on the RPI
Currently supported Sensors: DHT11, DHT22, AM2302, DS18B20 (1-wire), Ultrasonic Sensor(HR-04?)

Make sure to give the user (pi, nagios, ...) sudo-rights
example:
sudo visudo
pi ALL=(ALL) NOPASSWD: ALL
nagios ALL = NOPASSWD: /usr/bin/vcgencmd
nagios ALL = NOPASSWD: /usr/bin/python /etc/nagios/nrpe.d/rpi_sensors.py
nagios ALL = NOPASSWD: /etc/nagios/nrpe.d/Adafruit_DHT
nagios ALL = NOPASSWD: /sbin/modprobe w1-gpio
nagios ALL = NOPASSWD: /sbin/modprobe w1-therm


Parts from
-Adafruit Industries - www.adafruit.com
-Matt Hawkins - www.raspberrypi-spy.co.uk

