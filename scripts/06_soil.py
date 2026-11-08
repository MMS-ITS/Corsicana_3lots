"""USDA NRCS soil data (SSURGO via Soil Data Access) for each parcel.

Map units intersecting the parcel, their share of the lot (sampled on a grid),
major components with drainage / hydrologic group / slope / taxonomy, horizon
properties (texture fractions, pH, organic matter, Ksat, shrink-swell LEP),
restrictive layers, water-table depth, and the NRCS engineering interpretations
used in the report (dwellings, septic absorption, TX drip/leaching chambers,
shallow excavations, lawns & landscaping, local roads, GPR).
Also fetches map-unit polygons around the lot for the soil map.
"""
import json

from shapely.geometry import Point, Polygon, mapping, shape
from shapely import wkt as shwkt

from common import load, post, save

SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
RULES = [
    "ENG - Dwellings Without Basements",
    "ENG - Dwellings With Basements",
    "ENG - Septic Tank Absorption Fields",
    "ENG - Septic Tank Leaching Chamber (TX)",
    "ENG - Septic Tank, Subsurface Drip Irrigation (TX)",
    "ENG - Septic Tank, Gravity Distribution (TX)",
    "ENG - Shallow Excavations",
    "ENG - Lawn, Landscape, Golf Fairway",
    "ENG - Local Roads and Streets",
    "Ground Penetrating Radar Penetration",
    "AGR - Farmland Classification",
    "FOR - Potential Erosion Hazard (Road/Trail)",
]


def sql(q):
    d = post(SDA, data={"query": q, "format": "JSON+COLUMNNAME"}, timeout=240)
    t = d.get("Table") or []
    if not t:
        return []
    hdr = t[0]
    return [dict(zip(hdr, row)) for row in t[1:]]


def wkt_ring(ring):
    pts = ", ".join(f"{x:.7f} {y:.7f}" for x, y in ring)
    if ring[0] != ring[-1]:
        pts += f", {ring[0][0]:.7f} {ring[0][1]:.7f}"
    return f"polygon(({pts}))"


def main():
    P = load("parcels.json")
    out = {}
    for key, rec in P.items():
        ring = rec["ring"]
        poly = Polygon(ring)
        r = {}
        w = wkt_ring(ring)
        r["mapunits"] = sql(f"""SELECT mu.mukey, mu.muname, mu.musym, l.areasymbol, l.areaname
FROM mapunit mu JOIN legend l ON l.lkey = mu.lkey
WHERE mu.mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{w}'))""")
        print("==", key, [(m["musym"], m["muname"]) for m in r["mapunits"]])
        # share of lot by map unit: intersect map-unit polygons with the parcel
        polys = sql(f"""SELECT mupolygonkey, mukey, mupolygongeo.STAsText() AS wkt
FROM mupolygon WHERE mupolygongeo.STIntersects(geometry::STGeomFromText('{w.upper()}', 4326)) = 1""")
        share = {}
        geoms = []
        for p in polys:
            g = shwkt.loads(p["wkt"])
            inter = g.intersection(poly)
            share[p["mukey"]] = share.get(p["mukey"], 0.0) + inter.area
        tot = sum(share.values()) or 1.0
        r["share_pct"] = {k: round(100 * v / tot, 1) for k, v in share.items()}
        # wider polygons for the map (+-400 m)
        c = rec["centroid"]
        d = 0.0045
        env = (f"POLYGON(({c['lon']-d*1.18} {c['lat']-d}, {c['lon']+d*1.18} {c['lat']-d}, "
               f"{c['lon']+d*1.18} {c['lat']+d}, {c['lon']-d*1.18} {c['lat']+d}, {c['lon']-d*1.18} {c['lat']-d}))")
        wide = sql(f"""SELECT p.mukey, m.musym, m.muname, p.mupolygongeo.STAsText() AS wkt
FROM mupolygon p JOIN mapunit m ON m.mukey = p.mukey
WHERE p.mupolygongeo.STIntersects(geometry::STGeomFromText('{env}', 4326)) = 1""")
        r["map_polygons"] = [{"mukey": x["mukey"], "musym": x["musym"], "muname": x["muname"],
                              "geom": mapping(shwkt.loads(x["wkt"]))} for x in wide]
        mk = ",".join(f"'{m['mukey']}'" for m in r["mapunits"])
        r["muaggatt"] = sql(f"""SELECT mukey, muname, drclassdcd, hydgrpdcd, flodfreqdcd, pondfreqprs,
 wtdepannmin, wtdepaprjunmin, brockdepmin, slopegraddcp, slopegradwta, aws0100wta, engdwobdcd, engstafdcd
FROM muaggatt WHERE mukey IN ({mk})""")
        r["components"] = sql(f"""SELECT c.mukey, c.cokey, c.compname, c.comppct_r, c.majcompflag, c.drainagecl, c.hydgrp,
 c.taxclname, c.taxorder, c.slope_l, c.slope_r, c.slope_h, c.runoff, c.erocl, c.hydricrating, c.tfact,
 c.nirrcapcl, c.corcon, c.corsteel, c.geomdesc
FROM component c WHERE c.mukey IN ({mk}) ORDER BY c.mukey, c.comppct_r DESC""")
        ck = ",".join(f"'{x['cokey']}'" for x in r["components"] if x["majcompflag"] == "Yes")
        r["horizons"] = sql(f"""SELECT ch.cokey, ch.hzname, ch.hzdept_r, ch.hzdepb_r, ch.sandtotal_r, ch.silttotal_r,
 ch.claytotal_r, ch.om_r, ch.ph1to1h2o_r, ch.ksat_r, ch.lep_r, ch.awc_r, ch.cec7_r, ch.caco3_r, ch.ec_r,
 ch.sar_r, ch.kwfact, ch.ll_r, ch.pi_r
FROM chorizon ch WHERE ch.cokey IN ({ck}) ORDER BY ch.cokey, ch.hzdept_r""")
        r["texture"] = sql(f"""SELECT ch.cokey, ch.hzdept_r, tg.texture, tg.rvindicator
FROM chorizon ch JOIN chtexturegrp tg ON tg.chkey = ch.chkey
WHERE ch.cokey IN ({ck}) AND tg.rvindicator='Yes' ORDER BY ch.cokey, ch.hzdept_r""")
        r["restrictions"] = sql(f"""SELECT cokey, reskind, reshard, resdept_r, resdepb_r
FROM corestrictions WHERE cokey IN ({ck})""")
        r["water_table"] = sql(f"""SELECT co.cokey, cm.month, cs.soimoistdept_r, cs.soimoiststat
FROM comonth cm JOIN cosoilmoist cs ON cs.comonthkey = cm.comonthkey JOIN component co ON co.cokey = cm.cokey
WHERE co.cokey IN ({ck}) AND cs.soimoiststat = 'Wet' ORDER BY co.cokey, cs.soimoistdept_r""")
        rules = ",".join(f"'{x}'" for x in RULES)
        r["interpretations"] = sql(f"""SELECT cokey, mrulename, interphr, interphrc
FROM cointerp WHERE cokey IN ({ck}) AND ruledepth = 0 AND mrulename IN ({rules})""")
        # reasons (first-level sub-rules) for the septic and dwelling ratings
        r["interp_reasons"] = sql(f"""SELECT cokey, mrulename, rulename, interphr, interphrc
FROM cointerp WHERE cokey IN ({ck}) AND ruledepth = 1 AND interphr > 0 AND mrulename IN
('ENG - Septic Tank Absorption Fields','ENG - Dwellings Without Basements','ENG - Septic Tank, Subsurface Drip Irrigation (TX)')""")
        out[key] = r
        for m in r["muaggatt"]:
            print("  ", m["muname"], "| drain", m["drclassdcd"], "| HSG", m["hydgrpdcd"], "| flood", m["flodfreqdcd"],
                  "| wt", m["wtdepannmin"], "| rock", m["brockdepmin"], "| slope", m["slopegraddcp"])
        print("   share:", r["share_pct"])
        for x in r["interpretations"]:
            print("    ", x["cokey"], x["mrulename"][:48], "->", x["interphrc"], x["interphr"])
        for x in r["restrictions"]:
            print("    restriction", x)
    save("soil.json", out)


if __name__ == "__main__":
    main()
