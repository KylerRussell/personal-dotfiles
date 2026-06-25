#!/usr/bin/env python3
"""Workspace-overview thumbnail daemon.

Keeps /tmp/wsoverview/thumbs fresh so the overview shows real window content —
including a window's *last visible* frame after it has been parked on a hidden
workspace. It captures on two triggers:

  * Hyprland IPC events (socket2) — workspace switches, window moves, focus
    changes, etc. (debounced so a burst of events = one capture).
  * A slow periodic backstop, so a window that is about to be hidden has a
    recent snapshot even if no event fires first.

Launched once from hyprland.conf:  exec-once = .../thumb-daemon.py
"""
import os
import sys
import time
import socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thumb_capture import capture_visible, THUMBS  # noqa: E402

# events that change what's on screen -> snapshot the (still) visible windows
TRIGGERS = (
    "workspace>>", "workspacev2>>", "focusedmon>>", "focusedmonv2>>",
    "movewindow>>", "movewindowv2>>", "openwindow>>", "closewindow>>",
    "activewindow>>", "fullscreen>>", "changefloatingmode>>",
)
PERIODIC = 5.0      # seconds; backstop capture
DEBOUNCE = 0.6      # seconds; coalesce event bursts


def socket_path():
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not sig:
        return None
    xrd = os.environ.get("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid())
    return os.path.join(xrd, "hypr", sig, ".socket2.sock")


def main():
    os.makedirs(THUMBS, exist_ok=True)
    capture_visible()                      # initial snapshot
    last = time.time()

    path = socket_path()
    if not path or not os.path.exists(path):
        # No event socket (e.g. not under Hyprland) -> periodic only.
        while True:
            time.sleep(PERIODIC)
            capture_visible()

    while True:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(path)
            s.settimeout(PERIODIC)
            buf = b""
            while True:
                try:
                    data = s.recv(4096)
                    if not data:
                        break
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        ev = line.decode("utf-8", "replace")
                        if ev.startswith(TRIGGERS):
                            now = time.time()
                            if now - last >= DEBOUNCE:
                                capture_visible()
                                last = now
                except socket.timeout:
                    capture_visible()         # periodic backstop
                    last = time.time()
        except Exception:
            time.sleep(2)                     # socket dropped -> reconnect


if __name__ == "__main__":
    main()
