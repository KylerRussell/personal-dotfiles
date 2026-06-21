#!/usr/bin/env bash
python3 - <<'PY'
try:
    import datetime
    from astral import Observer
    from astral.sun import sun
    tz = datetime.datetime.now().astimezone().tzinfo
    obs = Observer(latitude=39.0997, longitude=-94.5786)
    s = sun(obs, date=datetime.date.today(), tzinfo=tz)
    out = f'↑ {s["sunrise"]:%H:%M} · ↓ {s["sunset"]:%H:%M}'
except Exception:
    out = '↑ —— · ↓ ——'
print(f'<span font="Barlow Condensed 16" foreground="#8a8a8a">{out}</span>')
PY
