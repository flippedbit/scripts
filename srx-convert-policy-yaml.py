#!/usr/bin/python

'''
Connects to a Juniper SRX and gathers all configured security policies
then converts those policies to a YAML format and outputs them to a file.
This would be used in order to get an existing Juniper SRX config into code
to possibly be used with Ansible or another config-as-code deployment app.

Usage: srx-convert-policy-yaml.py [SRX ADDRESS]

Example: srx-convert-policy-yaml.py 10.0.0.1

Output filename: 10.0.0.1.yaml
Output file structure:
security_policies:
- from: <FROM SECURITY ZONE>
  to: <TO SEUCIRYT ZONE>
  policies:
    <POLICY_1>:
      application: [<APPLICATION LIST>]
      destination_address: [<DESTINATION LIST>]
      source_address: [<SOURCE LIST>]
    <POLICY_2>:
      application: [<APPLICATION LIST>]
      destination_address: [<DESTINATION LIST>]
      source_address: [<SOURCE LIST>]
'''

from jnpr.junos import Device
from sys import argv
import yaml
import getpass

device=argv[1]
policies={}
yamlPolicies={"security_policies":[]}

user=raw_input("Username: ")
password=getpass.getpass("Password: ")

try:
	dev=Device(host=device, user=user, password=password).open()
	print("Connected to device %s" % device)
except:
	print("Could not connect to device %s" % device)
	quit()

try:
	print("- Gathering security policies")
	policyList=dev.rpc.get_firewall_policies()
except:
	print("!!! Could not gather security policies !!!")
	quit()
for zones in policyList.findall('.//security-context'):
	yamlPolicy={}
	yamlPolicy["from"]=zones.find('context-information/source-zone-name').text
	yamlPolicy["to"]=zones.find('context-information/destination-zone-name').text
	yamlPolicy["policies"]={}
	for policy in zones.findall('policies'):
		policyName=policy.find('policy-information/policy-name').text
		yamlPolicy["policies"][policyName]={}
		policySRC=[]
		for src in policy.findall('policy-information/source-addresses/source-address'):
			policySRC.append(src.find('address-name').text)
		policyDST=[]
		for dst in policy.findall('policy-information/destination-addresses/destination-address'):
			policyDST.append(dst.find('address-name').text)
		policyAPP=[]
		for app in policy.findall('policy-information/applications/application'):
			policyAPP.append(app.find('application-name').text)
		yamlPolicy["policies"][policyName]={"source_address":policySRC,"destination_address":policyDST,"application":policyAPP}
	yamlPolicies["security_policies"].append(yamlPolicy)

print("- Creating YAML file")
filename=device + ".yaml"
outfile=open(filename, "w")
yaml.dump(yamlPolicies,outfile)
outfile.close
dev.close()