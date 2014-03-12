#!/usr/bin/python
# -*- coding: utf-8 -*- 
###############################################################################
# Stefan SüAss www.sysstem.at
###############################################################################

import rpi_version, rpi_sensors
import argparse,sys
#from timeout import timeout

ports = rpi_version.getGPIOPorts()
outputs=("standard","nagios")
exitcode=0

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
###################
# Sensor Arguments
###################
    parser = argparse.ArgumentParser(description='Process args for NRPE Sensor readings')
    parser.add_argument('-o', '--output',    default='standard',      action='store', help='Define output format')
    parser.add_argument('-a', '--accuracy',  type=int,                action='store', help='Accuracy for measuring middle part of multiple measurements')
    parser.add_argument('-s', '--sensor',    required=True,           action='store', help='Determines which Sensor is being used')
    parser.add_argument('-t', '--type',                               action='store', help='Determines which Type of Sensor is being used')
    parser.add_argument('-p', '--port',      type=int,                action='store', help='Number of GPIO Pin')
    parser.add_argument('-n', '--number',    type=int,                action='store', help='Number of Sensor if more than one is connected')
    parser.add_argument(      '--trigger',   type=int,                action='store', help='Sensor Trigger GPIO Port')
    parser.add_argument(      '--echo',      type=int,                action='store', help='Sensor Echo GPIO Port')
    parser.add_argument(      '--wire1',     default=False,      action='store_true', help='Weather or not use Wiregate')
    parser.add_argument(      '--name',                               action='store', help='Name to give the sensor')
    parser.add_argument(      '--decimals',  type=int, default=1,     action='store', help='Limit output to X decimals')




###################
# Nagios Arguments
###################
    parser.add_argument('-w', '--warning',            action='append', help='Set warning value for Nagios')
    parser.add_argument('-c', '--critical',           action='append', help='Set critical value for Nagios')
    
    args = parser.parse_args()
    return args


#Checks if all requirements are given when one sensor is selected
def sanitize(args):
    if not args.output in outputs:
        raise ValueError("Wrong output! Possible:",outputs)
    if args.port != None and not args.port in ports:
        raise ValueError("Wrong GPIO port for <port>! Possible:",ports)
    if args.trigger != None and not args.trigger in ports:
        raise ValueError("Wrong GPIO port for <trigger>! Possible:",ports)
    if args.echo != None and not args.echo in ports:
        raise ValueError("Wrong GPIO port for <echo>! Possible:",ports)
    if args.output=="nagios" and not (args.warning and args.critical):
        raise AttributeError("you must specify -w and -c when output is set to nagios")
    if args.decimals != None and args.decimals < 0:
        args.decimals=args.decimals*-1
    return args

#Gets the selected sensor from rpi_sensor.py if all ports and stuff are correct
def getSensor(args):
    #If sensor got no name give it its sensortype as name
    if not args.name:
        args.name=args.sensor
    sensor=args.sensor.upper()
    if sensor=="DHT" and args.type and args.port:
        return rpi_sensors.DHT(args.name,args.type,args.port)
    elif sensor=="DS18B20":
        retdevice=None
        # getting devices from either 1wire or gpio
        if args.wire1==True:
            devices=rpi_sensors.init_onewire_devices("/media/1-wire/","28.*","/temperature")
        else:
            devices=rpi_sensors.init_onewire_devices()

        if args.number and args.number-1<len(devices):
            retdevice=devices[args.number-1]
        elif args.type:
            for device in devices:
                # using type, because it does not require INT
                if args.type in device.device_file:
                    retdevice=device
        if retdevice:
            retdevice.name=args.name
        return retdevice
    elif sensor=="BMP085":
        return rpi_sensors.BMP085(args.name)
    elif sensor=="PIR" and args.echo:
        return rpi_sensors.PIR(args.name,args.echo)
    elif sensor=="ULTRASONIC" and args.echo and args.trigger:
        return rpi_sensors.UltraSonic(args.name,args.trigger,args.echo)
    elif sensor=="RPI":
        return rpi_sensors.RPiSens(args.name)
    else:
        return None

#for none digit values
def formatValue(value,decimals):
    formatedvalue=None
    
    try:
        formatedvalue="{0:.{1}f}".format(value,decimals)
    except ValueError:
        formatedvalue=str(value)
    return formatedvalue

def setExitcode(value,warning,critical):
    global exitcode
    tempexitcode=0
    #if all are numbers it is possible to compare
    if is_number(value) and is_number(warning) and is_number(critical):
        if value > float(critical):
            tempexitcode=2
        elif value > float(warning):
            tempexitcode=1
        else:
            tempexitcode=0
    #if all are strings it is only possible to compare to exact match
    elif isinstance(value,str) and isinstance(warning,str) and isinstance(critical,str): 
        if value==critical:
            tempexitcode=2
        elif value==warning:
            tempexitcode=1
        #should be OK
        else:
            tempexitcode=0
    #if all else fails it's unknown status
    else:
        tempexitcode=3
    #highest status wins unknown>critical>warning>ok
    if tempexitcode > exitcode:
        exitcode=tempexitcode
    else:
        pass 

#a cheap one
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def main():
    outputstr=""
    outputstrnagios=" | "

    try:
        args = sanitize(GetArgs())
	sensor=getSensor(args)
        if not sensor:
            raise ValueError("Did not get sensor back")

	meas=sensor.readSensor()
        if not meas:
            raise AttributeError("No measurements found")

        #I wonder if with for loop would be better
        if args.output == "standard":
            for unit in meas:
                outputstr+="["+str(unit.timestamp)+"] "+sensor.name+" "+formatValue(unit.value,args.decimals)+" "+unit.shortname+"\n"
        elif args.output == "nagios":
            startstr=sensor.name+" has "
            outputstr+=startstr
            for unit in meas:
                if outputstr != startstr:
                    outputstr+=", "
                #Match the index of Unit in Meas to index in warnings/criticals provided
                curwarning=args.warning[meas.index(unit)]
                curcritical=args.critical[meas.index(unit)]
                outputstr+=formatValue(unit.value,args.decimals)+" "+unit.shortname
                outputstrnagios+="'"+unit.longname+"'"+"="+formatValue(unit.value,args.decimals)+";"+curwarning+";"+curcritical+" "
                setExitcode(unit.value,curwarning,curcritical)
            else:
                outputstr+=outputstrnagios

        print outputstr.strip()
        exit(exitcode)
        
    #Exceptions maybe need to be fixed for better understandig for the user 
    except (ValueError, TypeError) as e:
	#reserverd for verbose
        #print "No Device",args.sensor,"found with your parameters"
	print e
        exit(3)
    except AttributeError as e:
        print e
        exit(3)
    except IndexError as ie:
        print "You need to set "+str(len(meas))+" warning and criticals for sensor"
        #reserverd for verbose
        #print "You only provided "+str(len(args.warning))+" warnings and "+str(len(args.critical))+" critical flags"
        #print ie
        exit(3)
    except Exception as e:
	print "Unknown Exception: ",e
        exit(3)
    else:
	exit(0)
  

if __name__=="__main__":
    main()


