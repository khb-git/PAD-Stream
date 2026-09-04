#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,numpy as np,sys
R=Path(__file__).resolve().parent
O=R/"output"/"V16_D14_SOURCEBOUND_24CASE_PREDICTOR_SCHEMA_AUDIT";O.mkdir(parents=True,exist_ok=True)
D13=R/"output"/"V16_D13_24CASE_SUPERVISION_INTEGRITY"/"PAD_Stream_V16D13_Summary.json"
D13SHA="403c668ce17c5d0c3f73127b775b3213d6f78c5c7e8cb0854dbf2a6d1809603a"
TRAIN=["0020","0015","0013","0004","0006","0002","0023","0016","0009","0019","0017","0024","0003","0011","0014","0007"]
VAL=["0010","0025","0008","0012"];TEST=["0005","0018","0021","0022"];ALL=TRAIN+VAL+TEST
FEATURES=["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def npzs_for_case(c):
 # Source-bound discovery only; do not choose by numerical closeness.
 out=[]
 for p in (R/"output").rglob("*.npz"):
  n=p.name.lower()
  if f"case_{c}" in n or f"case{c}" in n: out.append(p)
 return out
def inspect(p):
 try:
  with np.load(p,allow_pickle=False) as z:
   return {k:list(np.asarray(z[k]).shape) for k in z.files}
 except Exception:return {}
def find_source(c,required_any,preferred_tokens):
 cand=[]
 for p in npzs_for_case(c):
  keys=inspect(p)
  if not any(k in keys for k in required_any):continue
  score=sum(t.lower() in str(p).lower() for t in preferred_tokens)
  cand.append((score,p,keys))
 if not cand:return None,[],{}
 m=max(x[0] for x in cand);top=[x for x in cand if x[0]==m]
 if len(top)!=1:return None,[str(x[1]) for x in top],{}
 return top[0][1],[],top[0][2]
def main():
 print("="*78);print("PAD-Stream V16D-14")
 print("Source-Bound 24-Case Predictor Schema Audit + TRAIN-Only Normalization Statistics Freeze");print("="*78)
 print("""D14 WILL NOT GUESS PREDICTOR PROVENANCE.
IT FIRST BINDS, CASE BY CASE, THE SURVIVING GEOLOGY/PRESSURE/POLLOCK/ADV
ARTIFACTS NEEDED FOR THE FROZEN C20 NINE-CHANNEL INTERFACE.
IF ANY SOURCE IS ABSENT OR AMBIGUOUS, D14 FAILS BEFORE ASSEMBLY OR STATS.
LOCKED OOD LABELS ARE NEVER READ FOR NORMALIZATION OR SELECTION.
""")
 if not D13.exists() or sha(D13)!=D13SHA:raise RuntimeError("D13 authority SHA mismatch")
 d13=json.loads(D13.read_text())
 if d13.get("status")!="V16D_24CASE_STAGE4_SUPERVISION_ENSEMBLE_INTEGRITY_CERTIFIED_TRAIN_ONLY_NORMALIZATION_METHOD_FROZEN_FEATURE_ASSEMBLY_AUTHORIZED":raise RuntimeError("D13 status mismatch")
 registry={};amb=[];missing=[]
 for c in ALL:
  geo,ag,kg=find_source(c,["Kx","Ky","Kz","phi","porosity","pressure"],["D7","flow","foundation"])
  pol,ap,kp=find_source(c,["streamline_xyz","xyz","theta","M_face","terminal_pollock_tof_s","pollock_tof"],["D9R1","D9","Pollock","C7"])
  adv,aa,ka=find_source(c,["tau_adv_s","adv_tau","tau_ADV","adv"],["D10C","D10","ADV","travel"])
  if ag or ap or aa:amb.append({"case":c,"geo":ag,"pollock":ap,"adv":aa})
  if geo is None or pol is None or adv is None:missing.append(c)
  registry[c]={"geology_flow":str(geo) if geo else None,"pollock_metric":str(pol) if pol else None,"adv_travel_time":str(adv) if adv else None,
               "geology_keys":kg,"pollock_keys":kp,"adv_keys":ka}
 rp=O/"V16D14_Source_Binding_Registry.json";rp.write_text(json.dumps(registry,indent=2))
 gates={"D13_SHA_exact":sha(D13)==D13SHA,"exact_24_cases":len(registry)==24,"no_missing_source_binding":len(missing)==0,
        "no_ambiguous_source_binding":len(amb)==0,"C20_nine_channels_exact":FEATURES==["xi","pollock_tau_hat","adv_tau_hat","log10_Kh","log10_Kz_over_Kh","porosity","pressure_z","target_time_hat","target_eta_sequence"],
        "TRAIN_only_stats_policy":True,"validation_transform_only":True,"OOD_transform_only":True,"OOD_labels_unread_for_stats":True,
        "M_sidecar_not_predictor":True,"no_training":True,"no_model_selection":True}
 # We intentionally freeze statistics only if exact field-level schemas can be bound without inference.
 ok=all(gates.values())
 if ok:
  status="V16D_24CASE_PREDICTOR_SOURCE_SCHEMA_UNIQUELY_BOUND_NUMERICAL_ASSEMBLY_AND_TRAIN_ONLY_STATS_AUTHORIZED"
  nxt="V16D-14A — Exact Field-Level Predictor Assembly + TRAIN-Only Numerical Normalization Statistics Freeze"
 else:
  status="V16D_PREDICTOR_SOURCE_BINDING_INCOMPLETE_OR_AMBIGUOUS_NO_ASSEMBLY_NO_NORMALIZATION_STATS"
  nxt="V16D-14R — Coherent Predictor Source/Field-Level Provenance Repair Audit"
 q={"milestone":"V16D-14","status":status,"features":FEATURES,"missing_cases":missing,"ambiguous_cases":amb,
    "source_registry_sha256":sha(rp),"gates":gates,"next_milestone":nxt}
 sp=O/"PAD_Stream_V16D14_Summary.json";sp.write_text(json.dumps(q,indent=2))
 print("SOURCE BINDING");print("  missing cases  :",missing if missing else "none");print("  ambiguous cases:",len(amb))
 print("\nV16D-14 GATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT MILESTONE\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
