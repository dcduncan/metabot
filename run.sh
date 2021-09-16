#!/bin/bash
set -e
set -u

docker build -t metabot .
docker run -it -e TOKEN=$TOKEN metabot
