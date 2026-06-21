#!/usr/bin/env bash
u=$(uptime -p 2>/dev/null | sed 's/^up //; s/ hours\?/h/; s/ minutes\?/m/; s/,//g')
[ -z "$u" ] && u="—"
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">UPTIME: %s</span>\n' "$u"
