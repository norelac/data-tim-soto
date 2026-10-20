import csv, pathlib

p = pathlib.Path(r"D:\tim soto\data\osm\ruas_osm_match.csv")
rs = [r for r in csv.DictReader(open(p, encoding="utf-8")) if r["metode"].startswith("mirip")]
print("total mirip:", len(rs))
for r in rs[:30]:
    print(f'{r["kecamatan"]:<18}|{r["nama_ruas"]:<32}|{r["osm_name"][:42]:<42}|'
          f'{r["metode"]:<12}|{r["rasio"]}')
