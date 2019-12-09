# Cluster Creation Walkthrough

## Versions

+ Ubuntu 18.04 LTS
+ Minikube v1.5.2 (for local deploys)
+ eksctl 0.10.2
+ kubectl v1.16
+ skaffold 1.0.1

## Creation

### Create reusable resources

```sh
# create files
code AWS_ACCESS_KEY_ID.txt && code AWS_SECRET_ACCESS_KEY.txt

# create secrets and configmaps
./create_resources.sh
```

### Create cluster

#### `Option A:` Local

```sh
minikube start --memory 4096 --cpus 2 --vm-driver=virtualbox
```

#### `Option B:` AWS (this will cost $)

```sh
eksctl create cluster --version 1.14 --nodegroup-name bingo \
    --node-type t3.small --nodes 2 --nodes-min 1 --nodes-max 10 \
    --node-ami auto --name bingo-small
```

#### Deploy with Skaffold

```sh
skaffold dev
```

## AWS Cluster Operations

### Scaling

```sh
eksctl scale nodegroup --cluster bingo-nano -n bingo -N <NEW_NUMBER_OF_NODES>
```

### Deleting

```sh
# this may take ~15min to complete
eksctl delete cluster --name=bingo-small
eksctl get clusters
```

> The cluster will now be created. You can [monitor](#Monitoring) it using a browser.

## Networking

### List available endpoints

```sh
kubectl get ep
```

### Remotely accessing URL Map (Redis) pod

```sh
kubectl expose pod urlmap-pod --name urlmap-6379 --type LoadBalancer --port 6379 --protocol TCP
kubectl exec -it urlmap-pod -- redis-cli
```

### Probing DNS Server

```sh
# check whether DNS service is running
kubectl get services kube-dns --namespace=kube-system

# run interactive 'curl' pod
kubectl run curl --image=radial/busyboxplus:curl -i --tty

# in the pod's shell, check DNS lookups
nslookup crawling-service
nslookup balancing-service
nslookup urlmap-service
```

## Monitoring

### Local dashboard

```sh
minikube dashboard
```

### AWS dashboard

```sh
./k8dashboard.sh
```

### Prometheus and Grafana

```sh
# start prometheus and grafana
kubectl apply -f kubeconfig.monitoring.yaml

# permission fix
real_user=$USER
sudo -u $real_user kubectl create clusterrolebinding permissive-binding --clusterrole=cluster-admin --user=admin --user=kubelet --group=system:serviceaccounts

# port forwarding
kubectl port-forward -n monitoring $(kubectl get pods -n monitoring --selector=app=prometheus-server --output=jsonpath="{.items..metadata.name}") 9090 &

kubectl port-forward -n monitoring $(kubectl get pods -n monitoring --selector=app=grafana --output=jsonpath="{.items..metadata.name}") 3000 &
```

## Storage

### List persistent volumes and claims

```sh
kubectl get pv
kubectl get pvc
```

## Cleanup

### Delete volatile `kubectl` resources

```sh
kubectl delete -n default daemonsets,replicasets,services,deployments,pods,rc,ing --all
```

#### `[ Danger ]` Delete **persistent data** only

```sh
# stateful sets, persistent volumes, persistent volume claims, and storage classes
kubectl delete -n default statefulsets,pv,pvc,sc,ing --all
```

#### `[ Danger ]` Delete everything created but `Secrets` and `ConfigMaps`

> Persistent data will be deleted!

```sh
kubectl delete -n default secrets,configmaps,daemonsets,replicasets,services,deployments,pods,rc,statefulsets,pv,pvc,sc,ing --all
```

---

## Other useful stuff

### Rebuilding images and running

```sh
docker build -t bingocrawler/<module>:latest .

# then push to Docker Hub
docker push bingocrawler/<module>:latest

# or run locally (not in minikube, as it will pull the image from Docker Hub)
docker run --name crawler -it bingocrawler/crawler:latest .env.local
docker run --name balancer -it bingocrawler/balancer:latest .env.local
```

### Starting interactive shell

```sh
# it might only work with "Running" containers. Check status with:
kubectl get pods

# connect to pod / container:
kubectl exec -it <POD_NAME> -- /bin/sh

# start a new "debug" pod:
kubectl run debug-pod --rm -i --tty --image alpine:latest -- /bin/sh
apk add less nano nmap curl
apk add python3
```

### Debug socket connection

```sh
# check configured ports in service and pod
kubectl get service balancing-service -o json | grep -C 3 -E "port|Port"
kubectl get pod domain-balancer-pod -o json | grep -C 3 -E "port|Port"

# start a new "debug" pod:
kubectl run debug-pod --rm -i --tty --image alpine:latest -- /bin/sh

# check if port appears open
apk add nmap
nmap balancing-service -p 9999

# test opening a socket
apk add nano curl python3
echo -e "
import socket\n\n\
sock_balancer = socket.socket(socket.AF_INET,\
socket.SOCK_STREAM)\n\
sock_balancer.connect(('balancing-service', 9999))\n\n\
print('Connected!')\n\
sock_balancer.close()" > socket_test.py
python3 socket_test.py
```

---

## Useful links

+ [Cheat Sheet for `kubectl`](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
+ [`kubeconfig` for self-hosted k8s cluster](http://docs.shippable.com/deploy/tutorial/create-kubeconfig-for-self-hosted-kubernetes-cluster/)
+ [Describing a Service in `kubeconfig`](https://kubernetes.io/docs/concepts/services-networking/service/#defining-a-service)
+ [`apiVersion` definition guide](https://matthewpalmer.net/kubernetes-app-developer/articles/kubernetes-apiversion-definition-guide.html)
