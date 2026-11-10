"""Content for the 10 Nov 2026 big-home + dock due-diligence PDF on 11 Bayview Cir and 5001 Arrowhead Pt
(LOTSET=two): facts with their evidence tags, alerts, first steps and costs, e-mail drafts, glossary, sources.

Numbers about the largest house and dock come from data/bigbuild.json (15_twolots_bigbuild.py). Everything
else is typed in from the records named next to it, read on 8-10 Nov 2026.
"""
import datetime as dt
import re

from common import load

CREATED = dt.date(2026, 11, 10)
MODEL = "Claude Opus 5.5"
STAMP = CREATED.strftime("%d-%b-%y")
LAKE_NOW, LAKE_NOW_DATE = 312.16, "9 Nov 2026"      # TWDB daily level
BB = load("bigbuild.json")
A, B = BB["bayview"], BB["arrowhead"]
HA, HB, HB75 = A["lake50"], B["lake50"], B["lake75"]
DA, DB = A["dock"], B["dock"]

RATE_A = 0.35 + 0.1077 + 0.0054 + 0.0691 + 1.0408            # 1.5730 %
RATE_B = 0.25 + 0.35 + 0.1077 + 0.0054 + 0.0691 + 0.9295     # 1.7117 %


def money(v):
    return f"${v:,.0f}"


LOT = {
    "bayview": dict(
        L="A", name="11 Bayview Cir", town="Corsicana, TX 75109", sub="White Rock Sub. Lot 11",
        acc="#0f766e", grad="linear-gradient(95deg,#115e59,#0f766e 45%,#0d9488)",
        legal="W0305 WHITE ROCK SUB LOT 11 .65 ACRES", cad_id="63254", mls="21146775",
        price=89900, cad=88808, cad_land=85197, acres=0.65, legal_sf=28314,
        tax=88808 * RATE_A / 100, rate=RATE_A,
        agent="John & Julie Teel, RE/MAX LakeSide Dreams", agent_tel="903-874-0001 · 903-328-1487",
        agent_mail="julie@teelteam.com",
        owner="Jason Hamad (Dallas), bought 15 Jul 2022",
        water="M.E.N. WSC (TX1750015)",
    ),
    "arrowhead": dict(
        L="B", name="5001 Arrowhead Pt", town="Streetman, TX 75859", sub="Rustling Oaks Estates Ph II, Blk 1 Lot 33",
        acc="#6d28d9", grad="linear-gradient(95deg,#4c1d95,#6d28d9 45%,#7c3aed)",
        legal="R1550.02 RUSTLING OAKS ESTATES PHASE II BLK 1 LOT 33 .5 ACRES", cad_id="56587", mls="21298338",
        price=99900, cad=68849, cad_land=65340, acres=0.50, legal_sf=21780,
        tax=56796 * RATE_B / 100, tax_full=68849 * RATE_B / 100, rate=RATE_B,
        agent="Laura Smith, Keller Williams Realty", agent_tel="817-795-2500 (broker line)",
        agent_mail="not published; use the MLS / LakeHouse contact form",
        owner="Danny & Leanna Pitts, who live next door at 5003 (Lot 32); deed 10 Apr 2015",
        water="Winkler WSC (TX1750023)",
    ),
}


# --------------------------------------------------------------------------- verdicts (summary page)
VERDICT = {
    "bayview": (f"<b>Big home: yes.</b> HOA sewer means no drip field, so only the set-backs, the "
                f"wedge shape and Zone A limit the house: up to a {HA['W']}×{HA['D']} ft footprint, "
                f"≈{HA['heated_2st_sf']:,} sf heated on two storeys in theory. <b>Private dock: yes, up to "
                f"{DA['cap_sf']:,} sf</b> in a basin about {DA['width_at_dock']:.0f} ft across, shared with two neighbours' "
                f"boathouses. <b>Main unknown: water depth.</b> TWDB never sounded the basin, so sound it before you buy. "
                f"Also check the HOA sewer plant, which settled a TCEQ order for 2023–24 effluent violations."),
    "arrowhead": (f"<b>Big home: yes, but the septic drip field sets the limit</b>: ≈{HB75['heated_2st_sf']:,}–"
                  f"{HB['heated_2st_sf']:,} sf heated in theory. That is far above the 2,200–3,500 sf of Rustling Oaks' "
                  f"most valuable homes. <b>Private dock: yes, up to {DB['cap_sf']:,} sf.</b> Water is "
                  f"{DB['depth_pool']:.0f} ft deep at full pool and {DB['depth_now']:.0f} ft today, {DB['reach_ft']:.0f} ft "
                  f"out from the bank (TWDB survey). Low holding cost ($144/yr dues), but the CC&Rs require the outside "
                  f"walls and roof to be finished within 120 days of starting, and they ban private wells."),
}


BOTTOM_LINE = ("For the biggest house with a private boathouse, <b>Lot A is the stronger site if two things check out</b>: "
               "the basin is at least ≈5 ft deep at full pool where the boathouse would go (or TRWD allows dredging), "
               "and the HOA confirms a sewer tap with no large assessment coming. Its neighbours are $1M+ homes, so a "
               "large house fits the street. <b>Lot B has measured water</b> (≈6 ft at full pool, 30 ft out) and costs "
               "about $3.5k a year less to hold. But the drip field caps the house, anything much over 3,500 sf would "
               "out-build Rustling Oaks, and the CC&Rs want the shell finished within 120 days. Find out about A's "
               "depth and sewer first; they decide the choice.")


# --------------------------------------------------------------------------- per-lot alerts and steps
NOTES = {
    "bayview": dict(
        pos=["HOA sewer: no septic field, so the most room for a house, pool and yard",
             f"Cheapest way into White Rock: the CAD values Lot 11 at {money(85197)} of land, about half the median "
             f"for the 12 vacant White Rock lots ($166k)",
             "Two neighbours built 977- and 1,024-sf boathouses on the same water in 2023, so TRWD has approved "
             "boathouses here",
             "Gated, 16 of 28 lots built, median home value about $1.2M (CAD), so a large home fits the street",
             "Steel bulkhead already in place (CAD: 170 ft, 2015)",
             "Asking price equals the CAD value; listed on and off since 2022, so there is room to negotiate"],
        neg=["Basin depth unknown: the TWDB 2018 soundings stop about 200 ft away, where the bottom is 306.3 ft "
             "(8.7 ft deep at full pool, 5.9 ft today)",
             f"The basin is {DA['width315_min']:.0f}–{DA['width315_max']:.0f} ft across at full pool, so one third of "
             f"its width limits how far a dock can reach (about {DA['lim']:.0f} ft here)",
             "The lot is a wedge that narrows to the water; 13% of it (the shore strip) is FEMA Zone A",
             "HOA dues $3,530/yr while you hold the lot (MLS figure, sewer included)",
             "White Rock's CC&Rs are not online. Height limits, set-backs from the water, boathouse rules and "
             "build-time limits are all unknown"],
        alert=["The HOA's sewer plant (TCEQ permit WQ0014821002, 8,000 gal/day for 28 lots) broke its effluent "
               "limits for at least nine months in 2023–24. The TCEQ agreed order (Texas Register notice, 19 Dec 2025) deferred "
               "$18,150 of a $21,750 penalty for financial inability to pay. Ask about special assessments, "
               "plant upgrades and spare capacity before you commit",
               "The listing says “deep water”. That describes the main lake, not the basin in front of the lot",
               "The Teel team lists this lot and also advertises as buyer's agents. Use your own buyer's agent or "
               "get the intermediary terms in writing"],
        steps=["Before any offer, sound the basin on site: depth at 10, 20, 30 ft out, at full pool and today "
               "(a marked pole from a kayak works).",
               "Get the CC&Rs, the HOA budget and the sewer plant's status in writing (HOA e-mail).",
               "Ask TRWD whether a 1,200-sf boathouse fits beside the two existing ones, and whether dredging is "
               "allowed if the basin is shallow.",
               "Offer ≈$80–85k with a 21–30-day option. Make it subject to TRWD's dock answer and the HOA's "
               "written sewer-tap confirmation.",
               "Survey in the option period: corners, 315/320-ft lines, Zone A line, bulkhead position."]),
    "arrowhead": dict(
        pos=["Lowest carrying cost: $144/yr POA dues (recorded CC&Rs) and about $970–1,180/yr tax today",
             "Phase II was platted in 1990, so TRWD's 1-acre septic rule (lots split after 8 Apr 2011) does not "
             "apply; the legal 0.500 ac meets TCEQ's ½-acre minimum",
             f"Real survey depth under the dock: {DB['depth_pool']} ft at full pool, {DB['depth_now']} ft today; "
             f"a {DB['deepest']['reach_ft']}-ft reach gives {DB['deepest']['depth_pool']} / {DB['deepest']['depth_now']} ft",
             "Flat, high ground: 99.8% above 320 ft, only 2.5% in Zone A",
             "Short, permissive CC&Rs: 1,600 sf minimum, 5-ft side and rear set-backs, no size or height cap",
             "TRWD's Richland-Chambers office is in Streetman, 140 FM 416"],
        neg=["Asking $99,900 is 1.45× the 2026 CAD value ($68,849), which itself rose 45% in one year",
             "The tax is capped now (taxable $56,796, the 20% circuit breaker). The cap ends for a buyer: "
             "≈$1,540/yr at a $90k value",
             "Over-building risk: Rustling Oaks' most valuable homes are 2,200–3,500 sf (CAD up to $844k)",
             "The drip field limits the house; a pool would compete with it for space",
             "Developer Kodiak TJ LLC still owns 54 vacant lots nearby, which may hold resale prices down"],
        alert=["CC&R ¶H: outside walls painted and roof finished within 120 days of starting. That is tight for a "
               "large custom home; agree how the ACC counts the 120 days before you pour the slab",
               "CC&R ¶J: owners may not drill water wells. ¶G: metal roofs need ACC approval",
               "The CAD GIS lot line runs 8–21 ft back from the full-pool water's edge, near the 320-ft contour. "
               "The survey must show where the plat line is, and TRWD must agree on the shoreline length",
               "The seller owns the house next door. Check that none of 5003's septic, drip lines, water line, "
               "fence or irrigation sits on Lot 33",
               "POA roads take 6-yard concrete loads only (50,000 lb), so a big slab means more truck trips and "
               "short-load fees"],
        steps=["Ask the POA/ACC how they apply the 120-day rule to a large home, and confirm the $144 vs $644 fee "
               "($644 may be dues plus the $500 road fee).",
               "Ask TRWD how it measures the shoreline here and whether a 30–50-ft walkway is acceptable.",
               "Offer ≈$85–90k with a 21–30-day option, subject to a septic site evaluation for 6 bedrooms and "
               "the survey.",
               "In the option period, get the survey (plat line vs 315/320 ft, encroachments from 5003) and the "
               "septic evaluation.",
               "Walk away if the drip field will not fit your bedroom count, or the survey shows 5003's "
               "systems on the lot."]),
}


# --------------------------------------------------------------------------- staged plan with costs
PLAN = [
    ("0", "This week", "Send the 14 e-mail drafts in this document; call TRWD; read the TCEQ file on the White Rock "
     "plant; check the County Clerk records for plats and CC&Rs", "$0", "both"),
    ("0", "This week", "Visit both lots while the lake is 2.8 ft low: see the bank and walls; measure depth at the "
     "dock spot with a marked pole from a kayak; ask the seller to show the corner pins", "$0–150 (fuel, kayak)", "both"),
    ("1", "Week 2–3", "Pick ONE lot from the answers. Offer with a 21–30-day option period and the contingencies "
     "below", "Option fee $200–500, credited at closing", "one"),
    ("2", "Option period", "Boundary + topographic survey: corners, 315/320-ft lines, Zone A line, walls, trees, "
     "easements; add a few depth soundings at the dock spot", "$2,000–3,500 (+$300–500 soundings)", "one"),
    ("2", "Option period", "Septic site evaluation with soil profile holes for 6 bedrooms (Lot B only)",
     "$750–1,500", "B"),
    ("2", "Option period", "HOA/POA resale certificate, title commitment, TRWD pre-application site meeting, dock "
     "builder's site visit and budget", "$0–375 (certificate; the seller often pays)", "one"),
    ("2", "Option period", "Optional: designer's test fit of the house on the survey", "$500–2,500", "one"),
    ("3", "After closing", "Geotechnical report; architect and engineer; septic design and TRWD OSSF permit (B); "
     "TRWD dock permit; ACC/HOA approval; county permit ($0.25/sf of heated area)", "$1,800–3,000 geotech + permits "
     "≈$0.7–3k + design", "one"),
]
SPEND = {"bayview": "≈$2.2–4.4k", "arrowhead": "≈$3.0–5.9k"}

CONTINGENCIES = [
    "Option period of 21–30 days (TREC contract, paragraph 5); you can end the contract for any reason and lose "
    "only the option fee.",
    "TRWD written answer on dock size and reach (and dredging for Lot A) before the option ends.",
    "Lot A: HOA letter confirming a sewer tap for Lot 11, the tap fee, and no pending special assessment.",
    "Lot B: septic site evaluation that supports a 6-bedroom aerobic + drip system.",
    "Survey that matches the legal description, with no encroachments; title commitment with the easements listed.",
    "Seller's disclosure and copies of any TRWD permits for the existing walls.",
]

AREA = dict(
    pos=["Richland-Chambers is Texas's third-largest inland lake: 43,874 ac at full pool, 25.6 ft mean and 76.8 ft "
         "maximum depth (TWDB 2018)",
         "Both house pads sit near 327–329 ft, 9–11 ft above TRWD's 318-ft 100-year lake level, so no fill is needed",
         "TRWD's 2026 rules are published and cheap to use: dock permit $300, septic permit $400, 10 + 30 business "
         "days review",
         "Navarro County grew 8.6% from 2020 to 2025"],
    neg=["The lake was below 312 ft on 27% of days since 2000; the 2006 low (303.6 ft) dried both coves. Expect "
         "seasons when a lift sits in mud",
         "Expansive clay (shrink-swell LEP ≈9%): plan an engineered post-tensioned slab or piers; for a big house "
         "budget $60–120k for foundation and pad",
         "FEMA NRI rates tornado and wind risk relatively high and hail moderate: wind/hail deductibles and the "
         "roof choice matter",
         "Property tax runs 1.57% (A) to 1.71% (B) of value: a $2M home ≈$31k/yr, a $1.4M home ≈$24k/yr before any "
         "homestead exemption"],
    alert=["Order of approvals: HOA/ACC → TRWD (dock, walls; septic for B) → county building permit (needs the "
           "OSSF permit number and a site plan) → three third-party inspections → 911 address",
           "Over-improvement: lenders and appraisers compare with nearby sales. A very large house can appraise "
           "below its cost, which matters if you need a construction loan",
           "Lake water belongs to TRWD: irrigation from the lake and any work below 320 ft need a TRWD permit"],
)

COSTS = {
    "bayview": [("House, ≈6,000 sf heated + 3-car garage, ≥60% stone/glass", "$300–400/sf", "$1.8–2.4M"),
                ("Foundation engineering, pad, drainage on clay", "", "$60–120k"),
                ("Boathouse ≤1,200 sf with lift and sundeck", "", "$100–200k"),
                ("Sewer tap, water, electric, HOA review", "", "$15–35k"),
                ("Design, survey, geotech, permits", "", "$60–120k")],
    "arrowhead": [("House, ≈5,000 sf heated + 3-car garage", "$250–325/sf", "$1.25–1.6M"),
                  ("Aerobic septic + 6,000-sf drip field (6 BR)", "", "$25–45k"),
                  ("Foundation engineering, pad, drainage on clay", "", "$50–100k"),
                  ("Boathouse 918 sf with lift + 10–30-ft walkway", "", "$80–160k"),
                  ("Water, electric, POA fees ($500 + $0.85/sf of slab)", "", "$15–30k"),
                  ("Design, survey, geotech, permits", "", "$50–100k")],
}


# --------------------------------------------------------------------------- e-mails
SIGN = "[Your name]\n[Phone] · [E-mail]"
LOTLINE = {"bayview": "11 Bayview Cir, Corsicana TX 75109 — White Rock Sub. Lot 11, 0.65 ac — Navarro CAD 63254 — "
                      "MLS 21146775",
           "arrowhead": "5001 Arrowhead Pt, Streetman TX 75859 — Rustling Oaks Estates Ph II Blk 1 Lot 33, 0.50 ac — "
                        "Navarro CAD 56587 — MLS 21298338"}
EMAILS = []
_NEW = re.compile(r"^\s*(\d+\.\s|-\s|\[|Hello|Thank you|Lot:|Lots:|Questions:|Scope:|Water \(|Electric \(|For Lot)")


def unwrap(body):
    """Join hard-wrapped source lines so each paragraph or numbered item is one line."""
    out = []
    for ln in body.split("\n"):
        if not ln.strip():
            out.append("")
        elif out and out[-1] != "" and not _NEW.match(ln):
            out[-1] = out[-1].rstrip() + " " + ln.strip()
        else:
            out.append(ln.rstrip())
    return "\n".join(out)


def mail(group, to, subject, body, lots="A + B"):
    EMAILS.append(dict(group=group, to=to, subject=subject, body=unwrap(body.strip()), lots=lots))


mail("Listing agent — 11 Bayview Cir", "John & Julie Teel, RE/MAX LakeSide Dreams · julie@teelteam.com · 903-874-0001",
     "Questions before an offer — Lot 11 Bayview Cir, White Rock (MLS 21146775)",
     f"""
Hello Julie and John,

I am interested in Lot 11 Bayview Circle and plan to build a large home with a private boathouse. Before I make an
offer, could you help with the following?

1. The seller's disclosure, any survey, and the recorded White Rock plat (volume and page).
2. The White Rock CC&Rs and architectural guidelines, the HOA budget, and the HOA contact for a buyer.
3. Is a sewer stub in place for Lot 11? What is the tap fee? Is any special assessment planned for the sewer plant?
4. Does the steel bulkhead have a TRWD permit? Has the basin in front of the lot ever been sounded or dredged?
5. White Rock lot and home sales in the last 24 months (MLS sold data).
6. Any earlier contracts that failed, and how flexible the seller is on price and on a 21–30-day option period.
7. You also advertise as buyer's agents. If I wrote an offer through you, would you act as intermediary? Please
   send the terms.

Lot: {LOTLINE['bayview']}

Thank you,
{SIGN}
""", "A")

mail("Listing agent — 5001 Arrowhead Pt", "Laura Smith, Keller Williams Realty · 817-795-2500 (e-mail not published; "
     "use the MLS or LakeHouse.com contact form)",
     "Questions before an offer — 5001 Arrowhead Point, Rustling Oaks (MLS 21298338)",
     f"""
Hello Ms. Smith,

I am interested in 5001 Arrowhead Point and plan to build a large home with a private boathouse. Before I make an
offer, could you help with the following?

1. The seller's disclosure, any survey, and the CC&Rs mentioned in the listing (“available in Transaction Desk”).
2. The sellers live next door at 5003. Do any of 5003's septic tank, drip lines, water or power lines, fence,
   irrigation or driveway sit on Lot 33?
3. Does the 2020 steel wall have a TRWD permit? Where is the sellers' boathouse relative to the shared line?
4. The MLS shows POA dues of $644/yr; the recorded CC&Rs set $12/month. Does $644 include the $500 road fee?
5. Any septic site evaluation, perc test or soil report for Lot 33.
6. Rustling Oaks waterfront lot and home sales in the last 24 months (MLS sold data).
7. The 2026 CAD value is $68,849. How flexible are the sellers on price and on a 21–30-day option period?

Lot: {LOTLINE['arrowhead']}

Thank you,
{SIGN}
""", "B")

mail("HOA — White Rock Homeowners Association", "White Rock Homeowners Association, Inc., 300 White Rock Rd, Corsicana "
     "TX 75109 · attn. the Board (TCEQ filings of 2024–25 name Susan Gilliland as President) · e-mail not published: "
     "ask the listing agent to forward",
     "Prospective buyer, Lot 11 Bayview Circle: rules, dues and sewer",
     f"""
Hello,

I may buy Lot 11 Bayview Circle (Navarro CAD 63254) and build a large home (5,000+ sq ft) with a private boathouse.
Could the Board or architectural committee help with these questions?

1. The recorded CC&Rs, any amendments, and the architectural guidelines: minimum and maximum size, height, set-backs
   from the water and side lines, exterior materials, roofs, fences, and any time limit to start or finish building.
2. Rules for docks and boathouses in the Bayview basin, which Lot 11 shares with two existing boathouses.
3. 2026 and expected 2027 dues ($3,530/yr per the MLS). What do they cover? Any special assessment, planned or
   under discussion?
4. The sewer plant: has the TCEQ agreed order (Docket 2024-0591-MWD-E) been met? What is the status of the TPDES
   permit renewal (WQ0014821002)? With a permit of 8,000 gallons a day, how many more homes can the plant take?
   Is a tap reserved for Lot 11, and what are the tap fee and connection rules (gravity or grinder pump)?
5. The reserve fund balance and the latest budget.
6. Resale certificate and transfer fees, and the rules for contractors and gate access during construction.
7. Rules on rentals and on short stays.

Lot: {LOTLINE['bayview']}

Thank you,
{SIGN}
""", "A")

mail("POA — Rustling Oaks Estates POA and ACC", "ACC: Mike Stotler · mstotler9686@gmail.com · 281-900-9686; cc Richard "
     "Coker · rc.lake01@gmail.com; Michael Norris · Michael.L.Norris@outlook.com · POA: 4001 Loper Dr, Streetman TX "
     "75859-7260 (2026 President Dan Plume)",
     "Prospective buyer, Phase II Lot 33 (5001 Arrowhead Pt): ACC rules for a large home and boathouse",
     f"""
Hello Mr. Stotler,

I may buy 5001 Arrowhead Point (Phase II, Block 1, Lot 33) and build a large home (4,000–5,500 sq ft) with a
boathouse. I have read the Phase II Declaration (Vol. 1224, p. 638) and the ACC handbook. Could you confirm:

1. Annual dues: $12/month per the Declaration. The MLS shows $644/yr. Is that the dues plus the $500 road fee?
   Any special assessment, planned or past due, on Lot 33?
2. Paragraph H requires exterior walls and roof complete within 120 days after construction starts. How does the
   ACC count the 120 days for a large custom home (from the slab pour?), and can it be extended?
3. Any recorded amendments to the Phase II Declaration since 1991.
4. ACC rules for boathouses and walkways (size, roof, colour) beyond TRWD's, and the $750 boathouse fee.
5. Any limit on height or size? Do you approve metal roofs (paragraph G)?
6. For a large slab, the concrete-truck rules (6-yard loads) and the fee of $0.85 per sq ft of slab.
7. What utilities run in the 30-ft front easement on Lot 33?
8. Is the 2013 lawsuit with the developer settled, and is any other dispute open?
9. The resale certificate fee, and how long ACC approval usually takes.

Lot: {LOTLINE['arrowhead']}

Thank you,
{SIGN}
""", "B")

mail("TRWD — Richland-Chambers permits (docks, walls, septic)", "TRWD Richland-Chambers office, 140 FM 416, Streetman "
     "TX 75859 · (903) 389-3928 (8–11 am Mon–Thu) · fax (903) 389-7587 · ask for the permit staff e-mail",
     "Pre-application questions: dock size and septic for two lots (Bayview Cir and Arrowhead Pt)",
     f"""
Hello,

I am deciding between two lots and want to understand what TRWD would permit before I commit. I would welcome a
pre-application site meeting.
  - {LOTLINE['bayview']} — about 158 ft of shoreline on a basin about 90–100 ft wide; steel bulkhead (CAD: 2015)
  - {LOTLINE['arrowhead']} — about 115 ft of shoreline where a narrow channel meets a wider cove; steel wall
    (CAD: 2020)

Questions:
1. Shoreline length you would use for the Attachment I size limit on each lot. For Bayview the formula gives
   1,230 sq ft; I plan to stay at 1,200 sq ft to keep the 5-ft side clearance. Is that right?
2. Bayview: the basin already has two boathouses (218 White Rock and 114 Bayview, both 2023). How far could a
   new boathouse extend, and what passage must it leave? Is dredging allowed if the basin is shallow?
3. Arrowhead: the CAD line sits 8–21 ft back from the 315-ft water's edge. Is that strip District Land, and how
   do you measure the shoreline? Would you accept a 30–50-ft walkway to reach about 6–7 ft of water at full pool?
4. Do you have permits on file for the existing walls on both lots, and for the boathouse at 5003 Arrowhead Pt?
5. Septic at Arrowhead: Phase II was platted in 1990. Please confirm that §3.03(c) of the 2026 OSSF Guidelines
   (1-acre minimum) does not apply, and which set-back from the 315-ft line you apply to a drip field on clay.
   Are there OSSF records for Lot 33 or for the system at 5003?
6. Typical review times for a dock permit and a residential OSSF permit.

Thank you,
{SIGN}
""")

mail("Navarro County Planning & Development", "Stanley Young, Director · syoung@navarrocounty.org · 601 N. 13th St., "
     "Suite 1, Corsicana TX 75110 · (903) 875-3312 · fax (903) 875-3314",
     "Zoning and permit questions for two lakeshore lots (CAD 63254 and 56587)",
     f"""
Hello Mr. Young,

I am evaluating two vacant lots inside the Richland-Chambers lakeshore zoning area and plan a large two-storey home
on one of them:
  - {LOTLINE['bayview']}
  - {LOTLINE['arrowhead']}

Could you confirm in writing:
1. The zoning district of each lot (SF-3 or another), with the front, rear and side set-backs, maximum coverage and
   maximum height. Is “2½ stories” the only height limit, or is there a limit in feet?
2. How the 50% rule for the area behind the side-line midpoints is measured on a wedge-shaped lot (Bayview).
3. Whether a floodplain development permit or a minimum floor elevation applies where a lot has a Zone A strip
   along the water (13% of the Bayview lot).
4. Whether an accessory dwelling (up to 40% of the house) and a detached garage are allowed.
5. The building permit fee ($0.25 per sq ft of heated area), the three required inspections, and the 911 address
   process.
6. For Arrowhead: whether the county or TRWD issues the septic permit, and whether a temporary RV during
   construction needs a Specific Use Permit.

Thank you,
{SIGN}
""")

mail("Navarro CAD — value questions", "Navarro Central Appraisal District, 1250 N. 45th St., Corsicana TX 75110 · (903) "
     "872-6161 · general.info@navarrocad.com",
     "Questions about 2026 values for parcels 63254 and 56587",
     f"""
Hello,

I am a prospective buyer of two vacant lots and would like to understand their values:
1. Parcel 56587 (5001 Arrowhead Pt): the 2026 market value is $68,849 and the taxable value is $56,796. Is the
   difference the 20% circuit-breaker limit (2025 value $47,330 × 1.2)? Will the 2027 value for a new owner be the
   full market value?
2. Parcel 56587: land rose from $43,560 to $65,340 in 2026. Was this a neighbourhood-wide change?
3. Parcel 63254 (11 Bayview Cir): land is $85,197, about half the value of other vacant White Rock lots. What
   adjustment explains it (shape, flood zone, water frontage)?
4. How would a sale price be used in setting the 2027 values?

Thank you,
{SIGN}
""")

mail("Utilities — water and electric", "M.E.N. WSC, 8542 S US Hwy 287, Corsicana · (903) 872-1899 (Bayview)   |   Winkler "
     "WSC, 2038 Loper Dr, Streetman · (903) 599-9096 (Arrowhead; number from its nonprofit listing)   |   Navarro County "
     "Electric Co-op · (903) 874-7411 (both)",
     "New service for a large home: availability and fees",
     f"""
Hello,

I may build a large home (5–6 bedrooms, 5,000+ sq ft) on one of these lots, both inside your service area on the
state map:
  - {LOTLINE['bayview']} (M.E.N. WSC)
  - {LOTLINE['arrowhead']} (Winkler WSC)

Water: Is a 1-in meter available at the lot (for a large home with irrigation and possibly fire sprinklers)? What
are the membership, tap and impact fees, the lead time and the typical pressure? Any moratorium?
Electric (NCEC): Is service at the road? What would a 400-amp underground service cost, including a feed to the
boathouse, and how long does it take?

Thank you,
{SIGN}
""")

mail("Surveyor — request for quote", "e.g. Jimmy W. Pogue Inc. Land Surveyors (serves Navarro County) · Andress "
     "Surveying · any Texas RPLS who works on TRWD lakes",
     "Quote: boundary + topographic survey of a lakefront lot (one of two)",
     f"""
Hello,

Please quote a boundary and topographic survey for one of these lots (I will confirm which):
  - {LOTLINE['bayview']}
  - {LOTLINE['arrowhead']}

Scope:
1. Boundary with corners found or set, the recorded plat lines, easements, and any encroachments (for
   Arrowhead, check whether anything of the house next door at 5003 sits on Lot 33).
2. 1-ft contours (NAVD88) with the 315-ft and 320-ft lines, the FEMA Zone A line, top and toe of bank, and the
   steel wall.
3. For Arrowhead: where the plat's water line sits relative to the 315-ft and 320-ft lines.
4. Trees of 10 in and larger in the building area.
5. Add-on: water depths at the planned dock spot (every 10 ft out to 60 ft) with the lake level of the day.

Please include price, turnaround and a sample drawing.

Thank you,
{SIGN}
""")

mail("Septic designer / site evaluator (Lot B)", "TRWD-registered OSSF designer or professional sanitarian (ask TRWD "
     "(903) 389-3928 for local names)",
     "Quote: site evaluation and aerobic + drip design for a 6-bedroom home",
     f"""
Hello,

I am evaluating {LOTLINE['arrowhead']}. TRWD permits septic here. I want the largest home the lot can serve: about
5,000–9,000 sq ft heated with 6 bedrooms.

Please quote:
1. Soil profile holes and a site evaluation (soil class within 1 ft of the emitters).
2. A preliminary layout for an aerobic unit + subsurface drip, showing the set-back from the 315-ft line, the
   30-ft front easement, and the drip area for 420, 480, 540 and 600 gal/day.
3. Locating the system of the house next door (5003, same owner) to confirm it is not on Lot 33.
4. Installed cost range and the yearly maintenance contract.

Thank you,
{SIGN}
""", "B")

mail("Geotechnical engineer — request for quote", "Licensed geotechnical firm serving Navarro County (Corsicana, "
     "Waxahachie or Dallas)",
     "Quote: geotechnical report for a large two-storey home on expansive clay",
     f"""
Hello,

Please quote a residential geotechnical investigation for a two-storey home of about 5,000–7,000 sq ft (footprint
about 6,000 sq ft with garage) on one of these lots:
  - {LOTLINE['bayview']} — about 21 ft of fall to a steel bulkhead
  - {LOTLINE['arrowhead']} — about 10 ft of fall to a steel wall

NRCS maps sandy loam over clay with high shrink-swell. Scope: borings to 20–25 ft, PVR, post-tensioned slab and
pier design values, and comments on building near the wall and bank.

Thank you,
{SIGN}
""")

mail("Dock builder — budget and site visit", "e.g. Kyle Construction (Streetman, boathouses since 1984) · BR Construction "
     "LLC (Corsicana) · Goodin and Perry Construction (Corsicana) — names from their own listings, not endorsements",
     "Budget for a covered boathouse with lift on Richland-Chambers",
     f"""
Hello,

I am choosing between two lots and would like a site visit and a budget range for a private boathouse on each:
  - {LOTLINE['bayview']} — up to 1,200 sq ft in a basin about 90–100 ft wide; depth not surveyed
  - {LOTLINE['arrowhead']} — up to 918 sq ft, about 6 ft deep at full pool 30 ft out (TWDB 2018 survey)

Questions:
1. Budget for a covered single or double slip with a lift for a 22–24-ft wake boat, and a sundeck (two storeys
   at most, lower deck 18 in above 320 ft).
2. Could you sound the water at the dock spot? Would you recommend dredging, a longer walkway, or both?
3. The condition of the existing steel walls.
4. Do you handle the TRWD permit and its insurance requirements? Current lead time?

Thank you,
{SIGN}
""")

mail("Title company — preliminary title", "e.g. Navarro County Abstract Co. · Micro Title Navarro County · Royal Title "
     "(Corsicana)",
     "Preliminary title report for a vacant lakefront lot (one of two)",
     f"""
Hello,

Before contracting, I would like a preliminary title report or a quote for one of these lots:
  - {LOTLINE['bayview']}
  - {LOTLINE['arrowhead']}

Please list recorded easements (including TRWD flowage easements to 320 ft and, for Arrowhead, the 30-ft front
easement in the Phase II Declaration, Vol. 1224 p. 638), the CC&Rs and amendments that apply, mineral reservations,
liens, HOA or POA liens, and any agreement between Lots 32 and 33 of Rustling Oaks Ph II (one owner holds both).

Thank you,
{SIGN}
""")

mail("Insurance agent — quotes for budgeting", "Any agent who writes Texas lake homes (wind/hail and flood)",
     "Insurance estimate for a large lake home and boathouse",
     f"""
Hello,

I plan to build a 5,000–7,000 sq ft home with a covered boathouse on Richland-Chambers Lake (Navarro County),
either at 11 Bayview Cir, Corsicana 75109 or at 5001 Arrowhead Pt, Streetman 75859. Both house sites are in FEMA
Zone X, with a Zone A strip along the water.

Could you give a rough yearly range for: builder's risk during construction; homeowners cover with wind and hail
(and the usual deductible); a preferred-risk flood policy; and boathouse and lift cover?

Thank you,
{SIGN}
""")


# --------------------------------------------------------------------------- glossary and sources
GLOSSARY = [
    ("315 ft / 320 ft", "Richland-Chambers normal pool / TRWD flood-flowage line (ft above sea level)"),
    ("TRWD", "Tarrant Regional Water District: owns the lake, permits docks, walls and (here) septic systems"),
    ("Attachment I", "TRWD Residential Improvement Permit Guidelines (2026): dock size and placement rules"),
    ("Navigable passage", "open water a dock must leave: ≥20 ft wide in a residential cove (TRWD ordinance)"),
    ("One-third rule", "TRWD guideline: no structure may take more than ⅓ of a channel's width"),
    ("OSSF / ATU", "on-site sewage facility (septic) / aerobic treatment unit"),
    ("Drip field", "buried drip lines that disperse treated effluent; area = flow ÷ 0.10 gal/sf/day on clay"),
    ("TCEQ Table III", "state table of septic design flow by bedrooms and heated area"),
    ("TPDES", "state permit to discharge treated wastewater (the White Rock plant's permit)"),
    ("Zone A / Zone X", "FEMA 1%-a-year flood zone without a base elevation / minimal flood risk"),
    ("CC&Rs / ACC", "recorded covenants / architectural control committee that approves building"),
    ("SF-3", "county single-family district: ½-acre lots, 35/15/10-ft set-backs, ≤40% coverage, 2½ storeys"),
    ("Option period", "paid days in a Texas contract when the buyer may cancel for any reason"),
    ("Resale certificate", "HOA statement of dues, assessments and violations for a lot being sold"),
    ("Circuit breaker", "Texas 20% yearly cap on taxable value of property under $5M; ends on sale"),
    ("CAD", "central appraisal district (Navarro CAD) that sets values for property tax"),
    ("GIS / lidar", "map data and laser elevation (USGS 2022); not a survey"),
    ("TWDB", "Texas Water Development Board: lake levels and the 2018 lake-bottom survey"),
    ("VE ×n", "vertical exaggeration: heights drawn n times larger than lengths"),
]

SOURCES = [
    "Navarro CAD property records 63254, 56587, 56586 and neighbours (2026 certified values)",
    "Rustling Oaks Estates Ph II Declaration of CC&Rs, Vol 1224 p 638 (1991); POA management certificate (2007); "
    "ACC handbook and fee schedule (2023–24); 2022 bylaws (rustlingoaksestates.org)",
    "TCEQ agreed order, Docket 2024-0591-MWD-E (White Rock HOA); TPDES permit WQ0014821002 renewal notice (2024)",
    "TRWD Residential Improvement Permit Guidelines (2026), OSSF Guidelines (2026), General Ordinance (2025), "
    "Richland-Chambers improvement guidelines (2001), permit fees (Feb 2026), contact page",
    "Navarro County Richland-Chambers Lakeshore Zoning Ordinance (rev. 2017) Table B; 2025 building permit package",
    "TWDB Water Data for Texas (daily level, 9 Nov 2026), TWDB 2018 volumetric survey, Water Service Boundary Viewer",
    "USGS 3DEP 1-m lidar (2022); FEMA NFHL; USDA NRCS SSURGO; Esri World Imagery (May 2025)",
    "LakeHouse.com listings 7100373 and 7885360 (MLS 21146775, 21298338); company listings for dock builders",
]
