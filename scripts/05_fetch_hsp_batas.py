import requests, zipfile, io, pathlib, json, re

RAW = pathlib.Path(r"D:\tim soto\data\raw")
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SemarangCheck-research/1.0"

# 1. HSP Bina Marga (harga satuan) - CSV resmi
hsp_url = ("https://data.jatengprov.go.id/dataset/6f733bc7-882b-4709-84d2-36d1dd9a77f6/"
           "resource/d85b61b7-89ad-4e67-b1bd-a4055e7439f8/download/kota.semarang.csv")
p = RAW / "hsp_bina_marga_2026_semarang.csv"
if not p.exists():
    r = S.get(hsp_url, timeout=120)
    r.raise_for_status()
    p.write_bytes(r.content)
print("HSP:", p.name, p.stat().st_size, "bytes")

# 2. batas kecamatan: coba geoBoundaries, lalu GADM
def try_bytes(url, **kw):
    try:
        r = S.get(url, timeout=120, **kw)
        print("   ", url[:70], r.status_code, len(r.content), r.headers.get("content-type"))
        return r.content if r.status_code == 200 else None
    except Exception as e:
        print("   ", url[:70], "ERR", type(e).__name__)
        return None

print("geoBoundaries api:")
try_bytes("https://www.geoboundaries.org/api/current/gbOpen/IDN/ADM2/")
print("GADM zip ADM3 (kecamatan):")
b = try_bytes("https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_IDN_3.json.zip")
if b:
    (RAW / "gadm41_IDN_3.json.zip").write_bytes(b)
    z = zipfile.ZipFile(io.BytesIO(b))
    print("    isi zip:", z.namelist())
