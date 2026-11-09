# Richland-Chambers lakefront lots: due diligence (8 Nov 2026)

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

## Rebuild
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
