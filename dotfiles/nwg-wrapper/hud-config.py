#!/usr/bin/env python3
"""Anduril HUD configuration utility.

A small GTK window with one column per monitor. Each column has dropdowns for
Telemetry / Hero (clock) / Image / Figure. Selections are saved to hud.conf and
applied by re-running hud.sh.

To add a new option: drop a preset file in presets/<section>/ (or a PNG in
~/.config/hypr/wallpapers/ for images) and add it to the matching OPTIONS list
below.
"""
import os
import subprocess
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

HOME = os.path.expanduser("~")
DIR = os.path.join(HOME, ".config", "nwg-wrapper")
CONF = os.path.join(DIR, "hud.conf")
HUD = os.path.join(DIR, "hud.sh")

# (display label, stored value) — extend these as you add presets.
OPTIONS = {
    "telemetry": [("Coordinates", "coordinates"), ("System stats", "system"),
                  ("Minimal", "minimal"), ("Off", "off")],
    "hero":      [("Clock 24h", "clock24"), ("Clock 12h", "clock12"),
                  ("Clock + seconds", "clocksec"), ("Off", "off")],
    "image":     [("Globe", "globe"), ("City map", "citymap"),
                  ("Topography", "topography"), ("None", "none")],
    "figure":    [("Hemispheric (FIG.1)", "fig1"), ("Urban Grid (FIG.2)", "fig2"),
                  ("Terrain (FIG.3)", "fig3"), ("Off", "off")],
}
SECTIONS = [("Telemetry", "telemetry"), ("Hero / Clock", "hero"),
            ("Image", "image"), ("Figure", "figure")]
DEFAULTS = {
    "m1": {"telemetry": "coordinates", "hero": "clock24", "image": "globe", "figure": "fig1"},
    "m2": {"telemetry": "coordinates", "hero": "clock24", "image": "citymap", "figure": "fig2"},
    "m3": {"telemetry": "coordinates", "hero": "clock24", "image": "topography", "figure": "fig3"},
}


def load_conf():
    cfg = {f"m{m}": dict(DEFAULTS[f"m{m}"]) for m in (1, 2, 3)}
    if os.path.exists(CONF):
        for line in open(CONF):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = (p.strip() for p in line.split("=", 1))
            if "_" in key:
                mon, sec = key.split("_", 1)
                if mon in cfg and sec in cfg[mon]:
                    cfg[mon][sec] = val
    return cfg


def save_conf(cfg):
    with open(CONF, "w") as f:
        f.write("# HUD configuration — edited by hud-config.py (or by hand).\n")
        for m in (1, 2, 3):
            for _, sec in SECTIONS:
                f.write(f"m{m}_{sec}={cfg[f'm{m}'][sec]}\n")


class HudConfig(Gtk.Window):
    def __init__(self):
        super().__init__(title="HUD Configuration")
        self.set_border_width(16)
        self.set_resizable(False)
        self.cfg = load_conf()
        self.combos = {}

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(root)

        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        root.pack_start(cols, True, True, 0)

        for m in (1, 2, 3):
            frame = Gtk.Frame(label=f"  Monitor {m}  ")
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            col.set_border_width(12)
            frame.add(col)
            for title, sec in SECTIONS:
                lbl = Gtk.Label(label=title, xalign=0.0)
                lbl.set_margin_top(6)
                col.pack_start(lbl, False, False, 0)
                combo = Gtk.ComboBoxText()
                for disp, val in OPTIONS[sec]:
                    combo.append(val, disp)
                combo.set_active_id(self.cfg[f"m{m}"].get(sec, OPTIONS[sec][0][1]))
                self.combos[(m, sec)] = combo
                col.pack_start(combo, False, False, 0)
            cols.pack_start(frame, True, True, 0)

        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btns.set_halign(Gtk.Align.END)
        close_b = Gtk.Button(label="Close")
        close_b.connect("clicked", lambda *_: self.close())
        apply_b = Gtk.Button(label="Apply")
        apply_b.connect("clicked", self.on_apply)
        apply_b.get_style_context().add_class("suggested-action")
        btns.pack_start(close_b, False, False, 0)
        btns.pack_start(apply_b, False, False, 0)
        root.pack_start(btns, False, False, 0)

    def on_apply(self, *_):
        for (m, sec), combo in self.combos.items():
            val = combo.get_active_id()
            if val:
                self.cfg[f"m{m}"][sec] = val
        save_conf(self.cfg)
        subprocess.Popen(["bash", HUD])


def main():
    win = HudConfig()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
