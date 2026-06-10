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
        swaybg
        mesa
        vulkan-swrast
        vulkan-tools
        ttf-jetbrains-mono
        otf-font-awesome
        python-gobject
        python-cairo
        gtk3
        gtk-layer-shell
        wlr-randr
        python-pip
        git
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
        # Do a FULL system upgrade alongside the install. Installing onto a
        # refreshed DB without upgrading (`pacman -Sy pkg`) is a partial upgrade
        # and can pull a newer mesa/libdrm than the running system -> broken EGL.
        if [ "$EUID" -ne 0 ]; then
            sudo pacman -Syu --noconfirm "${MISSING_PACKAGES[@]}"
        else
            pacman -Syu --noconfirm "${MISSING_PACKAGES[@]}"
        fi
    else
        echo "All core packages are already installed."
    fi
else
    echo "Warning: pacman not found. Skipping package installation."
fi

# Install Barlow Condensed font directly from the google/fonts repo.
# Pull individual weights (stable raw URLs) instead of the flaky zip endpoint,
# which extracts into a subfolder and breaks the "already installed" check.
FONT_DIR="$HOME/.local/share/fonts/barlow-condensed"
FONT_BASE="https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed"
FONT_WEIGHTS=(Regular Medium SemiBold Bold)

if [ ! -f "$FONT_DIR/BarlowCondensed-Bold.ttf" ]; then
    if command -v curl &> /dev/null; then
        echo "Installing Barlow Condensed font..."
        mkdir -p "$FONT_DIR"
        DOWNLOADED=0
        for weight in "${FONT_WEIGHTS[@]}"; do
            if curl -fsSL "$FONT_BASE/BarlowCondensed-$weight.ttf" \
                    -o "$FONT_DIR/BarlowCondensed-$weight.ttf"; then
                DOWNLOADED=$((DOWNLOADED + 1))
            else
                echo "  Warning: failed to fetch BarlowCondensed-$weight.ttf"
            fi
        done
        if [ "$DOWNLOADED" -gt 0 ]; then
            fc-cache -f "$FONT_DIR" &> /dev/null
            echo "Barlow Condensed font installed ($DOWNLOADED weights)."
        else
            echo "Warning: Could not download Barlow Condensed. Clock may use a fallback font."
        fi
    else
        echo "Warning: curl not found. Skipping font download."
    fi
else
    echo "Barlow Condensed font already installed."
fi

# Install nwg-wrapper (layer-shell HUD widget, the conky replacement) from source.
if ! command -v nwg-wrapper &> /dev/null; then
    echo "Installing nwg-wrapper from source..."
    NWG_TMP="/tmp/nwg-wrapper-src"
    rm -rf "$NWG_TMP"
    if command -v git &> /dev/null && git clone --depth 1 https://github.com/nwg-piotr/nwg-wrapper.git "$NWG_TMP" &> /dev/null; then
        if ( cd "$NWG_TMP" && pip install --break-system-packages . &> /dev/null ); then
            echo "nwg-wrapper installed."
        else
            echo "Warning: nwg-wrapper build failed (needs python-gobject + gtk-layer-shell)."
        fi
        rm -rf "$NWG_TMP"
    else
        echo "Warning: could not fetch nwg-wrapper (git/network)."
    fi
else
    echo "nwg-wrapper already installed."
fi

mkdir -p "$TARGET_DIR"

# Loop through configurations and generate absolute links
for config in hypr kitty rofi nwg-wrapper; do
    if [ -d "$REPO_DIR/$config" ]; then
        echo "Mapping: $config -> $TARGET_DIR/$config"
        # Remove old configs safely
        rm -rf "$TARGET_DIR/$config"
        ln -sfn "$REPO_DIR/$config" "$TARGET_DIR/$config"
    fi
done

# HUD widget scripts must be executable
chmod +x "$TARGET_DIR"/nwg-wrapper/*.sh 2>/dev/null

# Copy (do NOT symlink) the update script to the home directory. A symlink here
# points back into the repo tree that update.sh itself overwrites while running,
# which can truncate the script mid-execution. A standalone copy is immune.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/update.sh" ]; then
    echo "Mapping: update.sh -> home directory (standalone copy)"
    rm -f "$HOME/update.sh"   # drop any old symlink so cp can't hit "same file"
    cp -f "$SCRIPT_DIR/update.sh" "$HOME/update.sh"
    chmod +x "$HOME/update.sh"
fi

echo "Deployment complete. Reload Hyprland with SUPER+M or reboot."
