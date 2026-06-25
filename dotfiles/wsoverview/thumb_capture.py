#!/usr/bin/env python3
"""Shared window-thumbnail capture for the workspace overview.

capture_visible() grabs a grim screenshot of every window that is *currently
visible* (on a monitor's active workspace) and stores it as
<thumbs>/<address>.png. Because hidden windows keep their last-captured file,
the overview can still show what a window looked like before it was parked.
Imported by both the daemon (periodic / event-driven) and the overlay (a fresh
capture the moment it opens, before its own layer is mapped).
"""
import os
import json
import subprocess

THUMBS = "/tmp/wsoverview/thumbs"


def _json(cmd):
    try:
        out = subprocess.run(["hyprctl", cmd, "-j"],
                             capture_output=True, text=True, timeout=4).stdout
        return json.loads(out)
    except Exception:
        return []


def capture_visible(thumbs=THUMBS):
    os.makedirs(thumbs, exist_ok=True)
    mons = _json("monitors")
    clients = _json("clients")
    if not mons or not clients:
        return 0
    active = {m.get("activeWorkspace", {}).get("id") for m in mons}
    live = set()
    n = 0
    for c in clients:
        if c.get("workspace", {}).get("id") not in active:
            continue
        if not c.get("mapped", True) or c.get("hidden", False):
            continue
        w, h = c.get("size", [0, 0])
        x, y = c.get("at", [0, 0])
        if w <= 0 or h <= 0:
            continue
        addr = c.get("address", "").replace("0x", "")
        if not addr:
            continue
        live.add(addr)
        path = os.path.join(thumbs, addr + ".png")
        try:
            subprocess.run(["grim", "-g", "%d,%d %dx%d" % (x, y, w, h), path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5)
            n += 1
        except Exception:
            pass
    return n


if __name__ == "__main__":
    print("captured", capture_visible())
