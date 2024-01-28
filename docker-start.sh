#!/bin/bash

# example - ./docker-start.sh 20240116 6 20240116 12 20240116 18

PARAMS="$*"
export PARAMS
docker-compose up -d

sleep 5