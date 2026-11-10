"""Largest house + private dock each Shores lot can take (desk estimate, not a design).

Rules applied (sources in the report):
  * Navarro County Lakeshore Zoning, Table B, SF-3: front 35 ft, rear (lake) 15 ft, side 10 ft,
    max building coverage 40 % of the lot, main + accessory buildings <= 50 % of the lot area
    behind the line joining the side-line midpoints, 2 1/2 storeys; no building below 320 ft.
  * P.O.A. of The Shores plat/ACC: first 20 ft beside the road is a POA easement (no planting,
    drainage) -> kept free of house and drip lines here; garage doors face a side or rear line
    (side-entry apron modelled); 2- to 5-car garage.
  * House pad kept on ground >= 322 ft (2 ft above the TRWD 320-ft flood-flowage line).
  * Septic (TRWD is the OSSF authority; TCEQ 30 TAC 285): aerobic unit + subsurface drip,
    Ra = 0.10 gal/sf/day (clay, Class IV, within 1 ft of the emitters), drip field >= 5 ft
    from lot lines, >= 50 ft from the 315-ft normal pool (75 ft also tested), off the
    house (+5 ft), driveway/apron (+5 ft) and tank pad. Flow Q = Table III with water-saving
    fixtures: max(by bedrooms, by heated floor area).
  * TRWD Attachment I (2026) dock size: 8 sf per foot of shoreline up to 150 ft; >= 5 ft from
    side lines; lower deck >= 18 in above 320 ft; max 2 storeys, no toilets, no living space.

Writes data/<set>/maxbuild.json and figures/<set>/maxbuild_<lot>.png.
"""
import importlib
import json
import math

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from common import LOTS, load, save
from figlib import HALO, PAL, rot, scale_bar

F9 = importlib.import_module("09_figures")
T = load("terrain.json")
CANAL = load("canal.json", {}) or {}

LEGAL_SF = {"lot442": 24306, "lot411": 21780, "lot441": 23130, "bayview": 28314, "arrowhead": 21780}
SB = {"road": 35.0, "lake": 15.0, "side": 10.0}
ROAD_EASE = 20.0
RA = 0.10
GARAGE_SF = 960.0          # 3-car side-entry garage, 40 x 24 ft
PORCH_SF = 360.0           # covered porches counted in coverage
BEDROOMS = 6


def q_gpd(heated_sf, br=BEDROOMS):
    by_br = 180 + 60 * max(0, br - 2)
    tiers = [(1500, 180), (2500, 240), (3500, 300), (4500, 360), (5500, 420)]
    by_area = next((q for lim, q in tiers if heated_sf < lim), None)
    if by_area is None:
        by_area = 420 + 60 * math.ceil((heated_sf - 5500) / 1500.0)
    return max(by_br, by_area)


def poly(coords):
    return Polygon(coords).buffer(0)


def lake_line(t):
    segs = [LineString(e["seg_lf"]) for e in t["edges"] if e["kind"] == "lake"]
    return unary_union(segs)


def road_line(t):
    return unary_union([LineString(e["seg_lf"]) for e in t["edges"] if e["kind"] == "road"])


def side_mid_line(t, lot):
    sides = [LineString(e["seg_lf"]) for e in t["edges"] if e["kind"] == "side"]
    sides = sorted(sides, key=lambda s: -s.length)[:2]
    if len(sides) < 2:
        return None
    m1, m2 = sides[0].interpolate(0.5, normalized=True), sides[1].interpolate(0.5, normalized=True)
    return LineString([m1, m2])


def rear_half(t, lot):
    """Part of the lot behind (lake side of) the line joining the side-line midpoints."""
    ml = side_mid_line(t, lot)
    if ml is None:
        return None
    (x1, y1), (x2, y2) = ml.coords
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    lk = lake_line(t).centroid
    if (lk.x - x1) * nx + (lk.y - y1) * ny < 0:
        nx, ny = -nx, -ny
    far = 2000
    half = Polygon([(x1 - dx / L * far, y1 - dy / L * far), (x2 + dx / L * far, y2 + dy / L * far),
                    (x2 + dx / L * far + nx * far, y2 + dy / L * far + ny * far),
                    (x1 - dx / L * far + nx * far, y1 - dy / L * far + ny * far)])
    return lot.intersection(half)


def pool_poly(t):
    ps = [poly(p) for p in t["pool315_lf"] if len(p) > 3]
    return unary_union(ps) if ps else Polygon()


def solve(key, lake_sb=50.0):
    t = T[key]
    lot = poly(t["ring_lf"])
    env = unary_union([poly(p) for p in t["envelope_lf"]])
    rd = road_line(t)
    ease = rd.buffer(ROAD_EASE, cap_style=2).intersection(lot)
    env = env.difference(rd.buffer(ROAD_EASE + 0.5, cap_style=2)).buffer(0)
    legal = LEGAL_SF.get(key, lot.area)
    cov_max = 0.40 * legal
    rh = rear_half(t, lot)
    pool = pool_poly(t)
    drip_base = lot.buffer(-5.0).difference(pool.buffer(lake_sb)).difference(ease.buffer(0.1)).buffer(0)
    (ax_, ay_), (bx_, by_) = t["section_lf"]
    spine = math.degrees(math.atan2(by_ - ay_, bx_ - ax_))
    cands = []
    ex0, ey0, ex1, ey1 = env.bounds
    for ang in (spine, spine + 90, spine + 8, spine - 8, spine + 82, spine + 98):
        for W in range(44, 132, 4):          # along the angle direction
            for D in range(36, 112, 4):
                if W * D > cov_max:
                    continue
                r0 = box(-W / 2, -D / 2, W / 2, D / 2)
                r0 = affinity.rotate(r0, ang, origin=(0, 0))
                for cx in np.arange(ex0, ex1 + 0.1, 6.0):
                    for cy in np.arange(ey0, ey1 + 0.1, 6.0):
                        rr = affinity.translate(r0, cx, cy)
                        if env.contains(rr):
                            cands.append((W * D, ang, W, D, cx, cy, rr))
    cands.sort(key=lambda c: -c[0])
    best = None
    checked = 0
    seen_area = set()
    for area, ang, W, D, cx, cy, rr in cands:
        if rh is not None and rr.intersection(rh).area > 0.5 * rh.area:
            continue
        living_fp = area - GARAGE_SF - PORCH_SF
        if living_fp < 1200:
            break
        heated2 = 2 * living_fp
        q = q_gpd(heated2)
        need = q / RA
        # driveway: 16 ft from the house front to the road + a 30 x 30 ft side-entry apron
        hp = rr
        rpt = rd.interpolate(rd.project(hp.centroid))
        near = hp.exterior.interpolate(hp.exterior.project(rpt))
        drive = LineString([near, rpt]).buffer(8.0, cap_style=2)
        apron = near.buffer(17.0, cap_style=3)
        tank = hp.centroid.buffer(1).envelope  # placeholder, replaced below
        # tank pad 10 x 24 ft beside the house on the road side of the drip field
        side_pt = hp.exterior.interpolate(hp.exterior.project(rpt) + 40.0)
        tank = side_pt.buffer(8.0, cap_style=3)
        blocked = unary_union([hp.buffer(5.0, join_style=2), drive.buffer(5.0), apron.buffer(5.0),
                               tank.buffer(5.0)])
        drip = drip_base.difference(blocked).buffer(0)
        pieces = [g for g in (drip.geoms if isinstance(drip, MultiPolygon) else [drip]) if g.area >= 150]
        avail = sum(g.area for g in pieces)
        checked += 1
        if avail >= need:
            best = dict(footprint_sf=round(area), angle=round(ang, 1), W=W, D=D, living_fp_sf=round(living_fp),
                        heated_2st_sf=round(heated2), heated_25st_sf=round(heated2 + 0.5 * living_fp),
                        q_gpd=q, drip_need_sf=round(need), drip_avail_sf=round(avail),
                        coverage_pct=round(100 * area / legal, 1), cov_max_sf=round(cov_max),
                        house=list(rr.exterior.coords), drive=list(drive.exterior.coords),
                        apron=list(apron.exterior.coords), tank=list(tank.exterior.coords),
                        drip=[list(g.exterior.coords) for g in pieces],
                        rear_half_sf=None if rh is None else round(rh.area),
                        rear_half_used_sf=None if rh is None else round(rr.intersection(rh).area))
            break
        if checked > 4000:
            break
    # dock: TRWD 8 sf per ft of shoreline (<=150 ft) ; 5 ft from extended side lines
    lake_ft = t["frontage_lake_ft"]
    return best, dict(env_sf=round(env.area), lot_gis_sf=round(lot.area), legal_sf=legal,
                      ease_sf=round(ease.area), drip_base_sf=round(drip_base.area), lake_ft=lake_ft,
                      candidates=len(cands))


def dock_spec(key, t):
    lake_ft = t["frontage_lake_ft"]
    if key == "lot411":
        # plat: east line 95.78 ft on the 315-ft deed line of the canal tract; open water today
        # touches only ~35 ft of it (canal head silted/vegetated) -> two cases
        return {"shore_ft_plat": 95.8, "shore_ft_open_water": 35.0,
                "max_sf_plat": round(8 * 95.8), "max_sf_open_water": round(8 * 35.0),
                "note": "TRWD decides the shoreline length; canal head is silted"}
    sf = 8 * min(lake_ft, 150) + 4 * max(0, min(lake_ft, 250) - 150)
    return {"shore_ft": lake_ft, "max_sf": round(sf), "usable_width_ft": round(lake_ft - 10, 1)}


def figure(key, best, info, dock):
    t = T[key]
    th = F9.theta_of(key)
    u0, u1, v0, v1 = F9.fit_aspect(*F9.frame_limits(key, th, (20, 40, 28, 28)))
    us, vs, rgb, Z = F9.grids_rot(key, (u0, u1), (v0, v1), 1.0, th, zoom=19, smooth=1.5)
    w, h = u1 - u0, v1 - v0
    fig = plt.figure(figsize=(4.6, 4.6 * h / w))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#f8fafc")
    water = Z < 313.6
    ax.contourf(us, vs, water.astype(float), levels=[0.5, 1.5], colors=["#bfdbfe"], zorder=1)
    ax.contour(us, vs, Z, levels=[315.0], colors=[PAL["sky"]], linewidths=1.0, linestyles="--", zorder=3)
    ax.contour(us, vs, Z, levels=[320.0], colors=[PAL["amber"]], linewidths=1.0, linestyles="--", zorder=3)
    for p, xy in F9.neighbour_rings(key):
        q = rot(xy, th)
        ax.fill(q[:, 0], q[:, 1], facecolor="#f1f5f9", edgecolor="#94a3b8", lw=0.5, zorder=2)
    ring = rot(t["ring_lf"], th)
    ax.fill(ring[:, 0], ring[:, 1], facecolor="#fff7ed", edgecolor=PAL["coral"], lw=1.8, zorder=4)
    for pp in t["envelope_lf"]:
        q = rot(pp, th)
        ax.plot(q[:, 0], q[:, 1], color=PAL["green"], lw=0.9, ls="--", zorder=5)
    lot = poly(t["ring_lf"])
    ease = road_line(t).buffer(ROAD_EASE, cap_style=2).intersection(lot)
    for g in (ease.geoms if hasattr(ease, "geoms") else [ease]):
        if g.area > 10:
            q = rot(np.array(g.exterior.coords), th)
            ax.fill(q[:, 0], q[:, 1], facecolor="none", edgecolor="#64748b", hatch="////", lw=0.3, zorder=5)
    if best:
        for pp in best["drip"]:
            q = rot(np.array(pp), th)
            ax.fill(q[:, 0], q[:, 1], facecolor=(0.05, 0.65, 0.91, 0.22), edgecolor=PAL["sky"], lw=0.6,
                    hatch="....", zorder=6)
        for nm, col in (("drive", "#94a3b8"), ("apron", "#94a3b8")):
            q = rot(np.array(best[nm]), th)
            ax.fill(q[:, 0], q[:, 1], facecolor=col, edgecolor="none", alpha=0.7, zorder=6)
        q = rot(np.array(best["tank"]), th)
        ax.fill(q[:, 0], q[:, 1], facecolor="#0e7490", edgecolor="white", lw=0.5, zorder=7)
        q = rot(np.array(best["house"]), th)
        ax.fill(q[:, 0], q[:, 1], facecolor=PAL["gold"], edgecolor="#854d0e", lw=1.1, alpha=0.95, zorder=8)
        cx_, cy_ = q[:-1, 0].mean(), q[:-1, 1].mean()
        ax.text(cx_, cy_, f"LARGEST HOUSE\nfootprint {best['footprint_sf']:,} sf\n≈{best['heated_2st_sf']:,} sf heated"
                f"\n(2 storeys, 6 BR)\n+ 3-car garage", ha="center", va="center", fontsize=4.6, fontweight="bold",
                color="#422006", zorder=9)
        dp = [np.array(pp) for pp in best["drip"]]
        if dp:
            big = max(dp, key=lambda a: Polygon(a).area)
            q = rot(big, th)
            ax.text(q[:, 0].mean(), q[:, 1].mean(), f"drip field\nneeds {best['drip_need_sf']:,} sf\nroom {best['drip_avail_sf']:,} sf",
                    ha="center", va="center", fontsize=4.2, color="#075985", fontweight="bold", zorder=9,
                    path_effects=HALO)
    # dock rectangle at the shoreline
    le = [rot(e["seg_lf"], th) for e in t["edges"] if e["kind"] == "lake"]
    if le:
        a = max(le, key=lambda s: np.hypot(*(s[1] - s[0])))
        p0, p1 = a[0], a[1]
        mid = (p0 + p1) / 2
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        n = np.array([-d[1], d[0]])
        if np.dot(mid + n - ring[:-1].mean(axis=0), n) < np.dot(mid - ring[:-1].mean(axis=0), n):
            n = -n
        sf = dock.get("max_sf") or dock.get("max_sf_open_water")
        width = min(24.0, np.linalg.norm(p1 - p0) - 10) if key != "lot411" else 14.0
        length = sf / width
        off = 12.0 if key != "lot411" else 36.0
        base = mid + n * off
        if key == "lot411":
            # put the dock where open water is: scan the lake edge for water 36 ft out

            def z_at(pt):
                i = int(np.clip(np.searchsorted(vs, pt[1]), 0, len(vs) - 1))
                j = int(np.clip(np.searchsorted(us, pt[0]), 0, len(us) - 1))
                return Z[i, j]
            ts = [tt for tt in np.linspace(0.05, 0.95, 19) if z_at(p0 + (p1 - p0) * tt + n * off) < 313.6]
            tt = float(np.median(ts)) if ts else 0.8
            base = p0 + (p1 - p0) * tt + n * off
            mid = p0 + (p1 - p0) * tt
        corners = np.array([base - d * width / 2, base + d * width / 2, base + d * width / 2 + n * length,
                            base - d * width / 2 + n * length])
        ax.fill(corners[:, 0], corners[:, 1], facecolor="#a16207", edgecolor="#422006", lw=0.8, alpha=0.85, zorder=8)
        walk0 = mid
        ax.plot([walk0[0], base[0]], [walk0[1], base[1]], color="#a16207", lw=2.2, zorder=7)
        lab = (f"DOCK max {sf:,} sf\n({dock.get('shore_ft', dock.get('shore_ft_open_water')):.0f} ft shoreline × 8)"
               if key != "lot411" else f"DOCK {dock['max_sf_open_water']}–{dock['max_sf_plat']} sf\n(35–96 ft × 8, TRWD decides)")
        tp = corners.mean(axis=0) + n * (length / 2 + 14)
        ax.text(tp[0], tp[1], lab, fontsize=4.4, ha="center", va="center", color="#422006", fontweight="bold",
                zorder=10, path_effects=HALO)
    ax.set_xlim(u0, u1); ax.set_ylim(v0, v1); ax.set_aspect("equal"); ax.axis("off")
    ncx, ncy = u1 - 22, v1 - 26
    F9.north_rot(ax, ncx, ncy, 16, th)
    ax.text(ncx - math.sin(th) * 24, ncy + math.cos(th) * 24, "N", ha="center", va="center", fontsize=6,
            fontweight="bold", zorder=41)
    scale_bar(ax, u0 + 8, v0 + 8, 50, label="50 ft")
    leg = [mpatches.Patch(facecolor="#fff7ed", edgecolor=PAL["coral"], label="Lot (CAD GIS)"),
           plt.Line2D([], [], color=PAL["green"], ls="--", label="Setbacks 35/15/10 ft + ground ≥322 ft"),
           mpatches.Patch(facecolor="none", edgecolor="#64748b", hatch="////", label="20-ft POA road easement"),
           mpatches.Patch(facecolor=PAL["gold"], edgecolor="#854d0e", label="Largest house that leaves room for the drip field"),
           mpatches.Patch(facecolor=(0.05, 0.65, 0.91, 0.25), edgecolor=PAL["sky"], hatch="....",
                          label="Drip field (≥5 ft lines, ≥50 ft pool)"),
           mpatches.Patch(facecolor="#0e7490", label="Aerobic tank pad"),
           mpatches.Patch(facecolor="#a16207", label="Dock / boathouse (TRWD max)"),
           plt.Line2D([], [], color=PAL["amber"], ls="--", label="320 ft TRWD flowage"),
           plt.Line2D([], [], color=PAL["sky"], ls="--", label="315 ft normal pool")]
    lg = ax.legend(handles=leg, loc="upper left", fontsize=4.2, framealpha=0.92, borderpad=0.35,
                   labelspacing=0.22, handlelength=1.4)
    lg.set_zorder(50)
    from figlib import save as fsave
    return fsave(fig, f"maxbuild_{key}.png", dpi=330)


def main():
    import sys
    if "fig" in sys.argv[1:]:          # redraw from the saved solution (the search takes ~3 min)
        res = load("maxbuild.json")
        for key in LOTS:
            print(figure(key, res[key]["lake50"], res[key]["info"], res[key]["dock"]))
        return
    out = {}
    for key in LOTS:
        b50, info = solve(key, 50.0)
        b75, _ = solve(key, 75.0)
        dock = dock_spec(key, T[key])
        out[key] = {"lake50": b50, "lake75": None if b75 is None else {k: v for k, v in b75.items()
                                                                       if k not in ("house", "drive", "apron", "tank", "drip")},
                    "info": info, "dock": dock, "canal": CANAL.get(key)}
        s = {k: v for k, v in (b50 or {}).items() if k not in ("house", "drive", "apron", "tank", "drip")}
        print(key, info, "\n   50ft:", s, "\n   75ft:", out[key]["lake75"], "\n   dock:", dock)
        print("  ", figure(key, b50, info, dock))
    save("maxbuild.json", out)


if __name__ == "__main__":
    main()
