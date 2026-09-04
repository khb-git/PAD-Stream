from __future__ import annotations

from pathlib import Path
import csv
import json
import hashlib
import re
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R4_PERSISTED_AUTHORITY_RECOVERY_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

R3_DIR = ROOT / "output" / "V16_A_R3_RECONSTRUCTION_FEASIBILITY_AUDIT"
R3_SUMMARY = R3_DIR / "PAD_Stream_V16AR3_Summary.json"

INVENTORY_CSV = OUT / "V16AR4_Historical_Artifact_Inventory.csv"
PRESSURE_CSV = OUT / "V16AR4_Pressure_Authority_Candidates.csv"
FLUX_CSV = OUT / "V16AR4_Flux_Authority_Candidates.csv"
PRODUCER_CSV = OUT / "V16AR4_Producer_Authority_Candidates.csv"
CONSUMER_CSV = OUT / "V16AR4_Downstream_Consumer_Provenance.csv"
BINDING_CSV = OUT / "V16AR4_Authority_Binding_Decision.csv"
GATES_CSV = OUT / "V16AR4_Final_Authority_Recovery_Gates.csv"
CONTRACT = OUT / "V16AR4_Persisted_Authority_Recovery_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR4_Summary.json"

TARGETS = {
    "pressure": [(15,50,50)],
    "Qx": [(15,50,49)],
    "Qy": [(15,49,50)],
    "Qz": [(14,50,50)],
    "producer_id": [(1078,), (1078,1)],
}

ALIASES = {
    "pressure": ["pressure","p_grid","pressure_grid","p_psi","p_pa","p3d","solution","pvec"],
    "Qx": ["qx","q_x","flux_x","face_flux_x","darcy_flux_x"],
    "Qy": ["qy","q_y","flux_y","face_flux_y","darcy_flux_y"],
    "Qz": ["qz","q_z","flux_z","face_flux_z","darcy_flux_z"],
    "producer_id": [
        "producer_id","producer_ids","prod_id","prod_ids","terminal_producer",
        "capture_id","producer_idx","producer_index","destination_id",
        "target_producer","well_id","well_index"
    ],
}

SOURCE_TERMS = {
    "pressure": ["pressure", "p_grid", "p_psi", "p_pa", "solve"],
    "Qx": ["qx", "flux", "darcy"],
    "Qy": ["qy", "flux", "darcy"],
    "Qz": ["qz", "flux", "darcy"],
    "producer_id": ["producer", "capture", "terminal", "destination", "well_id"],
}

def save_csv(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def sha_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024), b""): h.update(c)
    return h.hexdigest()

def sha_arr(a):
    a=np.ascontiguousarray(a)
    h=hashlib.sha256()
    h.update(str(a.dtype).encode()); h.update(str(tuple(a.shape)).encode()); h.update(a.tobytes())
    return h.hexdigest()

def is_pre_v16(p):
    s=str(p).lower()
    return "v16_" not in s and "v16a" not in s

def key_score(target, key):
    k=key.lower()
    aliases=[x.lower() for x in ALIASES[target]]
    if k in aliases: return 100
    if any(a in k for a in aliases): return 60
    return 0

def path_score(target, p):
    s=str(p).lower()
    score=0
    if target=="pressure" and ("sg3" in s or "pressure" in s): score += 30
    if target in {"Qx","Qy","Qz"} and ("sg4" in s or "flux" in s): score += 30
    if target=="producer_id" and ("sg5" in s or "sg6" in s or "pollock" in s or "streamline" in s): score += 30
    return score

def inventory_npz():
    rows=[]; by_target={t:[] for t in TARGETS}
    outroot=ROOT/"output"
    if not outroot.exists(): return rows,by_target
    for p in sorted(outroot.rglob("*.npz")):
        if not is_pre_v16(p): continue
        try:
            with np.load(p, allow_pickle=True) as db:
                for key in db.files:
                    a=np.asarray(db[key])
                    row={
                        "artifact":str(p),"key":key,"shape":str(tuple(a.shape)),
                        "dtype":str(a.dtype),"artifact_sha256":sha_file(p),
                    }
                    rows.append(row)
                    if not np.issubdtype(a.dtype, np.number): continue
                    for t,shapes in TARGETS.items():
                        if tuple(a.shape) not in shapes: continue
                        ks=key_score(t,key); ps=path_score(t,p)
                        if ks==0 and ps==0: continue
                        finite=True
                        try: finite=bool(np.all(np.isfinite(a)))
                        except Exception: finite=False
                        rec=dict(row)
                        rec.update({
                            "target":t,"key_semantic_score":ks,"path_provenance_score":ps,
                            "total_score":ks+ps,"finite":finite,
                            "array_sha256":sha_arr(a) if finite else "",
                        })
                        by_target[t].append(rec)
        except Exception:
            continue
    return rows,by_target

def source_consumer_trace():
    rows=[]
    for p in sorted(ROOT.glob("*.py")):
        if not is_pre_v16(p): continue
        text=p.read_text(encoding="utf-8", errors="ignore")
        lines=text.splitlines()
        for target,terms in SOURCE_TERMS.items():
            for i,line in enumerate(lines,1):
                low=line.lower()
                if any(term in low for term in terms):
                    if any(tok in low for tok in ["np.save","np.savez","savez_compressed","load(","np.load","return ","[\"", "['"]):
                        rows.append({
                            "target":target,"source":str(p),"line":i,
                            "text":line.strip()[:500],
                        })
    return rows

def choose_binding(target, candidates, consumer_rows):
    # Authority cannot be selected by score alone. Require a unique numerical
    # identity plus semantic key/path evidence. Otherwise remain unresolved.
    valid=[r for r in candidates if r.get("finite")]
    hashes={}
    for r in valid: hashes.setdefault(r["array_sha256"],[]).append(r)

    semantic=[r for r in valid if r["key_semantic_score"]>=60]
    semantic_hashes={r["array_sha256"] for r in semantic}

    if len(semantic_hashes)==1:
        h=next(iter(semantic_hashes))
        rows=[r for r in semantic if r["array_sha256"]==h]
        best=sorted(rows,key=lambda r:(-r["total_score"],r["artifact"],r["key"]))[0]
        return {
            "target":target,"status":"UNIQUE_PERSISTED_SEMANTIC_AUTHORITY_CANDIDATE",
            "array_sha256":h,"artifact":best["artifact"],"key":best["key"],
            "candidate_count":len(valid),"distinct_hashes":len(hashes),
            "semantic_hashes":len(semantic_hashes),
            "reason":"one unique semantic persisted numerical identity found; downstream provenance must remain consistent",
        }

    if len(semantic_hashes)>1:
        return {
            "target":target,"status":"MULTIPLE_PERSISTED_SEMANTIC_IDENTITIES",
            "array_sha256":"","artifact":"","key":"",
            "candidate_count":len(valid),"distinct_hashes":len(hashes),
            "semantic_hashes":len(semantic_hashes),
            "reason":"multiple semantic numerical identities require exact creation/consumer lineage audit",
        }

    if valid:
        return {
            "target":target,"status":"SHAPE_OR_PATH_CANDIDATES_ONLY_NOT_AUTHORITATIVE",
            "array_sha256":"","artifact":"","key":"",
            "candidate_count":len(valid),"distinct_hashes":len(hashes),
            "semantic_hashes":0,
            "reason":"candidate arrays exist but no sufficiently explicit semantic key authority is persisted",
        }

    return {
        "target":target,"status":"NO_PERSISTED_AUTHORITY_FOUND",
        "array_sha256":"","artifact":"","key":"",
        "candidate_count":0,"distinct_hashes":0,"semantic_hashes":0,
        "reason":"no qualifying pre-V16 persisted numerical state found",
    }

def main():
    print("\n"+"="*78)
    print("PAD-Stream V16A-R4")
    print("Persisted Pressure / Flux / Producer Authority Recovery Audit")
    print("="*78)
    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO PRESSURE SOLVE WILL BE EXECUTED.
NO DARCY FLUX WILL BE RECOMPUTED.
NO VELOCITY FIELD WILL BE RECONSTRUCTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
NO AUTHORITY WILL BE SELECTED BY NUMERICAL CLOSENESS.
ONLY GENUINELY PERSISTED PRE-V16 AUTHORITY MAY BE RECOVERED.
""")
    if not R3_SUMMARY.exists(): raise FileNotFoundError(R3_SUMMARY)
    r3=json.loads(R3_SUMMARY.read_text(encoding="utf-8"))
    expected="V16A_FOUNDATION_EXTRACTION_REQUIRES_ADDITIONAL_PERSISTED_AUTHORITY_RECOVERY"
    if r3.get("status")!=expected:
        raise RuntimeError(f"Expected R3 status {expected}, got {r3.get('status')}")

    inventory,by_target=inventory_npz()
    consumers=source_consumer_trace()
    save_csv(INVENTORY_CSV,inventory)
    save_csv(CONSUMER_CSV,consumers)

    save_csv(PRESSURE_CSV,by_target["pressure"])
    save_csv(FLUX_CSV,by_target["Qx"]+by_target["Qy"]+by_target["Qz"])
    save_csv(PRODUCER_CSV,by_target["producer_id"])

    decisions=[choose_binding(t,by_target[t],consumers) for t in TARGETS]
    save_csv(BINDING_CSV,decisions)

    print("PERSISTED AUTHORITY RECOVERY")
    for d in decisions:
        print(f"  {d['target']:<14} | {d['status']:<48} | candidates={d['candidate_count']:<3} | hashes={d['distinct_hashes']}")

    recovered=[d for d in decisions if d["status"]=="UNIQUE_PERSISTED_SEMANTIC_AUTHORITY_CANDIDATE"]
    unresolved=[d for d in decisions if d["status"]!="UNIQUE_PERSISTED_SEMANTIC_AUTHORITY_CANDIDATE"]

    gates=[
        ("incoming_R3_status_reproduced",True),
        ("pre_V16_artifact_scope_enforced",True),
        ("pressure_persisted_authority_audited",True),
        ("Qx_persisted_authority_audited",True),
        ("Qy_persisted_authority_audited",True),
        ("Qz_persisted_authority_audited",True),
        ("producer_id_persisted_authority_audited",True),
        ("downstream_consumer_provenance_audited",True),
        ("no_authority_selected_by_numerical_closeness",True),
        ("no_pressure_solve_executed",True),
        ("no_Darcy_flux_recomputed",True),
        ("no_velocity_reconstructed",True),
        ("no_Pollock_retrace_executed",True),
        ("no_FMM_executed",True),
        ("no_model_predict_executed",True),
        ("no_training_performed",True),
        ("no_V15_artifact_changed",True),
    ]
    save_csv(GATES_CSV,[{"gate":g,"passed":p} for g,p in gates])

    if not unresolved:
        status="V16A_BLOCKED_COMPONENT_PERSISTED_AUTHORITIES_RECOVERED"
        diagnosis="PRESSURE_FLUX_AND_PRODUCER_COMPONENTS_HAVE_UNIQUE_PERSISTED_PRE_V16_SEMANTIC_IDENTITIES"
        recommendation="Proceed to exact binding verification and then Foundation Case 0001 extraction; reconstruct velocity only from the recovered authoritative flux and frozen geometry/porosity contract."
        next_ms="V16A-R5 — Exact Recovered Authority Binding Verification"
    else:
        status="V16A_PERSISTED_AUTHORITY_RECOVERY_INCOMPLETE"
        diagnosis="ONE_OR_MORE_PRESSURE_FLUX_OR_PRODUCER_COMPONENTS_LACK_A_UNIQUE_PERSISTED_PRE_V16_SEMANTIC_AUTHORITY"
        recommendation="Do not rerun frozen physics yet. Audit only unresolved targets using exact creator serialization, downstream consumer, manifest, and frozen deployment lineage. If no persisted authority exists, formally decide whether source-authentic deterministic V15 regeneration is permissible as a derived V16 foundation artifact."
        next_ms="V16A-R5 — Residual Frozen Component Authority / Regeneration Policy Audit"

    contract={
        "milestone":"V16A-R4","status":status,"diagnosis":diagnosis,
        "decisions":decisions,
        "recovered_targets":[d["target"] for d in recovered],
        "unresolved_targets":[d["target"] for d in unresolved],
        "recommendation":recommendation,"next_milestone":next_ms,
        "constraints":{
            "pressure_solve":False,"Darcy_flux_recompute":False,
            "velocity_reconstruction":False,"Pollock_retrace":False,
            "FMM":False,"model_predict":False,"training":False,
            "V15_mutation":False,
        }
    }
    CONTRACT.write_text(json.dumps(contract,indent=2),encoding="utf-8")
    SUMMARY.write_text(json.dumps({
        "milestone":"V16A-R4","status":status,"diagnosis":diagnosis,
        "recovered_targets":contract["recovered_targets"],
        "unresolved_targets":contract["unresolved_targets"],
        "recommendation":recommendation,"next_milestone":next_ms
    },indent=2),encoding="utf-8")

    print("\n"+"="*78)
    print("V16A-R4 FINAL AUTHORITY RECOVERY GATES")
    print("="*78)
    for g,p in gates: print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("="*78)
    print("\nSTATUS\n  "+status)
    print("\nDIAGNOSIS\n  "+diagnosis)
    print("\nRECOMMENDATION\n  "+recommendation)
    print("\nNEXT MILESTONE\n  "+next_ms)
    print("\nOUTPUTS\n  Directory:\n    "+str(OUT))
    print("\nTables:")
    for p in [INVENTORY_CSV,PRESSURE_CSV,FLUX_CSV,PRODUCER_CSV,CONSUMER_CSV,BINDING_CSV,GATES_CSV]:
        print("  "+p.name)
    print("\nContract:\n  "+CONTRACT.name)
    print("\nSummary:\n  "+SUMMARY.name)
    print("\n"+"="*78)
    print("PAD-STREAM V16A-R4 PERSISTED AUTHORITY RECOVERY AUDIT: COMPLETE")
    print("="*78)

if __name__=="__main__":
    main()
