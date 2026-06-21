#!/usr/bin/env bash
geom=$(hyprctl activewindow -j | python3 -c 'import json,sys; w=json.load(sys.stdin); print(f"{w[\"at\"][0]},{w[\"at\"][1]} {w[\"size\"][0]}x{w[\"size\"][1]}")')
[ -n "$geom" ] && grim -g "$geom" "$HOME/shot-$(date +%s).png"
