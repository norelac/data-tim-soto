"""Susun laporan riset data SemarangCheck -> Word (.docx)."""
import csv, json, pathlib, datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = pathlib.Path(r"D:\tim soto")
D = ROOT / "data"
ds = json.loads((D / "semarangcheck_dataset.json").read_text(encoding="utf-8"))
ind = list(csv.DictReader((D / "indikator_kecamatan.csv").open(encoding="utf-8-sig")))
ruas = list(csv.DictReader((D / "ruas_jalan_2022.csv").open(encoding="utf-8-sig")))
pend = list(csv.DictReader((D / "penduduk_kecamatan_2025.csv").open(encoding="utf-8-sig")))
sumber = json.loads((D / "sumber_ruas_jalan.json").read_text(encoding="utf-8"))
sim = ds["simulasi"]
rank = {k: ds["hasil_ranking"][k] for k in ds["hasil_ranking"]}

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10.5)
for s in doc.sections:
    s.top_margin = s.bottom_margin = Cm(2)
    s.left_margin = s.right_margin = Cm(2.2)

def h(txt, lvl=1):
    doc.add_heading(txt, level=lvl)

def p(txt, bold=False, italic=False):
    par = doc.add_paragraph()
    r = par.add_run(txt)
    r.bold = bold
    r.italic = italic
    return par

def bullet(txt):
    doc.add_paragraph(txt, style="List Bullet")

def add_link(par, url, text=None, size=9, bold=False):
    """Sisipkan hyperlink ke paragraf."""
    r_id = par.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F4E79")
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(size * 2)))
    rPr.append(color)
    rPr.append(u)
    rPr.append(sz)
    if bold:
        b = OxmlElement("w:b")
        rPr.append(b)
    run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text or url
    run.append(t)
    link.append(run)
    par._p.append(link)
    return par

def link_par(url, text=None, size=9):
    return add_link(doc.add_paragraph(), url, text, size)

def table(headers, rows, width=None):
    """rows: nilai biasa, atau ('LINK', teks, url) untuk hyperlink."""
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, x in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(str(x)).bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9)
    for r in rows:
        cells = t.add_row().cells
        for i, x in enumerate(r):
            cells[i].text = ""
            par = cells[i].paragraphs[0]
            if isinstance(x, tuple) and x and x[0] == "LINK":
                add_link(par, x[2], x[1], size=8)
            else:
                run = par.add_run(str(x))
                run.font.size = Pt(9)
    doc.add_paragraph()
    return t

def rp(x):
    return f"Rp {x/1e9:,.1f} M".replace(",", ".") if x >= 1e9 else f"Rp {x/1e6:,.0f} juta".replace(",", ".")

# ================= JUDUL =================
ti = doc.add_heading("SemarangCheck — Laporan Riset Data", level=0)
p(f"Platform analisis data publik untuk menentukan prioritas penanganan infrastruktur jalan di Kota Semarang", italic=True)
p(f"Status: riset data awal (data nyata sudah ditarik & dihitung) · Disusun {datetime.date.today():%d %B %Y}")

# ================= 1 =================
h("1. Ringkasan Eksekutif", 1)
p("SemarangCheck mengubah data publik yang tersebar menjadi urutan prioritas penanganan jalan antar-kecamatan "
  "yang dapat ditelusuri kembali ke sumbernya, dan menunjukkan apa yang bisa dicapai dengan anggaran terbatas.")
bullet(f"Data yang dipakai nyata dan sudah diverifikasi: {len(ruas)} ruas jalan dari 16 kecamatan (dataset resmi tahun 2022), "
       f"ditambah jumlah penduduk dan luas wilayah 16 kecamatan (BPS, 2025) dan harga satuan pekerjaan jalan resmi (HSP Bina Marga 2026 Kota Semarang).")
bullet(f"Total jalan yang tercatat: {sum(float(r['panjang_m']) for r in ruas)/1000:,.1f} km. "
       f"Kondisi: 513 ruas baik, 449 sedang, 40 rusak ringan, 4 rusak berat, 6 ruas tanpa keterangan kondisi.")
bullet(f"Perkiraan biaya memperbaiki seluruh ruas rusak ringan + rusak berat: {rp(ds['total_biaya_penuh'])} "
       "(belum termasuk jalan berkondisi sedang).")
bullet("Simulasi anggaran menunjukkan pengeluaran yang efisien: Rp 10 M menangani 55% kerusakan, "
       "Rp 15 M menangani 74% kerusakan — karena ruas dipilih berdasarkan kerusakan tertinggi per rupiah.")
bullet("Yang belum ada: data kondisi jalan setelah 2022, data tren antar tahun, koordinat titik ruas, dan data penerangan jalan (butuh izin akses).")

# ================= 2 =================
h("2. Rumusan Ide Final", 1)
p("Sub-tema: Data-Driven Decision Support", bold=True)
p("Pengguna utama: staf perencana di Bappelitbangda, Dinas PU Bina Marga, dan kecamatan yang menyusun usulan prioritas. "
  "Penerima manfaat: warga Kota Semarang. Produk ini tidak menggantikan kewenangan pemerintah; ia menyediakan dasar "
  "perhitungan yang terbuka untuk bahan pertimbangan.")
p("Fitur inti (enam):")
for x in ["Perbandingan 16 kecamatan dengan indikator yang sama dan seragam.",
          "Ranking prioritas berbasis SAW (Simple Additive Weighting) dengan bobot yang bisa diubah pengguna.",
          "Penjelasan skor: kontribusi tiap indikator untuk setiap kecamatan, bukan angka tunggal tanpa asal-usul.",
          "Analisis sensitivitas: empat skenario bobot untuk melihat seberapa stabil urutan prioritas.",
          "Simulasi anggaran tingkat ruas: daftar ruas yang ditangani untuk batas anggaran tertentu, beserta dampaknya.",
          "Peta choropleth 16 kecamatan, ekspor laporan (Word/PDF/CSV), dan halaman sumber data."]:
    bullet(x)
p("Yang secara sadar tidak dikerjakan: kanal pengaduan warga, prediksi (tanpa machine learning), "
  "ranking 'kecamatan terburuk' (framing yang dipakai adalah prioritas penanganan), dan multi-layanan publik "
  "(data sekolah/puskesmas/sampah tidak tersedia sampai tingkat kecamatan).")

# ================= 3 =================
h("3. Data: Hasil Verifikasi", 1)
p("Seluruh data pada laporan ini sudah diunduh dan diolah. Kolom 'Sumber' memuat tautan yang bisa diklik untuk melihat data aslinya.")
PORTAL = "https://data.jatengprov.go.id/dataset/?q=ruas+jalan+kecamatan+kota+semarang"
BPSURL = ("https://semarangkota.bps.go.id/id/statistics-table/2/NDgjMg%3D%3D/"
          "luas-wilayah--jumlah-penduduk--dan-kepadatan-penduduk.html")
HSPURL = ("https://data.jatengprov.go.id/dataset/"
          "harga-satuan-pekerjaan-hsp-konstruksi-bidang-bina-marga-edisi-ke-i-tahun-2026-kota-semarang")
GADMURL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_IDN_3.json.zip"
table(["Kebutuhan data", "Sumber (klik)", "Level", "Tahun", "Format", "Status"],
      [["Kondisi ruas jalan (panjang, lebar, kondisi)", ("LINK", "Portal Data Jawa Tengah — 16 paket 'Daftar Ruas Jalan Kec ...'", PORTAL), "Kecamatan & ruas", "2022", "Google Sheets & XLSX", "Tersedia & terunduh"],
       ["Jumlah penduduk & luas wilayah", ("LINK", "BPS Kota Semarang — Jumlah Penduduk Menurut Kecamatan", BPSURL), "Kecamatan", "2025", "HTML (JSON tertanam)", "Tersedia & terunduh"],
       ["Harga satuan pekerjaan jalan", ("LINK", "HSP Konstruksi Bina Marga Edisi I 2026 Kota Semarang", HSPURL), "Item pekerjaan", "2026", "CSV (111 item)", "Tersedia & terunduh"],
       ["Garis batas kecamatan (peta)", ("LINK", "GADM 4.1 level 3 — Indonesia (difilter Kota Semarang)", GADMURL), "Kecamatan", "Rilis 2022", "GeoJSON", "Tersedia (16 poligon)"],
       ["Titik lampu jalan (PJU) per kecamatan", "Portal Data Jawa Tengah (berkas Google Drive, minta izin akses)", "Kecamatan", "2022", "XLSX", "Tidak dapat diakses (401)"],
       ["Data kondisi jalan setelah 2022", "—", "—", "—", "—", "Tidak tersedia publik"],
       ["Koordinat titik/garis ruas jalan", "—", "—", "—", "—", "Tidak tersedia (hanya kode & nama ruas)"],
       ["Realisasi anggaran jalan per kecamatan", "—", "—", "—", "—", "Tidak tersedia (yang ada hanya belanja operasional kecamatan)"]])

h("3.1 Tautan sumber data", 2)
p("Empat tautan utama. Tautan rinci untuk 16 dataset ruas jalan ada di Lampiran A.")
for teks, url in [
    ("Pencarian dataset ruas jalan Kota Semarang di Portal Data Jawa Tengah", PORTAL),
    ("Tabel jumlah penduduk, luas wilayah, dan kepadatan penduduk per kecamatan (BPS Kota Semarang, 2025)", BPSURL),
    ("Halaman dataset HSP Bina Marga 2026 Kota Semarang (harga satuan pekerjaan jalan)", HSPURL),
    ("Unduhan batas kecamatan (GADM 4.1 level 3)", GADMURL),
    ("Antarmuka API portal data (untuk mengambil ulang data secara terprogram)",
     "https://data.jatengprov.go.id/api/3/action/package_search?q=ruas+jalan+kecamatan+kota+semarang")]:
    par = doc.add_paragraph(style="List Bullet")
    par.add_run(teks + ": ").font.size = Pt(9.5)
    add_link(par, url, url, size=9.5)
p("Berkas mentah hasil unduhan tersimpan di folder data\\raw, sehingga hasil bisa diperiksa tanpa internet.", italic=True)

p("Catatan kualitas data (temuan saat pengolahan):", bold=True)
bullet("Format tiap kecamatan tidak seragam: sebagian file punya kolom 'No.', sebagian tidak; nilai panjang kadang berupa teks '4,035 m', "
       "kadang berupa angka '633'. Diperlukan normalisasi. Ini menjadi bagian metode, bukan disembunyikan.")
bullet("Hanya 4 ruas berstatus 'Rusak Berat' dari 1.012 ruas; 6 ruas tidak mencantumkan kondisi (1,9 km). "
       "Karena itu bobot keparahan (rusak berat 1,0 / rusak ringan 0,6 / sedang 0,3) didominasi oleh rusak ringan dan sedang.")
bullet("Cross-check berhasil: jumlah penduduk 16 kecamatan = 1.722.421 jiwa, sama persis dengan angka Kota Semarang pada tabel BPS yang sama. "
       "Ini memvalidasi proses ekstraksi data penduduk.")

# ================= 4 =================
h("4. Metode Perhitungan", 1)
h("4.1 Indikator", 2)
table(["Indikator", "Definisi operasional"],
      [[i["nama"], i["definisi"]] for i in ds["indikator"]])
p("Catatan: penghitungan rusak dan sedang memakai km ekuivalen, yaitu panjang ruas dikalikan bobot keparahan. "
  "Tujuannya agar 1 km rusak berat tidak diperlakukan sama dengan 1 km berkondisi sedang.")
h("4.2 Normalisasi dan skor (SAW)", 2)
p("Setiap indikator dinormalisasi min-max ke rentang 0–1 antar kecamatan (nilai 0,5 bila seluruh kecamatan bernilai sama), "
  "lalu dikalikan bobot dan dijumlahkan: Vi = Σ wj · rij. Skor tertinggi mendapat peringkat 1.")
h("4.3 Bobot dan analisis sensitivitas", 2)
p("Bobot belum ditetapkan secara final; empat skenario diuji untuk melihat ketahanan urutan prioritas.")
table(["Skenario", "Maksud"] + [i["nama"] for i in ds["indikator"]],
      [[n, m] + [f"{ds['bobot_skenario'][n][i['kode']]:.2f}" for i in ds["indikator"]]
       for n, m in [("seimbang", "semua indikator setara"),
                    ("fokus_volume", "utamakan jumlah kerusakan absolut"),
                    ("fokus_keparahan", "utamakan tingkat intensitas & sebaran kerusakan"),
                    ("fokus_dampak_warga", "utamakan jumlah warga terdampak")]])

# ================= 5 =================
h("5. Hasil: Kondisi Jalan per Kecamatan", 1)
table(["Kecamatan", "Ruas", "Total km", "Baik km", "Sedang km", "Rusak ringan km", "Rusak berat km", "Km ekuivalen rusak", "Penduduk (jiwa)"],
      [[r["kecamatan"], r["ruas"], f"{float(r['km_total']):,.1f}", f"{float(r['km_baik']):,.1f}",
        f"{float(r['km_sedang']):,.1f}", f"{float(r['km_rusak_ringan']):,.1f}", f"{float(r['km_rusak_berat']):,.1f}",
        f"{float(r['km_ekuivalen_rusak']):,.1f}", f"{int(float(r['penduduk'])):,}".replace(",", ".")] for r in ind])

h("6. Hasil: Ranking Prioritas", 1)
p("Ranking skenario 'seimbang'. Skor = jumlah indikator ternormalisasi dikali bobot.", italic=True)
table(["Peringkat", "Kecamatan", "Skor", "Intensitas kerusakan", "Km ekuivalen rusak", "Sebaran ruas rusak", "Estimasi biaya penuh"],
      [[r["peringkat"], r["kecamatan"], f"{float(r['skor']):.3f}",
        f"{float(r['i1_persen_kerusakan'])*100:.1f}%", f"{float(r['km_ekuivalen_rusak']):,.1f}",
        f"{float(r['i4_sebaran_ruas_rusak'])*100:.1f}%", rp(float(r["estimasi_biaya_penuh"]))] for r in ind])

h("6.1 Ketahanan Peringkat antar Skenario", 2)
p("Tabel berikut menunjukkan peringkat setiap kecamatan pada empat skenario bobot. "
  "Tiga teratas (Mijen, Semarang Barat, Semarang Utara/Ngaliyan) relatif stabil.")
kecs = [r["kecamatan"] for r in ind]
table(["Kecamatan"] + [f"{n} ({i+1})" for i, n in enumerate(rank)],
      [[k] + [next(x["peringkat"] for x in rank[n] if x["kecamatan"] == k) for n in rank] for k in kecs])
p("Interpretasi: kecamatan yang peringkatnya bergerak tajam antar skenario (mis. Tugu, Gunung Pati) adalah kecamatan yang "
  "kebutuhannya sangat bergantung pada definisi prioritas yang dipilih. Ini informasi kebijakan, bukan kelemahan sistem.")

# ================= 7 =================
h("7. Hasil: Simulasi Anggaran", 1)
p("Ruas rusak diurutkan berdasarkan manfaat per rupiah (km ekuivalen kerusakan dibagi perkiraan biaya perbaikan), "
  "lalu dipilih sampai batas anggaran habis. Pendekatan ini dipilih agar hasilnya dapat dijelaskan, bukan kotak hitam.")
table(["Batas anggaran", "Ruas ditangani", "Km ditangani", "Cakupan kerusakan", "Sisa anggaran", "Kecamatan terbanyak"],
      [[rp(s["anggaran"]), s["ruas"], f"{s['km']:.1f}", f"{s['cakupan_persen']:.1f}%", rp(s["sisa"]),
        "; ".join(list(s["kecamatan"])[:3])] for s in sim])
p(f"Untuk membandingkan: menangani seluruh ruas rusak (ringan + berat) diperkirakan membutuhkan {rp(ds['total_biaya_penuh'])}. "
  "Jalan berkondisi sedang tidak dihitung dalam estimasi ini karena penanganannya bersifat pemeliharaan berkala, bukan perbaikan kerusakan.")

h("7.1 Asumsi Biaya (dinyatakan terbuka)", 2)
a = ds["asumsi_biaya"]
table(["Komponen", "Nilai"],
      [["Harga satuan pekerjaan", a["sumber_harga"]],
       ["Biaya penanganan rusak ringan (overlay) per m2", f"Rp {a['overlay_per_m2']:,.0f}".replace(",", ".")],
       ["Biaya penanganan rusak berat (rekonstruksi) per m2", f"Rp {a['rekonstruksi_per_m2']:,.0f}".replace(",", ".")],
       ["Tebal lapis aus / fondasi agregat / galian", f"{a['tebal_lapis_aus_m']*100:.0f} cm / {a['tebal_fondasi_m']*100:.0f} cm / 20 cm"],
       ["Densitas campuran beraspal", f"{a['densitas_ton_m3']} ton/m3"],
       ["Lapis resap pengikat", "0,5 liter/m2"]])
p("Biaya dihitung dari luas ruas (panjang x lebar) dikali harga satuan. Karena harga satuan berasal dari tahun 2026 "
  "sedangkan kondisi jalan dari tahun 2022, angka ini adalah estimasi indikatif untuk perbandingan, bukan rencana anggaran resmi.", italic=True)

# ================= 8 =================
h("8. Peta dan Batas Wilayah", 1)
p("Portal data tidak lagi menyediakan berkas batas wilayah Kota Semarang (tautan mengarah ke domain yang sudah tidak aktif). "
  "Sebagai gantinya, batas 16 kecamatan diambil dari GADM 4.1 dan disimpan sebagai GeoJSON berukuran 14 KB, "
  "siap dipakai untuk peta choropleth. Peta titik per ruas jalan tidak mungkin dibuat karena dataset tidak memuat koordinat.")

# ================= 9 =================
h("9. Keterbatasan dan Hal yang Harus Dibuktikan", 1)
bullet("Data kondisi jalan berasal dari tahun 2022 — sudah berumur beberapa tahun. Situs harus menampilkan tahun data pada setiap angka, "
       "bukan menyiratkan data terkini.")
bullet("Tidak ada data tren: dataset hanya tersedia untuk satu tahun (hasil pemeriksaan 17 judul dataset, semuanya 2022). "
       "Fitur grafik tren tidak dapat dibangun dari data publik yang ada.")
bullet("Tidak ada koordinat ruas, sehingga peta hanya dapat berupa choropleth per kecamatan.")
bullet("Estimasi biaya memakai asumsi teknis (tebal lapis, densitas, jenis penanganan). Asumsi ini harus diuji sensitivitasnya "
       "dan ditampilkan terbuka pada halaman metode.")
bullet("Norma keparahan didominasi rusak ringan/sedang karena rusak berat hanya 4 ruas. Perlu kehati-hatian dalam menyimpulkan "
       "'tingkat keparahan' kecamatan.")
bullet("Ranking bersifat relatif antar kecamatan, bukan penilaian mutu absolut. Perubahan bobot dapat mengubah urutan; "
       "karena itu analisis sensitivitas wajib ditampilkan, bukan opsional.")
bullet("Belum ada validasi pengguna. Perlu wawancara dengan calon pengguna (staf perencana, jurnalis/LSM) sebelum mengklaim manfaat.")

# ================= 10 =================
h("10. Langkah Berikutnya", 1)
for i, x in enumerate([
    "Wawancara 3-5 calon pengguna (kecamatan, dinas/Bappeda, jurnalis/LSM) untuk memvalidasi masalah dan mencatat kutipan.",
    "Tetapkan bobot indikator bersama calon pengguna (mis. melalui perbandingan berpasangan/AHP sederhana) sebagai pengganti bobot contoh.",
    "Bangun MVP: ranking + penjelasan skor + simulasi anggaran + ekspor laporan. Peta choropleth menyusul.",
    "Uji ulang angka di antarmuka terhadap berkas sumber (setiap angka harus sama dengan hasil hitung ulang).",
    "Susun halaman sumber data: tautan dataset, tanggal akses, tahun data, definisi indikator, dan seluruh asumsi biaya.",
    "Dokumentasikan batasan pada laporan dan pada situs, agar hasil tidak ditafsirkan sebagai keputusan resmi pemerintah."], 1):
    doc.add_paragraph(x, style="List Number")

# ================= 11 =================
h("11. Berkas yang Dihasilkan", 1)
table(["Berkas", "Isi"],
      [["SemarangCheck_Laporan_Riset_Data.docx", "laporan ini"],
       ["SemarangCheck_Data.xlsx", f"seluruh angka dalam bentuk tabel Excel: sumber data (bertanda tautan), indikator, "
                                   f"ruas jalan ({len(ruas)} baris), simulasi anggaran, asumsi biaya"],
       ["data/ruas_jalan_2022.csv", f"{len(ruas)} baris data ruas jalan (16 kecamatan), sudah dinormalisasi"],
       ["data/penduduk_kecamatan_2025.csv", "Penduduk, luas wilayah, kepadatan per kecamatan (BPS 2025)"],
       ["data/indikator_kecamatan.csv", "Indikator per kecamatan + skor & peringkat (skenario seimbang)"],
       ["data/simulasi_anggaran.csv", "Hasil simulasi anggaran pada beberapa batas anggaran"],
       ["data/semarangcheck_dataset.json", "Seluruh hasil hitung dalam satu berkas (siap dipakai aplikasi)"],
       ["data/batas_kecamatan_semarang.geojson", "Poligon 16 kecamatan untuk peta choropleth"],
       ["data/raw/", "Berkas mentah: 16 berkas jalan, HSP 2026, GADM"],
       ["scripts/", "Skrip pengambilan dan pengolahan data (dapat dijalankan ulang)"]])
p("Skrip dapat dijalankan ulang dengan urutan: 01_fetch_jalan.py, 04_fetch_penduduk.py, 05_fetch_hsp_batas.py, "
  "06_batas_kecamatan.py, 08_build_indicators.py, 09_build_docx.py.", italic=True)

out = ROOT / "SemarangCheck_Laporan_Riset_Data.docx"

# ================= LAMPIRAN A =================
doc.add_page_break()
h("Lampiran A. Tautan 16 Dataset Ruas Jalan (data asli)", 1)
p("Setiap kecamatan punya satu berkas tersendiri. Klik tautan pada kolom 'Berkas sumber' untuk membuka data aslinya, "
  "lalu bandingkan dengan hasil olahan pada laporan ini. Salinan mentah juga tersimpan di folder data\\raw.")
table(["Kecamatan", "Judul dataset", "Berkas sumber (klik)", "Tipe", "Ruas"],
      [[s["kecamatan"], s["judul"],
        ("LINK", "buka berkas", s["resource_url"]),
        "Google Sheets" if s["tipe_file"] == "sheets" else "Google Drive (xlsx)",
        s["baris"]] for s in sumber])

# ================= LAMPIRAN B =================
h("Lampiran B. Cara Memeriksa Data Asli", 1)
for x in [
    "Buka tautan dataset jalan (Lampiran A). Cocokkan panjang ruas dan kondisi dengan berkas data/ruas_jalan_2022.csv.",
    "Buka tautan BPS, cocokkan jumlah penduduk per kecamatan dengan berkas data/penduduk_kecamatan_2025.csv. "
    "Jumlah 16 kecamatan harus sama dengan angka Kota Semarang, yaitu 1.722.421 jiwa.",
    "Buka tautan HSP, cocokkan harga satuan yang dipakai (kode C.1, E.1, F.1, F.24, F.27) dengan berkas data/raw/hsp_bina_marga_2026_semarang.csv.",
    "Hitung ulang satu kecamatan secara manual: skor = Σ (bobot × nilai indikator ternormalisasi). Hasilnya harus sama dengan kolom 'skor' pada tabel ranking.",
    "Periksa langsung angka petunjuk pada peta: jumlah poligon harus 16, sesuai berkas data/batas_kecamatan_semarang.geojson."]:
    doc.add_paragraph(x, style="List Number")

p("Catatan tanggal akses: seluruh berkas diunduh pada sesi riset ini. Karena portal data pemerintah dapat berubah atau "
  "mengalami gangguan, salinan mentah pada folder data\\raw adalah rujukan yang dipakai untuk perhitungan di laporan ini.",
  italic=True)

try:
    doc.save(out)
    saved = out
except PermissionError:
    saved = out.with_name(out.stem + "_baru" + out.suffix)
    doc.save(saved)
    print("PERINGATAN: berkas utama sedang dibuka (Word). Disimpan sebagai:", saved.name)
print("saved:", saved)
