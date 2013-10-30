#!/usr/bin/python
# -*- coding: utf-8 -*- 
################################################
# Stefan Süss
# www.sysstem.at
# rpi_sensors.py - Version 0.1
################################################
# This script tries to combine all the known methods to read sensors on the RPI
# Currently supported Sensors: DHT11, DHT22, AM2302, DS18B20 (1-wire), Ultrasonic Sensor (HC-SR04)
# 
# Make sure to give the user (pi, nagios, ...) sudo-rights
# example:
# sudo visudo
# pi ALL=(ALL) NOPASSWD: ALL
# nagios ALL = NOPASSWD: /usr/bin/vcgencmd
# nagios ALL = NOPASSWD: /usr/bin/python /etc/nagios/nrpe.d/rpi_sensors.py
# nagios ALL = NOPASSWD: /etc/nagios/nrpe.d/Adafruit_DHT
# nagios ALL = NOPASSWD: /sbin/modprobe w1-gpio
# nagios ALL = NOPASSWD: /sbin/modprobe w1-therm
#
################################################
# Parts from
# -Adafruit Industries - www.adafruit.com
# -Matt Hawkins - www.raspberrypi-spy.co.uk
################################################

import subprocess,glob,time
import RPi.GPIO as GPIO

class LoadedModule(object):
    def __init__(self,name,size,used,by):
        self.name=name
        self.size=size
        self.used=used
        self.by=by

class Sensor(object):
    def __init__(self,name):
        self.name=name
        
class DHT(Sensor):
    def __init__(self,name,type,read_port):
        self.name=name
        self.type=type
        self.read_port=read_port
    def read_raw(self,dhtdriver="/etc/nagios/nrpe.d/Adafruit_DHT"):
        args = ("sudo",dhtdriver, self.type, self.read_port)
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        lines = popen.stdout.readlines()
        return lines

    def read_temp_hum(self):
        lines = self.read_raw()
        
        #check if DHT is connected
        dht_check=lines[1].find("Data (0): 0x0 0x0 0x0 0x0 0x0")
        if dht_check != -1:
           return "noDHT"

        while len(lines) != 3:
            time.sleep(0.5)
            lines = self.read_dht_raw()

        temp_pos = lines[2].find('Temp = ')
        hum_pos = lines[2].find('Hum = ')
        if temp_pos != -1:
            #Filter empty tuples due to double spaces in Adafruit Driver
            filtered_output=filter(None, lines[2].split(' '))
            temp_string = filtered_output[2]
            temp_c = float(temp_string)
            temp_c = round(temp_c, 3)
        if hum_pos != -1:
            hum_string = filtered_output[6]
            hum = float(hum_string)
        return temp_c, hum
       
class OneWire(Sensor):
    def __init__(self,name,type,device_file,read_port=None):
        self.name=name
        self.type=type
        self.read_port=read_port
        self.device_file=device_file
        
    def read_temp_raw(self):
        f = open(self.device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines
     
    def read_temp(self):
        lines = self.read_temp_raw(self.device_file)
        #DS18B20 sometimes give a wrong temperature of 85 deg Celsius
        while lines[0].strip()[-3:] != 'YES' or (lines[1].find('t=85')!=-1):
            time.sleep(0.2)
            lines = self.read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            return temp_c
        
class UltraSonic(Sensor):
    def __init__(self,name,trigger,echo):
        self.name=name
        self.trigger=trigger
        self.echo=echo
        
    def ultrasonic_setup(self):
        GPIO.setup(self.trigger,GPIO.OUT)
        GPIO.setup(self.echo,GPIO.IN)
        GPIO.output(self.trigger, False)
    
    #Matt Hawkins
    #http://www.raspberrypi-spy.co.uk/
    def measure_distance(self):
        GPIO.output(self.trigger, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger, False)
        start = time.time()

        while GPIO.input(self.echo)==0:
            start = time.time()

        while GPIO.input(self.echo)==1:
            stop = time.time()

        elapsed = stop-start
        distance = (elapsed * 34300)/2

        return distance
        
    def measure_average_distance(self,accuracy):
        all=0     #all together
        distance_now=0

        distance=[]
        #collect all measurements
        for round in range(0,accuracy):
            #measure
            distance_now=self.ultrasonic_measure()
            #add to list
            distance.append(distance_now)
            #add to total distance
            all+=distance_now
        #when all data collected sort the list
        distance.sort()
        #accuracy method only makes sense from 4 measurements
        if accuracy > 3:
            #cut the collected data in 3 parts: low-mid-high (the count of mid data is always >= low or high)
            for round in range(0,int(accuracy/3)):
                #remove last item
                pop=distance.pop()
                #remove high data from collected data
                all-=pop
                #remove first item
                pop=distance.pop(0)
                #remove low data from collected data
                all-=pop
        #return average of collected data where low and high data was cut
        return all/(accuracy-2*int(accuracy/3))

def init_onewire_devies():
    onewire_devices=[]
    for device in get_onewire_devices():
        onewire_devices.append=OneWire("DS18B20","Temperature",device)
    return onewire_devices
        
def get_onewire_devices(base_dir="/sys/bus/w1/devices/"):
    device_files=[]
    for device_folder in glob.glob(base_dir + '28*'):
        device_files.append(device_folder + '/w1_slave')
    return device_files
        
def getLsMod(with_header=0):
    lsmod=[]
    args=("sudo","lsmod")
    popen=subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    loaded_modules_header=popen.stdout.readline()
    for line in popen.stdout.readlines():
        columns=line.split()
        for x in range(0,4-len(columns)):
            columns.append("")
        lsmod.append(LoadedModule(columns[0],columns[1],columns[2],columns[3]))
    if with_header==1:
        return loaded_modules_header,lsmod
    else:
        return lsmod

def convert_to_fahrenheit(celsius):
    return 9.0/5.0 * celsius + 32
def convert_to_celsius(fahrenheit):
    return (fahrenheit - 32) * 5.0/9.0
def convert_to_kelvin(celsius):
    return celsius+273
