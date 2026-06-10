#!/usr/bin/env bash
# One-click updater: pull the latest main branch from GitHub and re-run install.
#
# This extracts to a TEMP dir first, then swaps it into the stable location the
# ~/.config symlinks point at. The old version downloaded directly over its own
# file while running, which could truncate this script mid-execution (leaving a
# 0-byte update.sh that silently does nothing). Don't reintroduce that.
set -euo pipefail

REPO_URL="https://github.com/KylerRussell/personal-dotfiles/archive/refs/heads/main.tar.gz"
DEST="$HOME/personal-dotfiles-main"

echo "=========================================="
echo "Pulling Latest Tactical Dotfiles Update"
echo "=========================================="

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! curl -fsSL "$REPO_URL" | tar -xz -C "$TMP"; then
    echo "ERROR: download/extract failed. Existing config left untouched."
    exit 1
fi

if [ ! -d "$TMP/personal-dotfiles-main" ]; then
    echo "ERROR: extracted archive did not contain personal-dotfiles-main. Aborting."
    exit 1
fi

# Swap the freshly downloaded tree into the stable path, then deploy.
rm -rf "$DEST"
mv "$TMP/personal-dotfiles-main" "$DEST"

cd "$DEST"
chmod +x install.sh
./install.sh

echo "=========================================="
echo "Update Complete."
echo "=========================================="
