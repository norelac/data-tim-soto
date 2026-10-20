# Riset: Pencocokan Ruas Jalan ke OpenStreetMap

Tanggal: 20 Oktober 2026
Tujuan: menguji apakah 1.012 ruas jalan (data 2022, tanpa koordinat) bisa diberi geometri
agar tampil sebagai peta garis per ruas.

## Kesimpulan singkat

**Bisa, tapi belum cukup untuk dijadikan tampilan utama.**

- 664 dari 1.012 ruas (65,6%) berhasil dicocokkan ke nama jalan OSM.
- Hanya 402 ruas (39,7%) yang panjangnya wajar (rasio OSM/dataset 0,6–1,6).
- Panjang yang wajar itu setara **243,5 km dari 839,9 km** jaringan (29%).
- Median rasio panjang = **1,00** → pada ruas yang cocok, kedua sumber mengukur hal yang sama.

Artinya: peta garis per ruas hanya akan menampilkan 29% jaringan. Terlalu bolong untuk
dijadikan visual utama. **Choropleth 16 kecamatan tetap jadi peta utama**; garis OSM
hanya layak sebagai lapisan tambahan berlabel.

## Metode

1. Ambil jalan ber-nama dari OSM per kecamatan (Overpass API).
   Query: `way["highway"]["name"]` di bbox tiap kecamatan, 16 query.
   Hasil: 23.152 way bernama.
2. Normalisasi nama kedua sisi:
   - buang "Jl.", "Jln.", "Jalan"
   - angka romawi → arab ("Tanjungsari V" → "tanjungsari5")
   - buang spasi & tanda baca ("Tanjung Sari" = "Tanjungsari")
   - singkatan: Kp→Kampung, H→Haji, Kh→Kiai, Gg→Gang
3. Tahap pencocokan: persis → induk (nama tanpa nomor vs pecahan I, II, …) → mirip (≥0,94,
   wajib konsisten nomor).
4. Panjang dihitung haversine dari geometri OSM, dibandingkan dengan kolom `panjang` dataset.
5. Kualitas: `penuh` (0,6–1,6×), `sebagian` (<0,6×), `berlebih` (>1,6×).

## Hasil per kecamatan

| Kecamatan | Cocok | Penuh | Km dataset |
|---|---|---|---|
| Gajah Mungkur | 80,5% | 61,0% | 31,0 |
| Semarang Tengah | 82,1% | 55,8% | 53,4 |
| Banyumanik | 84,8% | 51,8% | 67,3 |
| Candisari | 82,8% | 51,7% | 22,1 |
| Gayamsari | 55,2% | 51,7% | 25,2 |
| Semarang Selatan | 72,1% | 50,0% | 43,9 |
| Semarang Barat | 76,8% | 46,3% | 64,9 |
| Semarang Utara | 60,0% | 38,3% | 39,2 |
| Semarang Timur | 63,0% | 37,0% | 32,2 |
| Tembalang | 60,4% | 32,8% | 98,3 |
| Pedurungan | 64,0% | 32,0% | 66,3 |
| Ngaliyan | 56,8% | 29,5% | 52,5 |
| Genuk | 38,1% | 26,2% | 66,2 |
| Gunung Pati | 46,4% | 21,4% | 83,5 |
| Tugu | 25,0% | 12,5% | 18,0 |
| Mijen | 30,0% | 2,5% | 76,0 |

Pola: kecamatan tengah (jalan lama, sudah lama dipetakan) tinggi. Kecamatan pinggir
(Mijen, Tugu, Gunung Pati, Genuk) rendah — banyak perumahan baru dan jalan lingkungan
yang belum masuk OSM, dan dataset menomori jalan kecil (1, 2, 3) yang di OSM digabung
jadi satu nama atau tidak ada.

## Kenapa tidak semua cocok

1. Nama di dataset adalah nama lokal/administratif, bukan nama OSM. Contoh: `Jl. Potrosari BD`.
2. Satu jalan di dataset dipecah jadi beberapa nomor; di OSM jadi satu garis (atau sebaliknya).
3. Jalan lingkungan/perumahan baru belum dipetakan OSM.
4. Salah ejaan di salah satu sisi (`Potosari` vs `Potrosari`).

## Yang sudah tervalidasi

- Median rasio panjang 1,00 → data 2022 dan OSM tidak saling bertentangan.
- 311 ruas (46,8% dari yang cocok) panjangnya dalam ±25% → kualitas geometri baik.
- 110 km ruas berkondisi sedang/rusak berhasil dipetakan.

## Konsekuensi untuk produk

| Keputusan | Alasan |
|---|---|
| Peta utama = choropleth 16 kecamatan | data lengkap 100%, tidak ada lubang |
| Peta garis = fitur sekunder, berlabel "ruas yang berhasil dipetakan (29% jaringan)" | jujur, tetap menunjukkan kedalaman data |
| Jangan klaim "peta seluruh jalan kota" | hanya 29% yang wajar digambar |
| Atribusi wajib di footer | "© OpenStreetMap contributors" (lisensi ODbL) |

Kalau mau menaikkan cakupan: rekonsiliasi manual 1.012 nama (cocokkan satu per satu dengan
daftar nama OSM) memakan 3–4 jam dan mungkin mencapai 75–85%. Nilainya untuk lomba kecil,
karena 45% bobot ada di fungsionalitas + desain, bukan kelengkapan peta.

## Berkas

| Berkas | Isi |
|---|---|
| `data/osm/ruas_osm_match.csv` | 1.012 baris: hasil cocok, panjang OSM, rasio, kualitas |
| `data/osm/ruas_geometri.geojson` | 402 ruas `penuh` sebagai MultiLineString (siap Leaflet) |
| `data/osm/laporan_osm.txt` | ringkasan angka |
| `data/osm/raw/*.json` | jalan OSM mentah per kecamatan (23.152 way) |
| `scripts/12_fetch_osm_roads.py` | pengunduh (Overpass, paralel 3) |
| `scripts/13_match_osm.py` | pencocokan + hitung panjang + ekspor |
| `scripts/14_diag_names.py` | diagnosis nama yang tidak cocok |
| `scripts/15_check_mirip.py` | pemeriksaan hasil fuzzy |

Lisensi data OSM: ODbL 1.0 — wajib atribusi "© OpenStreetMap contributors".
