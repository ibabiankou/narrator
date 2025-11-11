#!/usr/bin/env bash

set -e

# Build and run docker image

IMAGE_NAME="narrator-api"

PLATFORMS="${PLATFORMS:-"linux/arm64"}"
COMMIT_HASH=$(git rev-parse --short HEAD)
TAG="${IMAGE_NAME}-${2:-$COMMIT_HASH}"

echo "Setup things for multiarch build"
docker buildx inspect multiarch \
  || docker buildx create --name multiarch --use --driver docker-container
docker run --rm --privileged tonistiigi/binfmt --install all
docker buildx inspect --bootstrap

docker buildx build \
  --platform "${PLATFORMS}" \
  --load \
  -t "ibabiankou/home-lab:${TAG}" .

# if --run is specified, then immediately run the newly built image.
run=false
for arg in "$@"; do
  if [[ "$arg" == "--run" ]]; then
    run=true
    break
  fi
done

if [ "$run" = true ]; then
  echo "Starting the api container..."
  docker run --rm --name api -p 8080:8000 "ibabiankou/home-lab:${TAG}"
fi
