#!/usr/bin/env python3
"""Kansas City street-grid wallpaper from live OpenStreetMap data (osmnx).

    pip install --break-system-packages osmnx matplotlib
    python3 gen_citymap.py
Writes ../dotfiles/hypr/wallpapers/citymap.png  (1920x1080, text-free).
"""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point

BG="#e9e7e2"; ST="#c6c2b9"; MID="#b4afa5"; HW="#a39d92"; WATER="#d3cfc6"; RED="#d9512f"
CENTER=(39.0997, -94.5786)   # lat, lon (downtown KC / river confluence)
DIST=6500                    # metres radius
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","dotfiles","hypr","wallpapers","citymap.png")

ox.settings.use_cache=True; ox.settings.log_console=False

print("downloading street network ...")
G=ox.graph_from_point(CENTER, dist=DIST, network_type="drive", simplify=True)
G=ox.project_graph(G)                      # local UTM -> correct aspect
edges=ox.graph_to_gdfs(G, nodes=False)
crs=edges.crs

def cls(h): return h[0] if isinstance(h,list) else h
edges["c"]=edges["highway"].map(cls)
big  =edges[edges["c"].isin(["motorway","trunk","primary","motorway_link","trunk_link"])]
mid  =edges[edges["c"].isin(["secondary","tertiary","secondary_link","tertiary_link"])]
small=edges[~edges.index.isin(big.index) & ~edges.index.isin(mid.index)]

water=None
try:
    print("downloading waterways ...")
    water=ox.features_from_point(CENTER, tags={"waterway":["river","stream","canal"],
                                               "natural":["water"]}, dist=DIST).to_crs(crs)
except Exception as e:
    print("  (water fetch skipped:", e, ")")

fig=plt.figure(figsize=(19.2,10.8),dpi=100); fig.patch.set_facecolor(BG)
ax=fig.add_axes([0,0,1,1]); ax.set_facecolor(BG); ax.axis("off"); ax.set_aspect("equal")

if water is not None and len(water):
    poly=water[water.geom_type.isin(["Polygon","MultiPolygon"])]
    line=water[water.geom_type.isin(["LineString","MultiLineString"])]
    if len(poly): poly.plot(ax=ax, facecolor=WATER, edgecolor="none", zorder=1)
    if len(line): line.plot(ax=ax, color=WATER, linewidth=6, zorder=1)

small.plot(ax=ax, color=ST,  linewidth=0.45, zorder=2)
mid.plot(  ax=ax, color=MID, linewidth=0.8,  zorder=3)
big.plot(  ax=ax, color=HW,  linewidth=1.8,  zorder=4)

pt=gpd.GeoSeries([Point(CENTER[1],CENTER[0])], crs=4326).to_crs(crs).iloc[0]
mx,my=pt.x, pt.y
for r,a in [(900,0.10),(600,0.16),(360,0.30)]:
    ax.add_patch(Circle((mx,my), r, color=RED, alpha=a, zorder=6))
ax.add_patch(Circle((mx,my), 1500, fill=False, edgecolor=RED, lw=1.4, alpha=0.85, zorder=6))
ax.add_patch(Circle((mx,my), 170, color=RED, zorder=7))

# --- zoom to the street network (so distant rivers don't blow out the view) ---
minx,miny,maxx,maxy = edges.total_bounds
cx,cy=(minx+maxx)/2,(miny+maxy)/2
half=max(maxx-minx, maxy-miny)/2*1.03
ax.set_xlim(cx-half*16/9, cx+half*16/9)
ax.set_ylim(cy-half, cy+half)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, facecolor=BG, dpi=100)
print("wrote", os.path.abspath(OUT))
