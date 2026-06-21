#!/usr/bin/env python3
"""Anduril HUD configuration utility.

One tab per monitor. Telemetry and Hero are composed from individual line
modules (checkboxes), with a Preset dropdown that quick-sets common combos.
Image and Figure are single selections. Apply saves hud.conf and re-runs hud.sh.

Add a new line: drop a script in presets/lines/<section>/ and add it to LINES.
Add a preset: add an entry to PRESETS.
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

# Available line modules per section, in display order: (value, label)
LINES = {
    "telemetry": [
        ("sector", "Sector"), ("lat", "Latitude"), ("lon", "Longitude"), ("elev", "Elevation"),
        ("host", "Host / Kernel"), ("ip", "IP address"), ("uptime", "Uptime"), ("disk", "Disk usage"),
        ("ram", "RAM bar"), ("cpu", "CPU bar"), ("net", "Net throughput"), ("windows", "Active windows"),
        ("git", "Git status"), ("status", "Status"),
    ],
    "hero": [
        ("clock", "Clock (24h)"), ("clock12", "Clock (12h)"), ("date", "Date"), ("city", "City name"),
        ("greeting", "Greeting"), ("season", "Season"), ("weekday", "Week / day"),
        ("sunrise", "Sunrise / sunset"), ("moon", "Moon phase"), ("weather", "Weather"),
    ],
}
# Quick presets: name -> ordered list of line values
PRESETS = {
    "telemetry": {
        "Coordinates": ["sector", "lat", "lon", "elev", "status"],
        "System": ["host", "cpu", "ram", "disk", "uptime", "status"],
        "Network": ["host", "ip", "net", "windows", "status"],
        "Full": ["sector", "lat", "lon", "elev", "host", "ip", "cpu", "ram",
                 "disk", "uptime", "net", "windows", "status"],
        "Minimal": ["sector", "status"],
    },
    "hero": {
        "Clock": ["clock", "date"],
        "Clock + Place": ["clock", "date", "city", "greeting"],
        "Almanac": ["clock", "date", "city", "weekday", "sunrise", "moon"],
        "Everything": ["clock", "date", "city", "greeting", "season",
                       "weekday", "sunrise", "moon", "weather"],
    },
}
IMAGES = [("globe", "Globe"), ("citymap", "City map"), ("topography", "Topography"), ("none", "None")]
FIGURES = [("fig1", "Hemispheric (FIG.1)"), ("fig2", "Urban Grid (FIG.2)"),
           ("fig3", "Terrain (FIG.3)"), ("off", "Off")]
DEFAULTS = {
    "m1": {"telemetry": ["sector", "lat", "lon", "elev", "status"], "hero": ["clock", "date"], "image": "globe", "figure": "fig1"},
    "m2": {"telemetry": ["sector", "lat", "lon", "elev", "status"], "hero": ["clock", "date"], "image": "citymap", "figure": "fig2"},
    "m3": {"telemetry": ["sector", "lat", "lon", "elev", "status"], "hero": ["clock", "date"], "image": "topography", "figure": "fig3"},
}


def load_conf():
    cfg = {f"m{m}": {k: (list(v) if isinstance(v, list) else v)
                     for k, v in DEFAULTS[f"m{m}"].items()} for m in (1, 2, 3)}
    if os.path.exists(CONF):
        for line in open(CONF):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = (p.strip() for p in line.split("=", 1))
            if "_" not in key:
                continue
            mon, sec = key.split("_", 1)
            if mon not in cfg:
                continue
            if sec in ("telemetry", "hero"):
                cfg[mon][sec] = [x for x in val.split(",") if x] if val and val != "off" else []
            elif sec in ("image", "figure"):
                cfg[mon][sec] = val
    return cfg


def save_conf(cfg):
    with open(CONF, "w") as f:
        f.write("# HUD configuration — edited by hud-config.py (or by hand).\n")
        for m in (1, 2, 3):
            mk = f"m{m}"
            for sec in ("telemetry", "hero"):
                lines = cfg[mk][sec]
                f.write(f"{mk}_{sec}={','.join(lines) if lines else 'off'}\n")
            f.write(f"{mk}_image={cfg[mk]['image']}\n")
            f.write(f"{mk}_figure={cfg[mk]['figure']}\n")


class HudConfig(Gtk.Window):
    def __init__(self):
        super().__init__(title="HUD Configuration")
        self.set_border_width(14)
        self.cfg = load_conf()
        self.checks = {}
        self.preset_combos = {}
        self.single = {}
        self._guard = False

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(root)
        nb = Gtk.Notebook()
        root.pack_start(nb, True, True, 0)
        for m in (1, 2, 3):
            nb.append_page(self._monitor_page(m), Gtk.Label(label=f"Monitor {m}"))

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

    def _section(self, m, sec, title):
        frame = Gtk.Frame(label=f"  {title}  ")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(10)
        frame.add(box)

        prow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        prow.pack_start(Gtk.Label(label="Preset:"), False, False, 0)
        combo = Gtk.ComboBoxText()
        combo.append("custom", "Custom")
        for name in PRESETS[sec]:
            combo.append(name, name)
        combo.connect("changed", self._on_preset, m, sec)
        self.preset_combos[(m, sec)] = combo
        prow.pack_start(combo, True, True, 0)
        box.pack_start(prow, False, False, 0)
        box.pack_start(Gtk.Separator(), False, False, 2)

        enabled = set(self.cfg[f"m{m}"][sec])
        for val, label in LINES[sec]:
            cb = Gtk.CheckButton(label=label)
            cb.set_active(val in enabled)          # before connect: no spurious signal
            cb.connect("toggled", self._on_toggle, m, sec)
            self.checks[(m, sec, val)] = cb
            box.pack_start(cb, False, False, 0)
        self._sync_preset_combo(m, sec)
        return frame

    def _monitor_page(self, m):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_border_width(10)
        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cols.pack_start(self._section(m, "telemetry", "Telemetry"), True, True, 0)
        cols.pack_start(self._section(m, "hero", "Hero / Clock"), True, True, 0)
        page.pack_start(cols, True, True, 0)

        srow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for key, opts, title in (("image", IMAGES, "Image"), ("figure", FIGURES, "Figure")):
            b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            b.pack_start(Gtk.Label(label=title, xalign=0.0), False, False, 0)
            combo = Gtk.ComboBoxText()
            for val, label in opts:
                combo.append(val, label)
            combo.set_active_id(self.cfg[f"m{m}"][key])
            self.single[(m, key)] = combo
            b.pack_start(combo, False, False, 0)
            srow.pack_start(b, True, True, 0)
        page.pack_start(srow, False, False, 0)
        return page

    def _current_lines(self, m, sec):
        return [v for v, _ in LINES[sec] if self.checks[(m, sec, v)].get_active()]

    def _sync_preset_combo(self, m, sec):
        cur = self._current_lines(m, sec)
        match = "custom"
        for name, vals in PRESETS[sec].items():
            if vals == cur:
                match = name
                break
        self._guard = True
        self.preset_combos[(m, sec)].set_active_id(match)
        self._guard = False

    def _on_preset(self, combo, m, sec):
        if self._guard:
            return
        name = combo.get_active_id()
        if name not in PRESETS[sec]:
            return
        vals = set(PRESETS[sec][name])
        self._guard = True
        for v, _ in LINES[sec]:
            self.checks[(m, sec, v)].set_active(v in vals)
        self._guard = False

    def _on_toggle(self, cb, m, sec):
        if self._guard:
            return
        self._sync_preset_combo(m, sec)

    def on_apply(self, *_):
        for m in (1, 2, 3):
            mk = f"m{m}"
            for sec in ("telemetry", "hero"):
                self.cfg[mk][sec] = self._current_lines(m, sec)
            self.cfg[mk]["image"] = self.single[(m, "image")].get_active_id()
            self.cfg[mk]["figure"] = self.single[(m, "figure")].get_active_id()
        save_conf(self.cfg)
        subprocess.Popen(["bash", HUD])


def main():
    win = HudConfig()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
