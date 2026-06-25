#!/usr/bin/env python3
"""Network-graph workspace overview overlay.

A full-screen gtk-layer-shell overlay (on the focused monitor) drawing the live
Hyprland topology as a node graph: the three monitors up top with tiled
previews, inactive workspaces as dark boxes, floating windows as free nodes,
joined by a charcoal web. Hover highlights a node + its links in red-orange.

Drag-and-drop (live, via hyprctl):
  * drag a free window or a window out of a monitor -> drop on a MONITOR to show
    it there, on a WORKSPACE box to park it there, or on empty canvas to park it
    on a fresh empty workspace.
  * drag a whole inactive WORKSPACE box -> drop on a MONITOR to display it there.

Toggle with Super+Tab (single instance via PIDFILE). Esc / Super+Tab closes.
"""
import os
import sys
import json
import time
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
DEVNULL = subprocess.DEVNULL


def hypr(cmd):
    try:
        return json.loads(subprocess.run(["hyprctl", cmd, "-j"],
                          capture_output=True, text=True, timeout=4).stdout)
    except Exception:
        return []


def dispatch(*args):
    try:
        subprocess.run(["hyprctl", "dispatch", *[str(a) for a in args]],
                       stdout=DEVNULL, stderr=DEVNULL, timeout=4)
    except Exception:
        pass


def gather_model():
    return core.build_model(hypr("monitors"), hypr("workspaces"),
                            hypr("clients"), THUMBS), hypr("monitors")


def focused_monitor(mons):
    for m in mons:
        if m.get("focused"):
            return m
    return mons[0] if mons else {"x": 0, "y": 0, "width": 1920, "height": 1080}


def first_empty_ws():
    used = {w.get("id") for w in hypr("workspaces") if w.get("windows", 0) > 0}
    i = 1
    while i in used:
        i += 1
    return i


class Overview(Gtk.Window):
    def __init__(self, model, mon):
        super().__init__()
        self.model = model
        self.lay = None
        self.hover = None
        self.drag = None
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
                             | Gdk.EventMask.BUTTON_PRESS_MASK
                             | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.area.connect("draw", self.on_draw)
        self.area.connect("motion-notify-event", self.on_motion)
        self.area.connect("button-press-event", self.on_press)
        self.area.connect("button-release-event", self.on_release)
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
        self._ensure_layout(area.get_allocated_width(), area.get_allocated_height())
        core.render(cr, self.lay, self.model, hover=self.hover, drag=self.drag)
        return False

    def on_motion(self, _w, e):
        if self.lay is None:
            return False
        if self.drag:
            self.drag["x"], self.drag["y"] = e.x, e.y
            self.drag["target"] = core.drop_target(self.lay, e.x, e.y)
            self.area.queue_draw()
            return True
        hit = core.hover_id(self.lay, e.x, e.y)
        if hit != self.hover:
            self.hover = hit
            self.area.queue_draw()
        return True

    def on_press(self, _w, e):
        if self.lay is None or e.button != 1:
            return False
        desc = core.pick(self.lay, e.x, e.y)
        if desc:
            self.drag = {"desc": desc, "x": e.x, "y": e.y, "target": None}
            self.hover = None
            self.area.queue_draw()
        return True

    def on_release(self, _w, e):
        if not self.drag:
            return False
        target = core.drop_target(self.lay, e.x, e.y)
        desc = self.drag["desc"]
        self.drag = None
        self.apply_drop(desc, target)
        self.refresh()
        return True

    def apply_drop(self, desc, target):
        tk = target["kind"]
        if desc["kind"] == "win":
            addr = desc["addr"]
            if not addr:
                return
            if tk == "monitor":
                dispatch("movetoworkspacesilent",
                         "%s,address:%s" % (target["mon"]["ws"], addr))
            elif tk == "box":
                dispatch("movetoworkspacesilent",
                         "%s,address:%s" % (target["ws"], addr))
            elif tk == "canvas":
                dispatch("movetoworkspacesilent",
                         "%s,address:%s" % (first_empty_ws(), addr))
        elif desc["kind"] == "box":
            if tk == "monitor":
                ws, name = desc["ws"], target["mon"]["name"]
                dispatch("moveworkspacetomonitor", ws, name)
                dispatch("focusmonitor", name)
                dispatch("workspace", ws)

    def refresh(self):
        time.sleep(0.06)               # let hyprctl settle
        self.model, _ = gather_model()
        self.lay = None
        self.hover = None
        self.area.queue_draw()

    def on_key(self, _w, e):
        if Gdk.keyval_name(e.keyval) in ("Escape", "Tab", "ISO_Left_Tab"):
            Gtk.main_quit()
        return True


def main():
    os.makedirs(os.path.dirname(PIDFILE), exist_ok=True)
    if os.path.exists(PIDFILE):
        try:
            os.kill(int(open(PIDFILE).read().strip()), signal.SIGTERM)
            os.remove(PIDFILE)
            return
        except (ValueError, ProcessLookupError):
            try:
                os.remove(PIDFILE)
            except OSError:
                pass

    try:
        capture_visible()              # fresh thumbs before our layer maps
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
