#!/usr/bin/env bash

# Tactical Environment Symlink Deployer
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dotfiles"
TARGET_DIR="$HOME/.config"

echo "=========================================="
echo "Initializing Tactical Environment Injection"
echo "=========================================="

mkdir -p "$TARGET_DIR"

# Loop through configurations and generate absolute links
for config in hypr kitty waybar; do
    if [ -d "$REPO_DIR/$config" ]; then
        echo "Mapping: $config -> $TARGET_DIR/$config"
        # Remove old configs or ML4W remnants safely
        rm -rf "$TARGET_DIR/$config"
        ln -sf "$REPO_DIR/$config" "$TARGET_DIR/"
    fi
done

echo "Deployment complete. Reload Hyprland with SUPER+M or reboot."
