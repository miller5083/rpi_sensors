#!/usr/bin/python
# -*- coding: utf-8 -*- 
###############################################################################
# Stefan Süwww.sysstem.at
# rpi_sensors.py - Version 0.1
###############################################################################
# This script tries to combine all the known methods to read sensors on the RPI
# Currently supported Sensors: DHT11, DHT22, AM2302
#                              DS18B20 with direct GPIO and WireGate DR9490R
#                              HC-SR04 (Ultrasonic Sensor)
#                              BMP085 (Temperate, Preasure, Altitude)
#                              PIR
###############################################################################
# Parts and Modules from
# -Adafruit Industries - www.adafruit.com
# -Matt Hawkins - www.raspberrypi-spy.co.uk
###############################################################################
# requirements: python-smbus, python-dev
# requirements for DHT: Adafruit_DHT binary (from their website)
# requirements for BMP085: Adafruit_BMP085 (from their website)
# requirements for WireGate DS9490R: owfs-fuse (apt-get install)
# install WireGate: mkdir /media/1-wire && owfs --allow_other -u /media/1-wire
###############################################################################
# required modules:
# snd-bcm2835, i2c-dev, i2c-bcm2708, spi_bcm2708, w1-gpio, w1-therm
###############################################################################

import subprocess,glob,time,datetime
import RPi.GPIO as GPIO
from Adafruit_BMP085 import BMP085 as ADA_BMP085
from timeout import timeout

GPIO.setmode(GPIO.BCM)


# MeasurementType is to store a Measurement with a value, names, timestamp and basetype of measurement (e.g. meter)
# the basetype is used for future release for conversion. conversion rate also needed

class MeasurementType(object):
    def __init__(self,value,shortcode,longname=None,shortname=None,mtype=None):
        self.value=value
	self.shortcode=shortcode
        self.timestamp=datetime.datetime.now()
        if (longname and shortname and mtype):
            self.longname=longname
            self.shortname=shortname
            self.mtype=mtype

# property is used to only give a shortcode while programming and automatically setting the names and types
# it's for internal usage but it's no problem if a user would see it
    @property
    def shortcode(self):
         return self._shortcode
    @shortcode.setter
    def shortcode(self,shortcode):
        self._shortcode=shortcode
        if (shortcode == "dc"):
            self.longname="degree Celsius"
            self.shortname="o C"
            #self.shortname="\xb0C"
            self.mtype="t"
        elif (shortcode == "df"):
            self.longname="degree Fahrenheit"
            self.shortname="o F"
            #self.shortname="\xb0F"
            self.mtype="t"
        elif (shortcode == "k"):
            self.longname="Kelvin"
            self.shortname="K"
            self.mtype="t"
        elif (shortcode == "h"):
            self.longname="percent humidity"
            self.shortname="%H"
            self.mtype="h"
        elif (shortcode == "hpa"):
            self.longname="hecto Pascal"
            self.shortname="hPa"
            self.mtype="p"
        elif (shortcode == "msea"):
            self.longname="meter sealevel"
            self.shortname="m"
            self.mtype="m"
        elif (shortcode == "cm"):
            self.longname="centi meter"
            self.shortname="cm"
            self.mtype="m"
        elif (shortcode == "md"):
            self.longname="motion detected"
            self.shortname="motion"
            self.mtype="b"
        elif (shortcode == "mhz"):
            self.longname="Mega Hertz"
            self.shortname="MHz"
            #1 Hertz= 1*s^-1. s=second
            self.mtype="s"
        elif (shortcode == "v"):
            self.longname="Volt"
            self.shortname="V"
            self.mtype="v"
        else:
            self.longname="undefined longname"
            self.shortname="undefined shortname"
            self.mtype="undefined"

    def __str__(self):
        return str(self.value)+" "+self.shortname

#better use of conversions would be to calculate back to base type and afterwards to the desired type
# e.g. if temp is given in F it should be converted to K and than to e.g. C
    def convertToFahrenheit(self):
        if (self.shortcode=="dc"):
            self.value=self.value*9.0/5.0 + 32
            self.shortcode="df"
        elif (self.shortcode=="k"):
            self.value=(self.value-273.15)*9.0/5.0 + 32
            self.shortcode="df"
        else:
            pass

    def convertToCelsius(self):
        if (self.shortcode=="df"):
            self.value=(self.value -32)/ 9.0 * 5.0
            self.shortcode="dc"
        elif (self.shortcode=="k"):
            self.value=self.value-273.15
            self.shortcode="dc"
        else:
            pass

    def convertToKelvin(self):
        if (self.shortcode=="dc"):
            self.value+=273.15
            self.shortcode="k"
        elif (self.shortcode=="df"):
            self.value=(self.value -32)/ 9.0 * 5.0+273.15
            self.shortcode="k"
        else:
            pass

#Base sensor with Name and function to read measurements
class Sensor(object):
    def __init__(self,name):
        self.name=name
    def readSensor(self):
        pass

#RPi sensors: mhz, govener, temp, voltage
class RPiSens(Sensor):
    def __init__(self,name=None):
        file="/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"
        if name==None:
            with open(file, 'r') as f:
                self.name=f.readline()
        else:
            self.name=name
    @timeout()
    def readSensor(self):
        #return [MeasurementType(self.read_frequency(),"mhz"),MeasurementType(self.read_governor(),"gov","Govener","Gov.","gov"),MeasurementType(self.read_temp(),"dc"),MeasurementType(self.read_volts(),"v")]
        return [MeasurementType(self.read_frequency(),"mhz"),MeasurementType(self.read_temp(),"dc"),MeasurementType(self.read_volts(),"v")]

    def read_frequency(self,file="/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq"):
        with open(file, 'r') as f:
            freq = f.readline()
        return float(freq)/1000
    def read_governor(self,file="/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"):
        with open(file, 'r') as f:
            #Strip is needed because otherwise it would have an \n at the end
            gov = f.readline().strip()
        return gov
    def read_temp(self,file="/sys/class/thermal/thermal_zone0/temp"):
        with open(file, 'r') as f:
            line = f.readline()
        return float(line)/1000

    def read_volts(self):
        args = ("/usr/bin/vcgencmd","measure_volts")
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        lines = popen.stdout.readline()
        return float(lines.split("=")[1].split("V")[0])

class DHT(Sensor):
    def __init__(self,name,type,read_port):
        Sensor.__init__(self,name)
        self.type=type
        self.read_port=read_port

    @timeout()
    def readSensor(self):
        measurements=self.read_temp_hum()
        if measurements != None:
            return [MeasurementType(measurements[0],"dc"),MeasurementType(measurements[1],"h")]
        else:
            return []
    def read_raw(self,dhtdriver):
        args = ("sudo",dhtdriver, str(self.type), str(self.read_port))
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        lines=popen.communicate()
        #return of communicate is tople(stdoutdata, stderrdata)
        lines=lines[0].strip().split("\n")
        return lines

    def read_temp_hum(self,dhtdriver="/etc/nagios/nrpe.d/Adafruit_DHT"):
        lines = self.read_raw(dhtdriver)
        
        #check if DHT is connected
        if len(lines)<1:
           print "no such file or not enough rights"
           return None
        if len(lines)==1:
           print lines
           return None
        dht_check=lines[1].find("Data (0): 0x0 0x0 0x0 0x0 0x0")
        if dht_check != -1:
           return None
        else:
            while len(lines) != 3:
               time.sleep(0.3)
               lines = self.read_raw(dhtdriver)
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
        return None
       
class OneWire(Sensor):
    def __init__(self,name,type,device_file,read_port=None):
        Sensor.__init__(self,name)
        self.type=type
        self.read_port=read_port
        self.device_file=device_file

    @timeout()
    def readSensor(self):
        return [MeasurementType(self.read_temp(),"dc")]

    def set_name(self,name):
        self.name=name

    def read_temp_raw(self):
        f = open(self.device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines
     
    def read_temp(self):
        lines = self.read_temp_raw()
        if len(lines)==1:
            return float(lines[0])
        else:
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
        Sensor.__init__(self,name)
        self.trigger=trigger
        self.echo=echo
        self.ultrasonic_setup()
        
    def ultrasonic_setup(self):
        GPIO.setup(self.trigger,GPIO.OUT)
        GPIO.setup(self.echo,GPIO.IN)
        GPIO.output(self.trigger, False)

    def __del__(self):
        cleanup()

    @timeout()
    def readSensor(self):
        return [MeasurementType(self.measure_distance(),"cm")]
    
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
        
class BMP085(Sensor,ADA_BMP085):
    def __init__(self,name,address=0x77,mode=1,debug=False):
        Sensor.__init__(self,name)
        ADA_BMP085.__init__(self,address, mode, debug)

    @timeout()
    def readSensor(self):
        return [MeasurementType(self.readTemperature(),"dc"),MeasurementType(float(self.readPressure())/100,"hpa"),MeasurementType(self.readAltitude(),"msea")]
        
class PIR(Sensor):
    def __init__(self,name,echo):
        Sensor.__init__(self,name)
        self.echo=echo
        self.__previous_state=0
	self.__current_state=0
	GPIO.setup(self.echo,GPIO.IN)
    
    @timeout()
    def readSensor(self):
        return [MeasurementType(self.isMotion(),"md")]
    
    def isMotion(self):
        self.__current_state=GPIO.input(self.echo)
        if self.__current_state==1 and self.__previous_state==0:
            self.__previous_state=1
            return True
        elif self.__current_state==0 and self.__previous_state==1:
                self.__previous_state=0
        return False


#Measure Average is for future release. It's for measuring multiple times, sort measurements, cut the two outer thirds and make an average of the last third
#I think this is like in ski jumping but they only cut the highest and lowest  
def measure_average(measurement_function,accuracy,sleeptime=0):

        all=0     #all together
        measurement_now=0

        measurements=[]
        #collect all measurements
        for round in range(0,accuracy):
            #measure
            measurement_now=measurement_function()
            #add to list
            measurements.append(measurement_now)
            #add to total measurement
            all+=measurement_now
            time.sleep(sleeptime)
        #when all data collected sort the list
        measurements.sort()
        #accuracy method only makes sense from 4 measurements
        if accuracy > 3:
            #cut the collected data in 3 parts: low-mid-high (the count of mid data is always >= low or high)
            for round in range(0,int(accuracy/3)):
                #remove last item
                pop=measurements.pop()
                #remove high data from collected data
                all-=pop
                #remove first item
                pop=measurements.pop(0)
                #remove low data from collected data
                all-=pop
        #return average of collected data where low and high data was cut
        try:
            return all/(accuracy-2*int(accuracy/3))
        except TypeError, te:
            return None

#same here but it's for multiple measurements.
#needs improvment for non digit values
#needs renaming for lists instead of tuples
#maybe this will go to a single function
def measure_average_tuples(measurement_function,accuracy,sleeptime=0):
    measurement_now=0

    measurements=[]
    #collect all measurements
    for round in range(0,accuracy):
        #measure
        measurement_now=measurement_function()
        #add to list
        measurements.append(measurement_now)
        time.sleep(sleeptime)
    #when all data collected sort the list
    measurements.sort()
    #accuracy method only makes sense from 4 measurements
    if accuracy > 3:
        #cut the collected data in 3 parts: low-mid-high (the count of mid data is always >= low or high)
        for round in range(0,int(accuracy/3)):
            #remove last item
            measurements.pop()
            #remove first item
            measurements.pop(0)
    #return average of collected data where low and high data was cut
    #http://stackoverflow.com/questions/12412546/average-tuple-of-tuples
    try:
        return tuple(map(lambda y: sum(y)/float(len(y)),zip(*measurements)))
    except TypeError, te:
        return None

#cleanup GPIO ports. currently only needed for ultrasonic sensor
def cleanup():
    GPIO.cleanup()    

#gets all 1-wire devices.
#currently only temperature (28*) devices are known to me
def init_onewire_devices(base_dir="/sys/bus/w1/devices/",sens_dir="28*",sub_dir="/w1_slave"):
    onewire_devices=[]
    for device in get_onewire_devices(base_dir,sens_dir,sub_dir):
        onewire_devices.append(OneWire("DS18B20","Temperature",device))
    return onewire_devices

#getting the OS files of the 1-wire devices
def get_onewire_devices(base_dir,sens_dir,sub_dir):
    device_files=[]
    for device_folder in glob.glob(base_dir + sens_dir):
        device_files.append(device_folder + sub_dir)
    return device_files
