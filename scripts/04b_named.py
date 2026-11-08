"""Targeted name searches (Esri World Geocoder) + OSRM routes for the
destinations the category search handles poorly: schools, hospitals, urgent
care, Indian/South Asian community anchors, boat ramps/marinas."""
import importlib.util, time
from common import get, haversine_mi, load, save
spec = importlib.util.spec_from_file_location('ctx', '04_context.py'); ctx = importlib.util.module_from_spec(spec); spec.loader.exec_module(ctx)
GEO = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
Q = {
 "schools_bayview": ["Mildred High School, Corsicana TX", "Mildred Elementary School, Corsicana TX", "Kerens School, Kerens TX"],
 "schools_arrowhead": ["Fairfield High School, Fairfield TX", "Fairfield Elementary School, Fairfield TX", "Fairfield Junior High School, Fairfield TX", "Fairfield Intermediate School, Fairfield TX"],
 "hospitals": ["Navarro Regional Hospital, 3201 W State Highway 22, Corsicana TX", "Freestone Medical Center, Fairfield TX", "Parkview Regional Hospital, Mexia TX", "Texas Health Presbyterian Hospital Kaufman, Kaufman TX", "Baylor Scott & White Medical Center Waxahachie, Waxahachie TX"],
 "urgent": ["Integrity Urgent Care, 2901 W 7th Ave, Corsicana TX", "Navarro Regional Hospital Emergency Room, Corsicana TX"],
 "indian": ["Patel Brothers, Irving TX", "India Bazaar, Irving TX", "Hindu Temple of Central Texas, Temple TX", "DFW Hindu Temple, Irving TX", "BAPS Shri Swaminarayan Mandir, Irving TX", "Islamic Center of Waco, Waco TX", "Waxahachie Indian restaurant", "Ennis Indian restaurant"],
 "lake": ["Oak Cove Marina, Corsicana TX", "Harbor Point Marina, Corsicana TX", "Fairfield Lake State Park", "Richland Chambers Lake Marina, Streetman TX", "Twin Creeks Marina, Streetman TX"],
}
P = load('parcels.json')
out = {}
for key, rec in P.items():
    lon, lat = rec['centroid']['lon'], rec['centroid']['lat']
    res = {}
    for grp, items in Q.items():
        if grp.startswith('schools_') and not grp.endswith(key):
            continue
        rows = []
        for text in items:
            d = get(GEO, params={"SingleLine": text, "maxLocations": 1, "outFields": "PlaceName,Place_addr,Type,Addr_type", "f": "json", "location": f"{lon},{lat}"})
            c = (d.get('candidates') or [None])[0]
            if not c:
                print(key, text, 'NOT FOUND'); continue
            a = c['attributes']; x, y = c['location']['x'], c['location']['y']
            mi, mins = ctx.route((lon, lat), (x, y))
            row = {"query": text, "name": a.get('PlaceName') or c['address'], "addr": a.get('Place_addr'), "type": a.get('Type'), "addr_type": a.get('Addr_type'), "score": c.get('score'), "lon": x, "lat": y, "crow_mi": round(haversine_mi((lon, lat), (x, y)), 1), "drive_mi": mi, "drive_min": mins}
            rows.append(row)
            print(f"{key:9s} {grp:16s} {row['name'][:45]:45s} | {str(row['addr'])[:50]:50s} | {row['addr_type']} {row['score']} | {mi} mi {mins} min")
            time.sleep(0.5)
        res[grp] = rows
    out[key] = res
save('services_named.json', out)
