"""Largest home + private dock for 11 Bayview Cir and 5001 Arrowhead Pt (LOTSET=two, 10 Nov 2026).

A desk estimate from public rules, lidar and the TWDB lake survey. It is not a design, a survey or a permit
decision. Writes data/bigbuild.json and, in figures/:
  bigbuild_<lot>.png       true-scale plan: lot, building envelope, largest house, drip field, dock, channel width
  dockxs_<lot>_true.png    section across the water at the dock, true 1:1
  dockxs_<lot>_ve.png      the same section, vertically exaggerated (printed beside the 1:1 version)

Rules applied (sources in the PDF):
  * Navarro County Lakeshore Zoning, Table B, SF-3 (district still to confirm): front 35, rear (lake) 15, side
    10 ft; building coverage <= 40% of the lot; main + accessory buildings <= 50% of the lot area behind the line
    joining the side-line midpoints; 2 1/2 storeys; no building below 320 ft. The house pad stays on ground
    >= 322 ft (the envelope from 08_terrain.py) and out of FEMA Zone A.
  * 11 Bayview Cir: White Rock HOA sewer plant, so no drip field. HOA minimum 2,500 sf heated (listing).
  * 5001 Arrowhead Pt, Rustling Oaks Estates Ph II Declaration (Vol 1224 p 638, 1991): buildings >= 5 ft from
    side and rear lines; 30-ft easement along the street for ditches, drains and utilities (kept free of drip
    lines here); >= 1,600 sf heated on a waterfront lot. Septic: aerobic unit + subsurface drip,
    Ra 0.10 gal/sf/day (clay), drip >= 5 ft from lot lines and >= 50 ft from the 315-ft line (75 ft also
    tested), off the house (+5 ft), driveway and tank pad. Flow: TCEQ Table III with water-saving fixtures.
  * TRWD Residential Improvement Permit Guidelines (Attachment I, 2026): dock area 8 sf per ft of shoreline up
    to 150 ft (max 1,200 sf), +4 sf per ft from 151-250 ft; >= 5 ft from side lines, 20 ft if over 1,200 sf.
    TRWD Richland-Chambers guidelines (2001): no structure over one third of a channel's width. TRWD General
    Ordinance: a residential cove keeps a navigable passage >= 20 ft wide.
"""
import importlib
import json
import math

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

from common import LOTS, LOTSET, load, save
from figlib import HALO, PAL, dem_local, rot, scale_bar
from figlib import save as fsave

MB = importlib.import_module("14_maxbuild")     # shared helpers: poly, road_line, rear_half, pool_poly, q_gpd
F9 = MB.F9
T = load("terrain.json")
BA = load("bathymetry.json")

POOL, FLOWAGE = 315.0, 320.0
LAKE_NOW, LAKE_NOW_DATE = 312.16, "9 Nov 2026"   # TWDB daily level, read 10 Nov 2026
LOW22 = 310.57                                   # Dec 2022-Jan 2023 mean, the last deep low
NOW_EDGE = 312.9                                 # water's edge in the 2022 lidar (water surface 312.57 ft)
LEGAL_SF = {"bayview": 28314, "arrowhead": 21780}
RULES = {
    "bayview": dict(septic=False, front_ease=0.0, min_heated=2500, side_dock=5.0),
    "arrowhead": dict(septic=True, front_ease=30.0, min_heated=1600, side_dock=5.0),
}
GARAGE_SF = 960.0          # 3-car garage, 40 x 24 ft
PORCH_SF = 360.0           # covered porches counted in coverage
BEDROOMS = 6
RA = 0.10
# Existing neighbour boathouses read off the May 2025 Esri imagery (local ft, approximate centres).
NEIGHBOUR_BH = {"bayview": [(-71.0, -140.0, "neighbour boathouse"), (151.0, -284.0, "neighbour boathouse")],
                "arrowhead": []}


# --------------------------------------------------------------------------- shared geometry
def zone_a(key):
    rings = [Polygon(r).buffer(0) for r in T[key].get("zoneA_lf") or [] if len(r) > 3]
    return unary_union(rings) if rings else Polygon()


def frontage(key):
    """Lake-edge end points of the lot (in ring order), the chord direction and the outward normal."""
    t = T[key]
    lake = [e for e in t["edges"] if e["kind"] == "lake"]
    a = np.array(lake[0]["seg_lf"][0]); b = np.array(lake[-1]["seg_lf"][1])
    d = (b - a) / np.linalg.norm(b - a)
    n = np.array([-d[1], d[0]])
    c = np.array(MB.poly(t["ring_lf"]).centroid.coords[0])
    if np.dot((a + b) / 2 + n - c, n) < np.dot((a + b) / 2 - c, n):
        n = -n
    return a, b, d, n


class Grid:
    """Lidar ground (2022) and TWDB 2018 lake bottom on one 1-ft local grid."""

    def __init__(self, key, half=600.0):
        self.xs, self.ys, self.Z = dem_local(key, half, 1.0)
        self.x0, self.y0 = self.xs[0], self.ys[0]
        # lake bottom: TWDB 1-ft contours (their vertices) + soundings, linear interpolation
        a, b, _, _ = frontage(key)
        cx, cy = (a + b) / 2
        pts, val = [], []
        for ln in BA[key]["lines"]:
            xy = np.array(ln["xy"])
            m = (np.abs(xy[:, 0] - cx) < 520) & (np.abs(xy[:, 1] - cy) < 520)
            if m.any():
                pts.append(xy[m]); val.append(np.full(m.sum(), ln["z"]))
        snd = np.array(BA[key]["soundings_sample"])
        m = (np.abs(snd[:, 0] - cx) < 520) & (np.abs(snd[:, 1] - cy) < 520)
        pts.append(snd[m, :2]); val.append(snd[m, 2])
        P = np.vstack(pts); V = np.concatenate(val)
        self.bx = np.arange(cx - 450, cx + 451, 2.0); self.by = np.arange(cy - 450, cy + 451, 2.0)
        BX, BY = np.meshgrid(self.bx, self.by)
        self.Bot = griddata(P, V, (BX, BY), method="linear")
        self.snd = snd[m]
        self.tree = cKDTree(self.snd[:, :2]) if len(self.snd) else None

    def z(self, x, y):
        j = int(round(x - self.x0)); i = int(round(y - self.y0))
        if 0 <= i < len(self.ys) and 0 <= j < len(self.xs):
            return float(self.Z[i, j])
        return float("nan")

    def bottom(self, x, y):
        j = int(round((x - self.bx[0]) / 2.0)); i = int(round((y - self.by[0]) / 2.0))
        if 0 <= i < len(self.by) and 0 <= j < len(self.bx):
            return float(self.Bot[i, j])
        return float("nan")

    def nearest_sounding_ft(self, x, y):
        if self.tree is None:
            return None
        return float(self.tree.query([x, y])[0])


def ray(G, p, n, level, start=-40.0, stop=700.0, step=0.5):
    """Distance along n (from point p) where the water at `level` starts and ends (None if not found)."""
    entry = None
    for s in np.arange(start, stop, step):
        z = G.z(p[0] + n[0] * s, p[1] + n[1] * s)
        if math.isnan(z):
            return entry, None
        if entry is None and z < level:
            entry = s
        elif entry is not None and z >= level:
            # ignore single-cell lidar noise: need 2 ft of dry ground
            z2 = G.z(p[0] + n[0] * (s + 2), p[1] + n[1] * (s + 2))
            if z2 >= level:
                return entry, s
    return entry, None


def obstacles(key):
    """Neighbours' boathouses as 32 x 32 ft squares (CAD lists 977 and 1,024 sf boathouses next to Bayview)."""
    return [box(x - 16, y - 16, x + 16, y + 16) for x, y, _ in NEIGHBOUR_BH.get(key, [])]


def free_until(p, n, entry, exit_, obs):
    """First distance after `entry` where the ray meets a neighbour's boathouse, else the far shore."""
    if entry is None or exit_ is None or not obs:
        return exit_
    ln = LineString([tuple(p + n * entry), tuple(p + n * exit_)])
    best = exit_
    for o in obs:
        hit = ln.intersection(o)
        if not hit.is_empty:
            dmin = min(Point(tuple(p)).distance(Point(c)) for g in getattr(hit, "geoms", [hit]) for c in g.coords)
            best = min(best, dmin)
    return best


# --------------------------------------------------------------------------- dock
def dock_plan(key, G):
    t = T[key]
    lf = t["frontage_lake_ft"]
    cap_formula = 8 * min(lf, 150) + 4 * max(0, min(lf, 250) - 150)
    cap = min(cap_formula, 1200.0)          # above 1,200 sf TRWD wants 20 ft from the side lines
    a, b, d, n = frontage(key)
    chord = float(np.linalg.norm(b - a))
    side = RULES[key]["side_dock"]
    ss = np.arange(side, chord - side + 0.01, 1.0)
    obs = obstacles(key)
    lot = MB.poly(t["ring_lf"])
    prof = []
    for s in ss:
        p = a + d * s
        e15, x15 = ray(G, p, n, POOL)
        enow, xnow = ray(G, p, n, NOW_EDGE)
        lotline = next((float(u) for u in np.arange(-40.0, 200.0, 0.5)
                        if u > -40 and lot.contains(Point(*(p + n * (u - 0.5)))) and not lot.contains(Point(*(p + n * u)))),
                       None)
        prof.append(dict(s=float(s), e=e15, x=x15, enow=enow, xnow=xnow, lotline=lotline,
                         free=free_until(p, n, e15, x15, obs)))
    ok = [q for q in prof if q["e"] is not None and q["x"] is not None]
    widths = [q["x"] - q["e"] for q in ok]

    def lift_depth(s0, L, emax, w0, P):
        """Median lake-bottom elevation under the outer half of the boathouse (where a lift sits), and
        whether it rests on survey data: nearest 2018 sounding <= 60 ft and the bottom below the 2022
        lidar water surface wherever the lidar shows water."""
        c0 = a + d * s0 + n * (emax + w0)
        bots, near, bad = [], [], 0
        for u in np.linspace(0.15, 0.85, 5):
            for v in (0.55, 0.75, 0.95):
                xy = c0 + d * (L * u) + n * (P * v)
                zb = G.bottom(*xy)
                if math.isnan(zb):
                    continue
                if G.z(*xy) < NOW_EDGE and zb >= 312.57:
                    bad += 1
                bots.append(zb); near.append(G.nearest_sounding_ft(*xy) or 1e9)
        if not bots:
            return None, False, None
        nr = float(np.median(near))
        return float(np.median(bots)), (nr <= 60 and bad == 0), nr

    # every placement: along-shore length L, start s0, walkway w0 beyond the water line, depth out P.
    # For every s in the span: outer edge (emax + w0 + P - e) <= W/3 (one-third rule, W = width at 315 ft)
    # and free - (emax + w0 + P) >= 20 (navigable passage to the far shore or a neighbour's boathouse).
    cands = []
    for L in np.arange(16.0, chord - 2 * side + 0.01, 1.0):
        for i0 in range(0, len(prof)):
            span = prof[i0:i0 + int(L) + 1]
            if len(span) < int(L) + 1 or any(q["e"] is None or q["x"] is None for q in span):
                continue
            emax = max(q["e"] for q in span)
            lim = min(min((q["x"] - q["e"]) / 3.0 - (emax - q["e"]), q["free"] - emax - 20.0) for q in span)
            if lim < 10:
                continue
            P = min(lim, cap / L, 60.0)
            if P < 10:
                continue
            for w0 in np.arange(0.0, 61.0, 5.0):
                if w0 + P > lim + 1e-6:
                    break
                passage = min(q["free"] - (emax + w0 + P) for q in span)
                cands.append(dict(L=float(L), P=float(P), area=float(L * P), s0=float(span[0]["s"]), emax=float(emax),
                                  w0=float(w0), lim=float(lim), passage=float(passage)))
    out = dict(frontage_ft=round(lf, 1), cap_formula_sf=round(cap_formula), cap_sf=round(cap), chord_ft=round(chord, 1),
               width315_min=round(min(widths), 0) if widths else None,
               width315_med=round(float(np.median(widths)), 0) if widths else None,
               width315_max=round(max(widths), 0) if widths else None,
               profile=prof, a=a.tolist(), b=b.tolist(), d=d.tolist(), n=n.tolist())
    if not cands:
        return out
    amax = max(c["area"] for c in cands)
    top = [c for c in cands if c["area"] >= amax - 1.0]
    for c in top:
        c["bottom"], c["reliable"], c["near"] = lift_depth(c["s0"], c["L"], c["emax"], c["w0"], c["P"])
    rel = [c for c in top if c["reliable"] and c["bottom"] is not None]
    deep = None
    if rel:
        # shortest structure that gives >= 6 ft over the lift at full pool (>= 3 ft at today's level), else deepest
        good = [c for c in rel if POOL - c["bottom"] >= 6.0]
        best = (min(good, key=lambda c: (c["w0"] + c["P"], -c["passage"])) if good
                else min(rel, key=lambda c: (c["bottom"], c["w0"] + c["P"])))
        dp = min(rel, key=lambda c: (c["bottom"], c["w0"] + c["P"]))
        deep = dict(reach_ft=round(dp["w0"] + dp["P"]), w0=dp["w0"], L=dp["L"], P=round(dp["P"], 1),
                    depth_pool=round(POOL - dp["bottom"], 1), depth_now=round(LAKE_NOW - dp["bottom"], 1),
                    depth_low22=round(LOW22 - dp["bottom"], 1))
    else:
        # no survey data under any placement: keep the boathouse at the shore, widest passage
        best = max([c for c in top if c["w0"] == 0] or top, key=lambda c: c["passage"])
    s0, L, P, em, w0 = best["s0"], best["L"], best["P"], best["emax"], best["w0"]
    c0 = a + d * s0 + n * (em + w0)
    rect = [c0, c0 + d * L, c0 + d * L + n * P, c0 + n * P, c0]
    mid = s0 + L / 2
    q = min(prof, key=lambda r: abs(r["s"] - mid))
    bot = best["bottom"]
    out.update({k: (round(v, 1) if isinstance(v, float) else v) for k, v in best.items() if k != "bottom"})
    gaps = [r["e"] - r["lotline"] for r in prof if r["e"] is not None and r["lotline"] is not None]
    out.update(rect=[list(map(float, r)) for r in rect], axis_s=float(mid), reach_ft=round(w0 + P, 0),
               width_at_dock=round(q["x"] - q["e"], 0), passage_left=round(best["passage"], 0),
               lotline_to_water=None if q["lotline"] is None else round(q["e"] - q["lotline"], 1),
               lotline_to_water_range=[round(min(gaps), 0), round(max(gaps), 0)] if gaps else None,
               deepest=deep, depth_reliable=bool(best["reliable"]),
               bottom_ft=None if bot is None else round(bot, 1),
               depth_pool=None if bot is None else round(POOL - bot, 1),
               depth_now=None if bot is None else round(LAKE_NOW - bot, 1),
               depth_low22=None if bot is None else round(LOW22 - bot, 1),
               nearest_sounding_ft=None if best["near"] is None else round(best["near"]))
    return out


# --------------------------------------------------------------------------- largest house
def solve_house(key, lake_sb=50.0):
    t = T[key]; R = RULES[key]
    lot = MB.poly(t["ring_lf"])
    za = zone_a(key)
    env = unary_union([MB.poly(p) for p in t["envelope_lf"]]).difference(za).buffer(0)
    rd = MB.road_line(t)
    ease = rd.buffer(R["front_ease"], cap_style=2).intersection(lot) if R["front_ease"] else Polygon()
    legal = LEGAL_SF[key]
    cov_max = 0.40 * legal
    rh = MB.rear_half(t, lot)
    pool = MB.pool_poly(t)
    drip_base = None
    if R["septic"]:
        drip_base = (lot.buffer(-5.0).difference(pool.buffer(lake_sb)).difference(ease.buffer(0.1))
                     .difference(za).buffer(0))
    (ax_, ay_), (bx_, by_) = t["section_lf"]
    spine = math.degrees(math.atan2(by_ - ay_, bx_ - ax_))
    cands = []
    ex0, ey0, ex1, ey1 = env.bounds
    penv = prep(env)
    for ang in (spine, spine + 90, spine + 8, spine - 8, spine + 82, spine + 98):
        for W in range(44, 140, 4):
            for D in range(36, 120, 4):
                if W * D > cov_max or W * D < 1800:
                    continue
                r0 = affinity.rotate(box(-W / 2, -D / 2, W / 2, D / 2), ang, origin=(0, 0))
                for cx in np.arange(ex0, ex1 + 0.1, 5.0):
                    for cy in np.arange(ey0, ey1 + 0.1, 5.0):
                        rr = affinity.translate(r0, cx, cy)
                        if penv.contains(rr):
                            cands.append((W * D, ang, W, D, rr))
    cands.sort(key=lambda c: -c[0])
    best = None
    for k_, (area, ang, W, D, rr) in enumerate(cands):
        if rh is not None and rr.intersection(rh).area > 0.5 * rh.area:
            continue
        living = area - GARAGE_SF - PORCH_SF
        heated2 = 2 * living
        rpt = rd.interpolate(rd.project(rr.centroid))
        near = rr.exterior.interpolate(rr.exterior.project(rpt))
        drive = LineString([near, rpt]).buffer(8.0, cap_style=2)
        apron = near.buffer(17.0, cap_style=3)
        side_pt = rr.exterior.interpolate(rr.exterior.project(rpt) + 40.0)
        tank = side_pt.buffer(8.0, cap_style=3)
        res = dict(footprint_sf=round(area), angle=round(ang, 1), W=W, D=D, living_fp_sf=round(living),
                   heated_2st_sf=round(heated2), heated_25st_sf=round(heated2 + 0.5 * living),
                   coverage_pct=round(100 * area / legal, 1), cov_max_sf=round(cov_max),
                   house=list(rr.exterior.coords), drive=list(drive.exterior.coords),
                   apron=list(apron.exterior.coords),
                   rear_half_sf=None if rh is None else round(rh.area),
                   rear_half_used_sf=None if rh is None else round(rr.intersection(rh).area))
        if not R["septic"]:
            res.update(q_gpd=MB.q_gpd(heated2), limit="building envelope and the 40% coverage cap")
            best = res
            break
        q = MB.q_gpd(heated2)
        need = q / RA
        blocked = unary_union([rr.buffer(5.0, join_style=2), drive.buffer(5.0), apron.buffer(5.0), tank.buffer(5.0)])
        drip = drip_base.difference(blocked).buffer(0)
        pieces = [g for g in (drip.geoms if isinstance(drip, MultiPolygon) else [drip]) if g.area >= 150]
        avail = sum(g.area for g in pieces)
        if avail >= need:
            res.update(q_gpd=q, drip_need_sf=round(need), drip_avail_sf=round(avail),
                       tank=list(tank.exterior.coords), drip=[list(g.exterior.coords) for g in pieces],
                       limit="drip field")
            best = res
            break
        if k_ > 6000:
            break
    info = dict(env_sf=round(env.area), lot_gis_sf=round(lot.area), legal_sf=legal, zoneA_sf=round(za.intersection(lot).area),
                ease_sf=round(ease.area), drip_base_sf=None if drip_base is None else round(drip_base.area),
                candidates=len(cands))
    return best, info


# --------------------------------------------------------------------------- figures
def plan_figure(key, house, dock, G):
    t = T[key]
    th = F9.theta_of(key)
    u0, u1, v0, v1 = F9.frame_limits(key, th, (20, 40, 28, 28))
    rr_ = rot(np.array(dock["rect"]), th) if dock.get("rect") else None
    pr = [p for p in dock["profile"] if p["x"] is not None]
    if pr:   # include the far shore in the frame
        a, d, n = np.array(dock["a"]), np.array(dock["d"]), np.array(dock["n"])
        far = np.array([a + d * p["s"] + n * (p["x"] + 12) for p in pr])
        q = rot(far, th)
        u0, u1 = min(u0, q[:, 0].min()), max(u1, q[:, 0].max())
        v0, v1 = min(v0, q[:, 1].min()), max(v1, q[:, 1].max())
    u0, u1, v0, v1 = F9.fit_aspect(u0, u1, v0, v1, 1.25)
    us, vs, rgb, Z = F9.grids_rot(key, (u0, u1), (v0, v1), 1.0, th, zoom=19, smooth=1.5)
    w, h = u1 - u0, v1 - v0
    fig = plt.figure(figsize=(4.6, 4.6 * h / w))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(rgb * 0.45 + 0.55, extent=[us[0], us[-1], vs[0], vs[-1]], origin="lower", zorder=0)
    ax.contourf(us, vs, (Z < 315.0).astype(float), levels=[0.5, 1.5], colors=["#93c5fd"], alpha=0.55, zorder=1)
    ax.contourf(us, vs, (Z < NOW_EDGE).astype(float), levels=[0.5, 1.5], colors=["#3b82f6"], alpha=0.35, zorder=1)
    ax.contour(us, vs, Z, levels=[POOL], colors=[PAL["sky"]], linewidths=0.9, linestyles="--", zorder=3)
    ax.contour(us, vs, Z, levels=[FLOWAGE], colors=[PAL["amber"]], linewidths=0.9, linestyles="--", zorder=3)
    for p, xy in F9.neighbour_rings(key):
        q = rot(xy, th)
        ax.plot(q[:, 0], q[:, 1], color="#64748b", lw=0.5, zorder=2)
    ring = rot(t["ring_lf"], th)
    ax.fill(ring[:, 0], ring[:, 1], facecolor=(1, 0.97, 0.93, 0.55), edgecolor=PAL["coral"], lw=1.6, zorder=4)
    za = zone_a(key).intersection(MB.poly(t["ring_lf"]))
    for g in (za.geoms if hasattr(za, "geoms") else [za]):
        if g.area > 20:
            q = rot(np.array(g.exterior.coords), th)
            ax.fill(q[:, 0], q[:, 1], facecolor="none", edgecolor="#7c3aed", hatch="xxxx", lw=0.3, zorder=5)
    for pp in t["envelope_lf"]:
        q = rot(pp, th)
        ax.plot(q[:, 0], q[:, 1], color=PAL["green"], lw=0.9, ls="--", zorder=5)
    if RULES[key]["front_ease"]:
        lot = MB.poly(t["ring_lf"])
        ease = MB.road_line(t).buffer(RULES[key]["front_ease"], cap_style=2).intersection(lot)
        for g in (ease.geoms if hasattr(ease, "geoms") else [ease]):
            if g.area > 10:
                q = rot(np.array(g.exterior.coords), th)
                ax.fill(q[:, 0], q[:, 1], facecolor="none", edgecolor="#64748b", hatch="////", lw=0.3, zorder=5)
    if house:
        for pp in house.get("drip", []):
            q = rot(np.array(pp), th)
            ax.fill(q[:, 0], q[:, 1], facecolor=(0.05, 0.65, 0.91, 0.22), edgecolor=PAL["sky"], lw=0.6,
                    hatch="....", zorder=6)
        for nm in ("drive", "apron"):
            q = rot(np.array(house[nm]), th)
            ax.fill(q[:, 0], q[:, 1], facecolor="#94a3b8", edgecolor="none", alpha=0.7, zorder=6)
        if house.get("tank"):
            q = rot(np.array(house["tank"]), th)
            ax.fill(q[:, 0], q[:, 1], facecolor="#0e7490", edgecolor="white", lw=0.5, zorder=7)
        q = rot(np.array(house["house"]), th)
        ax.fill(q[:, 0], q[:, 1], facecolor=PAL["gold"], edgecolor="#854d0e", lw=1.1, alpha=0.95, zorder=8)
        ax.text(q[:-1, 0].mean(), q[:-1, 1].mean(),
                f"LARGEST HOUSE\n{house['W']}×{house['D']} ft = {house['footprint_sf']:,} sf\n"
                f"≈{house['heated_2st_sf']:,} sf heated\n(2 storeys) + 3-car garage",
                ha="center", va="center", fontsize=4.5, fontweight="bold", color="#422006", zorder=9)
        if house.get("drip"):
            big = max(house["drip"], key=lambda a_: Polygon(a_).area)
            q = rot(np.array(big), th)
            ax.text(q[:, 0].mean(), q[:, 1].mean(), f"drip field\nneeds {house['drip_need_sf']:,} sf\n"
                    f"room {house['drip_avail_sf']:,} sf", ha="center", va="center", fontsize=4.1,
                    color="#075985", fontweight="bold", zorder=9, path_effects=HALO)
    for x, y, lab in NEIGHBOUR_BH.get(key, []):
        q = rot(np.array([[x, y]]), th)[0]
        if not (u0 + 10 < q[0] < u1 - 10 and v0 + 10 < q[1] < v1 - 10):
            continue
        ax.plot(q[0], q[1], marker="s", ms=9, mfc="#475569", mec="white", mew=0.6, zorder=8)
        ax.text(q[0], q[1] - 9, lab, fontsize=3.9, ha="center", va="top", color="#1e293b", path_effects=HALO, zorder=9)
    if dock.get("rect"):
        q = rr_
        ax.fill(q[:, 0], q[:, 1], facecolor="#a16207", edgecolor="#422006", lw=0.8, alpha=0.9, zorder=8)
        a, d, n = np.array(dock["a"]), np.array(dock["d"]), np.array(dock["n"])
        s = dock["axis_s"]
        base = a + d * s
        wk = rot(np.array([base - n * 12, base + n * (dock["emax"] + dock.get("w0", 0.0))]), th)
        ax.plot(wk[:, 0], wk[:, 1], color="#a16207", lw=2.0, zorder=7)
        pp = [p for p in dock["profile"] if abs(p["s"] - s) < 0.6 and p["x"] is not None]
        if pp:
            p = pp[0]
            seg = rot(np.array([base + n * p["e"], base + n * p["x"]]), th)
            ax.annotate("", xy=seg[1], xytext=seg[0], arrowprops=dict(arrowstyle="<->", color="#1e3a8a", lw=0.7),
                        zorder=10)
            m = seg.mean(axis=0)
            ax.text(m[0], m[1], f"{p['x'] - p['e']:.0f} ft\nacross at 315′", fontsize=4.2, color="#1e3a8a",
                    ha="center", va="center", fontweight="bold", path_effects=HALO, zorder=11)
        c = q[:-1].mean(axis=0)
        ax.text(c[0], c[1], f"DOCK\n{dock['L']:.0f}×{dock['P']:.0f} ft\n≈{dock['area']:,.0f} sf", fontsize=4.2,
                ha="center", va="center", color="white", fontweight="bold", zorder=10)
        if dock.get("w0"):
            # label beside the walkway, clear of the boathouse: shifted along the shore past the dock's end
            m = rot(np.array([base + n * (dock["emax"] + dock["w0"] / 2) - d * (dock["L"] / 2 + 14)]), th)[0]
            ax.text(m[0], m[1], f"walkway\n{dock['w0']:.0f} ft", fontsize=3.9, ha="center", va="center",
                    color="#78350f", fontweight="bold", path_effects=HALO, zorder=10)
    ax.set_xlim(u0, u1); ax.set_ylim(v0, v1); ax.set_aspect("equal"); ax.axis("off")
    ncx, ncy = u1 - 0.07 * w, v1 - 0.12 * h
    F9.north_rot(ax, ncx, ncy, 0.07 * h, th)
    scale_bar(ax, u0 + 0.04 * w, v0 + 0.03 * h, 50, height=0.012 * h, label="50 ft")
    leg = [mpatches.Patch(facecolor="#fff7ed", edgecolor=PAL["coral"], label="Lot (CAD GIS)"),
           plt.Line2D([], [], color=PAL["green"], ls="--", label="Set-backs 35/15/10 ft, ground ≥322 ft"),
           mpatches.Patch(facecolor="none", edgecolor="#7c3aed", hatch="xxxx", label="FEMA Zone A (kept clear)"),
           mpatches.Patch(facecolor=PAL["gold"], edgecolor="#854d0e", label="Largest rectangular house")]
    if RULES[key]["septic"]:
        leg += [mpatches.Patch(facecolor="none", edgecolor="#64748b", hatch="////", label="30-ft street easement (CC&Rs)"),
                mpatches.Patch(facecolor=(0.05, 0.65, 0.91, 0.25), edgecolor=PAL["sky"], hatch="....",
                               label="Drip field (≥5 ft lines, ≥50 ft pool)"),
                mpatches.Patch(facecolor="#0e7490", label="Aerobic tank pad")]
    leg += [mpatches.Patch(facecolor="#a16207", label="Dock / boathouse (TRWD limits)"),
            mpatches.Patch(facecolor="#93c5fd", label="Water at 315 ft (full pool)"),
            mpatches.Patch(facecolor="#60a5fa", label="Water now (≈312.2–312.6 ft)"),
            plt.Line2D([], [], color=PAL["amber"], ls="--", label="320 ft TRWD flowage")]
    if NEIGHBOUR_BH.get(key):
        leg.append(plt.Line2D([], [], marker="s", ms=5, color="none", mfc="#475569", label="Neighbour boathouse (aerial)"))
    lg = ax.legend(handles=leg, loc="lower right", fontsize=4.1, framealpha=0.92, borderpad=0.35,
                   labelspacing=0.22, handlelength=1.4)
    lg.set_zorder(50)
    return fsave(fig, f"bigbuild_{key}.png", dpi=330)


def section_data(key, dock, G):
    """Ground (2022 lidar) and lake bottom (TWDB 2018) along the dock axis, from 70 ft inland to past the far
    shore. Where the lidar shows water but the TWDB surface is not below it (unsurveyed water near the bank),
    the bottom is unknown: it is drawn 0.5 ft under the 2022 water surface and flagged."""
    a, d, n = np.array(dock["a"]), np.array(dock["d"]), np.array(dock["n"])
    s = dock["axis_s"]
    p0 = a + d * s
    pp = min(dock["profile"], key=lambda p: abs(p["s"] - s))
    far = (pp["x"] or 150) + 25
    dist = np.arange(-70.0, far, 1.0)
    zg = np.array([G.z(*(p0 + n * u)) for u in dist])
    zb = np.array([G.bottom(*(p0 + n * u)) for u in dist])
    wet = zg < NOW_EDGE
    unknown = wet & (np.isnan(zb) | (zb >= 312.3))
    known = ~unknown & wet
    floor = min(float(np.nanmin(zb[known])) if known.any() else 306.0, 306.0) if unknown.any() else None
    # unsurveyed water: drawn as a hatched band from the deepest nearby bottom up to the 2022 water surface
    bed = np.where(wet, np.where(unknown, floor if floor else 312.0, zb), zg)
    # x = 0 at the water's edge at full pool (315 ft) on this line
    return dist - pp["e"], bed, unknown, pp


def _draw_section(ax, dist, bed, unknown, dock, labels=True, fs=4.0):
    ax.fill_between(dist, 290, bed, color="#d6b98c", lw=0, zorder=2)
    ax.plot(dist, np.where(unknown, np.nan, bed), color="#5b3a1a", lw=0.8, zorder=3)
    for lv, col, a_ in ((POOL, "#bae6fd", 0.75), (LAKE_NOW, "#3b82f6", 0.45)):
        m = bed < lv
        ax.fill_between(dist, np.where(m, bed, lv), lv, where=m, color=col, alpha=a_, lw=0, zorder=1)
    if unknown.any():
        ax.fill_between(dist, np.where(unknown, bed, np.nan), 312.0, where=unknown, facecolor="none",
                        edgecolor="#64748b", hatch="////", lw=0, zorder=3)
    levels = ((FLOWAGE, PAL["amber"], "320 TRWD flowage"), (POOL, PAL["sky"], "315 full pool"),
              (LAKE_NOW, PAL["lake"], f"{LAKE_NOW} lake now ({LAKE_NOW_DATE})"),
              (LOW22, "#0f172a", f"{LOW22:.1f} Dec-2022 low"))
    for lv, col, lab in levels:
        ax.axhline(lv, color=col, lw=0.55, ls="--", zorder=4)
        if labels:
            ax.text(labels - 1, lv + 0.12, lab, fontsize=fs, color=col, ha="right", va="bottom", zorder=6,
                    path_effects=HALO, clip_on=True)
    off = dock["profile_e"]                       # plot x = distance from the 315-ft water's edge
    x0 = dock["emax"] + dock.get("w0", 0.0) - off; x1 = x0 + dock["P"]
    deck = FLOWAGE + 1.5
    ax.plot([-15, x0], [deck, deck], color="#a16207", lw=0.9, zorder=6)
    ax.plot([x0, x1], [deck, deck], color="#a16207", lw=2.4, zorder=6, solid_capstyle="butt")
    for xx in np.linspace(x0, x1, 4):
        zz = float(np.interp(xx, dist, bed))
        ax.plot([xx, xx], [zz, deck], color="#78350f", lw=0.45, zorder=5)
    return x0, x1, deck


def section_figures(key, dock, G):
    """True 1:1 figure (whole section + near-shore detail) and a vertically exaggerated figure of the same
    section; the PDF prints them side by side."""
    dist, bed, unknown, pp = section_data(key, dock, G)
    dock["profile_e"] = pp["e"]
    out = []
    # ---- true scale: whole section strip (top) + 90-ft detail at the bank (bottom), both 1:1
    W_IN, H_IN = 3.85, 2.0
    fig = plt.figure(figsize=(W_IN, H_IN))
    L = dist[-1] - dist[0]
    wa = 0.86 * W_IN
    lo = float(np.nanmin(bed)) - 1.0
    hA = (30.0 / L) * wa                                   # 30 ft of height at 1:1
    axA = fig.add_axes([0.11, 0.93 - hA / H_IN, 0.86, hA / H_IN])
    _draw_section(axA, dist, bed, unknown, dock, labels=False)
    axA.set_xlim(dist[0], dist[-1]); axA.set_ylim(lo, lo + 30.0); axA.set_aspect("equal", adjustable="box")
    axA.set_title("TRUE SCALE 1:1 — whole section across the water at the dock", fontsize=5.4, loc="left",
                  color=PAL["navy"], fontweight="bold", pad=1.5)
    axA.tick_params(labelsize=4.0, length=1.2)
    axA.set_yticks([int(lo) + 5, int(lo) + 25])
    span = 90.0
    x0d = -25.0
    top_b = 0.93 - hA / H_IN - 0.13                        # room for the lower panel's title
    hb = top_b - 0.10
    axB = fig.add_axes([0.11, 0.10, 0.86, hb])
    _draw_section(axB, dist, bed, unknown, dock, labels=x0d + span, fs=3.9)
    axB.set_xlim(x0d, x0d + span)
    axB.set_ylim(lo, lo + span * (hb * H_IN) / wa)
    axB.set_aspect("equal", adjustable="box", anchor="SW")
    axB.set_title(f"TRUE SCALE 1:1 — first {span:.0f} ft at the bank (real angles)", fontsize=5.4, loc="left",
                  color=PAL["navy"], fontweight="bold", pad=1.5)
    axB.tick_params(labelsize=4.0, length=1.2)
    axB.set_xlabel("ft from the water's edge at full pool (315 ft); + = toward the far shore", fontsize=4.2,
                   labelpad=1)
    out.append(fsave(fig, f"dockxs_{key}_true.png", dpi=330))
    # ---- vertical exaggeration
    fig = plt.figure(figsize=(W_IN, H_IN))
    ax = fig.add_axes([0.10, 0.15, 0.88, 0.75])
    x0, x1, deck = _draw_section(ax, dist, bed, unknown, dock, labels=dist[-1], fs=4.0)
    ax.text((x0 + x1) / 2, deck + 0.35, f"boathouse {dock['P']:.0f} ft deep, lower deck ≥321.5 ft", fontsize=3.9,
            ha="center", va="bottom", color="#78350f", zorder=7, path_effects=HALO)
    if unknown.any():
        k = np.where(unknown)[0]
        run = k[: (np.argmax(np.diff(k) > 1) + 1) if (np.diff(k) > 1).any() else len(k)]   # nearest run
        if len(run) >= 25:
            ax.text(dist[run].mean(), (312.0 + float(bed[run].min())) / 2,
                    "depth not surveyed\n(TWDB 2018 did not sound here)", fontsize=3.9, color="#334155",
                    ha="center", va="center", zorder=7, path_effects=HALO)
    ax.set_xlim(dist[0], dist[-1])
    hi = max(float(np.nanmax(bed[dist < 0])) if (dist < 0).any() else 325.0, deck) + 2.0
    ax.set_ylim(lo, hi)
    wc, hc = 0.88 * W_IN, 0.75 * H_IN
    ve = ((dist[-1] - dist[0]) / wc) / ((hi - lo) / hc)
    ax.set_title(f"VERTICAL EXAGGERATION ×{ve:.0f} — same section", fontsize=5.4, loc="left", color=PAL["coral"],
                 fontweight="bold", pad=1.5)
    ax.tick_params(labelsize=4.2, length=1.5)
    ax.set_xlabel("ft from the water's edge at full pool (315 ft); + = toward the far shore", fontsize=4.2,
                  labelpad=1)
    ax.set_ylabel("ft msl", fontsize=4.2, labelpad=1)
    out.append(fsave(fig, f"dockxs_{key}_ve.png", dpi=330))
    dock["ve_drawn"] = round(ve, 1)
    return out


def main():
    assert LOTSET == "two", "run with LOTSET=two (the default)"
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"     # all | dock (keep saved houses) | fig (redraw only)
    res = load("bigbuild.json", {}) if mode in ("fig", "dock") else {}
    for key in LOTS:
        G = Grid(key)
        if mode == "all":
            h50, info = solve_house(key, 50.0)
            h75 = solve_house(key, 75.0)[0] if RULES[key]["septic"] else None
            res[key] = dict(lake50=h50, lake75=None if h75 is None else {k: v for k, v in h75.items() if k not in
                                                                         ("house", "drive", "apron", "tank", "drip")},
                            info=info)
        if mode in ("all", "dock"):
            res[key]["dock"] = dock_plan(key, G)
        r = res[key]
        slim = {k: v for k, v in (r["lake50"] or {}).items() if k not in ("house", "drive", "apron", "tank", "drip")}
        print(key, r["info"], "\n   house:", slim, "\n   75 ft:", r["lake75"],
              "\n   dock:", {k: v for k, v in r["dock"].items() if k not in ("profile", "rect", "a", "b", "d", "n")})
        print("  ", plan_figure(key, r["lake50"], r["dock"], G))
        if r["dock"].get("rect"):
            print("  ", section_figures(key, r["dock"], G))
    save("bigbuild.json", res)


if __name__ == "__main__":
    main()
