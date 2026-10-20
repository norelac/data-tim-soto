"""Uji konektivitas banyak endpoint Overpass (OSM) dengan query kecil."""
import time, requests

Q = '[out:json][timeout:60];way["highway"]["name"](-7.06,110.38,-7.05,110.41);out tags 5;'
ENDPOINTS = [
    "https://overpass.osm.jp/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
S = requests.Session()
S.headers["User-Agent"] = "SemarangCheck-research/1.0 (riset data lomba)"

for u in ENDPOINTS:
    t0 = time.time()
    try:
        r = S.post(u, data={"data": Q}, timeout=120)
        dt = time.time() - t0
        ok = r.status_code == 200 and r.text.lstrip().startswith("{")
        print(f"{u:<55} {r.status_code} {dt:6.1f}s {len(r.text):>7} char  {'OK' if ok else r.text[:60]!r}", flush=True)
    except Exception as e:
        print(f"{u:<55} ERR {type(e).__name__} {time.time()-t0:.1f}s", flush=True)
