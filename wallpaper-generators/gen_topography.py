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
# bbox centred on KC and sized to the right-panel aspect (1280x1080) so the
# contours fill it edge-to-edge instead of sitting as a square block in the middle.
_DLAT=0.125; _DLON=0.1906
W,S,E,N = CENTER[1]-_DLON, CENTER[0]-_DLAT, CENTER[1]+_DLON, CENTER[0]+_DLAT
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","dotfiles","hypr","wallpapers","topography.png")

print("downloading USGS 3DEP elevation ...")
dem=py3dep.get_dem((W,S,E,N), resolution=30)
dem=dem.rio.reproject("EPSG:4326")        # ensure lon/lat so it lines up with rivers
dem=dem.where(dem > -1e6)                  # mask nodata
z=dem.values; x=dem.x.values; y=dem.y.values
zmin,zmax=np.nanmin(z),np.nanmax(z)
print(f"  elevation {zmin:.0f}-{zmax:.0f} m, grid {z.shape}")

fig=plt.figure(figsize=(12.8,10.8),dpi=100); fig.patch.set_facecolor(BG)
ax=fig.add_axes([0,0,1,1]); ax.set_facecolor(BG); ax.axis("off")
ax.set_aspect(1/np.cos(np.radians(CENTER[0])))   # geographic aspect correction

lv=np.linspace(zmin, zmax, 24)
ax.contour(x, y, z, levels=lv,      colors=LINE,  linewidths=0.4, zorder=2)
ax.contour(x, y, z, levels=lv[::4], colors=INDEX, linewidths=0.7, zorder=3)

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

# Composite onto the canvas, nudged a little left of the other panels, with its
# left/right edges feathered into the background so there's no hard seam.
from PIL import Image as _PILImage
_BG_RGB=(233,231,226)
_m=_PILImage.open(OUT).convert("RGB")
_XOFF=470          # panel left edge in px (smaller = further left)
_FADE=230          # px over which contours fade into the background each side
_mask=np.full((_m.height,_m.width),255,np.uint8)
_ramp=(np.linspace(0,1,_FADE)*255).astype(np.uint8)
_mask[:,:_FADE]=_ramp[np.newaxis,:]
_mask[:,-_FADE:]=_ramp[::-1][np.newaxis,:]
_canvas=_PILImage.new("RGB",(1920,1080),_BG_RGB)
_canvas.paste(_m,(_XOFF,0),_PILImage.fromarray(_mask,"L"))
_canvas.save(OUT)
