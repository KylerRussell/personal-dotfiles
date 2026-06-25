#!/usr/bin/env python3
"""Network-graph workspace overview — pure-cairo model + layout + render.

This module has NO GTK dependency so it can be rendered headlessly for tests.
The overlay app (ws-overview.py) feeds it live hyprctl data; the test harness
feeds mock data. Everything is drawn with the cairo "toy" text API so it works
identically in the sandbox and in the VM.

Pipeline:  build_model(...) -> layout(model, W, H) -> render(cr, ..., hover)
hit_test(lay, x, y) maps a cursor position back to a node/box id.
"""
import os
import math
import hashlib
import cairo

# ---- Anduril palette -------------------------------------------------------
BG        = (0.906, 0.894, 0.871)   # warm light gray   #e7e4de
GRID      = (0.78, 0.77, 0.74)      # dot grid
TICK      = (0.66, 0.65, 0.62)      # edge crosshairs
TELEM     = (0.46, 0.45, 0.43)      # monospace telemetry text
CHARCOAL  = (0.227, 0.227, 0.227)   # #3a3a3a labels / lines
LINE      = (0.30, 0.30, 0.31)      # connection lines
DOT       = (0.24, 0.24, 0.25)      # junction dots
ACCENT    = (0.851, 0.318, 0.184)   # #d9512f red-orange
BOX_FILL  = (0.227, 0.227, 0.239)   # dark gray workspace box  #3a3a3d
BOX_EDGE  = (0.15, 0.15, 0.16)
WIN_FILL  = (0.149, 0.149, 0.165)   # stylized window body  #26262a
WIN_EDGE  = (0.10, 0.10, 0.11)
PREVIEW_DIM = (0.0, 0.0, 0.0, 0.0)

# stylized window header colors, chosen per app
APP_PALETTE = [
    (0.36, 0.45, 0.55), (0.45, 0.40, 0.52), (0.50, 0.42, 0.36),
    (0.36, 0.50, 0.45), (0.52, 0.46, 0.36), (0.42, 0.44, 0.50),
]

# known class -> display name overrides
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
    short = cls.split(".")[-1]
    return short.upper()[:12]


def app_color(cls):
    h = int(hashlib.md5((cls or "x").encode()).hexdigest(), 16)
    return APP_PALETTE[h % len(APP_PALETTE)]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
def _visible(c):
    return (c.get("mapped", True) and not c.get("hidden", False)
            and c.get("size", [0, 0])[0] > 0 and c.get("size", [0, 0])[1] > 0)


def _norm(windows, ref):
    """Return per-window relative rects (0..1) inside ref=(x,y,w,h)."""
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
    """Assemble the overview model from hyprctl json structures."""
    active_ws = {}
    for m in monitors:
        aw = m.get("activeWorkspace", {})
        active_ws[aw.get("id")] = m.get("id")
    active_ws_ids = set(active_ws.keys())

    by_ws = {}
    for c in clients:
        wid = c.get("workspace", {}).get("id")
        by_ws.setdefault(wid, []).append(c)

    # --- monitor row ---
    mons = []
    for m in sorted(monitors, key=lambda m: m.get("x", 0)):
        awid = m.get("activeWorkspace", {}).get("id")
        wins = [c for c in by_ws.get(awid, []) if _visible(c)]
        ref = (m.get("x", 0), m.get("y", 0), m.get("width", 1920), m.get("height", 1080))
        rels = _norm(wins, ref)
        mons.append({
            "id": "mon:%s" % m.get("id"),
            "label": "MONITOR %s" % (m.get("id", 0) + 1),
            "empty": len(wins) == 0,
            "windows": [dict(_win(c, thumb_dir), rel=r) for c, r in zip(wins, rels)],
        })

    # --- inactive workspace boxes + free floating nodes ---
    boxes, free = [], []
    ws_meta = {w.get("id"): w for w in workspaces}
    for wid, cs in sorted(by_ws.items(), key=lambda kv: (kv[0] is None, kv[0])):
        if wid in active_ws_ids or wid is None:
            continue
        if wid is not None and wid < 0:        # special / scratchpad -> free nodes
            for c in cs:
                free.append(dict(_win(c, thumb_dir), ws=wid))
            continue
        tiled = [c for c in cs if not c.get("floating", False)]
        floaters = [c for c in cs if c.get("floating", False)]
        for c in floaters:
            free.append(dict(_win(c, thumb_dir), ws=wid))
        if not tiled:
            continue
        rels = _norm(tiled, _bbox(tiled))
        name = ws_meta.get(wid, {}).get("name", str(wid))
        boxes.append({
            "id": "ws:%s" % wid,
            "ws": wid,
            "label": ("WS %s" % name).upper(),
            "windows": [dict(_win(c, thumb_dir), rel=r) for c, r in zip(tiled, rels)],
        })

    inactive_count = sum(len(b["windows"]) for b in boxes) + len(free)
    active_count = sum(len(m["windows"]) for m in mons)
    return {
        "monitors": mons, "boxes": boxes, "free": free,
        "active_count": active_count, "inactive_count": inactive_count,
    }


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def _seed(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def layout(model, W, H):
    margin = 42
    lay = {"W": W, "H": H, "mons": [], "nodes": {}, "conns": [], "labels": []}

    # monitor row
    gap = 26
    mb_w = (W - 2 * margin - 2 * gap) / 3.0
    mb_h = min(168, mb_w * 0.46)
    top_y = 70
    for i, mon in enumerate(model["monitors"][:3]):
        rect = (margin + i * (mb_w + gap), top_y, mb_w, mb_h)
        lay["mons"].append({"rect": rect, "mon": mon})

    area_top = top_y + mb_h + 78
    area_bot = H - margin - 22

    # inactive workspace boxes: left column, organic x jitter
    boxes = model["boxes"]
    n = max(1, len(boxes))
    col_x = margin
    col_w = W * 0.34
    bh = min(190, (area_bot - area_top - (n - 1) * 34) / n) if n else 150
    bh = max(120, bh)
    for i, b in enumerate(boxes):
        sd = _seed(b["id"])
        wcount = len(b["windows"])
        bw = min(col_w, 200 + 26 * math.sqrt(max(1, wcount)))
        jx = (sd % 70)
        y = area_top + i * (bh + 34)
        rect = (col_x + jx, y, bw, bh)
        lay["nodes"][b["id"]] = {"rect": rect, "kind": "box", "data": b}

    # free floating nodes: scatter in the right area on a jittered grid
    free = model["free"]
    fx0 = W * 0.46
    fx1 = W - margin - 80
    fy0 = area_top - 10
    fy1 = area_bot - 40
    cols = 3
    nw, nh = 96, 70
    for i, f in enumerate(free):
        sd = _seed(f["addr"] or str(i))
        cxk = i % cols
        ryk = i // cols
        cell_w = (fx1 - fx0) / cols
        x = fx0 + cxk * cell_w + (sd % 46)
        y = fy0 + ryk * 132 + (sd // 47 % 54)
        y = min(y, fy1)
        fid = "free:%s" % (f["addr"] or i)
        lay["nodes"][fid] = {"rect": (x, y, nw, nh), "kind": "free", "data": f}
        f["_id"] = fid

    # connections: free node -> its origin workspace box; chain boxes; a few webs
    box_by_ws = {b["ws"]: b["id"] for b in boxes}
    for f in free:
        bid = box_by_ws.get(f.get("ws"))
        if bid:
            lay["conns"].append((bid, f["_id"]))
    for i in range(len(boxes) - 1):
        lay["conns"].append((boxes[i]["id"], boxes[i + 1]["id"]))
    # extra organic cross-links for the web look
    bids = [b["id"] for b in boxes]
    fids = [f["_id"] for f in free]
    for j, fid in enumerate(fids):
        if bids and j % 2 == 1:
            tgt = bids[(_seed(fid) % len(bids))]
            if (tgt, fid) not in lay["conns"]:
                lay["conns"].append((tgt, fid))
    return lay


def _center(rect):
    x, y, w, h = rect
    return (x + w / 2.0, y + h / 2.0)


def hit_test(lay, x, y):
    # nodes first (front-most), then connection endpoints handled via highlight
    for nid, n in lay["nodes"].items():
        rx, ry, rw, rh = n["rect"]
        if rx <= x <= rx + rw and ry <= y <= ry + rh + 16:
            return nid
    return None


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def _text(cr, s, x, y, size, color, mono=False, bold=False, align="center"):
    cr.select_font_face(
        "monospace" if mono else "sans-serif",
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    cr.set_font_size(size)
    ext = cr.text_extents(s)
    if align == "center":
        tx = x - ext.width / 2 - ext.x_bearing
    elif align == "left":
        tx = x
    else:
        tx = x - ext.width
    ty = y - ext.y_bearing
    cr.set_source_rgb(*color)
    cr.move_to(tx, ty)
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
        hb = max(8, h * 0.2)
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


def _window_tile(cr, rect, win, accent=False):
    _thumb_or_stub(cr, rect, win)
    x, y, w, h = rect
    cr.set_source_rgb(*(ACCENT if accent else WIN_EDGE))
    cr.set_line_width(1.5 if accent else 1)
    cr.rectangle(x, y, w, h)
    cr.stroke()


def _tiled_windows(cr, container, windows, accent=False):
    cx, cy, cw, ch = container
    pad = 8
    inx, iny, inw, inh = cx + pad, cy + pad, cw - 2 * pad, ch - 2 * pad
    for win in windows:
        rx, ry, rw, rh = win["rel"]
        rect = (inx + rx * inw, iny + ry * inh,
                max(16, rw * inw - 3), max(12, rh * inh - 3))
        _thumb_or_stub(cr, rect, win)
        cr.set_source_rgb(*WIN_EDGE)
        cr.set_line_width(1)
        cr.rectangle(*rect)
        cr.stroke()


def _dashed_empty(cr, rect):
    x, y, w, h = rect
    cr.set_source_rgb(*TICK)
    cr.set_line_width(1)
    cr.set_dash([5, 5])
    cr.rectangle(x + 10, y + 10, w - 20, h - 20)
    cr.stroke()
    cr.move_to(x + 10, y + 10)
    cr.line_to(x + w - 10, y + h - 10)
    cr.move_to(x + w - 10, y + 10)
    cr.line_to(x + 10, y + h - 10)
    cr.stroke()
    cr.set_dash([])


def _background(cr, W, H):
    cr.set_source_rgb(*BG)
    cr.paint()
    # dot grid
    step = 26
    cr.set_source_rgb(*GRID)
    for gx in range(step, W, step):
        for gy in range(step, H, step):
            cr.rectangle(gx, gy, 1.2, 1.2)
    cr.fill()
    # edge crosshair ticks
    cr.set_source_rgb(*TICK)
    cr.set_line_width(1)
    for gx in range(0, W + 1, W // 4 if W >= 4 else W):
        for ty in (8, H - 8):
            cr.move_to(gx - 6, ty); cr.line_to(gx + 6, ty)
            cr.move_to(gx, ty - 6); cr.line_to(gx, ty + 6)
    for gy in range(0, H + 1, H // 4 if H >= 4 else H):
        for tx in (8, W - 8):
            cr.move_to(tx - 6, gy); cr.line_to(tx + 6, gy)
            cr.move_to(tx, gy - 6); cr.line_to(tx, gy + 6)
    cr.stroke()


def render(cr, lay, model, hover=None):
    W, H = lay["W"], lay["H"]
    _background(cr, W, H)

    # telemetry
    _text(cr, "ACTIVE NODES: %d" % model["active_count"], 16, 14, 13, TELEM,
          mono=True, align="left")
    _text(cr, "INACTIVE: %d" % model["inactive_count"], 16, 32, 13, TELEM,
          mono=True, align="left")
    _text(cr, "FIG.2  WORKSPACE TOPOLOGY", W - 16, H - 24, 12, TELEM,
          mono=True, align="right")

    # adjacency for hover highlight
    hi_lines = set()
    if hover:
        for a, b in lay["conns"]:
            if hover in (a, b):
                hi_lines.add((a, b))

    # connection lines (under nodes)
    for a, b in lay["conns"]:
        na, nb = lay["nodes"].get(a), lay["nodes"].get(b)
        if not na or not nb:
            continue
        pa, pb = _center(na["rect"]), _center(nb["rect"])
        accent = (a, b) in hi_lines
        cr.set_source_rgb(*(ACCENT if accent else LINE))
        cr.set_line_width(1.4 if accent else 1)
        cr.move_to(*pa)
        cr.line_to(*pb)
        cr.stroke()
        mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
        for p in (pa, pb, mid):
            cr.set_source_rgb(*(ACCENT if accent else DOT))
            cr.arc(p[0], p[1], 2.4, 0, 2 * math.pi)
            cr.fill()

    # monitor row
    for i, mb in enumerate(lay["mons"]):
        x, y, w, h = mb["rect"]
        mon = mb["mon"]
        _text(cr, mon["label"], x + 2, y - 18, 12, ACCENT, mono=True, align="left")
        if mon["empty"]:
            _dashed_empty(cr, mb["rect"])
        else:
            _tiled_windows(cr, mb["rect"], mon["windows"])
        cr.set_source_rgb(*ACCENT)
        cr.set_line_width(1.8)
        cr.rectangle(x, y, w, h)
        cr.stroke()

    # inactive workspace boxes + free nodes
    for nid, n in lay["nodes"].items():
        x, y, w, h = n["rect"]
        accent = (nid == hover)
        if n["kind"] == "box":
            b = n["data"]
            cr.set_source_rgb(*BOX_FILL)
            cr.rectangle(x, y, w, h)
            cr.fill()
            _tiled_windows(cr, n["rect"], b["windows"])
            cr.set_source_rgb(*(ACCENT if accent else BOX_EDGE))
            cr.set_line_width(2 if accent else 1.2)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            _text(cr, b["label"], x + w / 2, y + h + 6, 12, CHARCOAL, mono=True)
        else:
            f = n["data"]
            _window_tile(cr, n["rect"], f, accent=accent)
            _text(cr, f["app"], x + w / 2, y + h + 6, 12, CHARCOAL, mono=True)


# quick self-test when run directly with no data
if __name__ == "__main__":
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 1024)
    cr = cairo.Context(surf)
    m = build_model([], [], [], "/tmp")
    render(cr, layout(m, 1024, 1024), m)
    surf.write_to_png("/tmp/wsoverview_empty.png")
    print("ok")
