#! /bin/bash

# rolling delete pods from nodes
# simulate a rolling upgrade of kops cluster
# if no context is given as parameter uses current-context

if [[ ! -z $1 ]] ; then
    CONTEXT=$1
else
	CONTEXT=$(kubectl config current-context)
fi

echo "##########"
echo "Rolling nodes in cluster: ${CONTEXT}"
echo "Start time:"
date
echo "##########"
# cycle through configured InstanceGroups, excluding master
for ig in $( kubectl --context ${CONTEXT} get no -L kops.k8s.io/instancegroup | grep -v master | tail -n +2 | awk '{print $6}' | sort | uniq ) ;
do 
	echo "--- ${ig}"
    # cyclde through nodes in InstanceGroup
	for node in $( kubectl --context ${CONTEXT} get no -l kops.k8s.io/instancegroup=${ig} | tail -n +2 | awk '{print $1}' ) ;
    do 
		echo "----- ${node}"
        # cycle through pods on Node
		for i in $( kubectl --context ${CONTEXT} get po --all-namespaces -o jsonpath='{range.items[*]}{@.metadata.namespace}{":"}{@.metadata.name}{" "}{@.spec.nodeName}{"\n"}' | grep ${node} | awk '{print $1}' ) ;
        do 
			ns=$(echo ${i} | tr ":" " " | awk '{print $1}') 
			pod=$(echo ${i} | tr ":" " " | awk '{print $2}')
			kubectl --context ${CONTEXT} delete pod -n ${ns} ${pod} &
		done
	done
done

echo "##########"
echo "End time:"
date
echo "##########"