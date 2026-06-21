#!/usr/bin/env python3
"""Anduril radial (pie) menu.

A gtk-layer-shell overlay that draws a hierarchical pie menu at the cursor.
Left-click a wedge to descend a sub-menu or run its command. The centre
(crosshair at the top level, back-arrow in sub-levels) / right-click / Esc
goes back one level (or closes at the top). Clicking outside closes it.

Single-instance: launching while a menu is open just closes it (toggle), so
Super+Space can't stack copies. The tree lives in menu.json next to this file.
"""
import os
import json
import math
import signal
import subprocess
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GtkLayerShell, Pango, PangoCairo
import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
MENU_FILE = os.path.join(HERE, "menu.json")
PIDFILE = "/tmp/radial-menu.pid"

# Palette
BG       = (1.00, 1.00, 1.00, 0.90)     # frosted white 90%
EDGE     = (0.78, 0.78, 0.78, 0.6)      # subtle outer edge
BORDER   = (0.55, 0.55, 0.55)           # inset outline
DIVIDER  = (0.72, 0.72, 0.72)
TEXT     = (0.227, 0.227, 0.227)        # #3a3a3a
ACCENT   = (0.851, 0.318, 0.184)        # #d9512f
HILITE   = (0.851, 0.318, 0.184, 0.16)  # hovered wedge fill

RADIUS = 178      # outer (white) radius
INSET = 7         # gap between white edge and the gray outline
INNER = 50        # centre "back" zone
LABEL_R = 108     # icon/label anchor distance from centre
ICON_FONT = "Font Awesome 6 Free"


def hypr(args):
    try:
        return subprocess.check_output(["hyprctl"] + args, text=True)
    except Exception:
        return ""


def cursor_pos():
    out = hypr(["cursorpos"]).strip().replace(" ", "")
    try:
        x, y = (int(v) for v in out.split(","))
        return x, y
    except Exception:
        return None


def monitors():
    try:
        return json.loads(hypr(["monitors", "-j"]))
    except Exception:
        return []


class Radial(Gtk.Window):
    def __init__(self, menu):
        super().__init__()
        self.stack = [menu]
        self.hover = -1

        cp = cursor_pos()
        mons = monitors()
        self.mon = None
        if cp and mons:
            cx, cy = cp
            for m in mons:
                if m["x"] <= cx < m["x"] + m["width"] and m["y"] <= cy < m["y"] + m["height"]:
                    self.mon = m
                    break
        if self.mon and cp:
            self.cx, self.cy = cp[0] - self.mon["x"], cp[1] - self.mon["y"]
        else:
            self.mon = mons[0] if mons else {"x": 0, "y": 0, "width": 1920, "height": 1080}
            self.cx, self.cy = self.mon["width"] // 2, self.mon["height"] // 2

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)
        gdkmon = self._gdk_monitor(self.mon)
        if gdkmon:
            GtkLayerShell.set_monitor(self, gdkmon)

        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)

        self.area = Gtk.DrawingArea()
        self.add(self.area)
        self.area.set_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.area.connect("draw", self.on_draw)
        self.area.connect("motion-notify-event", self.on_motion)
        self.area.connect("button-press-event", self.on_button)
        self.connect("key-press-event", self.on_key)

    def _gdk_monitor(self, m):
        disp = Gdk.Display.get_default()
        for i in range(disp.get_n_monitors()):
            gm = disp.get_monitor(i)
            g = gm.get_geometry()
            if g.x == m["x"] and g.y == m["y"]:
                return gm
        return None

    @property
    def node(self):
        return self.stack[-1]

    def children(self):
        return self.node.get("children", [])

    def _index_at(self, mx, my):
        dx, dy = mx - self.cx, my - self.cy
        r = math.hypot(dx, dy)
        kids = self.children()
        if not kids:
            return -1
        if r < INNER:
            return -2
        if r > RADIUS + 24:
            return -1
        ang = (math.atan2(dy, dx) + math.pi / 2) % (2 * math.pi)
        return int(ang / (2 * math.pi) * len(kids)) % len(kids)

    def on_motion(self, _w, e):
        idx = self._index_at(e.x, e.y)
        if idx != self.hover:
            self.hover = idx
            self.area.queue_draw()
        return True

    def on_button(self, _w, e):
        if e.button == 3:
            self._back()
            return True
        if e.button == 1:
            idx = self._index_at(e.x, e.y)
            if idx == -2:
                self._back()
            elif idx == -1:
                self._close()
            else:
                self._activate(idx)
        return True

    def on_key(self, _w, e):
        name = Gdk.keyval_name(e.keyval)
        if name == "Escape":
            self._close()
        elif name in ("BackSpace", "Left"):
            self._back()
        return True

    def _activate(self, idx):
        kids = self.children()
        if idx >= len(kids):
            return
        node = kids[idx]
        if "children" in node:
            self.stack.append(node)
            self.hover = -1
            self.area.queue_draw()
        elif "cmd" in node:
            subprocess.Popen(["bash", "-c", node["cmd"]])
            self._close()

    def _back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.hover = -1
            self.area.queue_draw()
        else:
            self._close()

    def _close(self):
        Gtk.main_quit()

    def _text(self, cr, text, x, y, size, color, family="Barlow Condensed",
              weight=Pango.Weight.NORMAL):
        if not text:
            return
        layout = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription(f"{family} {size}")
        fd.set_weight(weight)
        layout.set_font_description(fd)
        layout.set_text(text, -1)
        w, h = layout.get_pixel_size()
        cr.move_to(x - w / 2, y - h / 2)
        cr.set_source_rgb(*color)
        PangoCairo.show_layout(cr, layout)

    def _draw_back(self, cr, cx, cy):
        cr.set_source_rgb(*TEXT)
        cr.set_line_width(2)
        cr.move_to(cx + 8, cy)
        cr.line_to(cx - 6, cy)
        cr.stroke()
        cr.move_to(cx - 6, cy)
        cr.line_to(cx, cy - 5)
        cr.move_to(cx - 6, cy)
        cr.line_to(cx, cy + 5)
        cr.stroke()

    def on_draw(self, _area, cr):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        kids = self.children()
        n = len(kids)
        if n == 0:
            return
        cx, cy, R = self.cx, self.cy, RADIUS
        CR = R - INSET                      # inset outline / content radius

        cr.set_source_rgba(0, 0, 0, 0.12)   # drop shadow
        cr.arc(cx + 4, cy + 6, R, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(*BG)             # white disk + subtle outer edge
        cr.arc(cx, cy, R, 0, 2 * math.pi)
        cr.fill_preserve()
        cr.set_source_rgba(*EDGE)
        cr.set_line_width(1)
        cr.stroke()
        cr.set_source_rgb(*BORDER)          # inset outline (white rim outside it)
        cr.set_line_width(1)
        cr.arc(cx, cy, CR, 0, 2 * math.pi)
        cr.stroke()

        start = -math.pi / 2
        seg = 2 * math.pi / n
        for i, node in enumerate(kids):
            a0 = start + i * seg
            if i == self.hover:
                cr.set_source_rgba(*HILITE)
                cr.move_to(cx, cy)
                cr.arc(cx, cy, CR, a0, a0 + seg)
                cr.close_path()
                cr.fill()
            cr.set_source_rgb(*DIVIDER)
            cr.set_line_width(1)
            cr.move_to(cx, cy)
            cr.line_to(cx + CR * math.cos(a0), cy + CR * math.sin(a0))
            cr.stroke()
            am = a0 + seg / 2
            ax = cx + LABEL_R * math.cos(am)
            ay = cy + LABEL_R * math.sin(am)
            self._text(cr, node.get("icon", ""), ax, ay - 13, 17, TEXT,
                       family=ICON_FONT, weight=Pango.Weight.HEAVY)
            self._text(cr, node["label"], ax, ay + 10, 13, TEXT)

        # centre: crosshair at the top level, back-arrow inside sub-levels
        if len(self.stack) > 1:
            self._draw_back(cr, cx, cy)
        else:
            cr.set_source_rgb(*DIVIDER)
            cr.set_line_width(1)
            cr.move_to(cx - 7, cy)
            cr.line_to(cx + 7, cy)
            cr.move_to(cx, cy - 7)
            cr.line_to(cx, cy + 7)
            cr.stroke()


def main():
    # Single-instance toggle: if a menu is already open, close it and exit.
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
    try:
        menu = json.load(open(MENU_FILE))
    except Exception as e:
        print("Failed to read menu.json:", e)
        return
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    try:
        win = Radial(menu)
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
