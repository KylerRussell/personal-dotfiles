#!/usr/bin/env bash
read -r tot used < <(free -m | awk '/Mem:/{print $2, $3}')
[ "${tot:-0}" -le 0 ] && tot=1
pct=$(( 100*used/tot )); filled=$(( pct/10 ))
bar=""; for i in $(seq 1 10); do [ "$i" -le "$filled" ] && bar+="█" || bar+="░"; done
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">RAM [%s] %d%%</span>\n' "$bar" "$pct"
