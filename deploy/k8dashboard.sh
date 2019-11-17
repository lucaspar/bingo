#!/bin/bash

# SETS UP KUBERNETES WEB GUI DASHBOARD FOR AWS
# Source: https://docs.aws.amazon.com/eks/latest/userguide/dashboard-tutorial.html

set -e

# install deps
sudo apt install curl jq

# download metrics server
DOWNLOAD_URL=$(curl --silent "https://api.github.com/repos/kubernetes-incubator/metrics-server/releases/latest" | jq -r .tarball_url)
DOWNLOAD_VERSION=$(grep -o '[^/v]*$' <<< $DOWNLOAD_URL)
curl -Ls $DOWNLOAD_URL -o metrics-server-$DOWNLOAD_VERSION.tar.gz
mkdir metrics-server-$DOWNLOAD_VERSION
tar -xzf metrics-server-$DOWNLOAD_VERSION.tar.gz --directory metrics-server-$DOWNLOAD_VERSION --strip-components 1
kubectl apply -f metrics-server-$DOWNLOAD_VERSION/deploy/1.8+/

# apply roles
kubectl get deployment metrics-server -n kube-system
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-beta4/aio/deploy/recommended.yaml
kubectl apply -f eks-admin-service-account.yaml

# :: GET TOKEN ::
kubectl -n kube-system describe secret $(kubectl -n kube-system get secret | grep eks-admin | awk '{print $1}')

# cleanup
rm -rf metrics-server-$DOWNLOAD_VERSION
rm metrics-server-$DOWNLOAD_VERSION.tar.gz

# start server
echo ">> Run 'kubectl proxy' to start server"
