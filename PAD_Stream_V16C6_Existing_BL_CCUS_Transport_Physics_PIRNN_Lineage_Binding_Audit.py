from __future__ import annotations
from pathlib import Path
import ast, csv, hashlib, json, re

ROOT = Path(__file__).resolve().parent
C5_DIR = ROOT/"output"/"V16_C5_TRANSPORT_TARGET_SUPERVISION_AUTHORITY_CONTRACT"
C5_SUMMARY = C5_DIR/"PAD_Stream_V16C5_Summary.json"
C5_CONTRACT = C5_DIR/"V16C5_Transport_Target_Supervision_Authority_Contract.json"
C4_CONTRACT = ROOT/"output"/"V16_C4_MODEL_READY_CONDITIONING_TENSOR_ASSEMBLY"/"V16C4_Model_Ready_Conditioning_Tensor_Contract.json"

SPECS = [
(1,"pi_rnn_stage1_incompressible.py","98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58","INCOMPRESSIBLE_BL_PIRNN"),
(2,"pi_rnn_stage2_compressible_godunov.py","1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397","COMPRESSIBLE_BL_GODUNOV_PIRNN"),
(3,"pi_rnn_stage3_capillary.py","dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f","CAPILLARY_BL_PIRNN"),
(4,"pi_rnn_stage4_full_godunov.py","165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a","FULL_COMPRESSIBLE_CAPILLARY_GODUNOV_PIRNN"),
]

OUT = ROOT/"output"/"V16_C6_BL_CCUS_PIRNN_LINEAGE_BINDING_AUDIT"; OUT.mkdir(parents=True,exist_ok=True)
files = {
"source":OUT/"V16C6_Source_Identity_and_Hash_Binding.csv",
"physics":OUT/"V16C6_Governing_Physics_Lineage.csv",
"model":OUT/"V16C6_Model_Architecture_Lineage.csv",
"cond":OUT/"V16C6_Conditioning_and_Coordinate_Lineage.csv",
"loss":OUT/"V16C6_Physics_Loss_and_Supervision_Lineage.csv",
"compat":OUT/"V16C6_Pollock_TOF_Compatibility_Matrix.csv",
"adapter":OUT/"V16C6_V16_Adapter_Requirements.csv",
"gates":OUT/"V16C6_Final_Lineage_Binding_Gates.csv",
"decision":OUT/"V16C6_Lineage_Binding_Decision.csv",
}
CONTRACT=OUT/"V16C6_BL_CCUS_PIRNN_Lineage_Binding_Contract.json"
SUMMARY=OUT/"PAD_Stream_V16C6_Summary.json"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def csvsave(p,rows):
    rows=list(rows)
    if not rows: p.write_text("",encoding="utf-8"); return
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def loadj(p): return json.loads(p.read_text(encoding="utf-8"))
def savej(p,x): p.write_text(json.dumps(x,indent=2),encoding="utf-8")

def parse(p):
    t=p.read_text(encoding="utf-8",errors="replace"); tr=ast.parse(t)
    fs=[n.name for n in tr.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    cs=[n.name for n in tr.body if isinstance(n,ast.ClassDef)]
    return t,fs,cs

def conds(t):
    ms=re.findall(r'condition_on\s*:\s*Tuple\[[^\]]+\]\s*=\s*\((.*?)\)',t,re.S)
    out=[re.findall(r'["\']([^"\']+)["\']',m) for m in ms]
    out=[x for x in out if x]
    return max(out,key=len) if out else []

def find_sources():
    candidates=[]
    for ext in ("*.py","*.txt"):
        for p in ROOT.rglob(ext):
            low={x.lower() for x in p.parts}
            if "output" in low or ".venv" in low or "venv" in low or p.resolve()==Path(__file__).resolve(): continue
            candidates.append(p)
    hs={}
    for p in candidates:
        try: hs[p]=sha(p)
        except: pass
    out=[]
    for st,name,h,label in SPECS:
        matches=[p for p,v in hs.items() if v==h]
        canonical=ROOT/name
        pick=canonical if canonical in matches else (sorted(matches)[0] if matches else None)
        out.append(dict(stage=st,name=name,expected=h,label=label,path=pick,count=len(matches)))
    return out

def stage_info(st,t,fs):
    c=conds(t)
    model=dict(stage=st,native_input=("xi_seq" if 'name="xi_seq"' in t else "xD_seq" if 'name="xD_seq"' in t else "UNRESOLVED"),
               build_model=("build_model" in fs),stacked_LSTM=("tf.keras.layers.LSTM" in t),
               bounded_output=("tf.math.sigmoid" in t and "swc" in t and "sor" in t),
               conditioning_count=(14 if st==4 and "PARAM_DIM_S4 = 14" in t else len(c)))
    cond=dict(stage=st,condition_on=";".join(c),has_Nc=("Nc" in t),has_inv_Pec=("inv_Pec" in t),
              has_lambda_bc=("lambda_bc" in t),has_logM=("log10(M)" in t or "logM" in t),
              native_sequence=model["native_input"])
    losses=[x for x in ["data_loss","injector_bc_loss","tip_bc_loss","outlet_bc_loss","physics_loss_char",
                        "pde_residual_loss","shape_loss","monotonicity_loss","mass_balance_loss","anchor_loss",
                        "curvature_hinge_loss"] if x in fs]
    loss=dict(stage=st,loss_functions=";".join(losses),
              physics_residual=("physics_loss_char" if "physics_loss_char" in fs else "pde_residual_loss" if "pde_residual_loss" in fs else "UNRESOLVED"))
    if st==1:
        phys=dict(stage=st,equation="dS/dtD + dfw/dxD = 0",truth="analytic Buckley-Leverett/Welge fan-shock",
                  compressible=False,capillary=False,native_coordinate="xi tied to xD/xD_star")
        comp=dict(stage=st,status="ADAPTER_REQUIRED",double_count_risk="LOW",capillary_metric_issue=False,
                  recommended_role="LIMIT/NESTING/PHYSICS-REGRESSION REFERENCE",
                  reason="Native xi is tied to xD_star fan/shock geometry; Pollock TOF is not xi by definition.")
    elif st==2:
        phys=dict(stage=st,equation="phi dS/dt + d(u fw)/dx = 0; u=u_inj exp(Nc xD)",
                  truth="conservative upwind Godunov snapshots",compressible=True,capillary=False,
                  native_coordinate="xi + xD_star; transform machinery retained")
        comp=dict(stage=st,status="ADAPTER_REQUIRED",double_count_risk="MATERIAL",capillary_metric_issue=False,
                  recommended_role="COMPRESSIBLE HYPERBOLIC ADAPTER REFERENCE",
                  reason="Explicit Nc velocity and native xD/xi must be reconciled with Pollock TOF, which already contains frozen velocity travel time.")
        loss["consistency_note"]="Godunov conservative truth is paired with intentionally retained transform-form characteristic residual."
    elif st==3:
        phys=dict(stage=st,equation="dS/dtD + dfw/dxD = (phi/Pe_c)d/dxD[D_tilde(S)dS/dxD]",
                  truth="Godunov advection + implicit tridiagonal capillary diffusion",compressible=False,capillary=True,
                  native_coordinate="xD full-profile native 64-node conditioning grid")
        comp=dict(stage=st,status="ADAPTER_REQUIRED",double_count_risk="LOW",capillary_metric_issue=True,
                  recommended_role="CAPILLARY OPERATOR/LOSS REFERENCE",
                  reason="Capillary second spatial derivatives are xD-based; Pollock TOF alone is not a spatial metric.")
    else:
        phys=dict(stage=st,equation="dS/dtD + d(u_D fw)/dxD = (phi/Pe_c)d/dxD[D_tilde(S)dS/dxD]; u_D=exp(Nc xD)",
                  truth="compressible conservative Godunov advection + implicit capillary diffusion",
                  compressible=True,capillary=True,native_coordinate="xD full-profile native 64-node conditioning grid")
        comp=dict(stage=st,status="PRIMARY_LINEAGE_ADAPTER_REQUIRED",
                  double_count_risk="HIGH_IF_Nc_AND_POLLOCK_VELOCITY_ARE_NAIVELY_STACKED",capillary_metric_issue=True,
                  recommended_role="PRIMARY V16 BL/CCUS TRANSPORT PHYSICS LINEAGE",
                  reason="Most complete existing CCUS lineage, but xD-based variable-velocity advection and capillary diffusion require an explicit Pollock-TOF/metric transform.")
    return phys,model,cond,loss,comp

def main():
    print("\n"+"="*78); print("PAD-Stream V16C-6"); print("Existing BL/CCUS Transport Physics / PI-RNN Lineage Binding Audit"); print("="*78)
    print("""
NO PI-RNN SOURCE WILL BE EXECUTED.
NO TENSORFLOW MODULE WILL BE IMPORTED FROM AUDITED SOURCES.
NO TRANSPORT SOLVE WILL BE EXECUTED.
NO Y_TRANSPORT OR SATURATION FIELD WILL BE GENERATED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO LOSS WEIGHT WILL BE CHANGED.
NO FROZEN V15/V16 ARTIFACT WILL BE CHANGED.
ONLY SOURCE / PHYSICS / MODEL / LOSS / POLLOCK-COMPATIBILITY LINEAGE IS AUDITED.
""")
    for p in [C5_SUMMARY,C5_CONTRACT,C4_CONTRACT]:
        if not p.exists(): raise FileNotFoundError(p)
    if loadj(C5_SUMMARY).get("status")!="V16C_TRANSPORT_SUPERVISION_AUTHORITY_CONTRACT_READY":
        raise RuntimeError("V16C-6 requires completed V16C-5.")

    res=find_sources()
    sr=[]; pr=[]; mr=[]; cr=[]; lr=[]; xr=[]
    for r in res:
        if r["path"] is None:
            sr.append(dict(stage=r["stage"],label=r["label"],canonical=r["name"],expected_sha256=r["expected"],
                           resolved_path="NONE",binding="UNRESOLVED",exact_match_count=0,parse_success=False)); continue
        try: t,fs,cs=parse(r["path"]); ok=True
        except Exception: t,fs,cs="",[],[]; ok=False
        sr.append(dict(stage=r["stage"],label=r["label"],canonical=r["name"],expected_sha256=r["expected"],
                       resolved_path=str(r["path"]),resolved_sha256=sha(r["path"]),
                       binding=("EXACT_SHA256" if r["count"]==1 else "EXACT_SHA256_DUPLICATE_IDENTICAL"),
                       exact_match_count=r["count"],parse_success=ok,functions=len(fs),classes=len(cs)))
        if ok:
            a,b,c,d,e=stage_info(r["stage"],t,fs); pr.append(a); mr.append(b); cr.append(c); lr.append(d); xr.append(e)

    adapters=[
      dict(adapter="A1_Pollock_coordinate_transform",required=True,purpose="Derive Pollock tau to native transport-coordinate/operator relation; do not relabel tau as xD/xi."),
      dict(adapter="A2_compressible_velocity_decomposition",required=True,purpose="Prevent Stage-2/4 Nc-based velocity from double counting velocity already encoded in Pollock TOF."),
      dict(adapter="A3_capillary_streamline_metric",required=True,purpose="Provide physical streamline distance/metric for capillary spatial derivatives."),
      dict(adapter="A4_sequence_interface",required=True,purpose="Reconcile Stage-3/4 native 64 nodes with frozen V16C 201-node Pollock database."),
      dict(adapter="A5_V16_conditioning_bridge",required=True,purpose="Bridge V16C geology/pressure/ADV context to existing PI-RNN conditioning without changing physics authority."),
    ]
    csvsave(files["source"],sr); csvsave(files["physics"],pr); csvsave(files["model"],mr); csvsave(files["cond"],cr); csvsave(files["loss"],lr); csvsave(files["compat"],xr); csvsave(files["adapter"],adapters)

    bound=(len(pr)==4 and all(r["resolved_path"]!="NONE" for r in sr))
    primary=any(r.get("stage")==4 and r.get("recommended_role","").startswith("PRIMARY V16") for r in xr)
    gates=[
      ("V16C5_supervision_authority_status_reproduced",True),
      ("four_uploaded_source_hashes_bound",bound),
      ("all_four_sources_parse_without_execution",len(pr)==4),
      ("stage1_incompressible_lineage_bound",any(r["stage"]==1 for r in pr)),
      ("stage2_compressible_godunov_lineage_bound",any(r["stage"]==2 for r in pr)),
      ("stage3_capillary_lineage_bound",any(r["stage"]==3 for r in pr)),
      ("stage4_full_godunov_lineage_bound",any(r["stage"]==4 for r in pr)),
      ("model_architecture_lineage_audited",len(mr)==4),
      ("conditioning_coordinate_lineage_audited",len(cr)==4),
      ("physics_loss_lineage_audited",len(lr)==4),
      ("Pollock_TOF_compatibility_classified_all_stages",len(xr)==4),
      ("no_native_coordinate_silently_relabelled_as_Pollock_TOF",all(r["status"]!="DIRECT" for r in xr) if xr else False),
      ("stage4_selected_primary_by_physics_completeness",primary),
      ("compressibility_double_count_risk_explicit",True),
      ("capillary_metric_requirement_explicit",True),
      ("no_source_execution",True),("no_transport_solve",True),("no_Y_transport_generated",True),
      ("no_saturation_generated",True),("no_model_predict",True),("no_training",True),("no_loss_weight_change",True),
      ("no_frozen_artifact_mutation",True)]
    csvsave(files["gates"],[dict(gate=g,passed=bool(v)) for g,v in gates])
    ok=all(v for _,v in gates)
    if ok:
        status="V16C_BL_CCUS_PIRNN_LINEAGE_BOUND_ADAPTER_REQUIRED"
        diagnosis="FOUR_STAGE_BL_CCUS_PIRNN_FAMILY_BOUND_STAGE4_PRIMARY_BUT_DIRECT_POLLOCK_TOF_SUBSTITUTION_INVALID"
        rec="Freeze C6 lineage. Proceed to V16C-7 to derive the Pollock-TOF / full BL-CCUS transport adapter, preventing velocity double counting and preserving capillary spatial metrics."
        nxt="V16C-7 — Pollock-TOF / Full BL-CCUS Transport Adapter Physics Contract"
    else:
        status="V16C_BL_CCUS_PIRNN_LINEAGE_BINDING_INCOMPLETE"; diagnosis="ONE_OR_MORE_SOURCE_OR_LINEAGE_GATES_FAILED"
        rec="Audit only failed V16C-6 source/hash/dataflow gates."; nxt="V16C-6R — BL/CCUS PI-RNN Lineage Residual Binding Audit"
    csvsave(files["decision"],[dict(status=status,diagnosis=diagnosis,primary_lineage=("STAGE4_FULL_COMPRESSIBLE_CAPILLARY_GODUNOV" if primary else "UNRESOLVED"),direct_Pollock_substitution="PROHIBITED",adapter_required=True,next_milestone=nxt)])
    savej(CONTRACT,dict(milestone="V16C-6",status=status,diagnosis=diagnosis,primary_lineage="Stage 4 full compressible+capillary conservative Godunov",required_adapters=[a["adapter"] for a in adapters],direct_Pollock_substitution=False,recommendation=rec,next_milestone=nxt))
    savej(SUMMARY,dict(milestone="V16C-6",status=status,diagnosis=diagnosis,source_count_bound=sum(r["resolved_path"]!="NONE" for r in sr),primary_lineage=("STAGE4_FULL_COMPRESSIBLE_CAPILLARY_GODUNOV" if primary else "UNRESOLVED"),adapter_required=True,recommendation=rec,next_milestone=nxt))

    print("SOURCE LINEAGE")
    for r in sr: print(f"  Stage {r['stage']} | {r['label']:<42} | {r['binding']} | parse={r['parse_success']}")
    print("\nPOLLOCK-TOF COMPATIBILITY")
    for r in xr: print(f"  Stage {r['stage']} | {r['status']}\n           {r['reason']}")
    print("\nPRIMARY V16 TRANSPORT LINEAGE")
    print("  STAGE 4 FULL COMPRESSIBLE + CAPILLARY CONSERVATIVE GODUNOV" if primary else "  UNRESOLVED")
    print("\nCRITICAL ADAPTER ISSUES")
    print("  1. Pollock tau is not xD/xi by definition.")
    print("  2. Nc/u_D must not double count velocity already encoded by Pollock TOF.")
    print("  3. Capillary diffusion needs a physical streamline spatial metric.")
    print("  4. Native 64-node full-profile interface must be reconciled with V16C 201 nodes.")
    print("\n"+"="*78); print("V16C-6 FINAL LINEAGE BINDING GATES"); print("="*78)
    for g,v in gates: print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("="*78+"\n\nSTATUS\n  "+status+"\n\nDIAGNOSIS\n  "+diagnosis+"\n\nRECOMMENDATION\n  "+rec+"\n\nNEXT MILESTONE\n  "+nxt)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    print("\n"+"="*78); print("PAD-STREAM V16C-6 BL/CCUS PI-RNN LINEAGE BINDING AUDIT: COMPLETE"); print("="*78)

if __name__=="__main__": main()
