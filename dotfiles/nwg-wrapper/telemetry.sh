#!/usr/bin/env bash
# HUD telemetry block (top-left).
# Static values for now — this is a normal script, so to make any field live
# later just swap the literal in for a command, e.g.
#   ELEV: $(some-sensor-command)m
# and give this widget a refresh interval (-r) in hyprland.conf.
cat <<'EOF'
<span font="Barlow Condensed 12" foreground="#8a8a8a">SECTOR: CENTRAL
LAT: 39.0997°N
LON: 94.5786°W
ELEV: 276m
</span><span font="Barlow Condensed 12" foreground="#e25822">STATUS: ACTIVE</span>
EOF
