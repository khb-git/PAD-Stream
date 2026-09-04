#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
 return h.hexdigest()
rows=list(csv.DictReader((ROOT/"SHA256SUMS.csv").open()))
for row in rows:
 p=ROOT/row["path"]
 assert p.exists(),p
 assert sha(p)==row["sha256"],p
summary=json.loads((ROOT/"PAD_Stream_V15F1_Summary.json").read_text())
validation=pd.read_csv(ROOT/"PAD_Stream_V15F1_Validation_Matrix.csv")
assert summary["status"]=="PASS"
assert validation[validation.group=="integrity"].passed.all()
assert validation[validation.group=="deployment"].passed.all()
p=np.load(ROOT/"PAD_Stream_V15F1_Predictions.npz",allow_pickle=False)
assert np.isfinite(p["screened_gas_cut"]).all()
assert np.all((p["screened_gas_cut"]>=0)&(p["screened_gas_cut"]<=1))
assert np.all(np.diff(p["monotone_breakthrough_hazard"])>=-1e-12)
print(f"PASS: {len(rows)}/{len(rows)} checksums; integrity {summary['integrity_gates_passed']}/{summary['integrity_gates_total']}; deployment {summary['deployment_gates_passed']}/{summary['deployment_gates_total']}")
