#!/usr/bin/python

'''
Used to create IPSec VPN config for Juniper SRX based on JSON file generated
by Azure portal. Asks for manual input of local SRX external interface,
loopback logical interface number, security zones to allow traffic to/from
within the VPN, and routes to associate with the VPN to be advertised via BGP.
'''


import json
from sys import argv

INFILE=argv[1]
JSONDATA=json.loads(open(INFILE).read())

for config in JSONDATA:
	VPNCONFIG=[]
	zoneInterfaces=[]
	instances={}
	zones=[]
	
	externalInterface=raw_input("external interface: ")
	zones=raw_input("security zones to allow (space separated): ")
	zones=zones.split()

	loopback=raw_input("lo0 logical interface: ")
	zoneInterfaces.append("lo0.%s" % loopback)
	VPNCONFIG.append("set interfaces lo0 unit %s family inet address %s/32" % (loopback, config["vpnSiteConfiguration"]["BgpSetting"]["BgpPeeringAddress"]))
	
	for vpnConfig in config["vpnSiteConnections"]:
		ri=raw_input("VPN Name: ")
			
		VPNCONFIG.append("set security ike proposal IKE_AES256_SHA1_GROUP2_28800 authentication-method pre-shared-keys")
		VPNCONFIG.append("set security ike proposal IKE_AES256_SHA1_GROUP2_28800 dh-group group2")
		VPNCONFIG.append("set security ike proposal IKE_AES256_SHA1_GROUP2_28800 authentication-algorithm sha1")
		VPNCONFIG.append("set security ike proposal IKE_AES256_SHA1_GROUP2_28800 encryption-algorithm aes-256-cbc")
		VPNCONFIG.append("set security ike proposal IKE_AES256_SHA1_GROUP2_28800 lifetime-seconds 28800")
		
		ikepol="ike-pol-"+ri
		
		VPNCONFIG.append("set security ike policy %s mode main" % ikepol)
		VPNCONFIG.append("set security ike policy %s proposals IKE_AES256_SHA1_GROUP2_28800" % ikepol)
		VPNCONFIG.append("set security ike policy %s pre-shared-key ascii-text %s" % (ikepol, vpnConfig["connectionConfiguration"]["PSK"]))
				
		VPNCONFIG.append("set security ipsec proposal ESP_AES256_SHA1_27000 protocol esp")
		VPNCONFIG.append("set security ipsec proposal ESP_AES256_SHA1_27000 authentication-algorithm hmac-sha1-96")
		VPNCONFIG.append("set security ipsec proposal ESP_AES256_SHA1_27000 encryption-algorithm aes-256-cbc")
		VPNCONFIG.append("set security ipsec proposal ESP_AES256_SHA1_27000 lifetime-seconds 27000")
				
		VPNCONFIG.append("set security ipsec policy IPSEC_ESP_AES256_SHA1_27000_P2 perfect-forward-secrecy keys group2")
		VPNCONFIG.append("set security ipsec policy IPSEC_ESP_AES256_SHA1_27000_P2 proposals ESP_AES256_SHA1_27000")
					
		i=1
		for instance in vpnConfig["gatewayConfiguration"]["IpAddresses"]:
			int=raw_input("st0 logical interface for gateway %s: " % i)
			zoneInterfaces.append("st0.%s" % int)
			instances[instance]="st0."+int
			
			VPNCONFIG.append("set interfaces st0 unit %s description %s" % (int, ri))
			VPNCONFIG.append("set interfaces st0 unit %s family inet mtu 1436" % int)

			ikegw="gw-"+ri+str(i)
		
			VPNCONFIG.append("set security ike gateway %s ike-policy %s" % (ikegw, ikepol))
			VPNCONFIG.append("set security ike gateway %s address %s" % (ikegw, vpnConfig["gatewayConfiguration"]["IpAddresses"][instance]))
			VPNCONFIG.append("set security ike gateway %s dead-peer-detection interval 10" % ikegw)
			VPNCONFIG.append("set security ike gateway %s dead-peer-detection threshold 3" % ikegw)
			VPNCONFIG.append("set security ike gateway %s no-nat-traversal" % ikegw)
			VPNCONFIG.append("set security ike gateway %s version v2-only" % ikegw)
			VPNCONFIG.append("set security ike gateway %s external-interface %s" % (ikegw, externalInterface))
		
		
			vpn="vpn-"+ri+str(i)
		
			VPNCONFIG.append("set security ipsec vpn %s bind-interface st0.%s" % (vpn, int))
			VPNCONFIG.append("set security ipsec vpn %s df-bit clear" % vpn)
			VPNCONFIG.append("set security ipsec vpn %s ike gateway %s" % (vpn, ikegw))
			VPNCONFIG.append("set security ipsec vpn %s ike ipsec-policy IPSEC_ESP_AES256_SHA1_27000_P2" % vpn)
			VPNCONFIG.append("set security ipsec vpn %s establish-tunnels immediately" % vpn)

			i += 1
		
		for interface in zoneInterfaces:
			VPNCONFIG.append("set security zones security-zone %s interfaces %s" % (ri, interface))
		
		VPNCONFIG.append("set security policies global policy VPN-%s match source-address any" % ri)
		VPNCONFIG.append("set security policies global policy VPN-%s match destination-address any" % ri)
		VPNCONFIG.append("set security policies global policy VPN-%s match application any" % ri)
		VPNCONFIG.append("set security policies global policy VPN-%s match from-zone %s" % (ri, ri))
		VPNCONFIG.append("set security policies global policy VPN-%s match to-zone %s" % (ri, ri))
		for zone in zones:
			VPNCONFIG.append("set security policies global policy VPN-%s match from-zone %s" % (ri, zone))
			VPNCONFIG.append("set security policies global policy VPN-%s match to-zone %s" % (ri, zone))
		VPNCONFIG.append("set security policies global policy VPN-%s then permit" % ri)
		
		outRoute=raw_input("Routes to advertise (separated by spaces): ")
		outRoute=outRoute.split(" ")
		if vpnConfig["connectionConfiguration"]["IsBgpEnabled"] is True:
			for route in vpnConfig["hubConfiguration"]["ConnectedSubnets"]:
				VPNCONFIG.append("set policy-options policy-statement BGP-INBOUND-ACCEPT-%s term 1 from route-filter %s orlonger" % (ri, route))
				VPNCONFIG.append("set policy-options policy-statement BGP-INBOUND-ACCEPT-%s term 1 from protocol bgp" % ri)
				VPNCONFIG.append("set policy-options policy-statement BGP-INBOUND-ACCEPT-%s term 1 then accept" % ri)
				VPNCONFIG.append("set policy-options policy-statement BGP-INBOUND-ACCEPT-%s term default then reject" % ri)
			
			for route in outRoute:
				VPNCONFIG.append("set policy-options policy-statement BGP-OUTBOUND-ACCEPT-%s term 1 from route-filter %s orlonger" % (ri, route))
				VPNCONFIG.append("set policy-options policy-statement BGP-OUTBOUND-ACCEPT-%s term 1 then accept" % ri)
				VPNCONFIG.append("set policy-options policy-statement BGP-OUTBOUND-ACCEPT-%s term default then reject" % ri)

			
			VPNCONFIG.append("set security zones security-zone %s host-inbound-traffic protocols bgp" % ri)

			for instance in vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"]:
				VPNCONFIG.append("set protocols bgp group ebgp neighbor %s hold-time 10" % vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance])
				VPNCONFIG.append("set protocols bgp group ebgp neighbor %s peer-as %s" % (vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance], vpnConfig["gatewayConfiguration"]["BgpSetting"]["Asn"]))
				VPNCONFIG.append("set protocols bgp group ebgp neighbor %s local-as %s" % (vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance], config["vpnSiteConfiguration"]["BgpSetting"]["Asn"]))
				VPNCONFIG.append("set protocols bgp group ebgp neighbor %s import BGP-INBOUND-ACCEPT-%s" % (vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance], ri))
				VPNCONFIG.append("set protocols bgp group ebgp neighbor %s export BGP-OUTBOUND-ACCEPT-%s" % (vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance], ri))
				VPNCONFIG.append("set protocols bgp group ebgp neighbor %s multipath" % vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance])
				VPNCONFIG.append("set protocols bgp group ebgp neighbor %s multihop" % vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance])
				VPNCONFIG.append("set routing-options static route %s next-hop %s" % (vpnConfig["gatewayConfiguration"]["BgpSetting"]["BgpPeeringAddresses"][instance], instances[instance]))
		else:
			i=1
			for localRoute in outRoute:
				for remoteRoute in vpnConfig["hubConfiguration"]["ConnectedSubnets"]:
					ts = "TS"+str(i)
					VPNCONFIG.append("set security ipsec vpn %s traffic-selector %s local-ip %s" % (vpn, ts, localRoute))
					VPNCONFIG.append("set security ipsec vpn %s traffic-selector %s remote-ip %s" % (vpn, ts, remoteRoute))
					i += 1

		print("\n\n---------------------------\nDONE WITH CONFIG\n---------------------------\n\n")
		for line in VPNCONFIG:
			print line
		print("\n\n---------------------------\nDONE WITH CONFIG\n---------------------------\n\n")
