#!/usr/bin/python

'''
Used as a way to check IKE and IPsec for a given peer address
Usage: srx-check-vpn-peer.py [LOCAL SRX] [REMOTE VPN PEER]
Example: srx-check-vpn-peer.py 10.0.0.1 1.2.3.4
'''

from jnpr.junos import Device
from lxml import etree
import sys
import getpass

device=sys.argv[1]
peer=sys.argv[2]
user=raw_input("Username: ")
password=getpass.getpass("Password: ")

phase1="[FAILED]"
phase2="[FAILED]"

# check phase 1
dev=Device(host=device, user=user, password=password).open()
active_peers=dev.rpc.get_ike_active_peers_information(peer_address=peer)
if peer in etree.tostring(active_peers):
	phase1="[SUCCESS]"
# check phase 2
security_associations=dev.rpc.get_security_associations_information(brief=True)
for sa in security_associations.findall("ipsec-security-associations-block/ipsec-security-associations"):
	if peer in etree.tostring(sa):
		phase2="[SUCCESS]"
		break
print("Phase 1:\t\t%s" % phase1)
print("Phase 2:\t\t%s" % phase2)
dev.close()
