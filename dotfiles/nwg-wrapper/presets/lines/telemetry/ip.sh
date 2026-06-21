#!/usr/bin/env bash
ip4=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
[ -z "$ip4" ] && ip4="—"
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">NET: %s</span>\n' "$ip4"
