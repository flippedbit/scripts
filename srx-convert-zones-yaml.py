#!/usr/bin/python 

'''
Connects to a Juniper SRX and gathers all configured security zones
then converts those policies to a YAML format and outputs them to a file.
This would be used in order to get an existing Juniper SRX config into code
to possibly be used with Ansible or another config-as-code deployment app.

Usage: srx-convert-zones-yaml.py [SRX ADDRESS]

Example: srx-convert-zones-yaml.py 10.0.0.1

Output filename: 10.0.0.1_zones.yaml
Output file structure:
security_zones:
  <ZONE_1>:
    flags: [ <FLAGS LIST> ]
    host_inbound_traffic:
      system-services:
        - <ZONE SYSTEM-SERVICES LIST>
      protocols:
        - <ZONE PROTOCOLS LIST>
    interfaces:
      - <INTERFACES LIST>

  <ZONE_2>:
    screen: <SCREEN NAME>
    host_inbound_traffic:
      system_services:
        - <SYSTEM-SERVICES LIST>
      protocols:
        - <PROTOCOLS LIST>
    interfaces:
      - name: <INTERFACE NAME>
        host-inbound-traffic:
          system-services:
            - <INTERFACE SYSTEM-SERVICES LIST>
'''

import yaml
from jnpr.junos.utils.config import Config
from jnpr.junos import Device
from sys import argv
import getpass

ip=argv[1]

yamlZones={"security_zones":[]}

user=raw_input("Username: ")
password=getpass.getpass("Password: ")

try:
	print("- Connecting to device")
	dev=Device(host=ip, user=user, password=password).open()
except:
	print("** Could not connect to Juniper SRX: %s" % ip)
	exit()

try:
	print("-- Gathering security zone configs")
	data=dev.rpc.get_config('security/zones')
except:
	print("** Could not gather config from %s" % ip)
	exit()
	
for zone in data.findall('security/zones/security-zone'):
	zoneName=zone.find('name').text
	zoneInfo={}
	zoneInfo[zoneName]={}
	zoneInfo[zoneName]["interfaces"]=[]
	
	if zone.find('tcp-rst') is not None:
		zoneInfo[zoneName]["flags"] = []
		zoneInfo[zoneName]["flags"].append("tcp-rst")
		
	if zone.find('host-inbound-traffic') is not None:
		zoneInfo[zoneName]["host-inbound-traffic"]={}
		
		if zone.find('host-inbound-traffic/system-services') is not None:
			zoneInfo[zoneName]["host-inbound-traffic"]["system-services"]=[]
			for service in zone.findall('host-inbound-traffic/system-services'):
				zoneInfo[zoneName]["host-inbound-traffic"]["system-services"].append(service.find('name').text)
				
		if zone.find('host-inbound-traffic/protocols') is not None:
			zoneInfo[zoneName]["host-inbound-traffic"]["protocols"]=[]
			for proto in zone.findall('host-inbound-traffic/protocols'):
				zoneInfo[zoneName]["host-inbound-traffic"]["protocols"].append(proto.find('name').text)
				
	for interface in zone.findall('interfaces'):
		if interface.find('host-inbound-traffic') is not None:
			interfaceDict={}
			interfaceDict["name"]=interface.find('name').text
			interfaceDict["host-inbound-traffic"]={}
			if interface.find('host-inbound-traffic/system-services') is not None:
				interfaceDict["host-inbound-traffic"]["system-services"]=[]
				for service in interface.findall('host-inbound-traffic/system-services'):
					interfaceDict["host-inbound-traffic"]["system-services"].append(service.find('name').text)
			if interface.find('host-inbound-traffic/protocols') is not None:
				interfaceDict["host-inbound-traffic"]["protocols"]=[]
				for proto in interface.findall('host-inbound-traffic/protoclls'):
					interfaceDict["host-inbound-traffic"]["protocols"].append(proto.find('name').text)
			zoneInfo[zoneName]["interfaces"].append(interfaceDict)
		else:
			zoneInfo[zoneName]["interfaces"].append(interface.find('name').text)
	yamlZones["security_zones"].append(zoneInfo)

print("- Disconnecting from device")
dev.close()
filename=ip + "_zones.yml"
print("- Creating YAML file: %s" % filename)
outfile=open(filename, "w")
yaml.dump(yamlZones,outfile)
outfile.close()
dev.close()
