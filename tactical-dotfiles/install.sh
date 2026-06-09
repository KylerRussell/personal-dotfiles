#!/usr/bin/env bash

# Tactical Environment Package Installer and Symlink Deployer
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dotfiles"
TARGET_DIR="$HOME/.config"

echo "=========================================="
echo "Initializing Tactical Environment Injection"
echo "=========================================="

# Check if pacman is available (Arch Linux check)
if command -v pacman &> /dev/null; then
    echo "Arch Linux detected. Checking dependencies..."
    
    # List of required packages
    PACKAGES=(
        hyprland
        kitty
        waybar
        rofi-wayland
        hyprpaper
        mesa
        vulkan-swrast
        vulkan-tools
        ttf-jetbrains-mono
        otf-font-awesome
    )
    
    # Check which packages are missing
    MISSING_PACKAGES=()
    for pkg in "${PACKAGES[@]}"; do
        if ! pacman -Qi "$pkg" &> /dev/null; then
            MISSING_PACKAGES+=("$pkg")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        echo "Installing missing packages: ${MISSING_PACKAGES[*]}"
        # If not root, prepend sudo
        if [ "$EUID" -ne 0 ]; then
            sudo pacman -Sy --noconfirm "${MISSING_PACKAGES[@]}"
        else
            pacman -Sy --noconfirm "${MISSING_PACKAGES[@]}"
        fi
    else
        echo "All core packages are already installed."
    fi
else
    echo "Warning: pacman not found. Skipping package installation."
fi

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
