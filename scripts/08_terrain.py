"""Terrain, frontage, slope, cross-section, envelope and septic-area analysis.

Everything here is GIS / lidar-derived (USGS 3DEP 1 m DEM, 2022 North-Central
Texas lidar; NAVD88 ~= NGVD29 here, VERTCON 3.0 shift < 0.03 ft) and parcel
lines from the Navarro CAD GIS (StratMap). Not a survey.

Writes data/terrain.json and data/grid_<lot>.npz (local-feet grids for figures).
"""
import math

import numpy as np
import rasterio.features
from affine import Affine
from matplotlib.path import Path as MPath
from pyproj import Transformer
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import nearest_points, unary_union
from shapely import affinity

from common import DATA, FT2M, M2FT, load, local_xy, save

TR = Transformer.from_crs(4326, 26914, always_xy=True)
INV = Transformer.from_crs(26914, 4326, always_xy=True)
POOL = 315.0          # TRWD conservation pool (ft msl)
FLOOD100 = 318.0      # TRWD-published 100-year flood level (ft msl)
FLOWAGE = 320.0       # TRWD flood-flowage easement line (ft msl)
RUN50 = 50.0          # ft window for "maximum slope over 50 ft"
# Navarro County Richland-Chambers Lakeshore Zoning Ordinance, Table B-1, SF-3
SETBACK = {"road": 35.0, "lake": 15.0, "side": 10.0}
# TCEQ 30 TAC 285.91 Table III (water-saving fixtures), gal/day by bedrooms
Q_GPD = {2: 180, 3: 240, 4: 300, 5: 360, 6: 420}
RA_CLASS_IV = 0.10    # gal/sf/day, drip irrigation in Class IV (clay) soil
DRIP_LAKE_SETBACK = 50.0   # ft from normal pool (drip w/ secondary treatment & disinfection)
DRIP_LINE_SETBACK = 5.0    # ft from property lines and foundations


def load_dem(key):
    d = np.load(f"{DATA}/dem_{key}_2022.npz")
    return d["z_ft"].astype("float64"), float(d["x0"]), float(d["y0"]), float(d["res"])


def to_rc(x, y, x0, y0, res):
    return (y0 - np.asarray(y)) / res, (np.asarray(x) - x0) / res


def sample(z, xs, ys, x0, y0, res):
    r, c = to_rc(xs, ys, x0, y0, res)
    return ndimage.map_coordinates(z, [np.atleast_1d(r), np.atleast_1d(c)], order=1, mode="nearest")


def slope_grid(zft, res_m):
    zf = zft * FT2M
    p = np.pad(zf, 1, mode="edge")
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d_, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dzdx = ((c + 2 * f + i) - (a + 2 * d_ + g)) / (8 * res_m)
    dzdy_s = ((g + 2 * h + i) - (a + 2 * b + c)) / (8 * res_m)
    return np.hypot(dzdx, dzdy_s), dzdx, -dzdy_s


def classify(avg_pct):
    for lim, name in ((1, "Flat"), (2, "Nearly flat"), (5, "Gentle slope"), (10, "Moderate slope"),
                      (20, "Steep slope")):
        if avg_pct < lim:
            return name
    return "Very steep slope"


def grading(max50_pct):
    if max50_pct < 5:
        return "Minimal grading"
    if max50_pct < 10:
        return "Moderate: cut-and-fill pad of ~1-3 ft"
    if max50_pct < 15:
        return "Significant: cut-and-fill pad, stem wall or stepped slab"
    return "Retaining walls / extensive site engineering"


def mask_polygon(mask, x0, y0, res):
    tf = Affine(res, 0, x0 - res / 2, 0, -res, y0 + res / 2)
    polys = [shape(g) for g, v in rasterio.features.shapes(mask.astype("uint8"), mask=mask, transform=tf) if v == 1]
    return unary_union(polys) if polys else Polygon()


def best_rect(env, w_ft, d_ft, angles, zfun=None):
    """Place a w x d (ft) rectangle inside polygon env (UTM m).

    Among all placements that fit, choose the one with the smallest ground-elevation
    range under the footprint (least grading); ties broken by distance from the edge.
    """
    if env.is_empty:
        return None
    w, d = w_ft * FT2M, d_ft * FT2M
    minx, miny, maxx, maxy = env.bounds
    best = None
    gx_, gy_ = np.meshgrid(np.linspace(-w / 2, w / 2, 7), np.linspace(-d / 2, d / 2, 6))
    for ang in angles:
        base = affinity.rotate(Polygon([(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]),
                               ang, origin=(0, 0))
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for x in np.arange(minx, maxx, 1.0):
            for y in np.arange(miny, maxy, 1.0):
                r = affinity.translate(base, x, y)
                if not env.contains(r):
                    continue
                rng = 0.0
                if zfun is not None:
                    px = x + gx_ * ca - gy_ * sa
                    py = y + gx_ * sa + gy_ * ca
                    zz = zfun(px.ravel(), py.ravel())
                    rng = float(zz.max() - zz.min())
                m = env.exterior.distance(r.centroid)
                score = (round(rng, 1), -m)
                if best is None or score < best[0]:
                    best = (score, r, ang, rng)
    if best is None:
        return None
    return (best[0], best[1], best[2], best[3])


def main():
    P = load("parcels.json")
    osm = load("osm_local.json")
    flood = load("flood.json")
    soil = load("soil.json")
    out = {}
    for key, rec in P.items():
        z, x0, y0, res = load_dem(key)
        ny, nx = z.shape
        X = x0 + np.arange(nx) * res
        Y = y0 - np.arange(ny) * res
        XX, YY = np.meshgrid(X, Y)
        ring = [TR.transform(lon, lat) for lon, lat in rec["ring"]]
        lot = Polygon(ring).buffer(0)
        coords = list(lot.exterior.coords)

        # water = largest hydro-flattened surface in the window
        wl = float(np.nanpercentile(z, 0.5))
        lab, n = ndimage.label(z <= wl + 0.25)
        sizes = ndimage.sum(np.ones_like(z), lab, range(1, n + 1))
        water = lab == (1 + int(np.argmax(sizes)))
        dist_m = ndimage.distance_transform_edt(~water) * res

        def wdist(x, y):
            r, c = to_rc(x, y, x0, y0, res)
            return dist_m[int(np.clip(round(float(r)), 0, ny - 1)), int(np.clip(round(float(c)), 0, nx - 1))]

        roads = []
        for e in osm.get(key, []):
            if e.get("type") == "way" and "highway" in e.get("tags", {}) and e.get("geometry"):
                pts = [TR.transform(g["lon"], g["lat"]) for g in e["geometry"]]
                if len(pts) > 1:
                    roads.append((e["tags"].get("name") or e["tags"].get("highway"), LineString(pts)))
        road_union = unary_union([r for _, r in roads])

        # ---- edges / frontage
        neigh = [Polygon([TR.transform(lon, lat) for lon, lat in p["ring"]]).buffer(0)
                 for p in rec["all_parcels"] if p["geo_id"] != rec["target"]["geo_id"] and p.get("legal")]
        sc = list(Polygon(coords).simplify(0.3).exterior.coords)
        edges = []
        for i in range(len(sc) - 1):
            seg = LineString([sc[i], sc[i + 1]])
            pts = [seg.interpolate(t, normalized=True) for t in np.linspace(0.1, 0.9, 9)]
            wd = float(np.median([wdist(p.x, p.y) for p in pts]))
            zz = float(np.median(sample(z, [p.x for p in pts], [p.y for p in pts], x0, y0, res)))
            rd = float(np.median([road_union.distance(p) for p in pts]))
            shared = np.median([min(q.exterior.distance(p) for q in neigh) for p in pts]) < 1.5 if neigh else False
            if wd < 9.0 or zz < FLOWAGE:
                kind = "lake"
            elif shared:
                kind = "side"
            else:
                kind = "road" if rd < 14.0 else "side"
            name = min(roads, key=lambda r: r[1].distance(seg.interpolate(0.5, normalized=True)))[0] \
                if kind == "road" else None
            edges.append({"i": i, "kind": kind, "len_ft": round(seg.length * M2FT, 1), "water_m": round(wd, 1),
                          "road_m": round(rd, 1), "z_med": round(zz, 1), "road_name": name,
                          "seg": [list(sc[i]), list(sc[i + 1])]})
        front_ft = round(sum(e["len_ft"] for e in edges if e["kind"] == "road"), 1)
        lake_ft = round(sum(e["len_ft"] for e in edges if e["kind"] == "lake"), 1)

        # ---- lot surface statistics
        inside = MPath(np.array(coords)).contains_points(np.c_[XX.ravel(), YY.ravel()]).reshape(z.shape)
        land = inside & ~water & (dist_m >= 1.0)
        zs = ndimage.gaussian_filter(z, 1.0)
        slope, gx, gy = slope_grid(zs, res)
        zl, sl = z[land], slope[land]
        imax = np.unravel_index(np.argmax(np.where(land, z, -1e9)), z.shape)
        imin = np.unravel_index(np.argmin(np.where(land, z, 1e9)), z.shape)
        area_above_320 = float((land & (zs >= FLOWAGE)).sum() * res * res * M2FT * M2FT)
        area_below_320 = float((land & (zs < FLOWAGE)).sum() * res * res * M2FT * M2FT)

        # ---- maximum grade over any 50-ft run (both ends on lot land), 36 directions
        step = RUN50 * FT2M
        rr, cc = np.nonzero(land)
        xa, ya = XX[rr, cc], YY[rr, cc]
        best = (0.0, None)
        for ang in np.arange(0, 180, 5):
            dx, dy = math.sin(math.radians(ang)) * step, math.cos(math.radians(ang)) * step
            for sgn in (1, -1):
                xb, yb = xa + sgn * dx, ya + sgn * dy
                rb, cb = to_rc(xb, yb, x0, y0, res)
                rbi = np.clip(np.round(rb).astype(int), 0, ny - 1)
                cbi = np.clip(np.round(cb).astype(int), 0, nx - 1)
                ok = land[rbi, cbi]
                zb = sample(z, xb, yb, x0, y0, res)
                g = np.where(ok, np.abs(zb - z[rr, cc]) / RUN50, 0.0)
                j = int(np.argmax(g))
                if g[j] > best[0]:
                    best = (float(g[j]), [float(xa[j]), float(ya[j]), float(xb[j]), float(yb[j])])
        max50_pct = best[0] * 100

        vx, vy = -float(np.mean(gx[land])), -float(np.mean(gy[land]))
        drain_az = (math.degrees(math.atan2(vx, vy)) + 360) % 360

        # ---- road -> lake transect along the lot spine
        lake_line = unary_union([LineString(e["seg"]) for e in edges if e["kind"] == "lake"])
        road_line = unary_union([LineString(e["seg"]) for e in edges if e["kind"] == "road"])
        lm = lake_line.interpolate(0.5, normalized=True) if lake_line.geom_type == "LineString" else \
            lake_line.centroid
        cands = [road_line.interpolate(t, normalized=True) for t in np.linspace(0.02, 0.98, 49)]
        rp = max(cands, key=lambda p: LineString([p, lm]).intersection(lot).length)
        u = np.array([lm.x - rp.x, lm.y - rp.y]); u /= np.linalg.norm(u)
        npnt = nearest_points(road_union, rp)[0]
        start = np.array([rp.x, rp.y]) - u * max(npnt.distance(rp) + 2.0, 6.0)
        endp = np.array([lm.x, lm.y]) + u * 14.0
        Ltot = float(np.linalg.norm(endp - start))
        nn = int(Ltot * M2FT) + 1
        tt = np.linspace(0, 1, nn)
        xs, ys = start[0] + (endp[0] - start[0]) * tt, start[1] + (endp[1] - start[1]) * tt
        prof = sample(z, xs, ys, x0, y0, res)
        dft = tt * Ltot * M2FT
        tl = LineString([tuple(start), tuple(endp)])
        inter = tl.intersection(lot)
        parts = [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", [])]
        parts = [g for g in parts if g.length > 0.5]
        a0 = min(Point(start).distance(Point(g.coords[0])) for g in parts) * M2FT
        a1 = max(Point(start).distance(Point(g.coords[-1])) for g in parts) * M2FT
        wm = np.array([wdist(x, y) < 0.5 for x, y in zip(xs, ys)])
        shore = float(dft[int(np.argmax(wm))]) if wm.any() else float(dft[-1])
        sel = (dft >= a0) & (dft <= min(a1, shore))
        zp, dp = prof[sel], dft[sel]
        hi = int(np.argmax(zp))
        cross = np.where((prof[:-1] >= POOL) & (prof[1:] < POOL))[0]
        d315 = float(dft[cross[-1]]) if len(cross) else shore
        cross320 = np.where((prof[:-1] >= FLOWAGE) & (prof[1:] < FLOWAGE))[0]
        d320 = float(dft[cross320[-1]]) if len(cross320) else None
        run = d315 - float(dp[hi])

        def zat(d):
            return float(np.interp(d, dft, prof))
        w50 = [(abs(zat(d + RUN50) - zat(d)) / RUN50, d) for d in np.arange(a0, min(a1, shore) - RUN50 + 0.01, 1.0)]
        w50max = max(w50) if w50 else (0.0, a0)
        bank_rise = zat(d315 - 20.0) - POOL
        bank_pct = bank_rise / 20.0 * 100
        s10 = max([(abs(zat(d + 10) - zat(d)) / 10.0, d) for d in np.arange(a0, shore - 10, 1.0)] or [(0, 0)])
        section = {
            "dist_ft": [round(float(v), 1) for v in dft], "z_ft": [round(float(v), 2) for v in prof],
            "front_lot_line_ft": round(a0, 1), "rear_lot_line_ft": round(a1, 1), "shore_ft": round(shore, 1),
            "d315_ft": round(d315, 1), "d320_ft": None if d320 is None else round(d320, 1),
            "high_ft": round(float(zp.max()), 2), "high_at_ft": round(float(dp[hi]), 1),
            "road_crown_ft": round(zat(0.0), 2), "front_line_z": round(zat(a0), 2),
            "low_land_ft": round(float(zp.min()), 2), "water_level_ft": round(wl, 2),
            "relief_to_pool_ft": round(float(zp.max()) - POOL, 2),
            "run_high_to_pool_ft": round(run, 1),
            "road_to_pool_ft": round(d315 - a0, 1),
            "avg_grade_pct": round((float(zp.max()) - POOL) / max(run, 1) * 100, 2),
            "direct_angle_deg": round(math.degrees(math.atan2(float(zp.max()) - POOL, max(run, 1))), 2),
            "max50_pct": round(w50max[0] * 100, 2), "max50_deg": round(math.degrees(math.atan(w50max[0])), 2),
            "max50_from_ft": round(float(w50max[1]), 1),
            "bank20_pct": round(bank_pct, 1), "bank20_deg": round(math.degrees(math.atan(bank_pct / 100)), 1),
            "steep10_pct": round(s10[0] * 100, 1), "steep10_deg": round(math.degrees(math.atan(s10[0])), 1),
            "steep10_from_ft": round(float(s10[1]), 1),
            "start_utm": start.tolist(), "end_utm": endp.tolist(),
            "bearing_deg": round((math.degrees(math.atan2(u[0], u[1])) + 360) % 360, 1),
        }

        # ---- building envelope: setbacks + keep >= 2 ft above the TRWD flowage line
        env = lot
        for e in edges:
            env = env.difference(LineString(e["seg"]).buffer(SETBACK[e["kind"]] * FT2M, cap_style=2, join_style=2))
        hi_ground = mask_polygon(zs >= FLOWAGE + 2.0, x0, y0, res)
        env = env.intersection(hi_ground).buffer(0)
        if env.geom_type == "MultiPolygon":
            env = max(env.geoms, key=lambda g: g.area)
        # slope inside the buildable envelope (this, not the lakeside bank, drives grading)
        env_mask = MPath(np.array(env.exterior.coords)).contains_points(
            np.c_[XX.ravel(), YY.ravel()]).reshape(z.shape) & land
        env_slope_mean = float(slope[env_mask].mean() * 100) if env_mask.any() else None
        er, ec = np.nonzero(env_mask)
        exa, eya = XX[er, ec], YY[er, ec]
        env_best = 0.0
        for ang in np.arange(0, 180, 5):
            dx, dy = math.sin(math.radians(ang)) * step, math.cos(math.radians(ang)) * step
            for sgn in (1, -1):
                xb, yb = exa + sgn * dx, eya + sgn * dy
                rb, cb = to_rc(xb, yb, x0, y0, res)
                ok = env_mask[np.clip(np.round(rb).astype(int), 0, ny - 1), np.clip(np.round(cb).astype(int), 0, nx - 1)]
                g = np.where(ok, np.abs(sample(z, xb, yb, x0, y0, res) - z[er, ec]) / RUN50, 0.0)
                env_best = max(env_best, float(g.max()) if g.size else 0.0)
        env_zmin = float(z[env_mask].min()) if env_mask.any() else None
        env_zmax = float(z[env_mask].max()) if env_mask.any() else None
        # rear-half coverage limit (Table B footnote ***): 50% of the lot area behind the
        # line joining side-line midpoints.  Reported, not drawn.
        env_area = env.area * M2FT * M2FT
        # candidate house footprints (two-storey 5-BR ~3,200-3,600 sf heated + 3-car garage)
        spine = (math.degrees(math.atan2(u[0], u[1])))
        angles = [-spine + k for k in (0, 90)] + [-spine + k for k in (-10, 10, 80, 100)]
        fits = {}

        def zfun(px, py):
            return sample(z, px, py, x0, y0, res)
        for label, (w, d) in {"two-storey 5BR 60x46 ft + garage (2,760 sf)": (60, 46),
                              "one-storey 5BR 84x56 ft incl. garage (4,700 sf)": (84, 56)}.items():
            b = best_rect(env, w, d, angles, zfun)
            if b is None:
                fits[label] = None
                continue
            poly = b[1]
            # level-pad earthwork: pad = footprint + 5 ft apron, balanced at median grade
            pad = poly.buffer(5 * FT2M, join_style=2)
            pm = MPath(np.array(pad.exterior.coords)).contains_points(
                np.c_[XX.ravel(), YY.ravel()]).reshape(z.shape)
            zz = z[pm]
            lvl = float(np.median(zz))
            cell_sf = (res * M2FT) ** 2
            cut = float(np.clip(zz - lvl, 0, None).sum() * cell_sf / 27.0)
            fill = float(np.clip(lvl - zz, 0, None).sum() * cell_sf / 27.0)
            fits[label] = {"angle": round(b[2], 1), "poly": [list(c) for c in poly.exterior.coords],
                           "ground_range_ft": round(float(zz.max() - zz.min()), 1),
                           "ground_min_ft": round(float(zz.min()), 1), "ground_max_ft": round(float(zz.max()), 1),
                           "pad_level_ft": round(lvl, 1), "cut_cy": round(cut), "fill_cy": round(fill)}

        # ---- drip-field area (septic case): lot minus 50 ft from the 315 ft line, minus
        # 5 ft from lot lines, minus the house (two-storey footprint + 5 ft) and a 16-ft drive
        pool_poly = mask_polygon(zs < POOL, x0, y0, res).buffer(0)
        lake_buf = pool_poly.buffer(DRIP_LAKE_SETBACK * FT2M)
        drip = lot.buffer(-DRIP_LINE_SETBACK * FT2M).difference(lake_buf)
        house = fits.get("two-storey 5BR 60x46 ft + garage (2,760 sf)")
        if house:
            hp = Polygon(house["poly"])
            drip = drip.difference(hp.buffer(DRIP_LINE_SETBACK * FT2M))
            # driveway: from house centroid to nearest road frontage point
            rpt = nearest_points(road_line, hp.centroid)[0]
            drive = LineString([hp.centroid, rpt]).buffer(8.0 * FT2M)
            drip = drip.difference(drive.buffer(DRIP_LINE_SETBACK * FT2M))
        drip = drip.buffer(0)
        drip_area = drip.area * M2FT * M2FT
        need = {br: round(q / RA_CLASS_IV) for br, q in Q_GPD.items()}
        max_br = max([br for br, a in need.items() if a <= drip_area] or [0])

        # ---- FEMA Zone A edge elevation near the lot (what elevation the A zone follows)
        zone_a_z = []
        for g in flood[key].get("zone_geoms_1500", []):
            if (g["a"] or {}).get("FLD_ZONE") == "A" and g["g"]:
                for rng in g["g"]["rings"]:
                    pts = [TR.transform(lon, lat) for lon, lat in rng]
                    for (px, py) in pts[::3]:
                        r, c = to_rc(px, py, x0, y0, res)
                        if 2 < r < ny - 2 and 2 < c < nx - 2 and dist_m[int(r), int(c)] > 3:
                            zone_a_z.append(float(sample(z, [px], [py], x0, y0, res)[0]))
        zone_a_inside = 0.0
        for g in flood[key].get("zone_geoms", []):
            pass
        za = None
        if zone_a_z:
            za = {"median": round(float(np.median(zone_a_z)), 1), "p25": round(float(np.percentile(zone_a_z, 25)), 1),
                  "p75": round(float(np.percentile(zone_a_z, 75)), 1), "n": len(zone_a_z)}
        # share of the lot inside Zone A polygons
        a_polys = []
        for g, a in zip(flood[key].get("zone_geoms", []), flood[key].get("zones_on_parcel", [])):
            if a.get("FLD_ZONE") == "A" and g:
                a_polys += [Polygon([TR.transform(lon, lat) for lon, lat in rng]).buffer(0) for rng in g["rings"]]
        a_union = unary_union(a_polys) if a_polys else Polygon()
        zone_a_pct = round(100 * lot.intersection(a_union).area / lot.area, 1)

        # ---- exported geometry is in a true-north local frame (feet east/north of the
        # parcel centroid), so figures carry a true north arrow (UTM grid north here is
        # ~1.5 deg off true north).
        cx, cy = lot.centroid.x, lot.centroid.y
        lon0, lat0 = INV.transform(cx, cy)

        def lf(pt):
            lon, lat = INV.transform(float(pt[0]), float(pt[1]))
            x, y = local_xy(lon, lat, lon0, lat0)
            return [round(x, 1), round(y, 1)]

        def poly_lf(p):
            if p is None or p.is_empty:
                return []
            gs = [p] if p.geom_type == "Polygon" else list(p.geoms)
            return [[lf(c) for c in g.exterior.coords] for g in gs if g.area > 1]

        hi_xy = (X[imax[1]], Y[imax[0]]); lo_xy = (X[imin[1]], Y[imin[0]])
        out[key] = {
            "lot_area_gis_sqft": round(lot.area * M2FT * M2FT), "frontage_road_ft": front_ft,
            "frontage_lake_ft": lake_ft,
            "edges": [{k: v for k, v in e.items() if k != "seg"} | {"seg_lf": [lf(e["seg"][0]), lf(e["seg"][1])]}
                      for e in edges],
            "ring_lf": [lf(c) for c in coords],
            "elev": {"min_land_ft": round(float(zl.min()), 2), "max_ft": round(float(zl.max()), 2),
                     "mean_ft": round(float(zl.mean()), 2), "median_ft": round(float(np.median(zl)), 2),
                     "relief_ft": round(float(zl.max() - zl.min()), 2), "water_surface_2022_ft": round(wl, 2),
                     "high_lf": lf(hi_xy), "low_lf": lf(lo_xy),
                     "high_lonlat": INV.transform(*hi_xy), "low_lonlat": INV.transform(*lo_xy),
                     "area_above_320_sqft": round(area_above_320), "area_below_320_sqft": round(area_below_320)},
            "slope": {"mean_pct": round(float(sl.mean() * 100), 1), "median_pct": round(float(np.median(sl) * 100), 1),
                      "p90_pct": round(float(np.percentile(sl, 90) * 100), 1),
                      "max_cell_pct": round(float(sl.max() * 100), 1),
                      "mean_deg": round(math.degrees(math.atan(float(sl.mean()))), 1),
                      "max50_pct": round(max50_pct, 1), "max50_deg": round(math.degrees(math.atan(best[0])), 1),
                      "max50_line_lf": [lf(best[1][:2]), lf(best[1][2:])] if best[1] else None,
                      "drain_az_deg": round(drain_az, 0),
                      "class": classify(float(sl.mean() * 100)),
                      "env_mean_pct": None if env_slope_mean is None else round(env_slope_mean, 1),
                      "env_max50_pct": round(env_best * 100, 1),
                      "env_z_range": [None if env_zmin is None else round(env_zmin, 1),
                                      None if env_zmax is None else round(env_zmax, 1)],
                      "grading": grading(env_best * 100)},
            "section": section,
            "section_lf": [lf(start), lf(endp)],
            "envelope_lf": poly_lf(env), "envelope_sqft": round(env_area),
            "fits": {k: (None if v is None else {kk: vv for kk, vv in v.items() if kk != "poly"}
                         | {"poly_lf": [lf(c) for c in v["poly"]]}) for k, v in fits.items()},
            "drip": {"area_sqft": round(drip_area), "need_sqft": need, "max_bedrooms": max_br,
                     "poly_lf": poly_lf(drip)},
            "pool315_lf": poly_lf(pool_poly.intersection(lot.buffer(80))),
            "zoneA_edge_elev_ft": za, "zoneA_pct_of_lot": zone_a_pct,
            "zoneA_lf": poly_lf(a_union.intersection(lot.buffer(60))),
            "centroid_utm": [cx, cy], "centroid_lonlat": [lon0, lat0],
            "corners": [{"lf": lf(c), "lonlat": [round(v, 6) for v in INV.transform(*c)]} for c in sc[:-1]],
        }
        r = out[key]
        print(f"== {key}: GIS {r['lot_area_gis_sqft']} sf | road front {front_ft} ft | lake front {lake_ft} ft")
        for e in r["edges"]:
            print(f"     edge {e['i']}: {e['kind']:5s} {e['len_ft']:6.1f} ft  water {e['water_m']} m  road {e['road_m']} m  z {e['z_med']}  {e['road_name'] or ''}")
        print("   elev", r["elev"])
        print("   slope", r["slope"])
        print("   section", {k: v for k, v in section.items() if k not in ("dist_ft", "z_ft", "start_utm", "end_utm")})
        print("   envelope", r["envelope_sqft"], "sf; fits:",
              {k: (None if v is None else {kk: vv for kk, vv in v.items() if kk != 'poly_lf'}) for k, v in r["fits"].items()})
        print("   drip area", r["drip"]["area_sqft"], "sf; max BR", max_br, "; zone A edge", za, "; zone A % of lot", zone_a_pct)
    save("terrain.json", out)


if __name__ == "__main__":
    main()
