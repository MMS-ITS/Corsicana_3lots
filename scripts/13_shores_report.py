"""Revised due diligence for The Shores lots 442, 411, 441 (run with LOTSET=shores3).

Writes, in the repo root:
  The-Shores-3-Lots-Revised-Due-Diligence_<dd-Mon-yy>_Claude-Opus-5.5.pdf   (10 letter pages)
  The-Shores-3-Lots-Checklists-and-Emails_<dd-Mon-yy>_Claude-Opus-5.5.pdf   (checklist + 12 e-mails)
and docs/shores3/{CORRECTIONS,CHECKLIST,EMAILS}.md, out/shores3/preview/*.png
"""
import asyncio
import os
import sys

from common import OUT, ROOT
from shores_data import (COMPS, CREATED, HOMES, LAKE_NOW, LK, LOT, MODEL, NEIGHBOURS, ORDER, RATE, SCORE, STAMP, T,
                         facts)
from shores_docs import CHECK, CORRECTIONS, EMAILS, SRC, check_cells
from shores_html import (CSS, CON, EST, GIS, NEW, OFF, box, dest, dm, fig, foot, heated_range, img, kv, lot_page1,
                         lot_page2, money, named)

PDF1 = f"The-Shores-3-Lots-Revised-Due-Diligence_{STAMP}_{MODEL.replace(' ', '-')}.pdf"
PDF2 = f"The-Shores-3-Lots-Checklists-and-Emails_{STAMP}_{MODEL.replace(' ', '-')}.pdf"
F = {k: facts(k) for k in LOT}
VERDICT = {
    "lot441": "<b>Best match for a large home and a private dock.</b> 105 ft of walled canal allows the largest dock "
              "(839 sf). Depth is 5.9 / 7.6 ft at full pool. $105k is 1.5× the 2026 CAD value, but the CAD cut this lot "
              "53% in 2026, and per foot of water it is the cheapest. Expect the tax to rise after the sale. Suggested "
              "offer ≈$90–95k, citing the CAD value and the 2025 price cut.",
    "lot442": "<b>Good canal, small water frontage, highest carrying cost.</b> The canal is the widest (≈113 ft) and the "
              "house footprint the largest, but only 60 ft touches the water (dock ≤480 sf). The CAD values it at $155k, "
              "2.2× its neighbours, so tax is $2,246. Unsold for 22 months after $30k of cuts: offer ≈$80–85k and protest "
              "the 2027 value.",
    "lot411": "<b>Cheapest, but the water access is uncertain.</b> The whole lot sits above 320 ft, but it ends at the "
              "canal tract's 315-ft deed line, 25–33 ft from open water at a silted canal head (2.7–3.2 ft deep today). "
              "Dock size (280–766 sf) and dredging are TRWD decisions. Buy only after TRWD confirms the dock in writing; "
              "otherwise price it as an off-water lot (The Shores' 1-acre off-water lots ask $60–70k).",
}



def FONTS(ttf):
    """DejaVu Sans fills the symbols Noto Sans lacks (≈ → ≤ ≥ ✓). Weight ranges make semibold (600) text use
    the bold face; a single 700 face was skipped by Chromium's fallback for 600-weight text."""
    return (f'@font-face {{ font-family: "DJV"; src: url("file://{ttf}/DejaVuSans.ttf"); font-weight: 100 549; }}\n'
            f'@font-face {{ font-family: "DJV"; src: url("file://{ttf}/DejaVuSans-Bold.ttf"); font-weight: 550 900; }}\n')


# --------------------------------------------------------------------------- page 1 summary
def summary_page():
    def card(k):
        d = LOT[k]
        return (f'<div class="card" style="--acc:{d["acc"]};--tint:{d["acc"]}18"><div class="ch">'
                f'<div class="score"><b>{d["score"]:.1f}</b><span>was {d["old_score"]}</span></div><div>'
                f'<h2>#{ORDER.index(k)+1} · {d["name"]}</h2><div class="cs">Phase {d["phase"]} · {d["acres"]:.3f} ac · '
                f'{money(d["price"])} asking · CAD {money(d["cad_mkt"])} · earlier rank {d["old_rank"]}</div></div></div>'
                f'<p>{VERDICT[k]}</p></div>')
    a, b, c = ORDER
    fa, fb, fc = F[a], F[b], F[c]

    def row(label, fn):
        return (label, fn(a), fn(b), fn(c))
    dockv = lambda k: (f"{F[k]['dock']['max_sf_open_water']}–{F[k]['dock']['max_sf_plat']} sf {CON}" if k == "lot411"
                       else f"{F[k]['dock']['max_sf']:,} sf")
    rows = [
        ("grp", "Price, value and holding cost"),
        row("Asking · $/acre", lambda k: f"<b>{money(LOT[k]['price'])}</b> · {money(F[k]['price_ac'])}/ac"),
        row("Per foot of water", lambda k: "$680–1,860 (35–96 ft)" if k == "lot411" else f"{money(LOT[k]['price']/F[k]['lake_ft'])}/ft"),
        row("CAD 2026 (2025)", lambda k: f"{money(LOT[k]['cad_mkt'])} ({money(LOT[k]['hist'][2025])}) {OFF}"),
        row("2026 tax bill", lambda k: f"{money(LOT[k]['tax26'])} {OFF}"),
        row("Holding cost / yr", lambda k: f"{money(F[k]['hold']['after_lo'])}–{money(F[k]['hold']['after_hi'])} {EST}"),
        row("On the market", lambda k: {"lot442": "672 days, −$30k", "lot411": "116 days", "lot441": "32 days (re-listed)"}[k]),
        ("grp", "Land"),
        row("Size legal · GIS", lambda k: f"{LOT[k]['acres']:.3f} ac · {F[k]['gis_sf']:,} sf"),
        row("Road / water line", lambda k: "102 / 95.8 ft (plat), open water 25–33 ft out" if k == "lot411"
            else f"{F[k]['road_ft']:.0f} / {F[k]['lake_ft']:.0f} ft"),
        row("Ground low–high", lambda k: f"{F[k]['zmin']:.1f}–{F[k]['zmax']:.1f} ft · max 50-ft {T[k]['slope']['max50_deg']:.0f}°"),
        row("FEMA", lambda k: "X" if T[k]["zoneA_pct_of_lot"] == 0 else f"X + {T[k]['zoneA_pct_of_lot']:.0f}% Zone A"),
        ("grp", "Water and dock"),
        row("Canal width (315 ft)", lambda k: f"≈{F[k]['canal_w']:.0f} ft, silted head" if k == "lot411" else f"≈{F[k]['canal_w']:.0f} ft"),
        row("Depth full pool → now", lambda k: f"{F[k]['depth_mean']}/{F[k]['depth_max']} → {F[k]['now_mean']}/{F[k]['now_max']} ft"),
        row("Largest dock (TRWD)", dockv),
        row("Steel wall (CAD)", lambda k: LOT[k]["wall"].replace("steel wall ", "").replace("(CAD: ", "(")),
        ("grp", "Largest home (septic-limited)"),
        row("Footprint · heated", lambda k: f"{F[k]['max50']['footprint_sf']:,} sf · {heated_range(k)} sf"),
        row("Septic", lambda k: f"aerobic + drip, 6 BR, {F[k]['max50']['q_gpd']} gal/day"),
    ]
    tr = []
    for r in rows:
        if r[0] == "grp":
            tr.append(f'<tr class="grp"><td colspan="4">{r[1]}</td></tr>')
        else:
            tr.append("<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>")
    table = (f'<table class="cmp"><tr><th style="background:#334155">Key facts (verified 10 Nov 2026)</th>'
             + "".join(f'<th style="background:{LOT[k]["acc"]}">#{i+1} {LOT[k]["name"]}</th>' for i, k in enumerate(ORDER))
             + f"</tr>{''.join(tr)}</table>")
    bottom = box("Bottom line", "<ul>"
                 "<li>The ranking flips: <b>441 first, 442 second, 411 third</b>. The earlier order rested on CAD values "
                 "that the CAD itself treats inconsistently (page 8).</li>"
                 "<li>All three can take a very large house. The septic drip field, not zoning, sets the limit: about "
                 "8,500–10,700 sf heated in theory, 5,000–6,500 sf in practice.</li>"
                 "<li>All three need an aerobic septic system with drip lines, permitted by TRWD. The 2011 one-acre rule "
                 "does not apply (plats are from 2008).</li>"
                 "<li>The canals are shallow: 5.5–7.6 ft at full pool and 2.8 ft less today. Plan a boat lift and expect "
                 "low-water seasons.</li>"
                 "<li>A house much above 4,500 sf would be the largest in The Shores; resale may not repay it.</li></ul>")
    corr = box(f"Main corrections to the earlier report (all {len(CORRECTIONS)}: page 8)", "<ul>"
               "<li><b>CAD values</b> are real but inconsistent: in 2026 the CAD cut six of eight Phase VI canal lots by "
               "22–57%, but not 442 or 444. The earlier ranking leaned on them.</li>"
               "<li><b>Tax:</b> the listing figures were 2023–24 bills. The 2026 bills are 442 $2,246, 411 $1,411 and "
               "441 $1,114.</li>"
               "<li><b>Septic:</b> TRWD's 1-acre rule does not apply (plats from 2008). Half-acre aerobic + drip systems "
               "are allowed.</li>"
               "<li><b>Canal depth</b> was “not surveyed”: TWDB sounded the canals in 2018 (5.5–7.6 ft at full pool).</li>"
               "<li><b>Lot 411</b> ends at the canal tract's 315-ft deed line, 25–33 ft short of open water.</li>"
               "<li><b>HOA:</b> leases under 90 days are banned (June 2026); the exterior must be done 9 months after "
               "the slab.</li></ul>")
    first = box("What to do first, and what to spend", "<ol>"
                "<li><b>This week, $0:</b> send the 12 e-mail drafts (second PDF). TRWD's answer on dock length decides 411.</li>"
                "<li><b>Offer on #1</b> with a 21-day option period (TREC unimproved-property contract; option fee $200–500).</li>"
                "<li><b>During the option, ≈$5–9k:</b> boundary + topo survey $2–4k, septic site evaluation $0.75–1.5k, "
                "geotech $1.8–3k, HOA resale certificate ≈$375, title commitment.</li>"
                "<li><b>Walk away</b> if TRWD will not confirm the dock, the drip field will not serve 6 BR, or the survey "
                "shows an encroachment.</li></ol>")
    band = ('<div class="band" style="background:linear-gradient(95deg,#1e3a8a,#0f766e 50%,#6d28d9)"><div>'
            '<h1>Three canal lots in The Shores, Richland-Chambers Lake — revised due diligence</h1>'
            '<div class="sub">Lots 442 & 441 Waters Edge Dr (Phase VI) and Lot 411 Sailboat Dr (Phase V), Corsicana TX 75109 · '
            'records re-checked 8–10 Nov 2026 · replaces the scores in “3 Corsicana lakefront lots Comparison”</div></div>'
            '<div class="kpis">'
            f'<div class="kpi"><b>{money(sum(LOT[k]["price"] for k in LOT), True)}</b><span>combined asking</span></div>'
            f'<div class="kpi"><b>{LAKE_NOW:.2f} ft</b><span>lake 9 Nov (pool 315)</span></div>'
            '<div class="kpi"><b>441 › 442 › 411</b><span>new ranking</span></div></div></div>')
    return (f'<section class="page sum" style="--acc:#1e3a8a">{band}<div class="fit"><div class="srow"><figure class="smap">'
            f'{img(fig("region.png"), 3.3, "cover")}</figure><div>{"".join(card(k) for k in ORDER)}</div></div>'
            f'{table}<div class="three" style="margin-top:5px">{bottom}{corr}{first}</div></div>'
            f'<div class="sp" style="flex:1"></div>{foot(1)}</section>')


# --------------------------------------------------------------------------- page 8 corrections
def pct(new, old):
    """Change as a signed whole percent; 'no change' instead of -0% / +0%."""
    p = 100 * (new / old - 1)
    return "no change" if abs(p) < 0.5 else f"{p:+.0f}%".replace("-", "−")


def corrections_page():
    rows = "".join(f"<tr><td>{a}</td><td class='old'>{b}</td><td class='new'>{c}</td><td>{d}</td><td>{e}</td></tr>"
                   for a, b, c, d, e in CORRECTIONS)
    corr = (f"<table class='corr'><tr><th>Topic</th><th>Earlier 3-lot report</th><th>Verified now</th><th>Source</th>"
            f"<th>Effect</th></tr>{rows}</table>")
    nb = "".join(f"<tr><td>{'<b>' if n in ('441','442') else ''}{n}{'</b>' if n in ('441','442') else ''}</td>"
                 f"<td class='n'>{ac:.3f}</td><td class='n'>{money(v25)}</td><td class='n'>{money(v26)}</td>"
                 f"<td class='n'>{money(v26/ac)}</td><td class='n'>{pct(v26, v25)}</td></tr>"
                 for n, ac, v25, v26 in NEIGHBOURS)
    cad = box("Navarro CAD land values, Phase VI canal lots (2025 → 2026)",
              "<table class='mini'><tr><th>Lot</th><th class='n'>acres</th><th class='n'>2025</th><th class='n'>2026</th>"
              f"<th class='n'>2026 $/ac</th><th class='n'>change</th></tr>{nb}</table><p>Six of eight lots were cut "
              "22–57%; 442 and 444 were not. Lot 411 (Phase V) went from $88,650 to $88,645.</p>")
    hr = []
    for k in ORDER:
        h = F[k]["hold"]
        hr.append(f"<tr><td><b>{LOT[k]['num']}</b></td><td class='n'>{money(h['tax_now'])}</td><td class='n'>$1,255</td>"
                  f"<td class='n'>$340–680</td><td class='n'><b>{money(h['now_lo'])}–{money(h['now_hi'])}</b></td>"
                  f"<td class='n'>{money(h['after_lo'])}–{money(h['after_hi'])}</td></tr>")
    hold = box("Actual holding cost per year (before building)",
               "<table class='mini'><tr><th>Lot</th><th class='n'>2026 tax</th><th class='n'>HOA</th><th class='n'>mow+ins.</th>"
               f"<th class='n'>now</th><th class='n'>after purchase</th></tr>{''.join(hr)}</table>"
               "<p>Tax is the 2026 adopted bill. HOA dues are from the MLS. Mowing (4 required) and liability cover are "
               "estimates. “After purchase” covers a protest to the price (442), or the CAD resetting 441 toward its 2025 "
               "value. Add 4.5% of the price for the cost of capital if you want an investor view.</p>")
    cp = "".join(f"<tr><td>{a}</td><td>{b}</td><td class='n'>{money(c)}</td></tr>" for a, b, c in COMPS)
    hp = "".join(f"<tr><td>{a}</td><td>{b}</td><td class='n'>{money(c)}</td></tr>" for a, b, c in HOMES)
    comps = box("Market check — The Shores, 10 Nov 2026",
                f"<table class='mini'><tr><th>Lots for sale</th><th></th><th class='n'>asking</th></tr>{cp}"
                f"<tr><th>Homes</th><th></th><th class='n'></th></tr>{hp}</table>"
                "<p>Texas does not publish sale prices. Ask the agents for MLS sold data on canal lots.</p>")
    band = ('<div class="band" style="background:linear-gradient(95deg,#312e81,#4338ca)"><div><h1 style="font-size:12pt">'
            'What changed — the earlier report checked against the records</h1><div class="sub">CAD, tax portal, HOA '
            'documents, TRWD/TCEQ rules, plat, TWDB survey · each row names its source</div></div></div>')
    return (f'<section class="page" style="--acc:#4338ca">{band}<div class="fit"><div style="margin-top:5px">{corr}</div>'
            f'<div class="three" style="margin-top:5px">{cad}{hold}{comps}</div></div><div class="sp" style="flex:1"></div>'
            f'{foot(8)}</section>')


# --------------------------------------------------------------------------- page 9 feasibility + plan
def feasibility_page():
    def r(label, fn):
        return f"<tr><td><b>{label}</b></td>" + "".join(f"<td>{fn(k)}</td>" for k in ORDER) + "</tr>"
    rows = "".join([
        r("Lot area (legal / GIS)", lambda k: f"{LOT[k]['legal_sf']:,} / {F[k]['gis_sf']:,} sf"),
        r("County cover cap 40%", lambda k: f"{F[k]['max50']['cov_max_sf']:,} sf (not the limit)"),
        r("Buildable envelope", lambda k: f"{T[k]['envelope_sqft']:,} sf (set-backs + ground ≥322 ft)"),
        r("Largest footprint", lambda k: f"<b>{F[k]['max50']['footprint_sf']:,} sf</b> incl. 3-car garage + porches"),
        r("Largest heated area", lambda k: f"<b>{F[k]['max50']['heated_2st_sf']:,} sf</b> (50-ft drip set-back) · "
                                            f"{F[k]['max75']['heated_2st_sf']:,} sf (75-ft)"),
        r("Septic for that house", lambda k: f"{F[k]['max50']['q_gpd']} gal/day → drip {F[k]['max50']['drip_need_sf']:,} sf, "
                                              f"room {F[k]['max50']['drip_avail_sf']:,} sf"),
        r("Practical large home", lambda k: "5,000–6,500 sf, 6 BR, pool fits beside a 4,800 sf drip field"),
        r("Largest dock", lambda k: (f"<span class='w'>{F[k]['dock']['max_sf_open_water']}–{F[k]['dock']['max_sf_plat']} sf, TRWD decides</span>"
                                     if k == "lot411" else f"<b>{F[k]['dock']['max_sf']:,} sf</b> (8 sf × {F[k]['lake_ft']:.0f} ft)")),
        r("Water at the dock today", lambda k: f"≈{F[k]['now_mean']}–{F[k]['now_max']} ft (Dec-2022 low: ≤{F[k]['low22_max']} ft)"),
        r("Feasible?", lambda k: {"lot441": "<span class='g'>Yes</span> — biggest dock; wall exists",
                                  "lot442": "<span class='g'>Yes</span> — dock limited to 480 sf",
                                  "lot411": "<span class='w'>Conditional</span> — TRWD dock length + dredging"}[k]),
    ])
    feas = (f"<table class='corr'><tr><th>Largest home & private dock</th>"
            + "".join(f"<th>{LOT[k]['name']}</th>" for k in ORDER) + f"</tr>{rows}</table>")
    cost = box("Budget for a 5,000–6,500 sf, 6-BR lake home (2026 estimate)",
               "<table class='mini'><tr><th>Item</th><th class='n'>range</th></tr>"
               "<tr><td>House, custom, $275–350/sf (Shores homes sell at $290–575/sf incl. land)</td><td class='n'>$1.38–2.28M</td></tr>"
               "<tr><td>Engineered foundation on high-shrink clay (extra over a plain slab)</td><td class='n'>$30–60k</td></tr>"
               "<tr><td>Aerobic septic + drip, 420–540 gal/day</td><td class='n'>$30–45k</td></tr>"
               "<tr><td>Covered dock/boathouse 480–839 sf + lift (≈$90–140/sf)</td><td class='n'>$45–115k</td></tr>"
               "<tr><td>Driveway, culvert, clearing, water tap, electric</td><td class='n'>$25–50k</td></tr>"
               "<tr><td>Permits: POA $6–10k, county $0.25/sf, TRWD $400 + $300, inspections</td><td class='n'>$9–14k</td></tr>"
               "<tr><td>Design, survey, geotech, septic design</td><td class='n'>$40–90k</td></tr>"
               "<tr><td><b>Total excluding the lot</b></td><td class='n'><b>≈$1.56–2.66M</b></td></tr></table>"
               f"<p>{EST} Get two builder bids. The theoretical maximum (8,500–10,700 sf) would cost ≈$2.5–3.8M, about "
               "twice the most expensive Shores listing.</p>")
    steps = box("Initial steps and money to spend before you commit", "<ol>"
                "<li><b>Free, this week:</b> e-mails to the three listing agents, PMI Alliance (HOA), TRWD, Navarro County "
                "Planning, M.E.N. WSC and NCEC. Ask TRWD for the shoreline length and dock limit, in writing.</li>"
                "<li><b>Free:</b> drive the canals at today's low level (312.2 ft) and look at the walls and depth at each lot.</li>"
                "<li><b>Option period (21 days), $200–500:</b> make the offer on #1 subject to the items below.</li>"
                "<li><b>$2,000–4,000:</b> boundary + 1-ft topo survey showing the 315/320 lines, the wall, and trees ≥10 in.</li>"
                "<li><b>$750–1,500:</b> septic site evaluation and a sketch layout for 420–540 gal/day.</li>"
                "<li><b>$1,800–3,000:</b> geotech borings + PVR (can wait until after closing if the option is short).</li>"
                "<li><b>≈$375 + $200:</b> HOA resale certificate (dues, assessments, violations) and transfer fee.</li>"
                "<li><b>$0 until closing:</b> title commitment; read every easement and the CC&Rs for Phase V/VI.</li>"
                "<li><b>Then decide.</b> Total at risk on one lot ≈$5–9k. Do steps 1–2 for all three lots, steps 3–8 only for #1.</li></ol>")
    pos = box("Positives", "<ul>"
              "<li>Gated community with pool, gym, ramp, marina and paved roads; Mildred ISD.</li>"
              "<li>Public water (M.E.N. WSC) and underground power at the road.</li>"
              "<li>Pre-2011 plats: half-acre septic is allowed; no deadline to start building.</li>"
              "<li>441 and 442 already have 2021 steel walls (saves $30–70k).</li>"
              "<li>No fill needed: the house pads (≈329–335 ft) sit 9–15 ft above the 320-ft flowage line.</li></ul>")
    limits = box("What limits the size of the house", kv([
        ("County", f"SF-3 (to confirm {CON}): set-backs 35 ft front, 15 ft rear (water side), 10 ft sides; buildings "
                   "≤40% of the lot; main + accessory buildings ≤50% of the rear half; 2½ storeys; nothing below 320 ft"),
        ("POA", "site-built; at least 1,800–2,200 sf; 2- to 5-car garage with side or rear doors; 6/12 roof; "
                "engineer's foundation plan; first 20 ft beside the road is a POA easement; exterior done 9 months "
                "after the slab"),
        ("Septic", "TRWD permits it (TCEQ rules). Flow for 6 BR is 420 gal/day up to 5,500 sf heated, +60 per extra "
                   "1,500 sf. Drip area = flow ÷ 0.10, so 4,200–4,800 sf for a 5,000–6,500 sf home and 6,000–6,600 sf "
                   "for the theoretical maximum. It must stay ≥5 ft from lot lines and 50–75 ft from the 315-ft line"),
        ("Result", "<b>the drip field runs out of room before zoning does</b>: the largest houses cover only 26–27% of "
                   "the lots against a 40% cap"),
    ]))
    method = box("How the largest-home figure was found", "<p>A computer search tried house rectangles from 44 × 36 ft "
                 "to 128 × 108 ft, turned 6 ways and moved in 6-ft steps, keeping those inside the set-backs and on "
                 "ground ≥322 ft. It took the largest one that still leaves room for the drip field, a driveway, a "
                 "side-entry apron and the tank pad. Each house includes a 960-sf 3-car garage and 360 sf of porches; "
                 "heated area = 2 storeys × the rest. Drawings: each lot's page 2. "
                 f"{EST}</p>")
    dock = box("Dock and boathouse rules (TRWD Attachment I, 5 Feb 2026)", kv([
        ("Permit", "needed for any dock, boathouse, wall, patio, pool or dredging on TRWD land or water: $300; review "
                   "10 business days + up to 30 more"),
        ("Size", "8 sf per foot of shoreline up to 150 ft (max 1,200 sf), measured at the end of the walkway incl. any "
                 "roof overhang >2 ft; one walkway ≤8 ft wide is not counted"),
        ("Placement", "≥5 ft from side lines. A side-entry slip must sit 1.5× its length from the property line, so "
                      "60 ft (442) suits a straight-in slip only. It must not block navigation"),
        ("Build", "not enclosed (one 20-sf store allowed); roof ≤6/12; ≤2 storeys; no toilet or living space; lower "
                  "deck ≥18 in above 320 ft, i.e. ≥6.5 ft above full pool, so plan a boat lift; light at the end if "
                  ">50 ft out"),
        ("Dredging", "own permit; side slopes ≤10%, no holes (needed at 411's canal head)"),
    ]))
    neg = box("Alerts", "<ul>"
              "<li><b>Shallow canals:</b> in a 2006-type drought (303.6 ft) all three canals go dry.</li>"
              "<li><b>411:</b> the lot does not reach open water; the 2010 wall is at 20% condition.</li>"
              "<li><b>Tax swings:</b> 442 is over-valued by the CAD; 441's 2026 cut will likely reverse after sale.</li>"
              "<li><b>Rules:</b> no rentals under 90 days; exterior in 9 months; 4 mowings a year while vacant.</li>"
              "<li><b>Clay:</b> LEP 9% — budget an engineered foundation and keep trees ≥15 ft from the slab.</li>"
              "<li><b>Services:</b> hospital 33 min, groceries 28 min (Corsicana); tornado and hail are the main hazards.</li></ul>")
    band = ('<div class="band" style="background:linear-gradient(95deg,#0f766e,#1e3a8a)"><div><h1 style="font-size:12pt">'
            'Largest home and private dock — feasibility, budget and first steps</h1><div class="sub">Navarro County SF-3 '
            'rules, POA ACC rules, TRWD 2026 dock and septic guidelines, TCEQ 30 TAC 285 · drawings on each lot’s page 2</div>'
            '</div></div>')
    return (f'<section class="page" style="--acc:#0f766e">{band}<div class="fit"><div style="margin-top:5px">{feas}</div>'
            f'<div class="two" style="margin-top:5px"><div>{limits}{method}{cost}</div><div>{dock}{steps}</div></div>'
            f'<div class="two">{pos}{neg}</div></div><div class="sp" style="flex:1"></div>{foot(9)}</section>')


# --------------------------------------------------------------------------- page 10 score + refs
def final_page():
    rows = "".join(f"<tr><td><b>{c}</b> ({w:g})</td>" + "".join(f"<td><b>{p[k][0]:g}</b> {p[k][1]}</td>" for k in ORDER) + "</tr>"
                   for c, w, p in SCORE)
    tot = ("<tr><td><b>Total (earlier)</b></td>" + "".join(f"<td><b>{LOT[k]['score']:.1f}</b> ({LOT[k]['old_score']})</td>"
                                                       for k in ORDER) + "</tr>")
    score = box("Revised holding score — points and reasons",
                "<table class='mini'><tr><th>Criterion (max)</th>" + "".join(f"<th>{LOT[k]['name']}</th>" for k in ORDER)
                + f"</tr>{rows}{tot}</table><p>The weights favour your goal (large home + private dock): dock and boating "
                "2.0, largest home 1.5, price 1.5. The earlier report weighted price vs CAD at 20% and gave 441 a 2/10 "
                "on a CAD value the district had just halved.</p>")
    gl = [("BFE", "base flood elevation, the 1%-chance flood level"), ("Zone A / X", "FEMA floodplain without a BFE / minimal hazard"),
          ("CAD", "Navarro Central Appraisal District (tax values)"), ("TNT", "Texas truth-in-taxation portal (adopted rates)"),
          ("Circuit breaker (20% limit)", "Tax Code §23.231: 20%/yr limit on non-homestead value increases, tax years 2024–2026 only; never passes to a buyer"),
          ("TRWD", "Tarrant Regional Water District — owns the lake, permits docks and septic"),
          ("315 / 320 ft", "normal pool / TRWD flood-flowage line (ft above sea level)"),
          ("315 deed line", "plat line that follows the 315-ft contour as surveyed at platting"),
          ("OSSF / ATU", "on-site sewage facility / aerobic treatment unit"), ("Drip field", "buried lines that spread treated effluent"),
          ("Ra", "septic loading rate, gal per sq ft per day (clay 0.10)"), ("LEP", "linear extensibility — clay shrink-swell; >6% is high"),
          ("SF-3", "county half-acre single-family zoning district"), ("ACC", "the POA's architectural control committee"),
          ("PVR", "potential vertical rise of clay under a slab"), ("RPLS", "Registered Professional Land Surveyor"),
          ("Option period", "paid right to cancel a Texas contract within a set number of days")]
    gloss = box("Glossary", "<table class='mini'>" + "".join(f"<tr><td><b>{a}</b></td><td>{b}</td></tr>" for a, b in gl) + "</table>")
    src = box("Sources (read 8–10 Nov 2026)", "<ul>"
              "<li>Navarro CAD property records 64391, 64288, 64390 + 11 neighbours (navarrocad.com); 2026 adopted rates and "
              "bills (texastaxtransparency.com)</li><li>TxGIO StratMap 2026 parcels · USGS 3DEP 1 m lidar (TX 2022) · "
              "Esri World Imagery</li><li>FEMA NFHL (FIRM 48349C0625D) · TWDB 2018 Richland-Chambers volumetric survey and "
              "daily lake levels · TWDB water-service areas</li><li>USDA NRCS SSURGO (Crockett CrB)</li>"
              "<li>TRWD General Ordinance (Dec 2025), Attachment I and OSSF Guidelines (2026), 2026 fee schedule · TCEQ RG-472 "
              "(30 TAC 285)</li><li>Navarro County Lakeshore Zoning Ordinance (2017, Table B) and 2025 permit package</li>"
              "<li>P.O.A. of The Shores: 2022 management certificate (Doc 2022-007945), 20th Supplement (6 Jun 2026), website</li>"
              "<li>LakeHouse.com listings (MLS 20810887, 21334950, 21407991) and Shores comparables; HAR, Redfin and realtor.com "
              "search snippets</li><li>Earlier artifact: “3 Corsicana lakefront lots Comparison.pdf” (7 Nov 2026)</li></ul>")
    limits = box("Method & limits", "<p>Desk study from public records — no site visit. Not a survey, appraisal, title "
                 "opinion, septic design or legal advice. Lidar is ±0.5 ft; GIS lot lines can be several feet off. The "
                 "largest-home figures come from a search over house rectangles inside the set-backs; the drip field must "
                 "fit the rest of the lot. HOA set-backs in the CC&Rs (members-only) could be stricter than the county's. "
                 "Zillow, Redfin, HAR and realtor.com block automated access, so realtor.com Fly Around views are replaced by "
                 "lidar fly-arounds.</p>")
    end = ("<div class='box' style='--acc:#0f172a;background:#f8fafc'><h3>End note</h3><p><b>Date of creation:</b> "
           f"{CREATED:%d %B %Y} · <b>Prepared by AI model:</b> {MODEL} (Anthropic), working in Kiro · <b>Files:</b> {PDF1} and "
           f"{PDF2}</p><p>Data and scripts: GitHub MMS-ITS/Corsicana_3lots (LOTSET=shores3).</p></div>")
    todo = box("Still to confirm, and who answers (e-mail drafts in the companion PDF)", kv([
        ("TRWD", "shoreline length and dock limit for each lot (decides 411); permits for the three walls; drip set-back "
                 "50 or 75 ft; whether 411's canal head may be dredged"),
        ("POA / PMI", "2026–27 dues, assessments and violations (resale certificate); CC&R set-backs and height; who owns "
                      "the canal tract beside 411"),
        ("County", "zoning district (SF-3?), which line is the rear on a canal lot, guest-house rules, permit fees"),
        ("CAD", "why 442 is taxed on $142,802; why 441 and its neighbours were cut; how 2027 values will be set"),
        ("Surveyor", "corners, the 315/320-ft lines, where each wall stands, 411's exact area (0.500 ac?)"),
        ("Septic designer", "soil class at the emitters; drip area for 6 bedrooms on the chosen lot"),
        ("Geotech", "PVR and the foundation design for 46% clay"),
        ("Utilities", "M.E.N. WSC tap and membership fees; NCEC service cost"),
        ("Title", "easements, mineral reservations, TRWD flowage easement, liens"),
        ("Agents", "sold prices of canal lots, seller's disclosure, any survey, price flexibility"),
    ]))
    band = ('<div class="band" style="background:linear-gradient(95deg,#334155,#1e3a8a)"><div><h1 style="font-size:12pt">'
            'Revised scores · open questions · glossary · sources · end note</h1><div class="sub">Checklists (61 items per '
            f'lot) and 12 e-mail drafts are in the companion PDF: {PDF2}</div></div></div>')
    return (f'<section class="page" style="--acc:#1e3a8a">{band}<div class="fit"><div style="margin-top:5px">{score}</div>'
            f'<div class="two"><div>{todo}{limits}{end}</div><div>{src}{gloss}</div></div></div>'
            f'<div class="sp" style="flex:1"></div>{foot(10)}</section>')


# --------------------------------------------------------------------------- companion PDF
CSS2 = r"""
@page { size: 8.5in 11in; margin: 0.42in 0.4in 0.45in; }
body { font-family: "Noto Sans", "DJV", sans-serif; color: #0f172a; font-size: 6.4pt; line-height: 1.2;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; margin: 0; }
h1 { font-size: 13pt; margin: 0 0 2px; color: #1e3a8a; } h2 { font-size: 10pt; margin: 8px 0 3px; color: #1e3a8a; }
.sub { color: #475569; font-size: 6.8pt; margin-bottom: 5px; }
table.ck { width: 100%; border-collapse: collapse; font-size: 7.5pt; line-height: 1.22; }
table.ck th { background: #1e3a8a; color: #fff; text-align: left; padding: 3px 4px; }
table.ck td { border-bottom: 0.5px solid #e2e8f0; padding: 2.6px 4px; vertical-align: top; }
table.ck .t { display: inline-block; vertical-align: top; width: calc(100% - 38px); }
table.ck tr.sec td { background: #eef2ff; color: #1e3a8a; font-weight: 700; }
thead { display: table-header-group; } tr { break-inside: avoid; }
.s { display: inline-block; width: 31px; text-align: center; font-size: 5.6pt; font-weight: 700; border-radius: 3px;
     padding: 0.5px 0; margin-right: 4px; vertical-align: top; margin-top: 0.8px; }
.sub .s { width: auto; padding: 0 3px; }
.ok { background: #dcfce7; color: #166534; } .gis { background: #dbeafe; color: #1e40af; }
.con { background: #fef3c7; color: #92400e; } .bad { background: #fee2e2; color: #991b1b; }
.mails { column-count: 2; column-gap: 12px; }
.mail { break-inside: avoid; border: 1px solid #cbd5e1; border-radius: 6px; margin: 0 0 8px; padding: 4px 6px; }
.mail h3 { margin: 0 0 2px; font-size: 8.4pt; color: #0f766e; }
.mail .meta { font-size: 6.9pt; color: #334155; margin-bottom: 3px; }
.mail pre { white-space: pre-wrap; font-family: "Noto Sans", "DJV", sans-serif; font-size: 7.1pt; line-height: 1.25; margin: 0; }
.pb { break-before: page; }
"""


def companion_html():
    lab = {"ok": "OK", "gis": "GIS", "con": "ASK", "bad": "ISSUE"}
    head = ("<thead><tr><th style='width:3%'>#</th><th style='width:17%'>Item</th>"
            + "".join(f"<th style='background:{LOT[k]['acc']}'>#{i+1} {LOT[k]['name']}</th>" for i, k in enumerate(ORDER))
            + "</tr></thead>")
    body, sec, n = [], None, 0
    for row in CHECK:
        s, item = row[0], row[1]
        if s != sec:
            body.append(f"<tr class='sec'><td colspan='5'>{s}</td></tr>"); sec = s
        n += 1
        cells = "".join(f"<td><span class='s {c}'>{lab[c]}</span><span class='t'>{t}</span></td>" for c, t in check_cells(row))
        body.append(f"<tr><td>{n}</td><td>{item}</td>{cells}</tr>")
    counts = {k: {s: sum(1 for row in CHECK if row[SRC[k]][0] == s) for s in lab} for k in ORDER}
    summ = " · ".join(f"<b>{LOT[k]['short']}</b>: " + ", ".join(f"{counts[k][s]} {lab[s]}" for s in lab) for k in counts)
    ck_html = (f"<h1>Due-diligence checklist — 61 items, sections A–M</h1><div class='sub'>Status: <span class='s ok'>OK</span>checked "
               f"against an official record · <span class='s gis'>GIS</span>lidar/GIS estimate · <span class='s con'>ASK</span>still to "
               f"confirm with the named party · <span class='s bad'>ISSUE</span>problem found. {summ}</div>"
               f"<table class='ck'>{head}<tbody>{''.join(body)}</tbody></table>")
    mails = "".join(f"<div class='mail'><h3>{e['group']}</h3><div class='meta'><b>To:</b> {e['to']}<br><b>Subject:</b> "
                    f"{e['subject']}</div><pre>{e['body']}</pre></div>" for e in EMAILS)
    endnote = (f"<div class='mail' style='border-color:#0f172a;background:#f8fafc'><h3 style='color:#0f172a'>End note</h3>"
               f"<div class='meta'><b>Date of creation:</b> {CREATED:%d %B %Y} · <b>Prepared by AI model:</b> {MODEL} "
               f"(Anthropic), working in Kiro<br><b>Companion to:</b> {PDF1}<br>Desk study from public records; not legal, "
               "survey, appraisal or engineering advice.</div></div>")
    em_html = (f"<h1 class='pb'>Due-diligence e-mail drafts</h1><div class='sub'>One e-mail per listing agent, and one per "
               "authority or contractor covering all three lots, so each office answers once. Fill in your name and contact "
               "details. Phone numbers are from the agencies’ own pages; e-mail addresses not published are marked.</div>"
               f"<div class='mails'>{mails}{endnote}</div>")
    import matplotlib
    ttf = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    fonts = FONTS(ttf)
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts}{CSS2}</style></head><body>{ck_html}{em_html}</body></html>"


def write_markdown():
    d = os.path.join(ROOT, "docs", "shores3"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "CORRECTIONS.md"), "w") as fh:
        fh.write("# Corrections to “3 Corsicana lakefront lots Comparison” (checked 10 Nov 2026)\n\n"
                 "| Topic | Earlier report | Verified now | Source | Effect |\n|---|---|---|---|---|\n")
        for row in CORRECTIONS:
            fh.write("| " + " | ".join(x.replace("|", "/") for x in row) + " |\n")
    with open(os.path.join(d, "CHECKLIST.md"), "w") as fh:
        fh.write("# Due-diligence checklist — The Shores lots 442, 411, 441 (61 items)\n\n"
                 "Status: OK = official record checked · GIS = lidar/GIS estimate · ASK = still to confirm · ISSUE = problem found\n\n")
        lab = {"ok": "OK", "gis": "GIS", "con": "ASK", "bad": "ISSUE"}
        cols = " | ".join(f"#{i+1} {LOT[k]['short']}" for i, k in enumerate(ORDER))
        sec, n = None, 0
        for row in CHECK:
            s, item = row[0], row[1]
            if s != sec:
                fh.write(f"\n## {s}\n\n| # | Item | {cols} |\n|---|---|---|---|---|\n"); sec = s
            n += 1
            fh.write(f"| {n} | {item} | " + " | ".join(f"**{lab[c]}** {t}" for c, t in check_cells(row)) + " |\n")
    with open(os.path.join(d, "EMAILS.md"), "w") as fh:
        fh.write("# Due-diligence e-mail drafts — The Shores lots 442, 411, 441\n\n"
                 "Fill in your name and contact details before sending.\n")
        for e in EMAILS:
            # two trailing spaces = markdown line break, so the letter keeps its lines on GitHub
            body = "\n".join((ln + "  ") if ln.strip() else "" for ln in e["body"].split("\n"))
            fh.write(f"\n---\n\n## {e['group']}\n\n**To:** {e['to']}  \n**Subject:** {e['subject']}\n\n{body}\n")
    return d


def build_html():
    pages = [summary_page()]
    n = 2
    for k in ORDER:
        pages += [lot_page1(k, n), lot_page2(k, n + 1)]
        n += 2
    pages += [corrections_page(), feasibility_page(), final_page()]
    import matplotlib
    ttf = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    fonts = FONTS(ttf)
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>The Shores lots — revised due diligence ({STAMP})"
            f"</title><style>{fonts}{CSS}</style></head><body>{''.join(pages)}</body></html>")


async def render(html_path, pdf_path, check=True, footer=False):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 816, "height": 1056})
        await pg.goto("file://" + html_path, wait_until="load")
        # Load both fallback faces, then rebuild the DOM so every text run is shaped with them available.
        # Without this, runs shaped while DejaVu was still loading kept blank glyphs in the PDF.
        await pg.evaluate("""async () => {
          await Promise.all([document.fonts.load('400 10px DJV', '≈→≤≥✓'), document.fonts.load('700 10px DJV', '≈→≤≥✓')]);
          document.body.innerHTML = document.body.innerHTML;
          await Promise.all(Array.from(document.images).map(i => i.decode().catch(() => null)));
          await document.fonts.ready; }""")
        await pg.wait_for_timeout(500)
        over = []
        if check:
            # Lot fact pages: raise the font until the text just fills three columns (binary search, then
            # step down 0.1 pt as a margin for print rounding). The PDF is printed from this adjusted DOM.
            sizes = await pg.evaluate("""([lo0, hi0]) => {
              const out = [];
              document.querySelectorAll('.flow').forEach((f) => {
                const fits = (pt) => { f.style.fontSize = pt + 'pt'; return f.scrollWidth <= f.clientWidth + 1; };
                let lo = lo0, hi = hi0;
                if (!fits(lo)) { out.push('no fit at ' + lo); return; }
                for (let i = 0; i < 16; i++) { const mid = (lo + hi) / 2; if (fits(mid)) lo = mid; else hi = mid; }
                const pt = Math.floor((lo - 0.1) * 20) / 20;
                fits(pt); out.push(pt);
              });
              return out; }""", [6.0, 9.5])
            over.append(f"fact-page font sizes (pt): {sizes}")
            # Pages 1, 8, 9, 10: raise the .fit font until the page is full but the footer still has its gap.
            sizes = await pg.evaluate("""([lo0, hi0]) => {
              const out = [];
              document.querySelectorAll('.fit').forEach((w) => {
                const page = w.closest('.page'); const sp = page.querySelector('.sp');
                const ok = (pt) => { w.style.fontSize = pt + 'pt';
                  return page.scrollHeight <= page.clientHeight + 1 && (!sp || sp.getBoundingClientRect().height >= 4); };
                let lo = lo0, hi = hi0;
                if (!ok(lo)) { out.push('no fit at ' + lo); return; }
                for (let i = 0; i < 16; i++) { const mid = (lo + hi) / 2; if (ok(mid)) lo = mid; else hi = mid; }
                const pt = Math.floor((lo - 0.1) * 20) / 20;
                ok(pt); out.push(pt);
              });
              return out; }""", [6.0, 8.4])
            over.append(f"summary/back-page font sizes (pt): {sizes}")
            over += await pg.evaluate("""() => {
              const out = [];
              document.querySelectorAll('.page').forEach((p, i) => {
                if (p.scrollHeight > p.clientHeight + 1) out.push(`page ${i+1} OVERFLOWS by ${p.scrollHeight - p.clientHeight}px`);
                p.querySelectorAll('.flow').forEach((f) => {
                  const fr = f.getBoundingClientRect(); const r = f.lastElementChild.getBoundingClientRect();
                  const col = Math.floor((r.left - fr.left + 4) / (fr.width / 3)) + 1;
                  if (f.scrollWidth > f.clientWidth + 2) out.push(`page ${i+1} text OVERFLOWS into a 4th column`);
                  else out.push(`page ${i+1} text ends in column ${col}, ${Math.round(fr.bottom - r.bottom)}px spare`);
                });
                p.querySelectorAll('figcaption').forEach((fc) => {
                  if (fc.scrollHeight > fc.clientHeight + 1) out.push(`page ${i+1} caption clipped: ${fc.textContent.slice(0, 60)}`);
                });
                const f = p.querySelector('.foot');
                const kids = Array.from(p.children).filter(c => !c.classList.contains('foot') && c.innerHTML.trim() !== '');
                const last = Math.max(...kids.map(c => c.getBoundingClientRect().bottom)) - p.getBoundingClientRect().top;
                out.push(`page ${i+1} content bottom ${Math.round(last)}px, footer ${f ? Math.round(f.getBoundingClientRect().top - p.getBoundingClientRect().top) : '-'}px`);
              });
              return out; }""")
        kw = dict(path=pdf_path, width="8.5in", height="11in", print_background=True)
        if footer:
            kw.update(display_header_footer=True, header_template="<span></span>",
                      footer_template=("<div style='font-size:6px;width:100%;padding:0 0.4in;color:#64748b;display:flex;"
                                       "justify-content:space-between'><span>The Shores lots 442, 411, 441 · checklists & "
                                       f"e-mail drafts</span><span>created {CREATED:%d %b %Y} · {MODEL} · p "
                                       "<span class='pageNumber'></span>/<span class='totalPages'></span></span></div>"),
                      margin={"top": "0.42in", "right": "0.4in", "bottom": "0.45in", "left": "0.4in"})
        else:
            kw.update(margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True)
        await pg.pdf(**kw)
        await b.close()
    return over


def main():
    import fitz
    dpi = int(sys.argv[1]) if len(sys.argv) > 1 else 110
    prev = os.path.join(OUT, "preview"); os.makedirs(prev, exist_ok=True)
    for old in os.listdir(prev):                 # drop pages left over from a longer earlier build
        if old.endswith(".png"):
            os.remove(os.path.join(prev, old))
    for name, html, check, footer in ((PDF1, build_html(), True, False), (PDF2, companion_html(), False, True)):
        hp = os.path.join(OUT, name.replace(".pdf", ".html"))
        open(hp, "w", encoding="utf-8").write(html)
        pdf = os.path.join(ROOT, name)
        for o in asyncio.run(render(hp, pdf, check, footer)):
            print("  ", o)
        doc = fitz.open(pdf)
        print("PDF:", name, f"{os.path.getsize(pdf)/1e6:.1f} MB", len(doc), "pages", f"{doc[0].rect.width/72:.2f}x{doc[0].rect.height/72:.2f} in")
        blank = {i + 1: n for i, pg in enumerate(doc) if (n := pg.get_text().count("\x00"))}
        print("   blank (missing) glyphs per page:", blank or "none")
        tag_ = "r" if name == PDF1 else "c"
        for i, pg in enumerate(doc):
            pg.get_pixmap(dpi=dpi).save(os.path.join(prev, f"{tag_}{i+1}.png"))
    print("markdown:", write_markdown())


if __name__ == "__main__":
    main()
