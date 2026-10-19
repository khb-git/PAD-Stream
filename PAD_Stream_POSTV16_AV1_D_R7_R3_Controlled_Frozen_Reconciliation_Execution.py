#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from scipy.sparse.csgraph import connected_components

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")


MILESTONE = "POSTV16-AV1-D-R7-R3"
STATUS_PASS = (
    "AV1DR7R3_FROZEN_SUPPORT_GRAPH_RECONCILIATION_EXECUTED_ALL_9_TIMES_"
    "END_TO_END_BOUNDED_CONSERVATIVE_INTEGRATION_PASS"
)
STATUS_FAIL = (
    "AV1DR7R3_FROZEN_SUPPORT_GRAPH_RECONCILIATION_EXECUTION_FAIL_"
    "NO_ADAPTATION_OR_ALTERNATE_REPAIR_AUTHORIZED"
)
STATUS_BLOCKED = "AV1DR7R3_TECHNICAL_EXECUTION_BLOCKED_BEFORE_VALID_DECISION"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R2_COMMIT = "3e3d9e0a54829a6b16cc10cbb9d27b54a4b500e5"

R7R2 = "PAD_Stream_POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"
R7R1 = "PAD_Stream_POSTV16_AV1_D_R7_R1_E37A_Mapback_Capacity_Failure_Localization.py"
R7R1_BLOB = "734fe31b3ff3cc6d40c33ebb9b0162b02e99a368"
R7 = "PAD_Stream_POSTV16_AV1_D_R7_Full_End_to_End_PAD_Stream_Integration.py"
R7_BLOB = "a28722b0b8059bd50d94fb8a914defc0b35f2f7b"
R6 = "PAD_Stream_POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding.py"
R6_BLOB = "1ca67ca946683eeb31fbba7d31fba2613d5c0f6f"
B2 = "PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B2_BLOB = "95025d1e67a74f9dacaad311e5a402b63e7b4335"
C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"
C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"
B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R7R2:R7R2_BLOB, R7R1:R7R1_BLOB, R7:R7_BLOB, R6:R6_BLOB,
    B2:B2_BLOB, C2:C2_BLOB, C26:C26_BLOB, B1:B1_BLOB,
    R2:R2_BLOB, E37A:E37A_BLOB, SG7D:SG7D_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R2_REL = BASE / "POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze"
R7R2_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R2_Summary.json"
R7R2_PROTOCOL = "POSTV16_AV1_D_R7_R2_Frozen_Reconciliation_Protocol.json"
R7R2_FREEZE = "POSTV16_AV1_D_R7_R2_Protocol_Freeze_Contract.json"
R7R2_MANIFEST = "POSTV16_AV1_D_R7_R2_Artifact_Manifest.csv"

R6_REL = BASE / "POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding"
R6_WEIGHTS = "POSTV16_AV1_D_R6_ACCEPTED_TRANSPORT_FROZEN.weights.h5"
R6_NORM = "POSTV16_AV1_D_R6_C3_Conditioning_Normalization_Parameters.npz"

OUT_REL = BASE / "POSTV16_AV1_D_R7_R3_Controlled_Frozen_Reconciliation_Execution"
BLOCKED_REL = BASE / "POSTV16_AV1_D_R7_R3_BLOCKED"

R7R2_STATUS = (
    "AV1DR7R2_CONSERVATIVE_BOUNDED_SUPPORT_GRAPH_OVERLAP_OCCUPANCY_"
    "RECONCILIATION_PROTOCOL_PROSPECTIVELY_FROZEN"
)
PROTOCOL_ID = "POSTV16_AV1_D_R7_R2_SUPPORT_GRAPH_MIN_COST_EXCESS_MASS_RECONCILIATION_V1"

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"
WEIGHTS_SHA = "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"
NORM_SHA = "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"

DAYS = np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.], dtype=np.float64)
GRID = (15,50,50)
NZ,NY,NX = GRID
NSL = 1078
NN = 201
NCV = 200
NT = 9
NSAMP = NSL*NT
DX = 6.096
DY = 6.096
DZ = 1.2192
BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60

EXPECTED_DAY30_OVERLOADED = 546
EXPECTED_DAY30_MAX_EXCESS = 9471.745379391963


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
    return git_text(root,"hash-object",str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str,str]]:
    with path.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str,str]:
    rows = read_csv(directory/name)
    m = {r["file"]:r["sha256"] for r in rows}
    for fn,expected in m.items():
        p = directory/fn
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{fn}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA_mismatch:{fn}:{actual}:{expected}")
    return m


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n").encode("utf-8")


def csv_bytes(rows: list[dict[str,Any]]) -> bytes:
    if not rows:
        return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str,Any]) -> bytes:
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            b=io.BytesIO()
            np.save(b,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy",date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16
            zf.writestr(info,b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str,bytes]) -> None:
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        p=out/name
        if p.exists() and p.read_bytes()!=data:
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def find_named_exact(roots: list[Path], name: str, expected_sha: str) -> Path:
    hits=[]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p)==expected_sha:
                    hits.append(p.resolve())
            except OSError:
                pass
    if not hits:
        raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    return sorted(set(hits),key=lambda p:(len(str(p)),str(p)))[0]


def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def build_support_graph(operator: dict[str,np.ndarray]) -> dict[str,Any]:
    stream=np.asarray(operator["streamline"],dtype=np.int64)
    flat=np.asarray(operator["flat_cell"],dtype=np.int64)
    nodes=np.unique(flat)
    lookup=np.full(NX*NY*NZ,-1,dtype=np.int64)
    lookup[nodes]=np.arange(len(nodes),dtype=np.int64)

    same=stream[1:]==stream[:-1]
    a=flat[:-1][same]
    b=flat[1:][same]
    keep=a!=b
    a=a[keep];b=b[keep]
    lo=np.minimum(a,b);hi=np.maximum(a,b)
    pairs=np.unique(np.stack([lo,hi],axis=1),axis=0)
    edge_u=lookup[pairs[:,0]]
    edge_v=lookup[pairs[:,1]]

    def coords(f):
        i=f%NX
        j=(f//NX)%NY
        k=f//(NX*NY)
        return k,j,i

    ku,ju,iu=coords(pairs[:,0])
    kv,jv,iv=coords(pairs[:,1])
    edge_cost=(
        5.0*np.abs(iu-iv)
        +5.0*np.abs(ju-jv)
        +1.0*np.abs(ku-kv)
    ).astype(np.float64)

    rows=np.concatenate([edge_u,edge_v])
    cols=np.concatenate([edge_v,edge_u])
    adj=sparse.csr_matrix(
        (np.ones(len(rows),dtype=np.int8),(rows,cols)),
        shape=(len(nodes),len(nodes)),
    )
    ncomp,labels=connected_components(adj,directed=False,return_labels=True)

    return {
        "nodes":nodes,
        "lookup":lookup,
        "edge_pairs_flat":pairs,
        "edge_u":edge_u,
        "edge_v":edge_v,
        "edge_cost":edge_cost,
        "component_labels":labels.astype(np.int64),
        "n_components":int(ncomp),
    }


def solve_component_lp(
    component_nodes: np.ndarray,
    component_edge_ids: np.ndarray,
    graph: dict[str,Any],
    excess_all: np.ndarray,
    spare_all: np.ndarray,
) -> dict[str,Any]:
    component_nodes=np.asarray(component_nodes,dtype=np.int64)
    component_edge_ids=np.asarray(component_edge_ids,dtype=np.int64)
    n=len(component_nodes)

    local_lookup=np.full(len(graph["nodes"]),-1,dtype=np.int64)
    local_lookup[component_nodes]=np.arange(n,dtype=np.int64)

    gu=graph["edge_u"][component_edge_ids]
    gv=graph["edge_v"][component_edge_ids]
    eu=local_lookup[gu]
    ev=local_lookup[gv]
    ecost=graph["edge_cost"][component_edge_ids]
    ne=len(component_edge_ids)
    ndir=2*ne
    nvar=ndir+n

    rows=[];cols=[];data=[]
    for e in range(ne):
        u=int(eu[e]);v=int(ev[e])
        rows.extend([u,v]);cols.extend([2*e,2*e]);data.extend([1.0,-1.0])
        rows.extend([v,u]);cols.extend([2*e+1,2*e+1]);data.extend([1.0,-1.0])
    for i in range(n):
        rows.append(i);cols.append(ndir+i);data.append(1.0)

    Aeq=sparse.csr_matrix((data,(rows,cols)),shape=(n,nvar))
    rhs=np.asarray(excess_all[component_nodes],dtype=np.float64)
    spare=np.asarray(spare_all[component_nodes],dtype=np.float64)

    c_primary=np.zeros(nvar,dtype=np.float64)
    if ne:
        c_primary[0:ndir:2]=ecost
        c_primary[1:ndir:2]=ecost

    bounds=[(0.0,None)]*ndir+[(0.0,float(x)) for x in spare]

    primary=linprog(
        c_primary,A_eq=Aeq,b_eq=rhs,bounds=bounds,method="highs"
    )
    if not primary.success:
        raise ScientificFail(
            "LP_primary_success_all_times",
            {"status":int(primary.status),"message":str(primary.message)},
        )

    optimum=float(primary.fun)
    tol_obj=max(1.0e-8,1.0e-12*max(abs(optimum),1.0))

    c_tie=np.zeros(nvar,dtype=np.float64)
    if ndir:
        c_tie[:ndir]=(np.arange(ndir,dtype=np.float64)+1.0)/float(ndir)
    if n:
        c_tie[ndir:]=(np.arange(n,dtype=np.float64)+1.0)/float(n)

    Aub=sparse.csr_matrix(c_primary.reshape(1,-1))
    tie=linprog(
        c_tie,A_ub=Aub,b_ub=np.array([optimum+tol_obj]),
        A_eq=Aeq,b_eq=rhs,bounds=bounds,method="highs",
    )
    if not tie.success:
        raise ScientificFail(
            "LP_tiebreak_success_all_times",
            {"status":int(tie.status),"message":str(tie.message)},
        )

    x=np.asarray(tie.x,dtype=np.float64)
    balance=np.asarray(Aeq@x-rhs,dtype=np.float64)
    total_excess=float(np.sum(rhs))
    bal_tol=max(1.0e-7,1.0e-11*max(total_excess,1.0))
    max_balance=float(np.max(np.abs(balance))) if len(balance) else 0.0
    if max_balance>bal_tol:
        raise ScientificFail(
            "max_node_balance_residual_kg",
            {"residual":max_balance,"tolerance":bal_tol},
        )

    actual_primary=float(np.dot(c_primary,x))
    if actual_primary>optimum+tol_obj+1.0e-8:
        raise ScientificFail(
            "tiebreak_preserves_primary_optimum",
            {
                "primary_optimum":optimum,
                "tie_primary_cost":actual_primary,
                "tolerance":tol_obj,
            },
        )

    absorption=x[ndir:]
    if np.any(absorption < -1.0e-8) or np.any(absorption-spare>1.0e-7):
        raise ScientificFail("absorption_bounds",None)

    return {
        "absorption":absorption,
        "primary_optimum":optimum,
        "tie_primary_cost":actual_primary,
        "tie_objective":float(tie.fun),
        "total_directed_edge_flow_kg":float(np.sum(x[:ndir])),
        "maximum_directed_edge_flow_kg":float(np.max(x[:ndir])) if ndir else 0.0,
        "max_node_balance_residual_kg":max_balance,
        "balance_tolerance_kg":bal_tol,
        "primary_objective_tolerance":tol_obj,
    }


def reconcile_mass(
    raw_mass_grid: np.ndarray,
    capacity_grid: np.ndarray,
    graph: dict[str,Any],
) -> tuple[np.ndarray,dict[str,Any],list[dict[str,Any]]]:
    raw=np.asarray(raw_mass_grid,dtype=np.float64).reshape(-1)
    cap=np.asarray(capacity_grid,dtype=np.float64).reshape(-1)
    nodes=graph["nodes"]
    labels=graph["component_labels"]
    edge_u=graph["edge_u"]
    edge_v=graph["edge_v"]

    supported_raw=raw[nodes]
    supported_cap=cap[nodes]
    base=np.minimum(supported_raw,supported_cap)
    excess=np.maximum(supported_raw-supported_cap,0.0)
    spare=supported_cap-base

    total_raw=float(np.sum(raw))
    total_cap=float(np.sum(cap))
    global_tol=max(1.0e-7,1.0e-11*max(abs(total_raw),1.0))
    if total_raw>total_cap+global_tol:
        raise ScientificFail(
            "global_mass_feasibility_all_times",
            {"raw_mass_kg":total_raw,"capacity_kg":total_cap,"tolerance_kg":global_tol},
        )

    final_supported=base.copy()
    comp_rows=[]
    active_components=0
    total_primary=0.0
    total_tie_primary=0.0
    total_edge_flow=0.0
    max_edge_flow=0.0
    max_balance=0.0
    max_component_mass_residual=0.0

    for comp in range(graph["n_components"]):
        cnodes=np.flatnonzero(labels==comp)
        if not len(cnodes):
            continue
        supply=float(np.sum(excess[cnodes]))
        available=float(np.sum(spare[cnodes]))
        tol=max(1.0e-7,1.0e-11*max(supply,1.0))

        if supply>available+tol:
            raise ScientificFail(
                "component_feasibility_all_times",
                {
                    "component":int(comp),
                    "excess_supply_kg":supply,
                    "spare_capacity_kg":available,
                    "tolerance_kg":tol,
                },
            )

        if supply<=tol:
            comp_rows.append({
                "component":int(comp),
                "node_count":int(len(cnodes)),
                "edge_count":int(np.sum(labels[edge_u]==comp)),
                "excess_supply_kg":supply,
                "spare_capacity_kg":available,
                "LP_executed":False,
                "primary_optimum":0.0,
                "component_mass_residual_kg":0.0,
            })
            continue

        active_components+=1
        eids=np.flatnonzero(labels[edge_u]==comp)
        if np.any(labels[edge_v[eids]]!=comp):
            raise GateError("support_graph_cross_component_edge")

        sol=solve_component_lp(cnodes,eids,graph,excess,spare)
        final_supported[cnodes]+=sol["absorption"]

        before=float(np.sum(supported_raw[cnodes]))
        after=float(np.sum(final_supported[cnodes]))
        cres=after-before
        ctol=max(1.0e-7,1.0e-11*max(abs(before),1.0))
        if abs(cres)>ctol:
            raise ScientificFail(
                "cross_support_component_transfer_exact_zero",
                {"component":int(comp),"mass_residual_kg":cres,"tolerance_kg":ctol},
            )

        max_component_mass_residual=max(max_component_mass_residual,abs(cres))
        total_primary+=sol["primary_optimum"]
        total_tie_primary+=sol["tie_primary_cost"]
        total_edge_flow+=sol["total_directed_edge_flow_kg"]
        max_edge_flow=max(max_edge_flow,sol["maximum_directed_edge_flow_kg"])
        max_balance=max(max_balance,sol["max_node_balance_residual_kg"])

        comp_rows.append({
            "component":int(comp),
            "node_count":int(len(cnodes)),
            "edge_count":int(len(eids)),
            "excess_supply_kg":supply,
            "spare_capacity_kg":available,
            "LP_executed":True,
            "primary_optimum":sol["primary_optimum"],
            "tie_primary_cost":sol["tie_primary_cost"],
            "tie_objective":sol["tie_objective"],
            "total_directed_edge_flow_kg":sol["total_directed_edge_flow_kg"],
            "maximum_directed_edge_flow_kg":sol["maximum_directed_edge_flow_kg"],
            "max_node_balance_residual_kg":sol["max_node_balance_residual_kg"],
            "component_mass_residual_kg":cres,
        })

    final=np.zeros_like(raw)
    final[nodes]=final_supported

    unsupported=np.ones(len(raw),dtype=bool)
    unsupported[nodes]=False
    if not np.array_equal(final[unsupported],np.zeros(np.sum(unsupported),dtype=np.float64)):
        raise ScientificFail("unsupported_cell_added_mass_exact_zero",None)

    max_cap_excess=float(np.max(final-cap))
    cap_tol=max(1.0e-7,1.0e-11*max(float(np.max(cap)),1.0))
    if max_cap_excess>cap_tol:
        raise ScientificFail(
            "max_capacity_excess_after_reconciliation_kg",
            {"excess":max_cap_excess,"tolerance":cap_tol},
        )

    final_total=float(np.sum(final))
    rel=abs(final_total-total_raw)/max(abs(total_raw),1.0)
    if rel>1.0e-10:
        raise ScientificFail(
            "total_component_mass_relative_closure",
            {"relative_residual":rel,"raw_total_kg":total_raw,"final_total_kg":final_total},
        )

    diag={
        "raw_total_component_mass_kg":total_raw,
        "final_total_component_mass_kg":final_total,
        "global_capacity_kg":total_cap,
        "global_capacity_fraction":total_raw/total_cap if total_cap>0 else 0.0,
        "raw_overloaded_cell_count":int(np.sum(raw-cap>cap_tol)),
        "raw_max_capacity_excess_kg":float(np.max(raw-cap)),
        "raw_total_excess_supply_kg":float(np.sum(excess)),
        "recipient_cell_count":int(np.sum(final_supported>base+1.0e-9)),
        "active_component_count":int(active_components),
        "primary_min_cost_total":float(total_primary),
        "tie_solution_primary_cost_total":float(total_tie_primary),
        "total_directed_edge_flow_kg":float(total_edge_flow),
        "maximum_directed_edge_flow_kg":float(max_edge_flow),
        "max_node_balance_residual_kg":float(max_balance),
        "max_component_mass_residual_kg":float(max_component_mass_residual),
        "max_capacity_excess_after_reconciliation_kg":float(max_cap_excess),
        "total_component_mass_relative_closure":float(rel),
        "unsupported_added_mass_exact_zero":True,
    }
    return final.reshape(GRID),diag,comp_rows


def self_test() -> None:
    # Three-node support chain, source overload 2 kg, first receiver accepts 1,
    # second receiver accepts the remaining 1. Frozen node balance is tested.
    graph={
        "nodes":np.array([0,1,2],dtype=np.int64),
        "edge_u":np.array([0,1],dtype=np.int64),
        "edge_v":np.array([1,2],dtype=np.int64),
        "edge_cost":np.array([5.0,5.0],dtype=np.float64),
    }
    excess=np.array([2.0,0.0,0.0])
    spare=np.array([0.0,1.0,3.0])
    sol=solve_component_lp(
        np.array([0,1,2],dtype=np.int64),
        np.array([0,1],dtype=np.int64),
        graph,excess,spare,
    )
    a=sol["absorption"]
    if not np.allclose(a,[0.0,1.0,1.0],rtol=0,atol=1e-8):
        raise RuntimeError(f"synthetic_absorption:{a}")
    if abs(sol["primary_optimum"]-15.0)>1e-8:
        raise RuntimeError(f"synthetic_primary:{sol['primary_optimum']}")
    print("POSTV16-AV1-D-R7-R3 self-test: PASS")


def main(root: Path, drive: Path) -> int:
    import tensorflow as tf

    gates: dict[str,dict[str,Any]]={}
    stage="preflight"
    inference_performed=False
    reconciliation_started=False
    completed_times=0
    out=drive/OUT_REL
    blocked=drive/BLOCKED_REL

    def gate(name: str, passed: Any, value: Any=None) -> None:
        ok=bool(passed)
        gates[name]={"passed":ok,"value":value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, passed: Any, value: Any=None) -> None:
        ok=bool(passed)
        gates[name]={"passed":ok,"value":value,"scientific_execution_gate":True}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" — {value}" if value is not None else ""))
        if not ok:
            raise ScientificFail(name,value)

    print("="*188)
    print("POSTV16-AV1-D-R7-R3 — CONTROLLED EXECUTION OF FROZEN SUPPORT-GRAPH RECONCILIATION")
    print("="*188)
    print("SINGLE FROZEN CANDIDATE. ALL 9 CANONICAL TIMES. FOUNDATION CASE 0001.")
    print("NO TRAINING. NO CHECKPOINT/B1 CHANGE. NO GEOLOGY0031. NO ACCEPTANCE TRUTH. NO ALTERNATE REPAIR.")
    print("A SCIENTIFIC FAIL DOES NOT AUTHORIZE RETUNING OR A SECOND RECONCILIATION CANDIDATE.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R2_commit",parent==PARENT_R7R2_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==blob,actual)

        stage="R7R2_protocol_binding"
        r7r2=drive/R7R2_REL
        gate("R7R2_output_present",r7r2.is_dir(),str(r7r2))
        m=verify_manifest(r7r2,R7R2_MANIFEST)
        gate("R7R2_manifest_SHA_closure",True,len(m))
        s=load_json(r7r2/R7R2_SUMMARY)
        protocol=load_json(r7r2/R7R2_PROTOCOL)
        freeze=load_json(r7r2/R7R2_FREEZE)

        gate("R7R2_status_exact",s["status"]==R7R2_STATUS,s["status"])
        gate("R7R2_protocol_id_exact",s["protocol_id"]==PROTOCOL_ID,s["protocol_id"])
        gate("R7R2_no_prior_repair_execution",s["repair_execution_performed"] is False)
        gate("R7R2_no_prior_model_inference",s["model_inference_performed"] is False)
        gate("R7R2_checkpoint_unmodified",s["accepted_checkpoint_modified"] is False)
        gate("R7R2_R7R3_authorized",s["R7R3_authorized"] is True)
        gate("R7R2_protocol_status_exact",protocol["status"]==R7R2_STATUS)
        gate("R7R2_protocol_id_identity",protocol["protocol_id"]==PROTOCOL_ID)
        gate("R7R2_single_candidate",int(freeze["candidate_count"])==1,freeze["candidate_count"])
        gate("R7R2_repair_search_forbidden",protocol["next"]["repair_search_authorized"] is False)
        gate("R7R2_alternate_candidate_forbidden",protocol["next"]["alternate_reconciliation_candidate_authorized"] is False)
        gate("R7R2_unsupported_sink_forbidden",protocol["support_graph"]["unsupported_cells_eligible"] is False)
        gate("R7R2_cross_component_transfer_forbidden",protocol["support_graph"]["cross_component_mass_transfer_allowed"] is False)
        gate("R7R2_no_global_rescaling",protocol["prohibitions"]["global_saturation_rescaling"] is True)
        gate("R7R2_no_Smax_relaxation",protocol["prohibitions"]["relax_Smax_above_0p80"] is True)
        gate("R7R2_no_B1_change",protocol["prohibitions"]["change_B1_half_overlap"] is True)
        gate("R7R2_no_checkpoint_change",protocol["prohibitions"]["change_accepted_checkpoint"] is True)
        gate("R7R2_no_geology0031",protocol["prohibitions"]["use_geology0031"] is True)
        gate("R7R2_all_9_required",protocol["hard_execution_gates_for_R7R3"]["all_9_canonical_times"] is True)

        stage="runtime_authority_binding"
        r6=drive/R6_REL
        weights=r6/R6_WEIGHTS
        norm=r6/R6_NORM
        gate("R6_weights_SHA_exact",weights.is_file() and sha256_file(weights)==WEIGHTS_SHA)
        gate("R6_norm_SHA_exact",norm.is_file() and sha256_file(norm)==NORM_SHA)
        foundation=find_named_exact([root,drive],FOUNDATION_NAME,FOUNDATION_SHA)
        gate("foundation_case0001_SHA_exact",sha256_file(foundation)==FOUNDATION_SHA,str(foundation))

        with np.load(foundation,allow_pickle=False) as z:
            keys=["Kx","Ky","Kz","porosity","pressure","Qx","Qy","Qz","Vx","Vy","Vz","streamline_xyz","pollock_tof","streamline_weight"]
            gate("foundation_required_arrays_present",set(keys).issubset(set(z.files)),sorted(z.files))
            d={k:np.asarray(z[k]).copy() for k in keys}

        stage="canonical_conditioning"
        r7=load_module(root/R7,"r7r3_r7")
        b2=load_module(root/B2,"r7r3_b2")
        c2=load_module(root/C2,"r7r3_c2")
        c26=load_module(root/C26,"r7r3_c26")
        b1=load_module(root/B1,"r7r3_b1")
        r2=load_module(root/R2,"r7r3_r2")
        e37a=load_module(root/E37A,"r7r3_e37a")

        pressure=np.asarray(d["pressure"],dtype=np.float64)
        cx,cy,cz=r7.face_to_cell(d["Vx"],d["Vy"],d["Vz"])
        _,_,_,source_mask,_=b2.bind_injector_sources(d["Qx"],d["Qy"],d["Qz"])
        adv,adv_audit=r7.solve_adv(cx,cy,cz,np.asarray(source_mask,bool),DX,DY,DZ)
        gate("ADV_relative_PDE_residual_lt_1e8",adv_audit["relative_L2_residual"]<1e-8,adv_audit["relative_L2_residual"])

        xyz=np.asarray(d["streamline_xyz"],dtype=np.float64)
        ptau=np.asarray(d["pollock_tof"],dtype=np.float64)
        terminal=ptau[:,-1]
        gate("Pollock_terminal_TOF_positive",np.all(terminal>0),[float(np.min(terminal)),float(np.max(terminal))])

        xi=np.linspace(0.0,1.0,NN)
        origin=np.array([0.0,0.0,0.0],dtype=np.float64)
        adv_s,_=c2.trilinear(adv,xyz,DX,DY,DZ,origin)
        kx_s,_=c2.trilinear(d["Kx"],xyz,DX,DY,DZ,origin)
        ky_s,_=c2.trilinear(d["Ky"],xyz,DX,DY,DZ,origin)
        kz_s,_=c2.trilinear(d["Kz"],xyz,DX,DY,DZ,origin)
        phi_s,_=c2.trilinear(d["porosity"],xyz,DX,DY,DZ,origin)
        p_s,_=c2.trilinear(pressure,xyz,DX,DY,DZ,origin)

        with np.load(norm,allow_pickle=False) as z:
            pmean=float(np.asarray(z["pressure_mean_psi"]).reshape(-1)[0])
            pstd=float(np.asarray(z["pressure_std_psi"]).reshape(-1)[0])

        Kh=np.sqrt(np.maximum(kx_s,1e-30)*np.maximum(ky_s,1e-30))
        X7=np.stack([
            np.broadcast_to(xi[None,:],(NSL,NN)),
            ptau/terminal[:,None],
            adv_s/terminal[:,None],
            np.log10(np.maximum(Kh,1e-30)),
            np.log10(np.maximum(kz_s,1e-30)/np.maximum(Kh,1e-30)),
            phi_s,
            (p_s-pmean)/pstd,
        ],axis=-1).astype(np.float32)

        X7f=np.broadcast_to(X7[None],(NT,NSL,NN,7)).reshape(NSAMP,NN,7).copy()
        time_hat=np.repeat(DAYS,NSL).astype(np.float32)/1000.0
        eta=DAYS[:,None]*86400.0/terminal[None,:]
        eta_seq=np.repeat(eta[:,:,None],NN,axis=2).reshape(NSAMP,NN).astype(np.float32)
        T=np.broadcast_to(time_hat[:,None,None],(NSAMP,NN,1)).astype(np.float32)
        X9=np.concatenate([X7f,T,eta_seq[:,:,None]],axis=2).astype(np.float32)
        gate("C26_runtime_input_shape_exact",X9.shape==(NSAMP,NN,9),X9.shape)
        gate("C26_runtime_input_finite",np.isfinite(X9).all())

        stage="accepted_transport_inference"
        try:
            tf.config.experimental.enable_op_determinism()
        except Exception:
            pass
        tf.keras.utils.set_random_seed(16021)
        model=c26.model()
        gate("C26_parameter_count_52033",model.count_params()==52033,model.count_params())
        model.load_weights(weights)
        pred_flat=model.predict(X9,batch_size=64,verbose=0).astype(np.float64)
        inference_performed=True
        sci_gate("accepted_transport_prediction_shape_exact",pred_flat.shape==(NSAMP,NN),pred_flat.shape)
        sci_gate("accepted_transport_prediction_finite",np.isfinite(pred_flat).all())
        sci_gate(
            "accepted_transport_saturation_bounds",
            float(np.min(pred_flat))>=BACKGROUND-1e-12 and float(np.max(pred_flat))<=INJECTED+1e-12,
            [float(np.min(pred_flat)),float(np.max(pred_flat))],
        )
        pred201=pred_flat.reshape(NT,NSL,NN)

        stage="B1_exact_representation_bridge"
        with tempfile.TemporaryDirectory(prefix="POSTV16_R7R3_SG7D_") as td:
            td=Path(td)
            sg7d_path=td/SG7D
            sg7d_path.write_bytes((root/SG7D).read_bytes())
            sg7d=load_module(sg7d_path,"r7r3_sg7d")

            operator=sg7d.build_subsegment_operator(
                xyz,
                ptau/float(e37a.DAY_TO_S),
                np.asarray(d["streamline_weight"],dtype=np.float64)*float(e37a.DAY_TO_S),
            )

            injection_pc=float(
                r2.capillary_pressure_from_incremental_sg(
                    float(r2.MAX_INCREMENTAL_CO2_SATURATION)
                )
            )
            injector_pw_pa=np.array([
                pressure[k,int(r2.INJECTOR_J),int(r2.INJECTOR_I)]*float(r2.PSI_TO_PA)
                for k in r2.COMPLETION_K
            ],dtype=np.float64)
            p_ref=float(np.mean(injector_pw_pa)+injection_pc)
            gate("reference_gas_pressure_finite",np.isfinite(p_ref),p_ref)

            geometry=e37a.build_control_volume_geometry(
                r2,operator,pressure,p_ref,NSL,NCV
            )
            coeff=np.asarray(geometry["cv_pressure_mass_coeff"],dtype=np.float64)
            gate("E37A_coeff_shape_exact",coeff.shape==(NSL,NCV),coeff.shape)
            gate("E37A_coeff_positive_finite",np.isfinite(coeff).all() and np.all(coeff>0))

            ids=np.tile(np.arange(NSL,dtype=np.int64),NT)
            pred200_flat,pred_mass_flat,pred_source_mass_flat=(
                b1.project_201_to_200_component_mass(
                    r2,e37a,pred201.reshape(-1,NN),coeff,ids
                )
            )
            pred200=pred200_flat.reshape(NT,NSL,NCV)
            pred_mass=pred_mass_flat.reshape(NT,NSL,NCV)
            pred_source_mass=pred_source_mass_flat.reshape(NT,NSL,NN)

            den=np.maximum(np.abs(np.sum(pred_mass,axis=(1,2))),1.0)
            cvtot=np.sum(pred_mass,axis=(1,2))
            srctot=np.sum(pred_source_mass,axis=(1,2))
            closures=np.abs(cvtot-srctot)/den
            sci_gate("same_B1_201_to_200_projection",float(np.max(closures))<=1e-12,float(np.max(closures)))

            naive=.5*(pred201[:,:,:-1]+pred201[:,:,1:])
            sci_gate(
                "direct_saturation_averaging_not_used",
                float(np.max(np.abs(pred200-naive)))>1e-12,
                float(np.max(np.abs(pred200-naive))),
            )

            stage="support_graph_freeze_execution"
            graph=build_support_graph(operator)
            gate("support_graph_nonempty",len(graph["nodes"])>0 and len(graph["edge_u"])>0,[len(graph["nodes"]),len(graph["edge_u"])])
            gate("support_graph_components_positive",graph["n_components"]>=1,graph["n_components"])
            gate("support_graph_no_cross_component_edges",np.all(graph["component_labels"][graph["edge_u"]]==graph["component_labels"][graph["edge_v"]]))

            flat=np.asarray(geometry["flat_cell"],dtype=np.int64)
            cv_id=np.asarray(geometry["cv_id"],dtype=np.int64)
            pv=np.asarray(geometry["pv_m3"],dtype=np.float64)
            pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)

            cell_pv=DX*DY*DZ*0.20
            smax=np.full(GRID,INJECTED,dtype=np.float64)
            rho_max=np.asarray(
                r2.gas_density_from_state(smax,pressure,p_ref),
                dtype=np.float64,
            )
            capacity=cell_pv*rho_max*MAX_SG
            gate("physical_cell_capacity_positive_finite",np.isfinite(capacity).all() and np.all(capacity>0))

            grid_sat=np.empty((NT,)+GRID,dtype=np.float64)
            grid_mass=np.empty((NT,)+GRID,dtype=np.float64)
            time_rows=[]
            component_rows=[]

            reconciliation_started=True

            for it,day in enumerate(DAYS):
                newf=np.asarray(pred200[it],dtype=np.float64).reshape(-1)
                newsub=newf[cv_id]
                newsg=np.clip(newsub-BACKGROUND,0.0,MAX_SG)
                rho_new=np.asarray(
                    r2.gas_density_from_state(newsub,pseg,p_ref),
                    dtype=np.float64,
                )
                sub_mass=pv*rho_new*newsg
                raw=np.bincount(
                    flat,weights=sub_mass,minlength=NX*NY*NZ
                ).reshape(GRID)

                target=float(np.sum(pred_mass[it]))
                transfer_residual=float(np.sum(raw)-target)
                transfer_tol=max(1.0e-7,1.0e-11*max(abs(target),1.0))
                sci_gate(
                    f"time_{int(day)}_B1_to_subsegment_mass_closure",
                    abs(transfer_residual)<=transfer_tol,
                    [transfer_residual,transfer_tol],
                )

                raw_excess=raw-capacity
                cap_tol=max(1.0e-7,1.0e-11*max(float(np.max(capacity)),1.0))
                overloaded=int(np.sum(raw_excess>cap_tol))
                max_raw_excess=float(np.max(raw_excess))

                if it==0:
                    sci_gate(
                        "day30_R7R1_overloaded_count_reproduced",
                        overloaded==EXPECTED_DAY30_OVERLOADED,
                        overloaded,
                    )
                    sci_gate(
                        "day30_R7R1_max_excess_reproduced",
                        abs(max_raw_excess-EXPECTED_DAY30_MAX_EXCESS)
                        <= max(1.0e-6,1.0e-10*EXPECTED_DAY30_MAX_EXCESS),
                        max_raw_excess,
                    )

                reconciled,diag,compaudit=reconcile_mass(raw,capacity,graph)

                sg=np.asarray(
                    r2._invert_incremental_sg_from_mass(
                        reconciled,pressure,p_ref,cell_pv
                    ),
                    dtype=np.float64,
                )
                sat=BACKGROUND+sg
                sci_gate(f"time_{int(day)}_grid_saturation_finite",np.isfinite(sat).all())
                sci_gate(
                    f"time_{int(day)}_grid_saturation_bounds",
                    float(np.min(sat))>=BACKGROUND-1e-12 and float(np.max(sat))<=INJECTED+1e-12,
                    [float(np.min(sat)),float(np.max(sat))],
                )

                reconstructed=float(
                    r2.stored_co2_mass_kg(
                        sat,pressure,p_ref,cell_pv
                    )
                )
                inv_rel=abs(reconstructed-float(np.sum(reconciled)))/max(abs(float(np.sum(reconciled))),1.0)
                sci_gate(
                    f"time_{int(day)}_EOS_mass_inversion_closure",
                    inv_rel<=1.0e-10,
                    inv_rel,
                )

                support_mask=np.zeros(NX*NY*NZ,dtype=bool)
                support_mask[graph["nodes"]]=True
                support_mask=support_mask.reshape(GRID)
                sci_gate(
                    f"time_{int(day)}_unsupported_saturation_background",
                    np.array_equal(
                        sat[~support_mask],
                        np.full(np.sum(~support_mask),BACKGROUND,dtype=np.float64),
                    ),
                )

                grid_sat[it]=sat
                grid_mass[it]=reconciled
                completed_times=it+1

                time_rows.append({
                    "target_day":float(day),
                    "raw_total_component_mass_kg":diag["raw_total_component_mass_kg"],
                    "raw_overloaded_cell_count":diag["raw_overloaded_cell_count"],
                    "raw_max_capacity_excess_kg":diag["raw_max_capacity_excess_kg"],
                    "raw_total_excess_supply_kg":diag["raw_total_excess_supply_kg"],
                    "recipient_cell_count":diag["recipient_cell_count"],
                    "active_component_count":diag["active_component_count"],
                    "primary_min_cost_total":diag["primary_min_cost_total"],
                    "tie_solution_primary_cost_total":diag["tie_solution_primary_cost_total"],
                    "total_directed_edge_flow_kg":diag["total_directed_edge_flow_kg"],
                    "maximum_directed_edge_flow_kg":diag["maximum_directed_edge_flow_kg"],
                    "max_node_balance_residual_kg":diag["max_node_balance_residual_kg"],
                    "max_component_mass_residual_kg":diag["max_component_mass_residual_kg"],
                    "max_capacity_excess_after_reconciliation_kg":diag["max_capacity_excess_after_reconciliation_kg"],
                    "total_component_mass_relative_closure":diag["total_component_mass_relative_closure"],
                    "grid_saturation_min":float(np.min(sat)),
                    "grid_saturation_max":float(np.max(sat)),
                    "EOS_mass_relative_closure":inv_rel,
                })
                for row in compaudit:
                    component_rows.append({"target_day":float(day),**row})

            sci_gate("all_9_canonical_times",completed_times==NT,completed_times)

        stage="seal_integrated_state"
        state_name="POSTV16_AV1_D_R7_R3_Foundation0001_Reconciled_Integrated_State.npz"
        state_bytes=deterministic_npz_bytes({
            "target_days":DAYS,
            "streamline_saturation_201":pred201.astype(np.float32),
            "streamline_saturation_200":pred200.astype(np.float32),
            "streamline_component_mass_200_kg":pred_mass.astype(np.float64),
            "grid_saturation":grid_sat.astype(np.float32),
            "grid_component_mass_kg":grid_mass.astype(np.float64),
            "foundation_case_sha256":np.array(FOUNDATION_SHA),
            "runtime_weights_sha256":np.array(WEIGHTS_SHA),
            "runtime_normalization_sha256":np.array(NORM_SHA),
            "reconciliation_protocol_id":np.array(PROTOCOL_ID),
        })
        immutable_publish(out,{state_name:state_bytes})
        state_sha=sha256_file(out/state_name)

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "scientific_execution_pass":True,
            "protocol_id":PROTOCOL_ID,
            "candidate_count":1,
            "all_9_canonical_times_completed":True,
            "accepted_weights_sha256":WEIGHTS_SHA,
            "normalization_sha256":NORM_SHA,
            "foundation_case_sha256":FOUNDATION_SHA,
            "integrated_state_sha256":state_sha,
            "accepted_checkpoint_modified":False,
            "B1_modified":False,
            "saturation_bounds_modified":False,
            "global_saturation_rescaling_used":False,
            "unsupported_cells_used_as_sinks":False,
            "geology0031_used":False,
            "acceptance_truth_used":False,
            "alternate_reconciliation_candidate_used":False,
            "new_accuracy_claim":False,
            "new_generalization_claim":False,
            "authorized_claim":(
                "End-to-end conservative interface executability with bounded "
                "support-constrained occupancy reconciliation on frozen Foundation Case 0001."
            ),
            "next":{
                "milestone":"POSTV16-AV1-D-R8",
                "name":"Prospective Full-Field / Plume Fidelity Validation Protocol",
                "authorized":True,
            },
        }

        summary={
            **decision,
            "repository_parent":PARENT_R7R2_COMMIT,
            "C26_input_shape":[NSAMP,NN,9],
            "streamline_saturation_201_shape":[NT,NSL,NN],
            "streamline_saturation_200_shape":[NT,NSL,NCV],
            "grid_saturation_shape":[NT,NZ,NY,NX],
            "prediction_saturation_min":float(np.min(pred201)),
            "prediction_saturation_max":float(np.max(pred201)),
            "grid_saturation_min":float(np.min(grid_sat)),
            "grid_saturation_max":float(np.max(grid_sat)),
            "maximum_raw_overloaded_cells":int(max(r["raw_overloaded_cell_count"] for r in time_rows)),
            "maximum_raw_capacity_excess_kg":float(max(r["raw_max_capacity_excess_kg"] for r in time_rows)),
            "maximum_post_reconciliation_capacity_excess_kg":float(max(r["max_capacity_excess_after_reconciliation_kg"] for r in time_rows)),
            "maximum_mass_relative_closure":float(max(r["total_component_mass_relative_closure"] for r in time_rows)),
            "maximum_EOS_mass_relative_closure":float(max(r["EOS_mass_relative_closure"] for r in time_rows)),
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R3_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R3_Final_Decision.json":json_bytes(decision),
            "POSTV16_AV1_D_R7_R3_Timewise_Reconciliation_Audit.csv":csv_bytes(time_rows),
            "POSTV16_AV1_D_R7_R3_Component_LP_Audit.csv":csv_bytes(component_rows),
            "POSTV16_AV1_D_R7_R3_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        })

        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R3_Artifact_Manifest.csv":
                manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"POSTV16_AV1_D_R7_R3_Artifact_Manifest.csv":csv_bytes(manifest)})

        print("\n"+"="*188)
        print("POSTV16-AV1-D-R7-R3: PASS")
        print("="*188)
        print(f"{'Status':106}: {STATUS_PASS}")
        print(f"{'Frozen protocol':106}: {PROTOCOL_ID}")
        print(f"{'Canonical times completed':106}: {completed_times} / 9")
        print(f"{'Accepted runtime weights SHA256':106}: {WEIGHTS_SHA}")
        print(f"{'Grid saturation shape':106}: {grid_sat.shape}")
        print(f"{'Grid saturation min / max':106}: {float(np.min(grid_sat)):.12e} / {float(np.max(grid_sat)):.12e}")
        print(f"{'Maximum raw overloaded-cell count':106}: {max(r['raw_overloaded_cell_count'] for r in time_rows)}")
        print(f"{'Maximum raw cell-capacity excess [kg]':106}: {max(r['raw_max_capacity_excess_kg'] for r in time_rows):.12e}")
        print(f"{'Maximum post-reconciliation capacity excess [kg]':106}: {max(r['max_capacity_excess_after_reconciliation_kg'] for r in time_rows):.12e}")
        print(f"{'Maximum total-mass relative closure':106}: {max(r['total_component_mass_relative_closure'] for r in time_rows):.12e}")
        print(f"{'Maximum EOS mass relative closure':106}: {max(r['EOS_mass_relative_closure'] for r in time_rows):.12e}")
        print(f"{'Accepted checkpoint / B1 / saturation bounds changed':106}: False / False / False")
        print(f"{'Unsupported cells used as sinks':106}: False")
        print(f"{'Geology0031 / acceptance truth used':106}: False / False")
        print(f"{'Integrated state SHA256':106}: {state_sha}")
        print(f"{'R8 prospective plume-fidelity protocol authorized':106}: True")
        print(f"{'NEXT':106}: POSTV16-AV1-D-R8 — prospective full-field/plume fidelity validation protocol")
        print("="*188)
        return 0

    except ScientificFail as sf:
        decision={
            "milestone":MILESTONE,
            "status":STATUS_FAIL,
            "scientific_execution_pass":False,
            "failed_gate":sf.gate,
            "failure_detail":sf.detail,
            "protocol_id":PROTOCOL_ID,
            "candidate_count":1,
            "completed_canonical_times":completed_times,
            "model_inference_performed":inference_performed,
            "reconciliation_started":reconciliation_started,
            "accepted_checkpoint_modified":False,
            "B1_modified":False,
            "saturation_bounds_modified":False,
            "global_saturation_rescaling_used":False,
            "unsupported_cells_used_as_sinks":False,
            "geology0031_used":False,
            "acceptance_truth_used":False,
            "alternate_reconciliation_candidate_authorized":False,
            "retuning_authorized":False,
            "next_action":(
                "Close and audit this single frozen reconciliation candidate. "
                "Do not retune, alter graph costs, relax bounds, add unsupported sinks, "
                "or execute an alternate reconciliation candidate under R7-R3."
            ),
        }
        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R3_Summary.json":json_bytes(decision),
            "POSTV16_AV1_D_R7_R3_Final_Decision.json":json_bytes(decision),
            "POSTV16_AV1_D_R7_R3_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        })
        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R3_Artifact_Manifest.csv":
                manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"POSTV16_AV1_D_R7_R3_Artifact_Manifest.csv":csv_bytes(manifest)})

        print("\n"+"="*188)
        print("POSTV16-AV1-D-R7-R3: SCIENTIFIC FAIL")
        print("="*188)
        print("Status        :",STATUS_FAIL)
        print("Failed gate   :",sf.gate)
        print("Failure detail:",sf.detail)
        print("Completed times:",completed_times)
        print("No adaptation or alternate repair candidate is authorized.")
        print("="*188)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_BLOCKED,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "model_inference_performed":inference_performed,
            "reconciliation_started":reconciliation_started,
            "completed_canonical_times":completed_times,
            "accepted_checkpoint_modified":False,
            "B1_modified":False,
            "geology0031_used":False,
            "acceptance_truth_used":False,
            "scientific_final_decision_reached":False,
            "next_action":(
                "Audit only this technical execution failure. Preserve the frozen R7-R2 "
                "protocol exactly; do not retune or substitute a reconciliation operator."
            ),
        }
        data=json_bytes(report)
        p=blocked/"POSTV16_AV1_D_R7_R3_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R3_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*188)
        print("POSTV16-AV1-D-R7-R3: TECHNICALLY BLOCKED")
        print("="*188)
        print("Failed stage :",stage)
        print("Exception    :",repr(exc))
        print("Inference run:",inference_performed)
        print("Reconciliation started:",reconciliation_started)
        print("Completed times:",completed_times)
        print("Report       :",p)
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
