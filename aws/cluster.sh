# SET OF USEFUL SNIPPETS FOR CLUSTER CREATION
# -------------------------------------------
echo "Do not run this script, ye bleedin' gobshite!"; code -n $0; exit

# ========
# CREATION
# ========

# create cluster (this will cost $)
eksctl create cluster --version 1.14 --nodegroup-name bingo --node-type t3.nano \
    --nodes 2 --nodes-min 1 --nodes-max 4 --node-ami auto --name bingo-nano

# apply kubeconfig files
kubectl apply -f kubeconfig.crawling.yaml
kubectl apply -f kubeconfig.indexing.yaml

# to use redis.conf file see:
# https://github.com/GoogleCloudPlatform/redis-docker/blob/master/4/README.md#configurations

# ==========
# NETWORKING
# ==========

# remote accessing url-map (redis) pod
kubectl expose pod url-map-pod --name url-map-6379 --type LoadBalancer --port 6379 --protocol TCP
kubectl exec -it url-map-pod -- redis-cli

# list endpoints
kubectl get ep

# probing dns server
kubectl get services kube-dns --namespace=kube-system       # check if dns service is running
kubectl run curl --image=radial/busyboxplus:curl -i --tty   # run interactive 'curl' pod
nslookup crawler-service                                    # or another service

# ==========
# MONITORING
# ==========

# local dashboard
minikube dashboard

# aws dashboard
./k8dashboard.sh

# list persistent volumes
kubectl get pv
kubectl get pvc

# =======
# CLEANUP
# =======

# delete all kubectl resources
kubectl delete daemonsets,replicasets,services,deployments,pods,rc --all

# delete all persistent volumes, volume claims, and storage classes
kubectl delete pv,pvc,sc --all
