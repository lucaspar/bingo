eksctl create cluster \
    --version 1.14 \
    --nodegroup-name bingo-crawlers \
    --node-type t3.nano \
    --nodes 2 \
    --nodes-min 1 \
    --nodes-max 4 \
    --node-ami auto \
    --name bingo-nano-003 \
