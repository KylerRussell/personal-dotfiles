#!/usr/bin/env bash
prev=/tmp/hud-cpu-prev
read -r _ a b c d _ < /proc/stat
total=$((a+b+c+d)); idle=$d
if [ -f "$prev" ]; then read -r pt pi < "$prev"; else pt=0; pi=0; fi
echo "$total $idle" > "$prev"
dt=$((total-pt)); di=$((idle-pi)); [ "$dt" -le 0 ] && dt=1
pct=$(( 100*(dt-di)/dt )); [ "$pct" -lt 0 ] && pct=0; [ "$pct" -gt 100 ] && pct=100
filled=$(( pct/10 ))
bar=""; for i in $(seq 1 10); do [ "$i" -le "$filled" ] && bar+="█" || bar+="░"; done
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">CPU [%s] %d%%</span>\n' "$bar" "$pct"
