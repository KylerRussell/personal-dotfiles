#!/usr/bin/env bash
printf '<span font="Barlow Condensed 16" foreground="#8a8a8a">WEEK %s · DAY %s</span>\n' "$(date +%V)" "$(date +%-j)"
