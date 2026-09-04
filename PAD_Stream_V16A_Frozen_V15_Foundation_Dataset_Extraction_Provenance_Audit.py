from __future__ import annotations
from pathlib import Path
import csv, hashlib, json
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_FOUNDATION_CASE_0001"
OUT.mkdir(parents=True, exist_ok=True)

CASE_NPZ = OUT / "PAD_Stream_V16A_Foundation_Case_0001.npz"
ARRAY_INVENTORY = OUT / "V16A_V15_Array_Inventory.csv"
CANDIDATE_TABLE = OUT / "V16A_Component_Candidate_Binding.csv"
BOUND_TABLE = OUT / "V16A_Bound_Component_Identity.csv"
GATE_TABLE = OUT / "V16A_Foundation_Case_Extraction_Gates.csv"
DECISION_TABLE = OUT / "V16A_Foundation_Case_Extraction_Decision.csv"
CONTRACT_FILE = OUT / "V16A_Foundation_Case_0001_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V16A_Summary.json"

GRID_SHAPE=(15,50,50)
EXPECTED={
"Kx":([(15,50,50)],["kx","permx","perm_x","permeability_x"],["flux","velocity","vel"]),
"Ky":([(15,50,50)],["ky","permy","perm_y","permeability_y"],["flux","velocity","vel"]),
"Kz":([(15,50,50)],["kz","permz","perm_z","permeability_z"],["flux","velocity","vel"]),
"porosity":([(15,50,50)],["poro","porosity","phi"],["flux","velocity","vel"]),
"pressure":([(15,50,50)],["pressure","press","p_field","pgrid"],["sat","saturation","truth"]),
"Qx":([(15,50,49)],["qx","flux_x","darcy_flux_x"],["velocity","vel"]),
"Qy":([(15,49,50)],["qy","flux_y","darcy_flux_y"],["velocity","vel"]),
"Qz":([(14,50,50)],["qz","flux_z","darcy_flux_z"],["velocity","vel"]),
"Vx":([(15,50,49)],["vx","vel_x","velocity_x"],["qx","flux"]),
"Vy":([(15,49,50)],["vy","vel_y","velocity_y"],["qy","flux"]),
"Vz":([(14,50,50)],["vz","vel_z","velocity_z"],["qz","flux"]),
"streamline_xyz":([(1078,201,3)],["xyz","streamline_xyz","transport_xyz"],["grid"]),
"pollock_tof":([(1078,201)],["tof","tau","pollock_tof","transport_tof"],["sat","truth"]),
"producer_id":([(1078,),(1078,1)],["producer","producer_id","prod_id"],[]),
"streamline_weight":([(1078,),(1078,1)],["weight","weights","streamline_weight"],[]),
}
BONUS={
"Kx":["v15_sg1","v15sg1","v15_sg2","v15sg2"],"Ky":["v15_sg1","v15sg1","v15_sg2","v15sg2"],
"Kz":["v15_sg1","v15sg1","v15_sg2","v15sg2"],"porosity":["v15_sg1","v15sg1","v15_sg6","v15sg6"],
"pressure":["v15_sg3","v15sg3"],"Qx":["v15_sg4","v15sg4"],"Qy":["v15_sg4","v15sg4"],"Qz":["v15_sg4","v15sg4"],
"Vx":["v15_sg5","v15sg5"],"Vy":["v15_sg5","v15sg5"],"Vz":["v15_sg5","v15sg5"],
"streamline_xyz":["v15_sg6","v15sg6"],"pollock_tof":["v15_sg6","v15sg6"],
"producer_id":["v15_sg6","v15sg6","v15_sg5","v15sg5"],"streamline_weight":["v15_sg6","v15sg6","v15_sg5","v15sg5"],
}

def sha_arr(a):
    a=np.ascontiguousarray(a)
    h=hashlib.sha256()
    h.update(str(a.dtype).encode()); h.update(str(tuple(a.shape)).encode()); h.update(a.tobytes())
    return h.hexdigest()

def sha_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def save_csv(p,rows):
    rows=list(rows)
    if not rows: p.write_text("",encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def save_json(p,obj): p.write_text(json.dumps(obj,indent=2),encoding="utf-8")

def inventory():
    rows=[]; entries=[]
    root=ROOT/"output"
    for p in sorted(root.rglob("*.npz")) if root.exists() else []:
        s=str(p).lower()
        if "v16_" in s or "v16a" in s or "v17" in s or "v18" in s or "v19" in s or "v20" in s: continue
        try:
            with np.load(p,allow_pickle=False) as db:
                for k in db.files:
                    a=np.asarray(db[k])
                    numeric=np.issubdtype(a.dtype,np.number)
                    finite=bool(np.all(np.isfinite(a))) if numeric else False
                    rec={"artifact":str(p),"artifact_sha256":sha_file(p),"key":k,"shape":str(tuple(a.shape)),
                         "dtype":str(a.dtype),"numeric":numeric,"finite":finite,"array_sha256":sha_arr(a) if numeric else ""}
                    rows.append(rec); entries.append((p,k,a.copy(),rec))
        except Exception as e:
            rows.append({"artifact":str(p),"load_error":repr(e)})
    return rows,entries

def score(comp,p,k,a):
    shapes,inc,exc=EXPECTED[comp]
    if tuple(a.shape) not in shapes or not np.issubdtype(a.dtype,np.number) or not np.all(np.isfinite(a)): return -10000
    lk=k.lower(); lp=str(p).lower(); sc=100
    sc+=80*sum(t in lk for t in inc); sc-=120*sum(t in lk for t in exc)
    sc+=100*sum(t in lp for t in BONUS.get(comp,[]))
    if lk==comp.lower(): sc+=200
    if any(x in lp for x in ["r26i","audit","replay","precision"]): sc-=40
    return sc

def bind(entries):
    cand=[]; bound_rows=[]; bound={}
    for comp in EXPECTED:
        arr=[]
        for p,k,a,rec in entries:
            sc=score(comp,p,k,a)
            if sc>0: arr.append((sc,p,k,a,rec))
        arr.sort(key=lambda x:(-x[0],str(x[1]),x[2]))
        uniq={}
        for r in arr: uniq.setdefault(r[4]["array_sha256"],r)
        u=sorted(uniq.values(),key=lambda x:(-x[0],str(x[1]),x[2]))
        for rank,r in enumerate(u[:20],1):
            sc,p,k,a,rec=r
            cand.append({"component":comp,"rank":rank,"score":sc,"artifact":str(p),"key":k,"shape":str(tuple(a.shape)),
                         "dtype":str(a.dtype),"array_sha256":rec["array_sha256"]})
        if not u:
            bound_rows.append({"component":comp,"status":"MISSING"}); continue
        best=u[0]; margin=best[0]-u[1][0] if len(u)>1 else best[0]
        sc,p,k,a,rec=best
        if sc>=180 and margin>0:
            bound[comp]=a
            bound_rows.append({"component":comp,"status":"BOUND","artifact":str(p),"artifact_sha256":rec["artifact_sha256"],
                               "key":k,"score":sc,"margin":margin,"shape":str(tuple(a.shape)),"dtype":str(a.dtype),
                               "array_sha256":rec["array_sha256"]})
        else:
            bound_rows.append({"component":comp,"status":"AMBIGUOUS","artifact":str(p),"artifact_sha256":rec["artifact_sha256"],
                               "key":k,"score":sc,"margin":margin,"shape":str(tuple(a.shape)),"dtype":str(a.dtype),
                               "array_sha256":rec["array_sha256"]})
    return cand,bound_rows,bound

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16A")
    print("Frozen V15 Foundation Dataset Extraction / Provenance Audit")
    print("="*78)
    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO NEW PHYSICS WILL BE SOLVED.
NO FROZEN VERSION 15 ARTIFACT WILL BE CHANGED.
NO MISSING FOUNDATION FEATURE WILL BE FABRICATED.
FAST MARCHING WILL NOT BE RUN IN V16A.
""")
    inv,entries=inventory(); save_csv(ARRAY_INVENTORY,inv)
    cand,bound_rows,bound=bind(entries); save_csv(CANDIDATE_TABLE,cand); save_csv(BOUND_TABLE,bound_rows)
    print(f"V15 NPZ array records : {len(inv)}")
    print("\nFOUNDATION COMPONENT BINDING")
    for r in bound_rows:
        print(f"  {r['component']:<20} | {r['status']:<10} | {Path(r.get('artifact','')).name if r.get('artifact') else 'NONE'}"
              f"{' :: '+r.get('key','') if r.get('key') else ''}")
    req=list(EXPECTED); all_bound=all(x in bound for x in req)
    gates=[(f"{x}_bound",x in bound) for x in req]+[
        ("all_required_components_bound",all_bound),("no_model_predict_executed",True),("no_training_performed",True),
        ("no_new_physics_solved",True),("no_V15_artifact_changed",True),("no_FMM_executed",True)]
    save_csv(GATE_TABLE,[{"gate":g,"passed":p} for g,p in gates])
    failed=[g for g,p in gates if not p]
    geometry={"grid_shape_nz_ny_nx":[15,50,50],"cell_dimensions_ft_dx_dy_dz":[20.0,20.0,4.0],
              "physical_dimensions_ft_x_y_z":[1000.0,1000.0,60.0],"well_pattern":"five-spot",
              "producer_bhp_psi":2000.0,"co2_injection_tonnes_per_day":500.0,"gravity_enabled":True}
    if all_bound:
        payload={k:np.asarray(v) for k,v in bound.items()}
        payload["grid_shape_nz_ny_nx"]=np.asarray(geometry["grid_shape_nz_ny_nx"],dtype=np.int32)
        payload["cell_dimensions_ft_dx_dy_dz"]=np.asarray(geometry["cell_dimensions_ft_dx_dy_dz"],dtype=np.float64)
        payload["physical_dimensions_ft_x_y_z"]=np.asarray(geometry["physical_dimensions_ft_x_y_z"],dtype=np.float64)
        np.savez_compressed(CASE_NPZ,**payload)
        status="V16A_FOUNDATION_CASE_0001_EXTRACTED_AND_PROVENANCE_BOUND"
        diagnosis="ALL_REQUIRED_FROZEN_V15_COMPONENTS_BOUND_TO_ONE_STANDARDIZED_FOUNDATION_CASE"
        recommendation="Freeze Foundation Case 0001 and proceed to V16B exact Fast Marching physics baseline."
        next_ms="V16B — Exact Fast Marching Physics Baseline"
    else:
        status="V16A_FOUNDATION_CASE_EXTRACTION_BLOCKED"
        diagnosis="ONE_OR_MORE_REQUIRED_V15_FOUNDATION_COMPONENTS_ARE_MISSING_OR_AMBIGUOUS"
        recommendation="Do not fabricate missing arrays and do not run Fast Marching. Audit only the failed V16A component bindings."
        next_ms="V16A-R1 — Missing / Ambiguous Foundation Component Binding Audit"
    save_csv(DECISION_TABLE,[{"status":status,"diagnosis":diagnosis,"bound_component_count":len(bound),
                             "required_component_count":len(req),"failed_gates":";".join(failed),
                             "case_npz_created":CASE_NPZ.exists(),"next_milestone":next_ms}])
    contract={"milestone":"V16A","case_id":"FOUNDATION_CASE_0001","parent_version":"V15_FROZEN","status":status,
              "diagnosis":diagnosis,"geometry":geometry,"required_components":req,"bound_components":bound_rows,
              "constraints":{"training_performed":False,"model_predict_executed":False,"new_physics_solved":False,
                             "FMM_executed":False,"V15_artifact_changed":False,"missing_feature_fabricated":False},
              "case_file":str(CASE_NPZ) if CASE_NPZ.exists() else None,
              "case_file_sha256":sha_file(CASE_NPZ) if CASE_NPZ.exists() else None,
              "recommendation":recommendation,"next_milestone":next_ms}
    save_json(CONTRACT_FILE,contract)
    save_json(SUMMARY_FILE,{"milestone":"V16A","status":status,"diagnosis":diagnosis,"failed_gates":failed,
                            "recommendation":recommendation,"next_milestone":next_ms})
    print("\n"+"="*78); print("V16A FINAL EXTRACTION GATES"); print("="*78)
    for g,p in gates: print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n ",status)
    print("\nDIAGNOSIS\n ",diagnosis)
    print("\nRECOMMENDATION\n ",recommendation)
    print("\nNEXT MILESTONE\n ",next_ms)
    print("\nOUTPUTS\n  Directory:\n   ",OUT)
    if CASE_NPZ.exists():
        print("\nFoundation Case:\n ",CASE_NPZ.name,"\n  SHA-256:",sha_file(CASE_NPZ))
    print("\nContract:\n ",CONTRACT_FILE.name)
    print("\nSummary:\n ",SUMMARY_FILE.name)
    print("\n"+"="*78)
    print("PAD-STREAM V16A FOUNDATION DATASET EXTRACTION: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
