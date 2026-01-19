#!/usr/bin/env bash

set -e

# This script retrieves the TLS certificate and key from a Kubernetes secret
# and saves them to files.

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null
then
    echo "kubectl could not be found. Please install it to use this script."
    exit 1
fi

SECRET_NAME="local-ggnt-eu"
NAMESPACE="default" # Assuming the secret is in the default namespace

echo "Attempting to retrieve TLS certificate and key from secret: $SECRET_NAME in namespace: $NAMESPACE"

mkdir -p "ssl"

# Get the certificate
kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.tls\.crt}' | base64 --decode > ssl/tls.crt

# Get the private key
kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.tls\.key}' | base64 --decode > ssl/tls.key

if [ $? -eq 0 ]; then
    echo "Successfully extracted tls.crt and tls.key from secret '$SECRET_NAME'."
    echo "Files saved as tls.crt and tls.key in the current directory."
else
    echo "Failed to extract TLS certificate and key. Please ensure the secret '$SECRET_NAME' exists in namespace '$NAMESPACE' and has 'tls.crt' and 'tls.key' fields."
    rm -f tls.crt tls.key # Clean up any partially created files
    exit 1
fi
