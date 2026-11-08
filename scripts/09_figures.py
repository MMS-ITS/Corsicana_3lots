"""Report figures (true north, feet; lidar / GIS-derived unless stated).

    plan_<lot>.png        true-scale boundary + 1-ft contour plan over aerial (rotated so the
                          road->lake section reads left->right; north arrow shows true north)
    section_<lot>.png     road->lake section: true 1:1 (full + lakeside detail) beside VE x5
    envelope_<lot>.png    building-envelope / septic / dock diagram (same rotation as the plan)
    terrain3d_<lot>.png   3-D terrain model draped with imagery (VE x3, stated on the figure)
    fema_<lot>.png        FEMA NFHL zones over aerial
    bathy_<lot>.png       TWDB Dec-2018 lake-bottom contours and depths near the lot
    aerial_<lot>_lot.jpg / _sub.jpg / _cove.jpg   annotated north-up aerial pictures
    fly_<lot>_<n>.jpg     fly-around style oblique 3-D views
    texas_<lot>.png       Texas locator with distance to Dallas
    region.png, texas_both.png   summary-page maps
"""
import json
import math
import os
import sys

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LightSource, Normalize
from PIL import Image
from scipy import ndimage

from common import ASSETS, DATA, FIG, FT2M, M2FT, load, local_xy
from figlib import (HALO, HALO_D, LOTNAME, PAL, aerial_local, centre, dem_local, grids_rot, lonlat_lf,
                    north_arrow, rot, save, scale_bar)

T = load("terrain.json")
P = load("parcels.json")
FL = load("flood.json")
SV = load("services.json")
LOTS = ["bayview", "arrowhead"]
ROADLBL = {"bayview": ["White Rock Rd", "Bayview Cir"], "arrowhead": ["Arrowhead Pt"]}
POOL, FLOOD100, FLOWAGE = 315.0, 318.0, 320.0
LAKE_NOW = 312.17        # TWDB daily level, 8 Nov 2026


def theta_of(key):
    (ax_, ay_), (bx_, by_) = T[key]["section_lf"]
    return -math.atan2(by_ - ay_, bx_ - ax_)


def neighbour_rings(key):
    out = []
    for p in P[key]["all_parcels"]:
        if p["geo_id"] == P[key]["target"]["geo_id"]:
            continue
        out.append((p, np.array([lonlat_lf(key, lo, la) for lo, la in p["ring"]])))
    return out


def north_rot(ax, x, y, size, theta, color="black"):
    dx, dy = -math.sin(theta) * size, math.cos(theta) * size
    # north (0,1) rotated by theta: (-sin t, cos t)
    ax.annotate("", xy=(x + dx, y + dy), xytext=(x, y),
                arrowprops=dict(arrowstyle="-|>,head_width=0.45,head_length=0.9", lw=1.5, color=color), zorder=40)
    ax.text(x + dx * 1.25, y + dy * 1.25, "N", ha="center", va="center", fontsize=7.5, fontweight="bold",
            color=color, path_effects=HALO, zorder=41)


def edge_labels(ax, key, theta, color="white", fs=5.4, minlen=28, off=9):
    r = T[key]
    ring = rot(r["ring_lf"], theta)
    cx, cy = ring[:, 0].mean(), ring[:, 1].mean()
    for e in r["edges"]:
        if e["len_ft"] < minlen:
            continue
        (x1, y1), (x2, y2) = rot(e["seg_lf"], theta)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        ang = ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
        nx, ny = -(y2 - y1), (x2 - x1)
        n = math.hypot(nx, ny) or 1
        nx, ny = nx / n, ny / n
        if (mx + nx - cx) ** 2 + (my + ny - cy) ** 2 < (mx - cx) ** 2 + (my - cy) ** 2:
            nx, ny = -nx, -ny
        ax.text(mx + nx * off, my + ny * off, f"{e['len_ft']:.0f}′", rotation=ang, ha="center", va="center",
                fontsize=fs, color=color, fontweight="bold", path_effects=HALO_D if color == "white" else HALO,
                zorder=30)


def frame_limits(key, theta, margin=(40, 40, 30, 30)):
    ring = rot(T[key]["ring_lf"], theta)
    s = rot(T[key]["section_lf"], theta)
    u0 = min(ring[:, 0].min(), s[:, 0].min()) - margin[0]
    u1 = max(ring[:, 0].max(), s[:, 0].max()) + margin[1]
    v0 = ring[:, 1].min() - margin[2]
    v1 = ring[:, 1].max() + margin[3]
    return u0, u1, v0, v1


ASPECT = 2.2   # every half-width picture on the lot picture page is 3.88 x 1.76 in


def fit_aspect(u0, u1, v0, v1, asp=ASPECT):
    """Grow the shorter side of a map frame so it has the print aspect ratio."""
    w, h = u1 - u0, v1 - v0
    if w / h < asp:
        d = (asp * h - w) / 2
        return u0 - d, u1 + d, v0, v1
    d = (w / asp - h) / 2
    return u0, u1, v0 - d, v1 + d


# =========================================================================== plan
def plan(key):
    r = T[key]
    th = theta_of(key)
    u0, u1, v0, v1 = fit_aspect(*frame_limits(key, th, (35, 45, 45, 45)))
    us, vs, rgb, Z = grids_rot(key, (u0, u1), (v0, v1), 0.6, th, zoom=19, smooth=1.3)
    w, h = u1 - u0, v1 - v0
    fig = plt.figure(figsize=(4.6, 4.6 * h / w))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(rgb, extent=[us[0], us[-1], vs[0], vs[-1]], origin="lower", zorder=1)
    ax.imshow(np.zeros(rgb.shape[:2]), extent=[us[0], us[-1], vs[0], vs[-1]], origin="lower", cmap="gray",
              alpha=0.22, zorder=2)
    zmin, zmax = math.floor(np.nanmin(Z)), math.ceil(np.nanmax(Z))
    lv1 = [v for v in range(zmin, zmax + 1) if v % 5 and v > 315]
    lv5 = [v for v in range(zmin, zmax + 1) if v % 5 == 0 and v > 315]
    ax.contour(us, vs, Z, levels=lv1, colors="#fde68a", linewidths=0.35, alpha=0.9, zorder=5)
    c5 = ax.contour(us, vs, Z, levels=lv5, colors="#fffbeb", linewidths=0.95, zorder=6)
    lbl = ax.clabel(c5, fmt="%d′", fontsize=5.0, inline=True, inline_spacing=2, colors="#fffbeb")
    for t in lbl:
        t.set_path_effects(HALO_D)
    ax.contour(us, vs, Z, levels=[POOL], colors=[PAL["sky"]], linewidths=1.2, linestyles="--", zorder=7)
    ax.contour(us, vs, Z, levels=[FLOWAGE], colors=[PAL["amber"]], linewidths=1.2, linestyles="--", zorder=7)
    for zp in r.get("zoneA_lf", []):
        ax.add_patch(mpatches.Polygon(rot(zp, th), closed=True, facecolor=(0.94, 0.27, 0.27, 0.16),
                                      edgecolor=PAL["coral"], hatch="////", lw=0.5, zorder=8))
    for p, xy in neighbour_rings(key):
        q = rot(xy, th)
        ax.plot(q[:, 0], q[:, 1], color="white", lw=0.55, alpha=0.8, zorder=9)
    ring = rot(r["ring_lf"], th)
    ax.plot(ring[:, 0], ring[:, 1], color=PAL["coral"], lw=2.1, zorder=12, solid_joinstyle="round")
    edge_labels(ax, key, th)
    for i, c in enumerate(r["corners"]):
        q = rot(c["lf"], th)
        ax.plot(*q, "o", ms=3.0, mfc="white", mec=PAL["coral"], mew=0.9, zorder=13)
        ax.text(q[0] + 3, q[1] + 3, f"P{i+1}", fontsize=4.6, color="white", path_effects=HALO_D, zorder=14)
    s = rot(r["section_lf"], th)
    ax.plot(s[:, 0], s[:, 1], color=PAL["pink"], lw=1.3, ls=(0, (5, 2)), zorder=15)
    ax.text(s[0, 0] - 2, s[0, 1] + 4, "A", color=PAL["pink"], fontsize=7, fontweight="bold", ha="right",
            path_effects=HALO, zorder=16)
    ax.text(s[1, 0] + 2, s[1, 1] + 4, "A′", color=PAL["pink"], fontsize=7, fontweight="bold",
            path_effects=HALO, zorder=16)
    hi = rot(r["elev"]["high_lf"], th); lo = rot(r["elev"]["low_lf"], th)
    ax.plot(*hi, marker="^", ms=6, color=PAL["gold"], mec="black", mew=0.6, zorder=17)
    ax.text(hi[0] + 8, hi[1] + 2, f"High {r['elev']['max_ft']:.1f}′", fontsize=5.2, ha="left", va="center",
            path_effects=HALO, zorder=17)
    ax.plot(*lo, marker="v", ms=6, color=PAL["sky"], mec="black", mew=0.6, zorder=17)
    ax.text(lo[0], lo[1] - 9, f"Low {r['elev']['min_land_ft']:.1f}′", fontsize=5.2, ha="center",
            path_effects=HALO, zorder=17)
    if r["slope"]["max50_line_lf"]:
        a_, b_ = rot(r["slope"]["max50_line_lf"], th)
        ax.annotate("", xy=b_, xytext=a_, arrowprops=dict(arrowstyle="-|>", color=PAL["amber"], lw=1.5), zorder=18)
        ax.text((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2 + 7, f"max 50-ft {r['slope']['max50_pct']:.0f}%",
                fontsize=4.8, color="black", ha="center", path_effects=HALO, zorder=18)
    az = math.radians(r["slope"]["drain_az_deg"])
    dvec = rot([math.sin(az), math.cos(az)], th)
    cx, cy = ring[:, 0].mean(), ring[:, 1].mean() + 14
    ax.annotate("", xy=(cx + 34 * dvec[0], cy + 34 * dvec[1]), xytext=(cx, cy),
                arrowprops=dict(arrowstyle="simple,head_width=0.75,head_length=0.8", color=PAL["sky"], ec="white",
                                lw=0.5), zorder=19)
    ax.text(cx, cy + 6, "drains", fontsize=4.8, color="white", ha="center", path_effects=HALO_D, zorder=19)
    # labels: lake (water cell farthest from the lot line) / road at A
    from shapely.geometry import Point as _Pt, Polygon as _Poly
    lotp = _Poly(ring)
    UU, VV = np.meshgrid(us[::8], vs[::8])
    wat = Z[::8, ::8] < 313.5
    best, bxy = -1, None
    for uu, vv in zip(UU[wat], VV[wat]):
        if not (u0 + 25 < uu < u1 - 25 and v0 + 12 < vv < v1 - 0.30 * (v1 - v0)):
            continue
        dd = lotp.exterior.distance(_Pt(uu, vv))
        if dd > best:
            best, bxy = dd, (uu, vv)
    if bxy:
        ax.text(bxy[0], bxy[1], "Richland-Chambers\nLake (cove)", fontsize=5.2, color="white", ha="center",
                va="center", style="italic", path_effects=HALO_D, zorder=20)
    ax.text(s[0, 0] + 3, s[0, 1] - 4, "road ℄", fontsize=4.8, color="white", ha="left", va="top",
            path_effects=HALO_D, zorder=20)
    ax.set_xlim(u0, u1); ax.set_ylim(v0, v1); ax.set_aspect("equal"); ax.axis("off")
    north_rot(ax, u1 - 0.05 * w, v1 - 0.22 * h, 0.12 * h, th)
    scale_bar(ax, u0 + 0.03 * w, v0 + 0.05 * h, 50, height=0.02 * h)
    leg = [mpatches.Patch(facecolor="none", edgecolor=PAL["coral"], lw=1.4, label="Lot line (CAD GIS)"),
           plt.Line2D([], [], color="#fffbeb", lw=0.9, label="5-ft contour (1-ft thin)"),
           plt.Line2D([], [], color=PAL["sky"], lw=1.1, ls="--", label="315′ normal pool"),
           plt.Line2D([], [], color=PAL["amber"], lw=1.1, ls="--", label="320′ TRWD flowage"),
           mpatches.Patch(facecolor=(0.94, 0.27, 0.27, 0.25), edgecolor=PAL["coral"], hatch="////",
                          label="FEMA Zone A"),
           plt.Line2D([], [], color=PAL["pink"], lw=1.2, ls="--", label="Section A–A′")]
    lg = ax.legend(handles=leg, loc="upper left", ncol=2, fontsize=4.1, framealpha=0.85, borderpad=0.3,
                   labelspacing=0.2, handlelength=1.5, columnspacing=0.8)
    lg.set_zorder(45)
    return save(fig, f"plan_{key}.png", dpi=330)


# =========================================================================== section
def section(key):
    r = T[key]
    s = r["section"]
    d = np.array(s["dist_ft"]); z = np.array(s["z_ft"])
    a0, shore, d315 = s["front_lot_line_ft"], s["shore_ft"], s["d315_ft"]
    hi_d, hi_z = s["high_at_ft"], s["high_ft"]
    fig = plt.figure(figsize=(7.9, 2.05))
    # ---- left top: full profile at TRUE 1:1
    L = d[-1]
    axA = fig.add_axes([0.035, 0.80, 0.445, 0.17])
    axA.fill_between(d, 300, z, color="#d6b98c", lw=0)
    axA.plot(d, z, color="#5b3a1a", lw=0.8)
    axA.fill_between(d, 300, np.where(d >= shore - 0.5, s["water_level_ft"], np.nan), color=PAL["lake"],
                     alpha=0.55, lw=0)
    axA.set_xlim(0, L); axA.set_ylim(z.min() - 2, z.max() + 3)
    axA.set_aspect("equal", adjustable="box", anchor="W")
    axA.set_title("TRUE SCALE 1:1 — whole section, road (A) → lake (A′)", fontsize=6.2, loc="left",
                  color=PAL["navy"], fontweight="bold", pad=2)
    axA.tick_params(labelsize=5, length=2)
    axA.set_yticks([320, 330])
    axA.set_xticks(range(0, int(L) + 1, 50))
    # direct line (high point -> 315 ft at the shore)
    axA.plot([hi_d, d315], [hi_z, POOL], color=PAL["pink"], lw=0.9)
    # ---- left bottom: lakeside detail at TRUE 1:1
    span = 90.0
    x0d = max(a0, d315 - span + 12)
    axB = fig.add_axes([0.035, 0.08, 0.445, 0.56])
    sel = (d >= x0d) & (d <= min(d[-1], d315 + 14))
    axB.fill_between(d[sel], 305, z[sel], color="#d6b98c", lw=0)
    axB.plot(d[sel], z[sel], color="#5b3a1a", lw=1.0)
    axB.axhline(POOL, color=PAL["sky"], lw=0.8, ls="--")
    axB.axhline(FLOWAGE, color=PAL["amber"], lw=0.8, ls="--")
    axB.axhspan(305, s["water_level_ft"], xmin=0, xmax=1, color=PAL["lake"], alpha=0.0)
    wsel = d[sel] >= shore - 0.5
    axB.fill_between(d[sel][wsel], 305, LAKE_NOW, color=PAL["lake"], alpha=0.45, lw=0)
    zlo = 309.0
    wa, ha = 0.445 * 7.9, 0.56 * 2.05            # axes box in inches
    axB.set_xlim(x0d, x0d + span)
    axB.set_ylim(zlo, zlo + span * ha / wa)      # identical ft-per-inch on both axes = true 1:1
    axB.set_aspect("equal", adjustable="box", anchor="SW")
    axB.set_title(f"TRUE SCALE 1:1 — lakeside {span:.0f} ft (real angles)", fontsize=6.2, loc="left",
                  color=PAL["navy"], fontweight="bold", pad=2)
    axB.tick_params(labelsize=5, length=2)
    axB.set_ylabel("ft (NAVD88≈msl)", fontsize=5)
    # bank angle at the lake: last 20 ft before the 315 line
    b0 = d315 - 20
    zb0 = float(np.interp(b0, d, z))
    axB.plot([b0, d315], [zb0, POOL], color=PAL["pink"], lw=1.4)
    axB.plot([b0, d315], [POOL, POOL], color=PAL["pink"], lw=0.6, ls=":")
    axB.text(d315 - 2, POOL + 0.8, f"bank {s['bank20_deg']:.0f}° ({s['bank20_pct']:.0f}%)\nover last 20 ft",
             fontsize=5.0, ha="right", va="bottom", color=PAL["pink"], path_effects=HALO)
    m0 = s["max50_from_ft"]
    if m0 + 50 >= x0d:
        zm0 = float(np.interp(m0, d, z)); zm1 = float(np.interp(m0 + 50, d, z))
        axB.plot([m0, m0 + 50], [zm0, zm1], color=PAL["amber"], lw=2.0, alpha=0.9)
        xm = min(max(m0 + 25, x0d + 22), x0d + span - 22)
        axB.text(xm, max(zm0, zm1) + 1.0, f"max over 50 ft: {s['max50_deg']:.1f}° ({s['max50_pct']:.1f}%)",
                 fontsize=5.0, ha="center", color="#92400e", path_effects=HALO, clip_on=True)
    axB.text(x0d + 2, POOL + 0.25, "315 normal pool", fontsize=4.6, color=PAL["sky"], va="bottom")
    axB.text(x0d + 2, FLOWAGE + 0.25, "320 TRWD flowage line", fontsize=4.6, color="#b45309", va="bottom")
    axB.text(x0d + span - 1, LAKE_NOW - 0.4, f"lake {LAKE_NOW:.1f} (8 Nov 2026)", fontsize=4.6, color="white",
             ha="right", va="top")
    # ---- right: vertically exaggerated, all annotations (factor computed from the drawn axes)
    axC = fig.add_axes([0.535, 0.10, 0.455, 0.80])
    axC.fill_between(d, 300, z, color="#e7cfa6", lw=0)
    axC.plot(d, z, color="#5b3a1a", lw=1.0)
    axC.fill_between(d, 300, np.where(d >= shore - 0.5, LAKE_NOW, np.nan), color=PAL["lake"], alpha=0.45, lw=0)
    for lv, col, lab in ((POOL, PAL["sky"], "315 normal pool"), (FLOOD100, PAL["purple"], "318 100-yr (TRWD)"),
                         (FLOWAGE, PAL["amber"], "320 TRWD flowage")):
        axC.axhline(lv, color=col, lw=0.7, ls="--")
        axC.text(2, lv + 0.15, lab, fontsize=4.6, color=col, va="bottom")
    for x_, lab in ((a0, "front lot line"), (min(s["rear_lot_line_ft"], shore), "lake lot line")):
        axC.axvline(x_, color=PAL["coral"], lw=0.7, ls=":")
        axC.text(x_ + 1.5, z.max() + 1.2, lab, fontsize=4.6, color=PAL["coral"], rotation=90, va="top")
    # contour crossings (every 5 ft) on the profile
    for lv in range(int(math.ceil(z.min())), int(z.max()) + 1):
        if lv % 5:
            continue
        idx = np.where((z[:-1] - lv) * (z[1:] - lv) <= 0)[0]
        for i in idx[:2]:
            axC.plot(d[i], lv, marker="|", color="black", ms=4, mew=0.6)
            axC.text(d[i], lv + 0.5, f"{lv}", fontsize=4.4, ha="center", va="bottom")
    axC.plot([hi_d, d315], [hi_z, POOL], color=PAL["pink"], lw=1.0, ls="--")
    m0 = s["max50_from_ft"]
    zm0 = float(np.interp(m0, d, z)); zm1 = float(np.interp(m0 + 50, d, z))
    axC.plot([m0, m0 + 50], [zm0, zm1], color=PAL["amber"], lw=2.2)
    pad = r["fits"].get("two-storey 5BR 60x46 ft + garage (2,760 sf)")
    axC.set_xlim(0, d[-1]); axC.set_ylim(min(z.min(), LAKE_NOW) - 1.5, z.max() + 9.0)
    axC.set_aspect("auto")
    # report the exaggeration actually drawn (ft-per-inch horizontal / vertical)
    wc, hc = 0.455 * 7.9, 0.80 * 2.05
    ve_drawn = (d[-1] / wc) / ((z.max() + 9.0 - (min(z.min(), LAKE_NOW) - 1.5)) / hc)
    VE = round(ve_drawn, 1)
    axC.set_title(f"VERTICAL EXAGGERATION ×{VE} — same section A–A′ (bearing {s['bearing_deg']:.0f}°)",
                  fontsize=6.2, loc="left", color=PAL["coral"], fontweight="bold", pad=2)
    axC.tick_params(labelsize=5, length=2)
    axC.set_xlabel("distance from road centre-line (ft)", fontsize=5.2, labelpad=1)
    run = s["run_high_to_pool_ft"]
    txt = (f"Road→315′ shoreline: {s['road_to_pool_ft']:.0f} ft   |   high {hi_z:.1f}′ → pool 315′: "
           f"H = {hi_z-POOL:.1f} ft over L = {run:.0f} ft\n"
           f"Direct angle {s['direct_angle_deg']:.1f}° (avg grade {s['avg_grade_pct']:.1f}%)   |   "
           f"max over 50 ft on this line: {s['max50_deg']:.1f}° ({s['max50_pct']:.1f}%)   |   steepest 10 ft: "
           f"{s['steep10_deg']:.0f}° (bulkhead/bank)\n"
           f"Max over 50 ft ANYWHERE on the lot: {r['slope']['max50_deg']:.1f}° ({r['slope']['max50_pct']:.0f}%) "
           f"— amber arrow on plan   |   rise at the lake edge (last 20 ft): {s['bank20_deg']:.1f}° "
           f"({s['bank20_pct']:.0f}%)")
    axC.text(0.99, 0.97, txt, transform=axC.transAxes, fontsize=4.9, va="top", ha="right",
             bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=PAL["slate"], lw=0.4, alpha=0.92))
    return save(fig, f"section_{key}.png", dpi=330)


# =========================================================================== envelope
def envelope(key):
    r = T[key]
    th = theta_of(key)
    u0, u1, v0, v1 = fit_aspect(*frame_limits(key, th, (20, 30, 28, 28)))
    us, vs, rgb, Z = grids_rot(key, (u0, u1), (v0, v1), 1.0, th, zoom=19, smooth=1.5)
    w, h = u1 - u0, v1 - v0
    fig = plt.figure(figsize=(4.6, 4.6 * h / w))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#f8fafc")
    water = Z < 313.6
    ax.contourf(us, vs, water.astype(float), levels=[0.5, 1.5], colors=["#bfdbfe"], zorder=1)
    ax.contour(us, vs, Z, levels=[POOL], colors=[PAL["sky"]], linewidths=1.0, linestyles="--", zorder=3)
    ax.contour(us, vs, Z, levels=[FLOWAGE], colors=[PAL["amber"]], linewidths=1.0, linestyles="--", zorder=3)
    ax.contour(us, vs, Z, levels=[FLOWAGE + 2], colors=[PAL["purple"]], linewidths=0.8, linestyles=":", zorder=3)
    cs = ax.contour(us, vs, Z, levels=[v for v in range(316, 345) if v % 2 == 0], colors="#cbd5e1",
                    linewidths=0.4, zorder=2)
    for p, xy in neighbour_rings(key):
        q = rot(xy, th)
        ax.fill(q[:, 0], q[:, 1], facecolor="#f1f5f9", edgecolor="#94a3b8", lw=0.5, zorder=2)
    ring = rot(r["ring_lf"], th)
    ax.fill(ring[:, 0], ring[:, 1], facecolor="#fff7ed", edgecolor=PAL["coral"], lw=1.8, zorder=4)
    for poly in r["envelope_lf"]:
        q = rot(poly, th)
        ax.fill(q[:, 0], q[:, 1], facecolor=(0.09, 0.64, 0.29, 0.20), edgecolor=PAL["green"], lw=1.0, ls="--",
                zorder=5)
    if key == "arrowhead":
        for poly in r["drip"]["poly_lf"]:
            q = rot(poly, th)
            ax.fill(q[:, 0], q[:, 1], facecolor=(0.05, 0.65, 0.91, 0.14), edgecolor=PAL["sky"], lw=0.6,
                    hatch="....", zorder=5)
    f2 = r["fits"]["two-storey 5BR 60x46 ft + garage (2,760 sf)"]
    f1 = r["fits"]["one-storey 5BR 84x56 ft incl. garage (4,700 sf)"]
    if f1:
        q = rot(f1["poly_lf"], th)
        ax.plot(q[:, 0], q[:, 1], color=PAL["navy"], lw=0.8, ls=(0, (3, 2)), zorder=6)
    if f2:
        q = rot(f2["poly_lf"], th)
        ax.fill(q[:, 0], q[:, 1], facecolor=PAL["gold"], edgecolor="#854d0e", lw=1.0, alpha=0.9, zorder=7)
        cx_, cy_ = q[:-1, 0].mean(), q[:-1, 1].mean()
        ax.text(cx_, cy_, "5-BR house\n2-storey\n60×46 ft", ha="center", va="center", fontsize=4.8,
                fontweight="bold", color="#422006", zorder=8)
        # driveway to nearest road frontage
        road_pts = [rot(e["seg_lf"], th) for e in r["edges"] if e["kind"] == "road"]
        if road_pts:
            allp = np.vstack(road_pts)
            j = int(np.argmin(np.hypot(allp[:, 0] - cx_, allp[:, 1] - cy_)))
            ax.plot([cx_, allp[j, 0]], [cy_, allp[j, 1]], color="#64748b", lw=5, alpha=0.55,
                    solid_capstyle="butt", zorder=6)
    # setback dimension labels on each edge
    for e in r["edges"]:
        if e["len_ft"] < 25:
            continue
        (x1, y1), (x2, y2) = rot(e["seg_lf"], th)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        sb = {"road": 35, "lake": 15, "side": 10}[e["kind"]]
        nx, ny = -(y2 - y1), (x2 - x1)
        n = math.hypot(nx, ny) or 1
        nx, ny = nx / n, ny / n
        if (mx + nx - ring[:, 0].mean()) ** 2 + (my + ny - ring[:, 1].mean()) ** 2 > \
                (mx - ring[:, 0].mean()) ** 2 + (my - ring[:, 1].mean()) ** 2:
            nx, ny = -nx, -ny
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        ang = ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
        ax.text(mx + nx * sb * 0.5, my + ny * sb * 0.5, f"{sb}′ {e['kind']}", fontsize=4.4, rotation=ang,
                ha="center", va="center", color="#166534", zorder=9)
    # dock zone (TRWD max structure size from lake frontage)
    lf = r["frontage_lake_ft"]
    dock_sf = 8 * min(lf, 150) + 4 * max(0, min(lf, 250) - 150)
    lake_edges = [rot(e["seg_lf"], th) for e in r["edges"] if e["kind"] == "lake"]
    if lake_edges:
        le = max(lake_edges, key=lambda a: np.hypot(*(a[1] - a[0])))
        mx, my = (le[0] + le[1]) / 2
        ax.text(mx + 10, my - 16, f"TRWD dock ≤ {dock_sf:,.0f} sf\n({lf:.0f} ft frontage)", fontsize=4.6,
                color=PAL["navy"], ha="center", path_effects=HALO, zorder=10)
    ax.set_xlim(u0, u1); ax.set_ylim(v0, v1); ax.set_aspect("equal"); ax.axis("off")
    north_rot(ax, u0 + 0.05 * w, v1 - 0.25 * h, 0.12 * h, th)
    scale_bar(ax, u0 + 0.03 * w, v0 + 0.04 * h, 50, height=0.018 * h)
    leg = [mpatches.Patch(facecolor="#fff7ed", edgecolor=PAL["coral"], label="Lot (GIS)"),
           mpatches.Patch(facecolor=(0.09, 0.64, 0.29, 0.25), edgecolor=PAL["green"], ls="--",
                          label="Buildable envelope (SF-3 setbacks, ≥322′)"),
           mpatches.Patch(facecolor=PAL["gold"], edgecolor="#854d0e", label="2-storey 5-BR footprint"),
           plt.Line2D([], [], color=PAL["navy"], lw=0.8, ls=(0, (3, 2)), label="1-storey 84×56 ft option"),
           plt.Line2D([], [], color=PAL["amber"], ls="--", label="320′ TRWD flowage"),
           plt.Line2D([], [], color=PAL["sky"], ls="--", label="315′ normal pool")]
    if key == "arrowhead":
        leg.append(mpatches.Patch(facecolor=(0.05, 0.65, 0.91, 0.18), edgecolor=PAL["sky"], hatch="....",
                                  label="Drip-field area (≥50′ from pool)"))
    lg = ax.legend(handles=leg, loc="lower right", fontsize=4.4, framealpha=0.9, borderpad=0.35,
                   labelspacing=0.25, handlelength=1.4)
    lg.set_zorder(50)
    return save(fig, f"envelope_{key}.png", dpi=330)


# =========================================================================== 3-D terrain
def terrain3d(key, ve=3.0):
    """Block-diagram terrain model: hypsometric tint + hillshade, draped 1-ft contours,
    lot line, 5-BR massing, slope arrow, lake at its Nov-2026 level. Vertical x3 (stated)."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    r = T[key]
    th = theta_of(key)
    u0, u1, v0, v1 = frame_limits(key, th, (20, 30, 25, 25))
    step = 2.0
    us, vs, rgb, Z = grids_rot(key, (u0, u1), (v0, v1), step, th, zoom=19, smooth=1.2)
    UU, VV = np.meshgrid(us, vs)
    base = 300.0
    Zw = np.where(Z < 313.6, LAKE_NOW, Z)
    ls = LightSource(azdeg=315, altdeg=35)
    cmap = plt.get_cmap("terrain")
    norm = Normalize(305, Z.max() + 4)
    col = ls.shade(Zw, cmap=cmap, norm=norm, vert_exag=ve, dx=step, dy=step, blend_mode="soft")
    col[Z < 313.6] = [0.35, 0.58, 0.86, 1.0]
    col[..., :3] = np.clip(col[..., :3] * 0.55 + rgb * 0.45, 0, 1) * np.where(Z[..., None] < 313.6, 0, 1) + \
        col[..., :3] * np.where(Z[..., None] < 313.6, 1, 0)
    fig = plt.figure(figsize=(4.6, 2.9))
    ax = fig.add_axes([-0.14, -0.30, 1.28, 1.52], projection="3d", computed_zorder=False)
    ax.plot_surface(UU, VV, (Zw - base) * ve, facecolors=col, rstride=1, cstride=1, linewidth=0,
                    antialiased=False, shade=False, zorder=2)
    # skirt (block sides)
    for edge in (np.s_[0, :], np.s_[-1, :], np.s_[:, 0], np.s_[:, -1]):
        ue, ve_, ze = UU[edge], VV[edge], (Zw[edge] - base) * ve
        verts = [list(zip(ue, ve_, ze)) + list(zip(ue[::-1], ve_[::-1], np.zeros_like(ze)))]
        ax.add_collection3d(Poly3DCollection(verts, facecolor="#a16207", edgecolor="#713f12", lw=0.3, alpha=0.95, zorder=1))

    def zat(x, y):
        return float(ndimage.map_coordinates(Zw, [[(y - vs[0]) / step], [(x - us[0]) / step]], order=1)[0])
    # draped contours every 2 ft
    cs = plt.figure().add_subplot().contour(us, vs, Z, levels=[v for v in range(316, 345, 2)])
    plt.close()
    for lev, segs in zip(cs.levels, cs.allsegs):
        for sg in segs:
            if len(sg) < 3:
                continue
            ax.plot(sg[:, 0], sg[:, 1], np.full(len(sg), (lev - base) * ve + 0.3), color="white", lw=0.35,
                    alpha=0.8, zorder=3)
    ring = rot(r["ring_lf"], th)
    zr = np.array([zat(x, y) for x, y in ring])
    ax.plot(ring[:, 0], ring[:, 1], (zr - base + 0.4) * ve, color=PAL["coral"], lw=2.0, zorder=5)
    f2 = r["fits"]["two-storey 5BR 60x46 ft + garage (2,760 sf)"]
    if f2:
        q = rot(f2["poly_lf"], th)[:4]
        zp = (f2["pad_level_ft"] - base) * ve
        zt = zp + 26 * ve * 0.45
        faces = [[(*q[k], zp), (*q[(k + 1) % 4], zp), (*q[(k + 1) % 4], zt), (*q[k], zt)] for k in range(4)]
        faces.append([(*q[k], zt) for k in range(4)])
        ax.add_collection3d(Poly3DCollection(faces, facecolor=PAL["gold"], edgecolor="#713f12", lw=0.6,
                                             alpha=0.95, zorder=6))
    # slope arrow along the section from the high point toward the lake
    s = r["section"]
    sl = rot(r["section_lf"], th)
    a_ = sl[0] + (sl[1] - sl[0]) * (s["high_at_ft"] / s["dist_ft"][-1])
    b_ = sl[0] + (sl[1] - sl[0]) * (s["d315_ft"] / s["dist_ft"][-1]) * 0.97
    ax.quiver(a_[0], a_[1] - 22, (zat(*a_) - base + 2) * ve, b_[0] - a_[0], 0,
              (zat(*b_) - zat(*a_)) * ve, color=PAL["sky"], lw=1.6, arrow_length_ratio=0.12, zorder=7)
    ax.set_box_aspect((u1 - u0, v1 - v0, (Z.max() - base + 2) * ve))
    ax.set_zlim(0, (Z.max() - base + 2) * ve)
    ax.view_init(elev=24, azim=-38)
    ax.set_axis_off()
    ax.text(sl[0, 0], sl[0, 1], (zat(*sl[0]) - base + 6) * ve, "road", fontsize=6, fontweight="bold", zorder=9)
    ax.text(sl[1, 0], sl[1, 1], (LAKE_NOW - base + 4) * ve, "lake", fontsize=6, color=PAL["navy"],
            fontweight="bold", zorder=9)
    # the vertical exaggeration (x3) is stated in the report caption next to the picture
    return save(fig, f"terrain3d_{key}.png", dpi=330)


# =========================================================================== FEMA
def fema(key):
    r = T[key]
    half = 700
    xs, ys, rgb = aerial_local(key, 18, half, 1.5)
    meta = json.load(open(os.path.join(ASSETS, f"nfhl_{key}.json")))
    im = np.asarray(Image.open(os.path.join(ASSETS, f"nfhl_{key}.png")).convert("RGBA")).astype("float32") / 255
    lon0, lat0 = centre(key)
    XX, YY = np.meshgrid(xs, ys)
    from common import local_lonlat
    lon, lat = local_lonlat(XX, YY, lon0, lat0)
    W0, S0, E0, N0 = meta["bbox"]
    px = (lon - W0) / (E0 - W0) * (im.shape[1] - 1)
    py = (N0 - lat) / (N0 - S0) * (im.shape[0] - 1)
    ov = np.stack([ndimage.map_coordinates(im[..., k], [py, px], order=0, mode="constant") for k in range(4)], -1)
    yh = half / ASPECT
    fig = plt.figure(figsize=(3.88, 3.88 / ASPECT))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(rgb, extent=[xs[0], xs[-1], ys[0], ys[-1]], origin="lower")
    ax.imshow(ov, extent=[xs[0], xs[-1], ys[0], ys[-1]], origin="lower", alpha=0.75)
    ring = np.array(r["ring_lf"])
    ax.plot(ring[:, 0], ring[:, 1], color="yellow", lw=1.6)
    ax.plot(ring[:, 0], ring[:, 1], color="black", lw=0.5)
    pan = FL[key]["panel"][0]
    ax.set_xlim(-half * 1.0, half * 1.0); ax.set_ylim(-yh, yh); ax.set_aspect("equal")
    ax.axis("off")
    ax.text(-half * 0.97, yh * 0.93, f"FEMA NFHL · FIRM panel {pan['FIRM_PAN']} (eff. 5 Jun 2012)\n"
            f"Zone A (no BFE) along shore · Zone X elsewhere · {r['zoneA_pct_of_lot']:.0f}% of lot in Zone A",
            fontsize=5.2, va="top", color="black",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.88))
    north_arrow(ax, half * 0.93, -yh * 0.05, yh * 0.28)
    scale_bar(ax, -half * 0.95, -yh * 0.88, 200, height=9)
    leg = [mpatches.Patch(facecolor="#9ecae1", edgecolor="#2171b5", label="Zone A (1% annual chance)"),
           mpatches.Patch(facecolor="yellow", edgecolor="black", label="Lot")]
    ax.legend(handles=leg, loc="lower right", fontsize=4.8, framealpha=0.85)
    return save(fig, f"fema_{key}.png", dpi=330)


# =========================================================================== bathymetry
def bathy(key):
    B = load("bathymetry.json")[key]
    r = T[key]
    half = 1150
    xs, ys, rgb = aerial_local(key, 16, half, 4.0)
    yh = half / ASPECT
    fig = plt.figure(figsize=(3.88, 3.88 / ASPECT))
    ax = fig.add_axes([0, 0, 1, 1])
    gray = rgb.mean(axis=2)
    ax.imshow(np.dstack([gray] * 3) * 0.55 + 0.45, extent=[xs[0], xs[-1], ys[0], ys[-1]], origin="lower")
    norm = Normalize(0, 40)
    cmap = plt.get_cmap("YlGnBu")
    segs, cols, lw = [], [], []
    for ln in B["lines"]:
        depth = POOL - ln["z"]
        if depth <= 0:
            continue
        segs.append(np.array(ln["xy"]))
        cols.append(cmap(norm(depth)))
        lw.append(0.9 if ln["z"] % 5 == 0 else 0.3)
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=lw))
    # depth labels: each 5-ft contour labelled at its visible point nearest the lot
    best = {}
    for ln in B["lines"]:
        if ln["z"] % 5 or ln["z"] >= POOL:
            continue
        xy = np.array(ln["xy"])
        vis = xy[(np.abs(xy[:, 0]) < half * 0.92) & (np.abs(xy[:, 1]) < yh * 0.85)]
        if len(vis) == 0:
            continue
        dd = np.hypot(vis[:, 0] - 150, vis[:, 1])
        i = int(np.argmin(dd))
        if ln["z"] not in best or dd[i] < best[ln["z"]][0]:
            best[ln["z"]] = (dd[i], vis[i])
    for zc, (_, m) in best.items():
        ax.text(m[0], m[1], f"{POOL - zc:.0f}", fontsize=4.6, color=PAL["navy"], ha="center",
                va="center", path_effects=HALO, zorder=6)
    ring = np.array(r["ring_lf"])
    ax.fill(ring[:, 0], ring[:, 1], color=PAL["coral"], zorder=8)
    ax.annotate(LOTNAME[key], xy=(ring[:, 0].mean(), ring[:, 1].mean()), xytext=(-half * 0.42, yh * 0.30),
                fontsize=5.5, color=PAL["coral"], fontweight="bold", path_effects=HALO,
                arrowprops=dict(arrowstyle="-|>", color=PAL["coral"], lw=0.8), zorder=9)
    ax.set_xlim(-half, half); ax.set_ylim(-yh, yh); ax.set_aspect("equal"); ax.axis("off")
    w150 = B.get("within_150ft") or B.get("within_300ft")
    lab = "≤150 ft" if B.get("within_150ft") else "≤300 ft"
    lk = load("bathymetry.json")["lake"]
    ax.text(-half * 0.98, yh * 0.95,
            f"TWDB Dec-2018 survey · depth (ft) below 315′ normal pool\n"
            f"Off this lot ({lab} of frontage): mean {w150['mean_depth_ft']:.0f} ft, max {w150['max_depth_ft']:.0f} ft"
            f"\nLake: mean {lk['mean_depth_ft']:.0f} ft, max {lk['max_depth_ft']:.0f} ft · now ~{POOL-LAKE_NOW:.1f} ft below pool",
            fontsize=5.0, va="top", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9))
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cax = fig.add_axes([0.70, 0.11, 0.27, 0.045])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("depth at normal pool (ft)", fontsize=4.6, labelpad=1)
    cb.ax.tick_params(labelsize=4.5, length=1.5)
    north_arrow(ax, half * 0.93, yh * 0.25, yh * 0.30)
    scale_bar(ax, -half * 0.95, -yh * 0.88, 500, height=12)
    return save(fig, f"bathy_{key}.png", dpi=330)


# =========================================================================== aerial pictures
def aerial_pics(key):
    r = T[key]
    ring = np.array(r["ring_lf"])
    out = []
    # (1) lot close-up, north-up
    xs, ys, rgb = aerial_local(key, 19, 260, 0.45)
    fig = plt.figure(figsize=(3.85, 2.45))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(rgb, extent=[xs[0], xs[-1], ys[0], ys[-1]], origin="lower")
    for p, xy in neighbour_rings(key):
        ax.plot(xy[:, 0], xy[:, 1], color="white", lw=0.5, alpha=0.75)
    ax.plot(ring[:, 0], ring[:, 1], color=PAL["coral"], lw=2.0)
    label_n = ring.mean(axis=0)
    ax.text(label_n[0], label_n[1], LOTNAME[key].split(" ", 1)[0], fontsize=8, fontweight="bold", color="white",
            ha="center", va="center", path_effects=HALO_D)
    cx, cy = ring[:, 0].mean(), ring[:, 1].mean()
    span = max(np.ptp(ring[:, 0]), np.ptp(ring[:, 1]) / 0.636) * 0.62 + 40
    ax.set_xlim(cx - span, cx + span); ax.set_ylim(cy - span * 0.636, cy + span * 0.636)
    ax.set_aspect("equal"); ax.axis("off")
    north_arrow(ax, cx + span * 0.9, cy + span * 0.30, span * 0.14, color="white")
    scale_bar(ax, cx - span * 0.95, cy - span * 0.58, 50, color="white", height=span * 0.015)
    out.append(save(fig, f"aerial_{key}_lot.jpg", dpi=330, pil_kwargs={"quality": 90}))
    # (2) subdivision context
    xs, ys, rgb = aerial_local(key, 18, 1300, 1.2)
    fig = plt.figure(figsize=(3.88, 3.88 / ASPECT))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(rgb, extent=[xs[0], xs[-1], ys[0], ys[-1]], origin="lower")
    ax.fill(ring[:, 0], ring[:, 1], facecolor=(0.94, 0.27, 0.27, 0.45), edgecolor=PAL["coral"], lw=1.6)
    ax.set_xlim(-1000, 1000); ax.set_ylim(-1000 / ASPECT, 1000 / ASPECT); ax.set_aspect("equal"); ax.axis("off")
    north_arrow(ax, 920, 120, 150, color="white")
    scale_bar(ax, -960, -410, 400, color="white", height=12)
    out.append(save(fig, f"aerial_{key}_sub.jpg", dpi=300, pil_kwargs={"quality": 90}))
    # (3) cove / lake context
    xs, ys, rgb = aerial_local(key, 16, 5400, 6.0)
    fig = plt.figure(figsize=(3.88, 3.88 / ASPECT))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(rgb, extent=[xs[0], xs[-1], ys[0], ys[-1]], origin="lower")
    ax.plot(0, 0, marker="o", ms=9, mfc="none", mec=PAL["coral"], mew=2.0)
    ax.plot(0, 0, marker="o", ms=3, color=PAL["coral"])
    ax.text(260, 260, LOTNAME[key], fontsize=6, color="white", fontweight="bold", path_effects=HALO_D)
    ax.set_xlim(-5200, 5200); ax.set_ylim(-5200 / ASPECT, 5200 / ASPECT); ax.set_aspect("equal"); ax.axis("off")
    north_arrow(ax, 4800, 700, 750, color="white")
    scale_bar(ax, -5000, -2150, 2640, color="white", height=60, label="½ mi")
    out.append(save(fig, f"aerial_{key}_cove.jpg", dpi=300, pil_kwargs={"quality": 90}))
    return out


# =========================================================================== fly-around
FLY = {"bayview": [(150, "from the cove (SE)"), (60, "from the east"), (330, "from the road (NW)"),
                   (240, "from the west")],
       "arrowhead": [(115, "from the cove (ESE)"), (200, "from the south"), (300, "from the road (WNW)"),
                     (25, "from the north")]}


def fly(key):
    from flyaround import Sampler, render
    s = Sampler(key)
    r = T[key]
    ring = [(x * FT2M, y * FT2M) for x, y in r["ring_lf"]]
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    out = []
    for i, (bear, desc) in enumerate(FLY[key], 1):
        a = math.radians(bear)
        D = 235.0
        cam = (D * math.sin(a), D * math.cos(a))
        look = (bear + 180) % 360
        im, _ = render(s, cam, 168.0, (0.0, 0.0), W=1540, Hh=700, fov=60, far=1800.0,
                       overlays=[(ring + [ring[0]], (239, 68, 68, 255), 5)],
                       labels=[((0.0, 0.0), LOTNAME[key], (220, 38, 38, 235))])
        from PIL import ImageDraw, ImageFont
        from flyaround import FONT
        d = ImageDraw.Draw(im, "RGBA")
        f = ImageFont.truetype(FONT, 30)
        txt = f"Fly-around view {i}/4 · {desc} · looking {names[int(((look + 22.5) % 360) // 45)]}"
        d.rounded_rectangle([18, 18, 30 + d.textlength(txt, font=f), 66], radius=10, fill=(15, 23, 42, 190))
        d.text((26, 24), txt, font=f, fill="white")
        f2 = ImageFont.truetype(FONT, 22)
        foot = "USGS 3DEP lidar (true vertical scale) draped with Esri World Imagery · generated view, not a photo"
        d.rounded_rectangle([18, im.height - 52, 30 + d.textlength(foot, font=f2), im.height - 16], radius=8,
                            fill=(255, 255, 255, 200))
        d.text((26, im.height - 48), foot, font=f2, fill=(30, 41, 59))
        p = os.path.join(FIG, f"fly_{key}_{i}.jpg")
        im.save(p, quality=88)
        out.append(p)
    return out


# =========================================================================== locator maps
def _poly_parts(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    return geom["coordinates"]


CITIES = [("Dallas", -96.797, 32.777, True), ("Fort Worth", -97.331, 32.755, False), ("Houston", -95.370, 29.760, True),
          ("Austin", -97.743, 30.267, True), ("San Antonio", -98.494, 29.424, True), ("Waco", -97.147, 31.549, False)]


def texas_mini(key):
    Bd = load("boundaries.json")
    fig = plt.figure(figsize=(2.5, 1.62))
    ax = fig.add_axes([0, 0, 1, 1])
    k = math.cos(math.radians(31.0))
    for part in _poly_parts(Bd["texas"]):
        for ringc in part[:1]:
            a = np.array(ringc)
            ax.fill(a[:, 0] * k, a[:, 1], facecolor="#ecfdf5", edgecolor=PAL["teal"], lw=0.8)
    lon0, lat0 = T[key]["centroid_lonlat"]
    off = {"Dallas": (-0.25, 0.25, "right"), "Houston": (0.25, -0.45, "left"), "Austin": (-0.25, 0.15, "right"),
           "San Antonio": (-0.25, -0.35, "right"), "Waco": (-0.25, -0.05, "right")}
    for name, lo, la, big in CITIES:
        if name not in off:
            continue
        dx, dy, ha = off[name]
        ax.plot(lo * k, la, "o", ms=2.6 if big else 1.8, color=PAL["slate"])
        ax.text(lo * k + dx, la + dy, name, fontsize=4.6 if big else 4.0, color=PAL["slate"], ha=ha)
    dal = [c for c in CITIES if c[0] == "Dallas"][0]
    ax.plot([lon0 * k, dal[1] * k], [lat0, dal[2]], color=PAL["coral"], lw=0.9, ls="--")
    ax.plot(lon0 * k, lat0, marker="*", ms=9, color=PAL["coral"], mec="white", mew=0.5)
    nm = [n for n in SV[key]["named"] if n["name"].startswith("Dallas (downtown)")][0]
    ax.text(lon0 * k + 0.45, lat0 + 0.05, f"{LOTNAME[key]}\n{nm['crow_mi']:.0f} mi SE of Dallas\n"
            f"({nm['drive_mi']:.0f} road mi · {nm['drive_min']:.0f} min)", fontsize=4.6, color=PAL["coral"],
            fontweight="bold", va="center", ha="left", path_effects=HALO)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-106.8 * k, -89.6 * k); ax.set_ylim(25.7, 36.6)
    return save(fig, f"texas_{key}.png", dpi=400)


def region():
    Bd = load("boundaries.json")
    fig = plt.figure(figsize=(4.15, 3.25))
    ax = fig.add_axes([0, 0, 1, 1])
    k = math.cos(math.radians(32.0))
    for c in Bd["counties"]:
        for part in _poly_parts(c["geom"]):
            a = np.array(part[0])
            ax.fill(a[:, 0] * k, a[:, 1], facecolor="#f8fafc", edgecolor="#cbd5e1", lw=0.6, zorder=1)
            if c["name"] in ("Navarro County", "Freestone County"):
                cx_, cy_ = a[:, 0].mean(), a[:, 1].mean()
    for c in Bd["counties"]:
        if c["name"] in ("Navarro County", "Freestone County"):
            a = np.array(_poly_parts(c["geom"])[0][0])
            ax.plot(a[:, 0] * k, a[:, 1], color="#94a3b8", lw=0.9, zorder=2)
    for part in _poly_parts(Bd["rc_lake"]):
        a = np.array(part[0])
        ax.fill(a[:, 0] * k, a[:, 1], facecolor="#93c5fd", edgecolor="#2563eb", lw=0.4, zorder=3)
    for h in Bd["highways"]:
        a = np.array(h["xy"])
        col = "#dc2626" if h["hw"] == "motorway" else ("#f59e0b" if h["hw"] == "trunk" else "#a3a3a3")
        ax.plot(a[:, 0] * k, a[:, 1], color=col, lw=1.1 if h["hw"] != "primary" else 0.6, zorder=4)
    towns = [("Corsicana", -96.469, 32.095), ("Kerens", -96.228, 32.131), ("Fairfield", -96.153, 31.725),
             ("Streetman", -96.326, 31.876), ("Wortham", -96.461, 31.788), ("Mildred", -96.385, 31.977)]
    for n, lo, la in towns:
        ax.plot(lo * k, la, "s", ms=2.6, color="#334155", zorder=6)
        ax.text(lo * k + 0.01, la + 0.012, n, fontsize=5.2, color="#334155", zorder=6, path_effects=HALO)
    for key, lab, dx, dy in (("bayview", "A · 11 Bayview Cir\n(White Rock)", 0.025, 0.015),
                             ("arrowhead", "B · 5001 Arrowhead Pt\n(Rustling Oaks)", -0.02, -0.055)):
        lo, la = T[key]["centroid_lonlat"]
        ax.plot(lo * k, la, marker="*", ms=12, color=PAL["coral"], mec="white", mew=0.7, zorder=8)
        ax.text(lo * k + dx, la + dy, lab, fontsize=5.6, color=PAL["coral"], fontweight="bold", zorder=9,
                ha="left" if dx > 0 else "right", path_effects=HALO)
    ax.text(-96.33 * k, 32.062, "Richland-Chambers\nReservoir (~43,900 ac)", fontsize=5.4, color="#1e3a8a",
            style="italic", ha="center", va="center", zorder=7, path_effects=HALO)
    ax.text(-96.56 * k, 32.03, "NAVARRO CO.", fontsize=5.0, color="#64748b", fontweight="bold", zorder=5)
    ax.text(-96.31 * k, 31.765, "FREESTONE CO.", fontsize=5.0, color="#64748b", fontweight="bold", zorder=5)
    import re as _re
    for pat, lbl, lat_t, lon_t in ((r"\bI ?-?45\b", "I-45", 31.84, None), (r"\bUS ?287\b", "US 287", None, -96.10),
                                   (r"\b(SH|TX) ?31\b", "SH 31", None, -96.33)):
        best = None
        for h in Bd["highways"]:
            if not h["ref"] or not _re.search(pat, h["ref"]):
                continue
            for x, y in h["xy"]:
                dd = abs(y - lat_t) if lat_t is not None else abs(x - lon_t)
                if -96.6 < x < -96.0 and 31.7 < y < 32.18 and (best is None or dd < best[0]):
                    best = (dd, x, y)
        if best:
            ax.text((best[1] + 0.012) * k, best[2] + 0.008, lbl, fontsize=5.0, color="#7f1d1d", fontweight="bold",
                    path_effects=HALO, zorder=7,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#7f1d1d", lw=0.4))
    ax.set_xlim(-96.62 * k, -95.98 * k); ax.set_ylim(31.69, 32.19); ax.set_aspect("equal"); ax.axis("off")
    # scale bar 5 mi
    mi = 1 / 69.17
    x0, y0 = -96.60 * k, 31.705
    ax.plot([x0, x0 + 5 * mi * k / math.cos(math.radians(32.0)) * math.cos(math.radians(32.0))], [y0, y0],
            color="black", lw=2)
    ax.text(x0, y0 + 0.006, "5 mi", fontsize=5)
    ax.annotate("", xy=(-96.0 * k, 32.17), xytext=(-96.0 * k, 32.13),
                arrowprops=dict(arrowstyle="-|>", lw=1.2, color="black"))
    ax.text(-96.0 * k, 32.175, "N", fontsize=6.5, ha="center", fontweight="bold")
    # Texas inset
    ins = fig.add_axes([0.66, 0.02, 0.33, 0.33])
    kt = math.cos(math.radians(31.0))
    for part in _poly_parts(Bd["texas"]):
        a = np.array(part[0])
        ins.fill(a[:, 0] * kt, a[:, 1], facecolor="#ecfdf5", edgecolor=PAL["teal"], lw=0.7)
    for name, lo, la, big in CITIES:
        if big:
            ins.plot(lo * kt, la, "o", ms=1.8, color=PAL["slate"])
            ins.text(lo * kt + 0.3, la + 0.1, name, fontsize=3.8, color=PAL["slate"])
    lo, la = T["bayview"]["centroid_lonlat"]
    ins.plot(lo * kt, la, "*", ms=7, color=PAL["coral"], mec="white", mew=0.4)
    ins.set_aspect("equal"); ins.axis("off")
    ins.set_xlim(-106.8 * kt, -93.4 * kt); ins.set_ylim(25.7, 36.6)
    ins.patch.set_alpha(0)
    return save(fig, "region.png", dpi=350)


if __name__ == "__main__":
    which = sys.argv[1:] or ["plan", "section", "envelope", "terrain3d", "fema", "bathy", "aerial", "fly", "maps"]
    if "maps" in which:
        print(region())
        for key in LOTS:
            print(texas_mini(key))
    for key in LOTS:
        if "fly" in which:
            print(fly(key))
    for key in LOTS:
        if "plan" in which:
            print(plan(key))
        if "section" in which:
            print(section(key))
        if "envelope" in which:
            print(envelope(key))
        if "terrain3d" in which:
            print(terrain3d(key))
        if "fema" in which:
            print(fema(key))
        if "bathy" in which:
            print(bathy(key))
        if "aerial" in which:
            print(aerial_pics(key))
