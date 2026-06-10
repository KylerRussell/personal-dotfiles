#!/usr/bin/env python3
"""Anduril-style orthographic globe wallpaper (text-free, 1920x1080).

Uses the bundled Natural Earth 110m shapefile in ./data, so it needs no
network and only pyshp + matplotlib + numpy.

    pip install pyshp matplotlib numpy
    python3 gen_globe.py
"""
import os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import shapefile  # pyshp

HERE = os.path.dirname(os.path.abspath(__file__))
SHP  = os.path.join(HERE, "data", "naturalearth_lowres.shp")
OUT  = os.path.join(HERE, "..", "dotfiles", "hypr", "wallpapers", "globe.png")

BG="#e9e7e2"; OCEAN="#e4e1da"; LAND="#d8d5cc"; COAST="#9a958a"
GRID="#cfcbc1"; RING="#d0ccc2"; RED="#d9512f"
LAT0, LON0 = 42.0, -98.0          # globe centre (North America)
KC = (-94.5786, 39.0997)          # Kansas City (lon, lat)
ARC_END = (12.0, 58.0)            # trajectory destination (N. Europe)

def ortho(lon, lat):
    lon=np.radians(lon); lat=np.radians(lat)
    l0=np.radians(LON0); p0=np.radians(LAT0)
    cosc=np.sin(p0)*np.sin(lat)+np.cos(p0)*np.cos(lat)*np.cos(lon-l0)
    x=np.cos(lat)*np.sin(lon-l0)
    y=np.cos(p0)*np.sin(lat)-np.sin(p0)*np.cos(lat)*np.cos(lon-l0)
    return x, y, cosc >= -0.02

fig=plt.figure(figsize=(12.8,10.8),dpi=100); fig.patch.set_facecolor(BG)
ax=fig.add_axes([0,0,1,1]); ax.set_facecolor(BG)
ax.set_xlim(-1.304,1.304); ax.set_ylim(-1.1,1.1); ax.set_aspect("equal"); ax.axis("off")
ax.add_patch(Circle((0,0),1.0,facecolor=OCEAN,edgecolor=RING,lw=1.6,zorder=1))
clip=Circle((0,0),1.0,transform=ax.transData)

for lon in range(-180,181,20):
    lat=np.linspace(-90,90,200); x,y,v=ortho(np.full_like(lat,lon),lat)
    ax.plot(np.where(v,x,np.nan),np.where(v,y,np.nan),color=GRID,lw=0.6,zorder=2)
for lat in range(-80,81,20):
    lon=np.linspace(-180,180,360); x,y,v=ortho(lon,np.full_like(lon,lat))
    ax.plot(np.where(v,x,np.nan),np.where(v,y,np.nan),color=GRID,lw=0.6,zorder=2)

for shp in shapefile.Reader(SHP).shapes():
    pts=np.array(shp.points); parts=list(shp.parts)+[len(pts)]
    for i in range(len(parts)-1):
        ring=pts[parts[i]:parts[i+1]]
        if len(ring)<3: continue
        x,y,v=ortho(ring[:,0],ring[:,1])
        if v.sum()<3: continue
        if v.all():
            p=ax.fill(x,y,facecolor=LAND,edgecolor="none",zorder=3)[0]; p.set_clip_path(clip)
        ln,=ax.plot(np.where(v,x,np.nan),np.where(v,y,np.nan),color=COAST,lw=0.7,zorder=4)
        ln.set_clip_path(clip)

kx,ky,_=ortho(np.array([KC[0]]),np.array([KC[1]])); kx,ky=kx[0],ky[0]
ax.add_patch(Circle((kx,ky),0.085,fill=False,edgecolor=RED,lw=1.4,alpha=0.9,zorder=6))
for r,a in [(0.05,0.10),(0.035,0.16),(0.022,0.30)]:
    ax.add_patch(Circle((kx,ky),r,color=RED,alpha=a,zorder=6))
ax.add_patch(Circle((kx,ky),0.012,color=RED,zorder=7))

def xyz(lon,lat):
    lon,lat=np.radians(lon),np.radians(lat)
    return np.array([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])
a=xyz(*KC); b=xyz(*ARC_END); om=np.arccos(np.clip(a@b,-1,1)); t=np.linspace(0,1,240)
arc=(np.sin((1-t)*om)[:,None]*a+np.sin(t*om)[:,None]*b)/np.sin(om)
alat=np.degrees(np.arcsin(arc[:,2])); alon=np.degrees(np.arctan2(arc[:,1],arc[:,0]))
x,y,v=ortho(alon,alat)
al,=ax.plot(np.where(v,x,np.nan),np.where(v,y,np.nan),color=RED,lw=1.3,alpha=0.85,zorder=6)
al.set_clip_path(clip)
ex,ey,ev=ortho(np.array([ARC_END[0]]),np.array([ARC_END[1]]))
if ev[0]:
    ax.add_patch(Circle((ex[0],ey[0]),0.014,fill=False,edgecolor=RED,lw=1.2,zorder=6))
    ax.add_patch(Circle((ex[0],ey[0]),0.005,color=RED,zorder=6))

os.makedirs(os.path.dirname(OUT),exist_ok=True)
fig.savefig(OUT,facecolor=BG,dpi=100)
print("wrote",os.path.abspath(OUT))

# Composite the map into the right two-thirds of a 1920x1080 canvas;
# the left third stays background colour (room for telemetry/clock text).
from PIL import Image as _PILImage
_BG_RGB=(233,231,226)
_m=_PILImage.open(OUT).convert("RGB")
_canvas=_PILImage.new("RGB",(1920,1080),_BG_RGB)
_canvas.paste(_m,(1920-_m.width,0))
_canvas.save(OUT)
