#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any


MILESTONE = "POSTV16-AV1-D-R7-R7D"
STATUS_PASS = (
    "AV1DR7R7D_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_DOMAIN_"
    "PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
STATUS_BLOCKED = "AV1DR7R7D_OCCUPANCY_DOMAIN_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R7C_COMMIT = "e4abe36f2a2ba24f28c958f04db29606b506b51b"

R7R7C = "PAD_Stream_POSTV16_AV1_D_R7_R7C_Support_Domain_Capacity_Failure_Closure.py"
R7R7C_BLOB = "a58f5910d2290ecb5a258af9ecf9a27afe6620ee"
R7R7B = "PAD_Stream_POSTV16_AV1_D_R7_R7B_Canonical_Solver_Native_Semantics_Execution.py"
R7R7B_BLOB = "c65fc15f630a097a81fbe6fe28dab87c7056ce65"
R7R7A = "PAD_Stream_POSTV16_AV1_D_R7_R7A_Canonical_Primary_Envelope_Arithmetic_Semantics_Freeze.py"
R7R7A_BLOB = "191792855ecbb2560475ca2066b307d6fef494d5"
R7R2 = "PAD_Stream_POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R7R7C:R7R7C_BLOB,
    R7R7B:R7R7B_BLOB,
    R7R7A:R7R7A_BLOB,
    R7R2:R7R2_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
}

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R7C_REL = BASE/"POSTV16_AV1_D_R7_R7C_Support_Domain_Capacity_Failure_Closure"
R7R7C_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7C_Summary.json"
R7R7C_CLOSURE = "POSTV16_AV1_D_R7_R7C_R7R7B_Failure_Closure.json"
R7R7C_MANIFEST = "POSTV16_AV1_D_R7_R7C_Artifact_Manifest.csv"

R7R7A_REL = BASE/"POSTV16_AV1_D_R7_R7A_Canonical_Primary_Envelope_Arithmetic_Semantics_Freeze"
R7R7A_PROTOCOL = "POSTV16_AV1_D_R7_R7A_Frozen_Canonical_Arithmetic_Semantics.json"
R7R7A_MANIFEST = "POSTV16_AV1_D_R7_R7A_Artifact_Manifest.csv"

R7R2_REL = BASE/"POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze"
R7R2_PROTOCOL = "POSTV16_AV1_D_R7_R2_Frozen_Reconciliation_Protocol.json"
R7R2_MANIFEST = "POSTV16_AV1_D_R7_R2_Artifact_Manifest.csv"

OUT_REL = BASE/"POSTV16_AV1_D_R7_R7D_Horizontal_Face_Halo_Occupancy_Domain_Freeze"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R7D_BLOCKED"

R7R7C_STATUS = (
    "AV1DR7R7C_R7R7B_SCIENTIFIC_FAIL_CLOSED_"
    "DAY365_SINGLE_SUPPORT_COMPONENT_CAPACITY_EXHAUSTION_LOCALIZED"
)
R7R7A_PROTOCOL_ID = "POSTV16_AV1_D_R7_R7A_SOLVER_NATIVE_UNSCALED_PRIMARY_ENVELOPE_SEMANTICS_V1"
R7R2_PROTOCOL_ID = "POSTV16_AV1_D_R7_R2_SUPPORT_GRAPH_MIN_COST_EXCESS_MASS_RECONCILIATION_V1"
NEW_PROTOCOL_ID = "POSTV16_AV1_D_R7_R7D_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_EXTENSION_V1"

GRID_SHAPE = [15,50,50]
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
HORIZONTAL_ENTRY_COST = 5.0
BACKGROUND_SATURATION = 0.20
MAX_SATURATION = 0.80

EXPECTED_DEFICIT_KG = 1629858.2850230522
EXPECTED_FAILED_DAY = 365.0
EXPECTED_COMPLETED = [30.0,60.0,100.0,150.0,250.0]


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def git_text(root: Path,*args: str) -> str:
    p=subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path,root: Path) -> str:
    return git_text(root,"hash-object",str(path))


def load_json(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str,str]]:
    with path.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path,name: str) -> dict[str,str]:
    rows=read_csv(directory/name)
    m={r["file"]:r["sha256"] for r in rows}
    for fn,expected in m.items():
        p=directory/fn
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{fn}")
        actual=sha256_file(p)
        if actual!=expected:
            raise GateError(f"manifest_SHA_mismatch:{fn}:{actual}:{expected}")
    return m


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n").encode("utf-8")


def csv_bytes(rows: list[dict[str,Any]]) -> bytes:
    if not rows:
        return b""
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode("utf-8")


def immutable_publish(out: Path,files: dict[str,bytes]) -> None:
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        p=out/name
        if p.exists() and p.read_bytes()!=data:
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def near(a: float,b: float,rtol: float=1e-13,atol: float=1e-8) -> bool:
    return abs(float(a)-float(b)) <= max(atol,rtol*max(abs(float(b)),1.0))


def self_test() -> None:
    # Pure geometry test of the frozen non-recursive same-layer x/y-face halo.
    S0={(0,1,1)}
    candidates=set()
    for k,j,i in S0:
        for dj,di in ((0,-1),(0,1),(-1,0),(1,0)):
            jj=j+dj; ii=i+di
            if 0<=jj<3 and 0<=ii<3:
                q=(k,jj,ii)
                if q not in S0:
                    candidates.add(q)
    expected={(0,1,0),(0,1,2),(0,0,1),(0,2,1)}
    if candidates!=expected:
        raise RuntimeError(f"halo_geometry:{sorted(candidates)}")
    if any(k!=0 for k,_,_ in candidates):
        raise RuntimeError("vertical_halo_created")
    print("POSTV16-AV1-D-R7-R7D self-test: PASS")


def main(root: Path,drive: Path) -> int:
    gates={};stage="preflight"
    out=drive/OUT_REL
    blocked=drive/BLOCKED_REL

    def gate(name: str,passed: Any,value: Any=None) -> None:
        ok=bool(passed)
        gates[name]={"passed":ok,"value":value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*196)
    print("POSTV16-AV1-D-R7-R7D — PROSPECTIVE CARTESIAN OCCUPANCY-DOMAIN EXTENSION DESIGN / FREEZE")
    print("="*196)
    print("DESIGN/FREEZE ONLY. NO MODEL INFERENCE. NO LP EXECUTION. NO FOUNDATION-CASE MAPBACK EXECUTION.")
    print("R7-R3, R7-R6, AND R7-R7B REMAIN IMMUTABLE FAILS.")
    print("THE NEW DOMAIN IS A SINGLE NON-RECURSIVE SAME-LAYER X/Y FACE-NEIGHBOR HALO AROUND EXACT SG7D SUPPORT.")
    print("HALO CELLS ARE TERMINAL OCCUPANCY SINKS ONLY — NEVER TRANSIT CELLS.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R7C_commit",parent==PARENT_R7R7C_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==blob,actual)

        stage="R7R7C_closure_binding"
        r7r7c=drive/R7R7C_REL
        gate("R7R7C_output_present",r7r7c.is_dir(),str(r7r7c))
        m7=verify_manifest(r7r7c,R7R7C_MANIFEST)
        gate("R7R7C_manifest_SHA_closure",True,len(m7))

        s7=load_json(r7r7c/R7R7C_SUMMARY)
        c7=load_json(r7r7c/R7R7C_CLOSURE)

        gate("R7R7C_status_exact",s7["status"]==R7R7C_STATUS,s7["status"])
        gate("R7R3_immutable_FAIL",s7["R7R3_result"]=="FAIL")
        gate("R7R6_immutable_FAIL",s7["R7R6_result"]=="FAIL")
        gate("R7R7B_immutable_FAIL",s7["R7R7B_result"]=="FAIL")
        gate("R7R7B_retest_forbidden",s7["R7R7B_retest_authorized"] is False)
        gate("R7R7D_freeze_authorized",s7["R7R7D_physical_domain_design_freeze_authorized"] is True)
        gate("first_failed_day365",float(s7["first_failed_target_day"])==EXPECTED_FAILED_DAY)
        gate("completed_times_exact",list(map(float,s7["completed_times"]))==EXPECTED_COMPLETED,s7["completed_times"])
        gate("support_graph_single_component",int(s7["support_graph_component_count"])==1,s7["support_graph_component_count"])
        gate("supported_domain_capacity_failure",s7["supported_domain_capacity_failure"] is True)
        gate("whole_grid_capacity_not_failure",s7["whole_grid_capacity_failure"] is False)
        gate("numerical_certification_not_failure",s7["numerical_certification_failure"] is False)
        gate("capacity_deficit_bound",near(float(s7["support_domain_capacity_deficit_kg"]),EXPECTED_DEFICIT_KG),
             s7["support_domain_capacity_deficit_kg"])

        cls=c7["classification"]
        gate("failure_class_exact",cls["failure_class"]=="SINGLE_CONNECTED_SUPPORT_DOMAIN_TOTAL_CAPACITY_EXHAUSTION")
        gate("frozen_support_capacity_failure_exact",cls["frozen_supported_domain_capacity_failure"] is True)
        gate("whole_grid_failure_false",cls["whole_grid_total_capacity_failure"] is False)
        gate("checkpoint_failure_false",cls["accepted_transport_checkpoint_failure"] is False)
        gate("B1_failure_false",cls["B1_failure"] is False)
        gate("EOS_failure_false",cls["EOS_failure"] is False)

        rules=c7["lineage_rules"]
        gate("do_not_enable_unsupported_sinks_in_R7R7B",rules["do_not_rerun_R7R7B_with_unsupported_sinks_enabled"] is True)
        gate("do_not_relax_bounds",rules["do_not_relax_saturation_bounds"] is True)
        gate("do_not_clip_mass",rules["do_not_clip_or_discard_mass"] is True)
        gate("do_not_global_rescale",rules["do_not_globally_rescale_saturation"] is True)
        gate("do_not_change_checkpoint_B1",rules["do_not_change_checkpoint_or_B1"] is True)
        gate("new_domain_requires_new_protocol",rules["future_physical_domain_change_requires_new_prospective_protocol"] is True)

        stage="prior_protocol_binding"
        r7r7a=drive/R7R7A_REL
        gate("R7R7A_output_present",r7r7a.is_dir(),str(r7r7a))
        ma=verify_manifest(r7r7a,R7R7A_MANIFEST)
        gate("R7R7A_manifest_SHA_closure",True,len(ma))
        pa=load_json(r7r7a/R7R7A_PROTOCOL)
        gate("canonical_arithmetic_protocol_exact",pa["protocol_id"]==R7R7A_PROTOCOL_ID,pa["protocol_id"])

        r7r2=drive/R7R2_REL
        gate("R7R2_output_present",r7r2.is_dir(),str(r7r2))
        m2=verify_manifest(r7r2,R7R2_MANIFEST)
        gate("R7R2_manifest_SHA_closure",True,len(m2))
        p2=load_json(r7r2/R7R2_PROTOCOL)
        gate("R7R2_protocol_exact",p2["protocol_id"]==R7R2_PROTOCOL_ID,p2["protocol_id"])
        gate("R7R2_primary_edge_cost_exact",
             p2["minimum_cost_flow"]["primary_edge_cost_units"]
             =="5*abs(delta_i) + 5*abs(delta_j) + abs(delta_k); 20-ft x/y cells therefore cost 5 units and 4-ft z cells cost 1 unit")
        gate("R7R2_B1_frozen",p2["prohibitions"]["change_B1_half_overlap"] is True)
        gate("R7R2_checkpoint_frozen",p2["prohibitions"]["change_accepted_checkpoint"] is True)
        gate("R7R2_Smax_frozen",p2["prohibitions"]["relax_Smax_above_0p80"] is True)

        stage="freeze_horizontal_halo_protocol"

        protocol={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":NEW_PROTOCOL_ID,
            "immutable_history":{
                "R7R3":"FAIL",
                "R7R6":"FAIL",
                "R7R7B":"FAIL",
                "prior_results_relabelled":False,
                "prior_failed_execution_rerun":False,
            },
            "design_basis":{
                "closed_failure":"SINGLE_CONNECTED_SUPPORT_DOMAIN_TOTAL_CAPACITY_EXHAUSTION",
                "first_failed_day":365.0,
                "known_supported_domain_deficit_kg":float(s7["support_domain_capacity_deficit_kg"]),
                "whole_grid_total_capacity_failed":False,
                "interpretation":(
                    "Exact streamline-crossed cells are adequate as a transport skeleton but "
                    "too restrictive as a finite-volume plume occupancy domain at later time. "
                    "The smallest grid-resolved domain enlargement is one non-recursive "
                    "face-adjacent lateral cell around that skeleton."
                ),
                "candidate_was_capacity_tested_before_freeze":False,
                "candidate_count":1,
            },
            "exact_support_set_S0":{
                "definition":"unique Cartesian cells crossed by frozen SG7D streamline subsegments",
                "source":"unchanged SG7D subsegment operator",
                "changed":False,
                "role":"transport backbone plus original occupancy cells",
            },
            "new_halo_set_H1":{
                "definition":(
                    "All in-bounds Cartesian cells not in S0 that share an x-face or y-face "
                    "with at least one S0 cell at the same k layer."
                ),
                "construction_offsets_ijk":[
                    [0,0,-1],
                    [0,0,1],
                    [0,-1,0],
                    [0,1,0],
                ],
                "computed_from":"S0 only",
                "recursive_growth":False,
                "same_layer_only":True,
                "vertical_neighbors_allowed":False,
                "diagonal_neighbors_allowed":False,
                "second_ring_neighbors_allowed":False,
                "maximum_center_to_center_off_skeleton_distance_ft":20.0,
                "role":"terminal finite-volume occupancy sinks only",
            },
            "extended_domain_D1":{
                "definition":"D1 = S0 union H1",
                "full_grid_opened_as_domain":False,
                "all_cells_outside_D1":"remain exactly background saturation 0.20 and receive zero component mass",
            },
            "graph_semantics":{
                "original_S0_to_S0_edges":"exact R7-R2 support graph, unchanged",
                "original_S0_graph_primary_cost":"5*|delta_i| + 5*|delta_j| + |delta_k|, unchanged",
                "new_edges":(
                    "For each S0-H1 x/y face adjacency, add a directed S0 -> H1 sink-entry arc."
                ),
                "new_edge_cost_units":HORIZONTAL_ENTRY_COST,
                "new_edge_cost_basis":"one frozen horizontal Cartesian step = 20 ft = 5 existing graph-distance units",
                "H1_to_S0_reverse_edges":False,
                "H1_to_H1_edges":False,
                "H1_as_transit_nodes":False,
                "cross_layer_new_edges":False,
                "purpose":(
                    "Allow the exact streamline support network to discharge conserved excess "
                    "component mass into immediately adjacent Cartesian pore volume without "
                    "creating a new transport shortcut network."
                ),
            },
            "mass_and_capacity_semantics":{
                "raw_subsegment_deposition":"unchanged; raw mass is first deposited only through the frozen SG7D/E37A operator",
                "S0_base_mass":"b_c = min(m_c, C_c), unchanged",
                "S0_excess_supply":"e_c = max(m_c - C_c, 0), unchanged",
                "S0_spare_capacity":"d_c = C_c - b_c, unchanged",
                "H1_initial_component_mass_kg":0.0,
                "H1_base_incremental_saturation":0.0,
                "H1_initial_total_saturation":BACKGROUND_SATURATION,
                "H1_spare_capacity":"full physical cell component-mass capacity from frozen R2 EOS at Sg=0.60",
                "mass_conservation":"exact up to frozen numerical tolerance",
                "mass_clipping_or_discarding":False,
                "global_rescaling":False,
            },
            "saturation_and_EOS":{
                "background_total_saturation":BACKGROUND_SATURATION,
                "maximum_total_saturation":MAX_SATURATION,
                "bounds_changed":False,
                "EOS":"frozen R2 gas-density and mass-to-saturation inversion, unchanged",
                "pressure_field":"frozen Foundation Case cell pressure",
                "porosity_and_cell_volume":"frozen Foundation Case physical cell values",
            },
            "canonical_numerics":{
                "protocol_id":R7R7A_PROTOCOL_ID,
                "solver_method":"highs-ds",
                "primary_envelope_semantics":"solver-native unscaled secondary inequality residual",
                "canonical_residual_floor":-1.0e-10,
                "math_fsum_and_numpy_dot":"diagnostic only",
                "changed":False,
            },
            "scientific_interpretation":{
                "claim_if_future_execution_passes":(
                    "A single one-cell lateral occupancy halo is sufficient for conservative "
                    "bounded end-to-end integration of Foundation Case 0001 across all nine "
                    "canonical times."
                ),
                "not_a_claim_of_plume_fidelity":True,
                "not_a_generalization_claim":True,
                "not_a_calibrated_dispersion_model":True,
                "reason_for_one_ring":(
                    "It is the minimal nonzero Cartesian-width correction to a zero-thickness "
                    "streamline occupancy skeleton and is frozen before testing its capacity."
                ),
            },
            "hard_gates_for_R7R7E":{
                "all_9_canonical_times_required":True,
                "S0_reconstructed_exactly_from_frozen_SG7D":True,
                "H1_constructed_only_from_S0_same_layer_xy_faces":True,
                "H1_nonrecursive":True,
                "H1_disjoint_from_S0":True,
                "every_H1_cell_has_S0_xy_face_parent":True,
                "no_vertical_or_diagonal_halo":True,
                "no_H1_transit_or_reverse_arcs":True,
                "S0_graph_unchanged":True,
                "raw_SG7D_E37A_deposition_unchanged":True,
                "B1_to_subsegment_mass_closure_unchanged":True,
                "component_and_global_capacity_feasibility":True,
                "canonical_solver_native_residual_gate":True,
                "node_balance_mass_conservation":True,
                "no_cell_capacity_exceeded":True,
                "EOS_mass_inversion_closure":True,
                "grid_saturation_bounds_0p20_0p80":True,
                "outside_D1_exact_background_and_zero_component_mass":True,
                "accepted_checkpoint_B1_C3_unchanged":True,
                "no_geology0031_or_acceptance_truth":True,
            },
            "prohibitions":{
                "second_ring_growth":True,
                "adaptive_ring_count":True,
                "capacity_driven_domain_growth_after_exposure":True,
                "vertical_halo":True,
                "diagonal_halo":True,
                "full_grid_sink_access":True,
                "halo_transit_shortcuts":True,
                "halo_reverse_arcs":True,
                "saturation_bound_relaxation":True,
                "mass_clipping":True,
                "mass_discard":True,
                "global_rescaling":True,
                "checkpoint_change":True,
                "B1_change":True,
                "C3_refit":True,
                "geology0031_use":True,
                "acceptance_truth_use":True,
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R7-R7E",
                "name":"Controlled execution of the frozen single-ring horizontal face-halo occupancy domain",
                "authorized":True,
                "candidate_count":1,
                "alternate_candidate_authorized":False,
            },
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":NEW_PROTOCOL_ID,
            "R7R3_result":"FAIL",
            "R7R6_result":"FAIL",
            "R7R7B_result":"FAIL",
            "new_domain":"single non-recursive same-layer x/y face-neighbor halo",
            "halo_transit_allowed":False,
            "halo_reverse_edges_allowed":False,
            "vertical_halo_allowed":False,
            "diagonal_halo_allowed":False,
            "adaptive_growth_allowed":False,
            "entry_cost_units":HORIZONTAL_ENTRY_COST,
            "physical_operator_execution_performed":False,
            "model_inference_performed":False,
            "LP_execution_performed":False,
            "candidate_capacity_pretested":False,
            "checkpoint_B1_bounds_changed":False,
            "canonical_arithmetic_changed":False,
            "R7R7E_authorized":True,
            "next":"POSTV16-AV1-D-R7-R7E — execute the one frozen horizontal face-halo occupancy candidate",
        }

        freeze={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":NEW_PROTOCOL_ID,
            "parent_closure":R7R7C_STATUS,
            "candidate_count":1,
            "execution_in_R7R7D":False,
            "foundation_capacity_pretest_in_R7R7D":False,
            "single_ring_xy_face_halo_frozen":True,
            "nonrecursive_frozen":True,
            "terminal_sink_only_frozen":True,
            "R7R2_support_graph_preserved":True,
            "R7R7A_arithmetic_preserved":True,
            "R7R7E_execution_authorized":True,
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R7D_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R7D_Frozen_Occupancy_Domain_Extension_Protocol.json":json_bytes(protocol),
            "POSTV16_AV1_D_R7_R7D_Protocol_Freeze_Contract.json":json_bytes(freeze),
            "POSTV16_AV1_D_R7_R7D_Final_Gate_Matrix.csv":csv_bytes(
                [{"gate":k,**v} for k,v in gates.items()]
            ),
        })

        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R7D_Artifact_Manifest.csv":
                manifest.append({
                    "file":p.name,
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        immutable_publish(out,{
            "POSTV16_AV1_D_R7_R7D_Artifact_Manifest.csv":csv_bytes(manifest)
        })

        print("\n"+"="*196)
        print("POSTV16-AV1-D-R7-R7D: PASS")
        print("="*196)
        print(f"{'Status':116}: {STATUS_PASS}")
        print(f"{'Immutable R7-R3 / R7-R6 / R7-R7B results':116}: FAIL / FAIL / FAIL")
        print(f"{'Frozen occupancy protocol':116}: {NEW_PROTOCOL_ID}")
        print(f"{'Exact support S0':116}: unchanged SG7D-crossed Cartesian cells")
        print(f"{'Halo H1':116}: one non-recursive same-layer x/y face-neighbor ring")
        print(f"{'Vertical / diagonal / second-ring halo':116}: False / False / False")
        print(f"{'Halo role':116}: terminal occupancy sinks only")
        print(f"{'Halo reverse / halo-halo transit edges':116}: False / False")
        print(f"{'Halo entry cost':116}: 5 graph-distance units")
        print(f"{'R7-R2 support graph / B1 / checkpoint / bounds changed':116}: False / False / False / False")
        print(f"{'R7-R7A canonical arithmetic changed':116}: False")
        print(f"{'Model inference / LP / mapback execution in R7-R7D':116}: False / False / False")
        print(f"{'Candidate capacity pretested before freeze':116}: False")
        print(f"{'R7-R7E one-candidate execution authorized':116}: True")
        print(f"{'NEXT':116}: POSTV16-AV1-D-R7-R7E — execute frozen horizontal face-halo occupancy domain")
        print("="*196)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_BLOCKED,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "R7R3_result_changed":False,
            "R7R6_result_changed":False,
            "R7R7B_result_changed":False,
            "model_inference_performed":False,
            "LP_execution_performed":False,
            "mapback_execution_performed":False,
            "R7R7E_authorized":False,
            "next_action":(
                "Audit only the R7-R7D design/freeze. Do not execute a domain "
                "extension unless this single candidate is validly frozen."
            ),
        }
        data=json_bytes(report)
        p=blocked/"POSTV16_AV1_D_R7_R7D_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R7D_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*196)
        print("POSTV16-AV1-D-R7-R7D: BLOCKED")
        print("="*196)
        print("Failed stage:",stage)
        print("Exception   :",repr(exc))
        print("Report      :",p)
        return 2


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    a=parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
