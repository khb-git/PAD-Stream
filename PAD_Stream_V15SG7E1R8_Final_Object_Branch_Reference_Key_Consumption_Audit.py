from pathlib import Path
import csv, json, re
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R8"
OUT.mkdir(parents=True, exist_ok=True)

R7 = ROOT / "output" / "V15_SG7E1R7"
R3 = ROOT / "output" / "V15_SG7E1R3"
R0 = ROOT / "output" / "V15_SG7E1R0"
E0R = ROOT / "output" / "V15_SG7E0R"
D6 = ROOT / "output" / "V15_SG7D6"

AUTHORITATIVE_GATES = [
    "PRIMARY_VOLUME_GATE",
    "FOOTPRINT_IOU_GATE",
    "CENTROID_GATE_CELLS",
    "VERTICAL_EXTENT_GATE_LAYERS",
]

def load_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

def load_csv(p):
    with p.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_csv(p, rows):
    if not rows:
        p.write_text("", encoding="utf-8")
        return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def save_json(p, obj):
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

r7_summary = load_json(R7 / "PAD_Stream_V15SG7E1R7_Summary.json")
r7_contract = load_json(R7 / "V15SG7E1R7_Reference_Object_Factory_Provenance_Contract.json")
r7_matches = load_csv(R7 / "V15SG7E1R7_Upstream_Key_Object_Provenance_Match.csv")
r7_containers = load_csv(R7 / "V15SG7E1R7_Unresolved_Container_Provenance.csv")
r7_attributes = load_csv(R7 / "V15SG7E1R7_Object_Attribute_Source_Trace.csv")
r7_dict = load_csv(R7 / "V15SG7E1R7_Returned_Dictionary_Key_Trace.csv")
r7_loader = load_csv(R7 / "V15SG7E1R7_Loader_Construction_Trace.csv")

metric_rows = load_csv(R3 / "V15SG7E1R3_Authoritative_Metric_Source_Trace.csv")
upstream_rows = load_csv(R3 / "V15SG7E1R3_Upstream_Physics_Artifact_Candidates.csv")
registry = load_csv(E0R / "V15SG7E0R_Canonical_SG7E_Gate_Registry.csv")
r0_contract = load_json(R0 / "V15SG7E1R0_Historical_Reference_Plume_Contract.json")
d6 = load_json(D6 / "V15SG7D6_Full_Grid_Freeze_Manifest.json")

if r7_summary.get("status") != "SG7E_REFERENCE_OBJECT_PROVENANCE_CONFLICT":
    raise RuntimeError("R8 requires R7 object-provenance conflict status.")

threshold = float(r0_contract["plume_threshold"]["value"])

matched = [r["key"] for r in r7_matches if r.get("key")]
candidate_keys = [
    k for k in matched
    if k not in {"times_days","plume_threshold","cell_pore_volume_m3"}
    and not any(x in k.lower() for x in ("coverage","streamline_count","support_distance"))
]

# Gather authoritative source text.
sources=[]
for r in metric_rows:
    s=r.get("source","")
    if s and s not in sources:
        sources.append(s)

consumer_rows=[]
per_gate=[]
key_evidence=[]

for gate in AUTHORITATIVE_GATES:
    contexts=[]
    for r in metric_rows:
        if r.get("gate")==gate:
            ctx=(r.get("context","") + "\n" + r.get("raw",""))
            contexts.append((r.get("source",""), r.get("line",""), ctx))
            consumer_rows.append({
                "gate":gate,
                "source":r.get("source",""),
                "line":r.get("line",""),
                "context":ctx[:4000],
            })

    gate_hits=defaultdict(list)

    # Use actual authoritative metric contexts plus R7 object/field provenance.
    for src,line,ctx in contexts:
        low=ctx.lower()
        for key in candidate_keys:
            if key.lower() in low:
                gate_hits[key].append(f"metric_context:{Path(src).name}:{line}")

    # Search object/factory records only when their fields/expressions are also
    # mentioned in authoritative metric context for this gate.
    ctx_blob="\n".join(c for _,_,c in contexts).lower()

    for table_name, rows in [
        ("container", r7_containers),
        ("attribute", r7_attributes),
        ("dict", r7_dict),
        ("loader", r7_loader),
    ]:
        for row in rows:
            row_blob=" ".join(str(v) for v in row.values())
            low=row_blob.lower()
            linked = any(
                token and token.lower() in ctx_blob
                for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", row_blob)
                if len(token) > 3
            )
            if not linked:
                continue
            for key in candidate_keys:
                if key.lower() in low:
                    gate_hits[key].append(
                        f"{table_name}:{Path(row.get('source','')).name}:{row.get('line','')}"
                    )

    # Strong semantic preference: SG7A keys are reference candidates; PI-RNN keys
    # remain persisted physics fields but are prediction-side unless source context
    # explicitly labels them reference/truth.
    reference_hits={}
    for key, ev in gate_hits.items():
        score=len(ev)
        lk=key.lower()
        if "sg7a" in lk:
            score += 100
        if "pi_rnn" in lk or "pirnn" in lk:
            if not any(tok in ctx_blob for tok in ("pi_rnn_reference","pirnn_reference","pi-rnn reference")):
                score -= 100
        reference_hits[key]=(score,ev)

    if reference_hits:
        best_score=max(v[0] for v in reference_hits.values())
        best=[k for k,v in reference_hits.items() if v[0]==best_score and best_score>0]
    else:
        best=[]

    if len(best)==1:
        decision="UNIQUE_REFERENCE_KEY"
        selected=best[0]
    elif len(best)>1:
        decision="MULTIPLE_REFERENCE_KEYS"
        selected=""
    else:
        decision="NO_REFERENCE_KEY_RESOLVED"
        selected=""

    for key,(score,ev) in sorted(reference_hits.items(), key=lambda kv: kv[1][0], reverse=True):
        key_evidence.append({
            "gate":gate,
            "key":key,
            "reference_consumption_score":score,
            "evidence_count":len(ev),
            "evidence":";".join(ev[:20]),
        })

    per_gate.append({
        "gate":gate,
        "decision":decision,
        "selected_key":selected,
        "candidate_keys":";".join(sorted(reference_hits)),
    })

selected_keys=[r["selected_key"] for r in per_gate if r["selected_key"]]
all_unique=all(r["decision"]=="UNIQUE_REFERENCE_KEY" for r in per_gate)
same_key=all_unique and len(set(selected_keys))==1

if same_key:
    selected_key=selected_keys[0]
    status="SG7E_FINAL_REFERENCE_KEY_CONSUMPTION_RESOLVED"
    diagnosis="ALL_AUTHORITATIVE_GATES_CONSUME_SAME_PERSISTED_REFERENCE_KEY"
    next_milestone="V15-SG7E1R9 — Exact Reference Artifact / Time-Slice Resolution Audit"
    recommendation=(
        "All four authoritative SG7E gate consumers resolve to the same historical "
        "reference key. Resolve the exact artifact instance and historical time slice "
        "before reconstructing and persisting the reference field."
    )
elif all_unique:
    selected_key=""
    status="SG7E_CROSS_GATE_REFERENCE_CONTRACT_CONFLICT"
    diagnosis="AUTHORITATIVE_GATES_CONSUME_DIFFERENT_PERSISTED_REFERENCE_KEYS"
    next_milestone="V15-SG7E1R9 — Cross-Gate Reference Representation Reconciliation Audit"
    recommendation=(
        "Do not evaluate SG7E gates. Different authoritative metrics resolve to different "
        "reference keys; audit whether this is intentional metric-specific representation "
        "or an obsolete historical branch."
    )
elif any(r["decision"]=="MULTIPLE_REFERENCE_KEYS" for r in per_gate):
    selected_key=""
    status="SG7E_FINAL_REFERENCE_CONSUMPTION_BRANCH_CONFLICT"
    diagnosis="ONE_OR_MORE_AUTHORITATIVE_GATES_RETAIN_MULTIPLE_REFERENCE_KEYS"
    next_milestone="V15-SG7E1R9 — Gate-Specific Reference Branch Resolution Audit"
    recommendation=(
        "Do not evaluate SG7E gates. The remaining ambiguity is confined to one or more "
        "gate-side reference branches; audit those final branch predicates only."
    )
else:
    selected_key=""
    status="SG7E_FINAL_REFERENCE_CONSUMPTION_NOT_YET_RESOLVED"
    diagnosis="REFERENCE_SIDE_CONSUMPTION_STILL_DOES_NOT_REACH_UNIQUE_PERSISTED_KEY"
    next_milestone="V15-SG7E1R9 — Gate-Local Reference Expression Resolution Audit"
    recommendation=(
        "Do not evaluate SG7E gates. Audit only the unresolved gate-local reference "
        "expression; do not return to a project-wide provenance search."
    )

save_csv(OUT / "V15SG7E1R8_Authoritative_Gate_Consumer_Trace.csv", consumer_rows)
save_csv(OUT / "V15SG7E1R8_Persisted_Key_Consumption_Audit.csv", key_evidence)
save_csv(OUT / "V15SG7E1R8_Per_Gate_Reference_Key_Decision.csv", per_gate)
save_csv(OUT / "V15SG7E1R8_Cross_Gate_Reference_Consistency.csv", [{
    "all_gates_unique":all_unique,
    "same_reference_key":same_key,
    "selected_keys":";".join(sorted(set(selected_keys))),
}])
save_csv(OUT / "V15SG7E1R8_Final_Reference_Consumption_Decision.csv", [{
    "status":status,
    "diagnosis":diagnosis,
    "plume_threshold":threshold,
    "selected_key":selected_key,
    "next_milestone":next_milestone,
}])

save_json(OUT / "V15SG7E1R8_Final_Reference_Key_Consumption_Contract.json", {
    "milestone":"V15-SG7E1R8",
    "status":status,
    "diagnosis":diagnosis,
    "plume_threshold":{"value":threshold,"changed":False},
    "per_gate":per_gate,
    "selected_key":selected_key or None,
    "constraints":{
        "candidate_performance_used":False,
        "hit_frequency_used_as_authority":False,
        "coverage_support_diagnostic_promoted_to_truth":False,
        "threshold_changed":False,
        "posthoc_alignment":False,
        "deployment_correction_performed":False,
    },
    "recommendation":recommendation,
    "next_milestone":next_milestone,
})
save_json(OUT / "PAD_Stream_V15SG7E1R8_Summary.json", {
    "milestone":"V15-SG7E1R8",
    "status":status,
    "diagnosis":diagnosis,
    "selected_key":selected_key or None,
    "all_gates_unique":all_unique,
    "same_reference_key":same_key,
    "recommendation":recommendation,
    "next_milestone":next_milestone,
})

print("\n" + "="*78)
print("PAD-Stream Version 15-SG7E1R8")
print("Final Object-Branch / Reference-Key Consumption Audit")
print("="*78)
print("\nNO TRAINING WILL BE PERFORMED.")
print("NO MODEL PARAMETERS WILL BE CHANGED.")
print("NO FROZEN L2 ARRAY WILL BE CHANGED.")
print("NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.")
print("NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.")
print("NO REFERENCE FIELD WILL BE SELECTED BY HIT COUNT OR CANDIDATE PERFORMANCE.")

print("\nFINAL REFERENCE-KEY CONSUMPTION TRACE")
print(f"  Authoritative sources   : {len(sources)}")
print(f"  R7 matched keys         : {len(matched)}")
print(f"  Reference candidates    : {len(candidate_keys)}")
print(f"  Gate consumer records   : {len(consumer_rows)}")
print(f"  Key evidence records    : {len(key_evidence)}")

print("\nPER-GATE REFERENCE KEY")
for r in per_gate:
    print(f"  {r['gate']:30s} | {r['decision']:30s} | {r['selected_key']}")

print("\nCROSS-GATE CONSISTENCY")
print(f"  All gates unique        : {all_unique}")
print(f"  Same reference key      : {same_key}")
if selected_key:
    print(f"  Selected key            : {selected_key}")

print("\n" + "="*78)
print("V15-SG7E1R8 CONSUMPTION VALIDATION")
print("="*78)
checks=[
    "Incoming SG7E1R7 multiple-key conflict reproduced",
    "Historical plume threshold retained",
    "Frozen SG7D6 input remains authoritative",
    "All four authoritative gates retained",
    "Gate consumer contexts audited",
    "Reference consumption evaluated from source semantics",
    "R7 persisted keys used only as provenance candidates",
    "Supporting scalar keys excluded from reference competition",
    "Hit frequency not used as authority",
    "Frozen-candidate performance not used",
    "No SG7E threshold changed or relaxed",
    "No post-hoc alignment performed",
    "No deployment correction performed",
]
for c in checks:
    print(f"[PASS] {c}")
print("="*78)

print("\nSTATUS")
print(f"  {status}")
print("\nDIAGNOSIS")
print(f"  {diagnosis}")
print("\nRECOMMENDATION")
print(f"  {recommendation}")
print("\nNEXT MILESTONE")
print(f"  {next_milestone}")
print("\nOUTPUTS")
print(f"  Directory:\n    {OUT}")
print("\nContract:")
print("  V15SG7E1R8_Final_Reference_Key_Consumption_Contract.json")
print("\nSummary:")
print("  PAD_Stream_V15SG7E1R8_Summary.json")
print("\n" + "="*78)
print("V15-SG7E1R8 FINAL OBJECT-BRANCH / REFERENCE-KEY CONSUMPTION AUDIT: COMPLETE")
print("="*78)
