# T0
minikube start
minikube dashboard

# T1
cd ~/work/bingo/balancer
docker push bingocrawler/balancer:latest
docker build -t bingocrawler/balancer:latest .

# T2
cd ~/work/bingo/crawler
docker push bingocrawler/crawler:latest
docker build -t bingocrawler/crawler:latest .

# T3
watch kubectl get pods

# T4
watch -n 10 kubectl get svc --all-namespaces

# T5
watch "kubectl logs domain-balancer-pod | tail -n $(($LINES - 4))"

# T6
watch "kubectl logs crawler-pod-849cfd6c49-rtlf2 | tail -n $(($LINES - 4))"

# T7
cd ~/work/bingo/deploy
kubectl delete daemonsets,replicasets,services,deployments,pods,rc,statefulsets,pv,pvc,sc --all
kubectl apply -f kubeconfig.crawling.yaml

# T8
kubectl run debug-pod --rm -i --tty --image alpine:latest -- /bin/sh
