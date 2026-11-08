"""Assemble the 6-page letter-size PDF.

  page 1  summary of both lots (map, scores, key-measurements table)
  page 2  Lot A facts (small pictures on top)      page 3  Lot A pictures (>= 3.5 in wide)
  page 4  Lot B facts                              page 5  Lot B pictures
  page 6  gardening, documents to obtain, glossary, sources, end note

HTML is generated with every figure embedded, printed by headless Chromium
(Playwright) at 8.5 x 11 in, then checked for page count and overflowing boxes.
Page previews are written to out/preview/.
"""
import asyncio
import base64
import datetime as dt
import io
import os
import statistics
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

from common import ASSETS, FIG, OUT, ROOT, load
from figlib import dem_local

MODEL = "Claude Opus 5.5"
CREATED = dt.date(2026, 11, 8)
STAMP = CREATED.strftime("%d-%b-%y")
PDF_NAME = f"Richland-Chambers-2-Lots-Due-Diligence_{STAMP}_{MODEL.replace(' ', '-')}.pdf"
LAKE_NOW = 312.17           # ft msl, TWDB daily level 8 Nov 2026
POOL, FLOOD100, FLOWAGE = 315.0, 318.0, 320.0

T = load("terrain.json"); P = load("parcels.json"); F = load("flood.json"); S = load("soil.json")
SV = load("services.json"); SN = load("services_named.json"); BA = load("bathymetry.json")
CL = load("climate.json"); CE = load("census.json"); NRI = load("nri.json"); LK = load("lake_levels.json")

# --------------------------------------------------------------------------- helpers
def tag(kind):
    lab = {"OFF": "OFFICIAL", "GIS": "GIS", "EST": "ESTIMATE", "CON": "CONFIRM"}[kind]
    return f'<span class="tag {kind}">{lab}</span>'


OFF, GIS, EST, CON = tag("OFF"), tag("GIS"), tag("EST"), tag("CON")


def money(v, k=False):
    if v is None:
        return "n/a"
    if k:
        return f"${v/1000:,.0f}k" if v < 1e6 else f"${v/1e6:,.2f}M"
    return f"${v:,.0f}"


def dm(r):
    if not r or r.get("drive_mi") is None:
        return "n/a"
    mi = r["drive_mi"]
    return f"{mi:.1f} mi · {r['drive_min']:.0f} min" if mi < 10 else f"{mi:.0f} mi · {r['drive_min']:.0f} min"


def named(key, grp, sub):
    for r in SN[key].get(grp, []):
        if sub.lower() in (r.get("name") or "").lower():
            return r
    return None


def dest(key, sub):
    for r in SV[key]["named"]:
        if sub.lower() in r["name"].lower():
            return r
    return None


def cat(key, label, i=0):
    rows = SV[key].get(label) or []
    return rows[i] if len(rows) > i else None


_IMG_CACHE = {}


def img(path, w_in, fit="contain", dpi=300, crop_white=False, pad_aspect=None, q=86):
    """Embed an image (resized to the print width) as a data URI <img>."""
    k = (path, w_in, crop_white, pad_aspect)
    if k not in _IMG_CACHE:
        im = Image.open(path)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        if crop_white:
            a = np.asarray(im).astype(int)
            mask = (np.abs(a - 255).sum(axis=2) > 30)
            ys, xs = np.nonzero(mask)
            im = im.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), min(xs.max() + 12, im.width),
                          min(ys.max() + 12, im.height)))
        if pad_aspect:
            w, h = im.size
            if w / h < pad_aspect:
                nw = int(h * pad_aspect)
                canvas = Image.new("RGB", (nw, h), "white"); canvas.paste(im, ((nw - w) // 2, 0)); im = canvas
            else:
                nh = int(w / pad_aspect)
                canvas = Image.new("RGB", (w, nh), "white"); canvas.paste(im, (0, (nh - h) // 2)); im = canvas
        W = int(w_in * dpi)
        if im.width > W:
            im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        _IMG_CACHE[k] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return f'<img src="{_IMG_CACHE[k]}" style="object-fit:{fit}">'


def fig(name):
    return os.path.join(FIG, name)


def comps(key, token):
    vals = []
    for p in P[key]["all_parcels"]:
        try:
            imp = float(p.get("imp_value") or 0); land = float(p.get("land_value") or 0)
        except (TypeError, ValueError):
            continue
        if p.get("legal") and token in str(p["legal"]) and imp > 100000:
            vals.append(land + imp)
    return sorted(vals)


def cove_width(key):
    xs, ys, Z = dem_local(key, 450, 1.0)
    water = Z < 313.6
    edt = ndimage.distance_transform_edt(water)
    s = T[key]["section"]; L = s["dist_ft"][-1]
    a = np.array(T[key]["section_lf"][0]); b = np.array(T[key]["section_lf"][1])
    p = a + (b - a) * (s["shore_ft"] / L)
    X, Y = np.meshgrid(xs, ys)
    near = (np.hypot(X - p[0], Y - p[1]) < 120) & water
    return round(2 * float(edt[near].max()), -1) if near.any() else None


def card_dir(az):
    return ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][
        int(((az + 11.25) % 360) // 22.5)]


# --------------------------------------------------------------------------- facts per lot
TAX_A = [("Navarro County", 0.35), ("Navarro College", 0.1077), ("Flood Control", 0.0054), ("Road & Bridge", 0.0691),
         ("Mildred ISD", 1.0408)]
TAX_B = [("Fairfield Hospital Dist.", 0.25), ("Navarro County", 0.35), ("Navarro College", 0.1077),
         ("Flood Control", 0.0054), ("Road & Bridge", 0.0691), ("Fairfield ISD", 0.9295)]

LOT = {
    "bayview": dict(
        L="A", name="11 Bayview Cir", city="Corsicana, TX 75109", acc="#0f766e", acc2="#14b8a6",
        grad="linear-gradient(95deg,#115e59,#0f766e 45%,#0d9488)",
        sub="White Rock Sub. (W0305) Lot 11 · Navarro County · gated community off US-287",
        parcel="63254", geo="W0305-00-00110-000-00-0", legal="W0305 WHITE ROCK SUB LOT 11 .65 ACRES",
        owner="Jason Hamad (Dallas) · warranty deed 15 Jul 2022, Vol 2022 p 7656",
        price=89900, price_txt="$89,900", price_src="MLS 21146775 · RE/MAX LakeSide Dreams (Teel) · LakeHouse.com ad 7100373, Nov 2026",
        acres=0.65, cad=88808, cad_land=85197, cad_imp=3611, cad_imp_txt="steel retaining wall (bulkhead)",
        hist={2022: 56630, 2023: 81400, 2024: 86160, 2025: 90550, 2026: 88808}, taxable=88808, rates=TAX_A,
        listing="on portals since ≥Dec 2022; current listing since 8 Jan 2026 (304 days): long time on market",
        links=[("LakeHouse", "https://www.lakehouse.com/lot-11-bayview-circle-corsicana-texas-75109-p7100373.html"),
               ("Zillow", "https://www.zillow.com/homedetails/11-Bayview-Cir-Corsicana-TX-75109/2106781179_zpid/"),
               ("Realtor.com", "https://www.realtor.com/realestateandhomes-detail/11-Bayview-Cir_Corsicana_TX_75109_M91110-26519"),
               ("Redfin", "https://www.redfin.com/TX/Corsicana/11-Bayview-Cir-75109/home/171532147")],
        isd="Mildred ISD", isd_grade="B", water="M.E.N. WSC (TX1750015)", subdiv_token="WHITE ROCK SUB",
        score=[("Price vs appraisal", 1.5, 1.3, "asking $89.9k = CAD $88.8k + 1%"),
               ("Value trend", 1.0, 0.9, "CAD value +57% since 2022"),
               ("Water frontage & use", 1.5, 1.0, "158 ft, bulkheaded, protected; cove only 8–10 ft deep"),
               ("Buildability", 1.5, 1.1, "pad 4–5 ft above flood proxy; clay; 12.5% max grade in envelope"),
               ("Utilities", 1.0, 1.0, "public water + HOA sewer: no septic"),
               ("HOA / holding cost", 1.0, 0.4, "dues $3,530/yr (sewer incl.) + $1.4k tax; 2,500 sf minimum"),
               ("Location & access", 1.0, 0.7, "on US-287: 27 min Corsicana, 84 min Dallas"),
               ("Liquidity / exit", 1.0, 0.5, "marketed on and off since 2022; 304 days on this listing"),
               ("Risk", 0.5, 0.3, "13% in Zone A; cove shallow in droughts; expansive clay")],
    ),
    "arrowhead": dict(
        L="B", name="5001 Arrowhead Pt", city="Streetman, TX 75859", acc="#6d28d9", acc2="#8b5cf6",
        grad="linear-gradient(95deg,#4c1d95,#6d28d9 45%,#7c3aed)",
        sub="Rustling Oaks Estates Ph II (R1550.02) Blk 1 Lot 33 · Navarro County · south shore",
        parcel="56587", geo="R1550-02-00010-033-00-0",
        legal="R1550.02 RUSTLING OAKS ESTATES PHASE II BLK 1 LOT 33 .5 ACRES",
        owner="Danny & Leanna Pitts (own the adjoining home, 5003) · deed 10 Apr 2015, Vol 2015 p 2509",
        price=99900, price_txt="$99,900", price_src="MLS 21298338 · Laura Smith, Keller Williams · LakeHouse.com ad 7885360, Nov 2026",
        acres=0.50, cad=68849, cad_land=65340, cad_imp=3509, cad_imp_txt="steel retaining wall",
        hist={2022: 43560, 2023: 47920, 2024: 47640, 2025: 47330, 2026: 68849}, taxable=56796, rates=TAX_B,
        listing="active since 15 Jun 2026 (145 days): 100+ ft lake frontage on a private cul-de-sac",
        links=[("LakeHouse", "https://www.lakehouse.com/5001-arrowhead-point-streetman-texas-75859-p7885360.html"),
               ("Realtor.com", "https://www.realtor.com/realestateandhomes-detail/5001-Arrowhead-Pt_Streetman_TX_75859_M88948-88255"),
               ("Zillow search", "https://www.zillow.com/homes/5001-Arrowhead-Pt-Streetman,-TX-75859_rb/"),
               ("HAR", "https://www.har.com/search/dosearch?quicksearch=5001%20Arrowhead%20Pt%20Streetman")],
        isd="Fairfield ISD", isd_grade="C", water="Winkler WSC (TX1750023)", subdiv_token="RUSTLING OAKS",
        score=[("Price vs appraisal", 1.5, 0.7, "asking $99.9k = 45% over CAD $68.8k"),
               ("Value trend", 1.0, 0.7, "CAD land +50% in one year (2026)"),
               ("Water frontage & use", 1.5, 0.9, "115 ft, steel wall, POA ramp & pier; cove 7–8.5 ft deep"),
               ("Buildability", 1.5, 1.2, "gentle house area (5%), 99.8% above 320 ft; clay"),
               ("Utilities", 1.0, 0.6, "public water; aerobic septic + drip required"),
               ("HOA / holding cost", 1.0, 0.7, "POA $144–644/yr, strict ACC rules, no poultry"),
               ("Location & access", 1.0, 0.5, "rural: 15 min store, 42 min Corsicana, 99 min Dallas"),
               ("Liquidity / exit", 1.0, 0.6, "fresh listing; priced above peers' land values"),
               ("Risk", 0.5, 0.4, "2.5% Zone A; cove shallow in droughts; expansive clay")],
    ),
}
for k, d in LOT.items():
    d["total"] = round(sum(x[2] for x in d["score"]), 1)
    d["tax_rate"] = sum(r for _, r in d["rates"])
    d["tax_now"] = d["taxable"] * d["tax_rate"] / 100
    d["tax_full"] = d["cad"] * d["tax_rate"] / 100
    d["comps"] = comps(k, d["subdiv_token"])
    d["cove_w"] = cove_width(k)
    lf = T[k]["frontage_lake_ft"]
    d["dock_sf"] = round(8 * min(lf, 150) + 4 * max(0, min(lf, 250) - 150))
    t = T[k]
    za = t["zoneA_edge_elev_ft"]["median"]
    d["bfe_proxy"] = max(FLOOD100, za)
    d["ffe_min"] = d["bfe_proxy"] + 2.0
    d["pad"] = t["fits"]["two-storey 5BR 60x46 ft + garage (2,760 sf)"]


# --------------------------------------------------------------------------- CSS
CSS = r"""
@page { size: 8.5in 11in; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Noto Sans", "DJV", sans-serif; color: #0f172a; font-size: 6.1pt; line-height: 1.16;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
a { color: inherit; }
.page { width: 8.5in; height: 11in; padding: 0.24in 0.34in 0.2in; position: relative; overflow: hidden;
        page-break-after: always; break-after: page; display: flex; flex-direction: column; background: #fff; }
.page:last-child { page-break-after: auto; break-after: auto; }
.band { border-radius: 8px; color: #fff; padding: 5px 9px; display: flex; justify-content: space-between;
        align-items: center; flex: none; gap: 8px; }
.band h1 { font-size: 14pt; margin: 0; line-height: 1.05; letter-spacing: .1px; }
.band .sub { font-size: 6.9pt; margin-top: 2px; opacity: .96; }
.kpis { display: flex; gap: 4px; align-items: center; }
.kpi { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.35); border-radius: 6px;
       padding: 2px 6px; text-align: center; }
.kpi b { display: block; font-size: 10.5pt; line-height: 1.1; white-space: nowrap; }
.kpi span { font-size: 5.6pt; opacity: .95; white-space: nowrap; }
.score { background: #fff; border-radius: 50%; width: 0.6in; height: 0.6in; display: flex; flex-direction: column;
         align-items: center; justify-content: center; font-weight: 800; flex: none; }
.score b { font-size: 15pt; line-height: 1; } .score span { font-size: 5.5pt; color: #475569; }
.strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin: 5px 0 3px; flex: none; }
.strip figure { margin: 0; height: 1.02in; position: relative; border-radius: 6px; overflow: hidden;
                border: 1px solid #cbd5e1; background: #f8fafc; }
.strip img { width: 100%; height: 100%; display: block; }
.strip figcaption { position: absolute; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,.76); color: #fff;
                    font-size: 5.2pt; padding: 1px 4px; line-height: 1.15; }
.legend { font-size: 5.5pt; color: #475569; margin: 0 0 3px; flex: none; }
.cols { flex: 1 1 auto; position: relative; min-height: 0; }
.flow { position: absolute; inset: 0; column-count: 3; column-gap: 6px; column-fill: auto; }
.flow .box { break-inside: auto; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.flow .box h3 { break-after: avoid; }
.flow tr, .flow li, .flow p { break-inside: avoid; }
.box { border: 1px solid #e2e8f0; border-left: 3px solid var(--acc); border-radius: 5px; padding: 2px 4px 3px;
       margin-bottom: 3.5px; background: #fff; }
.box h3 { margin: 0 0 1.5px; font-size: 7pt; color: var(--acc); display: flex; justify-content: space-between;
          align-items: baseline; }
.box h3 small { font-size: 5.3pt; color: #64748b; font-weight: 400; }
.box p { margin: 1px 0; }
.box ul { margin: 1px 0 0 9px; padding: 0; } .box li { margin: 0.4px 0; }
table.kv { width: 100%; border-collapse: collapse; }
table.kv td { padding: 0.35px 1.5px; vertical-align: top; border-bottom: 0.5px dotted #e2e8f0; }
table.kv td.k { color: #475569; white-space: nowrap; padding-right: 3px; width: 1%; }
table.mini { width: 100%; border-collapse: collapse; font-size: 5.7pt; }
table.mini td, table.mini th { padding: 0.3px 2px; border-bottom: 0.5px solid #f1f5f9; text-align: left;
                               vertical-align: top; }
table.mini th { color: #475569; font-weight: 600; }
.tag { display: inline-block; font-size: 4.7pt; font-weight: 700; padding: 0 2px; border-radius: 3px;
       vertical-align: 0.6pt; letter-spacing: .15px; }
.OFF { background: #dcfce7; color: #166534; } .GIS { background: #dbeafe; color: #1e40af; }
.EST { background: #fef3c7; color: #92400e; } .CON { background: #fee2e2; color: #991b1b; }
.g { color: #15803d; font-weight: 700; } .w { color: #b45309; font-weight: 700; } .r { color: #b91c1c; font-weight: 700; }
.foot { flex: none; font-size: 5.3pt; color: #64748b; display: flex; justify-content: space-between;
        border-top: 1px solid #e2e8f0; padding-top: 2px; margin-top: 2px; }
.bar { height: 4px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--acc); }
/* picture pages */
.pgrid { flex: 1 1 auto; display: grid; grid-template-columns: 1fr 1fr; column-gap: 6px; row-gap: 2px;
         align-content: start; margin-top: 5px; }
.pf { margin: 0; }
.pf .fr { height: 1.72in; border: 1px solid #cbd5e1; border-radius: 5px; overflow: hidden; background: #fff; }
.pf.full { grid-column: 1 / span 2; } .pf.full .fr { height: 2.03in; }
.pf img { width: 100%; height: 100%; display: block; }
.pf figcaption { font-size: 5.4pt; color: #334155; padding: 1px 2px 0; line-height: 1.17; height: 0.155in;
                 overflow: hidden; }
.pf figcaption b { color: var(--acc); }
/* summary */
.srow { display: grid; grid-template-columns: 3.86in 1fr; gap: 7px; margin: 6px 0 5px; flex: none; }
.smap { margin: 0; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; height: 3.36in; }
.smap img { width: 100%; height: 100%; display: block; }
.card { border-radius: 7px; border: 1px solid #e2e8f0; border-top: 4px solid var(--acc); padding: 4px 6px;
        margin-bottom: 5px; background: linear-gradient(180deg, var(--tint), #fff 60%); }
.card .ch { display: flex; gap: 7px; align-items: center; }
.card .score { border: 3px solid var(--acc); color: var(--acc); width: 0.62in; height: 0.62in; }
.card h2 { font-size: 9.2pt; margin: 0; color: var(--acc); }
.card .cs { font-size: 6.1pt; color: #334155; }
.card p { margin: 3px 0 2px; font-size: 6.3pt; }
table.cmp { width: 100%; border-collapse: collapse; font-size: 6.15pt; flex: none; }
table.cmp th { color: #fff; padding: 2px 4px; text-align: left; font-size: 6.6pt; }
table.cmp td { padding: 0.9px 4px; border-bottom: 0.5px solid #e2e8f0; vertical-align: top; }
table.cmp td:first-child { color: #334155; font-weight: 600; white-space: nowrap; width: 1.32in; }
table.cmp tr:nth-child(even) td { background: #f8fafc; }
table.cmp tr.grp td { background: #eef2ff; color: #1e3a8a; font-weight: 700; padding-top: 1.5px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.end h3 { margin: 0 0 2px; }
"""


# --------------------------------------------------------------------------- pieces
def foot(page_no, total=6):
    return (f'<div class="foot"><span>Richland-Chambers lots · 11 Bayview Cir (A) & 5001 Arrowhead Pt (B) · '
            f'desk screening from public records, not a survey or appraisal</span>'
            f'<span>created {CREATED:%d %b %Y} · {MODEL} · p {page_no}/{total}</span></div>')


def box(title, body, note=""):
    n = f"<small>{note}</small>" if note else ""
    return f'<div class="box"><h3><span>{title}</span>{n}</h3>{body}</div>'


def kv(rows):
    return '<table class="kv">' + "".join(f'<tr><td class="k">{a}</td><td>{b}</td></tr>' for a, b in rows) + "</table>"


def soil_desc(key):
    s = S[key]
    mus = {m["mukey"]: m for m in s["mapunits"]}
    share = s["share_pct"]
    parts = [f"{mus[m]['musym']} {mus[m]['muname']} ({share.get(m, 0):.0f}%)" for m in sorted(share, key=lambda x: -share[x])]
    return "; ".join(parts)


# --------------------------------------------------------------------------- lot page 1
def lot_page1(key, page_no):
    d = LOT[key]; t = T[key]; e = t["elev"]; sl = t["slope"]; s = t["section"]; pad = d["pad"]
    fl = F[key]; pan = fl["panel"][0]
    cw = d["cove_w"]
    b150 = BA[key].get("within_150ft") or BA[key].get("within_300ft")
    brad = "150" if BA[key].get("within_150ft") else "300"
    lake = BA["lake"]
    c = CL[key]
    cmin, cmax = (min(d["comps"]), max(d["comps"])) if d["comps"] else (None, None)
    cmed = statistics.median(d["comps"]) if d["comps"] else None
    pct_above320 = 100 * e["area_above_320_sqft"] / (e["area_above_320_sqft"] + e["area_below_320_sqft"])
    hist = d["hist"]
    road_edges = [x for x in t["edges"] if x["kind"] == "road"]
    side_edges = [x for x in t["edges"] if x["kind"] == "side"]
    corners = t["corners"]
    corner_html = '<table class="mini"><tr>' + "".join(
        f'<td>P{i+1} {cc["lonlat"][1]:.6f}, {cc["lonlat"][0]:.6f}</td>' + ("</tr><tr>" if i % 2 == 1 else "")
        for i, cc in enumerate(corners)) + "</tr></table>"
    is_a = key == "bayview"

    # ---------------- strip
    if is_a:
        strip = [(img(fig("listing_bayview_hero.jpg"), 1.92, "cover"),
                  "Listing photo: lot 11 and the main lake · LakeHouse.com / RE/MAX"),
                 (img(fig("aerial_bayview_lot.jpg"), 1.92, "cover"), "Lot outline on Esri imagery (Nov 2025)"),
                 (img(fig("fly_bayview_2.jpg"), 1.92, "cover"), "Fly-around view from the east (lidar 3-D)"),
                 (img(fig("texas_bayview.png"), 1.92, "contain"), "Texas location · 63 mi SE of Dallas")]
    else:
        strip = [(img(fig("listing_arrowhead_hero.jpg"), 1.92, "cover"),
                  "Listing photo: the cove from the lot · LakeHouse.com / NTREIS"),
                 (img(fig("aerial_arrowhead_lot.jpg"), 1.92, "cover"), "Lot outline on Esri imagery (May 2025)"),
                 (img(fig("fly_arrowhead_2.jpg"), 1.92, "cover"), "Fly-around view from the south (lidar 3-D)"),
                 (img(fig("texas_arrowhead.png"), 1.92, "contain"), "Texas location · 65 mi SE of Dallas")]
    strip_html = '<div class="strip">' + "".join(
        f'<figure>{im}<figcaption>{cap}</figcaption></figure>' for im, cap in strip) + "</div>"

    # ---------------- column 1
    sides = " / ".join("%.0f" % x["len_ft"] for x in side_edges)
    dims = f"road {t['frontage_road_ft']:.0f} ft · lake {t['frontage_lake_ft']:.0f} ft · sides {sides} ft"
    ident = kv([
        ("Address", f"{d['name']}, {d['city']} {OFF}"),
        ("Legal", f"{d['legal']} {OFF}"),
        ("CAD parcel", f"ID {d['parcel']} · Geo {d['geo']}"),
        ("Owner / deed", d["owner"]),
        ("Lot size", f"<b>{d['acres']:.2f} ac</b> legal ({d['acres']*43560:,.0f} sf) · GIS {t['lot_area_gis_sqft']/43560:.3f} ac "
                     f"({t['lot_area_gis_sqft']:,.0f} sf) {GIS}"),
        ("Dimensions", dims + f" {GIS}"),
        ("Asking", f"<b>{d['price_txt']}</b> · {money(d['price']/d['acres'])}/ac · "
                   f"{money(d['price']/t['frontage_lake_ft'])}/lake-ft <br><i>{d['price_src']}</i>"),
        ("CAD 2026", f"<b>{money(d['cad'])}</b> (land {money(d['cad_land'])} + {d['cad_imp_txt']} "
                     f"{money(d['cad_imp'])}) {OFF}"),
        ("Value history", " → ".join(f"{y}: {money(v, True)}" for y, v in hist.items())),
        ("Property tax", f"{d['tax_rate']:.4f}% → <b>{money(d['tax_full'])}/yr</b> on full value"
                         + (f" (now {money(d['tax_now'])}: 20% circuit-breaker cap, resets on sale)" if d['taxable'] < d['cad'] else "")),
        ("Listing history", d["listing"]),
        ("Links", " · ".join(f'<a href="{u}">{n}</a>' for n, u in d["links"])),
    ])
    col1 = box("1 · Identification, listing & value", ident)
    col1 += box("2 · Plat, GIS boundary & corners",
                f"<p>Recorded plat is not online (Navarro County Clerk) {CON}. Boundary = Navarro CAD GIS parcel "
                f"(TxGIO StratMap 2026) {GIS}; GIS area is {100*(t['lot_area_gis_sqft']/(d['acres']*43560)-1):+.0f}% vs "
                f"the legal acreage. "
                + ("Listing's “~158 ft platted water frontage” matches GIS 158 ft." if is_a else
                   "Listing's “100+ ft frontage” matches GIS 115 ft.")
                + f" Neighbours: {', '.join(sorted({(n['legal'] or '').split(' SUB ')[-1].split(' ESTATES ')[-1].replace('PHASE II ', '').title()[:22] for n in P[key]['neighbours'] if n.get('legal') and n['legal'] != 'Null'}))}.</p>"
                + corner_html, "lat, lon (NAD83)")
    col1 += box("3 · Terrain, slope & grading", kv([
        ("Ground", f"low <b>{e['min_land_ft']:.1f}</b> · high <b>{e['max_ft']:.1f}</b> · mean {e['mean_ft']:.1f} ft "
                   f"(NAVD88 ≈ msl) {GIS}"),
        ("Relief", f"{e['relief_ft']:.1f} ft · {pct_above320:.0f}% of the lot is above the 320 ft TRWD line"),
        ("vs lake", f"house pad ≈{pad['pad_level_ft']:.0f} ft = {pad['pad_level_ft']-POOL:.0f} ft above full pool, "
                    f"{pad['pad_level_ft']-LAKE_NOW:.0f} ft above today's lake"),
        ("Average slope", f"{sl['mean_pct']:.1f}% ({sl['mean_deg']:.1f}°) whole lot · {sl['env_mean_pct']:.1f}% in the "
                          f"building area"),
        ("Max 50-ft run", f"<b>{sl['max50_pct']:.0f}% ({sl['max50_deg']:.1f}°)</b> anywhere (lake bank) · "
                          f"{sl['env_max50_pct']:.1f}% in building area"),
        ("Road → lake", f"{s['road_to_pool_ft']:.0f} ft to the 315 ft shoreline · fall {s['relief_to_pool_ft']:.1f} ft · "
                        f"direct angle <b>{s['direct_angle_deg']:.1f}°</b> ({s['avg_grade_pct']:.1f}%)"),
        ("At the lake", f"last 20 ft rise {s['bank20_deg']:.1f}° ({s['bank20_pct']:.0f}%) · steepest 10 ft "
                        f"{s['steep10_deg']:.0f}° (bulkhead/bank)"),
        ("Drainage", f"sheet flow to the {card_dir(sl['drain_az_deg'])} into the cove; no channel crosses the lot"),
        ("Class", f"<b>{sl['class']}</b> overall; {'gentle-to-moderate' if sl['env_mean_pct'] < 6 else 'moderate'} "
                  f"where the house goes"),
        ("Grading", f"{sl['grading']} · 60×46 ft pad: ground {pad['ground_min_ft']:.1f}–{pad['ground_max_ft']:.1f} ft, "
                    f"≈{pad['cut_cy']} cy cut / {pad['fill_cy']} cy fill (balanced) {EST}"),
    ]))

    # ---------------- column 2
    za = t["zoneA_edge_elev_ft"]
    col2 = box("5 · Flood zone, BFE & finished floor", kv([
        ("FEMA zone", f"<b>Zone X</b> (minimal) on {100-t['zoneA_pct_of_lot']:.0f}% · <b>Zone A</b> (1%/yr, no BFE) on "
                      f"{t['zoneA_pct_of_lot']:.0f}% along the shore {OFF}"),
        ("FIRM panel", f"{pan['FIRM_PAN']}, effective 5 Jun 2012 · no LOMR/LOMA on file {OFF}"),
        ("BFE", f"none published for Zone A {OFF} · TRWD 100-yr lake level 318.0 ft; flowage easement to 320.0 ft {OFF}"),
        ("Zone A edge", f"lies on ground {za['p25']:.1f}–{za['p75']:.1f} ft (median {za['median']:.1f}) {GIS}"),
        ("Min floor", f"{d['bfe_proxy']:.1f} ft (proxy BFE) + 2 ft freeboard = <b>{d['ffe_min']:.1f} ft</b> {EST} · "
                      f"county freeboard rule not published {CON}"),
        ("Verdict", f"<span class='g'>Terrain adequate</span>: pad ≈{pad['pad_level_ft']:.0f} ft is "
                    f"{pad['pad_level_ft']-d['ffe_min']:.1f} ft above that → no fill, no elevated house; slab, "
                    f"pier-and-beam or crawlspace all allowed outside Zone A. No work below 320 ft without a TRWD "
                    f"permit."),
        ("First Street", f"not retrieved (site blocks automated access) {CON}"),
        ("Elev. cert.", f"none on file {CON}"),
    ]))
    sm = S[key]
    hz = [h for h in sm["horizons"] if h["cokey"] == sm["components"][0]["cokey"]] or sm["horizons"]

    def _num(h):
        out = {}
        for kk, vv in h.items():
            try:
                out[kk] = float(vv)
            except (TypeError, ValueError):
                out[kk] = vv
        return out
    hz = [_num(h) for h in hz]
    top = hz[0]; sub_ = hz[1]
    rest = sm["restrictions"][0] if sm["restrictions"] else None
    col2 += box("6 · Soil & foundation (USDA NRCS SSURGO)", kv([
        ("Map units", f"{soil_desc(key)} {OFF}"),
        ("Profile", f"{top['hzdepb_r']/2.54:.0f} in sandy loam (pH {top['ph1to1h2o_r']}, OM {top['om_r']}%) over "
                    f"<b>{sub_['claytotal_r']:.0f}% clay</b> to {hz[-1]['hzdepb_r']/2.54:.0f}+ in"
                    + (f"; dense clay-loam ‘bedrock’ at {float(rest['resdept_r'])/2.54:.0f} in" if rest else "")),
        ("Shrink-swell", f"<span class='r'>high</span> (LEP {sub_['lep_r']}% in the clay) · permeability very slow "
                         f"(Ksat {sub_['ksat_r']} µm/s) · moderately well drained · HSG C · no water table < 6.5 ft"),
        ("NRCS ratings", "dwellings <span class='r'>very limited</span> (shrink-swell) · septic fields very limited · "
                         "shallow excavation somewhat limited · steel corrosion high"),
        ("Foundation", f"engineered post-tensioned slab, or pier-and-beam on drilled piers below the active clay zone; "
                       f"no basement; stepped slab/stem wall where the pad falls >2 ft · <b>geotechnical report "
                       f"required</b> {CON}"),
    ]))
    if is_a:
        sep_rows = [
            ("Sewer", f"<b class='g'>available</b>: White Rock HOA's private sanitary plant (HOA-owned Lot C, ‘Sanitary "
                      f"Plant & Reserve Area’, 0.58 ac) {OFF}; included in HOA dues (listing) · no septic needed · "
                      f"tap fee {CON}"),
            ("If no sewer", f"TRWD zone allows only an aerobic unit + subsurface drip (spray banned); drip area "
                            f"≈{t['drip']['area_sqft']:,} sf vs 3,600 sf needed for 5 BR (360 gpd ÷ 0.10 gal/sf/day, "
                            f"clay) → soil/area would allow <b>5–6 BR</b> {EST}"),
        ]
    else:
        sep_rows = [
            ("Sewer", f"<b class='r'>none</b>: septic (OSSF) required (subdivision listings) {OFF}"),
            ("System", f"clay = TCEQ Class IV → no trenches; <b>aerobic unit + subsurface drip</b> (TRWD bans spray "
                       f"near the lake); RS/PE design, TRWD permit $400, quarterly maintenance {OFF} · TRWD's 1-ac "
                       f"minimum applies only to post-2011 plats"),
            ("Bedrooms", f"drip field ≥50 ft from the pool, ≥5 ft from lines/house: ≈{t['drip']['area_sqft']:,} sf vs "
                         f"<b>3,600 sf for 5 BR</b> (360 gpd), 4,200 sf for 6 BR → <b>5–6 BR fit</b> {EST} · site "
                         f"evaluation {CON}"),
        ]
    sep_rows.append(("Water well", "only if public water failed: USGS-logged wells nearby are 16–342 ft deep (Wilcox "
                                   "Group). Shallow wells (<100 ft) are surface-influenced and often iron-rich; "
                                   "<b>target ≈250–350 ft</b>, sealed casing, ≥100 ft from a drip field; test for "
                                   f"bacteria, iron, TDS {EST}"))
    col2 += box("7 · Sewer, septic & water quality", kv(sep_rows))
    if is_a:
        util = [("Water", f"{d['water']} service area {OFF} · listing: utilities in place"),
                ("Sewer", "White Rock HOA plant (see 7)"),
                ("Electric", f"Navarro County Electric Co-op (903-874-7411; Oncor overlaps) {OFF} · service at the street "
                             f"per listing {CON}"),
                ("Gas", "no natural-gas main found → propane (W & J Propane yard 0.2 mi away on CR 3190)"),
                ("Internet", "5G/fixed wireless (AT&T Internet Air, T-Mobile, Nextlink), Starlink (≤~400 Mbps), "
                             f"HughesNet; cable/fiber (Vyve, Vero, Rise) mainly inside Corsicana {CON}")]
    else:
        util = [("Water", f"{d['water']} service area {OFF} · tap fee {CON}"),
                ("Sewer", "none — septic (see 7)"),
                ("Electric", f"Navarro County Electric Co-op {OFF} · neighbours served; short extension {CON}"),
                ("Gas", "no natural-gas main → propane"),
                ("Internet", "5G/fixed wireless (AT&T Internet Air, T-Mobile, Nextlink), Starlink, HughesNet; "
                             f"Windstream Kinetic in parts of Streetman {CON}")]
    col2 += box("8 · Utilities", kv(util))

    # ---------------- column 3
    if is_a:
        hoa = [("HOA", f"White Rock Homeowners Assoc. Inc. — gated; owns common area Lot A (1.2 ac) and the sewer plant "
                       f"{OFF}. Dues <b>$3,530/yr</b>, private sewer included (MLS listing) {CON}; transfer fee and "
                       f"special assessments not published"),
               ("Restrictions", "site-built only, ≥2,500 sf heated & cooled, ≥60% stone & glass exterior (listing) · "
                                f"full CC&Rs not online {CON}")]
    else:
        hoa = [("POA", f"Rustling Oaks Estates POA, mandatory: <b>$12/month</b> ($144/yr) in the POA handbook {OFF}; "
                       f"the MLS flyer says <b>$644/yr</b> {CON} · ACC approves all "
                       f"building; $500 road fee + $0.85/sf of slab; pool $1,000; boathouse $750 · amenities: entrance, "
                       f"boat ramp, dock & pier, picnic area"),
               ("Rules", "≥1,600 sf heated on waterfront; RVs temporary only; shed ≤12×16 ft, no metal buildings; "
                         "no screening fences; no firearms; no ‘for sale’ signs on vacant lots")]
    hoa += [
        ("Zoning", f"Navarro Co. Richland-Chambers Lakeshore Zoning (≤5,000 ft from shore) {OFF}; district map not "
                   f"online — likely <b>SF-3</b>: front 35 / rear 15 / side 10 ft, ≤40% coverage, ≤2½ storeys {CON} · "
                   f"permit $0.25/sf + 3 third-party inspections"),
        ("In-law suite", "county allows an accessory dwelling ≤40% of the main house's floor area (no plumbing until "
                         "the house is occupied); a duplex is not allowed in SF districts"
                         + (" · HOA approval" if is_a else " · ACC: outbuildings only after the house slab")),
        ("Animals", "county: ≤4 dogs/cats; poultry/livestock count as ‘farm or ranch’ use (≥3 ac)"
                    + (" → not on this lot" if is_a else " · POA bans fowl, goats, hogs, sheep, horses, cattle")),
        ("STR", f"county lists only owner-occupied B&B (1 room; 2–4 by SUP); whole-house rentals not addressed "
                f"{CON}; 6% state hotel tax for stays <30 days"),
    ]
    col3 = box("9 · HOA, zoning, in-law suite, animals, STR", kv(hoa))
    lk_rows = [
        ("Frontage", f"direct, {t['frontage_lake_ft']:.0f} ft on a cove ≈{cw:.0f} ft wide {GIS}"
                     + (" · existing steel bulkhead with step-down walk (listing, CAD)" if is_a else
                        " · existing steel retaining wall (CAD)")),
        ("Dock", f"TRWD permit ($300): max <b>{d['dock_sf']:,} sf</b> (8 sf/ft of shoreline); ≥5 ft from side lines "
                 f"(20 ft if >1,200 sf); ≤2 storeys; no toilets or living space; lower deck ≥18 in above the 320 ft "
                 f"flowage line {OFF}"),
        ("Depth", f"{b150['mean_depth_ft']:.0f} ft mean / {b150['max_depth_ft']:.0f} ft max at full pool within "
                  f"{brad} ft (TWDB 2018) {OFF} · ≈{b150['mean_depth_ft']-(POOL-LAKE_NOW):.0f} ft today · the 2006 low "
                  f"(303.6 ft) would leave the cove dry"),
        ("Lake level", f"since 2000: mean {LK['mean_since_2000']:.1f} ft; below 312 ft {LK['pct_days_below_312_since_2000']:.0f}% "
                       f"of days; high May–Jun, low Nov–Dec · now {LAKE_NOW} ft (89% full)"),
        ("Boating", "all craft incl. ski/wake boats; 200 ft safe distance for towed sports (TRWD 2026)"
                    + (" · Oak Cove Marina 0.2 mi" if is_a else " · POA ramp & pier in the subdivision")),
        ("Fishing", "blue catfish (excellent), hybrid striped & white bass, largemouth, crappie; hybrids stocked "
                    "10–14/ac/yr (TPWD) · licence required · bag: catfish 25, white bass 25 (10 in), hybrid 5 (18 in), "
                    "bass 5 (14 in), crappie 25 (10 in) · fishing from own dock/shore allowed"),
    ]
    col1 += box("4 · Lake, dock, boating & fishing", kv(lk_rows))
    if is_a:
        loc = [("Schools", f"Mildred ISD (TEA <b>B</b> 2026): Mildred Elementary {dm(named(key,'schools_bayview','Mildred'))}"),
               ("Hospital", f"Navarro Regional (ER) {dm(named(key,'hospitals','Navarro'))} · Level-I trauma Baylor Dallas "
                            f"{dm(dest(key,'Baylor'))} · urgent care {dm(named(key,'urgent','Integrity'))}"),
               ("Shopping", f"store & gas at the gate 0.1 mi · H-E-B {dm(named(key,'indian','zz') or cat(key,'heb_byname'))} · "
                            f"Walmart {dm(cat(key,'walmart_byname'))} · Home Depot {dm(cat(key,'home_depot_byname'))}"),
               ("Indian", f"Food Belly (Indian), Corsicana ~27 min · Patel Bros / India Bazaar Irving "
                          f"{dm(named(key,'indian','Patel'))} · DFW Hindu Temple {dm(named(key,'indian','DFW Hindu'))} · "
                          f"Islamic Center of Waco {dm(named(key,'indian','Waco'))}")]
    else:
        loc = [("Schools", f"Fairfield ISD (TEA <b>C</b> 2026): elementary {dm(named(key,'schools_arrowhead','Elementary'))}, "
                           f"high school {dm(named(key,'schools_arrowhead','High'))}"),
               ("Hospital", f"Freestone Medical Center (ER) {dm(named(key,'hospitals','Freestone'))} · Navarro Regional "
                            f"{dm(named(key,'hospitals','Navarro'))} · Baylor Dallas {dm(dest(key,'Baylor'))}"),
               ("Shopping", f"Winkler store/gas/cafe {dm(cat(key,'gas'))} · bank {dm(cat(key,'bank'))} · H-E-B "
                            f"{dm(cat(key,'heb_byname'))} · Walmart {dm(cat(key,'walmart_byname'))}"),
               ("Indian", f"Food Belly (Indian), Corsicana ~42 min · Patel Bros Irving {dm(named(key,'indian','Patel'))} · "
                          f"DFW Hindu Temple {dm(named(key,'indian','DFW Hindu'))} · Islamic Center of Waco "
                          f"{dm(named(key,'indian','Waco'))}")]
    g = CE["geos"]; nav = g["05000US48349"]; tr = g["14000US48349970701"]
    loc += [
        ("Airport", f"DFW {dm(dest(key,'DFW'))} (AA hub, 200+ nonstops) · Love Field {dm(dest(key,'Love'))}"),
        ("Getting out", f"Corsicana {dm(dest(key,'Corsicana'))} · Dallas {dm(dest(key,'Dallas (downtown)'))} · car "
                        "needed" + (" (store, gas, grill ≤0.2 mi)" if is_a else " (store 5.8 mi)")),
        ("People", f"Navarro Co. 57,181 (2025, +8.6% since 2020); income {money(nav['mhi'])} (TX {money(78476)}); "
                   f"tract median age {tr['median_age']:.0f}, {100*tr['age65p']/tr['pop']:.0f}% 65+; Asian Indian 74 "
                   f"in county (0.1%) {OFF}"),
        ("Climate", f"mean {c['mean_annual_c']} °C · Jul–Aug highs {c['jul_aug_high_c']} °C · Jan lows {c['jan_low_c']} °C · "
                    f"extremes {c['record_high_c']}/{c['record_low_c']} °C · {c['annual_precip_mm']:,} mm · RH "
                    f"{c['mean_rh_pct']}% · {c['days_ge_35c_per_year']:.0f} days ≥35 °C"),
        ("Hazards", "FEMA NRI: tornado & wind relatively high; hail, lightning, ice, heat moderate; flood, drought, "
                    f"wildfire low · no karst/sinkholes · EPA radon zone 3 {CON}"),
    ]
    col3 += box("10 · Location & living", kv(loc))
    if is_a:
        cost = (f"<p>5 BR, ≈3,600 sf heated + 3-car garage, ≥60% stone/glass: <b>$260–320/sf</b> → house "
                f"$0.94–1.15M; foundation engineering & pad $45–80k; taps & HOA review $10–25k; design, survey, geotech, "
                f"permits $35–55k → <b>≈$1.03–1.31M</b> {EST} (+ boathouse $60–150k). Benchmark: 218 White Rock Rd "
                f"(3,929 sf, built 2022) CAD improvements $1.16M ≈ $295/sf. Built White Rock homes: CAD "
                f"{money(cmin, True)}–{money(cmax, True)} (median {money(cmed, True)}) → <span class='g'>in line</span>.</p>")
    else:
        cost = (f"<p>5 BR, ≈3,000 sf heated + 2-car garage, brick/stone/fiber-cement: <b>$200–250/sf</b> → "
                f"$0.60–0.75M; aerobic septic + drip $18–30k; pad & foundation $25–45k; water/electric $8–20k; POA "
                f"fees ≈$4k; design, survey, geotech, permits $25–40k → <b>≈$0.68–0.89M</b> {EST} (+ boathouse "
                f"$50–120k). Built Rustling Oaks homes: CAD {money(cmin, True)}–{money(cmax, True)} (median "
                f"{money(cmed, True)}) → <span class='w'>a 5-BR would top the street</span>; a 4-BR ≈2,600 sf "
                f"fits the market better.</p>")
    cost += ("<p style='color:#64748b'>2026 Texas guides: $180–280/sf builder-grade, $280–400+/sf custom "
             "(homeguide.com). Get two bids.</p>")
    col3 += box("11 · Cost to build a 5-bedroom home", cost)
    pts = " · ".join(f"{n} <b>{v:.1f}</b>/{w:.1f}" for n, w, v, why in d["score"])
    col3 += box(f"12 · Holding-investment score <b style='font-size:9pt'>{d['total']:.1f}/10</b>",
                f"<div class='bar'><i style='width:{d['total']*10:.0f}%'></i></div><p>{pts}</p>"
                f"<p style='color:#64748b'>Reasons for each point: page 6.</p>")
    band = (f'<div class="band" style="background:{d["grad"]}"><div><h1 style="font-size:12.5pt">{d["L"]} · '
            f'{d["name"]}, {d["city"]}</h1>'
            f'<div class="sub">{d["sub"]}</div></div><div class="kpis">'
            f'<div class="kpi"><b>{d["price_txt"]}</b><span>asking</span></div>'
            f'<div class="kpi"><b>{d["acres"]:.2f} ac</b><span>{t["lot_area_gis_sqft"]:,} sf GIS</span></div>'
            f'<div class="kpi"><b>{t["frontage_lake_ft"]:.0f} ft</b><span>lake frontage</span></div>'
            f'<div class="kpi"><b>{e["min_land_ft"]:.0f}–{e["max_ft"]:.0f}</b><span>ground ft msl</span></div>'
            f'<div class="score" style="color:{d["acc"]}"><b>{d["total"]:.1f}</b><span>/10 hold</span></div></div></div>')
    legend = ('<div class="legend">Evidence: ' + OFF + ' recorded source · ' + GIS + ' computed from lidar/GIS, not a '
              'survey · ' + EST + ' this report’s estimate · ' + CON + ' needs surveyor/engineer/county/HOA. '
              'Elevations: ft NAVD88 (≈ msl).</div>')
    return (f'<section class="page" style="--acc:{d["acc"]};--tint:{d["acc"]}14">{band}{strip_html}{legend}'
            f'<div class="cols"><div class="flow">{col1}{col2}{col3}</div></div>{foot(page_no)}</section>')


# --------------------------------------------------------------------------- lot page 2
def lot_page2(key, page_no):
    d = LOT[key]; t = T[key]; s = t["section"]
    W = 3.9
    is_a = key == "bayview"
    flys = [1, 3]
    last = ((fig("listing_bayview_boundary.jpg"), "cover",
             "<b>Listing drone photo</b> — lot lines drawn by the broker (approximate) · LakeHouse.com / RE/MAX") if is_a else
            (fig("listing_arrowhead_lake.jpg"), "cover",
             "<b>Listing drone photo</b> — lot lines (estimated by the broker), cove and main lake · LakeHouse.com / NTREIS"))
    cells = [
        (img(fig(f"fly_{key}_{flys[0]}.jpg"), W, "cover"),
         "<b>Fly-around 1</b> — from the cove; lidar 3-D at true vertical scale (replaces realtor.com Fly Around)",
         False),
        (img(fig(f"fly_{key}_{flys[1]}.jpg"), W, "cover"),
         "<b>Fly-around 2</b> — from the road side, looking toward the lake", False),
        (img(fig(f"plan_{key}.png"), W, "contain"),
         "<b>True-scale plan</b> (A→A′ = road→lake): 1-ft lidar contours, CAD lot lines, corners, high/low points",
         False),
        (img(fig(f"terrain3d_{key}.png"), W, "contain", crop_white=True, pad_aspect=2.25),
         "<b>3-D terrain model</b>, vertical ×3 (fly-arounds above are true 1:1): lot line, 5-BR massing, fall to lake",
         False),
        (img(fig(f"section_{key}.png"), 7.82, "contain", dpi=330),
         f"<b>Section A–A′, road→lake</b>: left TRUE 1:1 (whole section + lakeside 90 ft, real angles); right "
         f"exaggerated. Length {s['road_to_pool_ft']:.0f} ft, height {s['relief_to_pool_ft']:.1f} ft, direct angle "
         f"{s['direct_angle_deg']:.1f}°, max over 50 ft {t['slope']['max50_deg']:.1f}° on the lot", True),
        (img(fig(f"envelope_{key}.png"), W, "contain"),
         "<b>Building envelope</b>: SF-3 setbacks + ground ≥322 ft; 5-BR footprint placed for least grading"
         + ("" if is_a else "; dots = drip field"), False),
        (img(fig(f"fema_{key}.png"), W, "contain"),
         "<b>FEMA flood map</b> (NFHL): Zone A strip on the shore, rest Zone X", False),
        (img(fig(f"bathy_{key}.png"), W, "contain"),
         "<b>Lake-bottom contours</b> (TWDB Dec-2018 survey), depth below the 315 ft full pool", False),
        (img(last[0], W, last[1]), last[2], False),
    ]
    html = ""
    for im, cap, full in cells:
        html += f'<figure class="pf{" full" if full else ""}"><div class="fr">{im}</div><figcaption>{cap}</figcaption></figure>'
    band = (f'<div class="band" style="background:{d["grad"]}"><div><h1 style="font-size:12pt">{d["L"]} · {d["name"]} — '
            f'maps, terrain & views</h1><div class="sub">Pictures ≥3.8 in wide · true-north arrows · scale bars in '
            f'feet · imagery © Esri, Maxar, Earthstar</div></div>'
            f'<div class="kpis"><div class="kpi"><b>{s["direct_angle_deg"]:.1f}°</b><span>road-to-lake angle</span></div>'
            f'<div class="kpi"><b>{t["slope"]["max50_deg"]:.1f}°</b><span>max over 50 ft</span></div>'
            f'<div class="kpi"><b>{s["bank20_deg"]:.1f}°</b><span>rise at lake edge</span></div></div></div>')
    return (f'<section class="page" style="--acc:{d["acc"]}">{band}<div class="pgrid">{html}</div>{foot(page_no)}'
            f'</section>')


# --------------------------------------------------------------------------- summary
def summary_page():
    A, B = LOT["bayview"], LOT["arrowhead"]
    ta, tb = T["bayview"], T["arrowhead"]

    def card(k):
        d = LOT[k]; t = T[k]
        verdict = {
            "bayview": "Better hold of the two. Priced at its appraisal, with public water and HOA sewer, in a gated "
                       "upscale enclave with a bulkheaded, protected cove. Watch: $3,530/yr HOA dues while you hold; "
                       "narrow, shallow cove; costly 2,500 sf / 60% masonry minimum; long time on the market.",
            "arrowhead": "Cheap to hold ($144–644/yr POA, ≈$1.2k tax) and easy to build on, but the asking price is 45% over "
                         "the appraisal, it needs an aerobic septic + drip field, the cove is shallow, POA rules are strict "
                         "(no poultry) and it is rural (99 min to Dallas). Negotiate toward the $70–80k range."}[k]
        return (f'<div class="card" style="--acc:{d["acc"]};--tint:{d["acc"]}18"><div class="ch">'
                f'<div class="score"><b>{d["total"]:.1f}</b><span>/ 10</span></div><div><h2>{d["L"]} · {d["name"]}</h2>'
                f'<div class="cs">{d["city"]} · {d["acres"]:.2f} ac · {t["frontage_lake_ft"]:.0f} ft lake frontage · '
                f'{d["price_txt"]} asking · CAD {money(d["cad"])}</div></div></div>'
                f'<div class="bar" style="margin-top:3px"><i style="width:{d["total"]*10:.0f}%"></i></div>'
                f'<p>{verdict}</p></div>')

    bottom = box("Bottom line", "<ul>"
                 "<li>Both lots can take a 5-bedroom house and garage; neither needs fill for flooding. The house pads sit "
                 "4–6 ft above a conservative floor level (Zone-A edge + 2 ft).</li>"
                 "<li>Both sit on expansive Crockett/Axtell clay. Budget an engineered foundation and a geotechnical "
                 "report.</li>"
                 "<li>Both coves are only 7–10 ft deep at full pool and would be nearly dry in a 2006-type drought (lake "
                 "11 ft low).</li>"
                 "<li>Neither lot shows sinkhole, karst or wildfire concern; tornado and wind are the main hazards.</li>"
                 "</ul>")
    nm = lambda k, s_: dm(dest(k, s_))
    rows = [
        ("grp", "Price & value"),
        ("Asking price", f"{A['price_txt']} ({money(A['price']/A['acres'])}/ac) · MLS 21146775", f"{B['price_txt']} ({money(B['price']/B['acres'])}/ac) · MLS 21298338"),
        ("CAD 2026 value", f"{money(A['cad'])} · asking {100*(A['price']/A['cad']-1):+.0f}%", f"{money(B['cad'])} · asking {100*(B['price']/B['cad']-1):+.0f}%"),
        ("Property tax / yr", money(A["tax_full"]), f"{money(B['tax_full'])} (now {money(B['tax_now'])}, capped)"),
        ("5-BR build (est.)", "≈$1.03–1.31M (custom, 3,600 sf)", "≈$0.68–0.89M (3,000 sf)"),
        ("grp", "Land & terrain"),
        ("Lot size", f"{A['acres']:.2f} ac legal · {ta['lot_area_gis_sqft']:,} sf GIS", f"{B['acres']:.2f} ac legal · {tb['lot_area_gis_sqft']:,} sf GIS"),
        ("Lot dimensions", f"road {ta['frontage_road_ft']:.0f} · lake {ta['frontage_lake_ft']:.0f} · sides 298/247 ft (wedge)",
         f"road {tb['frontage_road_ft']:.0f} · lake {tb['frontage_lake_ft']:.0f} · sides 255/181 ft"),
        ("Lowest / highest", f"{ta['elev']['min_land_ft']:.1f} / {ta['elev']['max_ft']:.1f} ft", f"{tb['elev']['min_land_ft']:.1f} / {tb['elev']['max_ft']:.1f} ft"),
        ("Elevation difference", f"{ta['elev']['relief_ft']:.1f} ft", f"{tb['elev']['relief_ft']:.1f} ft"),
        ("Average slope", f"{ta['slope']['mean_pct']:.1f}% (house area {ta['slope']['env_mean_pct']:.1f}%)", f"{tb['slope']['mean_pct']:.1f}% (house area {tb['slope']['env_mean_pct']:.1f}%)"),
        ("Max slope (50 ft)", f"{ta['slope']['max50_pct']:.0f}% / {ta['slope']['max50_deg']:.1f}° at the bank", f"{tb['slope']['max50_pct']:.0f}% / {tb['slope']['max50_deg']:.1f}° at the bank"),
        ("Soil", "Crockett: sandy loam over high-shrink clay", "Axtell: sandy loam over high-shrink clay"),
        ("grp", "Flood"),
        ("FEMA zone", f"X + Zone A on {ta['zoneA_pct_of_lot']:.0f}% (shore) · 48349C0450D", f"X + Zone A on {tb['zoneA_pct_of_lot']:.0f}% (shore) · 48349C0600D"),
        ("BFE", "none published (Zone A); TRWD 100-yr 318 ft", "none published (Zone A); TRWD 100-yr 318 ft"),
        ("Min finished floor", f"≥{A['ffe_min']:.1f} ft (est.) · pad ≈{A['pad']['pad_level_ft']:.0f} ft", f"≥{B['ffe_min']:.1f} ft (est.) · pad ≈{B['pad']['pad_level_ft']:.0f} ft"),
        ("Fill required?", "<span class='g'>No</span>", "<span class='g'>No</span>"),
        ("grp", "Utilities"),
        ("Water / sewer", "M.E.N. WSC / White Rock HOA sewer plant", "Winkler WSC / <span class='r'>none</span>"),
        ("Septic required?", "<span class='g'>No</span>", "<span class='w'>Yes</span> — aerobic + drip; 5–6 BR fit"),
        ("Electric / gas / internet", "NCEC co-op / propane / 5G, fixed wireless, Starlink", "NCEC co-op / propane / 5G, fixed wireless, Starlink"),
        ("grp", "Rules"),
        ("HOA & fee", "White Rock HOA (gated) · <b>$3,530/yr</b> incl. sewer (listing)", f"Rustling Oaks POA · $144/yr handbook, $644/yr MLS {CON}"),
        ("Min house / zoning", "2,500 sf, 60% stone & glass · likely SF-3", "1,600 sf · likely SF-3"),
        ("In-law suite", "≤40% of main house (county) + HOA", "≤40% of main house (county) + ACC"),
        ("Hobby farming", "<span class='r'>No</span> poultry/livestock (needs ≥3 ac)", "<span class='r'>No</span> — POA bans fowl & livestock"),
        ("Short-term rental", "unclear — confirm county & HOA", "unclear — confirm county & POA"),
        ("grp", "Lake"),
        ("Dock possible?", f"<span class='g'>Yes</span>, TRWD ≤{A['dock_sf']:,} sf · bulkhead exists", f"<span class='g'>Yes</span>, TRWD ≤{B['dock_sf']:,} sf · steel wall exists"),
        ("Lake depth off lot", "8 ft mean / 10 ft max at full pool", "7 ft mean / 8.5 ft max at full pool"),
        ("Boating / fishing", "all craft · marina 0.2 mi · catfish, hybrids, bass, crappie", "all craft · POA ramp & pier · same fishery"),
        ("Main house, garage, pool, garden", "fit (envelope 12,800 sf); raised-bed garden", "fit (envelope 14,300 sf); raised-bed garden"),
        ("grp", "Access"),
        ("Nearest hospital", f"Navarro Regional {dm(named('bayview','hospitals','Navarro'))}", f"Freestone Medical {dm(named('arrowhead','hospitals','Freestone'))}"),
        ("Intl. airport", f"DFW {nm('bayview','DFW')}", f"DFW {nm('arrowhead','DFW')}"),
        ("Dallas / schools", f"{nm('bayview','Dallas (downtown)')} · Mildred ISD (B)", f"{nm('arrowhead','Dallas (downtown)')} · Fairfield ISD (C)"),
    ]
    tr = []
    for r in rows:
        if r[0] == "grp":
            tr.append(f'<tr class="grp"><td colspan="3">{r[1]}</td></tr>')
        else:
            tr.append(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>")
    table = (f'<table class="cmp"><tr><th style="background:#334155">Key measurements</th>'
             f'<th style="background:{A["acc"]}">A · 11 Bayview Cir (White Rock)</th>'
             f'<th style="background:{B["acc"]}">B · 5001 Arrowhead Pt (Rustling Oaks)</th></tr>{"".join(tr)}</table>')
    actions = box("Before you buy", "<ol style='margin:1px 0 0 12px;padding:0'>"
                  "<li><b>A:</b> get the White Rock CC&Rs and HOA budget; confirm what the $3,530/yr dues cover. "
                  "<b>B:</b> confirm the POA fee ($144 or $644/yr).</li>"
                  "<li><b>Both:</b> boundary + topographic survey showing the 315/318/320 ft lines; Elevation Certificate.</li>"
                  "<li><b>Both:</b> Navarro County zoning district and floodplain freeboard in writing.</li>"
                  "<li><b>B:</b> OSSF site evaluation by a sanitarian/engineer (TRWD permit) before closing.</li>"
                  "<li><b>Both:</b> water, electric and (A) sewer will-serve letters; geotechnical report; TRWD permit "
                  "history for the existing bulkheads.</li></ol>")
    band = ('<div class="band" style="background:linear-gradient(95deg,#1e3a8a,#0f766e 55%,#6d28d9)"><div>'
            '<h1 style="font-size:13pt">Two lakefront lots on Richland-Chambers Reservoir, Texas</h1>'
            '<div class="sub">Long-term land hold and future 5-bedroom lake home · Navarro County · summary of both '
            'lots · 8 Nov 2026</div></div><div class="kpis">'
            f'<div class="kpi"><b>{money(A["price"]+B["price"], True)}</b><span>combined asking</span></div>'
            f'<div class="kpi"><b>{A["acres"]+B["acres"]:.2f} ac</b><span>combined</span></div>'
            f'<div class="kpi"><b>{ta["frontage_lake_ft"]+tb["frontage_lake_ft"]:.0f} ft</b><span>lake frontage</span></div>'
            '</div></div>')
    return (f'<section class="page" style="--acc:#1e3a8a">{band}<div class="srow"><figure class="smap">'
            f'{img(fig("region.png"), 3.86, "cover")}</figure><div>{card("bayview")}{card("arrowhead")}{bottom}</div>'
            f'</div>{table}<div style="margin-top:4px">{actions}</div><div style="flex:1"></div>{foot(1)}</section>')


# --------------------------------------------------------------------------- end page
def end_page():
    garden = ("<table class='mini'><tr><th>Category</th><th>Suitable plants</th><th>Plant</th><th>Soil needs</th></tr>"
              "<tr><td>Vegetables</td><td>warm: tomato, pepper, okra, southern peas, squash, sweet potato, eggplant · "
              "cool: broccoli, cabbage, short-day onion, lettuce, spinach, carrot</td><td>warm Mar 15–May &amp; Jul–Aug "
              "(fall crop) · cool Sep–Oct &amp; Feb</td><td>raised beds 10–12 in, 50:50 topsoil/compost</td></tr>"
              "<tr><td>Fruits</td><td>blackberry (thornless), fig, pear, persimmon, pomegranate, low-chill peach, "
              "muscadine grape</td><td>bare-root Dec–Feb</td><td>mounded beds; avoid wet clay pockets</td></tr>"
              "<tr><td>Herbs</td><td>rosemary, oregano, thyme, sage, Mexican mint marigold; basil (summer); cilantro, "
              "dill, parsley (cool)</td><td>Mar–Apr; Oct for cool herbs</td><td>well drained, raised</td></tr>"
              "<tr><td>Trees</td><td>pecan, cedar elm, bur oak, live oak, Shumard oak, redbud, Mexican plum</td>"
              "<td>Nov–Feb</td><td>plant ≥15 ft from the foundation (clay shrink-swell)</td></tr></table>"
              "<p>Amendments, from SSURGO and to be confirmed by a $15 Texas A&amp;M soil test: compost 2–3 in and mulch on "
              "both lots. Lot A topsoil pH 6.5 needs no lime or sulfur. Lot B topsoil pH 5.8 may need light lime. Use "
              "balanced or N-only fertilizer as the test directs. The clay subsoil starts at 4–8 in and drains very "
              "slowly, so <b>raised beds are advised</b>. Growing season ≈297 frost-free days (ERA5; lake-moderated, "
              "verify locally); USDA zone 8a.</p>")
    docs = ("<ul><li><b>Both:</b> recorded subdivision plat; boundary + topographic survey with 315/318/320 ft lines; "
            "Elevation Certificate; title commitment; geotechnical report; zoning-district & floodplain letter from "
            "Navarro County Planning &amp; Development (601 N 13th St, Corsicana; 903-875-3312); TRWD permit history "
            "for the existing steel walls; will-serve letters (water co-op, NCEC electric); seller disclosures and "
            "listing photos.</li>"
            "<li><b>A (White Rock):</b> declaration & CC&Rs, architectural guidelines, HOA budget, dues, transfer fee, "
            "special assessments, sewer tap fee and plant capacity.</li>"
            "<li><b>B (Rustling Oaks):</b> full recorded Declaration of CC&Rs (only the ACC handbook is online); OSSF site "
            "evaluation & perc/soil test; Winkler WSC tap fee.</li></ul>")
    gl = [("BFE", "Base Flood Elevation: water level of the 1%-annual-chance (100-yr) flood"),
          ("Zone A / X", "FEMA 1%-chance floodplain without a BFE / area of minimal flood hazard"),
          ("FIRM", "Flood Insurance Rate Map panel"), ("Freeboard", "extra height above the BFE for the lowest floor"),
          ("NAVD88 / msl", "vertical datums for elevations (here within 0.03 ft of NGVD29/msl)"),
          ("Normal pool", "full lake level, 315.0 ft; TRWD flowage easement runs to 320.0 ft"),
          ("TRWD", "Tarrant Regional Water District — owns the lake; permits docks, walls, septic near it"),
          ("Lidar / DEM", "laser-scanned bare-earth elevation grid (1 m) used for contours and slopes"),
          ("Vertical exaggeration", "vertical scale stretched vs horizontal; ×1 = true shape"),
          ("CAD", "Central Appraisal District — tax parcel and value records"),
          ("GIS parcel", "digital tax-map lot outline; not a survey"),
          ("OSSF / ATU", "on-site sewage facility (septic) / aerobic treatment unit"),
          ("Drip field", "subsurface drip lines that disperse treated effluent; sized by Ra (gal/sf/day)"),
          ("Class IV soil", "clay, the slowest-draining septic soil class (Ra 0.1)"),
          ("Shrink-swell (LEP)", "clay volume change with moisture; LEP >6% is high"),
          ("HSG", "hydrologic soil group (runoff potential, A low – D high)"),
          ("SF-3 / SUP", "county ½-acre single-family district / Specific Use Permit"),
          ("HOA / POA / ACC", "home- or property-owners' association / architectural control committee"),
          ("WSC / NCEC", "water supply corporation / Navarro County Electric Cooperative"),
          ("Circuit breaker", "Texas 20%/yr cap on appraisal rises for non-homestead property ≤$5M"),
          ("STR", "short-term rental (<30 days)"), ("ERA5", "global weather reanalysis used for climate normals")]
    gloss = "<table class='mini'>" + "".join(f"<tr><td><b>{a}</b></td><td>{b}</td></tr>" for a, b in gl) + "</table>"
    src = ("<ul>"
           "<li>Navarro Central Appraisal District records (parcels 63254, 56587 and neighbours) · TxGIO StratMap 2026 "
           "parcels</li><li>USGS 3DEP 1 m lidar DEM (TX 2022 North-Central; 2018 Red River check) · USGS NWIS well "
           "records</li><li>FEMA National Flood Hazard Layer; FEMA National Risk Index (Dec 2025)</li>"
           "<li>USDA NRCS SSURGO via Soil Data Access</li><li>TWDB Dec-2018 volumetric survey & Water Data for Texas "
           "lake levels · TPWD Richland-Chambers survey report (2022)</li>"
           "<li>TRWD General Ordinance (Dec 2025) & 2026 Residential Improvement / OSSF guidelines; TRWD Waste Control "
           "Order (2011) · TCEQ 30 TAC 285 (RG-472)</li>"
           "<li>Navarro County Richland-Chambers Lakeshore Area Zoning Ordinance (rev. 2017; 2022 amendment) & 2025 "
           "building-permit package</li><li>Rustling Oaks Estates POA ACC handbook & fee schedules (2009–2024)</li>"
           "<li>LakeHouse.com listings 7100373 (MLS 21146775) and 7885360 (MLS 21298338): price, dues, listing photos "
           "· Zillow, Realtor.com, Redfin, HAR search snippets (pages block automated access) · The Teel Team</li>"
           "<li>US Census ACS 2020–24 (Census Reporter), QuickFacts V2025 · TEA 2026 ratings (Texas Tribune)</li>"
           "<li>Esri World Imagery & World Geocoder · OpenStreetMap / OSRM routes · HIFLD electric territories · TWDB "
           "water-service areas · ERA5 via Open-Meteo</li></ul>")
    limits = ("<p>Desk study from public records — no site visit. Not a survey, appraisal, flood determination, soil "
              "evaluation, title opinion or legal/engineering advice. Lidar elevations carry about ±0.5 ft error and "
              "GIS lot lines can differ from the recorded plat by several feet. Both HOA documents and the county "
              "zoning district were not obtainable online and are marked CONFIRM. Zillow, Redfin and realtor.com "
              "(including its Fly Around views) refuse automated access (HTTP 403/429), so listing photos come from "
              "LakeHouse.com (same MLS photos) and the fly-around views are generated from lidar.</p>")
    end = (f"<div class='box' style='--acc:#0f172a;background:#f8fafc'><h3>End note</h3><p><b>Date of creation:</b> "
           f"{CREATED:%d %B %Y} &nbsp;·&nbsp; <b>Prepared by AI model:</b> {MODEL} (Anthropic), working in Kiro &nbsp;·&nbsp; "
           f"<b>File:</b> {PDF_NAME}</p><p>Data, scripts and figures to rebuild this report are in the "
           f"GitHub repository MMS-ITS/Corsicana_3lots.</p></div>")
    Y, C_, N_ = "<span class='g'>Yes</span>", "<span class='w'>Conditional</span>", "<span class='r'>No</span>"
    A, B = LOT["bayview"], LOT["arrowhead"]
    feas = [("Main house (5 BR)", Y + " — envelope 12,800 sf; 60×46 ft pad on 2.7 ft of fall",
             Y + " — envelope 14,300 sf; 60×46 ft pad on 2.1 ft of fall"),
            ("In-law suite", C_ + " — ≤40% of house (county) + HOA approval", C_ + " — ≤40% of house + ACC approval"),
            ("Garage", Y + " — attached 3-car within setbacks", Y + " — attached; detached only after the house slab"),
            ("Septic system", "not needed — HOA sewer", Y + " — aerobic + drip, 5–6 BR, after site evaluation"),
            ("Garden", C_ + " — raised beds over clay", C_ + " — raised beds; lime per soil test"),
            ("Hobby farming", N_ + " — poultry/livestock need ≥3 ac", N_ + " — POA bans fowl & livestock"),
            ("Dock", Y + f" — TRWD ≤{A['dock_sf']:,} sf; narrow cove", Y + f" — TRWD ≤{B['dock_sf']:,} sf"),
            ("Boat access", C_ + " — 5–7 ft today; dry in a deep drought", C_ + " — 4–6 ft today; POA ramp & pier"),
            ("Short-term rental", C_ + " — not addressed by county; HOA rules unknown", C_ + " — not addressed; ask POA"),
            ("Pool / outdoor", Y + " — room behind the house; TRWD permit below 320 ft",
             C_ + " — must share space with the drip field; POA fee $1,000")]
    feas_html = ("<table class='mini'><tr><th></th><th>A · 11 Bayview Cir</th><th>B · 5001 Arrowhead Pt</th></tr>" +
                 "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in feas) + "</table>")
    srows = "".join(
        f"<tr><td><b>{a[0]}</b> ({a[1]:.1f})</td><td><b>{a[2]:.1f}</b> {a[3]}</td><td><b>{b[2]:.1f}</b> {b[3]}</td></tr>"
        for a, b in zip(A["score"], B["score"]))
    method = (f"<table class='mini'><tr><th>Criterion (max)</th><th>A · {A['total']:.1f}/10</th>"
              f"<th>B · {B['total']:.1f}/10</th></tr>{srows}</table>"
              "<p>A holding score rewards a fair price, appreciation, usable frontage, cheap and easy building, low "
              "carrying cost and an easy resale. A's $3,530/yr dues cost it 0.3 points; it still ranks first. If B's "
              "POA fee is $644, B's score is unchanged.</p>")
    band = ('<div class="band" style="background:linear-gradient(95deg,#334155,#1e3a8a)"><div><h1 style="font-size:12pt">'
            'Construction feasibility · gardening · documents · glossary · sources</h1><div class="sub">Shared notes '
            'for both lots</div></div></div>')
    body = (f"<div class='two' style='margin-top:6px'><div>{box('Final construction feasibility', feas_html)}</div>"
            f"<div>{box('Holding-investment score — points and reasons', method)}</div></div>"
            f"<div class='two'><div>{box('Gardening & farming (same climate, similar clay)', garden)}"
            f"{box('Documents to obtain before purchase', docs)}{box('Data sources', src)}</div>"
            f"<div>{box('Glossary', gloss)}{box('Method & limits', limits)}{end}</div></div>")
    return f'<section class="page" style="--acc:#1e3a8a">{band}{body}<div style="flex:1"></div>{foot(6)}</section>'


# --------------------------------------------------------------------------- build
def build_html():
    pages = [summary_page(), lot_page1("bayview", 2), lot_page2("bayview", 3), lot_page1("arrowhead", 4),
             lot_page2("arrowhead", 5), end_page()]
    import matplotlib
    ttf = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    # Noto Sans lacks ≈ ≥ ≤ → etc.; DejaVu Sans supplies those glyphs as a per-character fallback.
    fonts = (f'@font-face {{ font-family: "DJV"; src: url("file://{ttf}/DejaVuSans.ttf"); font-weight: 400; }}\n'
             f'@font-face {{ font-family: "DJV"; src: url("file://{ttf}/DejaVuSans-Bold.ttf"); font-weight: 700; }}\n')
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>Richland-Chambers lots — due diligence "
            f"({STAMP})</title><style>{fonts}{CSS}</style></head><body>{''.join(pages)}</body></html>")


async def render(html_path, pdf_path):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 816, "height": 1056})
        await pg.goto("file://" + html_path, wait_until="load")
        await pg.wait_for_timeout(800)
        over = await pg.evaluate("""() => {
          const out = [];
          document.querySelectorAll('.page').forEach((p, i) => {
            if (p.scrollHeight > p.clientHeight + 1) out.push(`page ${i+1} overflows by ${p.scrollHeight - p.clientHeight}px`);
            p.querySelectorAll('.flow').forEach((f) => {
              const fr = f.getBoundingClientRect();
              const r = f.lastElementChild.getBoundingClientRect();
              const col = Math.floor((r.left - fr.left + 4) / (fr.width / 3)) + 1;
              if (f.scrollWidth > f.clientWidth + 2) out.push(`page ${i+1} text OVERFLOWS into a 4th column`);
              else out.push(`page ${i+1} text ends in column ${col}, ${Math.round(fr.bottom - r.bottom)}px spare`);
            });
            p.querySelectorAll('figcaption').forEach((fc) => {
              if (fc.scrollHeight > fc.clientHeight + 1) out.push(`page ${i+1} caption clipped: ${fc.textContent.slice(0, 50)}`);
            });
            const f = p.querySelector('.foot'); const last = f ? f.getBoundingClientRect().bottom - p.getBoundingClientRect().top : 0;
            out.push(`page ${i+1} footer bottom ${Math.round(last)}px of ${p.clientHeight}`);
          });
          return out; }""")
        await pg.pdf(path=pdf_path, width="8.5in", height="11in", print_background=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True)
        await b.close()
    return over


def main():
    html = build_html()
    html_path = os.path.join(OUT, "report.html")
    open(html_path, "w", encoding="utf-8").write(html)
    pdf_path = os.path.join(ROOT, PDF_NAME)
    over = asyncio.run(render(html_path, pdf_path))
    for o in over:
        print("  ", o)
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    print("PDF:", pdf_path, f"{os.path.getsize(pdf_path)/1e6:.1f} MB", len(doc), "pages",
          [f"{p.rect.width/72:.2f}x{p.rect.height/72:.2f} in" for p in doc][:1])
    prev = os.path.join(OUT, "preview"); os.makedirs(prev, exist_ok=True)
    for i, pg in enumerate(doc):
        pg.get_pixmap(dpi=int(sys.argv[1]) if len(sys.argv) > 1 else 110).save(os.path.join(prev, f"page{i+1}.png"))
    return pdf_path


if __name__ == "__main__":
    main()
