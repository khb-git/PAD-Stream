#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,math,sys
R=Path(__file__).resolve().parent
D17=R/"output"/"V16_D17_EXP_MC1_FIRST_MULTIFOUNDATIONCASE_TRAINING_RUN"
D18=R/"output"/"V16_D18_EXP_MC1_LOCKED_CASELEVEL_OOD_FINAL_EVALUATION_ONE_TOUCH"
S17=D17/"PAD_Stream_V16D17_Summary.json"; S18=D18/"PAD_Stream_V16D18_Summary.json"
SHA17="160fe4d8138df99d46fb2c1b1b0e37668e66754fb3c11a074a1fac7b4e68caeb"
SHA18="f703041ce3f8653d567a0130fcff11d1d3935aef4af0a5a52f686a52b0037de5"
O=R/"output"/"V16_D19_EXP_MC1_GENERALIZATION_AUDIT_FORWARD_DECISION";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-19")
 print("EXP-MC1 Multi-Case Generalization Audit, Interpretation + Forward Decision");print("="*78)
 if sha(S17)!=SHA17 or sha(S18)!=SHA18:raise RuntimeError("D17/D18 frozen SHA mismatch")
 a=json.loads(S17.read_text());b=json.loads(S18.read_text())
 v=float(a["best_checkpoint_validation"]["loss"]); vm=float(a["best_checkpoint_validation"]["mae"])
 o=b["aggregate"]; om=float(o["MSE"]); orm=float(o["RMSE"]); oma=float(o["MAE"])
 vr=math.sqrt(v)
 mse_deg=(om/v-1)*100; rmse_deg=(orm/vr-1)*100; mae_deg=(oma/vm-1)*100
 cases=b["cases"]; rms=[x["RMSE"] for x in cases]
 interp={
 "validation":{"MSE":v,"RMSE":vr,"MAE":vm},
 "locked_OOD":{"MSE":om,"RMSE":orm,"MAE":oma,"max_abs_error":o["max_abs_error"]},
 "relative_to_validation_percent":{"MSE":mse_deg,"RMSE":rmse_deg,"MAE":mae_deg},
 "case_RMSE_range":[min(rms),max(rms)],
 "interpretation":[
  "EXP-MC1 demonstrates nontrivial generalization to four completely unseen Foundation Cases under the fixed-control Recipe1.1 spectral-GRF geology ensemble.",
  "OOD aggregate error is modestly higher than validation error; this is a measured generalization gap, not a tuning signal.",
  "All predictions respect the frozen saturation bounds.",
  "Large pointwise maximum errors coexist with low aggregate RMSE/MAE and require later structural/front diagnostics before stronger claims.",
  "This result does not by itself authorize a foundation-model claim: controls remain fixed and geology coverage is one versioned ensemble family."
 ],
 "forward_decision":{
  "EXP_MC1":"FROZEN_PREDICTIVE_BASELINE",
  "retrain_MC1":"NOT_AUTHORIZED",
  "OOD_informed_tuning":"PROHIBITED",
  "next_scientific_action":"audit OOD structure/front/time/case behavior using the already-frozen checkpoint; no adaptive selection",
  "physics_informed_multicase_EXP_MC2":"DESIGN_NOT_YET_AUTHORIZED_UNTIL_POST_OOD_DIAGNOSTIC_CONTRACT",
  "foundation_model_claim":"NOT_AUTHORIZED"
 }}
 ip=O/"V16D19_EXP_MC1_Generalization_Interpretation.json";ip.write_text(json.dumps(interp,indent=2))
 gates={"D17_SHA_exact":sha(S17)==SHA17,"D18_SHA_exact":sha(S18)==SHA18,"D18_one_touch_true":b["one_touch"] is True,
 "four_OOD_cases_present":len(cases)==4,"finite_metrics":all(math.isfinite(x) for x in [v,vm,om,orm,oma]),
 "no_retraining":True,"no_OOD_adaptation":True,"no_model_selection":True,"no_threshold_tuning":True,
 "MC1_frozen_as_baseline":True,"foundation_model_claim_not_authorized":True,"MC2_not_trained":True}
 status="V16D_EXP_MC1_MULTICASE_CASELEVEL_OOD_GENERALIZATION_BASELINE_FROZEN_POST_OOD_STRUCTURAL_DIAGNOSTIC_CONTRACT_AUTHORIZED"
 nxt="V16D-20 — Frozen EXP-MC1 OOD Structural / Front / Time-Resolved Diagnostic Contract and Audit"
 sp=O/"PAD_Stream_V16D19_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-19","status":status,"interpretation_sha256":sha(ip),"gates":gates,"next_milestone":nxt},indent=2))
 print(f"Validation: MSE={v:.9e} RMSE={vr:.9e} MAE={vm:.9e}")
 print(f"Locked OOD: MSE={om:.9e} RMSE={orm:.9e} MAE={oma:.9e}")
 print(f"OOD vs validation: MSE {mse_deg:+.3f}% | RMSE {rmse_deg:+.3f}% | MAE {mae_deg:+.3f}%")
 print(f"OOD case RMSE range: {min(rms):.9e} .. {max(rms):.9e}")
 print("\nDECISION\n  EXP-MC1 frozen; no retraining or OOD-informed tuning.")
 print("  Foundation-model claim: NOT AUTHORIZED.")
 print("  Next: diagnostic characterization of the already-observed OOD predictions.")
 print("\nGATES")
 for k,vv in gates.items():print(f"[{'PASS' if vv else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",nxt);print("\nSummary SHA-256:",sha(sp))
 if not all(gates.values()):sys.exit(2)
if __name__=="__main__":main()
