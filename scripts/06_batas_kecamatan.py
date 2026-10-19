"""Filter batas kecamatan Kota Semarang dari GADM 4.1 level 3 -> GeoJSON siap pakai untuk choropleth."""
import json, zipfile, pathlib, collections

RAW = pathlib.Path(r"D:\tim soto\data\raw")
OUT = pathlib.Path(r"D:\tim soto\data")
z = zipfile.ZipFile(RAW / "gadm41_IDN_3.json.zip")
gj = json.loads(z.read("gadm41_IDN_3.json"))

props = gj["features"][0]["properties"]
print("contoh properti:", props)
combos = collections.Counter((f["properties"].get("NAME_1"), f["properties"].get("NAME_2"))
                             for f in gj["features"])
print("\nkandidat 'Semarang':")
for k, v in combos.items():
    if k[1] and "semarang" in str(k[1]).lower():
        print("  ", k, v)

feats = [f for f in gj["features"]
         if str(f["properties"].get("NAME_2", "")).lower().replace(" ", "") == "kotasemarang"
         and str(f["properties"].get("NAME_1", "")).lower().replace(" ", "") == "jawatengah"]
print("\nkept:", len(feats))
for f in feats:
    print("   ", f["properties"].get("NAME_3"))

sem = {"type": "FeatureCollection",
       "metadata": {"sumber": "GADM 4.1 (gadm41_IDN_3), difilter Kota Semarang",
                    "level": "kecamatan", "catatan": "garis batas indikatif, bukan peta resmi"},
       "features": [{"type": "Feature",
                     "properties": {"kecamatan": f["properties"].get("NAME_3", "").title()},
                     "geometry": f["geometry"]} for f in feats]}
outp = OUT / "batas_kecamatan_semarang.geojson"
outp.write_text(json.dumps(sem, ensure_ascii=False), encoding="utf-8")
print("->", outp, f"{outp.stat().st_size/1024:.0f} KB")
