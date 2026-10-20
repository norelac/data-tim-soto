import csv, json, pathlib, re, unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

ROOT = pathlib.Path(r"D:\tim soto")

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = re.sub(r"\b(jl|jln|jalan)\b\.?", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

names = set()
for f in (ROOT / "data" / "osm" / "raw").glob("*.json"):
    for el in json.loads(f.read_text(encoding="utf-8")).get("elements", []):
        nm = (el.get("tags") or {}).get("name")
        if nm:
            names.add(norm(nm))

rows = list(csv.DictReader(open(ROOT / "data" / "ruas_jalan_2022.csv", encoding="utf-8-sig")))
un = [r for r in rows if norm(r["nama_ruas"]) not in names]
print("tidak cocok persis:", len(un))

for r in un[:30]:
    n = norm(r["nama_ruas"])
    best = sorted(((SequenceMatcher(None, n, c).ratio(), c) for c in names), reverse=True)[:2]
    print(f'{r["kecamatan"]:<18} {r["nama_ruas"]:<38} -> '
          + " | ".join(f"{c} ({s:.2f})" for s, c in best))
