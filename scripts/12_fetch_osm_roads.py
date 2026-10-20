"""Ambil jaringan jalan OSM (Overpass) per kecamatan, simpan JSON mentah.

Sumber: OpenStreetMap via Overpass API (© OpenStreetMap contributors, ODbL).
Jalankan: python scripts/12_fetch_osm_roads.py [nama_kecamatan]
"""
import json, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEO = ROOT / "data" / "batas_kecamatan_semarang.geojson"
OUT = ROOT / "data" / "osm" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

ENDPOINTS = [
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
HIGHWAY = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|road"

S = requests.Session()
S.headers["User-Agent"] = "SemarangCheck-research/1.0 (riset data lomba; kontak: tim)"


def bbox_of(geom):
    pts = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    pad = 0.004
    return (min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad)


def main(only=None, workers=3):
    gj = json.loads(GEO.read_text(encoding="utf-8"))
    feats = gj["features"]
    if only:
        feats = [f for f in feats if f["properties"]["kecamatan"].lower() == only.lower()]

    todo = []
    for f in feats:
        name = f["properties"]["kecamatan"]
        slug = name.lower().replace(" ", "_")
        dest = OUT / f"{slug}.json"
        if dest.exists() and dest.stat().st_size > 200:
            print(f"skip {name} ({dest.stat().st_size//1024} KB)")
            continue
        s, w, n, e = bbox_of(f["geometry"])
        q = (f'[out:json][timeout:600];way["highway"~"^({HIGHWAY})$"]["name"]'
             f'({s:.5f},{w:.5f},{n:.5f},{e:.5f});out geom;')
        todo.append((name, dest, q))

    def worker(item):
        name, dest, q = item
        ses = requests.Session()
        ses.headers["User-Agent"] = S.headers["User-Agent"]
        for attempt in range(4):
            for url in ENDPOINTS:
                t0 = time.time()
                try:
                    r = ses.post(url, data={"data": q}, timeout=400)
                    if r.status_code == 200 and r.text.lstrip().startswith("{"):
                        data = r.json()
                        dest.write_text(r.text, encoding="utf-8")
                        print(f"OK   {name:<20} {len(data.get('elements', [])):>5} way  "
                              f"{len(r.text)//1024:>5} KB  {time.time()-t0:5.1f}s  "
                              f"{url.split('/')[2]}", flush=True)
                        return
                    print(f"HTTP {r.status_code} {name} via {url.split('/')[2]} "
                          f"(coba {attempt+1})", flush=True)
                except Exception as e:
                    print(f"ERR  {name} via {url.split('/')[2]}  {type(e).__name__}  "
                          f"{time.time()-t0:.1f}s", flush=True)
            time.sleep(25 + attempt * 15)
        print(f"GAGAL {name}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(worker, todo))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
