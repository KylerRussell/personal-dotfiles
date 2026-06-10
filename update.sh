#!/usr/bin/env bash
# One-click updater: pull the latest main branch from GitHub and re-run install.
#
# IMPORTANT: this extracts IN PLACE over the repo dir and never deletes it. The
# ~/.config/* symlinks point INTO this directory, so removing it mid-update (even
# briefly) breaks the live config and can leave dangling symlinks if anything
# fails. $HOME/update.sh is a standalone copy (see install.sh), so overwriting
# $DEST/update.sh during extraction cannot truncate this running script.
set -euo pipefail

REPO_URL="https://github.com/KylerRussell/personal-dotfiles/archive/refs/heads/main.tar.gz"
DEST="$HOME/personal-dotfiles-main"

echo "=========================================="
echo "Pulling Latest Tactical Dotfiles Update"
echo "=========================================="

mkdir -p "$DEST"

# Tarball's top-level dir is "personal-dotfiles-main", so extracting into $HOME
# overwrites files inside $DEST in place, keeping every symlink target valid.
if ! curl -fsSL "$REPO_URL" | tar -xz -C "$HOME"; then
    echo "ERROR: download/extract failed. Existing config left untouched."
    exit 1
fi

cd "$DEST"
chmod +x install.sh
./install.sh

echo "=========================================="
echo "Update Complete."
echo "=========================================="
