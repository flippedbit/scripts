#!/usr/bin/python

'''
Used to test is a source address is allowed to talk to a destination on a given port.
Would the the same as executing match-policies on the SRX devices:
show security match-policies...
This takes a single YAML file as input and then connects to the given SRX device
and runs the given tests to determine if a policy exists.

Could be put into a pipeline as testing after security policies are put in place
to confirm policies match as intended. Could also alter to not accept yaml as input
but arguments and put into a Rundeck job to give self-service policy checking.


Input YAML format
vars:
 host: 
 junos_user: 
 junos_password: 
 tests:
 	- src_zone: 
 	  src_ip:
 	  dst_zone: 
 	  dst_ip: 
 	  dst_port: 
 	  protocol: 
 	  expected_action: 
 	  expected_policy:

TODO:
needs to be finished...
the match-policy is done but needs to compare to expected-policy and expected-action
should output FAIL based on if what is expected matches what is found.
'''

from jnpr.junos import Device
import yaml
import sys

inFile=yaml.load(open(sys.argv[1]))

for vars in inFile:
	device=inFile[vars]["host"]
	username=inFile[vars]["junos_user"]
	password=inFile[vars]["junos_password"]
	
	dev=Device(host=device, user=username, password=password).open()
	
	for test in inFile[vars]["tests"]:
		testResult=dev.rpc.match_firewall_policies(from_zone=test["src_zone"], to_zone=test["dst_zone"], source_ip=test["src_ip"], source_port="23456", destination_ip=test["dst_ip"], destination_port=test["dst_port"], protocol=test["protocol"])
		policyAction=testResult.find('.//policy-information/policy-action/action-type').text
		policyName = testResult.find('.//policy-information/policy-name').text
		print("%s - %s" % (policyName, policyAction))