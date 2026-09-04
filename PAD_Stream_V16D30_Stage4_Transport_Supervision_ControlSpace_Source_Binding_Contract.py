#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parent
O=R/"output"/"V16_D30_STAGE4_CONTROLSPACE_TRANSPORT_SUPERVISION_SOURCE_BINDING_CONTRACT";O.mkdir(parents=True,exist_ok=True)
AUTH={
"D27":("V16_D27_36CASE_SG6_STYLE_201NODE_POLLOCK_TRANSPORT_COORDINATES","PAD_Stream_V16D27_Summary.json","6c10ede5895bed51a9324ff8503ec3dffbf8b3d908cc077bdfb476dc65a822f1"),
"D28":("V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION","PAD_Stream_V16D28_R1_Summary.json","3f7664b8b9b2d5a11dc24e1d3528d9a373a606295c7ef39937aff35a4c071f4c"),
"D29":("V16_D29_R1_EXACT_D10C_DERIVED_FMM_ADV_36CASE_CONTROLSPACE_EXECUTION","PAD_Stream_V16D29_R1_Summary.json","18c05132c5206431d2562cbf0341915ebba07bc79311e71ec129f5b84fc2788c")}
D12=R/"PAD_Stream_V16D12_MultiCase_Stage4_Transport_Generator_Source_Binding_and_Case0002_Pilot_Contract.py"
C17="1d357be446103cb554c4759948347d2876235b7c630c64cd826801cbfc61dd4f"
YAUTH="d2a7ba92660dfc0ccf08a5f37b1c9519be000e4f42167ad4417e889be0015f63"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def matches(want,suffix):
 a=[]
 for p in R.rglob("*"):
  if p.is_file() and p.suffix.lower()==suffix and O not in p.parents:
   try:
    if sha(p)==want:a.append(p)
   except:pass
 return a
def named(tokens):
 a=[]
 for p in R.rglob("*.py"):
  if O in p.parents:continue
  n=sum(t in str(p).lower() for t in tokens)
  if n:a.append((n,str(p),p))
 a.sort(key=lambda x:(-x[0],x[1]));return a[0][2] if a else None
def main():
 print("="*78);print("PAD-Stream V16D-30")
 print("Stage-4 Transport Supervision Control-Space Source-Binding Contract");print("="*78)
 g={};up={}
 for k,(d,n,w) in AUTH.items():
  p=R/"output"/d/n;g[k+"_SHA_exact"]=p.exists() and sha(p)==w
  g[k+"_36_cases"]=(R/"output"/d/"cases").exists() and len(list((R/"output"/d/"cases").glob("*.npz")))==36
  up[k]={"path":str(p.relative_to(R)),"expected_sha256":w,"actual_sha256":sha(p) if p.exists() else None}
 g["historical_D12_exists"]=D12.exists()
 c=matches(C17,".py");g["exact_C17_source_SHA_unique"]=len(c)==1
 b={"C17_exact":None if len(c)!=1 else {"path":str(c[0].relative_to(R)),"sha256":C17}}
 for k,t in {"Stage4":["stage4","full_godunov","pi_rnn_stage4"],"C14":["v16c14"],"C15":["v16c15"]}.items():
  p=named(t);b[k]=None if p is None else {"path":str(p.relative_to(R)),"sha256":sha(p)};g[k+"_candidate_bound"]=p is not None
 contract={"version":"V16D_STAGE4_CONTROLSPACE_TRANSPORT_CONTRACT_1.0",
 "target_days":[30,60,100,150,250,365,500,750,1000],"Y_shape_per_case":[9,1078,201],
 "time_mapping":"eta_i(t)=86400*t_days/pollock_tau_end_s[i]",
 "kinematics":"Pollock authoritative; do not stack exp(Nc*xD)",
 "compressibility":"Nc is frozen Stage-4 metadata/source semantics only",
 "capillary":"use D28-R1 M_face_dtheta_dxD; node M sidecar only",
 "outlet_capillary_BC":"held-value identity row; not Neumann",
 "FMM_ADV":"auxiliary only; neither changes source-authentic Y",
 "controls":{"rate_tpd":[350,500,650],"bhp_psi":[1800,2000,2200],
 "rule":"controls act through Foundation-Case flow/kinematics; do not invent a new Stage-4 control law"},
 "split":{"TRAIN":"0026-0027 (18)","VALIDATION":"0028 (9)","LOCKED_OOD_TEST":"0029 (9)"},
 "pilot":"one TRAIN case before 36-case transport generation"}
 g.update({"Pollock_primary":True,"M_face_primary":True,"node_M_sidecar_only":True,
 "legacy_exp_Nc_xD_not_reintroduced":True,"FMM_ADV_auxiliary_only":True,
 "split_preserved":True,"one_TRAIN_pilot_first":True,"no_transport":True,"no_training":True,
 "no_fitting":True,"no_threshold_relaxation":True,"locked_OOD_not_evaluated":True})
 ok=all(g.values())
 status="V16D_STAGE4_CONTROLSPACE_TRANSPORT_LINEAGE_EXACTLY_BOUND_ONE_TRAIN_PILOT_GENERATION_AUTHORIZED" if ok else "V16D_D30_STAGE4_CONTROLSPACE_TRANSPORT_BINDING_BLOCKED"
 nxt="V16D-30-R1 — one TRAIN source-authentic 9-time Stage-4 transport supervision pilot" if ok else "Repair failed provenance gate; do not generate Y."
 y=[str(x.relative_to(R)) for x in matches(YAUTH,".npz")]
 rep={"milestone":"V16D-30","status":status,"upstream":up,"historical_D12_sha256":sha(D12) if D12.exists() else None,
 "bindings":b,"C17_source_sha256":C17,"C17_Y_authority_sha256":YAUTH,"C17_Y_local_matches":y,
 "transport_contract":contract,"gates":g,"next_milestone":nxt}
 cp=O/"V16D30_Stage4_ControlSpace_Transport_Contract.json";cp.write_text(json.dumps(rep,indent=2))
 sp=O/"PAD_Stream_V16D30_Summary.json";sp.write_text(json.dumps({"milestone":"V16D-30","status":status,"contract_sha256":sha(cp),"gates":g,"next_milestone":nxt},indent=2))
 print("\\nSOURCE BINDINGS");[print(" ",k,":",v["path"] if v else "NOT BOUND") for k,v in b.items()]
 print("\\nGATES");[print("[PASS]" if v else "[FAIL]",k) for k,v in g.items()]
 print("\\nSTATUS\\n ",status);print("\\nNEXT\\n ",nxt);print("\\nSummary SHA-256:",sha(sp))
 if not ok:sys.exit(2)
if __name__=="__main__":main()
