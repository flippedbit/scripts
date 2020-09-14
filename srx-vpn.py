#!/usr/bin/python

'''
Takes a JSON file as input and generates the configuration for a route-based
IPSec VPN for a Juniper SRX devices and applies the VPN to the device. It will
perform a "commit check" and rollback if that fails. Otherwise it will
perform a "commit confirmed 1" and a "commit" in case any additional
issues arise.This was thought of to stop manually configuring
VPN's although there are better ways to do this which maybe I will
write in the future.

This script will determine the next available st0 logical interface number to use.
As well as determine if the given VPN peer gateway is already an active peer.
It will also configure the routes required and check to make sure those routes do
not clash with previously configured routes on the device.

Boilerplate VPN JSON used:

{
	"username": "",
	"password": "",
	"tunnels": [
		{
			"localpeer": "",
			"env": "PROD",
			"ike-prop-auth-method": "pre-shared-keys",
			"ike-prop-group": "group2",
			"ike-prop-auth-alg": "sha-256",
			"ike-prop-enc-alg": "aes-256-cbc",
			"ike-prop-lifetime": "86400",
			"ike-pol-psk": "",
			"ike-gw-dpd-int": "10",
			"ike-gw-dpd-thresh": "3",
			"ike-gw-remote-address": "",
			"ipsec-prop-proto": "esp",
			"ipsec-prop-auth-alg": "hmac-sha-256-128",
			"ipsec-prop-enc-alg": "aes-256-cbc",
			"ipsec-prop-lifetime": "3600",
			"routes": [
				""
			]
		}
	]
}
'''

import json
import sys
import getpass
from jnpr.junos.utils.config import Config
from jnpr.junos.op.routes import RouteTable
from lxml import etree
from jnpr.junos import Device

INPUT_FILE = sys.argv[1]

def get_unit_number(UNITS, INT=0):
	if INT == 0:
		INT = int(UNITS[-1].split('.')[1]) + 1
	TEMP = "st0." + str(INT)
	if TEMP in UNITS:
		get_unit_number(UNITS, INT+1)
	else:
		return INT
	
def is_ActiveGateway(DEVICE, REMOTE_ADDRESS):
	GATEWAYS = []
	DATA = DEVICE.rpc.get_config(filter_xml='security/ike/gateway')
	for ADDRESS in DATA.findall('security/ike/gateway'):
		GATEWAYS.append(ADDRESS.find('address').text)
	if REMOTE_ADDRESS in GATEWAYS:
		return True
	else:
		return False

def is_ActiveRoute(DEVICE, REMOTE_ROUTE):
	ROUTE = RouteTable(DEVICE).get(destination=REMOTE_ROUTE)
	if "0.0.0.0/0" in ROUTE:
		return False
	else:
		return True

try:
	JSON_DATA = json.loads(open(INPUT_FILE, "r").read())
except:
	print("Could not read file %s" % INPUT_FILE)
	sys.exit()
	
USERNAME = JSON_DATA["username"]
PASSWORD = JSON_DATA["passwor"]


for TUNNEL in JSON_DATA["tunnels"]:	
	CONFIG=[]
	try:
		DEV = Device(host=TUNNEL["localpeer"], user=USERNAME, password=PASSWORD).open()
	except:
		print("Could not open connection to %s" % TUNNEL["localpeer"])
		break

	if is_ActiveGateway(DEV, TUNNEL['ike-gw-remote-address']):
		print("%s is an active tunnel on device %s, disconnecting." % (TUNNEL["ike-gw-remote-address"], TUNNEL["localpeer"]))
		break

	try:
		UNITS = []
		TUNNEL_INTERFACE = DEV.rpc.get_interface_information(terse=True, interface_name="st0")
		for U in TUNNEL_INTERFACE.findall("physical-interface/logical-interface"):
			UNITS.append(U.find('name').text)
		UNIT = get_unit_number(UNITS)
	except:
		UNIT = 0
		
	IKE_PROP_NAME = TUNNEL['ike-prop-auth-alg']+"-"+TUNNEL['ike-prop-enc-alg']+"-"+TUNNEL['ike-prop-group']+"-"+TUNNEL['ike-prop-lifetime']
	IKE_PROP_NAME = IKE_PROP_NAME.upper()
		
	CONFIG.append('set security ike proposal {} authentication-method {}'.format(IKE_PROP_NAME, TUNNEL['ike-prop-auth-method']))
	CONFIG.append('set security ike proposal {} dh-group {}'.format(IKE_PROP_NAME, TUNNEL['ike-prop-group']))
	CONFIG.append('set security ike proposal {} authentication-algorithm {}'.format(IKE_PROP_NAME, TUNNEL['ike-prop-auth-alg']))
	CONFIG.append('set security ike proposal {} encryption-algorithm {}'.format(IKE_PROP_NAME, TUNNEL['ike-prop-enc-alg']))
	CONFIG.append('set security ike proposal {} lifetime-seconds {}'.format(IKE_PROP_NAME, TUNNEL['ike-prop-lifetime']))
	
	IKE_POL_NAME = TUNNEL['ike-gw-remote-address'].replace('.','_')
	IKE_POL_NAME = IKE_POL_NAME.upper()
	
	CONFIG.append('set security ike policy {} mode main'.format(IKE_POL_NAME))
	CONFIG.append('set security ike policy {} proposals {}'.format(IKE_POL_NAME, IKE_PROP_NAME))
	if "pre-shared-keys" in TUNNEL['ike-prop-auth-method']:
		CONFIG.append('set security ike policy {} pre-shared-key ascii-text {}'.format(IKE_POL_NAME, TUNNEL['ike-pol-psk']))
	
	IKE_GW_NAME = "gw-"+TUNNEL['ike-gw-remote-address'].replace('.','_')
	IKE_GW_NAME = IKE_GW_NAME.upper()
	
	CONFIG.append('set security ike gateway {} ike-policy {}'.format(IKE_GW_NAME, IKE_POL_NAME))
	CONFIG.append('set security ike gateway {} external-interface reth0.100'.format(IKE_GW_NAME))
	CONFIG.append('set security ike gateway {} address {}'.format(IKE_GW_NAME, TUNNEL['ike-gw-remote-address']))
	if TUNNEL['ike-gw-dpd-int']:
		CONFIG.append('set security ike gateway {} dead-peer-detection interval {}'.format(IKE_GW_NAME, TUNNEL['ike-gw-dpd-int']))
	if TUNNEL['ike-gw-dpd-thresh']:
		CONFIG.append('set security ike gateway {} dead-peer-detection threshold {}'.format(IKE_GW_NAME, TUNNEL['ike-gw-dpd-thresh']))

	IPSEC_PROP_NAME = TUNNEL['ipsec-prop-proto']+"-"+TUNNEL['ipsec-prop-auth-alg']+"-"+TUNNEL['ipsec-prop-enc-alg']+"-"+TUNNEL['ipsec-prop-lifetime']
	IPSEC_PROP_NAME = IPSEC_PROP_NAME.upper()
	
	CONFIG.append('set security ipsec proposal {} protocol {}'.format(IPSEC_PROP_NAME, TUNNEL['ipsec-prop-proto']))
	CONFIG.append('set security ipsec proposal {} authentication-algorithm {}'.format(IPSEC_PROP_NAME, TUNNEL['ipsec-prop-auth-alg']))
	CONFIG.append('set security ipsec proposal {} encryption-algorithm {}'.format(IPSEC_PROP_NAME, TUNNEL['ipsec-prop-enc-alg']))
	CONFIG.append('set security ipsec proposal {} lifetime-seconds {}'.format(IPSEC_PROP_NAME, TUNNEL['ipsec-prop-lifetime']))
	
	IPSEC_POL_NAME = TUNNEL['ipsec-prop-proto']+"-"+TUNNEL['ipsec-prop-auth-alg']+"-"+TUNNEL['ipsec-prop-enc-alg']+"-"+TUNNEL['ipsec-prop-lifetime']
	IPSEC_POL_NAME = IPSEC_POL_NAME.upper()
	
	CONFIG.append('set security ipsec policy {} proposals {}'.format(IPSEC_POL_NAME, IPSEC_PROP_NAME))
	
	CONFIG.append('set interfaces st0 unit {} family inet'.format(UNIT))
	
	CONFIG.append('set security ipsec vpn vpn-{} bind-interface st0.{}'.format(TUNNEL['ike-gw-remote-address'], UNIT))
	CONFIG.append('set security ipsec vpn vpn-{} df-bit clear'.format(TUNNEL['ike-gw-remote-address']))
	CONFIG.append('set security ipsec vpn vpn-{} ike gateway {}'.format(TUNNEL['ike-gw-remote-address'], IKE_GW_NAME))
	CONFIG.append('set security ipsec vpn vpn-{} ike ipsec-policy {}'.format(TUNNEL['ike-gw-remote-address'], IPSEC_POL_NAME))
	CONFIG.append('set security ipsec vpn vpn-{} establish-tunnels immediately'.format(TUNNEL['ike-gw-remote-address']))

	CONFIG.append('set security zones security-zone vpn-{} interfaces st0.{}'.format(TUNNEL['ike-gw-remote-address'].replace('.','_'), UNIT))
	CONFIG.append('set security zones security-zone vpn-{} host-inbound-traffic system-services ike'.format(TUNNEL['ike-gw-remote-address'].replace('.','_')))
	CONFIG.append('set security zones security-zone vpn-{} host-inbound-traffic system-services ping'.format(TUNNEL['ike-gw-remote-address'].replace('.','_')))
	CONFIG.append('set security zones security-zone vpn-{} host-inbound-traffic system-services traceroute'.format(TUNNEL['ike-gw-remote-address'].replace('.','_')))
	
	CONFIG.append('set security policies global policy vpn-{} match from-zone [ vpn-{} {} ]'.format(TUNNEL['ike-gw-remote-address'].replace('.','_'), TUNNEL['ike-gw-remote-address'].replace('.','_'), TUNNEL['env']))
	CONFIG.append('set security policies global policy vpn-{} match to-zone [ vpn-{} {} ]'.format(TUNNEL['ike-gw-remote-address'].replace('.','_'), TUNNEL['ike-gw-remote-address'].replace('.','_'), TUNNEL['env']))
	CONFIG.append('set security policies global policy vpn-{} match source-address any'.format(TUNNEL['ike-gw-remote-address'].replace('.','_')))
	CONFIG.append('set security policies global policy vpn-{} match destination-address any'.format(TUNNEL['ike-gw-remote-address'].replace('.','_')))
	CONFIG.append('set security policies global policy vpn-{} match application any'.format(TUNNEL['ike-gw-remote-address'].replace('.','_')))
	CONFIG.append('set security policies global policy vpn-{} then permit'.format(TUNNEL['ike-gw-remote-address'].replace('.','_')))

	for ROUTE in TUNNEL['routes']:
		if is_ActiveRoute(DEVICE=DEV, REMOTE_ROUTE=ROUTE):
			print "\nWARNING: %s is an active route on %s, not adding route and moving on." % (ROUTE, TUNNEL['localpeer'])
		else:
			CONFIG.append('set routing-options static route {} next-hop st0.{}'.format(ROUTE, UNIT))

	print "Loading the following config:"
	CFG = Config(DEV, mode='private')
	for LINE in CONFIG:
		print LINE
		try:
			CFG.load(LINE, format='set')
		except:
			print "WARNING: Error loading config, rolling back"
			CFG.rollback(0)
			break

	print "DIFF:"
	CFG.pdiff()

	try:
		CFG.commit_check()
		print "Commit check succeeded."
	except:
		print "Commit check failed, rolling back."
		CFG.rollback(0)

	print "Performing commit confirmed with 1 minute interval."
	CFG.commit(confirmed=1)
	
	print "Performing final commit."
	CFG.commit()

	print "Closing session"
	DEV.close()