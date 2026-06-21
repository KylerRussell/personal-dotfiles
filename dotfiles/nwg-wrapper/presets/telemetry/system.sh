#!/usr/bin/env bash
load=$(cut -d' ' -f1 /proc/loadavg)
mem=$(free -m | awk '/Mem:/{printf "%d / %d MB", $3, $2}')
disk=$(df -h --output=used,size / 2>/dev/null | awk 'NR==2{print $1" / "$2}')
up=$(uptime -p 2>/dev/null | sed 's/^up //')
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">LOAD: %s\nMEM:  %s\nDISK: %s\nUPTIME: %s\n</span><span font="Barlow Condensed 12" foreground="#e25822">STATUS: ACTIVE</span>\n' "$load" "$mem" "$disk" "$up"
