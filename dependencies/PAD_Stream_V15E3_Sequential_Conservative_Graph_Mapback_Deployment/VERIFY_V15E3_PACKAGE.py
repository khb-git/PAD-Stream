#!/usr/bin/env python3
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
checks=json.loads((ROOT/"SHA256SUMS.json").read_text())
for rel,expected in checks.items():
 p=ROOT/rel
 assert p.exists(), rel
 assert sha(p)==expected, rel
summary=json.loads((ROOT/"PAD_Stream_V15E3_Summary.json").read_text())
validation=pd.read_csv(ROOT/"PAD_Stream_V15E3_Validation_Matrix.csv")
assert summary["status"] in {"PASS","AUDIT_COMPLETE_DEPLOYMENT_NOT_APPROVED"}
assert validation[validation.group=="integrity"].passed.all()
fields=np.load(ROOT/"PAD_Stream_V15E3_Rollout_Fields.npz",allow_pickle=False)
assert np.isfinite(fields["accepted_rmse"]).all()
print(f"PASS: {len(checks)}/{len(checks)} checksums; integrity {summary['integrity_gates_passed']}/{summary['integrity_gates_total']}; deployment {summary['deployment_gates_passed']}/{summary['deployment_gates_total']}")
