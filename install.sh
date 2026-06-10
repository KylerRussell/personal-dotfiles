#!/usr/bin/env bash

# Anduril HUD Environment Installer and Symlink Deployer
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dotfiles"
TARGET_DIR="$HOME/.config"

echo "=========================================="
echo "Initializing Anduril HUD Environment"
echo "=========================================="

# Check if pacman is available (Arch Linux check)
if command -v pacman &> /dev/null; then
    echo "Arch Linux detected. Checking dependencies..."
    
    # List of required packages
    PACKAGES=(
        hyprland
        kitty
        rofi-wayland
        hyprpaper
        conky
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

# Install Barlow Condensed font from Google Fonts
FONT_DIR="$HOME/.local/share/fonts"
if [ ! -f "$FONT_DIR/BarlowCondensed-Bold.ttf" ]; then
    echo "Installing Barlow Condensed font..."
    mkdir -p "$FONT_DIR"
    FONT_BASE="https://raw.githubusercontent.com/jpt/barlow/main/fonts/ttf"
    if command -v curl &> /dev/null; then
        curl -sL "$FONT_BASE/BarlowCondensed-Bold.ttf" -o "$FONT_DIR/BarlowCondensed-Bold.ttf"
        curl -sL "$FONT_BASE/BarlowCondensed-Regular.ttf" -o "$FONT_DIR/BarlowCondensed-Regular.ttf"
        curl -sL "$FONT_BASE/BarlowCondensed-Light.ttf" -o "$FONT_DIR/BarlowCondensed-Light.ttf"
        fc-cache -f "$FONT_DIR" 2>/dev/null
        if fc-list | grep -qi barlow; then
            echo "Barlow Condensed font installed."
        else
            echo "Warning: Font files downloaded but fc-cache did not register them."
        fi
    else
        echo "Warning: curl not found. Skipping font download."
    fi
else
    echo "Barlow Condensed font already installed."
fi

mkdir -p "$TARGET_DIR"

# Loop through configurations and generate absolute links
for config in hypr kitty rofi conky; do
    if [ -d "$REPO_DIR/$config" ]; then
        echo "Mapping: $config -> $TARGET_DIR/$config"
        # Remove old configs safely
        rm -rf "$TARGET_DIR/$config"
        ln -sfn "$REPO_DIR/$config" "$TARGET_DIR/$config"
    fi
done

# Map the update script to home directory for easy execution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/update.sh" ]; then
    echo "Mapping: update.sh -> $HOME/update.sh"
    ln -sfn "$SCRIPT_DIR/update.sh" "$HOME/update.sh"
    chmod +x "$HOME/update.sh"
fi

echo "Deployment complete. Reload Hyprland with SUPER+M or reboot."
