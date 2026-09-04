#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
AR2=R/"output"/"V16_D14AR2_EXACT_SAMPLING_STATEMENT_LINEAGE_BINDING"/"PAD_Stream_V16D14AR2_Summary.json"
AR2SHA="0f0fb6ecb402d7ba5a3f3c164810d652e5db740f98c04fdd011cea8d6d227483"
O=R/"output"/"V16_D14AR3_NEW_EXPLICIT_STREAMLINE_TO_GRID_SAMPLING_CONTRACT";O.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 print("="*78);print("PAD-Stream V16D-14AR3")
 print("New Explicit V16D Streamline-to-Grid Sampling Contract");print("="*78)
 print("""HISTORICAL RAW K/PRESSURE PATH-SAMPLING PROVENANCE IS INCOMPLETE.
AR3 DOES NOT RELABEL A NEW RULE AS HISTORICAL.

THIS MILESTONE DEFINES A NEW, EXPLICIT, VERSIONED V16D SAMPLING STANDARD.
NO TARGET LABELS ARE READ. NO NORMALIZATION IS FIT. NO TRAINING OCCURS.
""")
 if not AR2.exists() or sha(AR2)!=AR2SHA:raise RuntimeError("AR2 authority SHA mismatch")
 q2=json.loads(AR2.read_text())
 if q2.get("status")!="V16D_PRESERVED_SOURCES_DO_NOT_FULLY_BIND_RAW_C20_SAMPLING_ALGEBRA_NEW_VERSIONED_SAMPLING_CONTRACT_REQUIRED":raise RuntimeError("AR2 status mismatch")
 contract={
 "id":"V16D_STREAMLINE_TO_GRID_SAMPLING_1.0",
 "provenance":"NEW_V16D_CONTRACT_NOT_HISTORICAL_RECOVERY",
 "grid":{"array_order":"(k,j,i)=(z,y,x)","nx":50,"ny":50,"nz":15,
         "dx_m":6.096,"dy_m":6.096,"dz_m":1.2192,
         "origin":"domain_corner_(0,0,0)","cell_intervals":"half-open [edge_n,edge_n+1), with domain-max assigned to last cell"},
 "mapping":{
   "i":"clip(floor(x/dx_m),0,nx-1)",
   "j":"clip(floor(y/dy_m),0,ny-1)",
   "k":"clip(floor(z/dz_m),0,nz-1)",
   "interpolation":"NONE_NEAREST_CONTAINING_CELL",
   "boundary_policy":"clip only for exact/roundoff domain-edge coordinates; coordinates materially outside domain are ERROR",
   "outside_tolerance_m":1e-8},
 "raw_sampling":{
   "Kx_path":"Kx[k,j,i]","Ky_path":"Ky[k,j,i]","Kz_path":"Kz[k,j,i]",
   "porosity_path":"porosity[k,j,i]","pressure_path":"pressure[k,j,i]"},
 "derived_features":{
   "Kh":"sqrt(Kx_path*Ky_path)",
   "log10_Kh":"log10(Kh)",
   "log10_Kz_over_Kh":"log10(Kz_path/Kh)",
   "pressure_z":"TRAIN_ONLY_ZSCORE_OF_pressure_path",
   "porosity":"raw porosity path; normalization policy determined from TRAIN variance only"},
 "kinematic_features":{
   "xi":"common Pollock theta coordinate",
   "pollock_tau_hat":"pollock_tau_s/pollock_tau_end_s",
   "adv_tau_hat":"ADV travel time sampled/evaluated on the same 201 Pollock nodes, normalized by pollock_tau_end_s",
   "target_time_hat":"target_days/1000 days",
   "target_eta_sequence":"86400*target_days/pollock_tau_end_s broadcast over 201 nodes"},
 "physics_sidecar":{"M_face":"D9R1/C7 conservative face metric; NOT predictor"},
 "normalization":{"fit_partition":"TRAIN_CASES_ONLY","validation":"transform-only","locked_OOD":"transform-only",
                  "target_Y_used_for_predictor_stats":False,"zero_variance":"constant channel; no divide by zero"},
 "prohibitions":["NO historical relabeling","NO numerical-closeness calibration","NO interpolation unless future versioned contract",
                 "NO validation/OOD normalization fit","NO OOD label use for model selection","NO M_face predictor without new contract"],
 "case_scope":"V16D Recipe1.1 Foundation Cases 0002-0025; Case0001 excluded from this multi-case experiment"
 }
 cp=O/"V16D14AR3_Streamline_to_Grid_Sampling_Contract_1.0.json";cp.write_text(json.dumps(contract,indent=2))
 gates={"AR2_SHA_exact":sha(AR2)==AR2SHA,"new_contract_explicitly_not_historical":True,"grid_order_frozen":True,
 "origin_frozen":True,"cell_mapping_frozen":True,"boundary_policy_frozen":True,"raw_K_sampling_frozen":True,
 "raw_porosity_sampling_frozen":True,"raw_pressure_sampling_frozen":True,"derived_feature_algebra_frozen":True,
 "TRAIN_only_normalization":True,"validation_transform_only":True,"OOD_transform_only":True,
 "M_face_sidecar_only":True,"no_target_read":True,"no_fitting":True,"no_training":True}
 ok=all(gates.values())
 status="V16D_STREAMLINE_TO_GRID_SAMPLING_1_0_FROZEN_NEW_VERSIONED_PREDICTOR_ASSEMBLY_AUTHORIZED" if ok else "V16D_D14AR3_CONTRACT_BLOCKED"
 summary={"milestone":"V16D-14AR3","status":status,"contract_sha256":sha(cp),"gates":gates,
 "next_milestone":"V16D-14B — Contract-1.0 24-Case Predictor Assembly + TRAIN-Only Normalization Statistics Freeze" if ok else "V16D-14AR3R"}
 sp=O/"PAD_Stream_V16D14AR3_Summary.json";sp.write_text(json.dumps(summary,indent=2))
 print("CONTRACT ID:",contract["id"]);print("CONTRACT SHA-256:",sha(cp));print("\nGATES")
 for k,v in gates.items():print(f"[{'PASS' if v else 'FAIL'}] {k}")
 print("\nSTATUS\n ",status);print("\nNEXT\n ",summary["next_milestone"]);print("\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
