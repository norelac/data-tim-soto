"""Tarik 16 dataset ruas jalan Kota Semarang 2022 dari CKAN Jateng, normalisasi, simpan CSV."""
import csv, io, re, json, pathlib, time
import requests, openpyxl

ROOT = pathlib.Path(r"D:\tim soto")
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
API = "https://data.jatengprov.go.id/api/3/action/"
S = requests.Session()
S.headers["User-Agent"] = "SemarangCheck-research/1.0"

def get(url, **kw):
    for i in range(4):
        try:
            r = S.get(url, timeout=60, **kw)
            if r.status_code == 200:
                return r
            print("  HTTP", r.status_code, url[:80])
        except Exception as e:
            print("  retry", i, type(e).__name__)
        time.sleep(2 + i * 2)
    raise RuntimeError("gagal: " + url)

# 1. daftar paket
res = get(API + "package_search",
          params={"q": '"Daftar Ruas Jalan Kec" "Kota Semarang"', "rows": 40}).json()
packs = [p for p in res["result"]["results"]
         if re.match(r"^Daftar Ruas Jalan Kec .*2022$", p["title"].strip())]
packs.sort(key=lambda p: p["title"])
print(f"{len(packs)} paket ditemukan")

rows, meta, seen = [], [], set()

def parse_len(v):
    """'4,035 m' -> 4035.0 ; 633.0 -> 633.0. Koma/titik = pemisah ribuan bila 3 digit di belakang."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("\xa0", " ").strip()
    m = re.search(r"\d[\d.,]*", s)
    if not m:
        return None
    num = m.group(0)
    if "," in num and "." in num:
        dec = "," if num.rfind(",") > num.rfind(".") else "."
        thou = "." if dec == "," else ","
        num = num.replace(thou, "").replace(dec, ".")
    elif "," in num or "." in num:
        sep = "," if "," in num else "."
        head, _, tail = num.rpartition(sep)
        num = head + tail if len(tail) == 3 and head else head + "." + tail
    try:
        return float(num)
    except ValueError:
        return None

def norm_kondisi(v):
    s = re.sub(r"[^a-z ]", "", str(v or "").lower()).strip()
    s = re.sub(r"\s+", " ", s)
    if not s:
        return "KOSONG"
    if s.startswith("baik"):
        return "Baik"
    if s.startswith("sedang"):
        return "Sedang"
    if "ringan" in s:
        return "Rusak Ringan"
    if "berat" in s:
        return "Rusak Berat"
    if s.startswith("rusak"):
        return "Rusak"
    return "LAIN:" + s

for p in packs:
    kec = re.sub(r"^Daftar Ruas Jalan Kec ", "", p["title"])
    kec = re.split(r"(?i)kota", kec)[0]
    kec = kec.replace("\ufffd", "").strip(" \u00a0\u200b,")
    if kec in seen:
        continue
    seen.add(kec)
    d = get(API + "package_show", params={"id": p["name"]}).json()["result"]
    rss = [x for x in d.get("resources", []) if x.get("url")]
    if not rss:
        print("  tanpa resource:", kec)
        continue
    url = rss[0]["url"]
    m = re.search(r"(?:spreadsheets/d|file/d)/([A-Za-z0-9_-]+)", url)
    if not m:
        print("  url tak dikenal:", kec, url[:80])
        continue
    fid = m.group(1)
    kind = "sheets" if "spreadsheets" in url else "drive"
    if kind == "sheets":
        dl = f"https://docs.google.com/spreadsheets/d/{fid}/export?format=xlsx"
    else:
        dl = f"https://drive.usercontent.google.com/download?id={fid}&export=download"

    raw_path = RAW / f"ruas_{re.sub(r'[^a-z0-9]+', '_', kec.lower()).strip('_')}.xlsx"
    if not raw_path.exists():
        raw_path.write_bytes(get(dl).content)
    wb = openpyxl.load_workbook(raw_path, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    grid = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    hi = None
    for i, r in enumerate(grid[:15]):
        cells = [str(c).strip().lower() if c is not None else "" for c in r]
        if "kode ruas" in cells:
            hi = i
            break
    if hi is None:
        print("  header tak ketemu:", kec)
        continue
    hdr = [str(c).strip() if c is not None else "" for c in grid[hi]]
    idx = {h.lower(): i for i, h in enumerate(hdr)}
    n = 0
    for r in grid[hi + 1:]:
        if len(r) <= idx.get("kode ruas", 0) or not r[idx["kode ruas"]]:
            continue
        def cell(name):
            i = idx.get(name)
            return r[i] if i is not None and i < len(r) else None
        rows.append({
            "kecamatan": kec,
            "kode_ruas": str(cell("kode ruas")).strip(),
            "nama_ruas": str(cell("nama ruas") or "").strip(),
            "panjang_m": parse_len(cell("panjang")),
            "lebar_m": parse_len(cell("lebar")),
            "kondisi_raw": str(cell("kondisi") or "").strip(),
            "kondisi": norm_kondisi(cell("kondisi")),
            "sumber": d.get("title"),
            "sumber_url": f"https://data.jatengprov.go.id/dataset/{p['name']}",
            "file_url": url,
            "diakses": time.strftime("%Y-%m-%d"),
        })
        n += 1
    meta.append({"kecamatan": kec, "paket": p["name"], "judul": d["title"],
                 "tipe_file": kind, "baris": n, "resource_url": url,
                 "file_lokal": raw_path.name})

out = ROOT / "data" / "ruas_jalan_2022.csv"
with out.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
(ROOT / "data" / "sumber_ruas_jalan.json").write_text(
    json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"{len(meta)} kecamatan, {len(rows)} ruas -> {out}")
for m in meta:
    print(f"  {m['kecamatan']:<18} {m['tipe_file']:<7} {m['baris']:>4} ruas")
