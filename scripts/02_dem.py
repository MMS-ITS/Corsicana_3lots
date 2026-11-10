"""Read USGS 3DEP 1 m lidar DEM windows around each lot.

Source tiles (Cloud-Optimised GeoTIFFs on the USGS staged-products bucket):
  TX_2022NorthCentral_ContributedProcessing_D25 (primary, published Apr 2026)
  TX_RedRiver_3Area_B1_2018                     (cross-check)
CRS: NAD83 / UTM 14N (EPSG:26914); vertical: NAVD88 metres (converted to feet).

Writes data/dem_<lot>_<src>.npz with:
  z_ft  : 2-D array, feet NAVD88 (north-up, row 0 = north)
  x0,y0 : UTM easting/northing of the upper-left pixel centre
  res   : metres per pixel
"""
import os

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

from common import DATA, M2FT, load

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")

BASE = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects"


def tile_urls(cx, cy):
    """USGS 1 m tiles are 10 km squares named by the UTM 14N km/10 of their NW corner."""
    tx, ty = int(cx // 10000), int(cy // 10000) + 1
    return {
        "2022": f"{BASE}/TX_2022NorthCentral_ContributedProcessing_D25/TIFF/USGS_1M_14_x{tx}y{ty}_TX_2022NorthCentral_ContributedProcessing_D25.tif",
        "2018": f"{BASE}/TX_RedRiver_3Area_B1_2018/TIFF/USGS_one_meter_x{tx}y{ty}_TX_RedRiver_3Area_B1_2018.tif",
    }
HALF_LOT = 260.0      # m half-width of the detailed window
HALF_CTX = 1400.0     # m half-width of the context window (read at 1 m, stored at 3 m)


def read_window(url, cx, cy, half, step=1):
    with rasterio.open("/vsicurl/" + url) as ds:
        assert ds.crs.to_epsg() == 26914, ds.crs
        win = from_bounds(cx - half, cy - half, cx + half, cy + half, ds.transform)
        a = ds.read(1, window=win, boundless=True, fill_value=np.nan).astype("float32")
        nod = ds.nodata
        if nod is not None:
            a[a == nod] = np.nan
        t = ds.window_transform(win)
        res = t.a
        if step > 1:
            n0 = (a.shape[0] // step) * step
            n1 = (a.shape[1] // step) * step
            a = np.nanmean(a[:n0, :n1].reshape(n0 // step, step, n1 // step, step), axis=(1, 3))
            res = res * step
        x0 = t.c + res / 2.0
        y0 = t.f - res / 2.0
        return a, x0, y0, res, ds.tags()


def main():
    P = load("parcels.json")
    tr = Transformer.from_crs(4326, 26914, always_xy=True)
    for key, rec in P.items():
        cx, cy = tr.transform(rec["centroid"]["lon"], rec["centroid"]["lat"])
        TILES = {key: tile_urls(cx, cy)}
        for src, url in TILES[key].items():
            a, x0, y0, res, tags = read_window(url, cx, cy, HALF_LOT)
            z = a * M2FT
            np.savez_compressed(os.path.join(DATA, f"dem_{key}_{src}.npz"), z_ft=z.astype("float32"),
                                x0=x0, y0=y0, res=res, cx=cx, cy=cy)
            print(f"{key} {src}: {z.shape} res {res} m  min {np.nanmin(z):.2f} ft  max {np.nanmax(z):.2f} ft "
                  f" nan {np.isnan(z).mean()*100:.1f}%")
        a, x0, y0, res, _ = read_window(TILES[key]["2022"], cx, cy, HALF_CTX, step=3)
        z = a * M2FT
        np.savez_compressed(os.path.join(DATA, f"dem_{key}_ctx.npz"), z_ft=z.astype("float32"),
                            x0=x0, y0=y0, res=res, cx=cx, cy=cy)
        print(f"{key} ctx: {z.shape} res {res} m  min {np.nanmin(z):.2f}  max {np.nanmax(z):.2f}")


if __name__ == "__main__":
    main()
