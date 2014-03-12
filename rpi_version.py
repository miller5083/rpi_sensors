#!/usr/bin/python
# -*- coding: utf-8 -*- 
################################################
# Stefan Süss - www.sysstem.at
################################################

# Listmodel from http://elinux.org/RPi_HardwareHistory
class BoardRevision(object):
        def __init__(self,revision,releasedate,model,pcbrevision,memory,notes):
            self.revision=revision
            self.releasedate=releasedate
            self.model=model
            self.pcbrevision=pcbrevision
            self.memory=memory
            self.notes=notes

#http://elinux.org/RPi_Low-level_peripherals#GPIO_hardware_hacking
pcb_r1_gpio_ports= (0,1,4,7,8,9,10,11,14,15,17,18,21,22,23,24,25)
pcb_r2_gpio_ports= (2,3,4,7,8,9,10,11,14,15,17,18,22,23,24,25,27,28,29,30,31)            
            
# Listcontent from http://elinux.org/RPi_HardwareHistory
boardrevisionlist=[]
boardrevisionlist.append(BoardRevision("Beta","Q1 2012","B (Beta)","unknown",256000000,"Beta Board"))
boardrevisionlist.append(BoardRevision(0x0002,"Q1 2012","B",1.0,256000000,""))
boardrevisionlist.append(BoardRevision(0x0003,"Q3 2012","B (ECN0001)",1.0,256000000,"Fuses mod and D14 removed"))
boardrevisionlist.append(BoardRevision(0x0004,"Q3 2012","B",2.0,256000000,"(Mfg by Sony)"))
boardrevisionlist.append(BoardRevision(0x0005,"Q4 2012","B",2.0,256000000,"(Mfg by Qisda)"))
boardrevisionlist.append(BoardRevision(0x0006,"Q4 2012","B",2.0,256000000,"(Mfg by Egoman)"))
boardrevisionlist.append(BoardRevision(0x0007,"Q1 2013","A",2.0,256000000,"(Mfg by Egoman)"))
boardrevisionlist.append(BoardRevision(0x0008,"Q1 2013","A",2.0,256000000,"(Mfg by Sony)"))
boardrevisionlist.append(BoardRevision(0x0009,"Q1 2013","A",2.0,256000000,"(Mfg by Qisda)"))
boardrevisionlist.append(BoardRevision(0x000d,"Q4 2012","B",2.0,512000000,"(Mfg by Egoman)"))
boardrevisionlist.append(BoardRevision(0x000e,"Q4 2012","B",2.0,512000000,"(Mfg by Sony)"))
boardrevisionlist.append(BoardRevision(0x000f,"Q4 2012","B",2.0,512000000,"(Mfg by Qisda)"))

def getRevision():
    revisionstring="Revision"
    revision="unknown BoardRevision"
    with open("/proc/cpuinfo","r") as file:
        for line in file.readlines():
            if line.find(revisionstring)!=-1:
                revision="0x"+line.split(":")[1][1:-1]           
    return revision

def getBoardRevision(revision=getRevision()):
    try:
        #only check the last 2 Bytes for revision (ignore overvoltage indicator)
        #http://elinux.org/RPi_HardwareHistory
        revision=int(revision,16)&0xFFFF
    except ValueError:
        revision=revision
    for boardrevision in boardrevisionlist:
        if revision == boardrevision.revision:
            return boardrevision
    return "unknown BoardRevision"

def getGPIOPorts():
    rpi=getBoardRevision()
    try:
        if rpi.pcbrevision == 1.0:
            return pcb_r1_gpio_ports
        if rpi.pcbrevision == 2.0:
            return pcb_r2_gpio_ports
        else:
            return ()
    except AttributeError:
        return ()
        
def hasBeenOverVolted():
    ovvalue=0x1000000
    try:
        ov=int(getRevision(),16)&ovvalue
        if ov==ovvalue:
            return 1
        else:
            return 0
    #could not determine due to error in reading Revision
    except ValueError:
        return -1
        
