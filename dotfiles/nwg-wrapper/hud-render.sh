#!/usr/bin/env bash
# Stitches the enabled line modules for one widget. The launcher passes
# HUD_SECTION (telemetry|hero) and HUD_LINES (comma-separated module names).
DIR="$HOME/.config/nwg-wrapper"
[ -z "$HUD_LINES" ] && exit 0
IFS=',' read -ra arr <<< "$HUD_LINES"
for ln in "${arr[@]}"; do
    ln="${ln//[[:space:]]/}"
    f="$DIR/presets/lines/$HUD_SECTION/$ln.sh"
    [ -f "$f" ] && bash "$f"
done
