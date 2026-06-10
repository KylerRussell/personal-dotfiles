#!/usr/bin/env bash
# HUD clock + date (bottom-left). nwg-wrapper re-runs this on its refresh
# interval (-r) so the time stays current.
d=$(date +%-d)
case "$d" in
    1|21|31) s=st ;;
    2|22)    s=nd ;;
    3|23)    s=rd ;;
    *)       s=th ;;
esac
printf '<span font="Barlow Condensed Bold 96" foreground="#3a3a3a">%s</span>\n' "$(date +%H:%M)"
printf '<span font="Barlow Condensed 22" foreground="#8a8a8a">%s %d%s %s</span>' "$(date +%B)" "$d" "$s" "$(date +%Y)"
