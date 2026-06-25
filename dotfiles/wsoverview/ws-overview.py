#!/usr/bin/env python3
"""Network-graph workspace overview overlay.

A full-screen gtk-layer-shell overlay (on the focused monitor) that draws the
current Hyprland topology as a node graph: the three monitors up top with live
tiled previews, inactive workspaces as dark boxes, floating windows as free
nodes, joined by a charcoal web. Hovering a node highlights it and its links in
red-orange.

Toggle with Super+Tab (single instance via PIDFILE). Esc or Super+Tab closes.
The heavy lifting (model + drawing) lives in wsoverview_core; live window
thumbnails come from thumb_capture / the thumb daemon.
"""
import os
import sys
import json
import signal
import subprocess
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GtkLayerShell

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wsoverview_core as core            # noqa: E402
from thumb_capture import capture_visible, THUMBS  # noqa: E402

PIDFILE = "/tmp/wsoverview/overview.pid"


def hypr(cmd):
    try:
        return json.loads(subprocess.run(["hyprctl", cmd, "-j"],
                          capture_output=True, text=True, timeout=4).stdout)
    except Exception:
        return []


def gather_model():
    mons = hypr("monitors")
    wss = hypr("workspaces")
    clients = hypr("clients")
    return core.build_model(mons, wss, clients, THUMBS), mons


def focused_monitor(mons):
    for m in mons:
        if m.get("focused"):
            return m
    return mons[0] if mons else {"x": 0, "y": 0, "width": 1920, "height": 1080,
                                 "scale": 1}


class Overview(Gtk.Window):
    def __init__(self, model, mon):
        super().__init__()
        self.model = model
        self.lay = None
        self.hover = None
        self.mon = mon

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        gm = self._gdk_monitor(mon)
        if gm:
            GtkLayerShell.set_monitor(self, gm)

        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        self.area = Gtk.DrawingArea()
        self.add(self.area)
        self.area.set_events(Gdk.EventMask.POINTER_MOTION_MASK
                             | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.area.connect("draw", self.on_draw)
        self.area.connect("motion-notify-event", self.on_motion)
        self.connect("key-press-event", self.on_key)

    def _gdk_monitor(self, m):
        disp = Gdk.Display.get_default()
        for i in range(disp.get_n_monitors()):
            gm = disp.get_monitor(i)
            g = gm.get_geometry()
            if g.x == m.get("x") and g.y == m.get("y"):
                return gm
        return None

    def _ensure_layout(self, w, h):
        if self.lay is None or self.lay["W"] != w or self.lay["H"] != h:
            self.lay = core.layout(self.model, w, h)

    def on_draw(self, area, cr):
        w = area.get_allocated_width()
        h = area.get_allocated_height()
        self._ensure_layout(w, h)
        core.render(cr, self.lay, self.model, hover=self.hover)
        return False

    def on_motion(self, _w, e):
        if self.lay is None:
            return False
        hit = core.hit_test(self.lay, e.x, e.y)
        if hit != self.hover:
            self.hover = hit
            self.area.queue_draw()
        return True

    def on_key(self, _w, e):
        name = Gdk.keyval_name(e.keyval)
        if name in ("Escape", "Tab", "ISO_Left_Tab"):
            Gtk.main_quit()
        return True


def main():
    os.makedirs(os.path.dirname(PIDFILE), exist_ok=True)
    # Single-instance toggle: a second launch closes the open overview.
    if os.path.exists(PIDFILE):
        try:
            old = int(open(PIDFILE).read().strip())
            os.kill(old, signal.SIGTERM)
            os.remove(PIDFILE)
            return
        except (ValueError, ProcessLookupError):
            try:
                os.remove(PIDFILE)
            except OSError:
                pass

    # Refresh thumbnails for currently-visible windows BEFORE we map our own
    # layer (otherwise grim would capture this overlay instead of the windows).
    try:
        capture_visible()
    except Exception:
        pass

    model, mons = gather_model()
    mon = focused_monitor(mons)

    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    try:
        win = Overview(model, mon)
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        Gtk.main()
    finally:
        try:
            os.remove(PIDFILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()
