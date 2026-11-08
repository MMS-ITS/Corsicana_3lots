"""FEMA National Flood Hazard Layer lookup and map export for each lot.

Queries the parcel polygon (split-zone detection), the FIRM panel, any BFE
lines within 2,000 ft, and the LOMR/LOMA layers, then exports a flood-zone map
image (NFHL layers over Esri imagery is composed later in 07_figures.py).
"""
import json
import os

from common import ASSETS, LOTS, esri_query, get, load, save, SESSION

BASE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
L_ZONE, L_PANEL, L_BFE, L_LOMR, L_XS = 28, 3, 16, 1, 14


def attrs(feats):
    return [f.get("attributes", {}) for f in feats]


def main():
    P = load("parcels.json")
    out = {}
    for key, rec in P.items():
        poly = {"rings": [rec["ring"]], "spatialReference": {"wkid": 4326}}
        c = rec["centroid"]
        pt = {"x": c["lon"], "y": c["lat"], "spatialReference": {"wkid": 4326}}
        r = {}
        z = esri_query(BASE, L_ZONE, poly, "esriGeometryPolygon",
                       "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE,DEPTH,V_DATUM,DFIRM_ID,FLD_AR_ID,SOURCE_CIT",
                       want_geom=True)
        r["zones_on_parcel"] = attrs(z)
        r["zone_geoms"] = [f.get("geometry") for f in z]
        near = esri_query(BASE, L_ZONE, pt, "esriGeometryPoint",
                          "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE,V_DATUM", dist_ft=1500, want_geom=True)
        r["zones_within_1500ft"] = attrs(near)
        r["zone_geoms_1500"] = [{"a": f.get("attributes"), "g": f.get("geometry")} for f in near]
        r["panel"] = attrs(esri_query(BASE, L_PANEL, pt, "esriGeometryPoint",
                                      "FIRM_PAN,PANEL,SUFFIX,EFF_DATE,PANEL_TYP,PCOMM,DFIRM_ID",
                                      want_geom=False))
        r["bfe_lines_2000ft"] = attrs(esri_query(BASE, L_BFE, pt, "esriGeometryPoint",
                                                 "ELEV,LEN_UNIT,V_DATUM", dist_ft=2000, want_geom=False))
        r["lomr"] = attrs(esri_query(BASE, L_LOMR, pt, "esriGeometryPoint", "*", dist_ft=2000,
                                     want_geom=False))
        out[key] = r
        print(f"== {key}")
        print("   zones on parcel:", [(a.get('FLD_ZONE'), a.get('ZONE_SUBTY'), a.get('STATIC_BFE')) for a in r['zones_on_parcel']])
        print("   zones within 1500 ft:", sorted({(a.get('FLD_ZONE'), a.get('ZONE_SUBTY'), a.get('STATIC_BFE')) for a in r['zones_within_1500ft']}, key=str))
        print("   panel:", r["panel"])
        print("   BFE lines:", r["bfe_lines_2000ft"][:5])
        print("   LOMR:", r["lomr"][:3])
        # map export (transparent PNG of NFHL over the lot window)
        lon, lat = c["lon"], c["lat"]
        d = 0.0045
        bbox = f"{lon-d*1.18},{lat-d},{lon+d*1.18},{lat+d}"
        p = {"bbox": bbox, "bboxSR": 4326, "imageSR": 4326, "size": "1200,1015", "format": "png32",
             "transparent": "true", "layers": "show:28,16,14", "dpi": 150, "f": "image"}
        resp = SESSION.get(BASE + "/export", params=p, timeout=120)
        fn = os.path.join(ASSETS, f"nfhl_{key}.png")
        open(fn, "wb").write(resp.content)
        json.dump({"bbox": [lon - d * 1.18, lat - d, lon + d * 1.18, lat + d]},
                  open(fn.replace(".png", ".json"), "w"))
        print("   map:", resp.status_code, len(resp.content))
    save("flood.json", out)


if __name__ == "__main__":
    main()
