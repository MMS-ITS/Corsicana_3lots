"""HTML pieces for the 10 Nov 2026 Shores report (letter size, printed by Chromium)."""
import base64
import io
import os

import numpy as np
from PIL import Image

from common import ASSETS, FIG
from shores_data import (CREATED, FLOWAGE, LAKE_NOW, LAKE_NOW_DATE, LK, LOT, MODEL, POOL, RATE, RATES, SCORE, SN,
                         SV, T, facts, zone_a_distance_ft)

PAGES_TOTAL = 10


def tag(kind):
    lab = {"OFF": "OFFICIAL", "GIS": "GIS", "EST": "ESTIMATE", "CON": "CONFIRM", "NEW": "CORRECTED"}[kind]
    return f'<span class="tag {kind}">{lab}</span>'


OFF, GIS, EST, CON, NEW = (tag(k) for k in ("OFF", "GIS", "EST", "CON", "NEW"))


def money(v, k=False):
    if v is None:
        return "n/a"
    if k:
        return f"${v/1000:,.0f}k" if v < 1e6 else f"${v/1e6:,.2f}M"
    return f"${v:,.0f}"


_IMG = {}


def img(path, w_in, fit="cover", dpi=300, crop_white=False, q=86, pos="center"):
    k = (path, w_in, crop_white)
    if k not in _IMG:
        im = Image.open(path)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA"); bg = Image.new("RGB", im.size, "white"); bg.paste(im, mask=im.split()[-1]); im = bg
        else:
            im = im.convert("RGB")
        if crop_white:
            a = np.asarray(im).astype(int); ys, xs = np.nonzero(np.abs(a - 255).sum(axis=2) > 30)
            im = im.crop((max(xs.min() - 12, 0), max(ys.min() - 12, 0), min(xs.max() + 12, im.width),
                          min(ys.max() + 12, im.height)))
        W = int(w_in * dpi)
        if im.width > W:
            im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        _IMG[k] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return f'<img src="{_IMG[k]}" style="object-fit:{fit};object-position:{pos}">'


def fig(name):
    return os.path.join(FIG, name)


def heated_range(key):
    """Largest heated area, 2 storeys: '8,880–9,840' when the 75-ft and 50-ft drip set-backs differ, else one value."""
    f = facts(key); hi = f["max50"]["heated_2st_sf"]
    lo = min(hi, f["max75"]["heated_2st_sf"]) if f["max75"] else hi
    return f"{hi:,}" if lo == hi else f"{lo:,}–{hi:,}"


def photo(key, name):
    return os.path.join(ASSETS, "listing", key, name)


def box(title, body, note=""):
    n = f"<small>{note}</small>" if note else ""
    return f'<div class="box"><h3><span>{title}</span>{n}</h3>{body}</div>'


def kv(rows):
    return '<table class="kv">' + "".join(f'<tr><td class="k">{a}</td><td>{b}</td></tr>' for a, b in rows) + "</table>"


def foot(page_no, total=PAGES_TOTAL):
    return (f'<div class="foot"><span>The Shores on Richland Chambers Lake · Lots 442, 411, 441 · revised desk due '
            f'diligence from public records, not a survey or appraisal</span>'
            f'<span>created {CREATED:%d %b %Y} · {MODEL} · p {page_no}/{total}</span></div>')


def dm(r):
    if not r or r.get("drive_mi") is None:
        return "n/a"
    mi = r["drive_mi"]
    return f"{mi:.1f} mi · {r['drive_min']:.0f} min" if mi < 10 else f"{mi:.0f} mi · {r['drive_min']:.0f} min"


def dest(key, sub):
    for r in SV[key]["named"]:
        if sub.lower() in r["name"].lower():
            return r
    return None


def named(key, grp, sub):
    for r in SN[key].get(grp, []):
        if sub.lower() in (r.get("name") or "").lower():
            return r
    return None


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
.band h1 { font-size: 13.5pt; margin: 0; line-height: 1.05; }
.band .sub { font-size: 6.8pt; margin-top: 2px; opacity: .96; }
.kpis { display: flex; gap: 4px; align-items: center; }
.kpi { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.35); border-radius: 6px;
       padding: 2px 6px; text-align: center; }
.kpi b { display: block; font-size: 10.2pt; line-height: 1.1; white-space: nowrap; }
.kpi span { font-size: 5.5pt; opacity: .95; white-space: nowrap; }
.score { background: #fff; border-radius: 50%; width: 0.62in; height: 0.62in; display: flex; flex-direction: column;
         align-items: center; justify-content: center; font-weight: 800; flex: none; }
.score b { font-size: 15pt; line-height: 1; } .score span { font-size: 5.2pt; color: #475569; }
.score s { font-size: 5.6pt; color: #94a3b8; font-weight: 600; }
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
.box ul, .box ol { margin: 1px 0 0 10px; padding: 0; } .box li { margin: 0.5px 0; }
table.kv { width: 100%; border-collapse: collapse; }
table.kv td { padding: 0.35px 1.5px; vertical-align: top; border-bottom: 0.5px dotted #e2e8f0; }
table.kv td.k { color: #475569; white-space: nowrap; padding-right: 3px; width: 1%; }
table.mini { width: 100%; border-collapse: collapse; font-size: 5.7pt; }
table.mini td, table.mini th { padding: 0.4px 2px; border-bottom: 0.5px solid #eef2f7; text-align: left; vertical-align: top; }
table.mini th { color: #475569; font-weight: 700; background: #f8fafc; }
table.mini td.n, table.mini th.n { text-align: right; white-space: nowrap; }
.tag { display: inline-block; font-size: 4.6pt; font-weight: 700; padding: 0 2px; border-radius: 3px;
       vertical-align: 0.6pt; letter-spacing: .15px; }
.OFF { background: #dcfce7; color: #166534; } .GIS { background: #dbeafe; color: #1e40af; }
.EST { background: #fef3c7; color: #92400e; } .CON { background: #fee2e2; color: #991b1b; }
.NEW { background: #ede9fe; color: #5b21b6; }
.g { color: #15803d; font-weight: 700; } .w { color: #b45309; font-weight: 700; } .r { color: #b91c1c; font-weight: 700; }
.foot { flex: none; font-size: 5.3pt; color: #64748b; display: flex; justify-content: space-between;
        border-top: 1px solid #e2e8f0; padding-top: 2px; margin-top: 2px; }
.bar { height: 4px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--acc); }
.pgrid { flex: 1 1 auto; display: grid; grid-template-columns: 1fr 1fr; column-gap: 6px; row-gap: 2px;
         align-content: start; margin-top: 5px; }
.pf { margin: 0; }
.pf .fr { height: 1.72in; border: 1px solid #cbd5e1; border-radius: 5px; overflow: hidden; background: #fff; }
.pf.full { grid-column: 1 / span 2; } .pf.full .fr { height: 2.03in; }
.pf img { width: 100%; height: 100%; display: block; }
.pf figcaption { font-size: 5.4pt; color: #334155; padding: 1px 2px 0; line-height: 1.17; height: 0.155in; overflow: hidden; }
.pf figcaption b { color: var(--acc); }
.srow { display: grid; grid-template-columns: 3.3in 1fr; gap: 7px; margin: 6px 0 5px; flex: none; }
.smap { margin: 0; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; height: 2.62in; }
.smap img { width: 100%; height: 100%; display: block; }
.card { border-radius: 7px; border: 1px solid #e2e8f0; border-top: 4px solid var(--acc); padding: 3px 6px 3px;
        margin-bottom: 4px; background: linear-gradient(180deg, var(--tint), #fff 60%); }
.card .ch { display: flex; gap: 7px; align-items: center; }
.card .score { border: 3px solid var(--acc); color: var(--acc); width: 0.56in; height: 0.56in; }
.card .score b { font-size: 13.5pt; }
.card h2 { font-size: 8.8pt; margin: 0; color: var(--acc); }
.card .cs { font-size: 5.9pt; color: #334155; }
.card p { margin: 2px 0 1px; font-size: 6.05pt; }
table.cmp { width: 100%; border-collapse: collapse; font-size: 5.95pt; flex: none; }
table.cmp th { color: #fff; padding: 2px 4px; text-align: left; font-size: 6.4pt; }
table.cmp td { padding: 0.75px 4px; border-bottom: 0.5px solid #e2e8f0; vertical-align: top; }
table.cmp td:first-child { color: #334155; font-weight: 600; white-space: nowrap; width: 1.25in; }
table.cmp tr:nth-child(even) td { background: #f8fafc; }
table.cmp tr.grp td { background: #eef2ff; color: #1e3a8a; font-weight: 700; padding-top: 1.2px; }
table.corr { width: 100%; border-collapse: collapse; font-size: 5.75pt; }
table.corr th { background: #312e81; color: #fff; text-align: left; padding: 2px 3px; font-size: 6.1pt; }
table.corr td { padding: 1.1px 3px; border-bottom: 0.5px solid #e2e8f0; vertical-align: top; }
table.corr tr:nth-child(even) td { background: #f8fafc; }
table.corr td:first-child { font-weight: 700; color: #312e81; white-space: nowrap; }
table.corr td.old { color: #7f1d1d; } table.corr td.new { color: #14532d; }
/* lot fact pages: the base size is raised in the browser until the three columns are full (see render()) */
.flow { font-size: 6.55pt; line-height: 1.17; }
.flow .box h3 { font-size: 1.11em; } .flow .box h3 small { font-size: 0.74em; }
.flow table.mini { font-size: 0.94em; } .flow .tag { font-size: 0.70em; }
.flow .big { font-size: 1.3em; }
ul.pn { list-style: none; margin: 1px 0 0; padding: 0; }
ul.pn li { padding-left: 9px; position: relative; margin: 1px 0; }
ul.pn li::before { position: absolute; left: 0; top: -0.5px; font-weight: 800; }
ul.pn li.p::before { content: "+"; color: #15803d; } ul.pn li.m::before { content: "−"; color: #b91c1c; }
/* .fit wraps everything between the band and the footer on pages 1, 8, 9, 10. render() raises its font size
   until the page is full, so every size inside is relative (em) to it. */
.fit { flex: none; font-size: 6.6pt; }
.fit table.cmp { font-size: 1em; } .fit table.cmp th { font-size: 1.04em; }
.fit table.cmp td:first-child { width: 1.35in; }
.fit .card p { font-size: 1.01em; } .fit .card .cs { font-size: 0.95em; } .fit .card h2 { font-size: 1.33em; }
.fit .box h3 { font-size: 1.12em; } .fit .box h3 small { font-size: 0.78em; }
.fit table.mini { font-size: 0.94em; } .fit table.corr { font-size: 0.95em; } .fit table.corr th { font-size: 1.04em; }
.fit .tag { font-size: 0.72em; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.three { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; }
.chip { display:inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 2px; vertical-align: 0.2pt; }
"""


# --------------------------------------------------------------------------- per-lot alerts and next steps
# (+) positives and (−) alerts specific to each lot, then the lot's own first steps.
NOTES = {
    "lot441": dict(
        pos=["105 ft of steel-walled canal: the largest dock of the three (839 sf) and no wall to build",
             "$1,000 per foot of water, the lowest of the three (442: $1,580/ft)",
             "95% of the lot is above the 320-ft flowage line; the house pad needs no fill",
             "Same 7.6-ft maximum depth as 442; canal ≈92 ft wide at 315 ft",
             "One owner since buying from the developer in 2008: a short title chain to check"],
        neg=["11% of the lot (the shore strip) is FEMA Zone A with no base flood elevation: keep every building "
             "out of it, or a lender will require flood insurance",
             "The CAD cut the value 53% in 2026; in 2027 it may go back toward $150k (tax ≈$2,360)",
             "Highest asking price: $105k is 1.5× the 2026 CAD value",
             "Bank falls 22° over the last 20 ft: plan steps or a ramp down to the dock",
             "The CAD dates the wall to 2021 but rates it 73% good: inspect it and ask for its TRWD permit"],
        steps=["Offer ≈$90–95k with a 21-day option. Cite the $70,834 CAD value and the 2025 price cut.",
               "Ask the agent for any survey, the wall's TRWD permit, and any POA violation letters.",
               "Survey: 315/320-ft lines, the Zone A line, where the wall stands, and the corners.",
               "Septic evaluation: a 6-BR drip field outside Zone A and ≥50 ft from the 315-ft line.",
               "Walk away if the wall is unpermitted or off the lot, or the drip field will not fit."]),
    "lot442": dict(
        pos=["Widest canal (≈113 ft at 315 ft) and the best mean depth (6.1 ft at full pool)",
             "Largest house footprint of the three: 6,656 sf, ≈10,700 sf heated in theory",
             "Whole lot in FEMA Zone X; 98% of it above 320 ft",
             "672 days on the market after $30k of cuts: the seller has reason to negotiate"],
        neg=["Only 60 ft touches the water, so TRWD allows at most a 480-sf dock (one covered slip + lift)",
             "The CAD values it at $155k, 2.2× the per-acre value of most neighbours; tax $2,246, twice 441's",
             "Taxed on $142,802 although the CAD shows $155,239 with no cap or exemption: ask the CAD why. "
             "On $155k the tax would be ≈$2,440",
             "Wedge shape: 160 ft at the road, 60 ft at the water; bank 23° over the last 20 ft, 34° over the steepest 10 ft"],
        steps=["Offer ≈$80–85k with a 21-day option; the time on market and two cuts support it.",
               "Protest the 2027 value with the sale price. Texas deadline: 15 May, or 30 days after the notice.",
               "Ask TRWD whether 480 sf fits your boat, lift and any boathouse roof.",
               "Survey: confirm 60 ft at the 315-ft line and room for the 5-ft side clearances.",
               "Walk away if the dock limit is too small for your boat."]),
    "lot411": dict(
        pos=["Lowest price: $65k, $130k per acre",
             "Whole lot above 320 ft (321–336 ft) and in Zone X: the highest, driest ground of the three",
             "Simple rectangle with 102 ft on Sailboat Dr"],
        neg=["The lot stops at the canal tract's 315-ft deed line; open water is 25–33 ft further out",
             "Shallowest water: 5.5 / 6.0 ft (mean / max) at full pool, ≈2.7 / 3.2 ft now, ≤1.6 ft at the Dec 2022 low",
             "Silted, overgrown canal head: dredging needs TRWD approval (perhaps a USACE permit too); who pays is unknown",
             "The CAD's 100-ft wall dates from 2010 and is rated 20% good: budget to repair or replace it",
             "GIS area 0.487 ac vs legal 0.500 ac: the TCEQ half-acre septic minimum is at the margin"],
        steps=["Before any offer, get TRWD's written answer: which shoreline counts, whether a walkway may "
               "cross the canal tract, and who may dredge.",
               "Ask the POA who owns the canal tract and whether owners may cross it.",
               "Offer ≈$55–60k, subject to TRWD's dock approval. The Shores' 1-acre off-water lots ask $60–70k.",
               "Survey: confirm 0.500 ac (septic minimum) and where the 2010 wall stands.",
               "Walk away if TRWD will not allow a dock that reaches open water."]),
}


def notes_boxes(key):
    n = NOTES[key]
    alerts = box("13 · Alerts for this lot",
                 "<ul class='pn'>" + "".join(f"<li class='p'>{x}</li>" for x in n["pos"])
                 + "".join(f"<li class='m'>{x}</li>" for x in n["neg"]) + "</ul>",
                 "+ positive · − alert")
    steps = box("14 · Before you commit", "<ol>" + "".join(f"<li>{x}</li>" for x in n["steps"]) + "</ol>",
                "offer prices are estimates")
    return alerts + steps


# --------------------------------------------------------------------------- lot page 1
def corners_table(t):
    cs = t["corners"]
    cells = "".join(f'<td>P{i+1} {c["lonlat"][1]:.6f}, {c["lonlat"][0]:.6f}</td>' + ("</tr><tr>" if i % 2 == 1 else "")
                    for i, c in enumerate(cs))
    return f'<table class="mini"><tr>{cells}</tr></table>'


def lot_page1(key, page_no):
    d = LOT[key]; t = T[key]; f = facts(key); e = t["elev"]; sl = t["slope"]; s = t["section"]
    h = f["hold"]; m50, m75 = f["max50"], f["max75"]; dock = f["dock"]
    is411 = key == "lot411"
    pad = t["fits"]["two-storey 5BR 60x46 ft + garage (2,760 sf)"]
    za = t["zoneA_edge_elev_ft"]
    ffe = (max(318.0, za["median"]) if za else 318.0) + 2.0
    side = [x for x in t["edges"] if x["kind"] == "side"]
    strip = [(img(photo(key, d["photos"]["hero"]), 1.95), f"Listing photo · LakeHouse.com (NTREIS) · MLS {d['mls']}"),
             (img(fig(f"aerial_{key}_lot.jpg"), 1.95), "Lot outline on Esri imagery"),
             (img(fig(f"fly_{key}_2.jpg"), 1.95), "Fly-around view (lidar 3-D, true scale)"),
             (img(fig(f"texas_{key}.png"), 1.95, "contain"), "Texas location · 71 mi SE of Dallas")]
    strip_html = '<div class="strip">' + "".join(f"<figure>{i}<figcaption>{c}</figcaption></figure>" for i, c in strip) + "</div>"
    hist = " → ".join(f"{y}: {money(v, True)}" for y, v in d["hist"].items())
    b1 = box("1 · Identification & listing", kv([
        ("Address", f"{d['name']}, Corsicana TX 75109 · The Shores Ph {d['phase']} {OFF}"),
        ("Legal", f"{d['legal']} {OFF}"),
        ("CAD / Geo", f"{d['cad_id']} · {d['geo']}"),
        ("Owner", d["owner"]),
        ("Asking", f"<b>{money(d['price'])}</b> · {money(f['price_ac'])}/ac · {d['listed']} {OFF}"),
        ("Listing", f"MLS {d['mls']} · {d['agent']} · {d['agent_tel']} · <a href='{d['lh']}'>LakeHouse ad {d['ad']}</a>"),
    ]))
    b2 = box("2 · CAD value & 2026 tax", kv([
        ("CAD 2026", f"<b>{money(d['cad_mkt'])}</b> = land {money(d['cad_land'])} + {d['wall']} {money(d['cad_imp'])} {OFF}"),
        ("Taxable", f"{money(d['taxable'])}" + (" (below market on the roll: ask the CAD why)" if d["taxable"] < d["cad_mkt"] else "")),
        ("History", hist),
        ("2026 tax", f"<b>{money(d['tax26'])}</b> at {RATE:.4f}% (County .35 · College .1077 · Flood .0054 · R&B .0691 · "
                     f"Mildred ISD 1.0408) {OFF} · listing shows {d['listing_tax']} {NEW}"),
    ]))
    b3 = box("3 · Plat, boundary & corners", kv([
        ("Lot size", f"<b>{d['acres']:.3f} ac</b> legal ({d['legal_sf']:,} sf) · GIS {f['gis_sf']:,} sf "
                     f"({f['gis_sf']/43560:.3f} ac) {GIS}"),
        ("Lines", f"road {f['road_ft']:.0f} ft · water {f['lake_ft']:.0f} ft · sides "
                  f"{' / '.join('%.0f' % x['len_ft'] for x in side)} ft {GIS}"),
        ("Plat", d["plat"] + (" — east line on the “Revised 315 Deed Line”; the canal is a separate tract "
                              + NEW if is411 else "")),
    ]) + corners_table(t) + "<p style='color:#64748b'>Lat/lon of CAD GIS corners (NAD83). A survey sets the real corners.</p>")
    b4 = box("4 · Terrain & grading", kv([
        ("Ground", f"low <b>{f['zmin']:.1f}</b> · high <b>{f['zmax']:.1f}</b> · mean {f['zmean']:.1f} ft NAVD88 {GIS}"),
        ("Relief", f"{f['zmax']-f['zmin']:.1f} ft · {100*f['above320']/(f['above320']+f['below320']):.0f}% of the lot "
                   f"above 320 ft ({f['below320']:,} sf below)"),
        ("Slope", f"mean {sl['mean_pct']:.1f}% · house area {sl['env_mean_pct']:.1f}% · max over 50 ft "
                  f"<b>{sl['max50_pct']:.0f}% ({sl['max50_deg']:.1f}°)</b> at the bank"),
        ("Road→water", f"{s['road_to_pool_ft']:.0f} ft, fall {s['relief_to_pool_ft']:.1f} ft, direct angle "
                       f"<b>{s['direct_angle_deg']:.1f}°</b>; last 20 ft {s['bank20_deg']:.0f}° ({s['bank20_pct']:.0f}%)"),
        ("Pad", f"60×46 ft footprint has {pad['ground_range_ft']:.1f} ft of fall (pad ≈{pad['pad_level_ft']:.0f} ft; "
                f"≈{pad['cut_cy']+pad['fill_cy']} cy cut+fill) {EST}"),
        ("Drainage", f"surface sheets toward the canal (az. {sl['drain_az_deg']:.0f}°); POA requires a driveway culvert"),
    ]))
    dockline = (f"TRWD: 8 sf per ft of shoreline → <b>{dock['max_sf_open_water']}–{dock['max_sf_plat']} sf</b> (35 ft of open "
                f"water vs 95.8 ft plat line; TRWD decides) {CON}" if is411 else
                f"TRWD: 8 sf per ft × {dock['shore_ft']:.0f} ft → <b>max {dock['max_sf']:,} sf</b> incl. boathouse; "
                f"≥5 ft from side lines; deck ≥18 in above 320 ft {OFF}")
    b5 = box("5 · Canal, depth & dock", kv([
        ("Frontage", (f"plat line 95.8 ft on the canal tract; open water <b>25–33 ft</b> beyond the line, ≈35 ft of it opposite "
                      f"the lot; canal head vegetated/silted {NEW}" if is411 else
                      f"<b>{f['lake_ft']:.0f} ft</b> on a canal ≈{f['canal_w']:.0f} ft wide at 315 ft · {d['wall']} {GIS}")),
        ("Depth", f"TWDB 2018, within 150 ft: mean <b>{f['depth_mean']}</b> / max <b>{f['depth_max']} ft</b> at 315 ft "
                  f"(bottom {f['bottom']:.1f} ft) → today ({LAKE_NOW} ft) ≈{f['now_mean']} / {f['now_max']} ft; "
                  f"Dec 2022 low (310.6 ft) ≈{f['low22_max']} ft max {OFF}"),
        ("Drought", f"since 2000 the lake was below 312 ft on {LK['pct_days_below_312_since_2000']:.0f}% of days; "
                    f"2006 low 303.6 ft = canal dry"),
        ("Dock", dockline),
        ("Boating", "POA boat ramp and marina (slips sold to members); open lake ≈0.6 mi by canal"),
    ]))
    zpct = t["zoneA_pct_of_lot"]; zdist = zone_a_distance_ft(key)
    if zpct > 0:
        zone_txt = f"X + Zone A on {zpct:.0f}% (shore strip)"
    elif zdist is not None and zdist < 100:
        zone_txt = f"Zone X; Zone A (no BFE) starts ≈{max(5, round(zdist / 5) * 5):.0f} ft out, in the canal"
    else:
        zone_txt = ("Zone X; the canal beside the lot is not mapped; nearest Zone A ≈"
                    f"{round(zdist, -1):,.0f} ft away" if zdist else "Zone X; no Zone A nearby")
    floor = (f"proxy: max(318, Zone-A edge {za['median']}) + 2 ft = <b>≥{ffe:.1f} ft</b>" if za else
             "TRWD 100-yr 318 ft + 2 ft = <b>≥320.0 ft</b>")
    b6 = box("6 · Flood", kv([
        ("FEMA", f"{zone_txt} · FIRM 48349C0625D, 5 Jun 2012 {OFF}"),
        ("Levels", "TRWD: pool 315 · 100-yr 318 · flowage 320 ft (no building below 320 without SUP)"),
        ("Floor", f"{floor} vs pad ≈{pad['pad_level_ft']:.0f} ft → no fill {EST}"),
    ]))
    b7 = box("7 · Soil & foundation", kv([
        ("Soil", f"Crockett fine sandy loam 1–3% (CrB), 100% {OFF}: sandy loam 0–8 in, then <b>46% clay</b> to 45 in"),
        ("Shrink-swell", "<b class='r'>high</b>, LEP 9% · Ksat 0.9 µm/s · densic layer 53 in"),
        ("Foundation", "engineered post-tensioned slab or pier-and-beam; POA requires the engineer's plan; "
                       f"geotech report needed {CON}"),
    ]))
    b8 = box("8 · Septic, water & utilities", kv([
        ("Sewer", "<span class='r'>none</span> — on-site septic permitted by TRWD (POA: “start this first”) {}".format(OFF)),
        ("System", "aerobic unit + subsurface drip; surface spray banned; Ra 0.10 gal/sf/day on clay"),
        ("Lot size", ("plat pre-2008, so TRWD's 1-acre rule (lots split after 8 Apr 2011) does not apply; TCEQ ½-acre "
                      f"minimum met {NEW}") if not is411 else
                     f"pre-2008 plat ✓; legal 0.500 ac meets TCEQ ½ ac, GIS 0.487 ac — survey to confirm {CON}"),
        ("Water", f"M.E.N. WSC (TX1750015) {OFF} · no well needed · tap fee {CON}"),
        ("Power", f"underground at road (listings); Navarro County Electric Co-op {CON}"),
        ("Other", "no natural gas (propane) · internet: fixed wireless / 5G / Starlink"),
    ]))
    b9 = box("9 · HOA & county rules (same for all three)", kv([
        ("HOA", f"P.O.A. of The Shores, managed by PMI Alliance · dues <b>$1,255/yr</b> (MLS) {CON} · transfer $200"),
        ("House", "site-built, min 1,800–2,200 sf; 2–5-car garage, doors to side/rear; 6/12 roof; engineer's slab plan"),
        ("Timing", "no deadline to start; exterior done ≤9 months after the slab; approvals lapse after 2 yrs"),
        ("Use", "<b>no rentals under 90 days</b>; RV 7 days at a time; boats/trailers enclosed after 3 days"),
        ("Fees", "POA permit $2,750 (<2,500 sf) … $10,000 (≥6,000 sf); boathouse $500–750; pool $2,000"),
        ("County", f"SF-3 likely {CON}: front 35, rear 15, side 10 ft; ≤40% coverage; 2½ storeys; permit $0.25/sf"),
    ]))
    big = f"<b>{heated_range(key)} sf</b> heated"
    b10 = box("10 · Largest home & dock", kv([
        ("Footprint", f"<b>{m50['footprint_sf']:,} sf</b> incl. 3-car garage ({m50['coverage_pct']:.0f}% cover; the 40% cap "
                      f"would allow {m50['cov_max_sf']:,}) {EST}"),
        ("Home", f"{big}, 2 storeys, 6 BR — the drip field is the limit: needs {m50['drip_need_sf']:,} sf, room "
                 f"{m50['drip_avail_sf']:,} sf (50-ft set-back)"),
        ("Practical", "5,000–6,500 sf heated leaves room for a pool and yard; the largest listed Shores home is 4,252 sf"),
        ("Dock", (f"{dock['max_sf_open_water']}–{dock['max_sf_plat']} sf; walkway crosses 25–35 ft of canal tract; "
                  f"needs dredging for a lift" if is411 else f"{dock['max_sf']:,} sf covered slip + lift fits the canal")),
    ]))
    rows = [("2026 tax (actual)", money(h["tax_now"])), ("HOA dues", "$1,255"), ("Mowing (4 required)", "$240–480"),
            ("Liability insurance", "$100–200"),
            ("<b>Total now</b>", f"<b>{money(h['now_lo'])}–{money(h['now_hi'])}</b>"),
            ("After purchase", f"{money(h['after_lo'])}–{money(h['after_hi'])}"),
            ("Cost of capital 4.5%", money(h["capital"]))]
    b11 = box("11 · Holding cost per year",
              '<table class="mini">' + "".join(f"<tr><td>{a}</td><td class='n'>{b}</td></tr>" for a, b in rows) + "</table>"
              + {"lot442": "<p>Tax falls to ≈$1,530 if a 2027 protest uses the price; it rises to ≈$2,440 if the CAD drops the $142,802 taxable figure.</p>",
                 "lot411": "<p>Tax falls to ≈$1,040 if the CAD follows the price.</p>",
                 "lot441": "<p>The CAD may move the value back toward 2025 ($150k → ≈$2,360/yr). Texas's 20% limit on "
                           "increases covers 2024–2026 only and never passes to a buyer, so it would not cap that jump.</p>"}[key])
    pts = " · ".join(f"{c[0]} <b>{c[2][key][0]:g}</b>/{c[1]:g}" for c in SCORE)
    b12 = box(f"12 · Revised score <b class='big'>{d['score']:.1f}/10</b> <small>earlier {d['old_score']}</small>",
              f"<div class='bar'><i style='width:{d['score']*10:.0f}%'></i></div><p>{pts}</p>"
              "<p style='color:#64748b'>Reasons for each point: page 10.</p>")
    band = (f'<div class="band" style="background:{d["grad"]}"><div><h1>{d["name"]}, Corsicana TX</h1>'
            f'<div class="sub">The Shores on Richland Chambers Lake, Phase {d["phase"]} · Navarro County · canal lot · '
            f'MLS {d["mls"]}</div></div><div class="kpis">'
            f'<div class="kpi"><b>{money(d["price"])}</b><span>asking</span></div>'
            f'<div class="kpi"><b>{money(d["cad_mkt"])}</b><span>CAD 2026</span></div>'
            f'<div class="kpi"><b>{d["acres"]:.3f} ac</b><span>{f["gis_sf"]:,} sf GIS</span></div>'
            f'<div class="kpi"><b>{"35–96" if is411 else round(f["lake_ft"])} ft</b><span>water frontage</span></div>'
            f'<div class="kpi"><b>{f["zmin"]:.0f}–{f["zmax"]:.0f}</b><span>ground ft msl</span></div>'
            f'<div class="score" style="color:{d["acc"]}"><b>{d["score"]:.1f}</b><span>/10 · was {d["old_score"]}</span></div>'
            f'</div></div>')
    legend = ('<div class="legend">Evidence: ' + OFF + ' official record · ' + GIS + ' lidar/GIS, not a survey · ' + EST +
              ' this report’s estimate · ' + CON + ' still to confirm · ' + NEW + ' corrects the earlier report. Elevations ft NAVD88.</div>')
    flow = b1 + b2 + b3 + b4 + b5 + b6 + b7 + b8 + b9 + b10 + b11 + b12 + notes_boxes(key)
    return (f'<section class="page" style="--acc:{d["acc"]}">{band}{strip_html}{legend}'
            f'<div class="cols"><div class="flow">{flow}</div></div>{foot(page_no)}</section>')


# --------------------------------------------------------------------------- lot page 2
def fema_caption(key):
    pct, dist = T[key]["zoneA_pct_of_lot"], zone_a_distance_ft(key)
    if pct > 0:
        return f"Zone A strip along the shore ({pct:.0f}% of the lot), Zone X on the high ground"
    if dist is not None and dist < 100:
        return "Zone A in the canal, the whole lot in Zone X"
    if dist is None:
        return "no Zone A nearby: the lot and the water beside it are Zone X"
    return f"no Zone A in this view: the lot and this canal are Zone X (nearest Zone A ≈{round(dist, -1):,.0f} ft)"


def lot_page2(key, page_no):
    d = LOT[key]; t = T[key]; s = t["section"]; W = 3.9
    cells = [
        (img(fig(f"fly_{key}_1.jpg"), W), "<b>Fly-around 1</b> — from the canal; lidar 3-D at true scale (replaces realtor.com Fly Around)", False),
        (img(fig(f"fly_{key}_3.jpg"), W), "<b>Fly-around 2</b> — from the road, looking toward the water", False),
        (img(fig(f"plan_{key}.png"), W, "contain"), "<b>True-scale plan</b>: 1-ft lidar contours, CAD lot lines, corners, high/low points", False),
        (img(fig(f"terrain3d_{key}.png"), W, "contain", crop_white=True), "<b>3-D terrain</b>, vertical ×3 (fly-arounds are 1:1): lot line, 5-BR block, fall to water", False),
        (img(fig(f"section_{key}.png"), 7.82, "contain", dpi=330),
         f"<b>Section road→water</b>: left TRUE 1:1, right stretched. Length {s['road_to_pool_ft']:.0f} ft, height "
         f"{s['relief_to_pool_ft']:.1f} ft, direct angle {s['direct_angle_deg']:.1f}°, max over 50 ft {t['slope']['max50_deg']:.1f}°", True),
        (img(fig(f"maxbuild_{key}.png"), W, "contain"), "<b>Largest house + dock</b>: set-backs, 40% cap, drip field, tank, dock limit", False),
        (img(fig(f"fema_{key}.png"), W, "contain"), "<b>FEMA flood map</b> (NFHL): " + fema_caption(key), False),
        (img(fig(f"bathy_{key}.png"), W, "contain"), "<b>Canal and lake depths</b> (TWDB Dec-2018 survey) below the 315-ft pool", False),
        (img(photo(key, d["photos"]["big"]), W, "contain" if key == "lot411" else "cover"),
         f"<b>{d['photos']['big_cap']}</b> · LakeHouse.com (NTREIS)", False),
    ]
    html = "".join(f'<figure class="pf{" full" if full else ""}"><div class="fr">{im}</div><figcaption>{cap}</figcaption></figure>'
                   for im, cap, full in cells)
    band = (f'<div class="band" style="background:{d["grad"]}"><div><h1 style="font-size:12pt">{d["name"]} — maps, terrain, '
            f'largest build & photos</h1><div class="sub">Pictures ≥3.8 in wide · true-north arrows · feet · imagery © Esri, '
            f'Maxar · listing photos LakeHouse.com (NTREIS)</div></div><div class="kpis">'
            f'<div class="kpi"><b>{s["direct_angle_deg"]:.1f}°</b><span>road-to-water angle</span></div>'
            f'<div class="kpi"><b>{t["slope"]["max50_deg"]:.1f}°</b><span>max over 50 ft</span></div>'
            f'<div class="kpi"><b>{s["bank20_deg"]:.0f}°</b><span>bank, last 20 ft</span></div></div></div>')
    return f'<section class="page" style="--acc:{d["acc"]}">{band}<div class="pgrid">{html}</div>{foot(page_no)}</section>'
