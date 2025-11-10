#!/usr/bin/env bash

set -e

# Build and push docker image

IMAGE_NAME="narrator-api"

PLATFORMS="${PLATFORMS:-"linux/amd64,linux/arm64"}"
#PLATFORMS="${PLATFORMS:-"linux/arm64"}"
COMMIT_HASH=$(git rev-parse --short HEAD)
TAG="${IMAGE_NAME}-${2:-$COMMIT_HASH}"

echo "Setup things for multiarch build"
docker buildx inspect multiarch \
  || docker buildx create --name multiarch --use --driver docker-container
docker run --rm --privileged tonistiigi/binfmt --install all
docker buildx inspect --bootstrap

#  --load \
docker buildx build \
  --platform "${PLATFORMS}" \
  --push \
  -t "ibabiankou/home-lab:${TAG}" .
