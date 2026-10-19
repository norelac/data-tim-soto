"""Ambil jumlah penduduk, luas wilayah, kepadatan per kecamatan (BPS Kota Semarang, 2025).

Tabel: https://semarangkota.bps.go.id/id/statistics-table/2/NDgjMg%3D%3D/...
Data diambil dari JSON yang tertanam di halaman (bukan scraping HTML tabel).
"""
import csv, json, re, pathlib, requests

ROOT = pathlib.Path(r"D:\tim soto")
URL = ("https://semarangkota.bps.go.id/id/statistics-table/2/NDgjMg%3D%3D/"
       "luas-wilayah--jumlah-penduduk--dan-kepadatan-penduduk.html")
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

html = S.get(URL, timeout=60).text

# label kecamatan (vervar) ada sebelum datacontent di dalam blob JSON yang di-escape
lab = html[: html.find("datacontent")]
lab = re.sub(r"\\+(.)", r"\1", lab[lab.rfind("vervar"):])
labels = json.loads(lab[lab.find('['): lab.find("]") + 1])

# kunci datacontent: <vervar><var=48><kolom><tahun=1250>; kolom 3=luas, 5=penduduk, 6=kepadatan
data = {}
for m in re.finditer(r'\\?"(\d+?)485(\d)1250\\?":([\d.]+)', html):
    data.setdefault(int(m.group(1)), {})[int(m.group(2))] = float(m.group(3))

rows = []
for item in labels:
    i = item["val"]
    d = data.get(i, {})
    if not d:
        continue
    rows.append({
        "kecamatan": item["label"],
        "luas_km2": d.get(3),
        "penduduk_jiwa": int(d.get(5)) if d.get(5) else None,
        "kepadatan_jiwa_km2": d.get(6),
        "tahun": 2025,
        "sumber": "BPS Kota Semarang - Jumlah Penduduk Menurut Kecamatan, Luas Wilayah, dan Kepadatan Penduduk",
        "sumber_url": URL,
    })

out = ROOT / "data" / "penduduk_kecamatan_2025.csv"
with out.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"{len(rows)} baris -> {out}")
tot = sum(r["penduduk_jiwa"] for r in rows if r["kecamatan"] != "Kota Semarang")
for r in rows:
    print(f"  {r['kecamatan']:<18} {r['penduduk_jiwa']:>10,} jiwa  {r['luas_km2']:>7} km2")
print("jumlah 16 kecamatan:", f"{tot:,}", "| baris kota:", [r for r in rows if r["kecamatan"] == "Kota Semarang"])
