#!/bin/bash
set -m

DEPLOYS=()

while getopts hn:a:t: opt; do
	case $opt in
		a) app=$OPTARG
		;;
		n) namespace=$OPTARG
		;;
		t) timeout="$OPTARG"
		;;
		h) echo
		   echo "Quick chaos within Kubernetes cluster.
Scales down an app's deployment/statefulset and then deletes all other pods to check any dependancies.
It will wait for an aloted amount of time (default=70s)
watching as pods come up before scaling the deployment back up.
If no app label is given it will cycle through each app, scaling it down
and them deleting all other pods."
		   echo
		   echo "Flags:"
		   echo "-a: app label"
		   echo "-n: namespace (default=default)"
		   echo "-t: timeout (default=70)"
		   echo
		   echo "Example:"
		   echo "$0 -n default -a frontend -t 120"
		   exit 0
	esac
done

if [[ -z $namespace ]] ; then
	namespace="default"
fi
if [[ -z $timeout ]] ; then
	timeout="70"
fi
if [[ -z $app ]] ; then
	for i in $(kubectl get sts,deploy -n ${namespace} | tail -n +2 | awk '{print $1":"$2}') ; do
		DEPLOYS+=(${i})
	done
else
	for i in $(kubectl get sts,deploy -n ${namespace} -l app=${app} | tail -n +2 | awk '{print $1":"$2}') ; do
		DEPLOYS+=(${i})
	done
fi

for d in ${DEPLOYS[@]}
do
	name=$(echo ${d} | tr ':' ' ' | awk '{print $1}')
	desired=$(echo ${d} | tr ':' ' ' | awk '{print $2}')
	
	echo "//****************************"
	echo "/ Name: ${name}"
	echo "/ Desired Replicas: ${desired}"
	echo "//****************************"

	
	read -p "Scale down ${name}? (y/n) " user_break
	read -p "Kill all other pods? (y/n)" kill_pods
	if [[ "${user_break}" != "y" ]] ; then
		continue
	fi
	date && kubectl scale ${name} -n ${namespace} --replicas=0

	if [[ "${kill_pods}" == "y" ]] ; then
		kubectl delete po --all -n ${namespace}
	fi
	
	watch -d "kubectl get po -n ${namespace} | grep \"0/1\" | grep -v \"Completed\"" &
	PID=$(ps | grep watch | awk '{print $1}')
	sleep ${timeout} && echo "killing ${PID}" && kill ${PID} &
	fg %+

	back_up="n"
	while [ "${back_up}" != "y" ]
	do
		read -p "Scale back up? (y/n) " back_up
	done
	date && kubectl scale ${name} -n ${namespace} --replicas=${desired}
done