#!/bin/bash
set -e

# SETS UP KUBERNETES WEB GUI DASHBOARD FOR AWS
# Source: https://docs.aws.amazon.com/eks/latest/userguide/dashboard-tutorial.html

# install deps
sudo apt install curl jq

# download metrics server
DOWNLOAD_URL=$(curl --silent "https://api.github.com/repositories/92132038/releases/latest" | jq -r .tarball_url)
DOWNLOAD_VERSION=$(grep -o '[^/v]*$' <<< $DOWNLOAD_URL)
curl -Ls $DOWNLOAD_URL -o metrics-server-$DOWNLOAD_VERSION.tar.gz
mkdir metrics-server-$DOWNLOAD_VERSION
tar -xzf metrics-server-$DOWNLOAD_VERSION.tar.gz --directory metrics-server-$DOWNLOAD_VERSION --strip-components 1
kubectl apply -f metrics-server-$DOWNLOAD_VERSION/deploy/1.8+/

# cleanup
rm -rf metrics-server-$DOWNLOAD_VERSION
rm metrics-server-$DOWNLOAD_VERSION.tar.gz

# apply roles
kubectl get deployment metrics-server -n kube-system
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-beta6/aio/deploy/recommended.yaml
kubectl apply -f others/eks-admin-service-account.yaml

# :: GET TOKEN ::
kubectl -n kube-system describe secret $(kubectl -n kube-system get secret | grep eks-admin | awk '{print $1}')

# start server
sensible-browser "http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#\!/login"
echo "Running 'kubectl proxy'"
kubectl proxy
