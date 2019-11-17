# !/bin/sh

# create secrets
kubectl create secret generic aws-creds --from-file=./AWS_ACCESS_KEY_ID.txt --from-file=./AWS_SECRET_ACCESS_KEY.txt

# create configmap for redis.conf
# based on: https://github.com/GoogleCloudPlatform/redis-docker/blob/master/4/README.md#configurations
kubectl create configmap redisconfig --from-file=../balancer/redis.conf
