"""Fallback OSM: unduh via OSM API per petak kecil (Overpass sedang penuh).

Simpan way ber-nama (highway) + geometri ke data/osm/raw/<petak>.json,
format sama dengan keluaran Overpass supaya scripts/13_match_osm.py bisa dipakai.

Sumber: © OpenStreetMap contributors (ODbL).
Jalankan: python scripts/12b_fetch_osm_tiles.py
"""
import json, pathlib, time, xml.etree.ElementTree as ET
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEO = ROOT / "data" / "batas_kecamatan_semarang.geojson"
OUT = ROOT / "data" / "osm" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

TILE = 0.02
HIGHWAY = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
           "residential", "living_street", "service", "road"}
API = "https://api.openstreetmap.org/api/0.6/map"

S = requests.Session()
S.headers["User-Agent"] = "SemarangCheck-research/1.0 (riset data lomba)"


def bounds():
    gj = json.loads(GEO.read_text(encoding="utf-8"))
    pts = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for x in c:
                walk(x)

    for f in gj["features"]:
        walk(f["geometry"]["coordinates"])
    pad = 0.006
    return (min(p[1] for p in pts) - pad, min(p[0] for p in pts) - pad,
            max(p[1] for p in pts) + pad, max(p[0] for p in pts) + pad)


def fetch(s, w, n, e, depth=0):
    """Kembalikan list way ber-nama; pecah petak bila server menolak (terlalu besar)."""
    tag = f"{s:.4f}_{w:.4f}_{n:.4f}_{e:.4f}"
    dest = OUT / f"tile_{tag}.json"
    if dest.exists():
        return
    try:
        r = S.get(API, params={"bbox": f"{w},{s},{e},{n}"}, timeout=180)
    except Exception as ex:
        print(f"  ERR {tag} {type(ex).__name__}", flush=True)
        return
    if r.status_code == 509 or (r.status_code == 400 and b"too many" in r.content.lower()):
        if depth >= 3:
            print(f"  LEWATI {tag} (masih terlalu besar)", flush=True)
            return
        print(f"  pecah {tag}", flush=True)
        mlat, mlon = (s + n) / 2, (w + e) / 2
        fetch(s, w, mlat, mlon, depth + 1)
        fetch(s, mlon, mlat, e, depth + 1)
        fetch(mlat, w, n, mlon, depth + 1)
        fetch(mlat, mlon, n, e, depth + 1)
        return
    if r.status_code != 200:
        print(f"  HTTP {r.status_code} {tag}", flush=True)
        return

    nodes, ways, cur = {}, [], None
    root = ET.fromstring(r.content)
    for el in root:
        if el.tag == "node":
            nodes[el.get("id")] = (float(el.get("lat")), float(el.get("lon")))
        elif el.tag == "way":
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            refs = [nd.get("ref") for nd in el.findall("nd")]
            cur = {"type": "way", "id": int(el.get("id")), "tags": tags, "refs": refs}
            ways.append(cur)

    out = []
    for wobj in ways:
        tags = wobj["tags"]
        if tags.get("highway") not in HIGHWAY or not tags.get("name"):
            continue
        geom = [{"lat": nodes[r][0], "lon": nodes[r][1]} for r in wobj["refs"] if r in nodes]
        if len(geom) < 2:
            continue
        out.append({"type": "way", "id": wobj["id"], "tags": tags, "geometry": geom})

    dest.write_text(json.dumps({"elements": out}, ensure_ascii=False), encoding="utf-8")
    print(f"  {tag}  {len(out):>4} way  {len(r.content)//1024:>5} KB", flush=True)


def main():
    s0, w0, n0, e0 = bounds()
    lat_steps = int((n0 - s0) / TILE) + 1
    lon_steps = int((e0 - w0) / TILE) + 1
    print(f"bbox {s0:.4f},{w0:.4f} .. {n0:.4f},{e0:.4f}  → {lat_steps}×{lon_steps} = "
          f"{lat_steps*lon_steps} petak", flush=True)
    seen = set()
    for i in range(lat_steps):
        for j in range(lon_steps):
            s, w = s0 + i * TILE, w0 + j * TILE
            fetch(s, w, min(s + TILE, n0), min(w + TILE, e0))
            time.sleep(0.4)
        print(f"baris {i+1}/{lat_steps}", flush=True)


if __name__ == "__main__":
    main()
