"""Shared figure helpers: true-north local grids, aerial resampling, map furniture."""
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from pyproj import Transformer  # noqa: E402
from scipy import ndimage  # noqa: E402

from common import ASSETS, DATA, FIG, FT2M, M2FT, load, local_lonlat, local_xy  # noqa: E402

TR = Transformer.from_crs(4326, 26914, always_xy=True)

PAL = {"teal": "#0f766e", "navy": "#1e3a8a", "amber": "#f59e0b", "coral": "#ef4444",
       "green": "#16a34a", "purple": "#7c3aed", "sky": "#0ea5e9", "slate": "#334155",
       "lake": "#2563eb", "gold": "#facc15", "pink": "#db2777"}
LOTNAME = {"bayview": "11 Bayview Cir", "arrowhead": "5001 Arrowhead Pt"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 8,
                     "axes.labelsize": 7, "xtick.labelsize": 6, "ytick.labelsize": 6,
                     "savefig.dpi": 300, "figure.dpi": 100})
HALO = [pe.withStroke(linewidth=2.2, foreground="white")]
HALO_D = [pe.withStroke(linewidth=2.2, foreground="black")]


def centre(key):
    T = load("terrain.json")
    return T[key]["centroid_lonlat"]


def dem_local(key, half_ft, step_ft, src="2022", smooth=0.0):
    """DEM resampled to a true-north grid (x east, y north, feet from the lot centroid)."""
    d = np.load(f"{DATA}/dem_{key}_{src}.npz") if src != "ctx" else np.load(f"{DATA}/dem_{key}_ctx.npz")
    z, x0, y0, res = d["z_ft"].astype("float64"), float(d["x0"]), float(d["y0"]), float(d["res"])
    if smooth:
        z = ndimage.gaussian_filter(z, smooth)
    lon0, lat0 = centre(key)
    xs = np.arange(-half_ft, half_ft + 0.01, step_ft)
    ys = np.arange(-half_ft, half_ft + 0.01, step_ft)
    XX, YY = np.meshgrid(xs, ys)
    lon, lat = local_lonlat(XX, YY, lon0, lat0)
    ux, uy = TR.transform(lon, lat)
    r = (y0 - uy) / res
    c = (ux - x0) / res
    Z = ndimage.map_coordinates(z, [r, c], order=1, mode="nearest")
    return xs, ys, Z


def aerial_local(key, zoom, half_ft, step_ft):
    """Aerial mosaic resampled to the same true-north local grid (RGB float 0-1)."""
    meta = json.load(open(os.path.join(ASSETS, f"aerial_{key}_z{zoom}.json")))
    im = np.asarray(Image.open(os.path.join(ASSETS, meta["file"])).convert("RGB")).astype("float32") / 255.0
    H, W = im.shape[:2]
    lon0, lat0 = centre(key)
    xs = np.arange(-half_ft, half_ft + 0.01, step_ft)
    ys = np.arange(-half_ft, half_ft + 0.01, step_ft)
    XX, YY = np.meshgrid(xs, ys)
    lon, lat = local_lonlat(XX, YY, lon0, lat0)

    def merc(la):
        return np.log(np.tan(np.pi / 4 + np.radians(la) / 2))
    px = (lon - meta["west"]) / (meta["east"] - meta["west"]) * W
    py = (merc(meta["north"]) - merc(lat)) / (merc(meta["north"]) - merc(meta["south"])) * H
    out = np.zeros(XX.shape + (3,), "float32")
    for k in range(3):
        out[..., k] = ndimage.map_coordinates(im[..., k], [py, px], order=1, mode="nearest")
    return xs, ys, np.clip(out, 0, 1)


def grids_rot(key, ulim, vlim, step_ft, theta, zoom=19, smooth=1.0):
    """Aerial RGB and DEM on a grid in a rotated frame (u, v) = R(theta) * (x east, y north).

    theta is the counter-clockwise rotation (radians) applied to map coordinates.
    Returns us, vs, rgb, Z (Z in feet, lightly smoothed).
    """
    lon0, lat0 = centre(key)
    us = np.arange(ulim[0], ulim[1] + 0.01, step_ft)
    vs = np.arange(vlim[0], vlim[1] + 0.01, step_ft)
    UU, VV = np.meshgrid(us, vs)
    c, s = math.cos(theta), math.sin(theta)
    XX = c * UU + s * VV            # inverse rotation
    YY = -s * UU + c * VV
    lon, lat = local_lonlat(XX, YY, lon0, lat0)
    # DEM
    d = np.load(f"{DATA}/dem_{key}_2022.npz")
    z, x0, y0, res = d["z_ft"].astype("float64"), float(d["x0"]), float(d["y0"]), float(d["res"])
    if smooth:
        z = ndimage.gaussian_filter(z, smooth)
    ux, uy = TR.transform(lon, lat)
    Z = ndimage.map_coordinates(z, [(y0 - uy) / res, (ux - x0) / res], order=1, mode="nearest")
    # aerial
    meta = json.load(open(os.path.join(ASSETS, f"aerial_{key}_z{zoom}.json")))
    im = np.asarray(Image.open(os.path.join(ASSETS, meta["file"])).convert("RGB")).astype("float32") / 255.0
    H, W = im.shape[:2]

    def merc(la):
        return np.log(np.tan(np.pi / 4 + np.radians(la) / 2))
    px = (lon - meta["west"]) / (meta["east"] - meta["west"]) * W
    py = (merc(meta["north"]) - merc(lat)) / (merc(meta["north"]) - merc(meta["south"])) * H
    rgb = np.zeros(UU.shape + (3,), "float32")
    for k in range(3):
        rgb[..., k] = ndimage.map_coordinates(im[..., k], [py, px], order=1, mode="nearest")
    return us, vs, np.clip(rgb, 0, 1), Z


def rot(xy, theta):
    a = np.asarray(xy, dtype="float64")
    c, s = math.cos(theta), math.sin(theta)
    u = c * a[..., 0] - s * a[..., 1]
    v = s * a[..., 0] + c * a[..., 1]
    return np.stack([u, v], axis=-1)


def lonlat_lf(key, lon, lat):
    lon0, lat0 = centre(key)
    return local_xy(lon, lat, lon0, lat0)


def north_arrow(ax, x, y, size, color="black", label="N (true)"):
    ax.annotate("", xy=(x, y + size), xytext=(x, y),
                arrowprops=dict(arrowstyle="-|>,head_width=0.45,head_length=0.9", lw=1.6, color=color))
    ax.text(x, y + size * 1.12, "N", ha="center", va="bottom", fontsize=8, fontweight="bold", color=color,
            path_effects=HALO if color == "black" else HALO_D)


def scale_bar(ax, x, y, length_ft, color="black", height=None, label=None):
    h = height or length_ft * 0.06
    for i in range(4):
        ax.add_patch(plt.Rectangle((x + i * length_ft / 4, y), length_ft / 4, h,
                                   facecolor=color if i % 2 == 0 else "white", edgecolor=color, lw=0.6, zorder=20))
    halo = HALO_D if color == "white" else HALO
    ax.text(x, y + h * 1.4, "0", ha="center", va="bottom", fontsize=5.5, color=color, path_effects=halo, zorder=21)
    ax.text(x + length_ft, y + h * 1.4, label or f"{int(length_ft)} ft", ha="center", va="bottom", fontsize=5.5,
            color=color, path_effects=halo, zorder=21)


def save(fig, name, dpi=300, **kw):
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.02, **kw)
    plt.close(fig)
    return path
