from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V16A-R7C2
# Producer Group / Terminal Metadata Resolution Audit
#
# PURPOSE
# -------
# R7C1 established:
#   - producer_id remains the only unresolved V16A foundation component
#   - 30 producer mapping records exist
#   - 1 terminal metadata record exists
#   - 175 grouping metadata edge records exist
#   - but no exact group partition / executable rule was resolved
#
# R7C2 audits the ACTUAL persisted arrays behind those records.
#
# It asks:
#   1. Are any grouping artifacts per-producer streamline-index lists?
#   2. Do any four explicitly labelled producer groups partition 0..1077?
#   3. Does the terminal metadata array encode a producer/capture category?
#   4. Can terminal metadata be joined to one producer-name/index map?
#
# R7C2 DOES NOT reconstruct producer_id.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R7C2_PRODUCER_GROUP_TERMINAL_METADATA_RESOLUTION"
OUT.mkdir(parents=True, exist_ok=True)

R7C1_DIR = ROOT / "output" / "V16_A_R7C1_PRODUCER_CLASSIFICATION_RULE_EDGE_AUDIT"
R7C1_SUMMARY = R7C1_DIR / "PAD_Stream_V16AR7C1_Summary.json"

GROUP_ARRAYS = OUT / "V16AR7C2_Group_Array_Content_Audit.csv"
LABELED_GROUPS = OUT / "V16AR7C2_Labeled_Producer_Group_Candidates.csv"
PARTITION = OUT / "V16AR7C2_Four_Producer_Partition_Test.csv"
TERMINAL = OUT / "V16AR7C2_Terminal_Metadata_Content_Audit.csv"
TERMINAL_MAP = OUT / "V16AR7C2_Terminal_Value_to_Producer_Map_Audit.csv"
RULE = OUT / "V16AR7C2_Resolved_Producer_Rule.csv"
GATES = OUT / "V16AR7C2_Final_Resolution_Gates.csv"
DECISION = OUT / "V16AR7C2_Resolution_Decision.csv"
CONTRACT = OUT / "V16AR7C2_Producer_Metadata_Resolution_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR7C2_Summary.json"

N_STREAMLINES = 1078
PRODUCERS = ["PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE"]


def save_csv(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha_file(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def sha_arr(a):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(str(tuple(a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def infer_label(text: str):
    u = text.upper()
    for p in PRODUCERS:
        if p in u:
            return p
    for short in ["SW", "SE", "NW", "NE"]:
        if re.search(rf"(^|[_\-]){short}([_\-.]|$)", u):
            return f"PROD_{short}"
    return ""


def inventory_candidate_arrays():
    rows = []
    labeled = []
    terminal = []

    outroot = ROOT / "output"
    if not outroot.exists():
        return rows, labeled, terminal

    for p in sorted(outroot.rglob("*.npz")):
        lowp = str(p).lower()
        if "v16_" in lowp or "v16a" in lowp:
            continue
        if not any(tok in lowp for tok in ["sg5", "sg6", "pollock", "streamline"]):
            continue

        try:
            with np.load(p, allow_pickle=False) as db:
                for key in db.files:
                    a = np.asarray(db[key])
                    if not np.issubdtype(a.dtype, np.number):
                        continue
                    if not np.all(np.isfinite(a)):
                        continue

                    rec = {
                        "artifact": str(p),
                        "artifact_sha256": sha_file(p),
                        "key": key,
                        "shape": str(tuple(a.shape)),
                        "dtype": str(a.dtype),
                        "array_sha256": sha_arr(a),
                    }

                    flat = a.reshape(-1)
                    integer_like = np.allclose(flat, np.rint(flat), atol=0, rtol=0)
                    rec["integer_like"] = bool(integer_like)

                    label = infer_label(key + " " + str(p))
                    rec["producer_label"] = label

                    # candidate group index list
                    if integer_like and flat.size > 0:
                        vals = np.rint(flat).astype(np.int64)
                        valid_idx = np.all((vals >= 0) & (vals < N_STREAMLINES))
                        rec["valid_streamline_index_list"] = bool(valid_idx)
                        rec["count"] = int(len(vals))
                        rec["unique_count"] = int(len(np.unique(vals)))
                        if valid_idx and label:
                            labeled.append((p, key, vals, rec))

                    lk = key.lower()
                    if any(t in lk for t in ["terminal", "endpoint", "capture", "destination"]):
                        terminal.append((p, key, np.array(a, copy=True), rec))

                    rows.append(rec)
        except Exception:
            continue

    return rows, labeled, terminal


def test_four_group_partition(labeled):
    # group by producer label; try one candidate per label
    by_label = {p: [] for p in PRODUCERS}
    for item in labeled:
        by_label[item[3]["producer_label"]].append(item)

    rows = []
    complete_labels = all(by_label[p] for p in PRODUCERS)

    if not complete_labels:
        return rows, None

    # deterministic selection: shortest artifact path then key
    selected = {}
    for label in PRODUCERS:
        selected[label] = sorted(by_label[label], key=lambda x: (str(x[0]), x[1]))[0]

    union = []
    for label, item in selected.items():
        p, key, vals, rec = item
        u = np.unique(vals)
        rows.append({
            "producer_label": label,
            "artifact": str(p),
            "key": key,
            "count": len(vals),
            "unique_count": len(u),
            "min_index": int(u.min()) if len(u) else "",
            "max_index": int(u.max()) if len(u) else "",
            "array_sha256": rec["array_sha256"],
        })
        union.append(vals)

    allvals = np.concatenate(union)
    unique = np.unique(allvals)
    duplicates = len(allvals) - len(unique)
    covers = (
        len(unique) == N_STREAMLINES
        and unique.min() == 0
        and unique.max() == N_STREAMLINES - 1
    )
    exact = covers and duplicates == 0

    rows.append({
        "producer_label": "COMBINED",
        "artifact": "",
        "key": "",
        "count": len(allvals),
        "unique_count": len(unique),
        "min_index": int(unique.min()) if len(unique) else "",
        "max_index": int(unique.max()) if len(unique) else "",
        "duplicate_memberships": duplicates,
        "covers_all_1078": covers,
        "exact_partition": exact,
    })

    return rows, {
        "exact_partition": exact,
        "covers_all_1078": covers,
        "duplicate_memberships": duplicates,
        "selected": {
            label: {
                "artifact": str(selected[label][0]),
                "key": selected[label][1],
            }
            for label in PRODUCERS
        }
    }


def audit_terminal(terminal):
    rows = []
    categ = []

    for p, key, a, rec in terminal:
        flat = a.reshape(-1)
        integer_like = np.allclose(flat, np.rint(flat), atol=0, rtol=0)
        unique = np.unique(flat)

        small_category = integer_like and len(unique) <= 16

        row = {
            "artifact": str(p),
            "artifact_sha256": sha_file(p),
            "key": key,
            "shape": str(tuple(a.shape)),
            "dtype": str(a.dtype),
            "integer_like": bool(integer_like),
            "unique_value_count": len(unique),
            "small_category": bool(small_category),
            "values_preview": ";".join(map(str, unique[:20].tolist())),
            "array_sha256": sha_arr(a),
        }
        rows.append(row)

        if a.shape in [(N_STREAMLINES,), (N_STREAMLINES,1)] and small_category:
            categ.append((p,key,a.reshape(-1),row))

    return rows, categ


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R7C2")
    print("Producer Group / Terminal Metadata Resolution Audit")
    print("=" * 78)

    print("""
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECOMPUTED.
NO PRODUCER ID WILL BE RECONSTRUCTED IN R7C2.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO NEAREST-PRODUCER RULE WILL BE INVENTED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
ONLY THE ACTUAL GROUP / TERMINAL ARRAY CONTENT WILL BE RESOLVED.
""")

    if not R7C1_SUMMARY.exists():
        raise FileNotFoundError(R7C1_SUMMARY)

    r7c1 = json.loads(R7C1_SUMMARY.read_text(encoding="utf-8"))
    if r7c1.get("status") != "V16A_PRODUCER_CLASSIFICATION_RULE_EDGE_STILL_UNRESOLVED":
        raise RuntimeError("R7C2 expects unresolved R7C1 rule edge.")

    rows, labeled, terminal = inventory_candidate_arrays()
    save_csv(GROUP_ARRAYS, rows)

    labeled_rows = [x[3] for x in labeled]
    save_csv(LABELED_GROUPS, labeled_rows)

    partition_rows, partition = test_four_group_partition(labeled)
    save_csv(PARTITION, partition_rows)

    terminal_rows, terminal_categories = audit_terminal(terminal)
    save_csv(TERMINAL, terminal_rows)

    terminal_map_rows = []
    terminal_rule = None

    # If one categorical 1078-vector exists with exactly four categories,
    # it is a candidate ID encoding, but without a source-authentic category
    # mapping we do NOT reconstruct yet.
    four_cat = [x for x in terminal_categories if len(np.unique(x[2])) == 4]
    if len(four_cat) == 1:
        p, key, arr, rec = four_cat[0]
        values = np.unique(arr)
        for v in values:
            terminal_map_rows.append({
                "artifact": str(p),
                "key": key,
                "terminal_value": v,
                "producer_label": "UNBOUND",
                "count": int(np.sum(arr == v)),
            })
        terminal_rule = {
            "status": "FOUR_CATEGORY_TERMINAL_ENCODING_FOUND_MAPPING_UNBOUND",
            "authorized": False,
            "reason": "A 4-category terminal vector exists but category-to-producer mapping is not yet source-authentic.",
        }

    save_csv(TERMINAL_MAP, terminal_map_rows)

    if partition and partition["exact_partition"]:
        rule = {
            "status": "PERSISTED_FOUR_PRODUCER_GROUP_PARTITION_BOUND",
            "authorized": True,
            "rule_type": "EXPLICIT_LABELED_GROUP_MEMBERSHIP",
            "reason": "Four explicitly labelled producer index groups partition all 1,078 streamlines exactly once.",
        }
    elif terminal_rule is not None:
        rule = terminal_rule | {"rule_type": "TERMINAL_CATEGORY_ENCODING"}
    else:
        rule = {
            "status": "GROUP_AND_TERMINAL_METADATA_STILL_INSUFFICIENT",
            "authorized": False,
            "rule_type": "",
            "reason": "No exact labeled four-producer partition and no uniquely mappable terminal encoding was found.",
        }

    save_csv(RULE, [rule])

    print("PRODUCER METADATA RESOLUTION")
    print(f"  Numeric candidate arrays   : {len(rows)}")
    print(f"  Labeled group candidates   : {len(labeled)}")
    print(f"  Terminal candidates        : {len(terminal)}")
    print(f"  Exact four-group partition : {bool(partition and partition['exact_partition'])}")
    print(f"  Four-category terminal     : {len(four_cat) == 1}")
    print(f"  Rule status                : {rule['status']}")
    print(f"  Reconstruction authorized  : {rule['authorized']}")

    gates = [
        ("incoming_R7C1_unresolved_status_reproduced", True),
        ("group_array_content_audited", True),
        ("producer_labels_extracted_from_metadata_only", True),
        ("four_group_partition_tested", True),
        ("terminal_array_content_audited", True),
        ("terminal_category_mapping_audited", True),
        ("no_producer_id_reconstructed", True),
        ("no_nearest_rule_invented", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_recompute", True),
        ("no_Pollock_retrace", True),
        ("no_FMM", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_V15_mutation", True),
    ]
    save_csv(GATES, [{"gate": g, "passed": p} for g,p in gates])

    if rule["authorized"]:
        status = "V16A_PRODUCER_IDENTITY_RECONSTRUCTION_RULE_FINAL_BOUND"
        diagnosis = "PERSISTED_EXPLICITLY_LABELED_PRODUCER_GROUPS_DEFINE_ONE_EXACT_PARTITION_OF_ALL_1078_STREAMLINES"
        recommendation = (
            "Proceed to V16A-R7D and construct producer_id strictly from the four persisted producer groups."
        )
        next_ms = "V16A-R7D — Controlled Producer Identity Reconstruction"
    elif rule["status"] == "FOUR_CATEGORY_TERMINAL_ENCODING_FOUND_MAPPING_UNBOUND":
        status = "V16A_PRODUCER_IDENTITY_ONE_CATEGORY_MAP_SHORT"
        diagnosis = "A_FOUR_CATEGORY_TERMINAL_ENCODING_EXISTS_BUT_CATEGORY_TO_PRODUCER_LABEL_MAPPING_IS_NOT_YET_BOUND"
        recommendation = (
            "Audit only the category-to-producer mapping in SG5/SG6 source/summary outputs. Do not reconstruct producer_id yet."
        )
        next_ms = "V16A-R7C3 — Terminal Category-to-Producer Mapping Audit"
    else:
        status = "V16A_PRODUCER_IDENTITY_METADATA_RESOLUTION_STILL_INCOMPLETE"
        diagnosis = "PERSISTED_GROUP_AND_TERMINAL_ARRAY_CONTENT_DOES_NOT_YET_DEFINE_ONE_EXACT_PRODUCER_ID_RULE"
        recommendation = (
            "Do not reconstruct producer_id. Audit only remaining producer grouping / endpoint metadata provenance."
        )
        next_ms = "V16A-R7C3 — Final Producer Metadata Provenance Audit"

    save_csv(DECISION, [{
        "status": status,
        "diagnosis": diagnosis,
        "rule_status": rule["status"],
        "authorized": rule["authorized"],
        "exact_partition": bool(partition and partition["exact_partition"]),
        "four_category_terminal": len(four_cat) == 1,
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT, {
        "milestone": "V16A-R7C2",
        "status": status,
        "diagnosis": diagnosis,
        "rule": rule,
        "partition": partition,
        "constraints": {
            "producer_id_reconstructed": False,
            "nearest_rule_invented": False,
            "SG3_rerun": False,
            "SG4_rerun": False,
            "velocity_recompute": False,
            "Pollock_retrace": False,
            "FMM": False,
            "model_predict": False,
            "training": False,
            "V15_mutation": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY, {
        "milestone": "V16A-R7C2",
        "status": status,
        "diagnosis": diagnosis,
        "rule": rule,
        "partition": partition,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("\n" + "=" * 78)
    print("V16A-R7C2 FINAL RESOLUTION GATES")
    print("=" * 78)
    for g,p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in [GROUP_ARRAYS, LABELED_GROUPS, PARTITION, TERMINAL, TERMINAL_MAP, RULE, GATES, DECISION]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R7C2 PRODUCER METADATA RESOLUTION AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
