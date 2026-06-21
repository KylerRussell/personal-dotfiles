#!/usr/bin/env bash
k=$(uname -r | cut -d- -f1)
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">HOST: %s · %s</span>\n' "$(hostname)" "$k"
