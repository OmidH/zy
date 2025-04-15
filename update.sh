#!/bin/bash

# Check if the IP address is provided as an argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <IP_ADDRESS>"
    exit 1
fi

IP_ADDRESS=$1

# Check if the ./zy directory exists on the server, if not, create it
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy ]; then mkdir -p ./zy; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/nginx ]; then mkdir -p ./zy/nginx; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/crowdsec ]; then mkdir -p ./zy/crowdsec; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/webroot ]; then mkdir -p ./zy/webroot; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/webroot/ui ]; then mkdir -p ./zy/webroot/ui; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/data ]; then mkdir -p ./zy/data; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/data/uploads/audio ]; then mkdir -p ./zy/data/uploads/audio; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/data/uploads/audio/global ]; then mkdir -p ./zy/data/uploads/audio/global; fi'
ssh bb@$IP_ADDRESS 'if [ ! -d ./zy/data/uploads/wiki ]; then mkdir -p ./zy/data/uploads/wiki; fi'

# Copy files to the remote server
scp ./docker-compose.yml bb@$IP_ADDRESS:./zy/docker-compose.yml
scp .env.production bb@$IP_ADDRESS:./zy/.env.production
scp ./redis.conf bb@$IP_ADDRESS:./zy/redis.conf
scp ./start.sh bb@$IP_ADDRESS:./zy/start.sh
scp ./supervisord.conf bb@$IP_ADDRESS:./zy/supervisord.conf
scp -r ./nginx/* bb@$IP_ADDRESS:./zy/nginx/
scp -r ./crowdsec/* bb@$IP_ADDRESS:./zy/crowdsec/
scp -r ./webroot/* bb@$IP_ADDRESS:./zy/webroot/


# scp ./docker-compose.yml bb@49.12.66.139:./zy/docker-compose.yml
# scp .env.production bb@49.12.66.139:./zy/.env.production
# scp -r ./nginx/* bb@49.12.66.139:./zy/nginx/