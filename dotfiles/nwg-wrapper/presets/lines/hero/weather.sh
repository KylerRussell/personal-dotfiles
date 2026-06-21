#!/usr/bin/env bash
cache=/tmp/hud-weather
if [ -f "$cache" ] && [ $(( $(date +%s) - $(stat -c %Y "$cache" 2>/dev/null || echo 0) )) -lt 1800 ]; then
    cat "$cache"; exit 0
fi
raw=$(curl -fsS --max-time 4 "https://wttr.in/Kansas+City?format=%t+%C" 2>/dev/null)
if [ -n "$raw" ]; then
    raw=${raw#+}; temp=${raw%% *}; cond=${raw#* }
    txt=$(printf '%s · %s' "$temp" "$cond" | tr '[:lower:]' '[:upper:]')
    printf '<span font="Barlow Condensed 16" foreground="#8a8a8a">%s</span>\n' "$txt" | tee "$cache"
else
    printf '<span font="Barlow Condensed 16" foreground="#8a8a8a">WEATHER: —</span>\n'
fi
