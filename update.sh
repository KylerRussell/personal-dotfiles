#!/usr/bin/env bash

# Go to home directory to run the download
cd "$HOME" || exit

echo "=========================================="
echo "Pulling Latest Tactical Dotfiles Update"
echo "=========================================="

# Download and extract the latest tarball
curl -L https://github.com/KylerRussell/personal-dotfiles/archive/refs/heads/main.tar.gz | tar -xz

# Navigate to the repository folder
cd personal-dotfiles-main || exit 1

# Make install.sh executable and run it
chmod +x install.sh
./install.sh

echo "=========================================="
echo "Update Complete."
echo "=========================================="
