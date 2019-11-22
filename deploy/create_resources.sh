# !/bin/sh
set -e

# choose deploy environment (local or aws):
DEPLOY_ENV=aws

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
kubectl create configmap redisconfig --from-file=../balancer/redis.conf

echo " > Resources created for '$DEPLOY_ENV' environment!"
