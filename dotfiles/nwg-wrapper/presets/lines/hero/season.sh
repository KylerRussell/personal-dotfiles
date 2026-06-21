#!/usr/bin/env bash
m=$(date +%-m)
case "$m" in 12|1|2) s=WINTER;; 3|4|5) s=SPRING;; 6|7|8) s=SUMMER;; *) s=AUTUMN;; esac
printf '<span font="Barlow Condensed 16" foreground="#8a8a8a">%s</span>\n' "$s"
