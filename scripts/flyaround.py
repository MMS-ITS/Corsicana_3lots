"""Fly-around style oblique views: a small height-field ("voxel space") renderer.

The terrain is the USGS 3DEP lidar DEM (1 m near the lot, 3 m beyond) draped
with Esri World Imagery (0.5 m near, 2 m beyond).  Rendering is front-to-back
along depth slices with a per-column y-buffer, vectorised with numpy.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pyproj import Transformer
from scipy import ndimage

from common import ASSETS, DATA, FIG, M2FT, FT2M, load, local_lonlat, local_xy

TR = Transformer.from_crs(4326, 26914, always_xy=True)
import matplotlib as _mpl

FONT = os.path.join(os.path.dirname(_mpl.__file__), "mpl-data", "fonts", "ttf", "DejaVuSans-Bold.ttf")


class Sampler:
    """Height (m) and colour samplers in a true-north local frame (metres from the lot centroid)."""

    def __init__(self, key):
        T = load("terrain.json")
        self.lon0, self.lat0 = T[key]["centroid_lonlat"]
        self.dems = []
        for name in ("2022", "ctx"):
            d = np.load(f"{DATA}/dem_{key}_{name}.npz")
            z = d["z_ft"].astype("float32") * FT2M
            if name == "ctx":
                z = ndimage.gaussian_filter(z, 0.6)
            self.dems.append((z, float(d["x0"]), float(d["y0"]), float(d["res"])))
        self.imgs = []
        for zoom in (18, 16):
            m = json.load(open(os.path.join(ASSETS, f"aerial_{key}_z{zoom}.json")))
            a = np.asarray(Image.open(os.path.join(ASSETS, m["file"])).convert("RGB")).astype("float32")
            self.imgs.append((a, m))

    def _ll(self, x, y):
        return local_lonlat(x * M2FT, y * M2FT, self.lon0, self.lat0)

    def height(self, x, y):
        lon, lat = self._ll(x, y)
        ux, uy = TR.transform(lon, lat)
        out = np.full(np.shape(x), np.nan, "float32")
        for z, x0, y0, res in self.dems:
            r = (y0 - uy) / res
            c = (ux - x0) / res
            ok = np.isnan(out) & (r >= 0) & (c >= 0) & (r <= z.shape[0] - 1) & (c <= z.shape[1] - 1)
            if ok.any():
                out[ok] = ndimage.map_coordinates(z, [r[ok], c[ok]], order=1, mode="nearest")
        out[np.isnan(out)] = 95.0
        return out

    def colour(self, x, y):
        lon, lat = self._ll(x, y)
        out = np.full(np.shape(x) + (3,), np.nan, "float32")

        def merc(la):
            return np.log(np.tan(np.pi / 4 + np.radians(la) / 2))
        for a, m in self.imgs:
            H, W = a.shape[:2]
            px = (lon - m["west"]) / (m["east"] - m["west"]) * W
            py = (merc(m["north"]) - merc(lat)) / (merc(m["north"]) - merc(m["south"])) * H
            ok = np.isnan(out[..., 0]) & (px >= 0) & (py >= 0) & (px <= W - 1) & (py <= H - 1)
            if ok.any():
                for k in range(3):
                    out[..., k][ok] = ndimage.map_coordinates(a[..., k], [py[ok], px[ok]], order=1)
        out[np.isnan(out)] = 120.0
        return out


def render(s, cam_xy, cam_h, target_xy, W=1800, Hh=1100, fov=58, far=1500.0, ve=1.0, horizon_frac=0.18,
           overlays=(), labels=()):
    """Render an oblique view looking from cam_xy (m) toward target_xy.

    overlays: list of (polyline_xy_m, rgba, width)   labels: list of (xy_m, text, rgba)
    """
    cx, cy = cam_xy
    dx, dy = target_xy[0] - cx, target_xy[1] - cy
    head = math.atan2(dx, dy)
    dirv = np.array([math.sin(head), math.cos(head)])
    perp = np.array([math.cos(head), -math.sin(head)])
    tanf = math.tan(math.radians(fov / 2))
    focal = (W / 2) / tanf
    dist_t = math.hypot(dx, dy)
    zt = float(s.height(np.array([target_xy[0]]), np.array([target_xy[1]]))[0])
    base = float(np.nanmin(s.height(np.array([cx]), np.array([cy]))))
    # choose the horizon so the target sits at ~58% of the image height
    horizon = 0.58 * Hh - (cam_h - zt * ve) / dist_t * focal
    img = np.zeros((Hh, W, 3), "float32")
    sky = np.linspace(0, 1, Hh)[:, None]
    img[:] = (np.array([0.62, 0.78, 0.95]) * (1 - sky) + np.array([0.86, 0.91, 0.97]) * sky)[:, None, :][:, :, 0, :] \
        if False else 0
    top = np.array([0.55, 0.72, 0.93]); bot = np.array([0.88, 0.92, 0.97])
    for r in range(Hh):
        t = min(1.0, max(0.0, (r - 0) / max(horizon + 40, 1)))
        img[r, :, :] = top * (1 - t) + bot * t
    ybuf = np.full(W, Hh, "int32")
    cols = np.arange(W)
    lat_off = (cols - W / 2 + 0.5) / focal                    # tan of horizontal angle per column
    z = 3.0
    while z < far:
        px = cx + dirv[0] * z + perp[0] * lat_off * z
        py = cy + dirv[1] * z + perp[1] * lat_off * z
        hgt = s.height(px, py) * ve
        col = s.colour(px, py) / 255.0
        # water: flatten lake to its surface and tint a little
        haze = min(0.55, (z / far) ** 1.4 * 0.55)
        col = col * (1 - haze) + np.array([0.80, 0.86, 0.93]) * haze
        ys = (horizon + (cam_h - hgt) / z * focal).astype("int32")
        ys = np.clip(ys, 0, Hh)
        draw = ys < ybuf
        if draw.any():
            for c in cols[draw]:
                img[ys[c]:ybuf[c], c, :] = col[c]
            ybuf = np.minimum(ybuf, ys)
        z += 0.25 + z * 0.0035
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8"))
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    d = ImageDraw.Draw(im, "RGBA")

    def proj(x, y):
        rx, ry = x - cx, y - cy
        zz = rx * dirv[0] + ry * dirv[1]
        ll = rx * perp[0] + ry * perp[1]
        if zz <= 1:
            return None
        h = float(s.height(np.array([x]), np.array([y]))[0]) * ve
        return (W / 2 + ll / zz * focal, horizon + (cam_h - h) / zz * focal)
    for line, rgba, wid in overlays:
        pts = [proj(x, y) for x, y in line]
        pts = [p for p in pts if p is not None]
        if len(pts) > 1:
            d.line(pts, fill=(255, 255, 255, 200), width=wid + 4, joint="curve")
            d.line(pts, fill=rgba, width=wid, joint="curve")
    f = ImageFont.truetype(FONT, int(Hh * 0.032))
    for (x, y), text, rgba in labels:
        p = proj(x, y)
        if p is None:
            continue
        tw = d.textlength(text, font=f)
        d.rounded_rectangle([p[0] - tw / 2 - 10, p[1] - 58, p[0] + tw / 2 + 10, p[1] - 14], radius=10,
                            fill=rgba)
        d.polygon([(p[0] - 8, p[1] - 15), (p[0] + 8, p[1] - 15), (p[0], p[1] - 2)], fill=rgba)
        d.text((p[0] - tw / 2, p[1] - 54), text, font=f, fill=(255, 255, 255, 255))
    return im, head
