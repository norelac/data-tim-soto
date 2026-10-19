"""Cek kualitas data ruas jalan: null, panjang 0, sebaran kondisi, total km per kecamatan."""
import csv, pathlib, collections

ROOT = pathlib.Path(r"D:\tim soto")
rows = list(csv.DictReader((ROOT / "data" / "ruas_jalan_2022.csv").open(encoding="utf-8-sig")))
print(f"{len(rows)} baris, {len({r['kecamatan'] for r in rows})} kecamatan")

bad_p = [r for r in rows if not r["panjang_m"]]
bad_l = [r for r in rows if not r["lebar_m"]]
print("panjang kosong:", len(bad_p), "| lebar kosong:", len(bad_l))
print("kondisi mentah unik:", sorted({r["kondisi_raw"] for r in rows}))
print("kondisi ternormalisasi:", collections.Counter(r["kondisi"] for r in rows))
print("kode ruas duplikat:", len(rows) - len({r["kode_ruas"] for r in rows}))
print("kode ruas kosong:", sum(1 for r in rows if not r["kode_ruas"]))
dups = [k for k, v in collections.Counter(r["kode_ruas"] for r in rows).items() if v > 1]
print("contoh duplikat:", dups[:8])

tbl = []
for kec in sorted({r["kecamatan"] for r in rows}):
    s = [r for r in rows if r["kecamatan"] == kec]
    c = collections.Counter(r["kondisi"] for r in s)
    km = sum(float(r["panjang_m"] or 0) for r in s) / 1000
    km_rb = sum(float(r["panjang_m"] or 0) for r in s if r["kondisi"] == "Rusak Berat") / 1000
    km_rr = sum(float(r["panjang_m"] or 0) for r in s if r["kondisi"] == "Rusak Ringan") / 1000
    km_s = sum(float(r["panjang_m"] or 0) for r in s if r["kondisi"] == "Sedang") / 1000
    km_b = sum(float(r["panjang_m"] or 0) for r in s if r["kondisi"] == "Baik") / 1000
    km_k = sum(float(r["panjang_m"] or 0) for r in s if r["kondisi"] == "KOSONG") / 1000
    ekv = km_rb * 1.0 + km_rr * 0.6 + km_s * 0.3
    tbl.append((kec, len(s), round(km, 1), round(km_b, 1), round(km_s, 1), round(km_rr, 1),
                round(km_rb, 1), round(km_k, 1), round(ekv, 1), round(ekv / km * 100, 1) if km else 0))
print(f"\n{'kecamatan':<16}{'ruas':>5}{'km':>8}{'baik':>7}{'sdg':>7}{'RR':>7}{'RB':>7}{'kosong':>8}{'km_ekv':>8}{'%ekv':>7}")
for t in tbl:
    print(f"{t[0]:<16}{t[1]:>5}{t[2]:>8}{t[3]:>7}{t[4]:>7}{t[5]:>7}{t[6]:>7}{t[7]:>8}{t[8]:>8}{t[9]:>7}")
print("TOTAL km:", round(sum(t[2] for t in tbl), 1), "| ruas:", sum(t[1] for t in tbl))
