"""Area context: climate normals (deg C), Census demographics, FEMA National
Risk Index ratings for Navarro County, and Richland-Chambers lake-level history.

Outputs data/climate.json, data/census.json, data/nri.json, data/lake_levels.json
"""
import csv
import io
import statistics

from common import DATA, get, load, save, SESSION

ACS_VARS = {
    "B01003_001E": "population",
    "B19013_001E": "median_household_income",
    "B01002_001E": "median_age",
    "B11001_001E": "households",
    "B25077_001E": "median_home_value",
    "B02001_002E": "white_alone",
    "B02001_003E": "black_alone",
    "B02001_005E": "asian_alone",
    "B03003_003E": "hispanic",
    "B02015_002E": "asian_indian",
    "B09001_001E": "under18",
    "B01001_020E": "m65_66", "B01001_021E": "m67_69", "B01001_022E": "m70_74",
    "B01001_023E": "m75_79", "B01001_024E": "m80_84", "B01001_025E": "m85p",
    "B01001_044E": "f65_66", "B01001_045E": "f67_69", "B01001_046E": "f70_74",
    "B01001_047E": "f75_79", "B01001_048E": "f80_84", "B01001_049E": "f85p",
    "B11001_002E": "family_households", "B25003_002E": "owner_occupied", "B25003_001E": "occupied_units",
    "B15003_022E": "bachelors", "B15003_001E": "pop25p",
}


def climate(lat, lon):
    u = ("https://archive-api.open-meteo.com/v1/archive"
         f"?latitude={lat:.4f}&longitude={lon:.4f}&start_date=1995-01-01&end_date=2024-12-31"
         "&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,"
         "relative_humidity_2m_mean&timezone=America%2FChicago")
    d = get(u, timeout=300)["daily"]
    t = d["time"]
    years = sorted({x[:4] for x in t})
    mon = {m: {"mx": [], "mn": [], "mean": [], "p": [], "rh": []} for m in range(1, 13)}
    for i, day in enumerate(t):
        m = int(day[5:7])
        for k, src in (("mx", "temperature_2m_max"), ("mn", "temperature_2m_min"),
                       ("mean", "temperature_2m_mean"), ("p", "precipitation_sum"),
                       ("rh", "relative_humidity_2m_mean")):
            v = d[src][i]
            if v is not None:
                mon[m][k].append(v)
    monthly = []
    for m in range(1, 13):
        s = mon[m]
        monthly.append({"month": m, "tmax": round(statistics.mean(s["mx"]), 1),
                        "tmin": round(statistics.mean(s["mn"]), 1),
                        "precip_mm": round(sum(s["p"]) / len(years), 1),
                        "rh": round(statistics.mean(s["rh"]), 0) if s["rh"] else None})
    # growing season per year (last spring / first autumn day with Tmin <= 0 C)
    by_year = {}
    for i, day in enumerate(t):
        v = d["temperature_2m_min"][i]
        if v is not None:
            by_year.setdefault(day[:4], []).append((day, v))
    seasons, freeze_days, hot_days = [], [], []
    for y, rows in by_year.items():
        rows.sort()
        mid = len(rows) // 2
        fr = [k for k, (_, v) in enumerate(rows) if v <= 0.0]
        freeze_days.append(len(fr))
        sp = [k for k in fr if k < mid]
        fa = [k for k in fr if k >= mid]
        seasons.append((min(fa) if fa else len(rows)) - (max(sp) if sp else 0) - 1)
    for y in years:
        hot_days.append(sum(1 for i, day in enumerate(t) if day.startswith(y)
                            and (d["temperature_2m_max"][i] or -99) >= 35.0))
    tmax = [v for v in d["temperature_2m_max"] if v is not None]
    tmin = [v for v in d["temperature_2m_min"] if v is not None]
    tmean = [v for v in d["temperature_2m_mean"] if v is not None]
    pr = [v for v in d["precipitation_sum"] if v is not None]
    rh = [v for v in d["relative_humidity_2m_mean"] if v is not None]
    return {"period": f"{years[0]}-{years[-1]}", "source": "ERA5 reanalysis via Open-Meteo archive API",
            "mean_annual_c": round(statistics.mean(tmean), 1),
            "jul_aug_high_c": round((monthly[6]["tmax"] + monthly[7]["tmax"]) / 2, 1),
            "jan_low_c": monthly[0]["tmin"],
            "record_high_c": round(max(tmax), 1), "record_low_c": round(min(tmin), 1),
            "annual_precip_mm": round(sum(pr) / len(years)), "mean_rh_pct": round(statistics.mean(rh)),
            "growing_season_days": round(statistics.mean(seasons)),
            "freeze_days_per_year": round(statistics.mean(freeze_days), 1),
            "days_ge_35c_per_year": round(statistics.mean(hot_days), 1),
            "monthly": monthly}


def acs(state, county, tract):
    var = ",".join(ACS_VARS)
    out = {}
    for geo, q in (("county", f"for=county:{county}&in=state:{state}"),
                   ("tract", f"for=tract:{tract}&in=state:{state}%20county:{county}"),
                   ("texas", f"for=state:{state}")):
        for yr in (2024, 2023):
            u = f"https://api.census.gov/data/{yr}/acs/acs5?get=NAME,{var}&{q}"
            try:
                r = SESSION.get(u, timeout=90)
                if r.status_code != 200 or r.text.lstrip().startswith("<"):
                    continue
                d = r.json()
                rec = dict(zip(d[0], d[1]))
                vals = {ACS_VARS[k]: (float(rec[k]) if rec.get(k) not in (None, "") else None) for k in ACS_VARS}
                vals["name"] = rec["NAME"]
                vals["vintage"] = f"ACS 5-year {yr-4}-{yr}"
                out[geo] = vals
                break
            except Exception as e:  # noqa: BLE001
                out[geo + "_error"] = str(e)[:120]
    # decennial 2010 & 2020 county population for growth
    for yr, ds, v in ((2020, "dec/pl", "P1_001N"), (2010, "dec/sf1", "P001001")):
        u = f"https://api.census.gov/data/{yr}/{ds}?get=NAME,{v}&for=county:{county}&in=state:{state}"
        try:
            d = SESSION.get(u, timeout=90).json()
            out[f"census{yr}_county_pop"] = int(d[1][1])
        except Exception as e:  # noqa: BLE001
            out[f"census{yr}_error"] = str(e)[:120]
    return out


def nri(county_fips="48349"):
    base = ("https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
            "National_Risk_Index_Counties/FeatureServer/0/query")
    try:
        d = get(base, params={"where": f"STCOFIPS='{county_fips}'", "outFields": "*", "f": "json",
                              "returnGeometry": "false"}, timeout=90)
        a = d["features"][0]["attributes"]
        keep = {k: v for k, v in a.items() if k.endswith("_RISKR") or k in
                ("RISK_RATNG", "RISK_SCORE", "SOVI_RATNG", "RESL_RATNG", "EAL_RATNG", "COUNTY", "STATE",
                 "NRI_VER")}
        return keep
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}


def lake_levels():
    r = SESSION.get("https://www.waterdatafortexas.org/reservoirs/individual/richland-chambers.csv", timeout=120)
    rows = [x for x in r.text.splitlines() if not x.startswith("#")]
    rd = [x for x in csv.DictReader(io.StringIO("\n".join(rows))) if x["water_level"]]
    lv = [(x["date"], float(x["water_level"])) for x in rd]
    since = [v for dte, v in lv if dte >= "2000-01-01"]
    by_m = {m: [] for m in range(1, 13)}
    for dte, v in lv:
        if dte >= "2000-01-01":
            by_m[int(dte[5:7])].append(v)
    yr = {}
    for dte, v in lv:
        yr.setdefault(dte[:4], []).append(v)
    out = {"source": "TWDB Water Data for Texas (daily)", "first": lv[0], "last": lv[-1],
           "min_since_2000": min((v, dte) for dte, v in lv if dte >= "2000-01-01"),
           "max_since_2000": max((v, dte) for dte, v in lv if dte >= "2000-01-01"),
           "mean_since_2000": round(statistics.mean(since), 2),
           "pct_days_below_312_since_2000": round(100 * sum(v < 312 for v in since) / len(since), 1),
           "pct_days_above_315_since_2000": round(100 * sum(v > 315 for v in since) / len(since), 1),
           "monthly_mean_since_2000": {m: round(statistics.mean(v), 2) for m, v in by_m.items()},
           "annual_mean": {y: round(statistics.mean(v), 2) for y, v in yr.items()},
           "series_weekly": lv[::7]}
    # level at the 2022 lidar acquisition window
    out["dec2022_jan2023_mean"] = round(statistics.mean([v for dte, v in lv if "2022-11-01" <= dte <= "2023-02-28"]), 2)
    return out


def main():
    P = load("parcels.json")
    clim, cen = {}, {}
    for key, rec in P.items():
        c = rec["centroid"]
        clim[key] = climate(c["lat"], c["lon"])
        print(key, {k: v for k, v in clim[key].items() if k != "monthly"})
    save("climate.json", clim)
    # both lots: Navarro County (48349); tracts from the Census geocoder
    tracts = {"bayview": None, "arrowhead": "970701"}
    for key, rec in P.items():
        c = rec["centroid"]
        g = get("https://geocoding.geo.census.gov/geocoder/geographies/coordinates",
                params={"x": c["lon"], "y": c["lat"], "benchmark": "Public_AR_Current",
                        "vintage": "Current_Current", "layers": "Census Tracts,Counties", "format": "json"})
        tr = g["result"]["geographies"]["Census Tracts"][0]
        tracts[key] = tr["TRACT"]
        cen[key] = {"tract": tr["NAME"], "tract_geoid": tr["GEOID"],
                    "county": g["result"]["geographies"]["Counties"][0]["NAME"]}
        cen[key]["acs"] = acs("48", "349", tr["TRACT"])
        print(key, cen[key]["tract"], {k: v for k, v in cen[key]["acs"].items() if not isinstance(v, dict)})
        for geo in ("county", "tract", "texas"):
            if geo in cen[key]["acs"]:
                a = cen[key]["acs"][geo]
                print("   ", geo, a.get("name"), "pop", a.get("population"), "MHI", a.get("median_household_income"),
                      "age", a.get("median_age"), "asian", a.get("asian_alone"), "indian", a.get("asian_indian"))
    save("census.json", cen)
    n = nri()
    print("NRI:", n)
    save("nri.json", n)
    lk = lake_levels()
    print("lake:", {k: v for k, v in lk.items() if k not in ("series_weekly", "annual_mean")})
    save("lake_levels.json", lk)


if __name__ == "__main__":
    main()
