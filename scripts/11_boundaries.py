"""Boundaries for the locator maps: Texas outline and nearby counties (US Census
TIGERweb, generalised), the Richland-Chambers 315-ft shoreline (TWDB 2018,
simplified), and regional highways (OSM via Overpass, motorway/trunk/primary).
Output: data/boundaries.json
"""
import json
import os
import time

import shapefile
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, mapping, shape
from shapely.ops import transform as stransform

from common import OSM, get, save

TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer"
TWDB_DIR = os.environ.get("TWDB_DIR", "/projects/sandbox/scratch/twdb")


def tiger(layer, where, offset):
    d = get(f"{TIGER}/{layer}/query", params={"where": where, "outFields": "NAME,GEOID", "f": "geojson",
                                              "outSR": 4326, "maxAllowableOffset": offset,
                                              "returnGeometry": "true"}, timeout=180)
    return d["features"]


def main():
    out = {}
    st = tiger(0, "STATE='48'", 0.01)
    out["texas"] = st[0]["geometry"]
    out["us_states"] = [f["geometry"] for f in tiger(0, "STATE IN ('35','40','05','22')", 0.03)]
    cos = tiger(1, "STATE='48' AND COUNTY IN ('349','161','139','213','001','293','145','217','257')", 0.002)
    out["counties"] = [{"name": f["properties"]["NAME"], "geom": f["geometry"]} for f in cos]
    # Richland-Chambers shoreline at 315 ft (TWDB), simplified ~25 m
    sp = Transformer.from_crs(2276, 4326, always_xy=True)
    r = shapefile.Reader(os.path.join(TWDB_DIR, "RC18_Lake"))
    g = shape(r.shape(0).__geo_interface__)
    g = g.simplify(80.0)                                   # feet
    g = stransform(lambda x, y, z=None: sp.transform(x, y), g)
    out["rc_lake"] = mapping(g)
    # regional highways
    q = ('[out:json][timeout:120];(way["highway"~"^(motorway|trunk|primary)$"](31.55,-96.95,32.35,-95.85););'
         'out geom;')
    els = []
    for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter"):
        try:
            rr = OSM.post(ep, data={"data": q}, timeout=200)
            rr.raise_for_status()
            els = rr.json()["elements"]
            break
        except Exception as e:  # noqa: BLE001
            print("overpass", ep, e)
            time.sleep(5)
    roads = []
    for e in els:
        if e.get("geometry"):
            t = e.get("tags", {})
            ls = LineString([(p["lon"], p["lat"]) for p in e["geometry"]]).simplify(0.0004)
            roads.append({"ref": t.get("ref"), "name": t.get("name"), "hw": t.get("highway"),
                          "xy": [list(c) for c in ls.coords]})
    out["highways"] = roads
    print("texas parts:", len(out["texas"]["coordinates"]), "counties:", [c["name"] for c in out["counties"]],
          "highways:", len(roads))
    save("boundaries.json", out)


if __name__ == "__main__":
    main()
