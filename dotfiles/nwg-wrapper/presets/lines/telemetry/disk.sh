#!/usr/bin/env bash
d=$(df -h --output=used,size / 2>/dev/null | awk 'NR==2{print $1" / "$2}')
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">DISK: %s</span>\n' "$d"
