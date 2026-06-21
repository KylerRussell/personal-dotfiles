#!/usr/bin/env bash
python3 - <<'PY'
import datetime
known = datetime.datetime(2000,1,6,18,14, tzinfo=datetime.timezone.utc)
now   = datetime.datetime.now(datetime.timezone.utc)
syn   = 29.530588853
phase = ((now-known).total_seconds()/86400.0 % syn)/syn
idx   = int(phase*8 + 0.5) % 8
names = ["🌑 NEW MOON","🌒 WAXING CRESCENT","🌓 FIRST QUARTER","🌔 WAXING GIBBOUS",
         "🌕 FULL MOON","🌖 WANING GIBBOUS","🌗 LAST QUARTER","🌘 WANING CRESCENT"]
print(f'<span font="Barlow Condensed 16" foreground="#8a8a8a">{names[idx]}</span>')
PY
