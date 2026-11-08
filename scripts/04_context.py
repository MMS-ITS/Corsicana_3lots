"""Location context for each lot.

  * local OSM features (roads, water, gates) in a ~1.3 km window  -> maps
  * nearest services by category: Esri World Geocoder POI search (category +
    location bias), then OSRM driving distance/time over OpenStreetMap roads
  * named regional destinations (cities, airports, major hospitals, Indian
    groceries / temples / mosques found by name search), routed the same way

Outputs data/osm_local.json and data/services.json
"""
import time

from common import OSM, get, haversine_mi, load, save

OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]
GEOCODE = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
OSRM = "https://router.project-osrm.org/route/v1/driving/{a};{b}?overview=false"

# Esri POI categories -> label used in the report
CATEGORIES = [
    ("Hospital", "hospital"), ("Medical Clinic", "clinic"), ("Pharmacy", "pharmacy"),
    ("Grocery", "grocery"), ("Department Store", "department_store"),
    ("Convenience Store", "convenience"), ("Gas Station", "gas"), ("Bank", "bank"),
    ("Restaurant", "restaurant"), ("Coffee Shop", "cafe"), ("Bar or Pub", "bar"),
    ("Movie Theater", "cinema"), ("Home Improvement Store", "home_improvement"),
    ("Hardware Store", "hardware"), ("Fire Station", "fire_station"),
    ("Police Station", "police"), ("Post Office", "post_office"), ("Marina", "marina"),
    ("Elementary School", "elementary"), ("Middle School", "middle"), ("High School", "high"),
    ("Indian Food", "indian_restaurant"), ("Hindu Temple", "hindu_temple"), ("Mosque", "mosque"),
]
# Name searches (Esri SingleLine) for things the category taxonomy misses.
NAME_SEARCHES = [
    ("indian_grocery", "Patel Brothers"), ("indian_grocery", "India Bazaar"),
    ("indian_grocery", "Indian grocery"), ("walmart", "Walmart Supercenter"),
    ("heb", "H-E-B"), ("lowes", "Lowe's Home Improvement"), ("home_depot", "The Home Depot"),
    ("urgent_care", "Urgent Care"), ("hindu_temple", "Hindu Temple"), ("mosque", "Islamic Center"),
]
DEST = [
    ("city", "Dallas (downtown)", -96.7970, 32.7767),
    ("city", "Fort Worth (downtown)", -97.3308, 32.7555),
    ("city", "Corsicana (downtown)", -96.4689, 32.0954),
    ("city", "Fairfield", -96.1530, 31.7246),
    ("city", "Waco (downtown)", -97.1467, 31.5493),
    ("city", "Houston (downtown)", -95.3698, 29.7604),
    ("airport", "DFW International Airport (DFW)", -97.0403, 32.8998),
    ("airport", "Dallas Love Field (DAL)", -96.8517, 32.8471),
    ("airport", "Houston Bush Intercontinental (IAH)", -95.3414, 29.9902),
    ("hospital", "Baylor Univ. Medical Center, Dallas", -96.7800, 32.7884),
    ("hospital", "Parkland Memorial Hospital, Dallas", -96.8389, 32.8106),
    ("community", "Irving / Las Colinas (DFW South Asian hub)", -96.9489, 32.8140),
]


def overpass(q, tries=6):
    wait = 5
    for i in range(tries):
        try:
            r = OSM.post(OVERPASS[i % 2], data={"data": q}, timeout=120)
            r.raise_for_status()
            return r.json()["elements"]
        except Exception as e:  # noqa: BLE001
            print("   overpass retry", i + 1, str(e)[:60], flush=True)
            time.sleep(wait); wait = min(wait * 2, 60)
    return []


def route(a, b):
    url = OSRM.format(a=f"{a[0]:.6f},{a[1]:.6f}", b=f"{b[0]:.6f},{b[1]:.6f}")
    for i in range(4):
        try:
            d = OSM.get(url, timeout=60).json()
            if d.get("code") == "Ok":
                rt = d["routes"][0]
                return round(rt["distance"] / 1609.344, 1), round(rt["duration"] / 60.0)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2 * (i + 1))
    return None, None


def poi(lon, lat, category=None, text=None, n=6):
    p = {"location": f"{lon},{lat}", "maxLocations": n, "f": "json",
         "outFields": "PlaceName,Place_addr,Type,Distance,Phone,URL"}
    if category:
        p["category"] = category
    if text:
        p["SingleLine"] = text
    try:
        d = get(GEOCODE, params=p, timeout=60)
    except Exception as e:  # noqa: BLE001
        print("   geocode fail", category, text, e); return []
    out = []
    for c in d.get("candidates", []):
        a = c["attributes"]
        loc = c["location"]
        out.append({"name": a.get("PlaceName") or c.get("address"), "addr": a.get("Place_addr"),
                    "type": a.get("Type"), "lon": loc["x"], "lat": loc["y"],
                    "crow_mi": round(haversine_mi((lon, lat), (loc["x"], loc["y"])), 1)})
    return out


def main():
    P = load("parcels.json")
    local = load("osm_local.json", {}) or {}
    services = load("services.json", {}) or {}
    for key, rec in P.items():
        lon, lat = rec["centroid"]["lon"], rec["centroid"]["lat"]
        if key not in local or not local[key]:
            d = 0.012
            local[key] = overpass(
                f'[out:json][timeout:90];(way["highway"]({lat-d},{lon-d*1.2},{lat+d},{lon+d*1.2});'
                f'way["natural"="water"]({lat-d},{lon-d*1.2},{lat+d},{lon+d*1.2});'
                f'nwr["barrier"="gate"]({lat-d},{lon-d*1.2},{lat+d},{lon+d*1.2}););out geom;')
            save("osm_local.json", local)
        print(key, "local OSM elements:", len(local[key]), flush=True)
        res = {}
        for cat, label in CATEGORIES:
            c = poi(lon, lat, category=cat)
            c = [x for x in c if x["crow_mi"] < 120]
            c.sort(key=lambda x: x["crow_mi"])
            for x in c[:2]:
                x["drive_mi"], x["drive_min"] = route((lon, lat), (x["lon"], x["lat"]))
            res[label] = c[:2]
            if c:
                print(f"   {label:18s} {c[0]['name'][:42]:42s} {c[0]['addr'][:40] if c[0]['addr'] else '':40s} "
                      f"{c[0]['crow_mi']} mi | {c[0].get('drive_mi')} mi {c[0].get('drive_min')} min", flush=True)
        for label, text in NAME_SEARCHES:
            c = poi(lon, lat, text=text, n=8)
            c = [x for x in c if x["crow_mi"] < 150 and x["type"] not in ("Street Name", "Locality", "Postal")]
            c.sort(key=lambda x: x["crow_mi"])
            for x in c[:2]:
                x["drive_mi"], x["drive_min"] = route((lon, lat), (x["lon"], x["lat"]))
            res.setdefault(label + "_byname", []).extend(c[:2])
            if c:
                print(f"   {label:18s} {c[0]['name'][:42]:42s} {c[0]['addr'][:40] if c[0]['addr'] else '':40s} "
                      f"{c[0]['crow_mi']} mi | {c[0].get('drive_mi')} mi {c[0].get('drive_min')} min", flush=True)
        named = []
        for kind, name, dlon, dlat in DEST:
            mi, mins = route((lon, lat), (dlon, dlat))
            named.append({"kind": kind, "name": name, "lon": dlon, "lat": dlat,
                          "crow_mi": round(haversine_mi((lon, lat), (dlon, dlat)), 1),
                          "drive_mi": mi, "drive_min": mins})
            print(f"   {name:46s} {mi} mi {mins} min", flush=True)
        res["named"] = named
        services[key] = res
        save("services.json", services)


if __name__ == "__main__":
    main()
