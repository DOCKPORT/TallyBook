#!/bin/bash

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install it first:"
    echo "sudo apt update && sudo apt install docker.io"
    echo "sudo usermod -aG docker \$USER (then log out and back in)"
    exit 1
fi

echo "🚀 Building TallyBook AppImage using Ubuntu 22.04 Docker container..."

# Build the docker image
docker build -t tallybook-builder .

# Run the container to build the AppImage
# We mount the current directory to /build inside the container
docker run --rm -v "$(pwd)":/build tallybook-builder

echo "✅ Done! Your Ubuntu 22.04 compatible AppImage should be in the current directory."
