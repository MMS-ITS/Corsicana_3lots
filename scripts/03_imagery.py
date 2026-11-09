"""Aerial imagery mosaics for each lot (Esri World Imagery, Web-Mercator tiles).

Writes assets/aerial_<lot>_z<zoom>.jpg plus a JSON sidecar with the exact
geographic bounds of the mosaic so figures can georeference it, and records the
imagery citation (source, resolution, capture date) from Esri's metadata layer.
"""
import io
import json
import math
import os

from PIL import Image

from common import ASSETS, DATA, SESSION, get, load, save

TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
META = "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/identify"


def deg2num(lon, lat, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def num2deg(x, y, z):
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def mosaic(lon0, lat0, half_m, z, name):
    # half-width in degrees
    dlat = half_m / 110574.0
    dlon = half_m / (111320.0 * math.cos(math.radians(lat0)))
    x0f, y0f = deg2num(lon0 - dlon, lat0 + dlat, z)
    x1f, y1f = deg2num(lon0 + dlon, lat0 - dlat, z)
    tx0, ty0, tx1, ty1 = int(x0f), int(y0f), int(x1f), int(y1f)
    W = (tx1 - tx0 + 1) * 256
    H = (ty1 - ty0 + 1) * 256
    im = Image.new("RGB", (W, H))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            r = SESSION.get(TILE.format(z=z, x=tx, y=ty), timeout=60)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                t = Image.open(io.BytesIO(r.content)).convert("RGB")
                im.paste(t, ((tx - tx0) * 256, (ty - ty0) * 256))
    # crop to the requested window
    cx0 = int((x0f - tx0) * 256)
    cy0 = int((y0f - ty0) * 256)
    cx1 = int((x1f - tx0) * 256)
    cy1 = int((y1f - ty0) * 256)
    im = im.crop((cx0, cy0, cx1, cy1))
    west, north = num2deg(tx0 + cx0 / 256.0, ty0 + cy0 / 256.0, z)
    east, south = num2deg(tx0 + cx1 / 256.0, ty0 + cy1 / 256.0, z)
    path = os.path.join(ASSETS, f"{name}.jpg")
    im.save(path, quality=92)
    meta = {"file": os.path.basename(path), "zoom": z, "size": im.size,
            "west": west, "east": east, "north": north, "south": south,
            "m_per_px": 156543.03392 * math.cos(math.radians(lat0)) / 2 ** z}
    with open(os.path.join(ASSETS, f"{name}.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(name, im.size, f"{meta['m_per_px']:.3f} m/px")
    return meta


def citation(lon, lat):
    p = {"geometry": json.dumps({"x": lon, "y": lat}), "geometryType": "esriGeometryPoint",
         "sr": 4326, "layers": "all", "tolerance": 2, "mapExtent": f"{lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}",
         "imageDisplay": "800,800,96", "returnGeometry": "false", "f": "json"}
    try:
        d = get(META, params=p, timeout=60)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:120]}
    out = []
    for r in d.get("results", []):
        a = r.get("attributes", {})
        out.append({k: a.get(k) for k in ("SRC_DATE", "SRC_DATE2", "SRC_RES", "SRC_ACC", "SRC_DESC",
                                          "NICE_NAME", "NICE_DESC", "MinMapLevel", "MaxMapLevel")
                    if a.get(k) is not None})
    return out


def main():
    P = load("parcels.json")
    cites = {}
    for key, rec in P.items():
        lon, lat = rec["centroid"]["lon"], rec["centroid"]["lat"]
        mosaic(lon, lat, 120, 19, f"aerial_{key}_z19")     # lot close-up
        mosaic(lon, lat, 420, 18, f"aerial_{key}_z18")     # subdivision
        mosaic(lon, lat, 1700, 16, f"aerial_{key}_z16")    # cove / lake context
        cites[key] = citation(lon, lat)
        print(key, cites[key][:3])
    save("imagery_citation.json", cites)


if __name__ == "__main__":
    main()
