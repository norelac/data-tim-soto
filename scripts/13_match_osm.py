"""Cocokkan 1.012 ruas dataset (nama saja) ke geometri OSM.

Masukan : data/ruas_jalan_2022.csv, data/osm/raw/*.json
Luaran  : data/osm/ruas_osm_match.csv, data/osm/laporan_osm.txt,
          data/osm/ruas_geometri.geojson (hanya yang cocok)
Jalankan: python scripts/13_match_osm.py
"""
import csv, json, math, pathlib, re, unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "osm" / "raw"
OUT = ROOT / "data" / "osm"
OUT.mkdir(parents=True, exist_ok=True)

ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6",
         "vii": "7", "viii": "8", "ix": "9", "x": "10"}
ABBREV = {"kp": "kampung", "h": "haji", "kh": "kiai", "gg": "gang",
          "jl": "", "jln": "", "jalan": ""}


def norm(s: str) -> str:
    """Kunci pencocokan: tanpa spasi, tanpa 'Jl.', angka romawi -> arab."""
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = []
    for t in s.split():
        t = ABBREV.get(t, ROMAN.get(t, t))
        if t:
            toks.append(t)
    return "".join(toks)


def haversine(a, b):
    R = 6371008.8
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def norm_kec(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def way_length_m(elem):
    pts = [(p["lat"], p["lon"]) for p in elem.get("geometry") or []]
    return sum(haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside


def kec_at(lon, lat, kec_polys):
    for name, geom in kec_polys:
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            if poly and point_in_ring(lon, lat, poly[0]) and not any(
                    point_in_ring(lon, lat, hole) for hole in poly[1:]):
                return name
    return None


def load_osm(kec_polys):
    ways = {}          # id -> dict(name, len, geom, kec)
    for f in sorted(RAW.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for el in data.get("elements", []):
            if el.get("type") != "way" or not el.get("geometry"):
                continue
            name = (el.get("tags") or {}).get("name")
            if not name:
                continue
            p0 = el["geometry"][len(el["geometry"]) // 2]
            kec = ((kec_at(p0["lon"], p0["lat"], kec_polys) or f.stem)
                   if f.stem.startswith("tile_") else f.stem)
            ways[el["id"]] = {"name": name, "len": way_length_m(el),
                              "geom": [[p["lon"], p["lat"]] for p in el["geometry"]],
                              "kec": norm_kec(kec)}
    return ways


def main():
    geo = json.loads((ROOT / "data" / "batas_kecamatan_semarang.geojson").read_text(encoding="utf-8"))
    kec_polys = [(f["properties"]["kecamatan"], f["geometry"]) for f in geo["features"]]
    ways = load_osm(kec_polys)
    by_name = defaultdict(list)
    by_kec = defaultdict(lambda: defaultdict(list))
    for wid, w in ways.items():
        k = norm(w["name"])
        by_name[k].append((wid, w))
        if w["kec"]:
            by_kec[w["kec"]][k].append((wid, w))
    rows = list(csv.DictReader(open(ROOT / "data" / "ruas_jalan_2022.csv", encoding="utf-8-sig")))

    def pick(hits, kec):
        """Utamakan way dari kecamatan yang sama; jatuh ke semua bila kosong."""
        same = [h for h in hits if h[1]["kec"] == norm_kec(kec)]
        return same or hits

    out, matched_ways, feats = [], set(), []
    for r in rows:
        raw_name = r["nama_ruas"]
        k = norm(raw_name)
        same = by_kec.get(norm_kec(r["kecamatan"]), {})
        hits, metode = [], ""
        if k in by_name:
            hits, metode = pick(by_name[k], r["kecamatan"]), "persis"
        elif not k[-1:].isdigit():
            # nama dataset tanpa nomor, OSM memecah jadi beberapa nomor (I, II, ...)
            cand = [ck for ck in same if re.fullmatch(re.escape(k) + r"\d+", ck)]
            if cand:
                hits = [h for ck in cand for h in same[ck]]
                metode = f"induk ({len(cand)} ruas)" if len(cand) > 1 else "induk"
        if not hits:
            # fuzzy: bandingkan dengan nama OSM, prioritaskan kecamatan yang sama.
            # Wajib konsisten soal nomor: "Kapas" tidak boleh cocok ke "Kapas III".
            k_num = re.search(r"(\d+)$", k)
            best, score = None, 0.0
            for cand, lst in by_name.items():
                c_num = re.search(r"(\d+)$", cand)
                if (k_num.group(1) if k_num else None) != (c_num.group(1) if c_num else None):
                    continue
                s = SequenceMatcher(None, k, cand).ratio()
                if any(w["kec"] == norm_kec(r["kecamatan"]) for _, w in lst):
                    s += 0.03  # sedikit bonus untuk kecamatan yang sama
                if s > score:
                    best, score = cand, s
            score = min(score, 1.0)
            if best and score >= 0.94:
                hits, metode = pick(by_name[best], r["kecamatan"]), f"mirip ({score:.2f})"

        osm_len = sum(w["len"] for _, w in hits)
        for wid, _ in hits:
            matched_ways.add(wid)
        ds_len = float(r["panjang_m"] or 0)
        rasio = osm_len / ds_len if ds_len and osm_len else 0
        kualitas = ("" if not hits else
                    "penuh" if 0.6 <= rasio <= 1.6 else
                    "sebagian" if rasio < 0.6 else "berlebih")
        out.append({
            "kecamatan": r["kecamatan"],
            "kode_ruas": r["kode_ruas"],
            "nama_ruas": raw_name,
            "kondisi": r["kondisi"],
            "panjang_dataset_m": round(ds_len, 1),
            "panjang_osm_m": round(osm_len, 1),
            "rasio": round(rasio, 3) if rasio else "",
            "kualitas": kualitas,
            "n_way": len(hits),
            "metode": metode or "tidak cocok",
            "osm_name": " | ".join(sorted({w["name"] for _, w in hits})),
        })
        if hits and kualitas == "penuh":
            feats.append({"type": "Feature", "properties": {
                "kecamatan": r["kecamatan"], "kode_ruas": r["kode_ruas"],
                "nama_ruas": raw_name, "kondisi": r["kondisi"],
                "panjang_m": round(ds_len, 1)}, "geometry": {
                "type": "MultiLineString",
                "coordinates": [[[round(x, 6), round(y, 6)] for x, y in w["geom"]] for _, w in hits]}})

    with open(OUT / "ruas_osm_match.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    (OUT / "ruas_geometri.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")

    # laporan
    tot = len(out)
    ok = [r for r in out if r["n_way"]]
    penuh = [r for r in ok if r["kualitas"] == "penuh"]
    L = []
    L.append(f"ruas dataset          : {tot}")
    L.append(f"cocok ke OSM          : {len(ok)} ({len(ok)/tot*100:.1f}%)")
    L.append(f"  panjang mirip (±60%) : {len(penuh)} ({len(penuh)/tot*100:.1f}%)  "
             f"→ layak digambar tanpa catatan")
    L.append(f"  sebagian / berlebih  : {len(ok)-len(penuh)}")
    L.append(f"way OSM terpakai      : {len(matched_ways)} dari {len(ways)} way bernama")
    L.append(f"panjang dataset cocok : {sum(r['panjang_dataset_m'] for r in ok)/1000:.1f} km")
    L.append(f"panjang OSM (cocok)   : {sum(r['panjang_osm_m'] for r in ok)/1000:.1f} km")
    ratios = sorted(float(r["rasio"]) for r in ok if r["rasio"])
    if ratios:
        med = ratios[len(ratios) // 2]
        L.append(f"rasio OSM/dataset     : median {med:.2f}  "
                 f"(p10 {ratios[len(ratios)//10]:.2f} · p90 {ratios[len(ratios)*9//10]:.2f})")
        L.append(f"dalam ±25%            : {sum(1 for x in ratios if 0.75 <= x <= 1.25)}/{len(ratios)}")
    L.append("\nmetode:")
    for k, v in Counter(r["metode"].split(" (")[0] for r in out).most_common():
        L.append(f"  {k:<14} {v}")
    L.append("\nper kecamatan (cocok/total · penuh, km dataset):")
    per = defaultdict(lambda: [0, 0, 0, 0.0])
    for r in out:
        p = per[r["kecamatan"]]
        p[0] += 1
        p[1] += 1 if r["n_way"] else 0
        p[2] += 1 if r["kualitas"] == "penuh" else 0
        p[3] += r["panjang_dataset_m"] / 1000
    for k, (n, m, full, km) in sorted(per.items(), key=lambda x: -x[1][2] / x[1][0]):
        L.append(f"  {k:<20} {m:>4}/{n:<4} {m/n*100:5.1f}%  · penuh {full:>3} "
                 f"{full/n*100:5.1f}%  {km:6.1f} km")
    txt = "\n".join(L)
    (OUT / "laporan_osm.txt").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
