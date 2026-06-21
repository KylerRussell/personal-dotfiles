#!/usr/bin/env bash
n=$(hyprctl clients 2>/dev/null | grep -c '^Window')
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">WINDOWS: %s</span>\n' "${n:-0}"
