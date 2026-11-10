"""Verified facts for the 10 Nov 2026 re-check of The Shores lots 442, 411 and 441.

Everything here was read on 8-10 Nov 2026 from the source named next to it. GIS/lidar
numbers are read from data/shores3/*.json at import time, so they stay in step with the
pipeline. Literal values below are official records or listing data.
"""
import datetime as dt

from common import load

CREATED = dt.date(2026, 11, 10)
MODEL = "Claude Opus 5.5"
STAMP = CREATED.strftime("%d-%b-%y")

T = load("terrain.json")
MB = load("maxbuild.json")
BA = load("bathymetry.json")
LK = load("lake_levels.json")
SN = load("services_named.json")
SV = load("services.json")

LAKE_NOW = LK["last"][1]            # 312.16 ft, TWDB, 9 Nov 2026
LAKE_NOW_DATE = "9 Nov 2026"
POOL, FLOOD100, FLOWAGE = 315.0, 318.0, 320.0

# 2026 adopted rates per $100 (texastaxtransparency.com, Navarro; same on navarrocad.com)
RATES = [("Navarro County", 0.3500), ("Navarro College", 0.1077), ("Flood Control", 0.0054),
         ("Road & Bridge", 0.0691), ("Mildred ISD", 1.0408)]
RATE = sum(r for _, r in RATES)      # 1.5730 %
HOA_DUES = 1255                      # MLS maintenance fee (lots 442 and 249), per lot per year
MOW = (240, 480)                     # 4 required mows a year, wooded half-acre (estimate)
INS = (100, 200)                     # vacant-land liability cover (estimate)

ORDER = ["lot441", "lot442", "lot411"]   # revised ranking

LOT = {
    "lot442": dict(
        num="442", name="Lot 442 Waters Edge Dr", short="Lot 442", phase="VI",
        acc="#0f766e", grad="linear-gradient(95deg,#115e59,#0f766e 45%,#0d9488)",
        mls="20810887", ad="5680755", lh="https://www.lakehouse.com/lot-442-waters-edge-dr-corsicana-texas-75109-p5680755.html",
        agent="John & Julie Teel, RE/MAX LakeSide Dreams", agent_tel="903-874-0001",
        price=94900, listed="on market since ≥7 Jan 2025 at $125,000 → $110,000 → $94,900 (12 Mar 2026)",
        dom=672, legal="T0077.06 THE SHORES ON RICHLAND CHAMBERS LAKE PH VI LOT 442 .558 ACRES",
        cad_id="64391", geo="T0077-06-04420-000-00-0", acres=0.558, legal_sf=24306,
        owner="Justin Ray Guerrero & Jennifer Marie Rogas (Arlington) · deed 6 Aug 2021, Vol 2021 p 8967",
        cad_mkt=155239, cad_land=152885, cad_imp=2354, wall="steel wall 60 ft (CAD: eff. 2021, 73% good)",
        taxable=142802, tax26=2246.28,
        hist={2022: 68360, 2023: 82640, 2024: 116370, 2025: 155620, 2026: 155239},
        listing_tax="$1,528 and \"est. $2,140\" (earlier report)",
        old_score=7.2, old_rank="#1 of 20",
        photos=dict(hero="5680755_982.jpg", big="5680755_490.jpg",
                    big_cap="Listing drone photo — lot lines drawn by the broker (approximate)"),
        plat="Phase VI plat, Vol 7 pp 395–396 (not yet seen)",
    ),
    "lot411": dict(
        num="411", name="Lot 411 Sailboat Dr", short="Lot 411", phase="V",
        acc="#b45309", grad="linear-gradient(95deg,#78350f,#b45309 45%,#d97706)",
        mls="21334950", ad="7555161", lh="https://www.lakehouse.com/sailboat-dr-lot-411-corsicana-texas-75109-p7555161.html",
        agent="Leslie Melton, eXp Realty", agent_tel="888-519-7431",
        price=65000, listed="listed 17 Jul 2026 at $65,000, no price change",
        dom=116, legal="T0077.05 THE SHORES ON RICHLAND CHAMBERS LAKE PH V LOT 411 .5 ACRES",
        cad_id="64288", geo="T0077-05-04110-000-00-0", acres=0.500, legal_sf=21780,
        owner="Tawney Randell (Odessa) · deed 30 Aug 2023, Vol 2023 p 8227",
        cad_mkt=89720, cad_land=88645, cad_imp=1075, wall="steel wall 100 ft (CAD: built 2010, 20% good)",
        taxable=89720, tax26=1411.30,
        hist={2022: 43560, 2023: 34850, 2024: 67140, 2025: 89740, 2026: 89720},
        listing_tax="$1,029 (listing; matches the 2024 bill)",
        old_score=6.8, old_rank="#2 of 20",
        photos=dict(hero="gal_3yd-NTREIS-21334950_0.jpg", big="gal_3yd-NTREIS-21334950_30.jpg",
                    big_cap="Plat excerpt (listing): east line 95.78 ft on the “Revised 315 Deed Line”"),
        plat="Phase V plat, Vol 7 p 397 (excerpt in listing photo 30)",
    ),
    "lot441": dict(
        num="441", name="Lot 441 Waters Edge Dr", short="Lot 441", phase="VI",
        acc="#6d28d9", grad="linear-gradient(95deg,#4c1d95,#6d28d9 45%,#7c3aed)",
        mls="21407991", ad="6000520", lh="https://www.lakehouse.com/waters-edge-lot-441-corsicana-texas-75109-p6000520.html",
        agent="Annette Goolsby, Ebby Halliday REALTORS", agent_tel="972-772-1369 / 903-654-3354",
        price=105000, listed="re-listed 9 Oct 2026; a 2025 listing was cut by $25K (Redfin, Apr 2025)",
        dom=32, legal="T0077.06 THE SHORES ON RICHLAND CHAMBERS LAKE PH VI LOT 441 .531 ACRES",
        cad_id="64390", geo="T0077-06-04410-000-00-0", acres=0.531, legal_sf=23130,
        owner="Lucia Salas (Coppell) · bought from the developer 16 Jul 2008, Vol 2008 p 6430",
        cad_mkt=70834, cad_land=66753, cad_imp=4081, wall="steel wall 104 ft (CAD: eff. 2021, 73% good)",
        taxable=70834, tax26=1114.23,
        hist={2022: 65050, 2023: 78640, 2024: 112880, 2025: 150240, 2026: 70834},
        listing_tax="$1,206 (listing; matches the 2023 bill)",
        old_score=5.9, old_rank="#15 of 20",
        photos=dict(hero="gal_3yd-NTREIS-21407991_0.jpg", big="gal_3yd-NTREIS-21407991_25.jpg",
                    big_cap="Listing drone photo — lot outline drawn by the broker, canal and steel wall"),
        plat="Phase VI plat, Vol 7 pp 395–396 (not yet seen)",
    ),
}

# Phase VI neighbours, Navarro CAD land value 2025 -> 2026 (navarrocad.com, 10 Nov 2026)
NEIGHBOURS = [("439", 0.505, 162790, 84648), ("441", 0.531, 145490, 66753), ("442", 0.558, 152880, 152885),
              ("443", 0.558, 152880, 68348), ("444", 0.505, 138370, 138367), ("445", 0.505, 138370, 60231),
              ("446", 0.681, 98780, 76830), ("447", 0.590, 85580, 66563)]

# Active asking prices in The Shores (LakeHouse.com, 10 Nov 2026) + one recorded sale
COMPS = [("480 Canal St", "0.52 ac lakefront", 189000), ("Lot 229 The Shores Dr", "0.80 ac peninsula, 100 ft wall", 530000),
         ("Lot 109 Waters Edge Dr", "1.02 ac canal view, off-water", 69900),
         ("Lot 119 Waters Edge Dr", "1.02 ac off-water + boat slip", 100000),
         ("Lot 77 Clubhouse Dr", "1.02 ac interior + boat slip", 75000),
         ("Lots 72 / 139 Clubhouse Dr", "1.02 ac interior", 60000)]
HOMES = [("574 Clubhouse Dr", "4,252 sf, 5 BR, 0.62 ac, open water", 2290000),
         ("908 Sailboat Dr", "3,267 sf, 4 BR, 1.01 ac", 1875000),
         ("205 Canal St", "0.50 ac canal lot, home + guest apt", 957000),
         ("902 Waters Edge Dr", "3,350 sf, 4 BR, 1.03 ac — sold 8 Jul 2026", 1176100)]

# Revised holding-investment score: criterion, weight, {lot: (points, reason)}
SCORE = [
    ("Price vs value", 1.5, {
        "lot442": (0.9, "$94.9k = $170k/ac, $1,580 per canal-ft (highest); 672 days, two cuts"),
        "lot411": (1.2, "$65k = $130k/ac, cheapest; priced like an interior lot"),
        "lot441": (1.0, "$105k = $198k/ac but $1,000 per canal-ft (best)")}),
    ("Holding cost", 1.0, {
        "lot442": (0.5, "$3.1–4.4k/yr; tax $2,246 on an out-of-line CAD value"),
        "lot411": (0.7, "$2.6–3.3k/yr"),
        "lot441": (0.6, "$2.7–4.3k/yr; tax likely rises after sale")}),
    ("Largest home", 1.5, {
        "lot442": (1.3, "septic-limited max ≈10,700 sf heated"),
        "lot411": (1.0, "≈8,500 sf; smallest lot (GIS 0.487 ac)"),
        "lot441": (1.2, "≈8,900–9,800 sf")}),
    ("Private dock & boating", 2.0, {
        "lot442": (1.2, "480 sf max (60 ft); widest canal ≈113 ft; wall"),
        "lot411": (0.6, "280–766 sf, TRWD to decide; silted canal head"),
        "lot441": (1.7, "839 sf max (105 ft); wall; canal ≈92 ft")}),
    ("Water depth & drought", 1.0, {
        "lot442": (0.6, "6.1 / 7.6 ft at full pool, ≈3.3 / 4.8 ft now"),
        "lot411": (0.3, "5.5 / 6.0 ft at full pool, ≈2.7 / 3.2 ft now"),
        "lot441": (0.6, "5.9 / 7.6 ft at full pool, ≈3.1 / 4.8 ft now")}),
    ("Buildability & septic", 1.0, {
        "lot442": (0.7, "pad 2 ft of fall; clay; drip fits"),
        "lot411": (0.7, "all ≥321 ft; rectangle; clay"),
        "lot441": (0.7, "pad 2 ft of fall; clay; drip fits")}),
    ("Flood & site risk", 0.5, {
        "lot442": (0.4, "Zone X; steep 23° bank"),
        "lot411": (0.45, "Zone X; whole lot above 320 ft"),
        "lot441": (0.35, "11% Zone A strip at the shore")}),
    ("Location & access", 0.5, {
        "lot442": (0.4, "same gated community: 71 mi Dallas, 1.2 mi VFD"),
        "lot411": (0.4, "same"), "lot441": (0.4, "same")}),
    ("Liquidity / resale", 0.5, {
        "lot442": (0.25, "unsold for 22 months"),
        "lot411": (0.3, "weak water access limits buyers"),
        "lot441": (0.35, "105 ft of walled canal is the easiest resale")}),
    ("HOA rules", 0.5, {
        "lot442": (0.35, "no rentals <90 days; 9-month build; mowing"),
        "lot411": (0.35, "same"), "lot441": (0.35, "same")}),
]
for k in LOT:
    LOT[k]["score"] = round(sum(c[2][k][0] for c in SCORE), 1)


_ZA = {}


def zone_a_distance_ft(key):
    """Shortest distance (ft) from the CAD lot line to mapped FEMA Zone A, read from the NFHL
    raster saved by 05_flood.py (≈1 km square around the lot, ≈0.9 m pixels). 0 = Zone A on the lot."""
    if key not in _ZA:
        import json
        import os

        import numpy as np
        from PIL import Image

        from common import ASSETS
        meta = json.load(open(os.path.join(ASSETS, f"nfhl_{key}.json")))
        im = np.asarray(Image.open(os.path.join(ASSETS, f"nfhl_{key}.png")).convert("RGBA"))
        W, S, E, N = meta["bbox"]; h, w = im.shape[:2]; c = np.cos(np.radians((N + S) / 2))
        yy, xx = np.nonzero((im[..., 3] > 30) & (im[..., 0] < 60) & (im[..., 1] > 200))   # Zone A fill colour
        zx = (xx + 0.5) / w * (E - W) * 111320 * c; zy = (N - (yy + 0.5) / h * (N - S) - S) * 110950
        cs = [np.array(p["lonlat"]) for p in T[key]["corners"]]
        pts = np.array([a + t * (b - a) for a, b in zip(cs, cs[1:] + cs[:1]) for t in np.linspace(0, 1, 80)])
        px = (pts[:, 0] - W) * 111320 * c; py = (pts[:, 1] - S) * 110950
        d = np.sqrt((zx[None, :] - px[:, None]) ** 2 + (zy[None, :] - py[:, None]) ** 2).min() if len(zx) else None
        _ZA[key] = None if d is None else d / 0.3048
    return _ZA[key]


def facts(key):
    """Derived numbers used throughout the report."""
    d = LOT[key]; t = T[key]; m = MB[key]; b = BA[key]["within_150ft"]
    lake_ft = t["frontage_lake_ft"]
    out = dict(
        gis_sf=t["lot_area_gis_sqft"], road_ft=t["frontage_road_ft"], lake_ft=lake_ft,
        zmin=t["elev"]["min_land_ft"], zmax=t["elev"]["max_ft"], zmean=t["elev"]["mean_ft"],
        above320=t["elev"]["area_above_320_sqft"], below320=t["elev"]["area_below_320_sqft"],
        depth_mean=b["mean_depth_ft"], depth_max=b["max_depth_ft"], bottom=b["min_bottom_ft"],
        now_mean=round(b["mean_depth_ft"] - (POOL - LAKE_NOW), 1),
        now_max=round(b["max_depth_ft"] - (POOL - LAKE_NOW), 1),
        low22_max=round(b["max_depth_ft"] - (POOL - LK["dec2022_jan2023_mean"]), 1),
        canal_w=(m.get("canal") or {}).get("canal_width_315_ft"),
        max50=m and m["lake50"], max75=m and m["lake75"], dock=m["dock"],
        price_ac=d["price"] / d["acres"],
    )
    tax_now = d["tax26"]
    tax_at_price = (d["price"] + d["cad_imp"]) * RATE / 100
    tax_2025lvl = (d["hist"][2025]) * RATE / 100
    fixed_lo, fixed_hi = HOA_DUES + MOW[0] + INS[0], HOA_DUES + MOW[1] + INS[1]
    tax_mkt = d["cad_mkt"] * RATE / 100
    # the 20 % limit on non-homestead increases (Tax Code 23.231) covers 2024-2026 only and never
    # passes to a buyer; the CAD
    # may move the value toward the sale price (442 down on protest, 441 back up)
    worst = {"lot442": tax_mkt, "lot411": tax_now, "lot441": tax_2025lvl}[key]
    out["hold"] = dict(tax_now=tax_now, tax_at_price=tax_at_price, tax_2025=tax_2025lvl, tax_mkt=tax_mkt,
                       fixed_lo=fixed_lo, fixed_hi=fixed_hi,
                       now_lo=tax_now + fixed_lo, now_hi=tax_now + fixed_hi,
                       after_lo=min(tax_now, tax_at_price) + fixed_lo,
                       after_hi=max(tax_now, worst) + fixed_hi, worst_tax=max(tax_now, worst),
                       capital=d["price"] * 0.045)
    return out
