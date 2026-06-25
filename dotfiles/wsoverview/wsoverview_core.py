#!/usr/bin/env python3
"""Network-graph workspace overview — pure-cairo model + layout + render.

No GTK dependency, so it renders headlessly for tests. The overlay app feeds
live hyprctl data; the test harness feeds mock data. All text uses the cairo
"toy" API so it behaves identically in the sandbox and the VM.

Pipeline:  build_model(...) -> layout(model, W, H) -> render(cr, lay, model, ...)
Interaction helpers: pick(lay, x, y) (what's grabbable under the cursor) and
drop_target(lay, x, y) (where a drag would land). The overlay turns those
descriptors into hyprctl dispatch calls.
"""
import os
import math
import hashlib
import cairo

# ---- Anduril palette -------------------------------------------------------
BG        = (0.906, 0.894, 0.871)
GRID      = (0.72, 0.71, 0.68)      # dot grid (denser + a touch darker)
TICK      = (0.62, 0.61, 0.58)      # edge crosshairs
TELEM     = (0.46, 0.45, 0.43)
CHARCOAL  = (0.227, 0.227, 0.227)
LINE      = (0.30, 0.30, 0.31)
DOT       = (0.24, 0.24, 0.25)
ACCENT    = (0.851, 0.318, 0.184)
ACCENT_FILL = (0.851, 0.318, 0.184, 0.12)
BOX_FILL  = (0.227, 0.227, 0.239)
BOX_EDGE  = (0.15, 0.15, 0.16)
WIN_FILL  = (0.149, 0.149, 0.165)
WIN_EDGE  = (0.10, 0.10, 0.11)

APP_PALETTE = [
    (0.36, 0.45, 0.55), (0.45, 0.40, 0.52), (0.50, 0.42, 0.36),
    (0.36, 0.50, 0.45), (0.52, 0.46, 0.36), (0.42, 0.44, 0.50),
]
NAME_MAP = {
    "kitty": "KITTY", "firefox": "FIREFOX", "org.mozilla.firefox": "FIREFOX",
    "thunar": "THUNAR", "nautilus": "NAUTILUS", "org.gnome.nautilus": "NAUTILUS",
    "mpv": "MPV", "spotify": "SPOTIFY", "code": "CODE", "btop": "BTOP",
    "htop": "HTOP", "nvim": "NVIM",
}


def app_name(cls, title=""):
    if not cls:
        cls = title or "WINDOW"
    key = cls.lower()
    if key in NAME_MAP:
        return NAME_MAP[key]
    return cls.split(".")[-1].upper()[:12]


def app_color(cls):
    h = int(hashlib.md5((cls or "x").encode()).hexdigest(), 16)
    return APP_PALETTE[h % len(APP_PALETTE)]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
def _visible(c):
    s = c.get("size", [0, 0])
    return (c.get("mapped", True) and not c.get("hidden", False)
            and s[0] > 0 and s[1] > 0)


def _norm(windows, ref):
    rx, ry, rw, rh = ref
    if rw <= 0 or rh <= 0:
        return [(0, 0, 1, 1) for _ in windows]
    out = []
    for c in windows:
        x, y = c.get("at", [rx, ry])
        w, h = c.get("size", [rw, rh])
        out.append(((x - rx) / rw, (y - ry) / rh, w / rw, h / rh))
    return out


def _bbox(windows):
    xs = [c.get("at", [0, 0])[0] for c in windows]
    ys = [c.get("at", [0, 0])[1] for c in windows]
    xe = [c.get("at", [0, 0])[0] + c.get("size", [0, 0])[0] for c in windows]
    ye = [c.get("at", [0, 0])[1] + c.get("size", [0, 0])[1] for c in windows]
    x0, y0 = min(xs), min(ys)
    return (x0, y0, max(xe) - x0 or 1, max(ye) - y0 or 1)


def _win(c, thumb_dir):
    addr = c.get("address", "")
    thumb = os.path.join(thumb_dir, addr.replace("0x", "") + ".png") if addr else None
    if not (thumb and os.path.exists(thumb)):
        thumb = None
    cls = c.get("class", "") or c.get("initialClass", "")
    return {
        "addr": addr,
        "app": app_name(cls, c.get("title", "")),
        "color": app_color(cls),
        "thumb": thumb,
        "floating": c.get("floating", False),
    }


def build_model(monitors, workspaces, clients, thumb_dir):
    active_ws = {}
    for m in monitors:
        active_ws[m.get("activeWorkspace", {}).get("id")] = m.get("id")
    active_ws_ids = set(active_ws.keys())

    by_ws = {}
    for c in clients:
        by_ws.setdefault(c.get("workspace", {}).get("id"), []).append(c)

    mons = []
    for m in sorted(monitors, key=lambda m: m.get("x", 0)):
        awid = m.get("activeWorkspace", {}).get("id")
        wins = [c for c in by_ws.get(awid, []) if _visible(c)]
        mw, mh = m.get("width", 1920), m.get("height", 1080)
        ref = (m.get("x", 0), m.get("y", 0), mw, mh)
        rels = _norm(wins, ref)
        mons.append({
            "id": "mon:%s" % m.get("id"),
            "name": m.get("name", ""),
            "ws": awid,
            "w": mw, "h": mh,
            "label": "MONITOR %s" % (m.get("id", 0) + 1),
            "empty": len(wins) == 0,
            "windows": [dict(_win(c, thumb_dir), rel=r) for c, r in zip(wins, rels)],
        })

    boxes, free = [], []
    ws_meta = {w.get("id"): w for w in workspaces}
    for wid, cs in sorted(by_ws.items(), key=lambda kv: (kv[0] is None, kv[0])):
        if wid in active_ws_ids or wid is None:
            continue
        if wid < 0:                                  # special / scratchpad
            for c in cs:
                free.append(dict(_win(c, thumb_dir), ws=wid))
            continue
        tiled = [c for c in cs if not c.get("floating", False)]
        for c in (c for c in cs if c.get("floating", False)):
            free.append(dict(_win(c, thumb_dir), ws=wid))
        if not tiled:
            continue
        rels = _norm(tiled, _bbox(tiled))
        name = ws_meta.get(wid, {}).get("name", str(wid))
        boxes.append({
            "id": "ws:%s" % wid, "ws": wid,
            "label": ("WS %s" % name).upper(),
            "windows": [dict(_win(c, thumb_dir), rel=r) for c, r in zip(tiled, rels)],
        })

    inactive = sum(len(b["windows"]) for b in boxes) + len(free)
    active = sum(len(m["windows"]) for m in mons)
    return {"monitors": mons, "boxes": boxes, "free": free,
            "active_count": active, "inactive_count": inactive}


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def _seed(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def _place_tiled(rect, windows):
    """Return [(win, (x,y,w,h)), ...] tiled inside rect from each win['rel']."""
    cx, cy, cw, ch = rect
    pad = 8
    inx, iny, inw, inh = cx + pad, cy + pad, cw - 2 * pad, ch - 2 * pad
    out = []
    for win in windows:
        rx, ry, rw, rh = win["rel"]
        r = (inx + rx * inw, iny + ry * inh,
             max(14, rw * inw - 3), max(11, rh * inh - 3))
        out.append((win, r))
    return out


def layout(model, W, H):
    margin = 42
    lay = {"W": W, "H": H, "mons": [], "boxes": [], "free": [],
           "conns": [], "_centers": {}}

    # --- monitor row: true aspect, scaled down, left-aligned ---
    gap = 26
    mb_h = 178
    top_y = 72
    mons = model["monitors"][:3]
    widths = [mb_h * ((m["w"] / m["h"]) if m["h"] else 16 / 9) for m in mons]
    total = (sum(widths) + gap * (len(widths) - 1)) if widths else 0
    x = max(margin, (W - total) / 2)               # centre the monitor row
    for mon, mb_w in zip(mons, widths):
        rect = (x, top_y, mb_w, mb_h)
        wins = _place_tiled(rect, mon["windows"])
        lay["mons"].append({"id": mon["id"], "rect": rect, "mon": mon, "wins": wins})
        x += mb_w + gap

    area_top = top_y + mb_h + 84
    area_bot = H - margin - 24

    # --- inactive workspace boxes: left column with organic x jitter ---
    boxes = model["boxes"]
    n = max(1, len(boxes))
    bh = max(120, min(190, (area_bot - area_top - (n - 1) * 36) / n)) if boxes else 150
    for i, b in enumerate(boxes):
        sd = _seed(b["id"])
        bw = min(W * 0.34, 200 + 26 * math.sqrt(max(1, len(b["windows"]))))
        rect = (margin + (sd % 70), area_top + i * (bh + 36), bw, bh)
        wins = _place_tiled(rect, b["windows"])
        cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
        lay["boxes"].append({"id": b["id"], "rect": rect, "box": b, "wins": wins,
                             "center": (cx, cy)})
        lay["_centers"][b["id"]] = (cx, cy)

    # --- free floating nodes: jittered grid on the right ---
    free = model["free"]
    fx0, fx1 = W * 0.46, W - margin - 96
    fy0, fy1 = area_top - 8, area_bot - 40
    cols = max(1, int((fx1 - fx0) // 150))
    nw, nh = 100, 72
    for i, f in enumerate(free):
        sd = _seed(f["addr"] or str(i))
        cell_w = (fx1 - fx0) / cols
        fxk, fyk = i % cols, i // cols
        fx = fx0 + fxk * cell_w + (sd % 46)
        fy = min(fy0 + fyk * 134 + (sd // 47 % 54), fy1)
        fid = "free:%s" % (f["addr"] or i)
        cx, cy = fx + nw / 2, fy + nh / 2
        lay["free"].append({"id": fid, "rect": (fx, fy, nw, nh), "win": f})
        lay["_centers"][fid] = (cx, cy)
        f["_id"] = fid

    # --- connection web (boxes <-> their free children + box chain) ---
    box_by_ws = {b["box"]["ws"]: b["id"] for b in lay["boxes"]}
    for f in free:
        bid = box_by_ws.get(f.get("ws"))
        if bid:
            lay["conns"].append((bid, f["_id"]))
    bids = [b["id"] for b in lay["boxes"]]
    for i in range(len(bids) - 1):
        lay["conns"].append((bids[i], bids[i + 1]))
    for j, f in enumerate(free):
        if bids and j % 2 == 1:
            tgt = bids[_seed(f["_id"]) % len(bids)]
            if (tgt, f["_id"]) not in lay["conns"]:
                lay["conns"].append((tgt, f["_id"]))
    return lay


def _in(rect, x, y, pad=0):
    rx, ry, rw, rh = rect
    return rx - pad <= x <= rx + rw + pad and ry - pad <= y <= ry + rh + pad


# ---------------------------------------------------------------------------
# Interaction: what can be grabbed, and where a drag lands
# ---------------------------------------------------------------------------
def pick(lay, x, y):
    """Return a grab descriptor for the draggable under the cursor, or None."""
    for m in lay["mons"]:                         # a window inside a monitor
        for win, r in m["wins"]:
            if _in(r, x, y):
                return {"kind": "win", "addr": win["addr"], "win": win,
                        "from": "mon", "rect": r}
    for f in lay["free"]:                          # a free floating window
        if _in(f["rect"], x, y):
            return {"kind": "win", "addr": f["win"]["addr"], "win": f["win"],
                    "from": "free", "rect": f["rect"]}
    for b in lay["boxes"]:                          # a whole inactive workspace
        if _in(b["rect"], x, y, 14):
            return {"kind": "box", "ws": b["box"]["ws"], "box": b["box"],
                    "rect": b["rect"]}
    return None


def hover_id(lay, x, y):
    """Lightweight id under cursor for non-drag highlight."""
    for f in lay["free"]:
        if _in(f["rect"], x, y, 14):
            return f["id"]
    for b in lay["boxes"]:
        if _in(b["rect"], x, y, 14):
            return b["id"]
    return None


def drop_target(lay, x, y):
    for m in lay["mons"]:
        if _in(m["rect"], x, y):
            return {"kind": "monitor", "mon": m["mon"], "id": m["id"]}
    for b in lay["boxes"]:
        if _in(b["rect"], x, y, 8):
            return {"kind": "box", "ws": b["box"]["ws"], "id": b["id"]}
    return {"kind": "canvas"}


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def _text(cr, s, x, y, size, color, mono=False, bold=False, align="center"):
    cr.select_font_face("monospace" if mono else "sans-serif",
                        cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    ext = cr.text_extents(s)
    if align == "center":
        tx = x - ext.width / 2 - ext.x_bearing
    elif align == "right":
        tx = x - ext.width
    else:
        tx = x
    cr.set_source_rgb(*color)
    cr.move_to(tx, y - ext.y_bearing)
    cr.show_text(s)


def _thumb_or_stub(cr, rect, win):
    x, y, w, h = rect
    cr.save()
    cr.rectangle(x, y, w, h)
    cr.clip()
    drawn = False
    if win.get("thumb"):
        try:
            img = cairo.ImageSurface.create_from_png(win["thumb"])
            iw, ih = img.get_width(), img.get_height()
            if iw and ih:
                s = max(w / iw, h / ih)
                cr.save()
                cr.translate(x, y)
                cr.scale(s, s)
                cr.set_source_surface(img, 0, 0)
                cr.get_source().set_filter(cairo.FILTER_GOOD)
                cr.paint()
                cr.restore()
                drawn = True
        except Exception:
            drawn = False
    if not drawn:
        cr.set_source_rgb(*WIN_FILL)
        cr.rectangle(x, y, w, h)
        cr.fill()
        hb = max(7, h * 0.2)
        cr.set_source_rgb(*win["color"])
        cr.rectangle(x, y, w, hb)
        cr.fill()
        cr.set_source_rgba(0.7, 0.7, 0.72, 0.5)
        cr.set_line_width(1)
        for k in range(3):
            ly = y + hb + 8 + k * 9
            if ly < y + h - 4:
                cr.move_to(x + 6, ly)
                cr.line_to(x + w * (0.8 - 0.16 * k), ly)
                cr.stroke()
    cr.restore()


def _win_rects(cr, wins):
    for win, r in wins:
        _thumb_or_stub(cr, r, win)
        cr.set_source_rgb(*WIN_EDGE)
        cr.set_line_width(1)
        cr.rectangle(*r)
        cr.stroke()


def _dashed_empty(cr, rect):
    x, y, w, h = rect
    cr.set_source_rgb(*TICK)
    cr.set_line_width(1)
    cr.set_dash([5, 5])
    cr.rectangle(x + 10, y + 10, w - 20, h - 20)
    cr.stroke()
    cr.move_to(x + 10, y + 10); cr.line_to(x + w - 10, y + h - 10)
    cr.move_to(x + w - 10, y + 10); cr.line_to(x + 10, y + h - 10)
    cr.stroke()
    cr.set_dash([])


def _background(cr, W, H):
    cr.set_source_rgb(*BG)
    cr.paint()
    step = 23
    cr.set_source_rgb(*GRID)
    for gx in range(step, W, step):
        for gy in range(step, H, step):
            cr.rectangle(gx - 0.7, gy - 0.7, 1.5, 1.5)
    cr.fill()
    cr.set_source_rgb(*TICK)
    cr.set_line_width(1)
    nx = max(1, W // 5)
    ny = max(1, H // 5)
    for gx in range(0, W + 1, nx):
        for ty in (9, H - 9):
            cr.move_to(gx - 6, ty); cr.line_to(gx + 6, ty)
            cr.move_to(gx, ty - 6); cr.line_to(gx, ty + 6)
    for gy in range(0, H + 1, ny):
        for tx in (9, W - 9):
            cr.move_to(tx - 6, gy); cr.line_to(tx + 6, gy)
            cr.move_to(tx, gy - 6); cr.line_to(tx, gy + 6)
    cr.stroke()


def _ghost(cr, drag):
    """Draw the dragged item following the cursor."""
    x, y = drag["x"], drag["y"]
    desc = drag["desc"]
    cr.save()
    cr.push_group()
    if desc["kind"] == "win":
        w, h = 110, 78
        r = (x - w / 2, y - h / 2, w, h)
        _thumb_or_stub(cr, r, desc["win"])
        cr.set_source_rgb(*ACCENT)
        cr.set_line_width(2)
        cr.rectangle(*r)
        cr.stroke()
        _text(cr, desc["win"]["app"], x, y + h / 2 + 6, 12, CHARCOAL, mono=True)
    else:
        w, h = 120, 84
        cr.set_source_rgb(*BOX_FILL)
        cr.rectangle(x - w / 2, y - h / 2, w, h)
        cr.fill()
        cr.set_source_rgb(*ACCENT)
        cr.set_line_width(2)
        cr.rectangle(x - w / 2, y - h / 2, w, h)
        cr.stroke()
        _text(cr, desc["box"]["label"], x, y, 13, (0.9, 0.9, 0.9), mono=True)
    cr.pop_group_to_source()
    cr.paint_with_alpha(0.85)
    cr.restore()


def render(cr, lay, model, hover=None, drag=None):
    W, H = lay["W"], lay["H"]
    _background(cr, W, H)

    _text(cr, "ACTIVE NODES: %d" % model["active_count"], 16, 14, 13, TELEM,
          mono=True, align="left")
    _text(cr, "INACTIVE: %d" % model["inactive_count"], 16, 32, 13, TELEM,
          mono=True, align="left")
    _text(cr, "FIG.2  WORKSPACE TOPOLOGY", W - 16, H - 24, 12, TELEM,
          mono=True, align="right")

    target_id = drag["target"].get("id") if drag and drag.get("target") else None

    hi = set()
    if hover:
        for a, b in lay["conns"]:
            if hover in (a, b):
                hi.add((a, b))

    for a, b in lay["conns"]:
        pa, pb = lay["_centers"].get(a), lay["_centers"].get(b)
        if not pa or not pb:
            continue
        accent = (a, b) in hi
        cr.set_source_rgb(*(ACCENT if accent else LINE))
        cr.set_line_width(1.4 if accent else 1)
        cr.move_to(*pa); cr.line_to(*pb); cr.stroke()
        mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
        for p in (pa, pb, mid):
            cr.set_source_rgb(*(ACCENT if accent else DOT))
            cr.arc(p[0], p[1], 2.4, 0, 2 * math.pi)
            cr.fill()

    # monitor row
    for m in lay["mons"]:
        x, y, w, h = m["rect"]
        mon = m["mon"]
        is_t = target_id == m["id"]
        _text(cr, mon["label"], x + 2, y - 18, 12, ACCENT, mono=True, align="left")
        if mon["empty"]:
            _dashed_empty(cr, m["rect"])
        else:
            _win_rects(cr, m["wins"])
        if is_t:
            cr.set_source_rgba(*ACCENT_FILL)
            cr.rectangle(x, y, w, h); cr.fill()
        cr.set_source_rgb(*ACCENT)
        cr.set_line_width(2.6 if is_t else 1.8)
        cr.rectangle(x, y, w, h); cr.stroke()

    # inactive workspace boxes
    for b in lay["boxes"]:
        x, y, w, h = b["rect"]
        accent = (b["id"] == hover) or (b["id"] == target_id)
        cr.set_source_rgb(*BOX_FILL)
        cr.rectangle(x, y, w, h); cr.fill()
        _win_rects(cr, b["wins"])
        cr.set_source_rgb(*(ACCENT if accent else BOX_EDGE))
        cr.set_line_width(2 if accent else 1.2)
        cr.rectangle(x, y, w, h); cr.stroke()
        _text(cr, b["box"]["label"], x + w / 2, y + h + 8, 12, CHARCOAL, mono=True)

    # free floating nodes
    for f in lay["free"]:
        x, y, w, h = f["rect"]
        accent = (f["id"] == hover)
        _thumb_or_stub(cr, f["rect"], f["win"])
        cr.set_source_rgb(*(ACCENT if accent else WIN_EDGE))
        cr.set_line_width(1.6 if accent else 1)
        cr.rectangle(x, y, w, h); cr.stroke()
        _text(cr, f["win"]["app"], x + w / 2, y + h + 8, 12, CHARCOAL, mono=True)

    if drag:
        _ghost(cr, drag)


if __name__ == "__main__":
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 1024)
    cr = cairo.Context(surf)
    m = build_model([], [], [], "/tmp")
    render(cr, layout(m, 1024, 1024), m)
    surf.write_to_png("/tmp/wsoverview_empty.png")
    print("ok")
