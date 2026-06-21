#!/usr/bin/env bash
prev=/tmp/hud-net-prev
rx=0; tx=0
while read -r l; do
  case "$l" in *:*)
    ifc=${l%%:*}; ifc=${ifc// /}; [ "$ifc" = lo ] && continue
    set -- ${l#*:}; rx=$((rx+$1)); tx=$((tx+$9)) ;;
  esac
done < /proc/net/dev
now=$(date +%s)
if [ -f "$prev" ]; then read -r pt prx ptx < "$prev"; else pt=$((now-1)); prx=$rx; ptx=$tx; fi
echo "$now $rx $tx" > "$prev"
dts=$((now-pt)); [ "$dts" -le 0 ] && dts=1
drx=$(( (rx-prx)/dts )); dtx=$(( (tx-ptx)/dts ))
h(){ local b=$1; [ "$b" -lt 0 ] && b=0; if [ "$b" -ge 1048576 ]; then echo "$((b/1048576))MB/s"; elif [ "$b" -ge 1024 ]; then echo "$((b/1024))KB/s"; else echo "${b}B/s"; fi; }
printf '<span font="Barlow Condensed 12" foreground="#8a8a8a">NET ↑ %s ↓ %s</span>\n' "$(h "$dtx")" "$(h "$drx")"
