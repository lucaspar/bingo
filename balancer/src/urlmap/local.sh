# running it locally:
docker run -d --name url-map -p 6379:6379 -v $(pwd)/redis.conf:/redis.conf redis redis-server /redis.conf
