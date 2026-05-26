"""Unified extractor for 105-114年 A1 data — Taitung only.

Two schemas exist:
  - simple (105, 106, 110): 發生時間, 發生地點, 死亡受傷人數, 車種 (+ 經緯度 from 110)
  - full   (107-109, 111-114): full per-party rows with all crash detail fields

We normalize to one event-level record. For full-schema files we deduplicate the
per-party rows into one event keyed on (date, time, lon, lat, location).
"""
import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path("/Users/yunching0513/Taitung_Mobility/資料")
# (roc_year, calendar_year, filename pattern)
YEARS = [
    (105, 2016, "105年度A1交通事故資料.csv", "simple"),
    (106, 2017, "106年度A1交通事故資料.csv", "simple"),
    (107, 2018, "2018年度A1交通事故資料.csv", "full"),
    (108, 2019, "2019年度A1交通事故資料.csv", "full"),
    (109, 2020, "2020年度A1交通事故資料.csv", "full"),
    (110, 2021, "110年度A1交通事故資料.csv", "simple"),
    (111, 2022, "111年度A1交通事故資料.csv", "full"),
    (112, 2023, "112年度A1交通事故資料.csv", "full"),
    (113, 2024, "113年度A1交通事故資料.csv", "full"),
    (114, 2025, "114年度A1交通事故資料.csv", "full"),
]

DISTRICT_RE = re.compile(r"(?:台東縣|臺東縣)(.{1,4}?[鄉鎮市])")

def normalize_district(name: str) -> str:
    return name.replace("臺", "台") if name else "其他"

def parse_casualties(s: str) -> tuple[int, int]:
    deaths = injuries = 0
    if not s:
        return 0, 0
    m = re.search(r"死亡(\d+)", s); deaths = int(m.group(1)) if m else 0
    m = re.search(r"受傷(\d+)", s); injuries = int(m.group(1)) if m else 0
    return deaths, injuries

# Parse "105年01月01日 02時45分00秒" → "20160101", "024500"
ROC_DT_RE = re.compile(r"(\d+)年(\d+)月(\d+)日\s+(\d+)時(\d+)分(\d+)秒")
def parse_simple_datetime(s: str) -> tuple[str, str, int, int]:
    m = ROC_DT_RE.match(s)
    if not m:
        return "", "", 0, 0
    roc, mo, day, hh, mm, ss = map(int, m.groups())
    year = roc + 1911
    date = f"{year:04d}{mo:02d}{day:02d}"
    time = f"{hh:02d}{mm:02d}{ss:02d}"
    return date, time, year, mo

def classify_mode(vehicle_str: str) -> str:
    """Roll vehicle text up to one of: 機車 / 汽車 / 人 / 慢車 / 其他."""
    v = vehicle_str or ""
    if "機車" in v: return "機車"
    if "客車" in v or "貨車" in v or "曳引" in v: return "汽車"
    if "行人" in v or v.strip() == "人": return "人"
    if "自行車" in v or "慢車" in v: return "慢車"
    return "其他"

def primary_vehicle_simple(vehicle_field: str) -> str:
    """車種 field for simple schema looks like '普通重型-機車;自用-小貨車...'
    Use first segment as the principal party."""
    if not vehicle_field:
        return ""
    first = vehicle_field.split(";")[0]
    return first

events = []
year_party_counter = defaultdict(lambda: Counter())

for roc, cy, fname, schema in YEARS:
    path = BASE / f"{roc}年傷亡道路交通事故資料" / fname
    if not path.exists():
        print(f"MISSING: {path}", file=sys.stderr)
        continue

    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if schema == "simple":
        for row in rows:
            loc = row.get("發生地點", "")
            if "台東縣" not in loc and "臺東縣" not in loc:
                continue
            date, time, year_calc, month = parse_simple_datetime(row.get("發生時間",""))
            deaths, injuries = parse_casualties(row.get("死亡受傷人數",""))
            district_match = DISTRICT_RE.search(loc)
            district = normalize_district(district_match.group(1)) if district_match else "其他"
            try:
                lon = float(row.get("經度") or 0)
                lat = float(row.get("緯度") or 0)
            except ValueError:
                lon = lat = 0.0

            veh_field = row.get("車種","")
            principal = primary_vehicle_simple(veh_field)
            mode = classify_mode(principal)

            events.append({
                "schema": "simple",
                "roc": roc,
                "year": cy,
                "month": month,
                "date": date,
                "time": time,
                "location": loc,
                "district": district,
                "lon": lon, "lat": lat,
                "deaths": deaths,
                "injuries": injuries,
                "mode": mode,
                "principal_vehicle": principal,
                "vehicles_raw": veh_field,
                "weather": "", "light": "", "road_type": "", "speed_limit": "",
                "road_shape_main": "", "road_shape_sub": "",
                "surface": "", "signal": "",
                "accident_main": "", "accident_sub": "",
                "cause_main": "",
                "parties": [],
            })
            year_party_counter[cy][mode] += 1
    else:
        # full schema — group rows by event key
        by_key = {}
        for row in rows:
            loc = row.get("發生地點", "")
            if "台東縣" not in loc and "臺東縣" not in loc:
                continue
            key = (row["發生日期"], row["發生時間"], row.get("經度",""), row.get("緯度",""), loc)
            if key not in by_key:
                by_key[key] = []
            by_key[key].append(row)
        for key, group in by_key.items():
            first = group[0]
            try:
                lon = float(first.get("經度") or 0)
                lat = float(first.get("緯度") or 0)
            except ValueError:
                lon = lat = 0.0
            district_match = DISTRICT_RE.search(first.get("發生地點",""))
            district = normalize_district(district_match.group(1)) if district_match else "其他"
            deaths, injuries = parse_casualties(first.get("死亡受傷人數",""))
            month = int(first.get("發生月份") or 0)

            # principal party = order==1
            p1 = next((r for r in group if (r.get("當事者順位") or "") == "1"), group[0])
            principal_main = p1.get("當事者區分-類別-大類別名稱-車種","")
            principal_sub = p1.get("當事者區分-類別-子類別名稱-車種","")
            mode = classify_mode(principal_main + principal_sub)

            parties = []
            for r in group:
                age_raw = r.get("當事者事故發生時年齡","")
                try:
                    age = int(age_raw)
                    if age < 0: age = None
                except ValueError:
                    age = None
                parties.append({
                    "order": r.get("當事者順位",""),
                    "vehicle_main": r.get("當事者區分-類別-大類別名稱-車種",""),
                    "vehicle_sub": r.get("當事者區分-類別-子類別名稱-車種",""),
                    "gender": r.get("當事者屬-性-別名稱",""),
                    "age": age,
                    "protection": r.get("保護裝備名稱",""),
                    "action_main": r.get("當事者行動狀態大類別名稱",""),
                    "action_sub": r.get("當事者行動狀態子類別名稱",""),
                    "cause_individual": r.get("肇因研判子類別名稱-個別",""),
                })

            events.append({
                "schema": "full",
                "roc": roc,
                "year": cy,
                "month": month,
                "date": first["發生日期"],
                "time": (first.get("發生時間","") or "").zfill(6),
                "location": first["發生地點"],
                "district": district,
                "lon": lon, "lat": lat,
                "deaths": deaths,
                "injuries": injuries,
                "mode": mode,
                "principal_vehicle": principal_main + (("·"+principal_sub) if principal_sub else ""),
                "vehicles_raw": ";".join(
                    (r.get("當事者區分-類別-大類別名稱-車種","") or "")
                    + ("-" + r.get("當事者區分-類別-子類別名稱-車種","") if r.get("當事者區分-類別-子類別名稱-車種") else "")
                    for r in group),
                "weather": first.get("天候名稱",""),
                "light": first.get("光線名稱",""),
                "road_type": first.get("道路類別-第1當事者-名稱",""),
                "speed_limit": first.get("速限-第1當事者",""),
                "road_shape_main": first.get("道路型態大類別名稱",""),
                "road_shape_sub": first.get("道路型態子類別名稱",""),
                "surface": first.get("路面狀況-路面狀態名稱",""),
                "signal": first.get("號誌-號誌種類名稱",""),
                "accident_main": first.get("事故類型及型態大類別名稱",""),
                "accident_sub": first.get("事故類型及型態子類別名稱",""),
                "cause_main": first.get("肇因研判子類別名稱-主要",""),
                "parties": parties,
            })
            year_party_counter[cy][mode] += 1

events.sort(key=lambda e: (e["date"], e["time"]))

OUT_DIR = Path("/Users/yunching0513/Taitung_Mobility")
(OUT_DIR / "taitung_a1_all.json").write_text(
    json.dumps(events, ensure_ascii=False, separators=(",", ":")))

# Stats: produce a yearly summary
yearly = {}
for e in events:
    y = e["year"]
    s = yearly.setdefault(y, {
        "year": y, "roc": e["roc"], "schema": e["schema"],
        "events": 0, "deaths": 0, "injuries": 0,
        "with_coords": 0,
        "by_mode": Counter(), "by_district": Counter(),
        "by_month": Counter(), "by_hour": Counter(),
        "by_road": Counter(), "by_light": Counter(),
    })
    s["events"] += 1
    s["deaths"] += e["deaths"]
    s["injuries"] += e["injuries"]
    if e["lon"] and e["lat"]:
        s["with_coords"] += 1
    s["by_mode"][e["mode"]] += 1
    s["by_district"][e["district"]] += e["deaths"]
    s["by_month"][e["month"]] += 1
    try:
        hh = int(e["time"][:2])
        s["by_hour"][hh] += 1
    except ValueError:
        pass
    if e.get("road_type"): s["by_road"][e["road_type"]] += 1
    if e.get("light"): s["by_light"][e["light"]] += 1

# Print + serialize summary
print(f"{'Year':<6}{'Events':>8}{'Deaths':>8}{'Coords':>8}  Top mode")
for y in sorted(yearly):
    s = yearly[y]
    top = s["by_mode"].most_common(1)[0] if s["by_mode"] else ("-",0)
    print(f"{y:<6}{s['events']:>8}{s['deaths']:>8}{s['with_coords']:>8}  {top[0]} ({top[1]})")

# JSON-serialize summary (Counters → dicts)
def ser(s):
    return {
        "year": s["year"], "roc": s["roc"], "schema": s["schema"],
        "events": s["events"], "deaths": s["deaths"], "injuries": s["injuries"],
        "with_coords": s["with_coords"],
        "by_mode": dict(s["by_mode"]),
        "by_district": dict(s["by_district"]),
        "by_month": dict(s["by_month"]),
        "by_hour": dict(s["by_hour"]),
        "by_road": dict(s["by_road"]),
        "by_light": dict(s["by_light"]),
    }
yearly_serial = [ser(yearly[y]) for y in sorted(yearly)]
(OUT_DIR / "taitung_yearly_summary.json").write_text(
    json.dumps(yearly_serial, ensure_ascii=False, separators=(",", ":")))

# Also write JS embeddable assets
(OUT_DIR / "taitung_a1.js").write_text(
    "window.TAITUNG_A1 = " + json.dumps(events, ensure_ascii=False, separators=(",", ":")) + ";\n"
    "window.TAITUNG_YEARLY = " + json.dumps(yearly_serial, ensure_ascii=False, separators=(",", ":")) + ";\n"
)
print(f"\nTotal events across all years: {len(events)}")
print(f"Total deaths: {sum(e['deaths'] for e in events)}")
print(f"Events with coords: {sum(1 for e in events if e['lon'] and e['lat'])}")
