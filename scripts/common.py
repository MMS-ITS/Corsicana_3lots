"""Shared helpers for the Corsicana / Streetman lot due-diligence pipeline.

Network access goes only to public endpoints (TxGIO StratMap parcels, USGS 3DEP,
FEMA NFHL, USDA NRCS Soil Data Access, US Census, Open-Meteo, OSM/OSRM, Esri
World Imagery tiles). Every script caches what it fetched under data/ so the
report can be rebuilt without the network.
"""
import json
import math
import os
import time
import urllib.parse

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "figures")
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "out")
for _d in (DATA, FIG, ASSETS, OUT):
    os.makedirs(_d, exist_ok=True)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/141.0 Safari/537.36")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})
# OSM services (Overpass, Nominatim, OSRM demo) ask for an identifying user agent.
OSM = requests.Session()
OSM.headers.update({"User-Agent": "lot-due-diligence-research/1.0 (python-requests)",
                    "Accept": "application/json"})

M2FT = 3.280839895
FT2M = 0.3048

# The two subject lots. Seeds come from the Esri World Geocoder (PointAddress for
# Arrowhead, interpolated StreetAddress for Bayview) and only aim the parcel search.
LOTS = {
    "bayview": {
        "label": "11 Bayview Cir, Corsicana, TX 75109",
        "short": "11 Bayview Cir",
        "num": "11", "street": "BAYVIEW",
        "seed": (-96.217414, 32.001878),
        "city": "Corsicana",
    },
    "arrowhead": {
        "label": "5001 Arrowhead Point, Streetman, TX 75859",
        "short": "5001 Arrowhead Pt",
        "num": "5001", "street": "ARROWHEAD",
        "seed": (-96.273153, 31.951865),
        "city": "Streetman",
    },
}


def get(url, params=None, timeout=90, retries=4, as_json=True, **kw):
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=timeout, **kw)
            r.raise_for_status()
            return r.json() if as_json else r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET failed {url[:120]}: {last}")


def post(url, data, timeout=180, retries=4, as_json=True):
    last = None
    for i in range(retries):
        try:
            r = SESSION.post(url, data=data, timeout=timeout)
            r.raise_for_status()
            return r.json() if as_json else r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2.0 * (i + 1))
    raise RuntimeError(f"POST failed {url[:120]}: {last}")


def save(name, obj):
    p = os.path.join(DATA, name)
    with open(p, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    return p


def load(name, default=None):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


# ------------------------------------------------------------------ geometry
def local_xy(lon, lat, lon0, lat0):
    """Equirectangular projection to feet about (lon0, lat0). Good to <0.1% over a lot."""
    x = (lon - lon0) * 111320.0 * math.cos(math.radians(lat0)) * M2FT
    y = (lat - lat0) * 110574.0 * M2FT
    return x, y


def local_lonlat(x, y, lon0, lat0):
    lon = lon0 + x / (111320.0 * math.cos(math.radians(lat0)) * M2FT)
    lat = lat0 + y / (110574.0 * M2FT)
    return lon, lat


def ring_area_sqft(ring_xy):
    s = 0.0
    n = len(ring_xy)
    for i in range(n):
        x1, y1 = ring_xy[i]
        x2, y2 = ring_xy[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def haversine_ft(a, b):
    R = 20902231.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp = p2 - p1
    dl = math.radians(b[0] - a[0])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def haversine_mi(a, b):
    return haversine_ft(a, b) / 5280.0


def esri_query(base, layer, geometry, gtype, fields="*", dist_ft=None, want_geom=True,
               extra=None, timeout=180):
    p = {"f": "json", "geometry": json.dumps(geometry), "geometryType": gtype,
         "inSR": "4326", "outSR": "4326", "spatialRel": "esriSpatialRelIntersects",
         "outFields": fields, "returnGeometry": "true" if want_geom else "false"}
    if dist_ft:
        p["distance"] = str(dist_ft)
        p["units"] = "esriSRUnit_Foot"
    if extra:
        p.update(extra)
    d = post(f"{base}/{layer}/query", data=p, timeout=timeout)
    if "error" in d:
        raise RuntimeError(str(d["error"])[:240])
    return d.get("features", [])


def qs(d):
    return urllib.parse.urlencode(d)
