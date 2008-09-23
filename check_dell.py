#!/usr/bin/python                                

# Copyright 2008, Stone-IT
# Jasper Capel <capel@stone-it.com>
#                                  
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or   
# (at your option) any later version.                                 
#                                                                     
# This program is distributed in the hope that it will be useful,     
# but WITHOUT ANY WARRANTY; without even the implied warranty of      
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       
# GNU General Public License for more details.                        
#                                                                     
# You should have received a copy of the GNU General Public License   
# along with this program; if not, write to the Free Software         
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA       
# 02110-1301  USA                                                     


import sys, os, popen2
from optparse import OptionGroup, OptionParser
from elementtree.ElementTree import ElementTree

class vdisk:
        name = ""
        state = 0
        status = 0
        states = { "1": "Ready", "32": "Degraded" }
        stati = { "2": "Ok", "3": "Non-critical" } 

        def __init__(self, tree):
                self.name = tree.findtext("Name")
                self.state = tree.findtext("ObjState")
                self.status = tree.findtext("ObjStatus")

class pdisk:
        name = ""
        state = ""
        status = ""
        states = { "2": "Online", "4": "Online", "1024": "Removed", "8388608": "Rebuilding" }
        stati = { 2: "Ok", 3: "Critical" }                                                   
        progress = ""                                                                        
        vendor = ""                                                                          
        serial = ""                                                                          
        revision = ""                                                                        
        array = ""                                                                           
        length = ""                                                                          
        revision = ""                                                                        

        def __init__(self, tree):
                self.name = tree.findtext("Name")
                self.state = tree.findtext("ObjState")
                self.status = tree.findtext("ObjStatus")
                self.progress = tree.findtext("Progress")
                self.vendor = tree.findtext("Vendor")    
                self.serial = tree.findtext("DeviceSerialNumber").strip()
                self.array = tree.findtext("Array")                      
                self.length = tree.findtext("Length")                    
                self.revision = tree.findtext("Revision")                
                self.id = tree.findtext("DeviceID")                      

class tempprobe:
        status = ""
        stati = { "2": "Ok", "3": "Non-critical", "4": "Critical" }
        temperature = 0                                            
        location = ""                                              

        def __init__(self, tree):
                self.status = tree.findtext("ProbeStatus")
                self.temperature = int(tree.findtext("ProbeReading")) / 10
                self.location = tree.findtext("ProbeLocation")            

class powersupply:
        status = ""
        stati = {"1": "Unknown", "2": "Ok", "4": "Critical" }
        present = True                                       
        failed = True                                        
        aclost = True                                        

        index = 0


        def __init__(self, tree):
                self.status = tree.get("status")
                self.index = str(int(tree.get("index")) + 1)
                # Walk one down                             
                iter = tree.getchildren()                   
                for element in iter:                        
                        if element.tag == "PSState":        
                                statetree = element         

                if statetree.findtext("PSPresenceDetected") == "false":
                        self.present = False                           
                if statetree.findtext("PSFailureDetected") == "false": 
                        self.failed = False                            
                if statetree.findtext("PSACLost") == "false":          
                        self.aclost = False                            

class chassis:
        ambienttemp = ""

def getvdisks(controller="0"):
        cmd = [ "omreport", "storage", "vdisk", "controller=" + controller, "-fmt", "xml" ]
        (omstdin, omstdout) = popen2.popen2(cmd)                                           
        tree = ElementTree()                                                               
        root = tree.parse(omstdin)                                                         
        iter = root.getiterator()                                                          
        vdisks = []                                                                        
        for element in iter:                                                               
                if element.tag == "DCStorageObject":                                       
                        vdisks.append(vdisk(element))                                      
        return vdisks                                                                      

def getpdisks(controller="0"):
        cmd = [ "omreport", "storage", "pdisk", "controller=" + controller, "-fmt", "xml" ]
        (omstdin, omstdout) = popen2.popen2(cmd)                                           
        tree = ElementTree()                                                               
        root = tree.parse(omstdin)                                                         
        iter = root.getiterator()                                                          
        pdisks = []                                                                        
        for element in iter:                                                               
                if element.tag == "DCStorageObject":                                       
                        pdisks.append(pdisk(element))                                      
        return pdisks                                                                      

def gettemp():
        cmd = [ "omreport", "chassis", "temps", "-fmt", "xml" ]
        (omstdin, omstdout) = popen2.popen2(cmd)               
        tree = ElementTree()                                   
        root = tree.parse(omstdin)                             
        iter = root.getiterator()                              
        sensors = []                                           
        for element in iter:                                   
                if element.tag == "TemperatureProbe":          
                        sensors.append(tempprobe(element))     
        return sensors                                         

def getpower():
        cmd = [ "omreport", "chassis", "pwrsupplies", "-fmt", "xml" ]
        (omstdin, omstdout) = popen2.popen2(cmd)                     
        tree = ElementTree()                                         
        root = tree.parse(omstdin)                                   
        iter = root.getiterator()                                    
        status = ""                                                  
        pwrsupplies = []                                             
        for element in iter:                                         
                if element.tag == "Redundancy":                      
                        status = element.get("status")               
                        redunstatus = element.findtext("RedunStatus")
                if element.tag == "PowerSupply":                     
                        pwrsupplies.append(powersupply(element))     
        return [(status, redunstatus), pwrsupplies]                  

def do_phydisk(controller="0"):
        pdisks = getpdisks(controller)
        status = 0                    
        info = []                     
        for pdisk in pdisks:          
                if pdisk.status != "2":
                        status = 1     
                        if pdisk.state == "1024":
                                info.append("Disk %s %s (S/N: %s)" % (pdisk.id, pdisk.states[pdisk.state], pdisk.serial))

                        else:
                                info.append("State: %s, Status: %s" % (pdisk.state, pdisk.status))
                elif pdisk.state == "8388608":                                                    
                        info.append("Disk %s: %s (%s%% complete)" % (pdisk.id, pdisk.states[pdisk.state], pdisk.progress))

        if len(info) == 0:
                info.append("%s disks OK" % (len(pdisks)))
        return [status, ", ".join(info)]                  

def do_virtdisk(controller="0"):
        vdisks = getvdisks(controller)
        status = 0                    
        info = []                     
        for vdisk in vdisks:          
                if vdisk.status != "2": 
                        if status < 1:
                                status = 1
                        if vdisk.status == "4":
                                status = 2     
                if vdisk.state in vdisk.states and vdisk.status in vdisk.stati:
                        info.append("%s: %s" % (vdisk.name, vdisk.states[vdisk.state]))
                else:                                                                  
                        if status == 0:                                                
                                status = 3                                             
                        info.append("%s: State=%s Status=%s" % (vdisk.name, vdisk.state, vdisk.status))
        return [status, ", ".join(info)]                                                               

def do_temp():
        sensors = gettemp()
        status = 0         
        info = []          

        for sensor in sensors:
                if sensor.status == "3" and status < 1:
                        status = 1                     
                elif sensor.status == "4":             
                        status = 2                     
                info.append("%s: %s (%s C)" % (sensor.location, sensor.stati[sensor.status], sensor.temperature))

        return [status, ", ".join(info)]

def do_power():
        power = getpower()
        status = 0        
        powersupplies = power[1]
        info = []               
        if power[0][0] != "2":  
                status = 1      
        for powersupply in powersupplies:
                infostring = []          
                if powersupply.present:  
                        infostring.append("PRESENT")
                else:                               
                        infostring.append("NOT PRESENT")
                if powersupply.failed:                  
                        infostring.append("FAILED")     
                if powersupply.aclost:                  
                        infostring.append("AC LOST")    

                finalinfostring = ", ".join(infostring)
                info.append("PWR%s: (%s)" % (powersupply.index, finalinfostring))

        return [status, ", ".join(info)]

def do_memory():
        pass    

# command line options
validmodes = [ "memory", "phydisk", "power", "temp", "virtdisk" ]
validmodeshelp = "|".join(validmodes)
usage = "%prog [-h|-m <"+validmodeshelp+"> [-c <controllerid>]]"
parser = OptionParser(usage=usage,version="%prog 0.0.1")
parser.add_option("-m", "--mode", action="store", type="string", dest="mode", help="Mode <%s>" % validmodeshelp)

storgroup = OptionGroup(parser, "Storage options")
storgroup.add_option("-c", "--controller", action="store", type="string", dest="controller", help="Controller ID (default: 0)")

parser.add_option_group(storgroup)

# parse cmd line options
(options, args) = parser.parse_args()


if options.mode == None:
        parser.error("Missing required parameter: mode")
if options.mode not in validmodes:
        parser.error("Valid modes are: " + ", ".join(validmodes))

if options.mode == "memory":
        ret = do_memory()
elif options.mode == "phydisk":
        ret = do_phydisk()
elif options.mode == "power":
        ret = do_power()
elif options.mode == "temp":
        ret = do_temp()
elif options.mode == "virtdisk":
        ret = do_virtdisk()

print ret[1]
sys.exit(ret[0])
