# Cluster Creation Walkthrough

## CREATION

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
minikube start
```

#### `Option B:` AWS (this will cost $)

```sh
eksctl create cluster --version 1.14 --nodegroup-name bingo \
    --node-type t3.nano --nodes 2 --nodes-min 1 --nodes-max 4 \
    --node-ami auto --name bingo-nano
```

#### Apply kubeconfig files

```sh
kubectl apply -f kubeconfig.crawling.yaml
kubectl apply -f kubeconfig.indexing.yaml
```

### Networking

#### List available endpoints

```sh
kubectl get ep
```

#### Remote accessing URL Map (Redis) pod

```sh
kubectl expose pod urlmap-pod --name urlmap-6379 --type LoadBalancer --port 6379 --protocol TCP
kubectl exec -it urlmap-pod -- redis-cli
```

#### Probing DNS Server

```sh
# check whether DNS service is running
kubectl get services kube-dns --namespace=kube-system

# run interactive 'curl' pod
kubectl run curl --image=radial/busyboxplus:curl -i --tty

# in the pod's shell, check DNS lookups
nslookup crawling-service
nslookup balancing-service
nslookup urlmap.balancing-service
```

### Monitoring

#### Local deploy dashboard

```sh
minikube dashboard
```

#### AWS deploy dashboard

```sh
./k8dashboard.sh
```

### Storage

#### List persistent volumes

```sh
kubectl get pv
kubectl get pvc
```

### Cleanup

#### Delete volatile `kubectl` resources

```sh
kubectl delete daemonsets,replicasets,services,deployments,pods,rc --all
```

#### `[ Danger ]` Delete **persistent data**

```sh
# stateful sets, persistent volumes, persistent volume claims, and storage classes
kubectl delete statefulsets,pv,pvc,sc --all
```

#### `[ Danger ]` Delete everything (incl. persistent data!)

```sh
kubectl delete daemonsets,replicasets,services,deployments,pods,rc,statefulsets,pv,pvc,sc --all
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
```

---

## Useful links

+ [Cheat Sheet for `kubectl`](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
+ [`kubeconfig` for self-hosted k8s cluster](http://docs.shippable.com/deploy/tutorial/create-kubeconfig-for-self-hosted-kubernetes-cluster/)
+ [Describing a Service in `kubeconfig`](https://kubernetes.io/docs/concepts/services-networking/service/#defining-a-service)
+ [`apiVersion` definition guide](https://matthewpalmer.net/kubernetes-app-developer/articles/kubernetes-apiversion-definition-guide.html)
