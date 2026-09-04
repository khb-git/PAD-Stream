#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json,numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
rows=list(csv.DictReader((ROOT/"SHA256SUMS.csv").open()))
for r in rows:
 p=ROOT/r["path"]
 assert p.exists(),p
 assert sha(p)==r["sha256"],p
s=json.load((ROOT/"PAD_Stream_V15F2_Summary.json").open())
assert s["status"]=="PASS"
v=pd.read_csv(ROOT/"PAD_Stream_V15F2_Validation_Matrix.csv")
assert v[v.group=="integrity"].passed.all()
assert v[v.group=="deployment"].passed.all()
p=np.load(ROOT/"PAD_Stream_V15F2_Predictions.npz",allow_pickle=True)
assert np.isfinite(p["predicted_difficulty_score"]).all()
assert not p["unsafe_without_exact_escalation"].any()
print(f"PASS: {len(rows)}/{len(rows)} checksums, {len(v[v.group=='integrity'])}/{len(v[v.group=='integrity'])} integrity, {len(v[v.group=='deployment'])}/{len(v[v.group=='deployment'])} deployment")
