# Cluster Creation Walkthrough

## CREATION

### Create secrets

```sh
# create files
code AWS_ACCESS_KEY_ID.txt && code AWS_SECRET_ACCESS_KEY.txt

# create secrets
./create_secrets.sh
```

### Create cluster

#### Option A: Local

```sh
minikube start
```

#### Option B: AWS (this will cost $)

```sh
eksctl create cluster --version 1.14 --nodegroup-name bingo --node-type t3.nano \
    --nodes 2 --nodes-min 1 --nodes-max 4 --node-ami auto --name bingo-nano
```

#### Apply kubeconfig files

```sh
kubectl apply -f kubeconfig.crawling.yaml
kubectl apply -f kubeconfig.indexing.yaml
```

> To use `redis.conf` file see:
https://github.com/GoogleCloudPlatform/redis-docker/blob/master/4/README.md#configurations

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

#### list persistent volumes

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

## Useful links

+ [Cheat Sheet for `kubectl`](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
+ [`kubeconfig` for self-hosted k8s cluster](http://docs.shippable.com/deploy/tutorial/create-kubeconfig-for-self-hosted-kubernetes-cluster/)
+ [Describing a Service in `kubeconfig`](https://kubernetes.io/docs/concepts/services-networking/service/#defining-a-service)
+ [`apiVersion` definition guide](https://matthewpalmer.net/kubernetes-app-developer/articles/kubernetes-apiversion-definition-guide.html)
