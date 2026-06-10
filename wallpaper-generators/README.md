# Wallpaper generators

Scripts that build the three text-free 1920x1080 wallpapers used by this
dotfiles setup. They write straight into `../dotfiles/hypr/wallpapers/`.

All three share the palette: warm gray base `#e9e7e2`, charcoal/gray line work,
red-orange accents (`#d9512f`). No text is baked in — the conky overlay draws
the clock, telemetry, and figure labels on top.

| Script | Source data | Network needed? |
|--------|-------------|-----------------|
| `gen_globe.py` | Natural Earth 110m (bundled in `data/`) | No |
| `gen_citymap.py` | OpenStreetMap streets + waterways (osmnx) | Yes |
| `gen_topography.py` | USGS 3DEP elevation + OSM rivers (py3dep) | Yes |

## Usage

```bash
pip install --break-system-packages -r requirements.txt

python3 gen_globe.py         # offline, instant
python3 gen_citymap.py       # downloads KC street network (~10-30s)
python3 gen_topography.py    # downloads KC elevation tile (~30-60s)
```

The globe runs anywhere. The city and topo scripts must run somewhere with
internet access (the Arch VM works — it can already reach GitHub). They were
tested against osmnx 1.9-2.x and py3dep 0.16+.

## Customising

- `CENTER` / `KC` — the lat/lon the map is built around (default Kansas City,
  39.0997, -94.5786).
- `DIST` (city) / bbox `W,S,E,N` (topo) — how much area to cover.
- `ARC_END` (globe) — where the red trajectory arc lands.
- The `BG / ST / HW / RED / ...` colour constants at the top of each file.
