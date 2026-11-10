# Richland-Chambers lakefront lots: due diligence

## 11 Bayview Cir and 5001 Arrowhead Pt: largest home, private dock, first steps (10 Nov 2026)

**Report:** [`Bayview-Arrowhead-BigHome-Dock-DD-and-Emails_10-Nov-26_Claude-Opus-5.5.pdf`](Bayview-Arrowhead-BigHome-Dock-DD-and-Emails_10-Nov-26_Claude-Opus-5.5.pdf), 8 letter-size pages: summary, one feasibility page per lot, first steps and costs, 14 e-mail drafts, glossary and end note.
Markdown copies: [`docs/twolots/PLAN.md`](docs/twolots/PLAN.md), [`docs/twolots/EMAILS.md`](docs/twolots/EMAILS.md).

| | A · 11 Bayview Cir (White Rock) | B · 5001 Arrowhead Pt (Rustling Oaks) |
|---|---|---|
| Largest house (test fit) | 116×52 ft footprint, ≈9,400 sf heated on 2 storeys | 112×56 ft, ≈8,900–9,900 sf heated |
| What limits it | set-backs on a wedge-shaped lot + Zone A (HOA sewer, no septic) | the septic drip field (600 gal/day → 6,000 sf) |
| Largest dock (TRWD) | 1,200 sf; fits 56×21 ft in a basin ≈98 ft across | 918 sf; fits 45×20 ft after a 10-ft walkway |
| Depth over the lift | not surveyed: sound it before buying | 6.1 ft at full pool, 3.2 ft today (TWDB 2018) |
| Spend before committing | ≈$2.2–4.4k | ≈$3.0–5.9k (adds the septic evaluation) |

Main findings:
- White Rock's sewer plant (TCEQ permit for 8,000 gal/day) broke its effluent limits in 2023–24. The TCEQ agreed order deferred most of the penalty for inability to pay. Ask the HOA about assessments and spare capacity.
- Rustling Oaks Ph II CC&Rs (1991): $12/month dues, 1,600 sf minimum, no owner wells, and outside walls and roof finished within 120 days of starting.
- The 1990 Phase II plat means TRWD's 1-acre septic rule does not apply to Lot 33.
- Two neighbours of Lot 11 built 977- and 1,024-sf boathouses on the same basin in 2023.

Rebuild (two-lot set, the default `LOTSET`):
```bash
cd scripts && export MPLCONFIGDIR=/tmp/mpl
python 15_twolots_bigbuild.py        # largest house + dock search, about 3 min -> data/bigbuild.json, figures/bigbuild_*, dockxs_*
python 16_twolots_report.py 100      # the PDF, docs/twolots/*.md and out/twolots/preview/
```
`python 15_twolots_bigbuild.py dock` re-runs only the dock search; `fig` only redraws.

## The Shores lots 442, 411, 441: revised due diligence (10 Nov 2026)

**Report:** [`The-Shores-3-Lots-Revised-Due-Diligence_10-Nov-26_Claude-Opus-5.5.pdf`](The-Shores-3-Lots-Revised-Due-Diligence_10-Nov-26_Claude-Opus-5.5.pdf), 10 letter-size pages.
**Companion:** [`The-Shores-3-Lots-Checklists-and-Emails_10-Nov-26_Claude-Opus-5.5.pdf`](The-Shores-3-Lots-Checklists-and-Emails_10-Nov-26_Claude-Opus-5.5.pdf), 5 pages: the 61-item checklist for each lot and 12 e-mail drafts.
Markdown copies: [`docs/shores3/CORRECTIONS.md`](docs/shores3/CORRECTIONS.md), [`CHECKLIST.md`](docs/shores3/CHECKLIST.md), [`EMAILS.md`](docs/shores3/EMAILS.md).

This re-checks the earlier upload `3 Corsicana lakefront lots Comparison .pdf` against the records.

| Rank | Lot | Asking | CAD 2026 | 2026 tax | Holding cost/yr | Water frontage | Largest dock | Largest home (heated) | Score (earlier) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 441 Waters Edge Dr (Ph VI) | $105,000 | $70,834 | $1,114 | $2.7–4.3k | 105 ft | 839 sf | 8,880–9,840 sf | **7.2** (5.9) |
| 2 | 442 Waters Edge Dr (Ph VI) | $94,900 | $155,239 | $2,246 | $3.1–4.4k | 60 ft | 480 sf | 10,672 sf | **6.6** (7.2) |
| 3 | 411 Sailboat Dr (Ph V) | $65,000 | $89,720 | $1,411 | $2.6–3.3k | 35–96 ft, TRWD decides | 280–766 sf | 8,496–8,624 sf | **6.0** (6.8) |

Main findings:
- The ranking flips. The earlier order leaned on CAD values that the CAD applies unevenly: in 2026 it cut six of eight Phase VI canal lots by 22–57% but left 442 and 444 alone.
- The 2026 tax bills (1.5730%) are $2,246 (442), $1,411 (411) and $1,114 (441). The listing figures were 2023–24 bills.
- The septic drip field, not zoning, limits the house: about 8,500–10,700 sf heated in theory, 5,000–6,500 sf in practice. TRWD's 1-acre septic rule does not apply (the plats are from 2008).
- TRWD allows 8 sf of dock per foot of shoreline. Lot 411 ends at the canal tract's 315-ft deed line, 25–33 ft short of open water, so its dock size is TRWD's call.
- The canals are 5.5–7.6 ft deep at full pool and about 2.8 ft shallower today (312.16 ft on 9 Nov 2026).

Rebuild (same setup as below):
```bash
cd scripts && export LOTSET=shores3 MPLCONFIGDIR=/tmp/mpl
python 01_parcels.py && python 02_dem.py && python 03_imagery.py && python 04_context.py && python 04b_named.py
python 05_flood.py && python 06_soil.py && python 07_area.py && python 08_terrain.py && python 10_bathymetry.py && python 11_boundaries.py
python 14_maxbuild.py           # largest house + dock search, about 3 min -> data/shores3/maxbuild.json
python 09_figures.py            # figures/shores3/ (the fly-arounds are slow)
python 13_shores_report.py 100  # both PDFs, docs/shores3/*.md and out/shores3/preview/
```
`LOTSET` defaults to `two`, which rebuilds the 8 Nov report below unchanged. `data/shores3/canal.json` holds canal widths measured once from the 2022 lidar. `climate.json` and `census.json` are copies of the two-lot files (same area). Only the six listing photos the report uses are committed.

## Two lots: 11 Bayview Cir and 5001 Arrowhead Pt (8 Nov 2026)

**Report:** [`Richland-Chambers-2-Lots-Due-Diligence_08-Nov-26_Claude-Opus-5.5.pdf`](Richland-Chambers-2-Lots-Due-Diligence_08-Nov-26_Claude-Opus-5.5.pdf), 6 letter-size pages.

| Lot | Asking | Size | Lake frontage | Ground (ft msl) | Hold score |
|---|---|---|---|---|---|
| A · 11 Bayview Cir, Corsicana, TX 75109 (White Rock) | $89,900 (MLS 21146775) | 0.65 ac | 158 ft | 313.0–333.6 | **7.2 / 10** |
| B · 5001 Arrowhead Pt, Streetman, TX 75859 (Rustling Oaks) | $99,900 (MLS 21298338) | 0.50 ac | 115 ft | 319.5–330.2 | **6.3 / 10** |

Pages:
1. Summary of both lots, with a Texas/area map, score cards and a side-by-side table.
2. Lot A facts: listing, plat and corners, terrain, lake, flood, soil, sewer/septic, well, utilities, HOA and zoning, location, 5-BR build cost, score.
3. Lot A pictures (≥3.8 in wide): fly-around views, contour plan, 3-D terrain, true 1:1 and exaggerated sections, building envelope, FEMA map, lake-bottom contours, listing drone photo.
4. Lot B facts (same layout as page 2).
5. Lot B pictures (same layout as page 3).
6. Construction feasibility, score reasons, gardening, documents to obtain, glossary, sources, limits, end note.

Main findings:
- Both lots fit a 5-bedroom house and garage. Neither needs fill for flooding.
- Lot A has HOA sewer. Lot B needs an aerobic septic unit with a drip field; the soil and area allow 5–6 bedrooms.
- Both lots sit on expansive clay, so plan for an engineered foundation.
- Both coves are 7–10 ft deep at full pool.
- Lot A's HOA dues are $3,530/yr (sewer included). Lot B's POA fee is $144/yr in the handbook but $644/yr in the MLS flyer.

## Limits
This is a desk study, with no site visit. It is not a survey, appraisal, or flood or septic determination. Zillow, Redfin, HAR and realtor.com block automated access, so:
- The realtor.com "Fly Around" views are replaced by fly-around renders made from USGS 1 m lidar draped with Esri imagery.
- Listing photos come from LakeHouse.com (the same MLS photos).
- Items marked CONFIRM in the PDF need a surveyor, engineer, the county or the HOA.

## Setup and rebuild (two-lot report)
```bash
python -m venv .venv && .venv/bin/pip install requests numpy scipy matplotlib pillow rasterio shapely pyproj pyshp playwright pymupdf
PLAYWRIGHT_BROWSERS_PATH=.pw-browsers .venv/bin/playwright install chromium
cd scripts
python 01_parcels.py && python 02_dem.py && python 03_imagery.py && python 04_context.py && python 04b_named.py
python 05_flood.py && python 06_soil.py && python 07_area.py && python 08_terrain.py && python 10_bathymetry.py && python 11_boundaries.py
MPLCONFIGDIR=/tmp/mpl python 09_figures.py
python 12_report.py 110        # writes the PDF to the repo root and page previews to out/preview/
```
`10_bathymetry.py` needs the TWDB Richland-Chambers 2018 survey shapefiles (≈850 MB) unzipped into `TWDB_DIR`. The large raw downloads (`data/flood.json`, `data/bathymetry.json`, `data/parcels.json`, `data/stratmap_raw_*.json`) are not committed; the scripts fetch them again.
