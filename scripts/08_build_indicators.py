"""Bangun dataset indikator + ranking SAW + simulasi anggaran.

Input : data/ruas_jalan_2022.csv, data/penduduk_kecamatan_2025.csv, data/raw/hsp_bina_marga_2026_semarang.csv
Output: data/indikator_kecamatan.csv, data/simulasi_anggaran.csv, data/semarangcheck_dataset.json
"""
import csv, json, math, pathlib, re, unicodedata

ROOT = pathlib.Path(r"D:\tim soto")
D = ROOT / "data"

# ---------- util ----------
def norm_name(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())

def fnum(x):
    return float(x) if x not in (None, "") else 0.0

BOBOT_SEVERITY = {"Rusak Berat": 1.0, "Rusak Ringan": 0.6, "Sedang": 0.3, "Baik": 0.0, "KOSONG": 0.0}

# ---------- HSP: harga satuan ----------
hsp = {}
hsp_txt = (D / "raw" / "hsp_bina_marga_2026_semarang.csv").read_bytes().decode("cp1252", "replace")
for r in csv.DictReader(hsp_txt.splitlines()):
    kode = r.get("Kode", "").strip()
    h = re.sub(r"[^\d]", "", r.get("Harga Satuan (Rp)", "") or "")
    if kode and h:
        hsp[kode] = float(h)
print("harga satuan terpakai:")
for k in ["C.1", "E.1", "F.1", "F.24", "F.27"]:
    print(f"   {k:<5} Rp {hsp.get(k, 0):>12,.0f}")

# asumsi teknis (dinyatakan terbuka di laporan)
T_ACWC = 0.04          # tebal lapis aus (m)
T_AGG = 0.15           # tebal fondasi agregat (m)
T_GALI = 0.20          # kedalaman galian (m)
RHO = 2.3              # ton/m3 campuran beraspal
PRIME = 0.5            # liter/m2 lapis resap pengikat

BIAYA_OVERLAY = PRIME * hsp.get("F.1", 0) + T_ACWC * RHO * hsp.get("F.24", 0)
BIAYA_REKON = (T_GALI * hsp.get("C.1", 0) + T_AGG * hsp.get("E.1", 0)
               + PRIME * hsp.get("F.1", 0)
               + (T_ACWC * RHO * hsp.get("F.24", 0) + 0.05 * RHO * hsp.get("F.27", 0)))
print(f"\nasumsi biaya: overlay Rp {BIAYA_OVERLAY:,.0f}/m2 | rekonstruksi Rp {BIAYA_REKON:,.0f}/m2")

# ---------- data ruas ----------
ruas = list(csv.DictReader((D / "ruas_jalan_2022.csv").open(encoding="utf-8-sig")))
for r in ruas:
    r["panjang_m"] = fnum(r["panjang_m"])
    r["lebar_m"] = fnum(r["lebar_m"])
    r["luas_m2"] = r["panjang_m"] * r["lebar_m"]
    r["bobot"] = BOBOT_SEVERITY[r["kondisi"]]
    biaya_unit = BIAYA_REKON if r["kondisi"] == "Rusak Berat" else BIAYA_OVERLAY
    r["biaya_perbaikan"] = r["luas_m2"] * biaya_unit if r["kondisi"] in ("Rusak Berat", "Rusak Ringan") else 0.0
    r["km_ekuivalen_rusak"] = r["panjang_m"] / 1000 * r["bobot"]

# ---------- data penduduk ----------
pend = {norm_name(r["kecamatan"]): r
        for r in csv.DictReader((D / "penduduk_kecamatan_2025.csv").open(encoding="utf-8-sig"))}

# ---------- agregasi per kecamatan ----------
kecs = sorted({r["kecamatan"] for r in ruas}, key=norm_name)
agr = []
for k in kecs:
    s = [r for r in ruas if r["kecamatan"] == k]
    p = pend[norm_name(k)]
    km = sum(r["panjang_m"] for r in s) / 1000
    km_kond = {c: sum(r["panjang_m"] for r in s if r["kondisi"] == c) / 1000 for c in BOBOT_SEVERITY}
    ekv = sum(r["km_ekuivalen_rusak"] for r in s)
    pop = float(p["penduduk_jiwa"])
    luas = float(p["luas_km2"])
    biaya = sum(r["biaya_perbaikan"] for r in s)
    agr.append({
        "kecamatan": k,
        "ruas": len(s),
        "km_total": round(km, 3),
        "km_baik": round(km_kond["Baik"], 3),
        "km_sedang": round(km_kond["Sedang"], 3),
        "km_rusak_ringan": round(km_kond["Rusak Ringan"], 3),
        "km_rusak_berat": round(km_kond["Rusak Berat"], 3),
        "km_kondisi_kosong": round(km_kond["KOSONG"], 3),
        "km_ekuivalen_rusak": round(ekv, 3),
        "penduduk": int(pop),
        "luas_km2": luas,
        # indikator mentah
        "i0_volume_kerusakan": ekv,
        "i1_persen_kerusakan": ekv / km,
        "i2_kerusakan_per_1000_penduduk": ekv / pop * 1000,
        "i3_kerusakan_per_km2": ekv / luas,
        "i4_sebaran_ruas_rusak": sum(1 for r in s if r["kondisi"] in ("Rusak Berat", "Rusak Ringan")) / len(s),
        "estimasi_biaya_penuh": round(biaya),
        "km_perlu_penanganan": round(km_kond["Rusak Berat"] + km_kond["Rusak Ringan"], 3),
    })

INDIKATOR = [
    ("i0_volume_kerusakan", "Volume kerusakan (absolut)", "km ekuivalen rusak di kecamatan", "benefit"),
    ("i1_persen_kerusakan", "Intensitas kerusakan", "km ekuivalen rusak / km jalan kecamatan (bobot: RB 1,0 / RR 0,6 / sedang 0,3)", "benefit"),
    ("i2_kerusakan_per_1000_penduduk", "Beban kerusakan per penduduk", "km ekuivalen rusak per 1.000 penduduk", "benefit"),
    ("i3_kerusakan_per_km2", "Kerusakan per luas wilayah", "km ekuivalen rusak per km2", "benefit"),
    ("i4_sebaran_ruas_rusak", "Sebaran kerusakan", "proporsi ruas berkondisi rusak ringan/berat", "benefit"),
]

def saw(rows, bobot):
    """Normalisasi min-max + skor terbobot."""
    out = []
    rng = {}
    for key, *_ in INDIKATOR:
        vals = [r[key] for r in rows]
        rng[key] = (min(vals), max(vals))
    for r in rows:
        skor = 0.0
        rincian = {}
        for key, *_ in INDIKATOR:
            lo, hi = rng[key]
            rn = 0.5 if hi == lo else (r[key] - lo) / (hi - lo)
            rincian[key] = rn
            skor += rn * bobot[key]
        out.append({**r, **{f"n_{k}": round(v, 4) for k, v in rincian.items()}, "skor": skor})
    out.sort(key=lambda x: -x["skor"])
    for i, r in enumerate(out, 1):
        r["peringkat"] = i
    return out

SKENARIO = {
    "seimbang": {k: 1 / len(INDIKATOR) for k, *_ in INDIKATOR},
    "fokus_volume": {"i0_volume_kerusakan": 0.4, "i1_persen_kerusakan": 0.2,
                     "i2_kerusakan_per_1000_penduduk": 0.2, "i3_kerusakan_per_km2": 0.1,
                     "i4_sebaran_ruas_rusak": 0.1},
    "fokus_keparahan": {"i0_volume_kerusakan": 0.1, "i1_persen_kerusakan": 0.4,
                        "i2_kerusakan_per_1000_penduduk": 0.1, "i3_kerusakan_per_km2": 0.1,
                        "i4_sebaran_ruas_rusak": 0.3},
    "fokus_dampak_warga": {"i0_volume_kerusakan": 0.1, "i1_persen_kerusakan": 0.1,
                           "i2_kerusakan_per_1000_penduduk": 0.5, "i3_kerusakan_per_km2": 0.2,
                           "i4_sebaran_ruas_rusak": 0.1},
}
hasil = {name: saw(agr, w) for name, w in SKENARIO.items()}

# ---------- simulasi anggaran (greedy: manfaat per rupiah) ----------
kandidat = [r for r in ruas if r["kondisi"] in ("Rusak Berat", "Rusak Ringan") and r["biaya_perbaikan"] > 0]
for r in kandidat:
    r["manfaat_per_rupiah"] = r["km_ekuivalen_rusak"] / r["biaya_perbaikan"]
kandidat.sort(key=lambda r: -r["manfaat_per_rupiah"])

TOTAL_EKV = sum(r["km_ekuivalen_rusak"] for r in kandidat)

def simulasi(budget):
    sisa, paket = budget, []
    for r in kandidat:
        if r["biaya_perbaikan"] <= sisa:
            sisa -= r["biaya_perbaikan"]
            paket.append(r)
    km = sum(r["panjang_m"] for r in paket) / 1000
    ekv = sum(r["km_ekuivalen_rusak"] for r in paket)
    per_kec = {}
    for r in paket:
        per_kec[r["kecamatan"]] = per_kec.get(r["kecamatan"], 0) + r["panjang_m"] / 1000
    return {"anggaran": budget, "ruas": len(paket), "km": round(km, 2), "km_ekuivalen": round(ekv, 2),
            "cakupan_persen": round(ekv / TOTAL_EKV * 100, 1) if TOTAL_EKV else 0,
            "terpakai": round(budget - sisa), "sisa": round(sisa),
            "kecamatan": {k: round(v, 2) for k, v in sorted(per_kec.items(), key=lambda x: -x[1])}}

ANGGARAN = [5_000_000_000, 10_000_000_000, 15_000_000_000, 20_000_000_000]
sim = [simulasi(b) for b in ANGGARAN]
total_butuh = sum(r["biaya_perbaikan"] for r in kandidat)

# ---------- tulis ----------
with (D / "indikator_kecamatan.csv").open("w", newline="", encoding="utf-8-sig") as f:
    cols = ["peringkat", "kecamatan", "skor"] + [k for k, *_ in INDIKATOR] + \
           ["ruas", "km_total", "km_baik", "km_sedang", "km_rusak_ringan", "km_rusak_berat",
            "km_kondisi_kosong", "km_ekuivalen_rusak", "km_perlu_penanganan", "penduduk", "luas_km2",
            "estimasi_biaya_penuh"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in hasil["seimbang"]:
        w.writerow({**r, "skor": round(r["skor"], 4)})

with (D / "ruas_jalan_2022_lengkap.csv").open("w", newline="", encoding="utf-8-sig") as f:
    cols = ["kecamatan", "kode_ruas", "nama_ruas", "panjang_m", "lebar_m", "luas_m2", "kondisi_raw",
            "kondisi", "bobot", "km_ekuivalen_rusak", "biaya_perbaikan", "sumber_url"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in ruas:
        w.writerow({**r, "luas_m2": round(r["luas_m2"], 1),
                    "km_ekuivalen_rusak": round(r["km_ekuivalen_rusak"], 4),
                    "biaya_perbaikan": round(r["biaya_perbaikan"])})

with (D / "simulasi_anggaran.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["anggaran", "ruas_tertangani", "km_tertangani", "km_ekuivalen_tertangani", "cakupan_persen", "terpakai", "sisa", "kecamatan_teratas"])
    for s in sim:
        w.writerow([s["anggaran"], s["ruas"], s["km"], s["km_ekuivalen"], s["cakupan_persen"], s["terpakai"], s["sisa"],
                    "; ".join(f"{k} ({v} km)" for k, v in list(s["kecamatan"].items())[:5])])

json.dump({"indikator": [{"kode": k, "nama": n, "definisi": d, "arah": a} for k, n, d, a in INDIKATOR],
           "bobot_skenario": SKENARIO, "hasil_ranking": hasil, "simulasi": sim,
           "total_biaya_penuh": round(total_butuh),
           "asumsi_biaya": {"overlay_per_m2": round(BIAYA_OVERLAY), "rekonstruksi_per_m2": round(BIAYA_REKON),
                            "tebal_lapis_aus_m": T_ACWC, "tebal_fondasi_m": T_AGG, "densitas_ton_m3": RHO,
                            "sumber_harga": "HSP Bina Marga Edisi I 2026 Kota Semarang"}},
          (D / "semarangcheck_dataset.json").open("w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(f"\n{'#':>2} {'kecamatan':<16}{'skor':>7}{'km_ekv':>8}{'%kerus':>8}{'ekv/1000':>9}{'ekv/km2':>9}{'sebaran':>8}{'biaya(M)':>10}")
for r in hasil["seimbang"]:
    print(f"{r['peringkat']:>2} {r['kecamatan']:<16}{r['skor']:>7.3f}{r['km_ekuivalen_rusak']:>8.1f}"
          f"{r['i1_persen_kerusakan']*100:>7.1f}%{r['i2_kerusakan_per_1000_penduduk']:>9.3f}"
          f"{r['i3_kerusakan_per_km2']:>8.2f}{r['i4_sebaran_ruas_rusak']*100:>7.1f}%{r['estimasi_biaya_penuh']/1e9:>10.1f}")

print("\nstabilitas peringkat antar skenario (" + " / ".join(SKENARIO) + "):")
for k in kecs:
    r = [next(x for x in hasil[s] if x["kecamatan"] == k)["peringkat"] for s in SKENARIO]
    print(f"   {k:<16} {r[0]:>3} {r[1]:>3} {r[2]:>3}")

print(f"\ntotal biaya perbaikan seluruh ruas rusak: Rp {total_butuh/1e9:.1f} M")
print("simulasi anggaran:")
for s in sim:
    print(f"   Rp {s['anggaran']/1e9:>4.0f} M -> {s['ruas']:>3} ruas, {s['km']:>5.1f} km, "
          f"cakupan {s['cakupan_persen']:>5.1f}% kerusakan, sisa Rp {s['sisa']/1e6:>7.1f} juta")
