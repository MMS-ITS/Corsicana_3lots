"""Corrections list, 61-item due-diligence checklist and e-mail drafts for The Shores lots.

Status codes used in the checklist:  ok  = checked against an official record
                                     gis = measured from lidar/GIS (not a survey)
                                     con = still to confirm with the named party
                                     bad = problem found
"""
import re

from shores_data import HOA_DUES, LAKE_NOW, LOT, ORDER, RATE, facts

F = {k: facts(k) for k in LOT}
f2, f1, f4 = F["lot442"], F["lot411"], F["lot441"]


def m(v):
    return f"${v:,.0f}"


# --------------------------------------------------------------------------- corrections
# (topic, earlier report, verified now, source, effect)
CORRECTIONS = [
    ("CAD values", "Used 2026 land values as “value”: 442 $152,885, 411 $88,645, 441 $66,753; “county record not read”",
     "Same land values, read from navarrocad.com. Full 2026 market: 442 $155,239, 411 $89,720, 441 $70,834. "
     "Lot 442 is taxed on $142,802",
     "Navarro CAD records 64391, 64288, 64390",
     "Values are right, but they are not a fair yardstick (next row)"),
    ("CAD consistency", "Ranked 442 first partly on asking “0.62× CAD”",
     "In 2026 the CAD cut the land value of Phase VI canal lots 439, 441, 443 and 445 by 48–57% and 446–447 by 22%, "
     "but left 442 and 444 at 2025 levels. Lot 442 now carries $274k/ac against $119–126k/ac next door",
     "CAD roll history, 8 neighbours", "Price-vs-CAD flatters 442 and punishes 441; scored on asking $/canal-ft instead"),
    ("Property tax", "442 “est. $2,140” / $1,528; 411 $1,029; 441 $1,206",
     f"2026 adopted bills: 442 {m(LOT['lot442']['tax26'])}, 411 {m(LOT['lot411']['tax26'])}, 441 {m(LOT['lot441']['tax26'])} "
     f"at {RATE:.4f}% (County .35, College .1077, Flood .0054, R&B .0691, Mildred ISD 1.0408)",
     "texastaxtransparency.com (Navarro), 2026 adopted rates", "Listing figures are 2023–24 bills"),
    ("Tax after you buy", "Not covered",
     "Texas's 20% limit on non-homestead increases covers tax years 2024–2026 only and never passes to a buyer, so "
     "nothing caps a 2027 reset. 441 can go back toward its 2025 value ($150k → ≈$2,360/yr); 442 can be protested "
     "toward the price (≈$1,530/yr). 442 is taxed on $142,802 though the CAD lists $155,239 with no cap loss",
     "Tex. Tax Code §23.231; CAD and tax-portal records", "Holding cost is a range, not one figure"),
    ("HOA dues", "441/442 $1,255; 411 “$1,000 listed, $1,225–1,255 reported”",
     f"${HOA_DUES:,}/yr per lot on the MLS (442 and Lot 249). Transfer fee $200. The 411 figure looks out of date",
     "LakeHouse/MLS 20810887, HAR 21129188, HOA certificate 2022", "Ask PMI Alliance for a resale certificate"),
    ("Septic lot size", "“TRWD needs ≥1 ac if platted after 8 Apr 2011 … confirm”; county 1 ac on clay",
     "Phases V/VI were platted before July 2008. The developer sold these lots on 2 Jul and 16 Jul 2008, so the TRWD "
     "1-acre rule does not apply. TCEQ's ½-acre minimum is met. TRWD, not the county, permits septic here",
     "TRWD OSSF Guidelines 2026 §3.03(c); CAD deed history; TCEQ 30 TAC 285.4", "Half-acre septic is allowed: aerobic + drip"),
    ("Drip-field set-back", "75 ft from water (5-BR, 3,600 sf)",
     "TCEQ Table X: 25 ft when Ra<0.1, 75 ft when Ra>0.1, 50 ft with treatment + disinfection. Clay is exactly 0.1, so "
     "this report checks both 50 and 75 ft", "30 TAC 285.91(10)", "House size is limited by the drip field, not by zoning"),
    ("Canal depth", "“Lake max 75 ft, mean ≈27 ft; canal depth not surveyed”",
     f"TWDB boat survey (Dec 2018) did sound the canals: 442 {f2['depth_mean']}/{f2['depth_max']} ft, "
     f"441 {f4['depth_mean']}/{f4['depth_max']} ft, 411 {f1['depth_mean']}/{f1['depth_max']} ft (mean/max at 315 ft). "
     f"Today ({LAKE_NOW} ft) about 2.8 ft less", "TWDB 2018 volumetric survey soundings", "Boat lifts are marginal at 411"),
    ("Lot 411 water frontage", "“Canal-head waterfront”, dock ≤8 sf/ft of owned shoreline",
     "Plat: east line 95.78 ft runs on the “Revised 315 Deed Line” of a separate canal tract. Lidar puts that line at ≈321 ft. "
     "Open water starts 25–33 ft further out and touches only ≈35 ft opposite the lot", "Plat excerpt (listing photo 30); USGS lidar",
     "Dock 280–766 sf: TRWD must say which length counts"),
    ("Lot 411 wall", "Not mentioned", "CAD taxes a 100-ft steel wall, built 2010, at 20% condition. Its location is unknown",
     "CAD record 64288", "Inspect it; replacing it would cost $30–70k (estimate)"),
    ("Building permit fee", "“$0.50/sf”", "$0.25 per sf of HVAC area + three third-party inspections + $100 address application",
     "Navarro County 2025 building-permit package", "≈$1,250 for a 5,000 sf house"),
    ("Short-term rental", "“County has no STR permit … CC&Rs govern”",
     "HOA bans leases under 90 days and fines them (20th Supplement, Exhibit A5, approved 6 Jun 2026)",
     "POA of The Shores dedicatory instruments", "No Airbnb income"),
    ("HOA build rules", "Minimum 1,800–2,200 sf",
     "Also: 2- to 5-car garage with side/rear doors, 6/12 roof, engineer's foundation plan, exterior done within 9 months "
     "of the slab, approval lapses after 2 years, POA permit fee $2,750–$10,000 by size", "20th Supplement, Exhibits A1, A2, A4",
     "Large homes are expected and allowed"),
    ("Days on market", "442 ≈665 days; 411 ≈100; 441 “n/a, no history”",
     "442: 672 days (since ≥7 Jan 2025). 411: 116 days. 441: re-listed 9 Oct 2026 after a 2025 listing that was cut by $25k",
     "Homes.com (via earlier report), LakeHouse, Redfin snippet", "Room to negotiate on 442 and 441"),
    ("Lake level", "312.33 ft on 25 Oct 2026", f"{LAKE_NOW} ft on 9 Nov 2026 (2.8 ft below full pool)", "TWDB Water Data for Texas", "—"),
    ("Water supplier", "M.E.N. WSC (co-op)", "Confirmed: M.E.N. WSC, PWS TX1750015, for all three lots", "TWDB service-area map", "No well needed"),
    ("Sizes", "442 0.558 ac, 411 0.500 ac (GIS 0.489), 441 0.531 ac (GIS 0.539)",
     f"Legal acreage confirmed. GIS: 442 {f2['gis_sf']:,} sf, 411 {f1['gis_sf']:,} sf (−2%), 441 {f4['gis_sf']:,} sf (+1.6%)",
     "CAD + TxGIO parcels", "A survey settles 411's exact area"),
    ("Flood zones", "442 X; 411 X; 441 X 89% / A 11%", "Same, FIRM 48349C0625D (5 Jun 2012). No BFE is published",
     "FEMA NFHL", "Confirmed"),
]


# --------------------------------------------------------------------------- checklist
def ck(sec, item, a, b, c):
    return (sec, item, a, b, c)


CHECK = [
    ck("A. Identity & title", "Legal description & acreage",
       ("ok", "Ph VI Lot 442, 0.558 ac"), ("ok", "Ph V Lot 411, 0.500 ac"), ("ok", "Ph VI Lot 441, 0.531 ac")),
    ck("A. Identity & title", "CAD parcel & geographic ID",
       ("ok", "64391 · T0077-06-04420"), ("ok", "64288 · T0077-05-04110"), ("ok", "64390 · T0077-06-04410")),
    ck("A. Identity & title", "Owner & vesting deed",
       ("ok", "Guerrero/Rogas, 2021"), ("ok", "Randell, 2023"), ("ok", "Salas, 2008 (from developer)")),
    ck("A. Identity & title", "Title commitment: liens, easements, minerals",
       ("con", "order under contract"), ("con", "order under contract"), ("con", "order under contract")),
    ck("A. Identity & title", "Recorded plat & dedications",
       ("con", "Ph VI Vol 7 pp 395–396"), ("ok", "Ph V Vol 7 p 397 (excerpt seen)"), ("con", "Ph VI Vol 7 pp 395–396")),
    ck("B. Boundary & survey", "GIS area vs legal",
       ("gis", f"{f2['gis_sf']:,} vs 24,306 sf"), ("gis", f"{f1['gis_sf']:,} vs 21,780 sf (−2%)"), ("gis", f"{f4['gis_sf']:,} vs 23,130 sf")),
    ck("B. Boundary & survey", "Frontages (road / water)",
       ("gis", f"{f2['road_ft']:.0f} / {f2['lake_ft']:.0f} ft"), ("bad", "102 / 95.8 ft on canal tract, ≈35 ft open water"),
       ("gis", f"{f4['road_ft']:.0f} / {f4['lake_ft']:.0f} ft")),
    ck("B. Boundary & survey", "Corner coordinates", ("gis", "6 corners in report"), ("gis", "4 corners in report"), ("gis", "5 corners in report")),
    ck("B. Boundary & survey", "Boundary + topo survey (315/320 lines, trees, wall)",
       ("con", "order"), ("con", "order — critical"), ("con", "order")),
    ck("B. Boundary & survey", "Encroachments / wall on the line",
       ("con", "wall 60 ft on canal line"), ("bad", "100-ft wall, 2010, 20% — location?"), ("con", "wall 104 ft on canal line")),
    ck("C. Price & market", "Asking price, history, days on market",
       ("ok", "$94,900; −$30k since Jan 2025; 672 d"), ("ok", "$65,000; 116 d"), ("ok", "$105,000; re-listed; 32 d")),
    ck("C. Price & market", "CAD 2026 & 5-year history",
       ("ok", "$155,239 (2022 $68k)"), ("ok", "$89,720 (2022 $44k)"), ("ok", "$70,834 (2025 $150k)")),
    ck("C. Price & market", "Active comparable asking prices",
       ("ok", "interior $60–75k; canal $65–189k"), ("ok", "same"), ("ok", "same")),
    ck("C. Price & market", "Sold comps (MLS; Texas does not disclose)",
       ("con", "ask agent"), ("con", "ask agent"), ("con", "ask agent")),
    ck("D. Tax & holding cost", "2026 adopted tax bill",
       ("ok", m(LOT['lot442']['tax26'])), ("ok", m(LOT['lot411']['tax26'])), ("ok", m(LOT['lot441']['tax26']))),
    ck("D. Tax & holding cost", "Exemptions / caps after purchase",
       ("con", "taxed on $142,802 vs $155,239: ask CAD; protest toward price"), ("ok", "none"),
       ("bad", "no cap from 2027; may return to ≈$150k")),
    ck("D. Tax & holding cost", "HOA dues, transfer & resale certificate",
       ("con", "$1,255 + $200 + cert"), ("con", "$1,255? listing said $1,000"), ("con", "$1,255 + $200 + cert")),
    ck("D. Tax & holding cost", "Annual holding cost (tax+HOA+mow+ins.)",
       ("gis", f"{m(f2['hold']['after_lo'])}–{m(f2['hold']['after_hi'])}"), ("gis", f"{m(f1['hold']['after_lo'])}–{m(f1['hold']['after_hi'])}"),
       ("gis", f"{m(f4['hold']['after_lo'])}–{m(f4['hold']['after_hi'])}")),
    ck("D. Tax & holding cost", "Special assessments / unpaid dues on the lot",
       ("con", "resale certificate"), ("con", "resale certificate"), ("con", "resale certificate")),
    ck("E. Zoning & HOA", "County zoning district", ("con", "likely SF-3"), ("con", "likely SF-3"), ("con", "likely SF-3")),
    ck("E. Zoning & HOA", "Set-backs, coverage, height (SF-3)",
       ("ok", "35/15/10 ft, 40%, 2½ storeys"), ("ok", "same"), ("ok", "same")),
    ck("E. Zoning & HOA", "HOA minimum size, garage, roof, materials",
       ("ok", "1,800–2,200 sf min; 2–5 car; 6/12"), ("ok", "same"), ("ok", "same")),
    ck("E. Zoning & HOA", "Build timing (start / finish)", ("ok", "no start deadline; exterior in 9 months"), ("ok", "same"), ("ok", "same")),
    ck("E. Zoning & HOA", "Rentals, RVs, boats, guest house",
       ("ok", "lease ≥90 days; RV 7 days; guest house allowed"), ("ok", "same"), ("ok", "same")),
    ck("F. Terrain", "Ground range & relief",
       ("gis", f"{f2['zmin']:.1f}–{f2['zmax']:.1f} ft"), ("gis", f"{f1['zmin']:.1f}–{f1['zmax']:.1f} ft"), ("gis", f"{f4['zmin']:.1f}–{f4['zmax']:.1f} ft")),
    ck("F. Terrain", "Slope (mean / max over 50 ft)", ("gis", "6.8% / 19.0°"), ("gis", "7.4% / 13.3°"), ("gis", "9.2% / 18.3°")),
    ck("F. Terrain", "Road→water section & bank", ("gis", "231 ft, 16 ft, bank 23°"), ("gis", "235 ft, 21 ft, bank 24°"), ("gis", "226 ft, 14 ft, bank 22°")),
    ck("F. Terrain", "Drainage & culvert", ("gis", "W to canal; culvert req."), ("gis", "E to canal; culvert req."), ("gis", "WNW; culvert req.")),
    ck("G. Flood", "FEMA zone & panel", ("ok", "X · 48349C0625D"), ("ok", "X · 48349C0625D"), ("ok", "X + 11% A")),
    ck("G. Flood", "BFE & minimum floor", ("gis", "no BFE; floor ≥325.6 ft; pad ≈330"), ("gis", "no BFE; ≥320 ft; pad ≈335"), ("gis", "no BFE; ≥326 ft; pad ≈329")),
    ck("G. Flood", "Land below 320 ft (TRWD flowage)", ("gis", "570 sf"), ("gis", "none"), ("gis", "1,141 sf")),
    ck("G. Flood", "Flood insurance / elevation certificate",
       ("ok", "not required (X)"), ("ok", "not required (X)"), ("con", "house in X; EC optional")),
    ck("H. Soil & foundation", "Soil series & shrink-swell", ("ok", "Crockett CrB, LEP 9% at 8–25 in"), ("ok", "same"), ("ok", "same")),
    ck("H. Soil & foundation", "Geotechnical report (PVR)", ("con", "order"), ("con", "order"), ("con", "order")),
    ck("H. Soil & foundation", "Foundation type", ("gis", "engineered PT slab / piers"), ("gis", "same"), ("gis", "same")),
    ck("H. Soil & foundation", "Pad grading for the house", ("gis", "1.7 ft fall; ≈16 cy cut/fill"), ("gis", "1.7 ft; ≈37 cy fill"),
       ("gis", "2.1 ft; ≈23 cy cut")),
    ck("I. Septic", "Sewer available?", ("bad", "no"), ("bad", "no"), ("bad", "no")),
    ck("I. Septic", "Authority & system type", ("ok", "TRWD; aerobic + drip; no spray"), ("ok", "same"), ("ok", "same")),
    ck("I. Septic", "Lot-size rule", ("ok", "pre-2011 plat; >½ ac"), ("con", "0.500 ac legal, 0.487 GIS"), ("ok", "pre-2011 plat; >½ ac")),
    ck("I. Septic", "Drip room & bedrooms (largest house)",
       ("gis", f"{f2['max50']['drip_avail_sf']:,} sf → 6 BR, {f2['max50']['heated_2st_sf']:,} sf"),
       ("gis", f"{f1['max50']['drip_avail_sf']:,} sf → 6 BR, {f1['max50']['heated_2st_sf']:,} sf"),
       ("gis", f"{f4['max50']['drip_avail_sf']:,} sf → 6 BR, {f4['max50']['heated_2st_sf']:,} sf")),
    ck("I. Septic", "Site evaluation & design", ("con", "order"), ("con", "order"), ("con", "order")),
    ck("J. Utilities", "Water supplier", ("ok", "M.E.N. WSC TX1750015"), ("ok", "same"), ("ok", "same")),
    ck("J. Utilities", "Water tap availability & fee", ("con", "ask WSC"), ("con", "ask WSC"), ("con", "ask WSC")),
    ck("J. Utilities", "Electric", ("con", "underground at road; NCEC?"), ("con", "same"), ("con", "same")),
    ck("J. Utilities", "Internet & gas", ("con", "fixed wireless/Starlink; propane"), ("con", "same"), ("con", "same")),
    ck("K. Lake & dock", "Shoreline length for TRWD", ("gis", "60 ft"), ("bad", "35–96 ft, TRWD decides"), ("gis", "105 ft")),
    ck("K. Lake & dock", "Largest dock / boathouse", ("gis", "480 sf"), ("bad", "280–766 sf"), ("gis", "839 sf")),
    ck("K. Lake & dock", "Canal width at 315 ft", ("gis", f"≈{f2['canal_w']:.0f} ft"), ("gis", f"≈{f1['canal_w']:.0f} ft, silted head"), ("gis", f"≈{f4['canal_w']:.0f} ft")),
    ck("K. Lake & dock", "Depth full pool / today",
       ("ok", f"{f2['depth_mean']}/{f2['depth_max']} → {f2['now_mean']}/{f2['now_max']} ft"),
       ("bad", f"{f1['depth_mean']}/{f1['depth_max']} → {f1['now_mean']}/{f1['now_max']} ft"),
       ("ok", f"{f4['depth_mean']}/{f4['depth_max']} → {f4['now_mean']}/{f4['now_max']} ft")),
    ck("K. Lake & dock", "Wall permits & condition", ("con", "2021 wall; TRWD file?"), ("bad", "2010 wall, 20%"), ("con", "2021 wall; TRWD file?")),
    ck("L. Environment", "Trees & clearing rules", ("ok", "wooded; ≥10 in trees need plan"), ("ok", "mixed"), ("ok", "wooded")),
    ck("L. Environment", "Wet / vegetated areas", ("ok", "none on lot"), ("bad", "vegetated canal head"), ("ok", "shore strip")),
    ck("L. Environment", "Natural hazards", ("ok", "tornado, hail, wind, heat"), ("ok", "same"), ("ok", "same")),
    ck("L. Environment", "Easements & pipelines", ("ok", "20-ft POA road easement"), ("ok", "same"), ("ok", "same")),
    ck("M. Location & exit", "Drive times", ("gis", "Dallas 85 min; Corsicana 28"), ("gis", "same"), ("gis", "same")),
    ck("M. Location & exit", "Hospital & fire", ("gis", "Navarro Regional 33 min; VFD 1.2 mi"), ("gis", "same"), ("gis", "same")),
    ck("M. Location & exit", "Schools", ("ok", "Mildred ISD"), ("ok", "Mildred ISD"), ("ok", "Mildred ISD")),
    ck("M. Location & exit", "Gate, roads, amenities", ("ok", "gated; pool, gym, ramp, marina"), ("ok", "same"), ("ok", "same")),
    ck("M. Location & exit", "Resale ceiling for a big house", ("bad", "largest listed home 4,252 sf"), ("bad", "same"), ("bad", "same")),
    ck("M. Location & exit", "Insurance quote (wind/hail)", ("con", "get quote"), ("con", "get quote"), ("con", "get quote")),
    ck("M. Location & exit", "Lake level record", ("ok", "26.6% of days <312 ft since 2000"), ("ok", "same"), ("ok", "same")),
]
assert len(CHECK) == 61, len(CHECK)
SRC = {"lot442": 2, "lot411": 3, "lot441": 4}     # tuple position of each lot in a CHECK row


def check_cells(row, order=ORDER):
    """Cells of one checklist row in report (rank) order. "same" in the source means "same as the column to
    its left" (442 → 411 → 441); it is resolved, then shown as "same" only where it equals the new left cell."""
    res, prev = {}, None
    for k in ("lot442", "lot411", "lot441"):
        code, txt = row[SRC[k]]
        txt = prev if (txt == "same" and prev is not None) else txt
        res[k] = (code, txt); prev = txt
    out, left = [], None
    for k in order:
        code, txt = res[k]
        out.append((code, "same" if (left is not None and txt == left) else txt)); left = txt
    return out


# --------------------------------------------------------------------------- e-mails
SIGN = "[Your name]\n[Phone] · [E-mail]"
LOTLINE = {k: f"{LOT[k]['name']}, Corsicana TX 75109 — {LOT[k]['legal']} — CAD {LOT[k]['cad_id']} — MLS {LOT[k]['mls']}"
           for k in LOT}

EMAILS = []


# a line that starts a new paragraph item; every other non-blank line continues the line above it
_NEW = re.compile(r"^\s*(\d+\.\s|-\s|\[|Hello|Thank you|Lot:|Questions:|Scope:|Water \(|Electric \()")


def unwrap(body):
    """Join the hard-wrapped source lines so each paragraph or numbered item is one line (mail clients and the
    PDF re-wrap it to their own width)."""
    out = []
    for ln in body.split("\n"):
        if not ln.strip():
            out.append("")
        elif out and out[-1] != "" and not _NEW.match(ln):
            out[-1] = out[-1].rstrip() + " " + ln.strip()
        else:
            out.append(ln.rstrip())
    return "\n".join(out)


def mail(group, to, subject, body):
    EMAILS.append(dict(group=group, to=to, subject=subject, body=unwrap(body.strip())))


for k in ["lot442", "lot411", "lot441"]:
    d = LOT[k]
    extra = {
        "lot442": ("6. The lot has 60 ft of canal frontage. Has TRWD issued a permit for the 60-ft steel wall, and is there "
                   "a copy?\n7. The 2026 CAD value ($155,239) is about twice the value of Lots 441 and 443. Did the owner "
                   "protest in 2026? What is the reason for the $142,802 taxable value?"),
        "lot411": ("6. The plat shows the east line (95.78 ft) on the “Revised 315 Deed Line” of the canal tract. Who owns the "
                   "canal tract (TRWD, the POA, or the developer)? Has the seller confirmed with TRWD how many feet of "
                   "shoreline the lot gets for a dock?\n7. The CAD lists a 100-ft steel wall built in 2010 at 20% condition. "
                   "Where is it, and is it on the lot? Any TRWD permit?\n8. How deep is the canal head at the lot today? "
                   "Has anyone asked about dredging?"),
        "lot441": ("6. The lot was listed in 2025 and cut by $25,000. What were the earlier list prices and dates?\n7. The "
                   "2026 CAD value fell from $150,240 to $70,834. Did the owner protest? Please share the notice.\n"
                   "8. Has TRWD issued a permit for the 104-ft steel wall?"),
    }[k]
    mail(f"{d['short']} — listing agent", f"{d['agent']} · {d['agent_tel']}",
         f"Questions before an offer — {d['name']} (MLS {d['mls']})",
         f"""
Hello,

I am interested in {d['name']} in The Shores and plan to build a large home and a private dock. Before I make an offer,
could you help with the following?

1. Seller's disclosure, any existing survey, and the recorded plat page for the lot.
2. Sold prices for canal-front lots in The Shores over the last 24 months (MLS sold data).
3. Current HOA dues and any special assessment or unpaid balance on the lot.
4. Any offers or contracts that fell through, and how flexible the seller is on price and on an option period of
   21 days.
5. Any soil, septic, or perc test, tree survey, or builder quote the seller has.
{extra}

Lot: {LOTLINE[k]}

Thank you,
{SIGN}
""")

mail("HOA — P.O.A. of The Shores (PMI Alliance)", "support@pmialliance.com; cc mindy@pmialliance.com · (214) 295-9661",
     "Prospective buyer: rules and fees for Lots 411, 441, 442",
     f"""
Hello Ms. Love,

I am a prospective buyer for three vacant lots in The Shores:
  - {LOTLINE['lot442']}
  - {LOTLINE['lot411']}
  - {LOTLINE['lot441']}

I want to build as large a home as the rules allow, plus a private dock or boathouse. Could you or the ACC confirm:

1. 2026 and expected 2027 annual dues for each lot. Are there special assessments, unpaid balances or open
   violations on any of the three?
2. The fee for a resale certificate (Property Code §207.003) and the transfer fee.
3. The full CC&Rs and the supplemental declarations for Phase V (Doc 00002544) and Phase VI (Doc 00002700),
   especially building set-backs, maximum height, minimum and maximum house size, materials, and fences.
4. ACC rules for boathouses, piers, boat lifts and walls on the canals, and the order of approvals (ACC before TRWD).
5. Whether the canal next to Lot 411 is POA common area or TRWD land, and whether the POA has dredged canals.
6. The 2026 cost of the voluntary mowing program for an unimproved lot.
7. Marina slip availability and price, and the waiting list.

Thank you,
{SIGN}
""")

mail("TRWD — Richland-Chambers permits (dock & septic)", "TRWD Richland-Chambers office · (903) 389-3928 (ask for the permit e-mail)",
     "Pre-application questions: dock size and septic for three lots in The Shores",
     f"""
Hello,

I am considering buying one of these lots in The Shores (Navarro County) and would like to understand what TRWD would
permit before I commit:
  - {LOTLINE['lot442']} — about 60 ft of canal frontage, steel wall
  - {LOTLINE['lot441']} — about 105 ft of canal frontage, steel wall
  - {LOTLINE['lot411']} — east line 95.78 ft on the “Revised 315 Deed Line” of the canal tract; open water is
    25–33 ft beyond the line

Questions:
1. Shoreline length used for the Attachment I size limit (8 sq ft per foot up to 150 ft) for each lot. For Lot 411,
   does the 95.78-ft line count, or only the length that touches water?
2. Is there a limit on how far a dock can extend into a canal about 90–115 ft wide?
3. Does TRWD have permits on file for the existing steel walls (60 ft at 442, 104 ft at 441, 100 ft at 411)?
4. Can the canal head at Lot 411 be dredged, and what permit and depth limits apply?
5. Septic: these Phase V/VI lots were platted before April 2011. Please confirm that §3.03(c) of the 2026 OSSF
   Guidelines (1-acre minimum) does not apply, and that an aerobic unit with subsurface drip is acceptable. Which
   set-back from the 315-ft line do you apply to drip fields on clay (Ra 0.1)?
6. Typical review time for a residential OSSF permit and a dock permit.

Thank you,
{SIGN}
""")

mail("Navarro County Planning & Development", "601 N. 13th St., Suite 1, Corsicana TX 75110 · (903) 875-3311 / 875-3312",
     "Zoning district and permit questions — The Shores Phase V and VI",
     f"""
Hello,

I am evaluating three vacant lots in The Shores on Richland Chambers Lake (inside the 5,000-ft lakeshore zoning area):
Lots 442 and 441 (Phase VI, CAD 64391 and 64390) and Lot 411 (Phase V, CAD 64288).

Could you confirm in writing:
1. The zoning district for these lots (SF-3 or another district or PD), and the front, rear and side set-backs,
   maximum building coverage and maximum height that apply.
2. For a lot on a canal, which line counts as the “rear” line, and how the 50% rear-half coverage rule is measured.
3. Whether a guest house or accessory dwelling of up to 40% of the main house is allowed.
4. Whether any floodplain development permit is needed for Lot 441, which has a Zone A strip along the canal.
5. The current residential permit fee ($0.25 per sq ft of HVAC area?) and the inspection requirements.
6. How 911 addresses are issued for The Shores (county or City of Corsicana).

Thank you,
{SIGN}
""")

mail("Utilities — M.E.N. WSC and Navarro County Electric Co-op",
     "M.E.N. WSC, 8542 S US Hwy 287, Corsicana · (903) 872-1899   |   NCEC · (903) 874-7411",
     "Service availability for a new home in The Shores",
     f"""
Hello,

I may build a large (5–6 bedroom) home on one of these lots in The Shores: Lot 442 or 441 Waters Edge Dr (Phase VI)
or Lot 411 Sailboat Dr (Phase V), Corsicana 75109.

Water (M.E.N. WSC): Is a ¾-in or 1-in meter available at each lot? What are the membership, tap and impact fees and the
lead time? Is there any moratorium?
Electric (NCEC): Is underground service at the road for each lot? What is the cost of a 400-amp service and any line
extension?

Thank you,
{SIGN}
""")

mail("Surveyor — request for quote", "e.g. Jimmy W. Pogue Inc. Land Surveyors (serves Navarro) · Andress Surveying · other RPLS",
     "Quote: boundary + topographic survey of a canal lot in The Shores",
     f"""
Hello,

Please quote a boundary and topographic survey for one lot (I will confirm which one) in The Shores on Richland
Chambers Lake, Navarro County:
  - {LOTLINE['lot441']}
  - {LOTLINE['lot442']}
  - {LOTLINE['lot411']}

Scope:
1. Boundary with corners set or found, the recorded plat lines, and easements (20-ft POA road easement).
2. 1-ft contours with the 315-ft and 320-ft lines (NAVD88), top and toe of bank, and the steel wall.
3. Trees of 10 in and larger in the building area.
4. For Lot 411: where the lot line sits relative to the canal tract and open water.
5. Optional: elevation certificate (Lot 441), and canal depth soundings at the dock location.

Please include price, turnaround, and a sample drawing.

Thank you,
{SIGN}
""")

mail("Septic designer / site evaluator — request for quote", "TRWD-experienced OSSF designer (ask TRWD (903) 389-3928 for local names)",
     "Quote: site evaluation and aerobic + drip design for a large home",
     f"""
Hello,

I am evaluating a half-acre canal lot in The Shores (Lot 441 or 442 Waters Edge Dr, or Lot 411 Sailboat Dr). TRWD
permits septic here. I want the largest home the lot can serve, about 5,000–6,500 sq ft heated with 6 bedrooms.

Please quote:
1. Soil profile holes and a site evaluation, including the soil class within 1 ft of the emitters.
2. A preliminary layout for an aerobic unit + subsurface drip, showing the 315-ft set-back you would use, and the drip
   area for 420, 480 and 540 gal/day.
3. The installed cost range for such a system.

Thank you,
{SIGN}
""")

mail("Geotechnical engineer — request for quote", "Licensed geotechnical firm (Corsicana / Waxahachie / Dallas)",
     "Quote: geotechnical report for a two-storey home on Crockett clay",
     f"""
Hello,

Please quote a residential geotechnical investigation for a two-storey home (≈5,000–6,500 sq ft) on a canal lot in The
Shores, Navarro County. NRCS maps Crockett fine sandy loam over clay with high shrink-swell (LEP ≈9%).

Scope: two borings to 20–25 ft, PVR, and slab-on-grade or pier-and-beam design parameters. Please also comment on the
canal bank (≈23° over the last 20 ft) if a pool is planned on the lake side.

Thank you,
{SIGN}
""")

mail("Navarro CAD — value questions", "Navarro Central Appraisal District, 1250 N. 45th St., Corsicana · (903) 872-6161 · general.info@navarrocad.com",
     "Questions about 2026 values for parcels 64391, 64390 and 64288",
     f"""
Hello,

I am a prospective buyer and would like to understand the 2026 values for these parcels in The Shores:
1. Parcel 64391 (Lot 442): the CAD shows a market and appraised value of $155,239 with no cap loss or exemption, but
   the tax portal shows a taxable value of $142,802 for every unit. What causes the difference?
2. Parcels 64390 (Lot 441), 64392 (443) and 64394 (445) fell by about 55% from 2025 to 2026, while 64391 (442) and 64393
   (444) did not. Were the reductions protest settlements, or a change to the neighbourhood schedule?
3. How will the 2027 value be set after a sale, now that the §23.231 20% limit covers only 2024–2026 and does not pass
   to a new owner?

Thank you,
{SIGN}
""")

mail("Title company — preliminary title", "e.g. Navarro County Abstract Co. · Micro Title Navarro County · Royal Title (Corsicana)",
     "Preliminary title report for a vacant lot in The Shores",
     f"""
Hello,

Before contracting, I would like a preliminary title report or a quote for one of these lots: {LOT['lot441']['name']}
(CAD 64390), {LOT['lot442']['name']} (CAD 64391) or {LOT['lot411']['name']} (CAD 64288), The Shores on Richland Chambers
Lake, Corsicana.

Please list recorded easements, TRWD flowage easements (320 ft), mineral reservations, the HOA declarations that apply,
and any liens. For Lot 411, please also note who owns the adjoining canal tract.

Thank you,
{SIGN}
""")
