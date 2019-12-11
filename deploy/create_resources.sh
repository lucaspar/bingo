# !/bin/sh
set -e

# choose deploy environment (local or aws):
# DEPLOY_ENV=local
DEPLOY_ENV=$(kubectl config current-context)
echo $DEPLOY_ENV
if [[ $DEPLOY_ENV == "minikube" ]]; then
    DEPLOY_ENV=local
elif [[ $DEPLOY_ENV == *"eksctl"* ]]; then
    DEPLOY_ENV=aws
else
    echo " > Context not recognized :: using 'local'"
    DEPLOY_ENV=local
fi
export DEPLOY_ENV

echo " > Creating static resources for '$DEPLOY_ENV' environment..."

# create secrets
kubectl delete secrets --ignore-not-found aws-creds deploy
kubectl create secret generic aws-creds --from-file=./AWS_ACCESS_KEY_ID --from-file=./AWS_SECRET_ACCESS_KEY
kubectl create secret generic deploy --from-literal=ENV_FILE=.env.$DEPLOY_ENV

# to update / apply secrets during runtime:
# kubectl create secret generic <MY_SECRET> --from-file=<FILE_NAME> --dry-run -o yaml | kubectl apply -f -

# create configmap for redis.conf
# based on: https://github.com/GoogleCloudPlatform/redis-docker/blob/master/4/README.md#configurations
kubectl delete configmap --ignore-not-found redisconfig
kubectl delete configmap --ignore-not-found -n monitoring prometheus-server-conf
kubectl create configmap redisconfig --from-file=../balancer/redis.conf
kubectl apply -f prometheus.configmap.yaml

echo " > Resources created for '$DEPLOY_ENV' environment!"
