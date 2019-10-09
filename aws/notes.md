# Notes on k8s deploy

## Step-by-Step

http://docs.shippable.com/deploy/tutorial/create-kubeconfig-for-self-hosted-kubernetes-cluster/

## Describing a service

https://kubernetes.io/docs/concepts/services-networking/service/#defining-a-service

## apiVersion

https://matthewpalmer.net/kubernetes-app-developer/articles/kubernetes-apiversion-definition-guide.html

## Code Snippets

```sh
# delete all kubectl resources
kubectl delete daemonsets,replicasets,services,deployments,pods,rc --all

# creates and updates resourcess in a cluster according to a `.yaml` file
kubectl apply -f local.kubeconfig.yaml

```
