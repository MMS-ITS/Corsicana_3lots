"""Lake-bottom contours and survey depths near each lot from the TWDB December 2018
volumetric survey of Richland-Chambers Reservoir (1-ft contour shapefile and
sounding points; NAD83 Texas North Central, US feet).

The 850 MB TWDB shapefile archive is not committed; set TWDB_DIR to the unzipped
folder to rebuild. Output (committed): data/bathymetry.json
"""
import math
import os

import numpy as np
import shapefile
from pyproj import Transformer

from common import load, local_xy, save

TWDB_DIR = os.environ.get("TWDB_DIR", "/projects/sandbox/scratch/twdb")
SP = Transformer.from_crs(4326, 2276, always_xy=True)       # lon/lat -> TX N Central ftUS
SPI = Transformer.from_crs(2276, 4326, always_xy=True)
HALF_FT = 2300.0
POOL = 315.0


def main():
    P = load("parcels.json")
    T = load("terrain.json")
    out = {}
    cont = shapefile.Reader(os.path.join(TWDB_DIR, "rc18_1ftcont"))
    pts = shapefile.Reader(os.path.join(TWDB_DIR, "RC18_surveypts"))
    pfields = [f[0] for f in pts.fields[1:]]
    zi = pfields.index("corr_curre") if "corr_curre" in pfields else None   # corrected bottom elevation, ft
    # whole-lake extremes from the survey soundings
    lake_min = None
    for key, rec in P.items():
        lon0, lat0 = T[key]["centroid_lonlat"]
        ex, ey = SP.transform(lon0, lat0)
        bb = [ex - HALF_FT, ey - HALF_FT, ex + HALF_FT, ey + HALF_FT]
        lines = []
        for i, shp in enumerate(cont.iterShapes(bbox=bb)):
            pass
        # iterShapes(bbox) yields shapes only; read records alongside via shapeRecords
        lines = []
        for sr in cont.iterShapeRecords(bbox=bb):
            elev = float(sr.record["CONTOUR"])
            if elev % 5 != 0 and elev > 300:
                keep = elev % 1 == 0
            for pi, start in enumerate(sr.shape.parts):
                end = sr.shape.parts[pi + 1] if pi + 1 < len(sr.shape.parts) else len(sr.shape.points)
                seg = sr.shape.points[start:end]
                ll = [SPI.transform(x, y) for x, y in seg[::2]]
                xy = [local_xy(lo, la, lon0, lat0) for lo, la in ll]
                xy = [(round(x, 1), round(y, 1)) for x, y in xy if abs(x) < HALF_FT * 1.2 and abs(y) < HALF_FT * 1.2]
                if len(xy) > 1:
                    lines.append({"z": elev, "xy": xy})
        # soundings within the window
        sound = []
        for sr in pts.iterShapeRecords(bbox=bb):
            x, y = sr.shape.points[0]
            zz = float(sr.record[zi]) if zi is not None else float(sr.record["z"])
            lo, la = SPI.transform(x, y)
            lx, ly = local_xy(lo, la, lon0, lat0)
            sound.append((round(lx, 1), round(ly, 1), round(zz, 2)))
        sound = np.array(sound) if sound else np.zeros((0, 3))
        # depth off the lake frontage: soundings within 60-300 ft of the frontage midpoint
        sec = T[key]["section_lf"]
        lake_mid = np.array(sec[1])
        d = np.hypot(sound[:, 0] - lake_mid[0], sound[:, 1] - lake_mid[1]) if len(sound) else np.array([])
        near = sound[(d < 300)] if len(sound) else sound
        near150 = sound[(d < 150)] if len(sound) else sound
        def stats(a):
            if len(a) == 0:
                return None
            depth = POOL - a[:, 2]
            return {"n": int(len(a)), "mean_depth_ft": round(float(depth.mean()), 1),
                    "max_depth_ft": round(float(depth.max()), 1), "min_bottom_ft": round(float(a[:, 2].min()), 1)}
        out[key] = {"lines": lines, "n_soundings": int(len(sound)),
                    "within_150ft": stats(near150), "within_300ft": stats(near),
                    "window_ft": HALF_FT,
                    "soundings_sample": sound[:: max(1, len(sound) // 4000)].tolist()}
        print(key, "contour lines", len(lines), "soundings", len(sound), "near150", out[key]["within_150ft"],
              "near300", out[key]["within_300ft"])
    # lake-wide minimum bottom (scan the sounding file once, z only)
    zmin = 1e9
    for rec in pts.iterRecords(fields=["corr_curre"]):
        v = rec[0]
        if v is not None and v < zmin:
            zmin = v
    out["lake"] = {"min_bottom_ft": round(float(zmin), 1), "max_depth_ft": round(POOL - float(zmin), 1),
                   "area_acres_315": 43874, "volume_acft_315": 1125199,
                   "mean_depth_ft": round(1125199 / 43874, 1), "survey": "TWDB volumetric survey, Dec 2018"}
    print(out["lake"])
    save("bathymetry.json", out)


if __name__ == "__main__":
    main()
