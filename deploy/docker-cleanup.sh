#!/bin/bash

# Remove all unused containers, networks, images and volumes
docker system prune -f

# Remove all images (that aren't currently in use)
docker images -q | xargs -r docker rmi 