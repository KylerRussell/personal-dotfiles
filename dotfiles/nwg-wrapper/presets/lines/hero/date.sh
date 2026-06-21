#!/usr/bin/env bash
d=$(date +%-d)
case "$d" in 1|21|31) s=st;; 2|22) s=nd;; 3|23) s=rd;; *) s=th;; esac
printf '<span font="Barlow Condensed 22" foreground="#8a8a8a">%s %d%s %s</span>\n' "$(date +%B)" "$d" "$s" "$(date +%Y)"
