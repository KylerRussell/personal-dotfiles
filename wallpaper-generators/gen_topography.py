#!/usr/bin/env python3
"""Kansas City topographic-contour wallpaper from USGS 3DEP elevation,
with rivers traced in red from OpenStreetMap.

    pip install --break-system-packages py3dep osmnx matplotlib numpy rioxarray
    python3 gen_topography.py
Writes ../dotfiles/hypr/wallpapers/topography.png  (1920x1080, text-free).
"""
import os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse
import py3dep
import rioxarray  # noqa: enables the .rio accessor

BG="#e9e7e2"; LINE="#bdb9b0"; INDEX="#a39e94"; RED="#d9512f"
CENTER=(39.0997, -94.5786)               # lat, lon
W,S,E,N = -94.72, 38.97, -94.40, 39.22   # bbox west,south,east,north
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","dotfiles","hypr","wallpapers","topography.png")

print("downloading USGS 3DEP elevation ...")
dem=py3dep.get_dem((W,S,E,N), resolution=30)
dem=dem.rio.reproject("EPSG:4326")        # ensure lon/lat so it lines up with rivers
dem=dem.where(dem > -1e6)                  # mask nodata
z=dem.values; x=dem.x.values; y=dem.y.values
zmin,zmax=np.nanmin(z),np.nanmax(z)
print(f"  elevation {zmin:.0f}-{zmax:.0f} m, grid {z.shape}")

fig=plt.figure(figsize=(19.2,10.8),dpi=100); fig.patch.set_facecolor(BG)
ax=fig.add_axes([0,0,1,1]); ax.set_facecolor(BG); ax.axis("off")
ax.set_aspect(1/np.cos(np.radians(CENTER[0])))   # geographic aspect correction

lv=np.linspace(zmin, zmax, 40)
ax.contour(x, y, z, levels=lv,      colors=LINE,  linewidths=0.4, zorder=2)
ax.contour(x, y, z, levels=lv[::5], colors=INDEX, linewidths=0.8, zorder=3)

try:
    print("downloading rivers ...")
    import osmnx as ox
    riv=ox.features_from_point(CENTER, tags={"waterway":["river","stream"]}, dist=11000)
    riv=riv[riv.geom_type.isin(["LineString","MultiLineString"])]
    if len(riv): riv.plot(ax=ax, color=RED, linewidth=1.1, alpha=0.8, zorder=4)
except Exception as e:
    print("  (river overlay skipped:", e, ")")

ax.set_xlim(W,E); ax.set_ylim(S,N)
# markers drawn as ellipses so the aspect correction renders them as true circles
asp=1/np.cos(np.radians(CENTER[0]))
def mark(r, **kw):
    ax.add_patch(Ellipse((CENTER[1],CENTER[0]), width=2*r, height=2*r/asp, **kw))
for r,a in [(0.012,0.10),(0.008,0.16),(0.005,0.30)]:
    mark(r, color=RED, alpha=a, zorder=6)
mark(0.02, fill=False, edgecolor=RED, lw=1.4, alpha=0.85, zorder=6)
mark(0.0013, color=RED, zorder=7)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, facecolor=BG, dpi=100)
print("wrote", os.path.abspath(OUT))

# Flatten RGBA -> RGB: conky's ${image} renders alpha images as a white box
# on transparent ARGB windows. A plain-RGB PNG renders correctly.
from PIL import Image as _PILImage
_PILImage.open(OUT).convert("RGB").save(OUT)
