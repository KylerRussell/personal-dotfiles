#!/usr/bin/env bash
h=$(date +%-H)
if   [ "$h" -lt 5  ]; then g="GOOD NIGHT"
elif [ "$h" -lt 12 ]; then g="GOOD MORNING"
elif [ "$h" -lt 17 ]; then g="GOOD AFTERNOON"
elif [ "$h" -lt 21 ]; then g="GOOD EVENING"
else g="GOOD NIGHT"; fi
printf '<span font="Barlow Condensed 16" foreground="#8a8a8a">%s</span>\n' "$g"
