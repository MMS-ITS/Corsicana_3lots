"""Big-home + private-dock due diligence and e-mail drafts for 11 Bayview Cir and 5001 Arrowhead Pt
(LOTSET=two, 10 Nov 2026). Run 15_twolots_bigbuild.py first.

Writes, in the repo root:
  Bayview-Arrowhead-BigHome-Dock-DD-and-Emails_<dd-Mon-yy>_Claude-Opus-5.5.pdf   (letter size)
and docs/twolots/{PLAN,EMAILS}.md, out/twolots/preview/*.png

Fixed-layout pages (summary, one page per lot, steps and costs, glossary) and the flowing e-mail pages are printed
separately by headless Chromium and merged with PyMuPDF; the e-mail pages get their footer stamped after the merge.
"""
import asyncio
import base64
import io
import os
import sys

import numpy as np
from PIL import Image

from common import FIG, LOTSET, ROOT
from twolots_docs import (AREA, BB, BOTTOM_LINE, CONTINGENCIES, COSTS, CREATED, DA, DB, EMAILS, GLOSSARY, HA, HB,
                          HB75, LAKE_NOW, LAKE_NOW_DATE, LOT, MODEL, NOTES, PLAN, SOURCES, SPEND, STAMP, VERDICT, money)

PDF = f"Bayview-Arrowhead-BigHome-Dock-DD-and-Emails_{STAMP}_{MODEL.replace(' ', '-')}.pdf"
OUT = os.path.join(ROOT, "out", "twolots")
os.makedirs(OUT, exist_ok=True)


def tag(kind):
    lab = {"OFF": "OFFICIAL", "GIS": "GIS", "EST": "ESTIMATE", "CON": "CONFIRM"}[kind]
    return f'<span class="tag {kind}">{lab}</span>'


OFF, GIS, EST, CON = (tag(k) for k in ("OFF", "GIS", "EST", "CON"))
_IMG = {}


def img(path, w_in, q=88):
    k = (path, w_in)
    if k not in _IMG:
        im = Image.open(path)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA"); bg = Image.new("RGB", im.size, "white"); bg.paste(im, mask=im.split()[-1]); im = bg
        else:
            im = im.convert("RGB")
        W = int(w_in * 300)
        if im.width > W:
            im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        _IMG[k] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return f'<img src="{_IMG[k]}">'


def fig(name):
    return os.path.join(FIG, name)


def box(title, body, note="", acc=None, style=""):
    n = f"<small>{note}</small>" if note else ""
    st = (f"--acc:{acc};" if acc else "") + style
    st = f' style="{st}"' if st else ""
    return f'<div class="box"{st}><h3><span>{title}</span>{n}</h3>{body}</div>'


def kv(rows):
    return '<table class="kv">' + "".join(f'<tr><td class="k">{a}</td><td>{b}</td></tr>' for a, b in rows) + "</table>"


def pn(pos, neg, alert=()):
    return ("<ul class='pn'>" + "".join(f"<li class='p'>{x}</li>" for x in pos)
            + "".join(f"<li class='m'>{x}</li>" for x in neg) + "".join(f"<li class='a'>{x}</li>" for x in alert)
            + "</ul>")


CSS = r"""
@page { size: 8.5in 11in; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Noto Sans", "DJV", sans-serif; color: #0f172a; font-size: 6.4pt; line-height: 1.18;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
a { color: inherit; }
.page { width: 8.5in; height: 11in; padding: 0.24in 0.34in 0.2in; position: relative; overflow: hidden;
        page-break-after: always; break-after: page; display: flex; flex-direction: column; background: #fff; }
.page:last-child { page-break-after: auto; break-after: auto; }
.band { border-radius: 8px; color: #fff; padding: 5px 9px; display: flex; justify-content: space-between;
        align-items: center; flex: none; gap: 8px; }
.band h1 { font-size: 13.5pt; margin: 0; line-height: 1.08; }
.band .sub { font-size: 6.9pt; margin-top: 2px; opacity: .96; }
.kpis { display: flex; gap: 4px; align-items: center; }
.kpi { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.35); border-radius: 6px;
       padding: 2px 6px; text-align: center; }
.kpi b { display: block; font-size: 10pt; line-height: 1.1; white-space: nowrap; }
.kpi span { font-size: 5.5pt; opacity: .95; white-space: nowrap; }
.legend { font-size: 5.6pt; color: #475569; margin: 3px 0 3px; flex: none; }
.box { border: 1px solid #e2e8f0; border-left: 3px solid var(--acc); border-radius: 5px; padding: 2px 5px 3px;
       margin-bottom: 4px; background: #fff; }
.box h3 { margin: 0 0 1.5px; font-size: 1.12em; color: var(--acc); display: flex; justify-content: space-between;
          align-items: baseline; gap: 6px; }
.box h3 small { font-size: 0.76em; color: #64748b; font-weight: 400; }
.box p { margin: 1px 0; }
.box ul, .box ol { margin: 1px 0 0 11px; padding: 0; } .box li { margin: 0.6px 0; }
table.kv { width: 100%; border-collapse: collapse; }
table.kv td { padding: 0.5px 1.5px; vertical-align: top; border-bottom: 0.5px dotted #e2e8f0; }
table.kv td.k { color: #475569; white-space: nowrap; padding-right: 4px; width: 1%; font-weight: 600; }
.tag { display: inline-block; font-size: 0.70em; font-weight: 700; padding: 0 2px; border-radius: 3px;
       vertical-align: 0.08em; letter-spacing: .15px; }
.OFF { background: #dcfce7; color: #166534; } .GIS { background: #dbeafe; color: #1e40af; }
.EST { background: #fef3c7; color: #92400e; } .CON { background: #fee2e2; color: #991b1b; }
.g { color: #15803d; font-weight: 700; } .w { color: #b45309; font-weight: 700; } .r { color: #b91c1c; font-weight: 700; }
ul.pn { list-style: none; margin: 1px 0 0; padding: 0; }
ul.pn li { padding-left: 10px; position: relative; margin: 1.2px 0; }
ul.pn li::before { position: absolute; left: 0; top: -0.3px; font-weight: 800; }
ul.pn li.p::before { content: "+"; color: #15803d; } ul.pn li.m::before { content: "−"; color: #b91c1c; }
ul.pn li.a::before { content: "!"; color: #c2410c; left: 2px; }
ul.pn li.a { background: #fff7ed; border-radius: 3px; }
.foot { flex: none; font-size: 5.4pt; color: #64748b; display: flex; justify-content: space-between;
        border-top: 1px solid #e2e8f0; padding-top: 2px; margin-top: 3px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.three { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; }
/* summary and back pages: render() raises .fit's font until the page is full */
.fit { flex: none; font-size: 6.6pt; margin-top: 5px; }
.sp { flex: 1 1 auto; min-height: 0; }
.card { border-radius: 7px; border: 1px solid #e2e8f0; border-top: 4px solid var(--acc); padding: 3px 6px 4px;
        background: linear-gradient(180deg, var(--tint), #fff 65%); }
.card h2 { font-size: 1.45em; margin: 0 0 1px; color: var(--acc); }
.card .cs { font-size: 0.95em; color: #334155; margin-bottom: 2px; }
.card p { margin: 2px 0 0; }
table.cmp { width: 100%; border-collapse: collapse; margin: 5px 0; }
table.cmp th { color: #fff; padding: 2px 4px; text-align: left; font-size: 1.04em; }
table.cmp td { padding: 1px 4px; border-bottom: 0.5px solid #e2e8f0; vertical-align: top; }
table.cmp td:first-child { color: #334155; font-weight: 700; white-space: nowrap; width: 1.45in; }
table.cmp tr:nth-child(even) td { background: #f8fafc; }
table.cmp tr.grp td { background: #eef2ff; color: #1e3a8a; font-weight: 800; }
table.plan { width: 100%; border-collapse: collapse; margin-bottom: 5px; }
table.plan th { background: #1e3a8a; color: #fff; text-align: left; padding: 2px 4px; }
table.plan td { padding: 1.2px 4px; border-bottom: 0.5px solid #e2e8f0; vertical-align: top; }
table.plan { table-layout: fixed; }
table.plan td.st { font-weight: 800; color: #fff; text-align: center; }
table.plan td.n { white-space: nowrap; }
table.mini { width: 100%; border-collapse: collapse; }
table.mini td, table.mini th { padding: 0.6px 2px; border-bottom: 0.5px solid #eef2f7; text-align: left; vertical-align: top; }
table.mini th { color: #475569; background: #f8fafc; }
table.mini td.n { text-align: right; white-space: nowrap; }
/* lot pages */
.row1 { display: grid; grid-template-columns: 3.95in 1fr; gap: 6px; height: 3.2in; flex: none; margin-top: 2px; }
.planfig { margin: 0; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; background: #fff; height: 3.2in;
        display: flex; flex-direction: column; }
.planfig .im { flex: 1 1 auto; min-height: 0; }
.planfig img, .xs img { width: 100%; height: 100%; object-fit: contain; display: block; }
.planfig figcaption { flex: none; background: #334155; color: #fff; font-size: 5.3pt; padding: 1px 4px; }
.xs figcaption { position: absolute; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,.72);
       color: #fff; font-size: 5.3pt; padding: 1px 4px; }
.fitbox { height: 3.2in; overflow: hidden; font-size: 6.6pt; }
.fitbox .box { height: 100%; margin: 0; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; flex: none; margin-top: 5px; }
.xs { margin: 0; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; height: 2.12in; position: relative;
      background: #fff; padding-bottom: 0.14in; }
.xs.t { border-color: #1e3a8a; } .xs.v { border-color: #ef4444; }
.cols { flex: 1 1 auto; position: relative; min-height: 0; margin-top: 5px; }
.flow { position: absolute; inset: 0; column-count: 3; column-gap: 6px; column-fill: auto; font-size: 6.6pt; }
.flow .box { break-inside: auto; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.flow .box h3 { break-after: avoid; }
.flow tr, .flow li, .flow p { break-inside: avoid; }
"""

CSS_MAIL = r"""
@page { size: 8.5in 11in; margin: 0.42in 0.4in 0.5in; }
* { box-sizing: border-box; }
body { font-family: "Noto Sans", "DJV", sans-serif; color: #0f172a; font-size: 7.6pt; line-height: 1.3; margin: 0;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 14pt; margin: 0 0 2px; color: #fff; background: linear-gradient(95deg,#1e3a8a,#0f766e 55%,#6d28d9);
     padding: 6px 9px; border-radius: 8px; }
.sub { font-size: 7.2pt; color: #334155; margin: 4px 0 8px; }
.mails { column-count: 2; column-gap: 12px; }
.mail { break-inside: auto; border: 1px solid #cbd5e1; border-left: 4px solid var(--acc); border-radius: 6px;
        margin: 0 0 8px; padding: 4px 7px 5px; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.mail h3, .mail .meta { break-after: avoid; break-inside: avoid; }
.mail pre { orphans: 3; widows: 3; }
.idx { border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 7px; margin: 0 0 8px; background: #f8fafc;
       column-count: 2; column-gap: 12px; font-size: 6.9pt; }
.idx ol { margin: 0 0 0 14px; padding: 0; } .idx li { margin: 0.5px 0; break-inside: avoid; }
.mail h3 { margin: 0 0 2px; font-size: 8.6pt; color: var(--acc); display: flex; justify-content: space-between; gap: 6px; }
.mail h3 .chip { font-size: 6.4pt; color: #fff; background: var(--acc); border-radius: 8px; padding: 0.5px 6px;
        white-space: nowrap; align-self: center; }
.mail .meta { font-size: 6.9pt; color: #334155; margin-bottom: 3px; border-bottom: 0.5px dotted #cbd5e1; padding-bottom: 2px; }
.mail pre { white-space: pre-wrap; font-family: "Noto Sans", "DJV", sans-serif; font-size: 7.15pt; line-height: 1.28; margin: 0; }
"""


def FONTS():
    """DejaVu Sans fills symbols Noto Sans lacks (≈ → ≤ ≥ ⅓ ✓). Weight ranges let 600-weight text use the bold face."""
    import matplotlib
    ttf = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    return (f'@font-face {{ font-family: "DJV"; src: url("file://{ttf}/DejaVuSans.ttf"); font-weight: 100 549; }}\n'
            f'@font-face {{ font-family: "DJV"; src: url("file://{ttf}/DejaVuSans-Bold.ttf"); font-weight: 550 900; }}\n'), ttf


def foot(n, total):
    return (f'<div class="foot"><span>11 Bayview Cir &amp; 5001 Arrowhead Pt · largest home, private dock and due-diligence '
            f'plan · desk study from public records, not a survey, design or permit decision</span>'
            f'<span>created {CREATED:%d %b %Y} · {MODEL} · p {n}/{total}</span></div>')


LEGEND = ('<div class="legend">Evidence: ' + OFF + ' official record · ' + GIS + ' lidar/GIS, not a survey · ' + EST +
          ' this report’s estimate · ' + CON + ' still to confirm with the named party. Elevations in ft above sea '
          f'level (NAVD88). Lake {LAKE_NOW} ft on {LAKE_NOW_DATE}, 2.84 ft below full pool.</div>')


# --------------------------------------------------------------------------- page 1
def summary_page(total):
    a, b = LOT["bayview"], LOT["arrowhead"]

    def card(k):
        d = LOT[k]
        return (f'<div class="card" style="--acc:{d["acc"]};--tint:{d["acc"]}18"><h2>{d["L"]} · {d["name"]}</h2>'
                f'<div class="cs">{d["sub"]} · {d["acres"]:.2f} ac · asking {money(d["price"])} · CAD {money(d["cad"])} · '
                f'MLS {d["mls"]}</div><p>{VERDICT[k]}</p></div>')
    rows = [
        ("grp", "Largest home"),
        ("Largest footprint", f"{HA['W']}×{HA['D']} ft = <b>{HA['footprint_sf']:,} sf</b> incl. 3-car garage {EST}",
         f"{HB['W']}×{HB['D']} ft = <b>{HB['footprint_sf']:,} sf</b> (drip 50 ft from pool) {EST}"),
        ("Heated, 2 storeys", f"<b>≈{HA['heated_2st_sf']:,} sf</b> (2½ storeys allowed: ≈{HA['heated_25st_sf']:,})",
         f"<b>≈{HB75['heated_2st_sf']:,}–{HB['heated_2st_sf']:,} sf</b> (75- or 50-ft drip set-back)"),
        ("What limits it", f"set-backs on a wedge-shaped lot and Zone A; the 40% cover cap ({HA['cov_max_sf']:,} sf) "
                           f"is not reached {GIS}",
         f"the drip field: {HB['q_gpd']} gal/day needs {HB['drip_need_sf']:,} sf of drip {EST}"),
        ("Sensible size", "5,000–7,000 sf heated; White Rock homes median ≈$1.2M (CAD)",
         "4,000–5,500 sf; the top Rustling Oaks homes are 2,200–3,500 sf"),
        ("Minimum / rules", f"2,500 sf, site-built, ≥60% stone &amp; glass (listing) {CON}; CC&Rs not online",
         f"1,600 sf; 5-ft side/rear; no wells; walls + roof done in 120 days {OFF}"),
        ("Sewer", f"HOA plant, permit 8,000 gal/day; TCEQ order for 2023–24 violations {OFF}",
         f"aerobic unit + drip; TRWD permit $400; 1-acre rule n/a (1990 plat) {OFF}"),
        ("grp", "Private dock"),
        ("TRWD size limit", f"<b>{DA['cap_sf']:,} sf</b> (formula {DA['cap_formula_sf']:,}; above 1,200 sf needs 20 ft from "
                            f"side lines) {OFF}", f"<b>{DB['cap_sf']:,} sf</b> (8 sf × {DB['frontage_ft']:.0f} ft) {OFF}"),
        ("Water in front", f"basin {DA['width315_min']:.0f}–{DA['width315_max']:.0f} ft across at 315 ft; "
                           f"{DA['width_at_dock']:.0f} ft at the dock {GIS}",
         f"{DB['width315_min']:.0f}–{DB['width315_max']:.0f} ft (channel + cove); {DB['width_at_dock']:.0f} ft at the dock {GIS}"),
        ("Dock that fits", f"{DA['L']:.0f}×{DA['P']:.0f} ft at the shore; ≥{DA['passage_left']:.0f} ft passage left {EST}",
         f"{DB['L']:.0f}×{DB['P']:.0f} ft after a {DB['w0']:.0f}-ft walkway; {DB['passage_left']:.0f} ft passage {EST}"),
        ("Depth over the lift", f"<span class='r'>unknown</span>: basin not surveyed (nearest TWDB point "
                                f"{DA['nearest_sounding_ft']} ft away) {CON}",
         f"{DB['depth_pool']} ft full pool · <b>{DB['depth_now']} ft today</b> · {DB['depth_low22']} ft at the Dec-2022 "
         f"low {GIS}"),
        ("Boathouses nearby", f"977 + 1,024 sf, both 2023, same basin {OFF}", f"seller's 936 sf at 5003 (2013) {OFF}"),
        ("grp", "Money and risk"),
        ("Holding cost / yr", f"≈$4.9k: HOA $3,530 + tax {money(a['tax'])}",
         f"≈$1.1–1.7k: POA $144 + tax {money(b['tax'])} now, ≈$1,540 after a sale"),
        ("Spend before committing", f"{SPEND['bayview']}: survey + soundings", f"{SPEND['arrowhead']}: survey + septic evaluation"),
        ("Biggest open question", "basin depth; the HOA sewer plant's finances", "the 120-day build rule; over-building; "
                                                                               "where the lot line meets the water"),
    ]
    tr = []
    for r in rows:
        if r[0] == "grp":
            tr.append(f"<tr class='grp'><td colspan='3'>{r[1]}</td></tr>")
        else:
            tr.append(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>")
    table = (f"<table class='cmp'><tr><th style='background:#334155'>Feasibility</th>"
             f"<th style='background:{a['acc']}'>A · 11 Bayview Cir (White Rock)</th>"
             f"<th style='background:{b['acc']}'>B · 5001 Arrowhead Pt (Rustling Oaks)</th></tr>{''.join(tr)}</table>")
    start = box("Start here", "<ol>"
                f"<li><b>This week, $0:</b> send the e-mails on pages 5–{total - 1}; visit both lots while the lake is low and "
                "sound both dock spots with a marked pole.</li>"
                "<li><b>Pick one lot</b> once TRWD, the HOA/POA and the agents answer. Do not pay for surveys on both.</li>"
                "<li><b>Offer with a 21–30-day option</b> (fee $200–500). Spend on the survey, and the septic evaluation "
                "for B, only inside the option period.</li>"
                "<li><b>Before the option ends:</b> TRWD's dock answer in writing, plus the HOA sewer letter (A) or a "
                "passing septic evaluation (B).</li></ol>", "costs and walk-away triggers: page 4",
                acc="#1e3a8a")
    alerts = box("Top alerts", pn([], [], [
        "A: nobody has measured the basin depth; neighbours' boathouses already use part of the basin",
        "A: the HOA sewer plant broke its permit limits in 2023–24, and TCEQ deferred most of the penalty for "
        "inability to pay",
        "B: CC&Rs require outside walls and roof within 120 days of the start, and ban owner wells",
        "B: a house over ≈3,500 sf would be the largest in Rustling Oaks by far",
        "Both: the lake was below 312 ft on 27% of days since 2000; clay soil needs an engineered foundation"]),
        acc="#c2410c")
    band = ('<div class="band" style="background:linear-gradient(95deg,#1e3a8a,#0f766e 50%,#6d28d9)"><div>'
            '<h1>11 Bayview Cir &amp; 5001 Arrowhead Pt — largest home, private dock, first steps</h1>'
            f'<div class="sub">Richland-Chambers Lake, Navarro County, Texas · feasibility check, due-diligence plan and '
            f'e-mail drafts · {CREATED:%d %B %Y}</div></div><div class="kpis">'
            f'<div class="kpi"><b>{LAKE_NOW} ft</b><span>lake {LAKE_NOW_DATE}</span></div>'
            '<div class="kpi"><b>14</b><span>e-mail drafts</span></div></div></div>')
    bottom = box("Bottom line", f"<p>{BOTTOM_LINE}</p>", "advice, not a guarantee", acc="#0f172a",
                 style="background:#f8fafc")
    body = (f'<div class="fit"><div class="two">{card("bayview")}{card("arrowhead")}</div>{table}{bottom}'
            f'<div class="two">{start}{alerts}</div></div>')
    return (f'<section class="page" style="--acc:#1e3a8a">{band}{LEGEND}{body}<div class="sp"></div>'
            f'{foot(1, total)}</section>')


# --------------------------------------------------------------------------- lot pages
def lot_page(k, n, total):
    d = LOT[k]; h = HA if k == "bayview" else HB; dk = DA if k == "bayview" else DB
    isA = k == "bayview"
    plan = (f'<figure class="planfig"><div class="im">{img(fig(f"bigbuild_{k}.png"), 3.95)}</div><figcaption><b>True-scale '
            f'plan</b>, rotated (arrow = true north): largest house, ' + ("" if isA else "drip field, ")
            + "dock, water at full pool and today</figcaption></figure>")
    if isA:
        home = kv([
            ("Limit", f"building envelope: 35/15/10-ft set-backs, ground ≥322 ft, out of Zone A = "
                      f"<b>{BB[k]['info']['env_sf']:,} sf</b> {GIS}"),
            ("Footprint", f"<b>{h['W']}×{h['D']} ft = {h['footprint_sf']:,} sf</b> incl. 3-car garage and porches; "
                          f"{h['coverage_pct']:.0f}% of the lot (cap 40% = {h['cov_max_sf']:,} sf) {EST}"),
            ("Heated", f"<b>≈{h['heated_2st_sf']:,} sf</b> on two storeys; ≈{h['heated_25st_sf']:,} sf with a half-storey "
                       f"(zoning allows 2½) {EST}"),
            ("Rear half", f"{h['rear_half_used_sf']:,} of {h['rear_half_sf']:,} sf used; the 50% limit is not reached {GIS}"),
            ("Sensible", "5,000–7,000 sf heated leaves room for a pool, parking and the view corridor; an L-shaped plan "
                         "can use more of the wedge"),
            ("Sewer", f"White Rock HOA plant (no septic). TCEQ design flow for this size ≈{h['q_gpd']} gal/day, 7.5% of "
                      f"the plant's 8,000 gal/day permit {OFF}"),
            ("HOA rules", f"site-built, ≥2,500 sf, ≥60% stone &amp; glass (listing) {CON}; height, water set-back, "
                          f"build-time and boathouse rules unknown {CON}"),
            ("Zoning", f"likely SF-3 {CON}: front 35, rear 15, side 10 ft; ≤40% cover; 2½ storeys; county permit $0.25/sf"),
            ("Zone A", f"{BB[k]['info']['zoneA_sf']:,} sf (13%) of the lot along the water, kept clear {OFF}"),
        ])
    else:
        home = kv([
            ("Limit", f"<b>drip field</b>: a {h['heated_2st_sf']:,}-sf, 6-bedroom house needs {h['q_gpd']} gal/day ÷ 0.10 "
                      f"= {h['drip_need_sf']:,} sf of drip; room left {h['drip_avail_sf']:,} sf {EST}"),
            ("Footprint", f"<b>{h['W']}×{h['D']} ft = {h['footprint_sf']:,} sf</b> incl. 3-car garage ({h['coverage_pct']:.0f}% "
                          f"of the lot; cap 40% = {h['cov_max_sf']:,} sf) {EST}"),
            ("Heated", f"<b>≈{h['heated_2st_sf']:,} sf</b> on two storeys with drip 50 ft from the pool; "
                       f"≈{HB75['heated_2st_sf']:,} sf at 75 ft {EST}"),
            ("CC&Rs", f"Ph II Declaration, Vol 1224 p 638 (1991): ≥1,600 sf heated; ≥5 ft side/rear; 30-ft street "
                      f"easement; no wells; no metal storage buildings; metal roof only with ACC; walls + roof done "
                      f"≤120 days after start {OFF}"),
            ("ACC fees", f"$500 road fee + $0.85/sf of slab (≈{money(0.85 * h['footprint_sf'])} here), boathouse $750, "
                         f"pool $1,000 (2024 schedule) {OFF}"),
            ("Septic", f"aerobic + subsurface drip by an RS/PE; TRWD permit $400. 1-acre rule n/a: final plat 1 Nov 1990 "
                       f"{OFF}; legal 0.500 ac meets TCEQ's ½ ac {CON}"),
            ("Sensible", "4,000–5,500 sf heated: still the biggest home in the subdivision; leaves room for a pool"),
            ("Zoning", f"likely SF-3 {CON}: front 35, rear 15, side 10 ft; ≤40% cover; 2½ storeys"),
        ])
    homebox = '<div class="fitbox">' + box("Largest home: feasibility", home, "test fit, not a design") + '</div>'
    xs = (f'<div class="row2"><figure class="xs t">{img(fig(f"dockxs_{k}_true.png"), 3.86)}<figcaption>'
          f'<b>True scale 1:1</b> section through the dock, across the water</figcaption></figure>'
          f'<figure class="xs v">{img(fig(f"dockxs_{k}_ve.png"), 3.86)}<figcaption><b>Same section, vertical '
          f'exaggeration ×{dk.get("ve_drawn", 4):.0f}</b> (heights stretched to show depth)</figcaption></figure></div>')
    if isA:
        dock = kv([
            ("Size", f"TRWD: 8 sf/ft to 150 ft + 4 sf/ft above → {dk['cap_formula_sf']:,} sf; keep ≤<b>1,200 sf</b> so "
                     f"the 5-ft side clearance applies (20 ft above 1,200) {OFF}"),
            ("Water", f"the lot fronts a basin at the head of a channel, {dk['width315_min']:.0f}–{dk['width315_max']:.0f} ft "
                      f"across at 315 ft, {dk['width_at_dock']:.0f} ft at the dock spot {GIS}"),
            ("Fit", f"<b>{dk['L']:.0f}×{dk['P']:.0f} ft = {dk['area']:,.0f} sf</b> at the bulkhead; reach ≤⅓ of the width "
                    f"(≈{dk['lim']:.0f} ft); ≥{dk['passage_left']:.0f} ft left to the far shore or a neighbour {EST}"),
            ("Depth", f"<span class='r'>not surveyed</span>: TWDB 2018 soundings stop {dk['nearest_sounding_ft']} ft away, "
                      f"where the bottom is 306.3 ft (8.7 ft at full pool, 5.9 ft today). Sound it {CON}"),
            ("Neighbours", f"218 White Rock: 1,024-sf boathouse; 114 Bayview: 977 sf; both 2023 {OFF}"),
            ("Wall", f"steel bulkhead, CAD 170 ft, 2015, 38% good; TRWD permit? {CON}"),
            ("Rules", f"permit $300; ≤2 storeys; roof ≤6/12; not enclosed (one 20-sf store); no toilets; lower deck ≥18 in "
                      f"above 320 ft; lights if &gt;50 ft out {OFF}"),
        ])
    else:
        dp = dk["deepest"]
        dock = kv([
            ("Size", f"TRWD: 8 sf × {dk['frontage_ft']:.0f} ft = <b>{dk['cap_sf']:,} sf</b> incl. boathouse; one walkway "
                     f"≤8 ft wide not counted {OFF}"),
            ("Water", f"a narrow channel (≈{dk['width315_min']:.0f} ft) meets a wider cove; {dk['width_at_dock']:.0f} ft "
                      f"across at the dock spot {GIS}"),
            ("Fit", f"<b>{dk['L']:.0f}×{dk['P']:.0f} ft = {dk['area']:,.0f} sf</b> after a {dk['w0']:.0f}-ft walkway; "
                    f"reaches {dk['reach_ft']:.0f} ft from the 315-ft edge, inside ⅓ of the width; {dk['passage_left']:.0f} ft "
                    f"passage {EST}"),
            ("Depth", f"over the lift: <b>{dk['depth_pool']} ft</b> at full pool, <b>{dk['depth_now']} ft</b> today, "
                      f"{dk['depth_low22']} ft at the Dec-2022 low (TWDB 2018 survey; nearest sounding {dk['nearest_sounding_ft']} ft) {GIS}"),
            ("Deeper", f"a {dp['w0']:.0f}-ft walkway (reach {dp['reach_ft']} ft) gives {dp['depth_pool']} / {dp['depth_now']} / "
                       f"{dp['depth_low22']} ft; TRWD prefers the shortest reach that works {EST}"),
            ("Lot line", f"CAD GIS line {dk['lotline_to_water_range'][0]:.0f}–{dk['lotline_to_water_range'][1]:.0f} ft back "
                         f"from the 315-ft edge, near 320 ft: survey and TRWD to confirm the shoreline {CON}"),
            ("Wall", f"steel, CAD 100 ft, 2020, 68% good; TRWD permit? {CON} · seller's boathouse at 5003: 936 sf {OFF}"),
        ])
    notes = NOTES[k]
    flow = (box("Private dock: feasibility", dock)
            + box("Positives (+), negatives (−) and alerts (!)", pn(notes["pos"], notes["neg"], notes["alert"]))
            + box("Before you commit to this lot", "<ol>" + "".join(f"<li>{x}</li>" for x in notes["steps"]) + "</ol>",
                  "offer prices are estimates")
            + box("Budget for the big build", '<table class="mini">' + "".join(
                f"<tr><td>{a}</td><td class='n'>{b}</td><td class='n'><b>{c}</b></td></tr>" for a, b, c in COSTS[k])
                + "</table><p style='color:#64748b'>2026 Texas lake-home ranges; get two bids. Boathouse CAD values "
                  "nearby are $49–78k (depreciated).</p>", EST))
    kp = (f'<div class="kpi"><b>{money(d["price"])}</b><span>asking</span></div>'
          f'<div class="kpi"><b>{money(d["cad"])}</b><span>CAD 2026</span></div>'
          f'<div class="kpi"><b>≈{h["heated_2st_sf"]/1000:.1f}k sf</b><span>max heated (theory)</span></div>'
          f'<div class="kpi"><b>{dk["cap_sf"]:,} sf</b><span>max dock</span></div>'
          f'<div class="kpi"><b>{("?" if isA else str(dk["depth_now"]) + " ft")}</b><span>depth at lift today</span></div>')
    band = (f'<div class="band" style="background:{d["grad"]}"><div><h1>{d["L"]} · {d["name"]}, '
            f'{d["town"].rsplit(" ", 1)[0]}</h1>'
            f'<div class="sub">{d["sub"]} · {d["acres"]:.2f} ac · CAD {d["cad_id"]} · MLS {d["mls"]}<br>owner: '
            f'{d["owner"]}</div></div><div class="kpis">{kp}</div></div>')
    return (f'<section class="page" style="--acc:{d["acc"]}">{band}{LEGEND}<div class="row1">{plan}{homebox}</div>{xs}'
            f'<div class="cols"><div class="flow">{flow}</div></div>{foot(n, total)}</section>')


# --------------------------------------------------------------------------- page 4
def steps_page(n, total):
    col = {"0": "#0f766e", "1": "#1e3a8a", "2": "#6d28d9", "3": "#b45309"}
    who = {"both": "A + B", "one": "chosen lot", "B": "B only"}
    rows = "".join(f"<tr><td class='st' style='background:{col[s]}'>{s}</td><td class='n'><b>{w}</b></td><td>{t}</td>"
                   f"<td>{c}</td><td class='n'>{who[l]}</td></tr>" for s, w, t, c, l in PLAN)
    table = ("<table class='plan'><colgroup><col style='width:0.42in'><col style='width:0.85in'><col>"
             "<col style='width:1.75in'><col style='width:0.7in'></colgroup>"
             "<tr><th>Stage</th><th>When</th><th>What</th><th>Cost</th><th>Lot</th></tr>"
             f"{rows}</table>")
    spend = box("What to spend before committing", kv([
        ("Lot A", f"<b>{SPEND['bayview']}</b>: option fee, survey with soundings, resale certificate"),
        ("Lot B", f"<b>{SPEND['arrowhead']}</b>: the same plus the septic site evaluation"),
        ("Both at once", "≈$5–10k. Not worth it: use the free answers to choose, then spend on one lot"),
        ("After closing", "geotech $1.8–3k, design, TRWD dock $300, OSSF $400 (B), county $0.25/sf, ACC fees (B)"),
    ]), acc="#0f766e")
    cont = box("Put these in the offer", "<ul>" + "".join(f"<li>{x}</li>" for x in CONTINGENCIES) + "</ul>",
               acc="#1e3a8a")
    walk = box("Walk away if", "<ul>"
               "<li><b>A:</b> the basin is under ≈4 ft at full pool where the boathouse would go and TRWD will not "
               "allow dredging.</li>"
               "<li><b>A:</b> the HOA cannot confirm a sewer tap, or a large special assessment for the plant is "
               "coming.</li>"
               "<li><b>A:</b> the CC&Rs cap height, size or the water set-back below your plan.</li>"
               "<li><b>B:</b> the septic evaluation will not support the bedrooms you want.</li>"
               "<li><b>B:</b> the survey finds 5003's septic or utilities on Lot 33, or the plat line leaves TRWD "
               "unwilling to permit the dock.</li>"
               "<li><b>B:</b> the ACC will not give a workable reading of the 120-day rule.</li></ul>",
               acc="#b91c1c")
    order = box("Approvals, in order", "<ol>"
                "<li>HOA (A) or ACC (B) written approval of plans, plot plan and materials (B: valid 6 months).</li>"
                "<li>TRWD: dock / boathouse permit ($300), wall work, and the septic permit for B ($400).</li>"
                "<li>Navarro County building permit: site/survey plan, OSSF permit number (B), $0.25/sf of heated area.</li>"
                "<li>Three third-party inspections: foundation (before concrete), framing/MEP, final.</li>"
                "<li>911 address through the building permit.</li></ol>",
                acc="#6d28d9")
    timeline = box("Typical timeline", kv([
        ("Weeks 0–2", "e-mails, site visit, depth check, TRWD pre-application call"),
        ("Weeks 2–6", "offer, option period: survey, septic evaluation (B), HOA/POA documents"),
        ("Weeks 6–10", "closing (30–45 days after contract)"),
        ("Months 3–8", "design, geotech, approvals (TRWD review 10 + up to 30 business days)"),
        ("Months 8–24", "build 12–16 months; B: walls and roof within 120 days of the start"),
    ]), acc="#0f766e")
    area = box("The area: positives (+), negatives (−) and alerts (!) for both lots", pn(AREA["pos"], AREA["neg"],
                                                                                    AREA["alert"]),
               acc="#334155")
    band = ('<div class="band" style="background:linear-gradient(95deg,#0f766e,#1e3a8a 55%,#6d28d9)"><div>'
            '<h1>First steps and money before a final decision</h1><div class="sub">Spend nothing until the answers '
            'come back, then spend only on the lot you choose, inside a paid option period</div></div>'
            '<div class="kpis"><div class="kpi"><b>$0</b><span>stage 0</span></div>'
            f'<div class="kpi"><b>{SPEND["bayview"]}</b><span>Lot A before closing</span></div>'
            f'<div class="kpi"><b>{SPEND["arrowhead"]}</b><span>Lot B before closing</span></div></div></div>')
    body = (f'<div class="fit">{table}<div class="three">{spend}{cont}{walk}</div>'
            f'<div class="two"><div>{order}{timeline}</div><div>{area}</div></div></div>')
    return (f'<section class="page" style="--acc:#1e3a8a">{band}{body}<div class="sp"></div>{foot(n, total)}</section>')


def mail_index():
    short = {
        "Listing agent — 11 Bayview Cir": "disclosure, survey, CC&Rs, sewer stub, wall permit, sales, intermediary terms",
        "Listing agent — 5001 Arrowhead Pt": "disclosure, survey, 5003's systems on Lot 33?, wall permit, $644 vs $144",
        "HOA — White Rock Homeowners Association": "CC&Rs, dues, assessments, sewer plant status and capacity, tap",
        "POA — Rustling Oaks Estates POA and ACC": "dues, the 120-day rule, boathouse rules, roof, lawsuit, fees",
        "TRWD — Richland-Chambers permits (docks, walls, septic)": "dock size and reach, dredging, shoreline, walls, septic",
        "Navarro County Planning & Development": "zoning district, height, Zone A, accessory dwelling, permits",
        "Navarro CAD — value questions": "2027 value after a sale, Lot 11's low land value",
        "Utilities — water and electric": "1-in meter, tap fees, 400-amp service to house and boathouse",
        "Surveyor — request for quote": "boundary, topo, 315/320 lines, encroachments, depths",
        "Septic designer / site evaluator (Lot B)": "6-BR aerobic + drip layout, 5003's system",
        "Geotechnical engineer — request for quote": "borings, PVR, slab/pier design near the wall",
        "Dock builder — budget and site visit": "boathouse + lift budget, soundings, dredging, walls",
        "Title company — preliminary title": "easements, CC&Rs, liens, Lots 32/33 agreements",
        "Insurance agent — quotes for budgeting": "builder's risk, wind/hail, flood, boathouse",
    }
    return "".join(f"<li><b>{e['group'].split(' — ')[0].split(' / ')[0]}:</b> {short.get(e['group'], '')}</li>" for e in EMAILS)


# --------------------------------------------------------------------------- back page
def back_page(n, total):
    gl = box("Glossary", '<table class="mini">' + "".join(f"<tr><td><b>{a}</b></td><td>{b}</td></tr>" for a, b in GLOSSARY)
             + "</table>", acc="#0f766e")
    src = box("Sources (read 8–10 Nov 2026)", "<ul>" + "".join(f"<li>{s}</li>" for s in SOURCES) + "</ul>",
              acc="#1e3a8a")
    method = box("How the largest home and dock were found", "<ul>"
                 "<li>House: every rectangle (44–136 × 36–116 ft, six angles, 5-ft grid) inside the set-back envelope "
                 "(ground ≥322 ft, out of Zone A) was tested, largest first. A rectangle passes if it meets the 40% "
                 "cover cap and the 50% rear-half rule, and, for B, leaves enough drip field after the house, "
                 "driveway, garage apron and tank pad. The footprint includes a 960-sf garage and 360 sf of porches; "
                 "heated area = 2 × (footprint − garage − porches).</li>"
                 "<li>Septic flow (B): TCEQ Table III with water-saving fixtures, the larger of 6 bedrooms (420 gal/day) "
                 "and the heated-area tier (+60 gal/day per 1,500 sf over 5,500 sf); drip area = flow ÷ 0.10.</li>"
                 "<li>Dock: lines were cast every foot along the frontage, perpendicular to it, to measure the water "
                 "width at 315 ft on the 2022 lidar. A boathouse passes if its outer edge stays within ⅓ of that width "
                 "and leaves ≥20 ft to the far shore or a neighbour's boathouse, and it sits ≥5 ft inside the side lines "
                 "drawn perpendicular to the shore. Depth comes from the TWDB 2018 contours and soundings; it counts as "
                 "measured only where a sounding lies within 60 ft.</li></ul>",
                 acc="#6d28d9")
    limits = box("Limits", "<p>This is a desk study with no site visit. It is not a survey, design, appraisal, legal "
                 "opinion or permit decision. Lot lines are CAD GIS lines and can be off by several feet; the house and "
                 "dock shapes are test fits, not designs. White Rock's CC&Rs and the county zoning map are not online, so "
                 "items marked CONFIRM need the HOA, the county or TRWD. Costs are 2026 ranges for budgeting only. "
                 "Phone numbers come from each agency's own pages, except Winkler WSC (nonprofit listing) and the "
                 "dock builders (their own listings).</p>",
                 acc="#b91c1c")
    end = box("End note", f"<p><b>Date of creation:</b> {CREATED:%d %B %Y} · <b>Prepared by AI model:</b> {MODEL} "
              f"(Anthropic), working in Kiro · <b>File:</b> {PDF}</p><p>Earlier reports in this repository: the 8 Nov 2026 "
              "two-lot due diligence (Richland-Chambers-2-Lots-Due-Diligence_08-Nov-26_Claude-Opus-5.5.pdf) and the "
              "10 Nov 2026 Shores re-check. This document adds the largest-home and dock checks, the first-steps plan "
              "and the e-mail drafts for the two original lots.</p>",
              acc="#0f172a", style="background:#f8fafc")
    band = ('<div class="band" style="background:linear-gradient(95deg,#334155,#1e3a8a 60%,#0f766e)"><div>'
            '<h1>Glossary, sources, method and limits</h1><div class="sub">How to read the tags and numbers in this '
            'document</div></div></div>')
    body = f'<div class="fit"><div class="two"><div>{gl}</div><div>{src}{method}</div></div>{limits}{end}</div>'
    return f'<section class="page" style="--acc:#1e3a8a">{band}{body}<div class="sp"></div>{foot(n, total)}</section>'


# --------------------------------------------------------------------------- e-mail pages
def mails_html(scale=1.0):
    fonts, _ = FONTS()
    css = CSS_MAIL + (f"\nbody {{ font-size: {7.6 * scale:.2f}pt; }} .mail pre {{ font-size: {7.15 * scale:.2f}pt; }}"
                      f" .mail .meta {{ font-size: {6.9 * scale:.2f}pt; }} .idx {{ font-size: {6.9 * scale:.2f}pt; }}")
    acc = {"A": "#0f766e", "B": "#6d28d9", "A + B": "#1e3a8a"}
    lab = {"A": "Lot A · Bayview", "B": "Lot B · Arrowhead", "A + B": "both lots"}
    mails = "".join(f"<div class='mail' style='--acc:{acc[e['lots']]}'><h3><span>{i + 1}. {e['group']}</span>"
                    f"<span class='chip'>{lab[e['lots']]}</span></h3><div class='meta'><b>To:</b> {e['to']}<br>"
                    f"<b>Subject:</b> {e['subject']}</div><pre>{e['body']}</pre></div>" for i, e in enumerate(EMAILS))
    head = ("<h1>Due-diligence e-mail drafts — 11 Bayview Cir &amp; 5001 Arrowhead Pt</h1><div class='sub'>One e-mail per "
            "listing agent and association, and one per authority or contractor covering both lots, so each office "
            "answers once. Replace the bracketed name and contact lines before sending. Where no e-mail address is "
            "published, the line says so; call or use the office's web form. Send them all this week: they cost "
            "nothing and the answers decide which lot is worth a survey.</div>"
            f"<div class='idx'><ol>{mail_index()}</ol></div>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts}{css}</style></head><body>{head}"
            f"<div class='mails'>{mails}</div></body></html>")


def fixed_html(pages):
    fonts, _ = FONTS()
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>Bayview &amp; Arrowhead — big home and dock ({STAMP})"
            f"</title><style>{fonts}{CSS}</style></head><body>{''.join(pages)}</body></html>")


async def render(html_path, pdf_path, fixed=True):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 816, "height": 1056})
        await pg.goto("file://" + html_path, wait_until="load")
        # load both fallback faces, then rebuild the DOM so every text run is shaped with them available
        await pg.evaluate("""async () => {
          await Promise.all([document.fonts.load('400 10px DJV', '≈→≤≥⅓✓'), document.fonts.load('700 10px DJV', '≈→≤≥⅓✓')]);
          document.body.innerHTML = document.body.innerHTML;
          await Promise.all(Array.from(document.images).map(i => i.decode().catch(() => null)));
          await document.fonts.ready; }""")
        await pg.wait_for_timeout(400)
        notes = []
        if fixed:
            notes = await pg.evaluate("""() => {
              const out = [];
              const search = (set, ok, lo0, hi0) => {
                let lo = lo0, hi = hi0;
                if (!ok(lo)) { set(lo); return 'no fit at ' + lo; }
                for (let i = 0; i < 16; i++) { const mid = (lo + hi) / 2; if (ok(mid)) lo = mid; else hi = mid; }
                const pt = Math.floor((lo - 0.1) * 20) / 20; set(pt); ok(pt); return pt;
              };
              document.querySelectorAll('.fitbox').forEach((el) => {
                const set = (pt) => { el.style.fontSize = pt + 'pt'; };
                out.push('fitbox ' + search(set, (pt) => { set(pt); return el.scrollHeight <= el.clientHeight + 1 &&
                         el.firstElementChild.scrollHeight <= el.firstElementChild.clientHeight + 1; }, 5.6, 9.5));
              });
              document.querySelectorAll('.flow').forEach((f) => {
                const set = (pt) => { f.style.fontSize = pt + 'pt'; };
                out.push('flow ' + search(set, (pt) => { set(pt); return f.scrollWidth <= f.clientWidth + 1; }, 5.6, 9.5));
              });
              document.querySelectorAll('.fit').forEach((w) => {
                const page = w.closest('.page'); const sp = page.querySelector('.sp');
                const set = (pt) => { w.style.fontSize = pt + 'pt'; };
                out.push('fit ' + search(set, (pt) => { set(pt); return page.scrollHeight <= page.clientHeight + 1 &&
                         (!sp || sp.getBoundingClientRect().height >= 4); }, 5.8, 9.6));
              });
              document.querySelectorAll('.page').forEach((p, i) => {
                if (p.scrollHeight > p.clientHeight + 1) out.push(`page ${i+1} OVERFLOWS by ${p.scrollHeight - p.clientHeight}px`);
                p.querySelectorAll('.flow').forEach((f) => {
                  const fr = f.getBoundingClientRect(); const r = f.lastElementChild.getBoundingClientRect();
                  if (f.scrollWidth > f.clientWidth + 2) out.push(`page ${i+1} flow OVERFLOWS`);
                  else out.push(`page ${i+1} flow ends ${Math.round(fr.bottom - r.bottom)}px above the bottom of column ${Math.floor((r.left - fr.left + 4) / (fr.width / 3)) + 1}`);
                });
                p.querySelectorAll('figcaption').forEach((fc) => {
                  if (fc.scrollHeight > fc.clientHeight + 2) out.push(`page ${i+1} caption wraps: ${fc.textContent.slice(0, 50)}`);
                });
              });
              return out; }""")
            await pg.pdf(path=pdf_path, width="8.5in", height="11in", print_background=True,
                         margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True)
        else:
            await pg.pdf(path=pdf_path, width="8.5in", height="11in", print_background=True, prefer_css_page_size=True)
        await b.close()
    return notes


def stamp_footers(doc, first, last, total, ttf):
    import fitz
    for i in range(first, last):
        page = doc[i]
        w, h = page.rect.width, page.rect.height
        y = h - 0.3 * 72
        page.draw_line((0.4 * 72, y - 7), (w - 0.4 * 72, y - 7), color=(0.89, 0.91, 0.94), width=0.6)
        left = "11 Bayview Cir & 5001 Arrowhead Pt · due-diligence e-mail drafts"
        right = f"created {CREATED:%d %b %Y} · {MODEL} · p {i + 1}/{total}"
        font = fitz.Font(fontfile=os.path.join(ttf, "DejaVuSans.ttf"))
        page.insert_font(fontname="djv", fontfile=os.path.join(ttf, "DejaVuSans.ttf"))
        page.insert_text((0.4 * 72, y), left, fontname="djv", fontsize=5.6, color=(0.39, 0.45, 0.55))
        tw = font.text_length(right, fontsize=5.6)
        page.insert_text((w - 0.4 * 72 - tw, y), right, fontname="djv", fontsize=5.6, color=(0.39, 0.45, 0.55))


def write_markdown():
    d = os.path.join(ROOT, "docs", "twolots"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "EMAILS.md"), "w") as fh:
        fh.write("# Due-diligence e-mail drafts — 11 Bayview Cir and 5001 Arrowhead Pt (10 Nov 2026)\n\n"
                 "Replace the bracketed name and contact lines before sending.\n")
        for i, e in enumerate(EMAILS):
            body = "\n".join((ln + "  ") if ln.strip() else "" for ln in e["body"].split("\n"))
            fh.write(f"\n---\n\n## {i + 1}. {e['group']} ({e['lots']})\n\n**To:** {e['to']}  \n**Subject:** {e['subject']}"
                     f"\n\n{body}\n")
    import re as _re

    def plain(s):
        return _re.sub(r"<[^>]+>", "", s).replace("&amp;", "&").replace("&gt;", ">")
    with open(os.path.join(d, "PLAN.md"), "w") as fh:
        fh.write("# Largest home, private dock and first steps — 11 Bayview Cir and 5001 Arrowhead Pt (10 Nov 2026)\n\n"
                 "Desk study from public records; not a survey, design or permit decision. Full version with figures: "
                 f"[`{PDF}`](../../{PDF}).\n\n## Verdicts\n\n")
        for k in ("bayview", "arrowhead"):
            fh.write(f"**{LOT[k]['L']} · {LOT[k]['name']}.** {plain(VERDICT[k])}\n\n")
        fh.write("| | A · 11 Bayview Cir | B · 5001 Arrowhead Pt |\n|---|---|---|\n")
        fh.write(f"| Largest footprint (test fit) | {HA['W']}×{HA['D']} ft = {HA['footprint_sf']:,} sf | {HB['W']}×{HB['D']} ft = "
                 f"{HB['footprint_sf']:,} sf |\n")
        fh.write(f"| Heated, 2 storeys | ≈{HA['heated_2st_sf']:,} sf | ≈{HB75['heated_2st_sf']:,}–{HB['heated_2st_sf']:,} sf |\n")
        fh.write("| Limit | set-back envelope on a wedge + Zone A | drip field (600 gal/day → 6,000 sf) |\n")
        fh.write(f"| Dock (TRWD) | {DA['cap_sf']:,} sf; fits {DA['L']:.0f}×{DA['P']:.0f} ft | {DB['cap_sf']:,} sf; fits "
                 f"{DB['L']:.0f}×{DB['P']:.0f} ft after a {DB['w0']:.0f}-ft walkway |\n")
        fh.write(f"| Water width at the dock | {DA['width_at_dock']:.0f} ft | {DB['width_at_dock']:.0f} ft |\n")
        fh.write(f"| Depth over the lift (pool / today / Dec-2022) | not surveyed | {DB['depth_pool']} / {DB['depth_now']} / "
                 f"{DB['depth_low22']} ft |\n")
        fh.write(f"| Spend before committing | {SPEND['bayview']} | {SPEND['arrowhead']} |\n\n")
        for k in ("bayview", "arrowhead"):
            n = NOTES[k]
            fh.write(f"## {LOT[k]['L']} · {LOT[k]['name']}\n\n")
            fh.write("".join(f"- (+) {x}\n" for x in n["pos"]) + "".join(f"- (−) {x}\n" for x in n["neg"])
                     + "".join(f"- (!) {x}\n" for x in n["alert"]))
            fh.write("\nBefore you commit:\n\n" + "".join(f"{i + 1}. {x}\n" for i, x in enumerate(n["steps"])) + "\n")
        fh.write("## Staged plan and costs\n\n| Stage | When | What | Cost | Lot |\n|---|---|---|---|---|\n")
        for s, w, t, c, l in PLAN:
            fh.write(f"| {s} | {w} | {t} | {c} | {l} |\n")
        fh.write("\nPut these in the offer:\n\n" + "".join(f"- {x}\n" for x in CONTINGENCIES))
        fh.write("\n## The area\n\n" + "".join(f"- (+) {x}\n" for x in AREA["pos"]) + "".join(f"- (−) {x}\n" for x in AREA["neg"])
                 + "".join(f"- (!) {x}\n" for x in AREA["alert"]))
    return d


def main():
    import fitz
    assert LOTSET == "two", "run with LOTSET=two (the default)"
    dpi = int(sys.argv[1]) if len(sys.argv) > 1 else 110
    _, ttf = FONTS()
    # 1. e-mail pages first, to know the page count. If the last page holds only a stub, shrink the type a
    #    little (at most 6%) so the stub moves back onto the page before it.
    mh = os.path.join(OUT, "emails.html"); mp = os.path.join(OUT, "emails.pdf")
    for scale in (1.0, 0.985, 0.97, 0.955, 0.94):
        open(mh, "w", encoding="utf-8").write(mails_html(scale))
        asyncio.run(render(mh, mp, fixed=False))
        md = fitz.open(mp)
        last = md[-1]
        fill = max((b[3] for b in last.get_text("blocks")), default=0) / last.rect.height
        print(f"  e-mails at {scale:.3f}: {len(md)} pages, last page filled to {fill:.0%}")
        if fill > 0.25:
            break
    n_mail = len(fitz.open(mp))
    total = 4 + n_mail + 1
    # 2. fixed pages: summary, lot A, lot B, steps (pages 1-4) and the back page
    front = [summary_page(total), lot_page("bayview", 2, total), lot_page("arrowhead", 3, total), steps_page(4, total)]
    fh_ = os.path.join(OUT, "front.html"); open(fh_, "w", encoding="utf-8").write(fixed_html(front))
    fp = os.path.join(OUT, "front.pdf")
    for o in asyncio.run(render(fh_, fp)):
        print("  front:", o)
    bh = os.path.join(OUT, "back.html"); open(bh, "w", encoding="utf-8").write(fixed_html([back_page(total, total)]))
    bp = os.path.join(OUT, "back.pdf")
    for o in asyncio.run(render(bh, bp)):
        print("  back:", o)
    doc = fitz.open(fp)
    doc.insert_pdf(fitz.open(mp))
    doc.insert_pdf(fitz.open(bp))
    stamp_footers(doc, 4, 4 + n_mail, total, ttf)
    doc.set_metadata({"title": "11 Bayview Cir & 5001 Arrowhead Pt — largest home, private dock, first steps, e-mails",
                      "author": f"{MODEL} (Anthropic) in Kiro", "subject": "Desk due diligence, Richland-Chambers Lake",
                      "creationDate": fitz.get_pdf_now()})
    pdf = os.path.join(ROOT, PDF)
    doc.save(pdf, garbage=3, deflate=True)
    doc = fitz.open(pdf)
    print("PDF:", PDF, f"{os.path.getsize(pdf)/1e6:.1f} MB", len(doc), "pages",
          f"{doc[0].rect.width/72:.2f}x{doc[0].rect.height/72:.2f} in", "e-mail pages", n_mail)
    blank = {i + 1: c for i, pg in enumerate(doc) if (c := pg.get_text().count("\x00"))}
    print("   blank (missing) glyphs per page:", blank or "none")
    prev = os.path.join(OUT, "preview"); os.makedirs(prev, exist_ok=True)
    for old in os.listdir(prev):
        if old.endswith(".png"):
            os.remove(os.path.join(prev, old))
    for i, pg in enumerate(doc):
        pg.get_pixmap(dpi=dpi).save(os.path.join(prev, f"p{i+1}.png"))
    for f in ("front.pdf", "back.pdf", "emails.pdf"):
        os.remove(os.path.join(OUT, f))
    print("markdown:", write_markdown())


if __name__ == "__main__":
    main()
