"""Parcel geometry for both lots and their neighbours.

Source: TxGIO StratMap statewide land parcels (Navarro CAD 2026 roll), via the
MapServer `identify` operation. The target parcels were matched by legal
description and confirmed against the Navarro CAD property records:

  bayview   -> W0305 WHITE ROCK SUB LOT 11 .65 ACRES       (Parcel ID 63254)
  arrowhead -> R1550.02 RUSTLING OAKS ESTATES PHASE II BLK 1 LOT 33 .5 ACRES
               (Parcel ID 56587; 5001 Arrowhead Pt is the Esri PointAddress
               inside this polygon, next to the same owners' 5003 / Lot 32)
"""
import json
import math

from shapely.geometry import Point, Polygon, mapping
from shapely.ops import unary_union

from common import LOTS, get, local_xy, save

SVC = ("https://feature.geographic.texas.gov/arcgis/rest/services/Parcels/"
       "stratmap_land_parcels_48_most_recent/MapServer/identify")
TARGET_GEO = {k: v["geo"] for k, v in LOTS.items()}
HALF = 0.0075  # degrees half-window for neighbour harvest (~800 m)


def identify(lon, lat, d):
    p = {"f": "json",
         "geometry": json.dumps({"xmin": lon - d, "ymin": lat - d, "xmax": lon + d,
                                 "ymax": lat + d, "spatialReference": {"wkid": 4326}}),
         "geometryType": "esriGeometryEnvelope", "sr": "4326", "tolerance": "1",
         "mapExtent": f"{lon-d},{lat-d},{lon+d},{lat+d}", "imageDisplay": "1600,1600,96",
         "layers": "all", "returnGeometry": "true", "maxAllowableOffset": "0.000001"}
    return get(SVC, params=p, timeout=180).get("results", [])


def ring_of(res):
    rings = (res.get("geometry") or {}).get("rings") or []
    if not rings:
        return None
    return max(rings, key=len)


def main():
    out = {}
    for key, lot in LOTS.items():
        lon, lat = lot["seed"]
        res = identify(lon, lat, HALF)
        parcels = []
        for r in res:
            ring = ring_of(r)
            if not ring:
                continue
            a = r["attributes"]
            parcels.append({"geo_id": str(a.get("GEO_ID")), "situs": a.get("SITUS_ADDR"),
                            "legal": a.get("LEGAL_DESC"), "owner": a.get("OWNER_NAME"),
                            "land_value": a.get("LAND_VALUE"), "imp_value": a.get("IMP_VALUE"),
                            "legal_area": a.get("LEGAL_AREA"), "ring": ring})
        tgt = [p for p in parcels if p["geo_id"] == TARGET_GEO[key]]
        assert tgt, f"target parcel not found for {key}"
        t = tgt[0]
        ring = t["ring"]
        poly = Polygon(ring)
        cen = poly.centroid
        lon0, lat0 = cen.x, cen.y
        xy = [local_xy(x, y, lon0, lat0) for x, y in ring]
        pxy = Polygon(xy)
        # corners: simplify the ring to its significant vertices
        simp = pxy.simplify(1.0)
        corners_xy = list(simp.exterior.coords)[:-1]
        corners = []
        for (x, y) in corners_xy:
            # nearest original vertex -> lon/lat
            j = min(range(len(xy)), key=lambda k: (xy[k][0] - x) ** 2 + (xy[k][1] - y) ** 2)
            corners.append({"x_ft": round(x, 1), "y_ft": round(y, 1),
                            "lon": round(ring[j][0], 7), "lat": round(ring[j][1], 7)})
        edges = []
        for i in range(len(corners_xy)):
            x1, y1 = corners_xy[i]
            x2, y2 = corners_xy[(i + 1) % len(corners_xy)]
            L = math.hypot(x2 - x1, y2 - y1)
            brg = (math.degrees(math.atan2(x2 - x1, y2 - y1)) + 360) % 360
            edges.append({"from": i, "to": (i + 1) % len(corners_xy), "length_ft": round(L, 1),
                          "bearing_deg": round(brg, 1)})
        # neighbours touching the target (within 3 ft)
        nb = []
        for p in parcels:
            if p["geo_id"] == t["geo_id"]:
                continue
            q = Polygon(p["ring"])
            if q.distance(poly) * 364000 < 3.0:   # deg->ft approx
                nb.append({k: p[k] for k in ("geo_id", "situs", "legal", "owner",
                                             "land_value", "imp_value")})
        rec = {
            "target": {k: t[k] for k in ("geo_id", "situs", "legal", "owner", "land_value",
                                         "imp_value", "legal_area")},
            "ring": ring,
            "centroid": {"lon": round(lon0, 7), "lat": round(lat0, 7)},
            "area_sqft": round(pxy.area, 0),
            "area_acres": round(pxy.area / 43560.0, 4),
            "perimeter_ft": round(pxy.length, 1),
            "corners": corners,
            "edges": edges,
            "neighbours": nb,
            "all_parcels": [{k: p[k] for k in ("geo_id", "situs", "legal", "owner", "ring",
                                               "land_value", "imp_value")} for p in parcels],
        }
        out[key] = rec
        print(f"== {key}: {t['legal']}  GIS area {rec['area_sqft']:.0f} sf = "
              f"{rec['area_acres']:.3f} ac, perimeter {rec['perimeter_ft']:.0f} ft, "
              f"{len(corners)} corners, {len(nb)} neighbours, {len(parcels)} parcels harvested")
        for e in edges:
            print(f"     edge {e['from']}->{e['to']}: {e['length_ft']:.1f} ft @ {e['bearing_deg']:.0f} deg")
        for n in nb:
            print("     nb:", n["situs"], "|", n["legal"], "|", n["owner"])
    save("parcels.json", out)


if __name__ == "__main__":
    main()
