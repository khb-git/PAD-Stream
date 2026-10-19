#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
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


MILESTONE = "POSTV16-AV1-D-R7-R7E"
STATUS_PASS = (
    "AV1DR7R7E_FROZEN_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_DOMAIN_"
    "EXECUTED_ALL_9_TIMES_END_TO_END_BOUNDED_CONSERVATIVE_INTEGRATION_PASS"
)
STATUS_FAIL = (
    "AV1DR7R7E_FROZEN_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_DOMAIN_"
    "SCIENTIFIC_FAIL_NO_ADAPTATION_OR_ALTERNATE_CANDIDATE_AUTHORIZED"
)
STATUS_BLOCKED = (
    "AV1DR7R7E_TECHNICAL_EXECUTION_BLOCKED_BEFORE_VALID_DECISION"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R7D_COMMIT = "90183c154095467c76153ec45201a6846ad0e2ea"

R7R7D = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7D_"
    "Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
)
R7R7D_BLOB = "bd2873f7fb6b98d4e857c98864b78e2da6f202a4"

R7R7C = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7C_"
    "Support_Domain_Capacity_Failure_Closure.py"
)
R7R7C_BLOB = "a58f5910d2290ecb5a258af9ecf9a27afe6620ee"

R7R7B = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7B_"
    "Canonical_Solver_Native_Semantics_Execution.py"
)
R7R7B_BLOB = "c65fc15f630a097a81fbe6fe28dab87c7056ce65"

R7R7A = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7A_"
    "Canonical_Primary_Envelope_Arithmetic_Semantics_Freeze.py"
)
R7R7A_BLOB = "191792855ecbb2560475ca2066b307d6fef494d5"
R7R7 = "PAD_Stream_POSTV16_AV1_D_R7_R7_R7R6_Certification_Semantics_Failure_Closure.py"
R7R7_BLOB = "1b44f47ff40394162788f73531301b2336cc2b24"
R7R6 = "PAD_Stream_POSTV16_AV1_D_R7_R6_Strict_Numerical_Certification_Execution.py"
R7R6_BLOB = "b7bddd20ed08c05f3b832d5006ae98586468fd26"
R7R5 = "PAD_Stream_POSTV16_AV1_D_R7_R5_Deterministic_Numerical_Certification_Redesign_Freeze.py"
R7R5_BLOB = "bc43079146772a16a3c3ecc6cea13fe88a963857"
R7R4 = "PAD_Stream_POSTV16_AV1_D_R7_R4_R7R3_Tiebreak_Certification_Failure_Closure.py"
R7R4_BLOB = "687aa4580c85b8a188e4d2e2dc0493b2f25dc97f"
R7R3 = "PAD_Stream_POSTV16_AV1_D_R7_R3_Controlled_Frozen_Reconciliation_Execution.py"
R7R3_BLOB = "a431ac9d4faa3fdf0ecf415c36208ac31c797ad0"
R7R2 = "PAD_Stream_POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"
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
    R7R7D:R7R7D_BLOB,
    R7R7C:R7R7C_BLOB,
    R7R7B:R7R7B_BLOB,
    R7R7A:R7R7A_BLOB, R7R7:R7R7_BLOB,
    R7R6:R7R6_BLOB, R7R5:R7R5_BLOB, R7R4:R7R4_BLOB,
    R7R3:R7R3_BLOB, R7R2:R7R2_BLOB, R7:R7_BLOB, R6:R6_BLOB,
    B2:B2_BLOB, C2:C2_BLOB, C26:C26_BLOB, B1:B1_BLOB,
    R2:R2_BLOB, E37A:E37A_BLOB, SG7D:SG7D_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R7D_REL = (
    BASE /
    "POSTV16_AV1_D_R7_R7D_Horizontal_Face_Halo_Occupancy_Domain_Freeze"
)
R7R7D_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7D_Summary.json"
R7R7D_PROTOCOL = (
    "POSTV16_AV1_D_R7_R7D_Frozen_Occupancy_Domain_Extension_Protocol.json"
)
R7R7D_FREEZE = "POSTV16_AV1_D_R7_R7D_Protocol_Freeze_Contract.json"
R7R7D_MANIFEST = "POSTV16_AV1_D_R7_R7D_Artifact_Manifest.csv"

R7R7A_REL = BASE / (
    "POSTV16_AV1_D_R7_R7A_"
    "Canonical_Primary_Envelope_Arithmetic_Semantics_Freeze"
)
R7R7A_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7A_Summary.json"
R7R7A_PROTOCOL = "POSTV16_AV1_D_R7_R7A_Frozen_Canonical_Arithmetic_Semantics.json"
R7R7A_FREEZE = "POSTV16_AV1_D_R7_R7A_Protocol_Freeze_Contract.json"
R7R7A_MANIFEST = "POSTV16_AV1_D_R7_R7A_Artifact_Manifest.csv"

R6_REL = BASE / "POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding"
R6_WEIGHTS = "POSTV16_AV1_D_R6_ACCEPTED_TRANSPORT_FROZEN.weights.h5"
R6_NORM = "POSTV16_AV1_D_R6_C3_Conditioning_Normalization_Parameters.npz"

OUT_REL = (
    BASE /
    "POSTV16_AV1_D_R7_R7E_Frozen_Horizontal_Face_Halo_"
    "Occupancy_Domain_Execution"
)
BLOCKED_REL = BASE / "POSTV16_AV1_D_R7_R7E_BLOCKED"

R7R7D_STATUS = (
    "AV1DR7R7D_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_DOMAIN_"
    "PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

R7R7D_PROTOCOL_ID = (
    "POSTV16_AV1_D_R7_R7D_"
    "SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_EXTENSION_V1"
)

HALO_ENTRY_COST = 5.0

R7R7A_STATUS = (
    "AV1DR7R7A_SINGLE_CANONICAL_SOLVER_NATIVE_PRIMARY_ENVELOPE_"
    "ARITHMETIC_SEMANTICS_PROSPECTIVELY_FROZEN"
)
NUMERICAL_PROTOCOL_ID = "POSTV16_AV1_D_R7_R7A_SOLVER_NATIVE_UNSCALED_PRIMARY_ENVELOPE_SEMANTICS_V1"
PHYSICAL_PROTOCOL_ID = "POSTV16_AV1_D_R7_R2_SUPPORT_GRAPH_MIN_COST_EXCESS_MASS_RECONCILIATION_V1"

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

LP_METHOD = "highs-ds"
PRIMAL_FEAS_TOL = 1.0e-10
DUAL_FEAS_TOL = 1.0e-10
CANONICAL_RESIDUAL_FLOOR = -1.0e-10

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
        check=True,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
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
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
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


def fsum_dot(c: np.ndarray, x: np.ndarray) -> float:
    return float(math.fsum(float(ci)*float(xi) for ci,xi in zip(c,x)))


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


def build_extended_halo_graph(
    operator: dict[str,np.ndarray],
) -> dict[str,Any]:
    """
    Build the exact prospectively frozen R7-R7D occupancy domain.

    S0
    --
    Exact Cartesian cells crossed by the frozen SG7D subsegment operator.
    The original R7-R2 S0 support graph remains unchanged.

    H1
    --
    One non-recursive same-layer horizontal face-neighbor ring around S0:
        (delta_k, delta_j, delta_i)
        (0,  0, -1)
        (0,  0, +1)
        (0, -1,  0)
        (0, +1,  0)

    D1
    --
        D1 = S0 union H1

    Directed graph semantics
    ------------------------
    * Original S0-S0 support connections retain both directions.
    * New halo connections are S0 -> H1 only.
    * H1 -> S0 is forbidden.
    * H1 -> H1 is forbidden.
    * H1 is therefore terminal occupancy space, never transit space.
    * Every S0 -> H1 entry arc has frozen cost 5 graph-distance units.

    This function constructs geometry/graph data only.
    It does not run an LP or alter reconciliation.
    """

    support = build_support_graph(operator)

    s0 = np.asarray(
        support["nodes"],
        dtype=np.int64,
    )

    if len(s0) == 0:
        raise GateError("empty_exact_SG7D_support_S0")

    s0_set = set(
        int(x)
        for x in s0.tolist()
    )

    # -----------------------------------------------------------------
    # Exact single non-recursive horizontal face-neighbor ring.
    #
    # IMPORTANT:
    # Iterate over S0 only. Newly discovered halo cells are never used
    # as parents, so this cannot recurse into a second ring.
    # -----------------------------------------------------------------

    halo_set: set[int] = set()
    parent_pairs: set[tuple[int,int]] = set()

    horizontal_offsets = (
        (0,  0, -1),
        (0,  0, +1),
        (0, -1,  0),
        (0, +1,  0),
    )

    for flat0 in s0:
        flat = int(flat0)

        i = flat % NX
        j = (flat // NX) % NY
        k = flat // (NX * NY)

        for dk,dj,di in horizontal_offsets:
            kk = k + dk
            jj = j + dj
            ii = i + di

            if not (
                0 <= kk < NZ
                and 0 <= jj < NY
                and 0 <= ii < NX
            ):
                continue

            neighbor = int(
                kk * NX * NY
                + jj * NX
                + ii
            )

            if neighbor in s0_set:
                continue

            halo_set.add(neighbor)

            # One H1 cell may share a face with more than one S0 cell.
            # Preserve every exact S0-H1 face adjacency as a candidate
            # terminal entry arc.
            parent_pairs.add(
                (flat, neighbor)
            )

    h1 = np.asarray(
        sorted(halo_set),
        dtype=np.int64,
    )

    if len(h1) == 0:
        raise GateError("empty_frozen_horizontal_halo_H1")

    if len(
        np.intersect1d(
            s0,
            h1,
            assume_unique=True,
        )
    ):
        raise GateError("S0_H1_overlap")

    # Preserve S0 local numbering exactly by putting S0 first.
    # H1 follows as the occupancy-only extension.
    d1 = np.concatenate(
        [s0, h1]
    ).astype(
        np.int64,
        copy=False,
    )

    lookup = np.full(
        NX * NY * NZ,
        -1,
        dtype=np.int64,
    )

    lookup[d1] = np.arange(
        len(d1),
        dtype=np.int64,
    )

    s0_mask = np.zeros(
        len(d1),
        dtype=bool,
    )
    s0_mask[:len(s0)] = True

    h1_mask = ~s0_mask

    # -----------------------------------------------------------------
    # Original S0 support graph -> explicit directed arcs.
    #
    # build_support_graph() stores every undirected physical connection
    # once. For the future directed LP representation, each such edge
    # becomes the original two directions with the exact same cost.
    # -----------------------------------------------------------------

    support_pairs_flat = np.asarray(
        support["edge_pairs_flat"],
        dtype=np.int64,
    ).reshape(-1, 2)

    support_cost = np.asarray(
        support["edge_cost"],
        dtype=np.float64,
    )

    if len(support_pairs_flat):
        support_u = lookup[
            support_pairs_flat[:, 0]
        ]
        support_v = lookup[
            support_pairs_flat[:, 1]
        ]

        if (
            np.any(support_u < 0)
            or np.any(support_v < 0)
        ):
            raise GateError(
                "S0_support_edge_not_in_D1"
            )

        # Preserve the exact R7-R7B directed-flow variable ordering:
        #
        #   edge 0: u -> v, v -> u
        #   edge 1: u -> v, v -> u
        #   ...
        #
        # This matters because the frozen R7-R7A secondary tie
        # objective is deterministic and index-dependent.
        nsupport = len(support_u)

        arc_u = np.empty(
            2 * nsupport,
            dtype=np.int64,
        )
        arc_v = np.empty(
            2 * nsupport,
            dtype=np.int64,
        )
        arc_cost = np.empty(
            2 * nsupport,
            dtype=np.float64,
        )

        arc_u[0::2] = support_u
        arc_v[0::2] = support_v
        arc_cost[0::2] = support_cost

        arc_u[1::2] = support_v
        arc_v[1::2] = support_u
        arc_cost[1::2] = support_cost

        # 0 = unchanged S0-S0 transport-backbone arc.
        arc_kind = np.zeros(
            2 * nsupport,
            dtype=np.int8,
        )

    else:
        arc_u = np.empty(
            0,
            dtype=np.int64,
        )
        arc_v = np.empty(
            0,
            dtype=np.int64,
        )
        arc_cost = np.empty(
            0,
            dtype=np.float64,
        )
        arc_kind = np.empty(
            0,
            dtype=np.int8,
        )

    # -----------------------------------------------------------------
    # Frozen new S0 -> H1 terminal-entry arcs.
    # -----------------------------------------------------------------

    halo_pairs_flat = np.asarray(
        sorted(parent_pairs),
        dtype=np.int64,
    ).reshape(-1, 2)

    if len(halo_pairs_flat) == 0:
        raise GateError(
            "no_S0_to_H1_face_adjacencies"
        )

    halo_u = lookup[
        halo_pairs_flat[:, 0]
    ]
    halo_v = lookup[
        halo_pairs_flat[:, 1]
    ]

    if (
        np.any(halo_u < 0)
        or np.any(halo_v < 0)
    ):
        raise GateError(
            "halo_arc_endpoint_not_in_D1"
        )

    # By construction every new arc is directed S0 -> H1.
    if not np.all(
        s0_mask[halo_u]
    ):
        raise GateError(
            "halo_arc_origin_not_S0"
        )

    if not np.all(
        h1_mask[halo_v]
    ):
        raise GateError(
            "halo_arc_target_not_H1"
        )

    arc_u = np.concatenate(
        [arc_u, halo_u]
    )

    arc_v = np.concatenate(
        [arc_v, halo_v]
    )

    arc_cost = np.concatenate([
        arc_cost,
        np.full(
            len(halo_u),
            HALO_ENTRY_COST,
            dtype=np.float64,
        ),
    ])

    # 1 = frozen S0 -> H1 terminal occupancy-entry arc.
    arc_kind = np.concatenate([
        arc_kind,
        np.ones(
            len(halo_u),
            dtype=np.int8,
        ),
    ])

    # -----------------------------------------------------------------
    # Weak component bookkeeping.
    #
    # This is NOT permission for reverse transport. The symmetric
    # adjacency here is used only to identify weakly connected domains.
    # Directed flow semantics remain in arc_u -> arc_v.
    # -----------------------------------------------------------------

    weak_rows = np.concatenate(
        [arc_u, arc_v]
    )

    weak_cols = np.concatenate(
        [arc_v, arc_u]
    )

    weak_adj = sparse.csr_matrix(
        (
            np.ones(
                len(weak_rows),
                dtype=np.int8,
            ),
            (
                weak_rows,
                weak_cols,
            ),
        ),
        shape=(
            len(d1),
            len(d1),
        ),
    )

    ncomp, labels = connected_components(
        weak_adj,
        directed=False,
        return_labels=True,
    )

    return {
        # Extended domain.
        "nodes": d1,
        "lookup": lookup,

        # Exact frozen sets.
        "s0_nodes": s0,
        "h1_nodes": h1,
        "s0_mask": s0_mask,
        "h1_mask": h1_mask,

        # Exact unchanged R7-R2 graph authority.
        "support": support,

        # Every exact S0-H1 x/y face adjacency in flat-cell space.
        "halo_parent_pairs_flat": halo_pairs_flat,

        # Explicit directed graph for future R7-R7E LP connection.
        "arc_u": np.asarray(
            arc_u,
            dtype=np.int64,
        ),
        "arc_v": np.asarray(
            arc_v,
            dtype=np.int64,
        ),
        "arc_cost": np.asarray(
            arc_cost,
            dtype=np.float64,
        ),
        "arc_kind": np.asarray(
            arc_kind,
            dtype=np.int8,
        ),

        # Weak component bookkeeping only.
        "component_labels": labels.astype(
            np.int64
        ),
        "n_components": int(ncomp),
    }


def solve_component_lp_strict(
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
    options={
        "presolve":True,
        "primal_feasibility_tolerance":PRIMAL_FEAS_TOL,
        "dual_feasibility_tolerance":DUAL_FEAS_TOL,
    }

    primary=linprog(
        c_primary,
        A_eq=Aeq,
        b_eq=rhs,
        bounds=bounds,
        method=LP_METHOD,
        options=options,
    )
    if not primary.success:
        raise ScientificFail(
            "primary_LP_success_all_times",
            {"status":int(primary.status),"message":str(primary.message)},
        )

    # R7-R7A canonical authority:
    # primary.fun is the primary optimum authority used to construct the
    # exact unscaled secondary inequality row and RHS.
    primary_fun=float(primary.fun)
    tol_obj=max(1.0e-8,1.0e-12*max(abs(primary_fun),1.0))
    secondary_rhs=primary_fun+tol_obj

    c_tie=np.zeros(nvar,dtype=np.float64)
    if ndir:
        c_tie[:ndir]=(np.arange(ndir,dtype=np.float64)+1.0)/float(ndir)
    if n:
        c_tie[ndir:]=(np.arange(n,dtype=np.float64)+1.0)/float(n)

    Aub=sparse.csr_matrix(c_primary.reshape(1,-1))
    tie=linprog(
        c_tie,
        A_ub=Aub,
        b_ub=np.array([secondary_rhs],dtype=np.float64),
        A_eq=Aeq,
        b_eq=rhs,
        bounds=bounds,
        method=LP_METHOD,
        options=options,
    )
    if not tie.success:
        raise ScientificFail(
            "secondary_LP_success_all_times",
            {
                "status":int(tie.status),
                "message":str(tie.message),
                "primary_fun":primary_fun,
                "primary_envelope_tolerance":tol_obj,
            },
        )

    x=np.asarray(tie.x,dtype=np.float64)

    ineq_res=np.asarray(tie.ineqlin.residual,dtype=np.float64).reshape(-1)
    if len(ineq_res)!=1:
        raise GateError(f"unexpected_secondary_ineqlin_residual_shape:{ineq_res.shape}")
    ineq_slack=float(ineq_res[0])

    # ONE canonical pass/fail arithmetic, exactly as frozen in R7-R7A.
    if ineq_slack<CANONICAL_RESIDUAL_FLOOR:
        raise ScientificFail(
            "canonical_secondary_residual_all_times",
            {
                "secondary_inequality_residual":ineq_slack,
                "required_minimum":CANONICAL_RESIDUAL_FLOOR,
                "primary_fun":primary_fun,
                "primary_envelope_tolerance":tol_obj,
                "secondary_rhs":secondary_rhs,
            },
        )

    # Diagnostics only — these cannot alter PASS/FAIL.
    primary_x=np.asarray(primary.x,dtype=np.float64)
    primary_fsum=fsum_dot(c_primary,primary_x)
    primary_numpy=float(np.dot(c_primary,primary_x))
    tie_primary_fsum=fsum_dot(c_primary,x)
    tie_primary_numpy=float(np.dot(c_primary,x))
    tie_obj_fsum=fsum_dot(c_tie,x)

    balance=np.asarray(Aeq@x-rhs,dtype=np.float64)
    total_excess=float(np.sum(rhs))
    bal_tol=max(1.0e-7,1.0e-11*max(total_excess,1.0))
    max_balance=float(np.max(np.abs(balance))) if len(balance) else 0.0
    if max_balance>bal_tol:
        raise ScientificFail(
            "max_node_balance_residual_kg",
            {"residual":max_balance,"tolerance":bal_tol},
        )

    absorption=x[ndir:]
    if np.any(absorption < -1.0e-8) or np.any(absorption-spare>1.0e-7):
        raise ScientificFail(
            "absorption_bounds",
            {
                "minimum_absorption":float(np.min(absorption)) if len(absorption) else 0.0,
                "maximum_capacity_overrun":float(np.max(absorption-spare)) if len(absorption) else 0.0,
            },
        )

    return {
        "absorption":absorption,
        "solver_method":LP_METHOD,
        "primal_feasibility_tolerance":PRIMAL_FEAS_TOL,
        "dual_feasibility_tolerance":DUAL_FEAS_TOL,
        "reported_primary_fun":primary_fun,
        "certified_primary_optimum":primary_fun,
        "primary_fun_minus_certified":primary_fun-primary_fsum,
        "primary_objective_tolerance":tol_obj,
        "reported_secondary_fun":float(tie.fun),
        "certified_tie_primary_cost":tie_primary_fsum,
        "secondary_primary_certification_limit":secondary_rhs,
        "secondary_primary_margin":ineq_slack,
        "secondary_inequality_slack":ineq_slack,
        "secondary_tie_objective":tie_obj_fsum,
        "diagnostic_primary_math_fsum":primary_fsum,
        "diagnostic_primary_numpy_dot":primary_numpy,
        "diagnostic_secondary_primary_math_fsum":tie_primary_fsum,
        "diagnostic_secondary_primary_numpy_dot":tie_primary_numpy,
        "diagnostic_math_fsum_over_solver_rhs":tie_primary_fsum-secondary_rhs,
        "total_directed_edge_flow_kg":float(np.sum(x[:ndir])),
        "maximum_directed_edge_flow_kg":float(np.max(x[:ndir])) if ndir else 0.0,
        "max_node_balance_residual_kg":max_balance,
        "balance_tolerance_kg":bal_tol,
    }


def solve_directed_component_lp_strict(
    component_nodes: np.ndarray,
    component_arc_ids: np.ndarray,
    graph: dict[str,Any],
    excess_all: np.ndarray,
    spare_all: np.ndarray,
) -> dict[str,Any]:
    """
    R7-R7E directed-domain counterpart to solve_component_lp_strict().

    The ONLY structural change is the flow-variable representation:

      R7-R7B:
          each undirected support edge creates two nonnegative
          directed flow variables internally.

      R7-R7E:
          the graph already contains explicit directed arcs.

    This is necessary because R7-R7D freezes S0 -> H1 terminal
    entry arcs without H1 -> S0 reverse arcs.

    The R7-R7A solver method, feasibility tolerances, primary
    objective-envelope arithmetic, secondary inequality, solver-native
    residual authority, balance gate, and absorption bounds are
    preserved exactly.
    """

    component_nodes=np.asarray(
        component_nodes,
        dtype=np.int64,
    )

    component_arc_ids=np.asarray(
        component_arc_ids,
        dtype=np.int64,
    )

    n=len(component_nodes)

    if n == 0:
        raise GateError(
            "empty_directed_component"
        )

    local_lookup=np.full(
        len(graph["nodes"]),
        -1,
        dtype=np.int64,
    )

    local_lookup[component_nodes]=np.arange(
        n,
        dtype=np.int64,
    )

    gu=np.asarray(
        graph["arc_u"],
        dtype=np.int64,
    )[component_arc_ids]

    gv=np.asarray(
        graph["arc_v"],
        dtype=np.int64,
    )[component_arc_ids]

    eu=local_lookup[gu]
    ev=local_lookup[gv]

    if (
        np.any(eu < 0)
        or np.any(ev < 0)
    ):
        raise GateError(
            "directed_arc_crosses_component"
        )

    ecost=np.asarray(
        graph["arc_cost"],
        dtype=np.float64,
    )[component_arc_ids]

    na=len(component_arc_ids)
    nvar=na+n

    # -------------------------------------------------------------
    # Directed node balance.
    #
    # For an arc u -> v:
    #   +f at u
    #   -f at v
    #
    # and local absorption a_i enters with +1.
    #
    # Therefore:
    #
    #   outgoing - incoming + absorption = excess_supply
    #
    # exactly matching the sign convention used in R7-R7B.
    # -------------------------------------------------------------

    rows=[]
    cols=[]
    data=[]

    for e in range(na):
        u=int(eu[e])
        v=int(ev[e])

        rows.extend(
            [u,v]
        )

        cols.extend(
            [e,e]
        )

        data.extend(
            [1.0,-1.0]
        )

    for i in range(n):
        rows.append(i)
        cols.append(na+i)
        data.append(1.0)

    Aeq=sparse.csr_matrix(
        (data,(rows,cols)),
        shape=(n,nvar),
    )

    rhs=np.asarray(
        excess_all[component_nodes],
        dtype=np.float64,
    )

    spare=np.asarray(
        spare_all[component_nodes],
        dtype=np.float64,
    )

    if (
        np.any(~np.isfinite(rhs))
        or np.any(~np.isfinite(spare))
    ):
        raise GateError(
            "nonfinite_directed_LP_rhs_or_capacity"
        )

    if np.any(rhs < -1.0e-12):
        raise GateError(
            "negative_directed_LP_excess_supply"
        )

    if np.any(spare < -1.0e-12):
        raise GateError(
            "negative_directed_LP_spare_capacity"
        )

    # -------------------------------------------------------------
    # R7-R7A primary objective.
    #
    # Every explicit directed arc carries its frozen graph cost.
    # Absorption itself remains zero-cost.
    # -------------------------------------------------------------

    c_primary=np.zeros(
        nvar,
        dtype=np.float64,
    )

    if na:
        c_primary[:na]=ecost

    bounds=(
        [(0.0,None)]*na
        + [
            (0.0,float(x))
            for x in spare
        ]
    )

    # EXACT frozen R7-R7A solver authority.
    options={
        "presolve":True,
        "primal_feasibility_tolerance":PRIMAL_FEAS_TOL,
        "dual_feasibility_tolerance":DUAL_FEAS_TOL,
    }

    primary=linprog(
        c_primary,
        A_eq=Aeq,
        b_eq=rhs,
        bounds=bounds,
        method=LP_METHOD,
        options=options,
    )

    if not primary.success:
        raise ScientificFail(
            "primary_LP_success_all_times",
            {
                "status":int(primary.status),
                "message":str(primary.message),
            },
        )

    # =============================================================
    # EXACT R7-R7A CANONICAL PRIMARY-ENVELOPE AUTHORITY
    # =============================================================
    #
    # primary.fun is the sole primary optimum authority used to
    # construct the exact unscaled secondary inequality row and RHS.
    #
    # Do NOT replace this with math.fsum or numpy.dot.
    # Those remain diagnostics only.
    # =============================================================

    primary_fun=float(
        primary.fun
    )

    tol_obj=max(
        1.0e-8,
        1.0e-12
        * max(
            abs(primary_fun),
            1.0,
        ),
    )

    secondary_rhs=(
        primary_fun
        + tol_obj
    )

    # -------------------------------------------------------------
    # Exact R7-R7A deterministic secondary objective FORMULA.
    #
    # The problem dimension is now the prospectively frozen D1
    # directed variable space, but the formula itself is unchanged:
    #
    #   flow_j       -> (j+1)/N_flow
    #   absorption_i -> (i+1)/N_node
    # -------------------------------------------------------------

    c_tie=np.zeros(
        nvar,
        dtype=np.float64,
    )

    if na:
        c_tie[:na]=(
            np.arange(
                na,
                dtype=np.float64,
            )
            + 1.0
        ) / float(na)

    if n:
        c_tie[na:]=(
            np.arange(
                n,
                dtype=np.float64,
            )
            + 1.0
        ) / float(n)

    # EXACT unscaled R7-R7A primary-envelope inequality.
    Aub=sparse.csr_matrix(
        c_primary.reshape(
            1,
            -1,
        )
    )

    tie=linprog(
        c_tie,
        A_ub=Aub,
        b_ub=np.array(
            [secondary_rhs],
            dtype=np.float64,
        ),
        A_eq=Aeq,
        b_eq=rhs,
        bounds=bounds,
        method=LP_METHOD,
        options=options,
    )

    if not tie.success:
        raise ScientificFail(
            "secondary_LP_success_all_times",
            {
                "status":int(tie.status),
                "message":str(tie.message),
                "primary_fun":primary_fun,
                "primary_envelope_tolerance":tol_obj,
            },
        )

    x=np.asarray(
        tie.x,
        dtype=np.float64,
    )

    # =============================================================
    # ONE canonical R7-R7A pass/fail arithmetic.
    # =============================================================

    ineq_res=np.asarray(
        tie.ineqlin.residual,
        dtype=np.float64,
    ).reshape(-1)

    if len(ineq_res)!=1:
        raise GateError(
            "unexpected_secondary_ineqlin_residual_shape:"
            f"{ineq_res.shape}"
        )

    ineq_slack=float(
        ineq_res[0]
    )

    if (
        ineq_slack
        < CANONICAL_RESIDUAL_FLOOR
    ):
        raise ScientificFail(
            "canonical_secondary_residual_all_times",
            {
                "secondary_inequality_residual":
                    ineq_slack,
                "required_minimum":
                    CANONICAL_RESIDUAL_FLOOR,
                "primary_fun":
                    primary_fun,
                "primary_envelope_tolerance":
                    tol_obj,
                "secondary_rhs":
                    secondary_rhs,
            },
        )

    # -------------------------------------------------------------
    # Diagnostics only — NEVER independent PASS/FAIL authority.
    # -------------------------------------------------------------

    primary_x=np.asarray(
        primary.x,
        dtype=np.float64,
    )

    primary_fsum=fsum_dot(
        c_primary,
        primary_x,
    )

    primary_numpy=float(
        np.dot(
            c_primary,
            primary_x,
        )
    )

    tie_primary_fsum=fsum_dot(
        c_primary,
        x,
    )

    tie_primary_numpy=float(
        np.dot(
            c_primary,
            x,
        )
    )

    tie_obj_fsum=fsum_dot(
        c_tie,
        x,
    )

    # -------------------------------------------------------------
    # Node-balance certification.
    # -------------------------------------------------------------

    balance=np.asarray(
        Aeq@x-rhs,
        dtype=np.float64,
    )

    total_excess=float(
        np.sum(rhs)
    )

    bal_tol=max(
        1.0e-7,
        1.0e-11
        * max(
            total_excess,
            1.0,
        ),
    )

    max_balance=(
        float(
            np.max(
                np.abs(balance)
            )
        )
        if len(balance)
        else 0.0
    )

    if max_balance>bal_tol:
        raise ScientificFail(
            "max_node_balance_residual_kg",
            {
                "residual":max_balance,
                "tolerance":bal_tol,
            },
        )

    # -------------------------------------------------------------
    # Bounded terminal/local absorption.
    # -------------------------------------------------------------

    absorption=x[na:]

    if (
        np.any(
            absorption
            < -1.0e-8
        )
        or np.any(
            absorption-spare
            > 1.0e-7
        )
    ):
        raise ScientificFail(
            "absorption_bounds",
            {
                "minimum_absorption":
                    float(
                        np.min(absorption)
                    )
                    if len(absorption)
                    else 0.0,
                "maximum_capacity_overrun":
                    float(
                        np.max(
                            absorption-spare
                        )
                    )
                    if len(absorption)
                    else 0.0,
            },
        )

    return {
        "absorption":absorption,
        "arc_flow":x[:na],

        "solver_method":
            LP_METHOD,

        "primal_feasibility_tolerance":
            PRIMAL_FEAS_TOL,

        "dual_feasibility_tolerance":
            DUAL_FEAS_TOL,

        "reported_primary_fun":
            primary_fun,

        "certified_primary_optimum":
            primary_fun,

        "primary_fun_minus_certified":
            primary_fun-primary_fsum,

        "primary_objective_tolerance":
            tol_obj,

        "reported_secondary_fun":
            float(tie.fun),

        "certified_tie_primary_cost":
            tie_primary_fsum,

        "secondary_primary_certification_limit":
            secondary_rhs,

        "secondary_primary_margin":
            ineq_slack,

        "secondary_inequality_slack":
            ineq_slack,

        "secondary_tie_objective":
            tie_obj_fsum,

        "diagnostic_primary_math_fsum":
            primary_fsum,

        "diagnostic_primary_numpy_dot":
            primary_numpy,

        "diagnostic_secondary_primary_math_fsum":
            tie_primary_fsum,

        "diagnostic_secondary_primary_numpy_dot":
            tie_primary_numpy,

        "diagnostic_math_fsum_over_solver_rhs":
            tie_primary_fsum-secondary_rhs,

        "total_directed_edge_flow_kg":
            float(
                np.sum(x[:na])
            ),

        "maximum_directed_edge_flow_kg":
            float(
                np.max(x[:na])
            )
            if na
            else 0.0,

        "max_node_balance_residual_kg":
            max_balance,

        "balance_tolerance_kg":
            bal_tol,
    }


def reconcile_mass_strict(
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
    min_ineq_slack=float("inf")
    min_primary_margin=float("inf")
    max_reported_primary_fun_delta=0.0

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
                "certified_primary_optimum":0.0,
                "certified_tie_primary_cost":0.0,
                "secondary_inequality_slack":0.0,
                "component_mass_residual_kg":0.0,
            })
            continue

        active_components+=1
        eids=np.flatnonzero(labels[edge_u]==comp)
        if np.any(labels[edge_v[eids]]!=comp):
            raise GateError("support_graph_cross_component_edge")

        sol=solve_component_lp_strict(
            cnodes,eids,graph,excess,spare
        )
        final_supported[cnodes]+=sol["absorption"]

        before=float(np.sum(supported_raw[cnodes]))
        after=float(np.sum(final_supported[cnodes]))
        cres=after-before
        ctol=max(1.0e-7,1.0e-11*max(abs(before),1.0))
        if abs(cres)>ctol:
            raise ScientificFail(
                "cross_support_component_transfer_exact_zero",
                {
                    "component":int(comp),
                    "mass_residual_kg":cres,
                    "tolerance_kg":ctol,
                },
            )

        max_component_mass_residual=max(max_component_mass_residual,abs(cres))
        total_primary+=sol["certified_primary_optimum"]
        total_tie_primary+=sol["certified_tie_primary_cost"]
        total_edge_flow+=sol["total_directed_edge_flow_kg"]
        max_edge_flow=max(max_edge_flow,sol["maximum_directed_edge_flow_kg"])
        max_balance=max(max_balance,sol["max_node_balance_residual_kg"])
        min_ineq_slack=min(min_ineq_slack,sol["secondary_inequality_slack"])
        min_primary_margin=min(min_primary_margin,sol["secondary_primary_margin"])
        max_reported_primary_fun_delta=max(
            max_reported_primary_fun_delta,
            abs(sol["primary_fun_minus_certified"]),
        )

        comp_rows.append({
            "component":int(comp),
            "node_count":int(len(cnodes)),
            "edge_count":int(len(eids)),
            "excess_supply_kg":supply,
            "spare_capacity_kg":available,
            "LP_executed":True,
            "solver_method":sol["solver_method"],
            "primal_feasibility_tolerance":sol["primal_feasibility_tolerance"],
            "dual_feasibility_tolerance":sol["dual_feasibility_tolerance"],
            "reported_primary_fun":sol["reported_primary_fun"],
            "certified_primary_optimum":sol["certified_primary_optimum"],
            "primary_fun_minus_certified":sol["primary_fun_minus_certified"],
            "primary_objective_tolerance":sol["primary_objective_tolerance"],
            "reported_secondary_fun":sol["reported_secondary_fun"],
            "certified_tie_primary_cost":sol["certified_tie_primary_cost"],
            "secondary_primary_certification_limit":sol["secondary_primary_certification_limit"],
            "secondary_primary_margin":sol["secondary_primary_margin"],
            "secondary_inequality_slack":sol["secondary_inequality_slack"],
            "secondary_tie_objective":sol["secondary_tie_objective"],
            "total_directed_edge_flow_kg":sol["total_directed_edge_flow_kg"],
            "maximum_directed_edge_flow_kg":sol["maximum_directed_edge_flow_kg"],
            "max_node_balance_residual_kg":sol["max_node_balance_residual_kg"],
            "component_mass_residual_kg":cres,
        })

    final=np.zeros_like(raw)
    final[nodes]=final_supported

    unsupported=np.ones(len(raw),dtype=bool)
    unsupported[nodes]=False
    if not np.array_equal(
        final[unsupported],
        np.zeros(np.sum(unsupported),dtype=np.float64),
    ):
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
            {
                "relative_residual":rel,
                "raw_total_kg":total_raw,
                "final_total_kg":final_total,
            },
        )

    if active_components==0:
        min_ineq_slack=0.0
        min_primary_margin=0.0

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
        "certified_primary_min_cost_total":float(total_primary),
        "certified_tie_primary_cost_total":float(total_tie_primary),
        "total_directed_edge_flow_kg":float(total_edge_flow),
        "maximum_directed_edge_flow_kg":float(max_edge_flow),
        "max_node_balance_residual_kg":float(max_balance),
        "max_component_mass_residual_kg":float(max_component_mass_residual),
        "minimum_secondary_inequality_slack":float(min_ineq_slack),
        "minimum_secondary_primary_certification_margin":float(min_primary_margin),
        "maximum_reported_primary_fun_minus_certified_abs":float(max_reported_primary_fun_delta),
        "max_capacity_excess_after_reconciliation_kg":float(max_cap_excess),
        "total_component_mass_relative_closure":float(rel),
        "unsupported_added_mass_exact_zero":True,
    }
    return final.reshape(GRID),diag,comp_rows


def reconcile_mass_halo_strict(
    raw_mass_grid: np.ndarray,
    capacity_grid: np.ndarray,
    graph: dict[str,Any],
) -> tuple[np.ndarray,dict[str,Any],list[dict[str,Any]]]:
    """
    Prospectively frozen R7-R7D occupancy-domain reconciliation.

    Raw transport deposition remains unchanged and must occur only on
    exact SG7D support S0.

    S0:
        base   = min(raw, capacity)
        excess = max(raw - capacity, 0)
        spare  = capacity - base

    H1:
        initial component mass = 0
        base                   = 0
        excess supply          = 0
        spare capacity         = full physical cell capacity

    Excess may move through the unchanged S0 transport graph and may
    terminate through frozen directed S0 -> H1 entry arcs.

    H1 never originates a flow arc and is therefore never transit space.
    """

    raw=np.asarray(
        raw_mass_grid,
        dtype=np.float64,
    ).reshape(-1)

    cap=np.asarray(
        capacity_grid,
        dtype=np.float64,
    ).reshape(-1)

    nodes=np.asarray(
        graph["nodes"],
        dtype=np.int64,
    )

    s0_nodes=np.asarray(
        graph["s0_nodes"],
        dtype=np.int64,
    )

    h1_nodes=np.asarray(
        graph["h1_nodes"],
        dtype=np.int64,
    )

    s0_mask=np.asarray(
        graph["s0_mask"],
        dtype=bool,
    )

    h1_mask=np.asarray(
        graph["h1_mask"],
        dtype=bool,
    )

    labels=np.asarray(
        graph["component_labels"],
        dtype=np.int64,
    )

    arc_u=np.asarray(
        graph["arc_u"],
        dtype=np.int64,
    )

    arc_v=np.asarray(
        graph["arc_v"],
        dtype=np.int64,
    )

    arc_kind=np.asarray(
        graph["arc_kind"],
        dtype=np.int8,
    )

    # -----------------------------------------------------------------
    # Structural domain certification.
    # -----------------------------------------------------------------

    if len(nodes) != len(s0_nodes) + len(h1_nodes):
        raise GateError(
            "D1_cardinality_inconsistent"
        )

    if not np.array_equal(
        nodes[:len(s0_nodes)],
        s0_nodes,
    ):
        raise GateError(
            "D1_S0_prefix_not_preserved"
        )

    if not np.array_equal(
        nodes[len(s0_nodes):],
        h1_nodes,
    ):
        raise GateError(
            "D1_H1_suffix_not_preserved"
        )

    if np.any(
        s0_mask & h1_mask
    ):
        raise GateError(
            "S0_H1_mask_overlap"
        )

    if not np.all(
        s0_mask | h1_mask
    ):
        raise GateError(
            "D1_mask_partition_incomplete"
        )

    # H1 is terminal only.
    if np.any(
        h1_mask[arc_u]
    ):
        raise GateError(
            "H1_originating_arc_present"
        )

    halo_arc = (
        arc_kind == 1
    )

    if np.any(
        ~s0_mask[
            arc_u[halo_arc]
        ]
    ):
        raise GateError(
            "halo_arc_origin_not_S0"
        )

    if np.any(
        ~h1_mask[
            arc_v[halo_arc]
        ]
    ):
        raise GateError(
            "halo_arc_target_not_H1"
        )

    # -----------------------------------------------------------------
    # Raw SG7D/E37A deposition must remain exactly on S0.
    #
    # H1 is an occupancy extension only. It is NOT a new raw
    # streamline-deposition support.
    # -----------------------------------------------------------------

    outside_s0=np.ones(
        len(raw),
        dtype=bool,
    )

    outside_s0[s0_nodes]=False

    if not np.array_equal(
        raw[outside_s0],
        np.zeros(
            np.sum(outside_s0),
            dtype=np.float64,
        ),
    ):
        raise ScientificFail(
            "raw_deposition_outside_exact_S0_zero",
            {
                "absolute_outside_S0_mass_kg":
                    float(
                        np.sum(
                            np.abs(
                                raw[outside_s0]
                            )
                        )
                    ),
            },
        )

    # -----------------------------------------------------------------
    # D1-local raw mass and physical capacity.
    # -----------------------------------------------------------------

    raw_d1=raw[nodes]
    cap_d1=cap[nodes]

    if (
        np.any(~np.isfinite(raw_d1))
        or np.any(~np.isfinite(cap_d1))
    ):
        raise GateError(
            "nonfinite_D1_raw_or_capacity"
        )

    if np.any(
        raw_d1 < -1.0e-12
    ):
        raise GateError(
            "negative_D1_raw_component_mass"
        )

    if np.any(
        cap_d1 < -1.0e-12
    ):
        raise GateError(
            "negative_D1_capacity"
        )

    # -----------------------------------------------------------------
    # EXACT frozen S0 arithmetic.
    #
    # H1 base/excess remain exactly zero.
    # -----------------------------------------------------------------

    base=np.zeros(
        len(nodes),
        dtype=np.float64,
    )

    excess=np.zeros(
        len(nodes),
        dtype=np.float64,
    )

    base[s0_mask]=np.minimum(
        raw_d1[s0_mask],
        cap_d1[s0_mask],
    )

    excess[s0_mask]=np.maximum(
        raw_d1[s0_mask]
        - cap_d1[s0_mask],
        0.0,
    )

    # H1 begins at background saturation / zero incremental component
    # mass, so its full physical capacity is available.
    spare=cap_d1-base

    if not np.array_equal(
        base[h1_mask],
        np.zeros(
            np.sum(h1_mask),
            dtype=np.float64,
        ),
    ):
        raise GateError(
            "H1_base_component_mass_not_zero"
        )

    if not np.array_equal(
        excess[h1_mask],
        np.zeros(
            np.sum(h1_mask),
            dtype=np.float64,
        ),
    ):
        raise GateError(
            "H1_excess_supply_not_zero"
        )

    if not np.array_equal(
        spare[h1_mask],
        cap_d1[h1_mask],
    ):
        raise GateError(
            "H1_spare_not_full_physical_capacity"
        )

    # -----------------------------------------------------------------
    # D1 total-capacity feasibility.
    #
    # This is intentionally NOT a whole-grid capacity test.
    # -----------------------------------------------------------------

    total_raw=float(
        np.sum(raw)
    )

    total_d1_capacity=float(
        np.sum(cap_d1)
    )

    global_tol=max(
        1.0e-7,
        1.0e-11
        * max(
            abs(total_raw),
            1.0,
        ),
    )

    if (
        total_raw
        > total_d1_capacity
        + global_tol
    ):
        raise ScientificFail(
            "D1_global_mass_feasibility_all_times",
            {
                "raw_mass_kg":
                    total_raw,
                "D1_capacity_kg":
                    total_d1_capacity,
                "tolerance_kg":
                    global_tol,
            },
        )

    # -----------------------------------------------------------------
    # Component-wise directed reconciliation.
    # -----------------------------------------------------------------

    final_d1=base.copy()

    comp_rows=[]

    active_components=0

    total_primary=0.0
    total_tie_primary=0.0
    total_edge_flow=0.0

    max_edge_flow=0.0
    max_balance=0.0
    max_component_mass_residual=0.0

    min_ineq_slack=float("inf")
    min_primary_margin=float("inf")

    max_reported_primary_fun_delta=0.0

    for comp in range(
        int(graph["n_components"])
    ):

        cnodes=np.flatnonzero(
            labels == comp
        )

        if not len(cnodes):
            continue

        supply=float(
            np.sum(
                excess[cnodes]
            )
        )

        available=float(
            np.sum(
                spare[cnodes]
            )
        )

        tol=max(
            1.0e-7,
            1.0e-11
            * max(
                supply,
                1.0,
            ),
        )

        if (
            supply
            > available
            + tol
        ):
            raise ScientificFail(
                "D1_component_feasibility_all_times",
                {
                    "component":
                        int(comp),
                    "excess_supply_kg":
                        supply,
                    "spare_capacity_kg":
                        available,
                    "tolerance_kg":
                        tol,
                },
            )

        # Explicit directed arcs wholly within this weak component.
        aids=np.flatnonzero(
            labels[arc_u]
            == comp
        )

        if np.any(
            labels[
                arc_v[aids]
            ]
            != comp
        ):
            raise GateError(
                "D1_arc_crosses_weak_component"
            )

        if supply <= tol:
            comp_rows.append({
                "component":
                    int(comp),

                "node_count":
                    int(len(cnodes)),

                "S0_node_count":
                    int(
                        np.sum(
                            s0_mask[cnodes]
                        )
                    ),

                "H1_node_count":
                    int(
                        np.sum(
                            h1_mask[cnodes]
                        )
                    ),

                "directed_arc_count":
                    int(len(aids)),

                "S0_backbone_arc_count":
                    int(
                        np.sum(
                            arc_kind[aids]
                            == 0
                        )
                    ),

                "H1_entry_arc_count":
                    int(
                        np.sum(
                            arc_kind[aids]
                            == 1
                        )
                    ),

                "excess_supply_kg":
                    supply,

                "spare_capacity_kg":
                    available,

                "LP_executed":
                    False,

                "certified_primary_optimum":
                    0.0,

                "certified_tie_primary_cost":
                    0.0,

                "secondary_inequality_slack":
                    0.0,

                "component_mass_residual_kg":
                    0.0,
            })

            continue

        active_components+=1

        sol=solve_directed_component_lp_strict(
            cnodes,
            aids,
            graph,
            excess,
            spare,
        )

        final_d1[cnodes]+=sol[
            "absorption"
        ]

        # Raw H1 mass is zero by contract, so this is also the
        # exact pre-reconciliation component mass.
        before=float(
            np.sum(
                raw_d1[cnodes]
            )
        )

        after=float(
            np.sum(
                final_d1[cnodes]
            )
        )

        cres=after-before

        ctol=max(
            1.0e-7,
            1.0e-11
            * max(
                abs(before),
                1.0,
            ),
        )

        if abs(cres)>ctol:
            raise ScientificFail(
                "cross_D1_component_transfer_exact_zero",
                {
                    "component":
                        int(comp),
                    "mass_residual_kg":
                        cres,
                    "tolerance_kg":
                        ctol,
                },
            )

        max_component_mass_residual=max(
            max_component_mass_residual,
            abs(cres),
        )

        total_primary+=sol[
            "certified_primary_optimum"
        ]

        total_tie_primary+=sol[
            "certified_tie_primary_cost"
        ]

        total_edge_flow+=sol[
            "total_directed_edge_flow_kg"
        ]

        max_edge_flow=max(
            max_edge_flow,
            sol[
                "maximum_directed_edge_flow_kg"
            ],
        )

        max_balance=max(
            max_balance,
            sol[
                "max_node_balance_residual_kg"
            ],
        )

        min_ineq_slack=min(
            min_ineq_slack,
            sol[
                "secondary_inequality_slack"
            ],
        )

        min_primary_margin=min(
            min_primary_margin,
            sol[
                "secondary_primary_margin"
            ],
        )

        max_reported_primary_fun_delta=max(
            max_reported_primary_fun_delta,
            abs(
                sol[
                    "primary_fun_minus_certified"
                ]
            ),
        )

        comp_rows.append({
            "component":
                int(comp),

            "node_count":
                int(len(cnodes)),

            "S0_node_count":
                int(
                    np.sum(
                        s0_mask[cnodes]
                    )
                ),

            "H1_node_count":
                int(
                    np.sum(
                        h1_mask[cnodes]
                    )
                ),

            "directed_arc_count":
                int(len(aids)),

            "S0_backbone_arc_count":
                int(
                    np.sum(
                        arc_kind[aids]
                        == 0
                    )
                ),

            "H1_entry_arc_count":
                int(
                    np.sum(
                        arc_kind[aids]
                        == 1
                    )
                ),

            "excess_supply_kg":
                supply,

            "spare_capacity_kg":
                available,

            "LP_executed":
                True,

            "solver_method":
                sol[
                    "solver_method"
                ],

            "primal_feasibility_tolerance":
                sol[
                    "primal_feasibility_tolerance"
                ],

            "dual_feasibility_tolerance":
                sol[
                    "dual_feasibility_tolerance"
                ],

            "reported_primary_fun":
                sol[
                    "reported_primary_fun"
                ],

            "certified_primary_optimum":
                sol[
                    "certified_primary_optimum"
                ],

            "primary_fun_minus_certified":
                sol[
                    "primary_fun_minus_certified"
                ],

            "primary_objective_tolerance":
                sol[
                    "primary_objective_tolerance"
                ],

            "reported_secondary_fun":
                sol[
                    "reported_secondary_fun"
                ],

            "certified_tie_primary_cost":
                sol[
                    "certified_tie_primary_cost"
                ],

            "secondary_primary_certification_limit":
                sol[
                    "secondary_primary_certification_limit"
                ],

            "secondary_primary_margin":
                sol[
                    "secondary_primary_margin"
                ],

            "secondary_inequality_slack":
                sol[
                    "secondary_inequality_slack"
                ],

            "secondary_tie_objective":
                sol[
                    "secondary_tie_objective"
                ],

            "total_directed_edge_flow_kg":
                sol[
                    "total_directed_edge_flow_kg"
                ],

            "maximum_directed_edge_flow_kg":
                sol[
                    "maximum_directed_edge_flow_kg"
                ],

            "max_node_balance_residual_kg":
                sol[
                    "max_node_balance_residual_kg"
                ],

            "component_mass_residual_kg":
                cres,
        })

    # -----------------------------------------------------------------
    # Return to full Cartesian grid.
    # -----------------------------------------------------------------

    final=np.zeros_like(
        raw
    )

    final[nodes]=final_d1

    outside_d1=np.ones(
        len(raw),
        dtype=bool,
    )

    outside_d1[nodes]=False

    if not np.array_equal(
        final[outside_d1],
        np.zeros(
            np.sum(outside_d1),
            dtype=np.float64,
        ),
    ):
        raise ScientificFail(
            "outside_D1_added_mass_exact_zero",
            None,
        )

    # -----------------------------------------------------------------
    # Capacity certification.
    # -----------------------------------------------------------------

    max_cap_excess=float(
        np.max(
            final-cap
        )
    )

    cap_tol=max(
        1.0e-7,
        1.0e-11
        * max(
            float(
                np.max(cap)
            ),
            1.0,
        ),
    )

    if (
        max_cap_excess
        > cap_tol
    ):
        raise ScientificFail(
            "max_capacity_excess_after_reconciliation_kg",
            {
                "excess":
                    max_cap_excess,
                "tolerance":
                    cap_tol,
            },
        )

    # -----------------------------------------------------------------
    # Global mass conservation.
    # -----------------------------------------------------------------

    final_total=float(
        np.sum(final)
    )

    rel=abs(
        final_total
        - total_raw
    ) / max(
        abs(total_raw),
        1.0,
    )

    if rel>1.0e-10:
        raise ScientificFail(
            "total_component_mass_relative_closure",
            {
                "relative_residual":
                    rel,
                "raw_total_kg":
                    total_raw,
                "final_total_kg":
                    final_total,
            },
        )

    if active_components==0:
        min_ineq_slack=0.0
        min_primary_margin=0.0

    # -----------------------------------------------------------------
    # H1-specific diagnostics.
    #
    # These diagnose use of the frozen occupancy extension.
    # They do NOT impose an unfrozen requirement that early H1 mass
    # must be zero.
    # -----------------------------------------------------------------

    h1_component_mass=float(
        np.sum(
            final_d1[h1_mask]
        )
    )

    h1_capacity=float(
        np.sum(
            cap_d1[h1_mask]
        )
    )

    h1_occupied_cell_count=int(
        np.sum(
            final_d1[h1_mask]
            > 1.0e-9
        )
    )

    h1_max_cell_mass=(
        float(
            np.max(
                final_d1[h1_mask]
            )
        )
        if np.any(h1_mask)
        else 0.0
    )

    s0_component_mass=float(
        np.sum(
            final_d1[s0_mask]
        )
    )

    diag={
        "raw_total_component_mass_kg":
            total_raw,

        "final_total_component_mass_kg":
            final_total,

        "D1_capacity_kg":
            total_d1_capacity,

        "D1_capacity_fraction":
            (
                total_raw
                / total_d1_capacity
                if total_d1_capacity>0
                else 0.0
            ),

        "S0_capacity_kg":
            float(
                np.sum(
                    cap_d1[s0_mask]
                )
            ),

        "H1_capacity_kg":
            h1_capacity,

        "raw_overloaded_cell_count":
            int(
                np.sum(
                    raw-cap
                    > cap_tol
                )
            ),

        "raw_max_capacity_excess_kg":
            float(
                np.max(
                    raw-cap
                )
            ),

        "raw_total_excess_supply_kg":
            float(
                np.sum(excess)
            ),

        "recipient_cell_count":
            int(
                np.sum(
                    final_d1
                    > base
                    + 1.0e-9
                )
            ),

        "active_component_count":
            int(
                active_components
            ),

        "certified_primary_min_cost_total":
            float(
                total_primary
            ),

        "certified_tie_primary_cost_total":
            float(
                total_tie_primary
            ),

        "total_directed_edge_flow_kg":
            float(
                total_edge_flow
            ),

        "maximum_directed_edge_flow_kg":
            float(
                max_edge_flow
            ),

        "max_node_balance_residual_kg":
            float(
                max_balance
            ),

        "max_component_mass_residual_kg":
            float(
                max_component_mass_residual
            ),

        "minimum_secondary_inequality_slack":
            float(
                min_ineq_slack
            ),

        "minimum_secondary_primary_certification_margin":
            float(
                min_primary_margin
            ),

        "maximum_reported_primary_fun_minus_certified_abs":
            float(
                max_reported_primary_fun_delta
            ),

        "max_capacity_excess_after_reconciliation_kg":
            float(
                max_cap_excess
            ),

        "total_component_mass_relative_closure":
            float(rel),

        "outside_D1_added_mass_exact_zero":
            True,

        "S0_final_component_mass_kg":
            s0_component_mass,

        "H1_final_component_mass_kg":
            h1_component_mass,

        "H1_capacity_fraction_used":
            (
                h1_component_mass
                / h1_capacity
                if h1_capacity>0
                else 0.0
            ),

        "H1_occupied_cell_count":
            h1_occupied_cell_count,

        "H1_max_cell_component_mass_kg":
            h1_max_cell_mass,

        "H1_fraction_of_total_component_mass":
            (
                h1_component_mass
                / max(
                    total_raw,
                    1.0,
                )
            ),
    }

    return (
        final.reshape(GRID),
        diag,
        comp_rows,
    )


def self_test() -> None:
    """
    R7-R7E implementation regression tests only.

    No Foundation Case inference, production LP execution, or mapback
    is performed here.

    Tests:
      1. Historical R7-R7B solver regression.
      2. Exact D1 = S0 union H1 geometry.
      3. Exact historical S0 directed-variable ordering.
      4. Directed solver equivalence on pure S0.
      5. Terminal S0 -> H1 occupancy reconciliation.
      6. Raw deposition onto H1 remains forbidden.
    """

    # =============================================================
    # TEST 1 — untouched historical R7-R7B solver regression
    # =============================================================

    old_graph={
        "nodes":
            np.array(
                [0,1,2],
                dtype=np.int64,
            ),

        "edge_u":
            np.array(
                [0,1],
                dtype=np.int64,
            ),

        "edge_v":
            np.array(
                [1,2],
                dtype=np.int64,
            ),

        "edge_cost":
            np.array(
                [5.0,5.0],
                dtype=np.float64,
            ),
    }

    old_excess=np.array(
        [2.0,0.0,0.0],
        dtype=np.float64,
    )

    old_spare=np.array(
        [0.0,1.0,3.0],
        dtype=np.float64,
    )

    old_sol=solve_component_lp_strict(
        np.array(
            [0,1,2],
            dtype=np.int64,
        ),
        np.array(
            [0,1],
            dtype=np.int64,
        ),
        old_graph,
        old_excess,
        old_spare,
    )

    if not np.allclose(
        old_sol["absorption"],
        [0.0,1.0,1.0],
        rtol=0.0,
        atol=1.0e-8,
    ):
        raise RuntimeError(
            "R7R7B_regression_absorption:"
            f"{old_sol['absorption']}"
        )

    if abs(
        old_sol["reported_primary_fun"]
        - 15.0
    ) > 1.0e-8:
        raise RuntimeError(
            "R7R7B_regression_primary:"
            f"{old_sol['reported_primary_fun']}"
        )

    if (
        old_sol["secondary_inequality_slack"]
        < CANONICAL_RESIDUAL_FLOOR
    ):
        raise RuntimeError(
            "R7R7B_regression_secondary_slack:"
            f"{old_sol['secondary_inequality_slack']}"
        )

    # =============================================================
    # TEST 2 — exact R7-R7D D1 geometry
    #
    # Three horizontally adjacent S0 cells.
    # =============================================================

    k=4
    j=10
    i=10

    a=(
        k*NX*NY
        + j*NX
        + i
    )

    b=a+1
    c=a+2

    operator={
        "streamline":
            np.array(
                [0,0,0],
                dtype=np.int64,
            ),

        "flat_cell":
            np.array(
                [a,b,c],
                dtype=np.int64,
            ),
    }

    graph=build_extended_halo_graph(
        operator
    )

    expected_s0=np.array(
        [a,b,c],
        dtype=np.int64,
    )

    if not np.array_equal(
        graph["s0_nodes"],
        expected_s0,
    ):
        raise RuntimeError(
            "R7R7E_S0_geometry:"
            f"{graph['s0_nodes']}"
        )

    if len(
        np.intersect1d(
            graph["s0_nodes"],
            graph["h1_nodes"],
        )
    ):
        raise RuntimeError(
            "R7R7E_S0_H1_overlap"
        )

    # Every H1 parent relation must be same-k and exactly one x/y face.
    hp=np.asarray(
        graph["halo_parent_pairs_flat"],
        dtype=np.int64,
    )

    sf=hp[:,0]
    hf=hp[:,1]

    si=sf%NX
    sj=(sf//NX)%NY
    sk=sf//(NX*NY)

    hi=hf%NX
    hj=(hf//NX)%NY
    hk=hf//(NX*NY)

    if not np.all(
        sk==hk
    ):
        raise RuntimeError(
            "R7R7E_vertical_halo_detected"
        )

    if not np.all(
        (
            np.abs(si-hi)
            + np.abs(sj-hj)
        )
        == 1
    ):
        raise RuntimeError(
            "R7R7E_nonface_halo_detected"
        )

    # =============================================================
    # TEST 3 — historical S0 variable order + terminal semantics
    # =============================================================

    arc_kind=np.asarray(
        graph["arc_kind"],
        dtype=np.int8,
    )

    support_ids=np.flatnonzero(
        arc_kind==0
    )

    halo_ids=np.flatnonzero(
        arc_kind==1
    )

    if not np.array_equal(
        graph["arc_u"][support_ids],
        np.array(
            [0,1,1,2],
            dtype=np.int64,
        ),
    ):
        raise RuntimeError(
            "R7R7E_S0_arc_u_order:"
            f"{graph['arc_u'][support_ids]}"
        )

    if not np.array_equal(
        graph["arc_v"][support_ids],
        np.array(
            [1,0,2,1],
            dtype=np.int64,
        ),
    ):
        raise RuntimeError(
            "R7R7E_S0_arc_v_order:"
            f"{graph['arc_v'][support_ids]}"
        )

    if not np.all(
        halo_ids
        > np.max(support_ids)
    ):
        raise RuntimeError(
            "R7R7E_H1_variables_not_appended"
        )

    if np.any(
        graph["h1_mask"][
            graph["arc_u"]
        ]
    ):
        raise RuntimeError(
            "R7R7E_H1_originating_arc"
        )

    if not np.all(
        graph["s0_mask"][
            graph["arc_u"][halo_ids]
        ]
    ):
        raise RuntimeError(
            "R7R7E_H1_entry_origin_not_S0"
        )

    if not np.all(
        graph["h1_mask"][
            graph["arc_v"][halo_ids]
        ]
    ):
        raise RuntimeError(
            "R7R7E_H1_entry_target_not_H1"
        )

    if not np.all(
        graph["arc_cost"][halo_ids]
        == HALO_ENTRY_COST
    ):
        raise RuntimeError(
            "R7R7E_H1_entry_cost"
        )

    # =============================================================
    # TEST 4 — builder + directed solver reduces exactly to R7-R7B
    # on the S0-only variable subset.
    # =============================================================

    excess=np.zeros(
        len(graph["nodes"]),
        dtype=np.float64,
    )

    spare=np.zeros(
        len(graph["nodes"]),
        dtype=np.float64,
    )

    excess[:3]=old_excess
    spare[:3]=old_spare

    directed_sol=solve_directed_component_lp_strict(
        np.arange(
            3,
            dtype=np.int64,
        ),
        support_ids,
        graph,
        excess,
        spare,
    )

    if not np.allclose(
        directed_sol["absorption"],
        old_sol["absorption"],
        rtol=0.0,
        atol=1.0e-8,
    ):
        raise RuntimeError(
            "R7R7E_directed_regression_absorption:"
            f"{directed_sol['absorption']}"
        )

    if abs(
        directed_sol["reported_primary_fun"]
        - old_sol["reported_primary_fun"]
    ) > 1.0e-10:
        raise RuntimeError(
            "R7R7E_directed_regression_primary"
        )

    if abs(
        directed_sol["reported_secondary_fun"]
        - old_sol["reported_secondary_fun"]
    ) > 1.0e-10:
        raise RuntimeError(
            "R7R7E_directed_regression_secondary"
        )

    # =============================================================
    # TEST 5 — actual terminal H1 reconciliation.
    #
    # One S0 cell with 2 kg excess.
    # Four same-layer H1 neighbors, each with 3 kg spare.
    # All 2 kg must terminate in H1 with cost 10.
    # =============================================================

    center=(
        4*NX*NY
        + 20*NX
        + 20
    )

    terminal_operator={
        "streamline":
            np.array(
                [0,0],
                dtype=np.int64,
            ),

        "flat_cell":
            np.array(
                [center,center],
                dtype=np.int64,
            ),
    }

    terminal_graph=build_extended_halo_graph(
        terminal_operator
    )

    raw=np.zeros(
        NX*NY*NZ,
        dtype=np.float64,
    )

    cap=np.zeros(
        NX*NY*NZ,
        dtype=np.float64,
    )

    raw[center]=2.0

    cap[
        terminal_graph["h1_nodes"]
    ]=3.0

    final,diag,_=reconcile_mass_halo_strict(
        raw.reshape(GRID),
        cap.reshape(GRID),
        terminal_graph,
    )

    final_flat=final.reshape(-1)

    if abs(
        final_flat[center]
    ) > 1.0e-8:
        raise RuntimeError(
            "R7R7E_terminal_S0_mass_not_zero:"
            f"{final_flat[center]}"
        )

    h1_mass=float(
        np.sum(
            final_flat[
                terminal_graph["h1_nodes"]
            ]
        )
    )

    if abs(
        h1_mass-2.0
    ) > 1.0e-8:
        raise RuntimeError(
            "R7R7E_terminal_H1_mass:"
            f"{h1_mass}"
        )

    if abs(
        diag[
            "certified_primary_min_cost_total"
        ]
        - 10.0
    ) > 1.0e-8:
        raise RuntimeError(
            "R7R7E_terminal_primary:"
            f"{diag['certified_primary_min_cost_total']}"
        )

    if (
        diag[
            "total_component_mass_relative_closure"
        ]
        > 1.0e-10
    ):
        raise RuntimeError(
            "R7R7E_terminal_mass_closure:"
            f"{diag['total_component_mass_relative_closure']}"
        )

    if (
        diag[
            "max_capacity_excess_after_reconciliation_kg"
        ]
        > 1.0e-7
    ):
        raise RuntimeError(
            "R7R7E_terminal_capacity_excess:"
            f"{diag['max_capacity_excess_after_reconciliation_kg']}"
        )

    # =============================================================
    # TEST 6 — H1 may receive reconciled occupancy but may never
    # receive raw SG7D/E37A deposition.
    # =============================================================

    bad_raw=np.zeros(
        NX*NY*NZ,
        dtype=np.float64,
    )

    bad_raw[
        terminal_graph["h1_nodes"][0]
    ]=1.0

    rejected=False

    try:
        reconcile_mass_halo_strict(
            bad_raw.reshape(GRID),
            cap.reshape(GRID),
            terminal_graph,
        )

    except ScientificFail as exc:
        if (
            exc.gate
            ==
            "raw_deposition_outside_exact_S0_zero"
        ):
            rejected=True

    if not rejected:
        raise RuntimeError(
            "R7R7E_raw_H1_deposition_not_rejected"
        )

    print(
        "POSTV16-AV1-D-R7-R7E self-test: PASS"
    )


def main(root: Path, drive: Path) -> int:
    import tensorflow as tf

    gates: dict[str,dict[str,Any]]={}
    stage="preflight"
    inference_performed=False
    reconciliation_started=False
    completed_times=0
    out=drive/OUT_REL
    blocked=drive/BLOCKED_REL
    time_rows: list[dict[str,Any]]=[]
    component_rows: list[dict[str,Any]]=[]

    def gate(name: str, passed: Any, value: Any=None) -> None:
        ok=bool(passed)
        gates[name]={"passed":ok,"value":value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, passed: Any, value: Any=None) -> None:
        ok=bool(passed)
        gates[name]={
            "passed":ok,
            "value":value,
            "scientific_execution_gate":True,
        }
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" — {value}" if value is not None else ""))
        if not ok:
            raise ScientificFail(name,value)

    print("="*190)
    print("POSTV16-AV1-D-R7-R7E — FROZEN SINGLE-RING HORIZONTAL FACE-HALO OCCUPANCY-DOMAIN EXECUTION")
    print("="*190)
    print("ONE FROZEN R7-R7D OCCUPANCY-DOMAIN CANDIDATE. R7-R2 S0 BACKBONE AND R7-R7A ARITHMETIC REMAIN FROZEN.")
    print("NO R7-R7B RETEST. NO TRAINING. NO CHECKPOINT/B1/BOUND CHANGE. NO GEOLOGY0031 OR ACCEPTANCE TRUTH.")
    print("R7-R7D DOMAIN GEOMETRY IS BOUND HERE BEFORE ANY R7-R7E EXECUTION. NO ALTERNATE CANDIDATE IS AUTHORIZED.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R7D_commit",parent==PARENT_R7R7D_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==blob,actual)

        stage="R7R7D_protocol_binding"

        r7r7d=drive/R7R7D_REL
        gate(
            "R7R7D_output_present",
            r7r7d.is_dir(),
            str(r7r7d),
        )

        md=verify_manifest(
            r7r7d,
            R7R7D_MANIFEST,
        )
        gate(
            "R7R7D_manifest_SHA_closure",
            True,
            len(md),
        )

        sd=load_json(r7r7d/R7R7D_SUMMARY)
        pd=load_json(r7r7d/R7R7D_PROTOCOL)
        fd=load_json(r7r7d/R7R7D_FREEZE)

        gate(
            "R7R7D_status_exact",
            sd["status"]==R7R7D_STATUS,
            sd["status"],
        )
        gate(
            "R7R7D_protocol_exact",
            sd["protocol_id"]==R7R7D_PROTOCOL_ID,
            sd["protocol_id"],
        )

        gate(
            "R7R7D_R7R3_immutable_FAIL",
            sd["R7R3_result"]=="FAIL",
        )
        gate(
            "R7R7D_R7R6_immutable_FAIL",
            sd["R7R6_result"]=="FAIL",
        )
        gate(
            "R7R7D_R7R7B_immutable_FAIL",
            sd["R7R7B_result"]=="FAIL",
        )

        gate(
            "R7R7D_domain_exact",
            sd["new_domain"]
            =="single non-recursive same-layer x/y face-neighbor halo",
        )
        gate(
            "R7R7D_halo_transit_forbidden",
            sd["halo_transit_allowed"] is False,
        )
        gate(
            "R7R7D_halo_reverse_forbidden",
            sd["halo_reverse_edges_allowed"] is False,
        )
        gate(
            "R7R7D_vertical_halo_forbidden",
            sd["vertical_halo_allowed"] is False,
        )
        gate(
            "R7R7D_diagonal_halo_forbidden",
            sd["diagonal_halo_allowed"] is False,
        )
        gate(
            "R7R7D_adaptive_growth_forbidden",
            sd["adaptive_growth_allowed"] is False,
        )
        gate(
            "R7R7D_entry_cost_exact",
            float(sd["entry_cost_units"])==HALO_ENTRY_COST,
            sd["entry_cost_units"],
        )

        gate(
            "R7R7D_candidate_not_capacity_pretested",
            sd["candidate_capacity_pretested"] is False,
        )
        gate(
            "R7R7D_R7R7E_authorized",
            sd["R7R7E_authorized"] is True,
        )

        gate(
            "R7R7D_candidate_count_one",
            int(fd["candidate_count"])==1,
            fd["candidate_count"],
        )
        gate(
            "R7R7D_no_execution_in_freeze",
            fd["execution_in_R7R7D"] is False,
        )
        gate(
            "R7R7D_no_capacity_pretest_in_freeze",
            fd["foundation_capacity_pretest_in_R7R7D"] is False,
        )
        gate(
            "R7R7D_terminal_sink_only_frozen",
            fd["terminal_sink_only_frozen"] is True,
        )
        gate(
            "R7R7D_support_graph_preserved",
            fd["R7R2_support_graph_preserved"] is True,
        )
        gate(
            "R7R7D_arithmetic_preserved",
            fd["R7R7A_arithmetic_preserved"] is True,
        )
        gate(
            "R7R7D_execution_authorized",
            fd["R7R7E_execution_authorized"] is True,
        )

        halo=pd["new_halo_set_H1"]
        graph_sem=pd["graph_semantics"]

        gate(
            "R7R7D_H1_nonrecursive",
            halo["recursive_growth"] is False,
        )
        gate(
            "R7R7D_H1_same_layer_only",
            halo["same_layer_only"] is True,
        )
        gate(
            "R7R7D_H1_vertical_false",
            halo["vertical_neighbors_allowed"] is False,
        )
        gate(
            "R7R7D_H1_diagonal_false",
            halo["diagonal_neighbors_allowed"] is False,
        )
        gate(
            "R7R7D_H1_second_ring_false",
            halo["second_ring_neighbors_allowed"] is False,
        )
        gate(
            "R7R7D_H1_role_terminal_sink",
            halo["role"]
            =="terminal finite-volume occupancy sinks only",
        )

        gate(
            "R7R7D_reverse_edges_false",
            graph_sem["H1_to_S0_reverse_edges"] is False,
        )
        gate(
            "R7R7D_H1_H1_edges_false",
            graph_sem["H1_to_H1_edges"] is False,
        )
        gate(
            "R7R7D_H1_transit_false",
            graph_sem["H1_as_transit_nodes"] is False,
        )
        gate(
            "R7R7D_cross_layer_new_edges_false",
            graph_sem["cross_layer_new_edges"] is False,
        )
        gate(
            "R7R7D_new_edge_cost_exact",
            float(graph_sem["new_edge_cost_units"])
            ==HALO_ENTRY_COST,
            graph_sem["new_edge_cost_units"],
        )

        stage="R7R7A_protocol_binding"
        r7r7a=drive/R7R7A_REL
        gate("R7R7A_output_present",r7r7a.is_dir(),str(r7r7a))
        m=verify_manifest(r7r7a,R7R7A_MANIFEST)
        gate("R7R7A_manifest_SHA_closure",True,len(m))

        sA=load_json(r7r7a/R7R7A_SUMMARY)
        pA=load_json(r7r7a/R7R7A_PROTOCOL)
        fA=load_json(r7r7a/R7R7A_FREEZE)

        gate("R7R7A_status_exact",sA["status"]==R7R7A_STATUS,sA["status"])
        gate("R7R7A_protocol_id_exact",sA["protocol_id"]==NUMERICAL_PROTOCOL_ID,sA["protocol_id"])
        gate("R7R7A_R7R3_immutable_FAIL",sA["R7R3_result"]=="FAIL")
        gate("R7R7A_R7R6_immutable_FAIL",sA["R7R6_result"]=="FAIL")
        gate("R7R7A_canonical_arithmetic_exact",sA["canonical_arithmetic"]=="solver-native unscaled secondary inequality residual")
        gate("R7R7A_canonical_pass_rule_exact",sA["canonical_pass_rule"]=="secondary.success and residual >= -1e-10")
        gate("R7R7A_primary_envelope_unchanged",sA["primary_envelope_formula_changed"] is False)
        gate("R7R7A_constraint_unscaled",sA["constraint_scaling_applied"] is False)
        gate("R7R7A_solver_method_exact",sA["solver_method"]==LP_METHOD)
        gate("R7R7A_primal_tolerance_exact",float(sA["primal_feasibility_tolerance"])==PRIMAL_FEAS_TOL)
        gate("R7R7A_dual_tolerance_exact",float(sA["dual_feasibility_tolerance"])==DUAL_FEAS_TOL)
        gate("R7R7A_fsum_not_pass_fail",sA["independent_fsum_pass_fail_gate"] is False)
        gate("R7R7A_physical_operator_unchanged",sA["physical_operator_changed"] is False)
        gate("R7R7A_R7R7B_authorized",sA["R7R7B_authorized"] is True)

        gate("R7R7A_protocol_status_exact",pA["status"]==R7R7A_STATUS)
        gate("R7R7A_protocol_identity",pA["protocol_id"]==NUMERICAL_PROTOCOL_ID)
        gate("R7R7A_physical_protocol_identity",pA["physical_authority"]["protocol_id"]==PHYSICAL_PROTOCOL_ID)
        gate("R7R7A_physical_reconciliation_unchanged",pA["physical_authority"]["changed"] is False)

        solver=pA["solver_authority"]
        gate("R7R7A_solver_highs_ds",solver["method"]==LP_METHOD)
        gate("R7R7A_presolve_true",solver["presolve"] is True)
        gate("R7R7A_primal_tol_exact",float(solver["primal_feasibility_tolerance"])==PRIMAL_FEAS_TOL)
        gate("R7R7A_dual_tol_exact",float(solver["dual_feasibility_tolerance"])==DUAL_FEAS_TOL)

        canon=pA["canonical_primary_envelope_semantics"]
        gate("R7R7A_authority_name_exact",canon["authority_name"]=="SOLVER_NATIVE_UNSCALED_SECONDARY_INEQUALITY_RESIDUAL")
        gate("R7R7A_primary_fun_authority",canon["primary_optimum_authority"]=="float(primary.fun) returned by the frozen highs-ds primary solve")
        gate("R7R7A_envelope_formula_exact",canon["primary_envelope_formula"]=="tol_obj = max(1e-8, 1e-12*max(abs(primary.fun),1))")
        gate("R7R7A_coefficients_unscaled",canon["coefficient_scaling_applied"] is False)
        gate("R7R7A_single_quantity_exact",canon["single_pass_fail_quantity"]=="float(secondary.ineqlin.residual[0])")
        gate("R7R7A_residual_floor_exact",float(canon["residual_floor"])==CANONICAL_RESIDUAL_FLOOR)
        gate("R7R7A_fsum_diagnostic_only",canon["independent_math_fsum_is_pass_fail_authority"] is False)
        gate("R7R7A_numpy_diagnostic_only",canon["independent_numpy_dot_is_pass_fail_authority"] is False)
        gate("R7R7A_solver_constraint_only_authority",canon["solver_reported_secondary_primary_constraint_is_only_authority"] is True)

        gate("R7R7A_candidate_count_one",int(fA["candidate_count"])==1,fA["candidate_count"])
        gate("R7R7A_execution_authorized",fA["R7R7B_execution_authorized"] is True)
        gate("R7R7A_no_prior_LP_execution",fA["LP_execution_performed"] is False)
        gate("R7R7A_no_prior_model_inference",fA["model_inference_performed"] is False)

        stage="runtime_authority_binding"
        r6=drive/R6_REL
        weights=r6/R6_WEIGHTS
        norm=r6/R6_NORM
        gate("R6_weights_SHA_exact",weights.is_file() and sha256_file(weights)==WEIGHTS_SHA)
        gate("R6_norm_SHA_exact",norm.is_file() and sha256_file(norm)==NORM_SHA)
        foundation=find_named_exact([root,drive],FOUNDATION_NAME,FOUNDATION_SHA)
        gate("foundation_case0001_SHA_exact",sha256_file(foundation)==FOUNDATION_SHA,str(foundation))

        with np.load(foundation,allow_pickle=False) as z:
            keys=[
                "Kx","Ky","Kz","porosity","pressure",
                "Qx","Qy","Qz","Vx","Vy","Vz",
                "streamline_xyz","pollock_tof","streamline_weight",
            ]
            gate("foundation_required_arrays_present",set(keys).issubset(set(z.files)),sorted(z.files))
            d={k:np.asarray(z[k]).copy() for k in keys}

        stage="canonical_conditioning"
        r7=load_module(root/R7,"r7r6_r7")
        b2=load_module(root/B2,"r7r6_b2")
        c2=load_module(root/C2,"r7r6_c2")
        c26=load_module(root/C26,"r7r6_c26")
        b1=load_module(root/B1,"r7r6_b1")
        r2=load_module(root/R2,"r7r6_r2")
        e37a=load_module(root/E37A,"r7r6_e37a")

        pressure=np.asarray(d["pressure"],dtype=np.float64)
        cx,cy,cz=r7.face_to_cell(d["Vx"],d["Vy"],d["Vz"])
        _,_,_,source_mask,_=b2.bind_injector_sources(d["Qx"],d["Qy"],d["Qz"])
        adv,adv_audit=r7.solve_adv(
            cx,cy,cz,np.asarray(source_mask,bool),DX,DY,DZ
        )
        gate(
            "ADV_relative_PDE_residual_lt_1e8",
            adv_audit["relative_L2_residual"]<1e-8,
            adv_audit["relative_L2_residual"],
        )

        xyz=np.asarray(d["streamline_xyz"],dtype=np.float64)
        ptau=np.asarray(d["pollock_tof"],dtype=np.float64)
        terminal=ptau[:,-1]
        gate(
            "Pollock_terminal_TOF_positive",
            np.all(terminal>0),
            [float(np.min(terminal)),float(np.max(terminal))],
        )

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
        sci_gate(
            "accepted_transport_prediction_shape_exact",
            pred_flat.shape==(NSAMP,NN),
            pred_flat.shape,
        )
        sci_gate("accepted_transport_prediction_finite",np.isfinite(pred_flat).all())
        sci_gate(
            "accepted_transport_saturation_bounds",
            float(np.min(pred_flat))>=BACKGROUND-1e-12
            and float(np.max(pred_flat))<=INJECTED+1e-12,
            [float(np.min(pred_flat)),float(np.max(pred_flat))],
        )
        pred201=pred_flat.reshape(NT,NSL,NN)

        stage="B1_exact_representation_bridge"
        with tempfile.TemporaryDirectory(prefix="POSTV16_R7R6_SG7D_") as td:
            td=Path(td)
            sg7d_path=td/SG7D
            sg7d_path.write_bytes((root/SG7D).read_bytes())
            sg7d=load_module(sg7d_path,"r7r6_sg7d")

            operator=sg7d.build_subsegment_operator(
                xyz,
                ptau/float(e37a.DAY_TO_S),
                np.asarray(d["streamline_weight"],dtype=np.float64)
                *float(e37a.DAY_TO_S),
            )

            injection_pc=float(
                r2.capillary_pressure_from_incremental_sg(
                    float(r2.MAX_INCREMENTAL_CO2_SATURATION)
                )
            )
            injector_pw_pa=np.array([
                pressure[k,int(r2.INJECTOR_J),int(r2.INJECTOR_I)]
                *float(r2.PSI_TO_PA)
                for k in r2.COMPLETION_K
            ],dtype=np.float64)
            p_ref=float(np.mean(injector_pw_pa)+injection_pc)
            gate("reference_gas_pressure_finite",np.isfinite(p_ref),p_ref)

            geometry=e37a.build_control_volume_geometry(
                r2,operator,pressure,p_ref,NSL,NCV
            )
            coeff=np.asarray(geometry["cv_pressure_mass_coeff"],dtype=np.float64)
            gate("E37A_coeff_shape_exact",coeff.shape==(NSL,NCV),coeff.shape)
            gate(
                "E37A_coeff_positive_finite",
                np.isfinite(coeff).all() and np.all(coeff>0),
            )

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
            sci_gate(
                "same_B1_201_to_200_projection",
                float(np.max(closures))<=1e-12,
                float(np.max(closures)),
            )

            naive=.5*(pred201[:,:,:-1]+pred201[:,:,1:])
            sci_gate(
                "direct_saturation_averaging_not_used",
                float(np.max(np.abs(pred200-naive)))>1e-12,
                float(np.max(np.abs(pred200-naive))),
            )

            stage="frozen_halo_domain_execution"

            # =============================================================
            # Prospectively frozen R7-R7D occupancy domain:
            #
            #     D1 = S0 union H1
            #
            # S0 remains the exact SG7D transport/deposition skeleton.
            # H1 is terminal occupancy space only.
            # =============================================================

            graph=build_extended_halo_graph(
                operator
            )

            support=graph["support"]

            # -------------------------------------------------------------
            # Original S0 graph authority.
            # -------------------------------------------------------------

            gate(
                "S0_support_graph_nonempty",
                len(support["nodes"])>0
                and len(support["edge_u"])>0,
                [
                    len(support["nodes"]),
                    len(support["edge_u"]),
                ],
            )

            gate(
                "S0_support_graph_single_component",
                support["n_components"]==1,
                support["n_components"],
            )

            gate(
                "S0_support_graph_no_cross_component_edges",
                np.all(
                    support["component_labels"][
                        support["edge_u"]
                    ]
                    ==
                    support["component_labels"][
                        support["edge_v"]
                    ]
                ),
            )

            # -------------------------------------------------------------
            # Frozen D1 geometry.
            # -------------------------------------------------------------

            gate(
                "H1_nonempty",
                len(graph["h1_nodes"])>0,
                len(graph["h1_nodes"]),
            )

            gate(
                "S0_H1_disjoint",
                len(
                    np.intersect1d(
                        graph["s0_nodes"],
                        graph["h1_nodes"],
                    )
                )==0,
            )

            gate(
                "D1_exact_union_cardinality",
                len(graph["nodes"])
                ==
                len(graph["s0_nodes"])
                + len(graph["h1_nodes"]),
                [
                    len(graph["nodes"]),
                    len(graph["s0_nodes"]),
                    len(graph["h1_nodes"]),
                ],
            )

            gate(
                "D1_weak_component_count_one",
                graph["n_components"]==1,
                graph["n_components"],
            )

            hp=np.asarray(
                graph["halo_parent_pairs_flat"],
                dtype=np.int64,
            )

            gate(
                "S0_H1_face_adjacencies_nonempty",
                len(hp)>0,
                len(hp),
            )

            sf=hp[:,0]
            hf=hp[:,1]

            si=sf%NX
            sj=(sf//NX)%NY
            sk=sf//(NX*NY)

            hi=hf%NX
            hj=(hf//NX)%NY
            hk=hf//(NX*NY)

            gate(
                "H1_same_layer_only",
                np.all(
                    sk==hk
                ),
            )

            gate(
                "H1_xy_face_neighbor_only",
                np.all(
                    (
                        np.abs(si-hi)
                        + np.abs(sj-hj)
                    )
                    == 1
                ),
            )

            # -------------------------------------------------------------
            # Frozen directed graph semantics.
            # -------------------------------------------------------------

            arc_u=np.asarray(
                graph["arc_u"],
                dtype=np.int64,
            )

            arc_v=np.asarray(
                graph["arc_v"],
                dtype=np.int64,
            )

            arc_cost=np.asarray(
                graph["arc_cost"],
                dtype=np.float64,
            )

            arc_kind=np.asarray(
                graph["arc_kind"],
                dtype=np.int8,
            )

            support_arc=(
                arc_kind==0
            )

            halo_arc=(
                arc_kind==1
            )

            gate(
                "historical_S0_directed_arc_count_exact",
                int(np.sum(support_arc))
                ==
                2*len(support["edge_u"]),
                [
                    int(np.sum(support_arc)),
                    2*len(support["edge_u"]),
                ],
            )

            gate(
                "halo_entry_arcs_nonempty",
                int(np.sum(halo_arc))>0,
                int(np.sum(halo_arc)),
            )

            gate(
                "halo_entry_cost_exact_5",
                np.all(
                    arc_cost[halo_arc]
                    == HALO_ENTRY_COST
                ),
            )

            gate(
                "halo_arcs_originate_in_S0",
                np.all(
                    graph["s0_mask"][
                        arc_u[halo_arc]
                    ]
                ),
            )

            gate(
                "halo_arcs_terminate_in_H1",
                np.all(
                    graph["h1_mask"][
                        arc_v[halo_arc]
                    ]
                ),
            )

            gate(
                "H1_originating_arcs_zero",
                not np.any(
                    graph["h1_mask"][
                        arc_u
                    ]
                ),
            )

            gate(
                "H1_to_S0_reverse_arcs_zero",
                not np.any(
                    graph["h1_mask"][arc_u]
                    &
                    graph["s0_mask"][arc_v]
                ),
            )

            gate(
                "H1_to_H1_transit_arcs_zero",
                not np.any(
                    graph["h1_mask"][arc_u]
                    &
                    graph["h1_mask"][arc_v]
                ),
            )

            # -------------------------------------------------------------
            # Frozen SG7D/E37A geometry arrays.
            # -------------------------------------------------------------

            flat=np.asarray(
                geometry["flat_cell"],
                dtype=np.int64,
            )

            cv_id=np.asarray(
                geometry["cv_id"],
                dtype=np.int64,
            )

            pv=np.asarray(
                geometry["pv_m3"],
                dtype=np.float64,
            )

            pseg=np.asarray(
                geometry["pseg_psi"],
                dtype=np.float64,
            )

            gate(
                "S0_exact_unique_SG7D_crossed_cells",
                np.array_equal(
                    np.asarray(
                        graph["s0_nodes"],
                        dtype=np.int64,
                    ),
                    np.unique(flat),
                ),
            )

            # -------------------------------------------------------------
            # Frozen physical cell capacity.
            #
            # Same R2 EOS, pressure, porosity, cell volume, Sg=0.60.
            # H1 receives NO special capacity multiplier.
            # -------------------------------------------------------------

            cell_pv=DX*DY*DZ*0.20

            smax=np.full(
                GRID,
                INJECTED,
                dtype=np.float64,
            )

            rho_max=np.asarray(
                r2.gas_density_from_state(
                    smax,
                    pressure,
                    p_ref,
                ),
                dtype=np.float64,
            )

            capacity=(
                cell_pv
                * rho_max
                * MAX_SG
            )

            gate(
                "physical_cell_capacity_positive_finite",
                np.isfinite(capacity).all()
                and np.all(capacity>0),
            )

            capflat=capacity.reshape(-1)

            s0_capacity=float(
                np.sum(
                    capflat[
                        graph["s0_nodes"]
                    ]
                )
            )

            h1_capacity=float(
                np.sum(
                    capflat[
                        graph["h1_nodes"]
                    ]
                )
            )

            d1_capacity=float(
                np.sum(
                    capflat[
                        graph["nodes"]
                    ]
                )
            )

            capacity_partition_tol=max(
                1.0e-7,
                1.0e-12
                * max(
                    abs(d1_capacity),
                    1.0,
                ),
            )

            gate(
                "D1_capacity_partition_exact",
                abs(
                    d1_capacity
                    - (
                        s0_capacity
                        + h1_capacity
                    )
                )
                <= capacity_partition_tol,
                [
                    d1_capacity,
                    s0_capacity,
                    h1_capacity,
                ],
            )

            gate(
                "H1_physical_capacity_positive",
                h1_capacity>0.0,
                h1_capacity,
            )

            # -------------------------------------------------------------
            # Output arrays — unchanged grid shape.
            # -------------------------------------------------------------

            grid_sat=np.empty(
                (NT,)+GRID,
                dtype=np.float64,
            )

            grid_mass=np.empty(
                (NT,)+GRID,
                dtype=np.float64,
            )

            reconciliation_started=True

            # =============================================================
            # ALL NINE CANONICAL TIMES.
            # =============================================================

            for it,day in enumerate(DAYS):

                # ---------------------------------------------------------
                # Frozen B1 -> SG7D/E37A raw mass deposition.
                # ---------------------------------------------------------

                newf=np.asarray(
                    pred200[it],
                    dtype=np.float64,
                ).reshape(-1)

                newsub=newf[cv_id]

                newsg=np.clip(
                    newsub-BACKGROUND,
                    0.0,
                    MAX_SG,
                )

                rho_new=np.asarray(
                    r2.gas_density_from_state(
                        newsub,
                        pseg,
                        p_ref,
                    ),
                    dtype=np.float64,
                )

                sub_mass=(
                    pv
                    * rho_new
                    * newsg
                )

                raw=np.bincount(
                    flat,
                    weights=sub_mass,
                    minlength=NX*NY*NZ,
                ).reshape(GRID)

                target=float(
                    np.sum(
                        pred_mass[it]
                    )
                )

                transfer_residual=float(
                    np.sum(raw)
                    - target
                )

                transfer_tol=max(
                    1.0e-7,
                    1.0e-11
                    * max(
                        abs(target),
                        1.0,
                    ),
                )

                sci_gate(
                    f"time_{int(day)}_B1_to_subsegment_mass_closure",
                    abs(transfer_residual)
                    <= transfer_tol,
                    [
                        transfer_residual,
                        transfer_tol,
                    ],
                )

                # Raw deposition support remains EXACTLY S0.
                raw_flat=raw.reshape(-1)

                outside_s0=np.ones(
                    NX*NY*NZ,
                    dtype=bool,
                )

                outside_s0[
                    graph["s0_nodes"]
                ]=False

                sci_gate(
                    f"time_{int(day)}_raw_deposition_outside_S0_exact_zero",
                    np.array_equal(
                        raw_flat[
                            outside_s0
                        ],
                        np.zeros(
                            np.sum(outside_s0),
                            dtype=np.float64,
                        ),
                    ),
                )

                # ---------------------------------------------------------
                # Historical raw-overload audit remains unchanged.
                # ---------------------------------------------------------

                raw_excess=(
                    raw-capacity
                )

                cap_tol=max(
                    1.0e-7,
                    1.0e-11
                    * max(
                        float(
                            np.max(capacity)
                        ),
                        1.0,
                    ),
                )

                overloaded=int(
                    np.sum(
                        raw_excess
                        > cap_tol
                    )
                )

                max_raw_excess=float(
                    np.max(
                        raw_excess
                    )
                )

                if it==0:

                    sci_gate(
                        "day30_R7R1_overloaded_count_reproduced",
                        overloaded
                        == EXPECTED_DAY30_OVERLOADED,
                        overloaded,
                    )

                    sci_gate(
                        "day30_R7R1_max_excess_reproduced",
                        abs(
                            max_raw_excess
                            - EXPECTED_DAY30_MAX_EXCESS
                        )
                        <= max(
                            1.0e-6,
                            1.0e-10
                            * EXPECTED_DAY30_MAX_EXCESS,
                        ),
                        max_raw_excess,
                    )

                # =========================================================
                # R7-R7E scientific delta:
                # bounded conservative reconciliation over D1.
                # =========================================================

                reconciled,diag,compaudit=(
                    reconcile_mass_halo_strict(
                        raw,
                        capacity,
                        graph,
                    )
                )

                # ---------------------------------------------------------
                # Frozen EOS inversion — unchanged from R7-R7B.
                # ---------------------------------------------------------

                sg=np.asarray(
                    r2._invert_incremental_sg_from_mass(
                        reconciled,
                        pressure,
                        p_ref,
                        cell_pv,
                    ),
                    dtype=np.float64,
                )

                sat=(
                    BACKGROUND
                    + sg
                )

                sci_gate(
                    f"time_{int(day)}_grid_saturation_finite",
                    np.isfinite(sat).all(),
                )

                sci_gate(
                    f"time_{int(day)}_grid_saturation_bounds",
                    float(np.min(sat))
                    >= BACKGROUND-1e-12
                    and float(np.max(sat))
                    <= INJECTED+1e-12,
                    [
                        float(np.min(sat)),
                        float(np.max(sat)),
                    ],
                )

                reconstructed=float(
                    r2.stored_co2_mass_kg(
                        sat,
                        pressure,
                        p_ref,
                        cell_pv,
                    )
                )

                inv_rel=abs(
                    reconstructed
                    - float(
                        np.sum(reconciled)
                    )
                ) / max(
                    abs(
                        float(
                            np.sum(reconciled)
                        )
                    ),
                    1.0,
                )

                sci_gate(
                    f"time_{int(day)}_EOS_mass_inversion_closure",
                    inv_rel<=1.0e-10,
                    inv_rel,
                )

                # ---------------------------------------------------------
                # Everything outside prospectively frozen D1 remains exact
                # background saturation with zero component mass.
                # ---------------------------------------------------------

                d1_mask=np.zeros(
                    NX*NY*NZ,
                    dtype=bool,
                )

                d1_mask[
                    graph["nodes"]
                ]=True

                d1_mask=d1_mask.reshape(
                    GRID
                )

                sci_gate(
                    f"time_{int(day)}_outside_D1_saturation_background",
                    np.array_equal(
                        sat[~d1_mask],
                        np.full(
                            np.sum(~d1_mask),
                            BACKGROUND,
                            dtype=np.float64,
                        ),
                    ),
                )

                sci_gate(
                    f"time_{int(day)}_outside_D1_component_mass_zero",
                    np.array_equal(
                        reconciled[
                            ~d1_mask
                        ],
                        np.zeros(
                            np.sum(~d1_mask),
                            dtype=np.float64,
                        ),
                    ),
                )

                # ---------------------------------------------------------
                # H1 occupancy diagnostics.
                #
                # No early-time zero requirement is imposed.
                # ---------------------------------------------------------

                sat_flat=sat.reshape(-1)

                h1_sat=(
                    sat_flat[
                        graph["h1_nodes"]
                    ]
                )

                sci_gate(
                    f"time_{int(day)}_H1_saturation_finite",
                    np.isfinite(
                        h1_sat
                    ).all(),
                )

                sci_gate(
                    f"time_{int(day)}_H1_saturation_bounds",
                    float(
                        np.min(h1_sat)
                    )
                    >= BACKGROUND-1e-12
                    and float(
                        np.max(h1_sat)
                    )
                    <= INJECTED+1e-12,
                    [
                        float(
                            np.min(h1_sat)
                        ),
                        float(
                            np.max(h1_sat)
                        ),
                    ],
                )

                grid_sat[it]=sat
                grid_mass[it]=reconciled
                completed_times=it+1

                # ---------------------------------------------------------
                # Timewise audit.
                # ---------------------------------------------------------

                time_rows.append({
                    "target_day":
                        float(day),

                    "raw_total_component_mass_kg":
                        diag[
                            "raw_total_component_mass_kg"
                        ],

                    "raw_overloaded_cell_count":
                        diag[
                            "raw_overloaded_cell_count"
                        ],

                    "raw_max_capacity_excess_kg":
                        diag[
                            "raw_max_capacity_excess_kg"
                        ],

                    "raw_total_excess_supply_kg":
                        diag[
                            "raw_total_excess_supply_kg"
                        ],

                    "recipient_cell_count":
                        diag[
                            "recipient_cell_count"
                        ],

                    "active_component_count":
                        diag[
                            "active_component_count"
                        ],

                    "certified_primary_min_cost_total":
                        diag[
                            "certified_primary_min_cost_total"
                        ],

                    "certified_tie_primary_cost_total":
                        diag[
                            "certified_tie_primary_cost_total"
                        ],

                    "total_directed_edge_flow_kg":
                        diag[
                            "total_directed_edge_flow_kg"
                        ],

                    "maximum_directed_edge_flow_kg":
                        diag[
                            "maximum_directed_edge_flow_kg"
                        ],

                    "max_node_balance_residual_kg":
                        diag[
                            "max_node_balance_residual_kg"
                        ],

                    "max_component_mass_residual_kg":
                        diag[
                            "max_component_mass_residual_kg"
                        ],

                    "minimum_secondary_inequality_slack":
                        diag[
                            "minimum_secondary_inequality_slack"
                        ],

                    "minimum_secondary_primary_certification_margin":
                        diag[
                            "minimum_secondary_primary_certification_margin"
                        ],

                    "maximum_reported_primary_fun_minus_certified_abs":
                        diag[
                            "maximum_reported_primary_fun_minus_certified_abs"
                        ],

                    "max_capacity_excess_after_reconciliation_kg":
                        diag[
                            "max_capacity_excess_after_reconciliation_kg"
                        ],

                    "total_component_mass_relative_closure":
                        diag[
                            "total_component_mass_relative_closure"
                        ],

                    "D1_capacity_kg":
                        diag[
                            "D1_capacity_kg"
                        ],

                    "D1_capacity_fraction":
                        diag[
                            "D1_capacity_fraction"
                        ],

                    "S0_capacity_kg":
                        diag[
                            "S0_capacity_kg"
                        ],

                    "H1_capacity_kg":
                        diag[
                            "H1_capacity_kg"
                        ],

                    "S0_final_component_mass_kg":
                        diag[
                            "S0_final_component_mass_kg"
                        ],

                    "H1_final_component_mass_kg":
                        diag[
                            "H1_final_component_mass_kg"
                        ],

                    "H1_capacity_fraction_used":
                        diag[
                            "H1_capacity_fraction_used"
                        ],

                    "H1_occupied_cell_count":
                        diag[
                            "H1_occupied_cell_count"
                        ],

                    "H1_max_cell_component_mass_kg":
                        diag[
                            "H1_max_cell_component_mass_kg"
                        ],

                    "H1_fraction_of_total_component_mass":
                        diag[
                            "H1_fraction_of_total_component_mass"
                        ],

                    "H1_saturation_min":
                        float(
                            np.min(h1_sat)
                        ),

                    "H1_saturation_max":
                        float(
                            np.max(h1_sat)
                        ),

                    "grid_saturation_min":
                        float(
                            np.min(sat)
                        ),

                    "grid_saturation_max":
                        float(
                            np.max(sat)
                        ),

                    "EOS_mass_relative_closure":
                        inv_rel,
                })

                for row in compaudit:

                    component_rows.append({
                        "target_day":
                            float(day),

                        **row,
                    })

            sci_gate(
                "all_9_canonical_times",
                completed_times==NT,
                completed_times,
            )

        stage="seal_integrated_state"

        # =================================================================
        # R7-R7E integrated-state seal.
        #
        # This state explicitly distinguishes:
        #
        #   physical streamline support S0
        #   terminal occupancy halo H1
        #   admissible occupancy domain D1 = S0 union H1
        #
        # No historical result is overwritten or relabelled.
        # =================================================================

        state_name=(
            "POSTV16_AV1_D_R7_R7E_Foundation0001_"
            "Frozen_Horizontal_Face_Halo_Occupancy_Integrated_State.npz"
        )

        state_bytes=deterministic_npz_bytes({
            "target_days":
                DAYS,

            "streamline_saturation_201":
                pred201.astype(
                    np.float32
                ),

            "streamline_saturation_200":
                pred200.astype(
                    np.float32
                ),

            "streamline_component_mass_200_kg":
                pred_mass.astype(
                    np.float64
                ),

            "grid_saturation":
                grid_sat.astype(
                    np.float32
                ),

            "grid_component_mass_kg":
                grid_mass.astype(
                    np.float64
                ),

            "S0_flat_cells":
                np.asarray(
                    graph["s0_nodes"],
                    dtype=np.int64,
                ),

            "H1_flat_cells":
                np.asarray(
                    graph["h1_nodes"],
                    dtype=np.int64,
                ),

            "D1_flat_cells":
                np.asarray(
                    graph["nodes"],
                    dtype=np.int64,
                ),

            "H1_parent_pairs_flat":
                np.asarray(
                    graph["halo_parent_pairs_flat"],
                    dtype=np.int64,
                ),

            "foundation_case_sha256":
                np.array(
                    FOUNDATION_SHA
                ),

            "runtime_weights_sha256":
                np.array(
                    WEIGHTS_SHA
                ),

            "runtime_normalization_sha256":
                np.array(
                    NORM_SHA
                ),

            "physical_reconciliation_protocol_id":
                np.array(
                    PHYSICAL_PROTOCOL_ID
                ),

            "occupancy_domain_protocol_id":
                np.array(
                    R7R7D_PROTOCOL_ID
                ),

            "canonical_arithmetic_protocol_id":
                np.array(
                    NUMERICAL_PROTOCOL_ID
                ),
        })

        immutable_publish(
            out,
            {
                state_name:
                    state_bytes,
            },
        )

        state_sha=sha256_file(
            out/state_name
        )

        # All nine times exist here because reaching this point requires
        # the frozen all_9_canonical_times scientific gate to have passed.
        day365=next(
            row
            for row in time_rows
            if row["target_day"]==365.0
        )

        # =================================================================
        # PASS contract
        # =================================================================

        decision={
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "scientific_execution_pass":
                True,

            "occupancy_domain_protocol_id":
                R7R7D_PROTOCOL_ID,

            "canonical_arithmetic_protocol_id":
                NUMERICAL_PROTOCOL_ID,

            "physical_protocol_id":
                PHYSICAL_PROTOCOL_ID,

            "candidate_count":
                1,

            "all_9_canonical_times_completed":
                True,

            # -------------------------------------------------------------
            # Immutable historical results.
            # -------------------------------------------------------------

            "R7R3_immutable_result":
                "FAIL",

            "R7R6_immutable_result":
                "FAIL",

            "R7R7B_immutable_result":
                "FAIL",

            "R7R3_retested":
                False,

            "R7R6_retested":
                False,

            "R7R7B_retested":
                False,

            # -------------------------------------------------------------
            # Frozen runtime authorities.
            # -------------------------------------------------------------

            "accepted_weights_sha256":
                WEIGHTS_SHA,

            "normalization_sha256":
                NORM_SHA,

            "foundation_case_sha256":
                FOUNDATION_SHA,

            "integrated_state_sha256":
                state_sha,

            # -------------------------------------------------------------
            # Frozen R7-R7A numerics.
            # -------------------------------------------------------------

            "LP_method":
                LP_METHOD,

            "primal_feasibility_tolerance":
                PRIMAL_FEAS_TOL,

            "dual_feasibility_tolerance":
                DUAL_FEAS_TOL,

            "primary_envelope_changed":
                False,

            "constraint_scaling_applied":
                False,

            "canonical_arithmetic":
                (
                    "solver-native unscaled "
                    "secondary inequality residual"
                ),

            "independent_fsum_pass_fail_gate":
                False,

            # -------------------------------------------------------------
            # Frozen model / B1 / physics declarations.
            # -------------------------------------------------------------

            "accepted_checkpoint_modified":
                False,

            "B1_modified":
                False,

            "S0_support_graph_modified":
                False,

            "S0_primary_graph_cost_modified":
                False,

            "raw_SG7D_E37A_deposition_modified":
                False,

            "EOS_modified":
                False,

            "pressure_field_modified":
                False,

            "saturation_bounds_modified":
                False,

            # -------------------------------------------------------------
            # Prospectively frozen R7-R7D scientific delta.
            # -------------------------------------------------------------

            "occupancy_domain_extended":
                True,

            "occupancy_domain":
                (
                    "D1 = exact SG7D support S0 union frozen "
                    "single non-recursive same-layer x/y face halo H1"
                ),

            "H1_role":
                "terminal finite-volume occupancy sinks only",

            "halo_entry_cost_units":
                HALO_ENTRY_COST,

            "H1_reverse_arcs":
                False,

            "H1_to_H1_transit_arcs":
                False,

            "vertical_halo":
                False,

            "diagonal_halo":
                False,

            "second_ring_halo":
                False,

            "adaptive_domain_growth":
                False,

            "cells_outside_D1_used_as_sinks":
                False,

            "raw_deposition_outside_S0":
                False,

            # -------------------------------------------------------------
            # Explicit prohibitions preserved.
            # -------------------------------------------------------------

            "mass_clipping_or_discarding_used":
                False,

            "global_saturation_rescaling_used":
                False,

            "geology0031_used":
                False,

            "acceptance_truth_used":
                False,

            "alternate_candidate_used":
                False,

            "retuning_used":
                False,

            # -------------------------------------------------------------
            # Scientific claim boundary.
            # -------------------------------------------------------------

            "authorized_claim":
                (
                    "On frozen Foundation Case 0001, the single "
                    "prospectively frozen R7-R7D one-cell lateral "
                    "occupancy halo is sufficient for bounded conservative "
                    "end-to-end integration across all nine canonical times "
                    "while preserving the unchanged SG7D S0 transport "
                    "skeleton, accepted transport model, B1 representation "
                    "bridge, R7-R2 support-backbone costs, R7-R7A canonical "
                    "solver arithmetic, saturation bounds, and R2 EOS."
                ),

            "plume_fidelity_claim":
                False,

            "generalization_claim":
                False,

            "calibrated_dispersion_model_claim":
                False,

            "new_accuracy_claim":
                False,

            # -------------------------------------------------------------
            # Do NOT pre-name or pre-authorize the next experiment.
            # -------------------------------------------------------------

            "next":{
                "milestone":
                    None,

                "name":
                    None,

                "authorized":
                    False,

                "reason":
                    (
                        "R7-R7E outcome must first be reviewed and frozen "
                        "before any subsequent milestone is named or authorized."
                    ),
            },
        }

        # =================================================================
        # Summary
        # =================================================================

        summary={
            **decision,

            "repository_parent":
                PARENT_R7R7D_COMMIT,

            "C26_input_shape":
                [NSAMP,NN,9],

            "streamline_saturation_201_shape":
                [NT,NSL,NN],

            "streamline_saturation_200_shape":
                [NT,NSL,NCV],

            "grid_saturation_shape":
                [NT,NZ,NY,NX],

            # -------------------------------------------------------------
            # Domain geometry.
            # -------------------------------------------------------------

            "S0_cell_count":
                int(
                    len(
                        graph["s0_nodes"]
                    )
                ),

            "H1_cell_count":
                int(
                    len(
                        graph["h1_nodes"]
                    )
                ),

            "D1_cell_count":
                int(
                    len(
                        graph["nodes"]
                    )
                ),

            "S0_undirected_edge_count":
                int(
                    len(
                        graph["support"]["edge_u"]
                    )
                ),

            "S0_directed_arc_count":
                int(
                    np.sum(
                        graph["arc_kind"]==0
                    )
                ),

            "H1_entry_arc_count":
                int(
                    np.sum(
                        graph["arc_kind"]==1
                    )
                ),

            # -------------------------------------------------------------
            # Saturation ranges.
            # -------------------------------------------------------------

            "prediction_saturation_min":
                float(
                    np.min(pred201)
                ),

            "prediction_saturation_max":
                float(
                    np.max(pred201)
                ),

            "grid_saturation_min":
                float(
                    np.min(grid_sat)
                ),

            "grid_saturation_max":
                float(
                    np.max(grid_sat)
                ),

            # -------------------------------------------------------------
            # Capacity / conservation certification.
            # -------------------------------------------------------------

            "maximum_raw_overloaded_cells":
                int(
                    max(
                        row[
                            "raw_overloaded_cell_count"
                        ]
                        for row in time_rows
                    )
                ),

            "maximum_raw_capacity_excess_kg":
                float(
                    max(
                        row[
                            "raw_max_capacity_excess_kg"
                        ]
                        for row in time_rows
                    )
                ),

            "maximum_post_reconciliation_capacity_excess_kg":
                float(
                    max(
                        row[
                            "max_capacity_excess_after_reconciliation_kg"
                        ]
                        for row in time_rows
                    )
                ),

            "maximum_mass_relative_closure":
                float(
                    max(
                        row[
                            "total_component_mass_relative_closure"
                        ]
                        for row in time_rows
                    )
                ),

            "maximum_EOS_mass_relative_closure":
                float(
                    max(
                        row[
                            "EOS_mass_relative_closure"
                        ]
                        for row in time_rows
                    )
                ),

            "minimum_secondary_inequality_slack":
                float(
                    min(
                        row[
                            "minimum_secondary_inequality_slack"
                        ]
                        for row in time_rows
                    )
                ),

            "minimum_secondary_primary_certification_margin":
                float(
                    min(
                        row[
                            "minimum_secondary_primary_certification_margin"
                        ]
                        for row in time_rows
                    )
                ),

            "maximum_reported_primary_fun_minus_certified_abs":
                float(
                    max(
                        row[
                            "maximum_reported_primary_fun_minus_certified_abs"
                        ]
                        for row in time_rows
                    )
                ),

            # -------------------------------------------------------------
            # Halo utilization diagnostics.
            # -------------------------------------------------------------

            "maximum_H1_component_mass_kg":
                float(
                    max(
                        row[
                            "H1_final_component_mass_kg"
                        ]
                        for row in time_rows
                    )
                ),

            "maximum_H1_capacity_fraction_used":
                float(
                    max(
                        row[
                            "H1_capacity_fraction_used"
                        ]
                        for row in time_rows
                    )
                ),

            "maximum_H1_occupied_cell_count":
                int(
                    max(
                        row[
                            "H1_occupied_cell_count"
                        ]
                        for row in time_rows
                    )
                ),

            "day365_D1_capacity_kg":
                float(
                    day365[
                        "D1_capacity_kg"
                    ]
                ),

            "day365_S0_capacity_kg":
                float(
                    day365[
                        "S0_capacity_kg"
                    ]
                ),

            "day365_H1_capacity_kg":
                float(
                    day365[
                        "H1_capacity_kg"
                    ]
                ),

            "day365_S0_final_component_mass_kg":
                float(
                    day365[
                        "S0_final_component_mass_kg"
                    ]
                ),

            "day365_H1_final_component_mass_kg":
                float(
                    day365[
                        "H1_final_component_mass_kg"
                    ]
                ),

            "day365_H1_capacity_fraction_used":
                float(
                    day365[
                        "H1_capacity_fraction_used"
                    ]
                ),

            "day365_H1_occupied_cell_count":
                int(
                    day365[
                        "H1_occupied_cell_count"
                    ]
                ),

            "day365_H1_fraction_of_total_component_mass":
                float(
                    day365[
                        "H1_fraction_of_total_component_mass"
                    ]
                ),
        }

        # =================================================================
        # PASS artifacts.
        # =================================================================

        immutable_publish(
            out,
            {
                "PAD_Stream_POSTV16_AV1_D_R7_R7E_Summary.json":
                    json_bytes(
                        summary
                    ),

                "POSTV16_AV1_D_R7_R7E_Final_Decision.json":
                    json_bytes(
                        decision
                    ),

                "POSTV16_AV1_D_R7_R7E_Timewise_Strict_Certification_Audit.csv":
                    csv_bytes(
                        time_rows
                    ),

                "POSTV16_AV1_D_R7_R7E_Component_Strict_LP_Audit.csv":
                    csv_bytes(
                        component_rows
                    ),

                "POSTV16_AV1_D_R7_R7E_Final_Gate_Matrix.csv":
                    csv_bytes(
                        [
                            {
                                "gate":k,
                                **v,
                            }
                            for k,v
                            in gates.items()
                        ]
                    ),
            },
        )

        manifest=[]

        for p in sorted(
            out.iterdir()
        ):
            if (
                p.is_file()
                and p.name
                !=
                "POSTV16_AV1_D_R7_R7E_Artifact_Manifest.csv"
            ):
                manifest.append({
                    "file":
                        p.name,

                    "sha256":
                        sha256_file(p),

                    "bytes":
                        p.stat().st_size,
                })

        immutable_publish(
            out,
            {
                "POSTV16_AV1_D_R7_R7E_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest
                    ),
            },
        )

        # =================================================================
        # PASS terminal report.
        # =================================================================

        print(
            "\n"
            + "="*196
        )

        print(
            "POSTV16-AV1-D-R7-R7E: PASS"
        )

        print(
            "="*196
        )

        print(
            f"{'Status':116}: "
            f"{STATUS_PASS}"
        )

        print(
            f"{'Occupancy-domain protocol':116}: "
            f"{R7R7D_PROTOCOL_ID}"
        )

        print(
            f"{'Canonical arithmetic protocol':116}: "
            f"{NUMERICAL_PROTOCOL_ID}"
        )

        print(
            f"{'Physical reconciliation protocol':116}: "
            f"{PHYSICAL_PROTOCOL_ID}"
        )

        print(
            f"{'Immutable R7-R3 / R7-R6 / R7-R7B':116}: "
            "FAIL / FAIL / FAIL"
        )

        print(
            f"{'R7-R7B retested':116}: "
            "False"
        )

        print(
            f"{'Canonical times completed':116}: "
            f"{completed_times} / 9"
        )

        print(
            f"{'S0 / H1 / D1 cell counts':116}: "
            f"{len(graph['s0_nodes'])} / "
            f"{len(graph['h1_nodes'])} / "
            f"{len(graph['nodes'])}"
        )

        print(
            f"{'S0 directed arcs / H1 entry arcs':116}: "
            f"{int(np.sum(graph['arc_kind']==0))} / "
            f"{int(np.sum(graph['arc_kind']==1))}"
        )

        print(
            f"{'Halo entry cost':116}: "
            f"{HALO_ENTRY_COST}"
        )

        print(
            f"{'Day365 H1 component mass [kg]':116}: "
            f"{day365['H1_final_component_mass_kg']:.12e}"
        )

        print(
            f"{'Day365 H1 capacity [kg]':116}: "
            f"{day365['H1_capacity_kg']:.12e}"
        )

        print(
            f"{'Day365 H1 capacity fraction used':116}: "
            f"{day365['H1_capacity_fraction_used']:.12e}"
        )

        print(
            f"{'Day365 occupied H1 cells':116}: "
            f"{day365['H1_occupied_cell_count']}"
        )

        print(
            f"{'Maximum post-reconciliation capacity excess [kg]':116}: "
            f"{max(row['max_capacity_excess_after_reconciliation_kg'] for row in time_rows):.12e}"
        )

        print(
            f"{'Maximum total-mass relative closure':116}: "
            f"{max(row['total_component_mass_relative_closure'] for row in time_rows):.12e}"
        )

        print(
            f"{'Maximum EOS mass relative closure':116}: "
            f"{max(row['EOS_mass_relative_closure'] for row in time_rows):.12e}"
        )

        print(
            f"{'Minimum canonical secondary inequality residual':116}: "
            f"{min(row['minimum_secondary_inequality_slack'] for row in time_rows):.12e}"
        )

        print(
            f"{'Checkpoint / B1 / S0 graph / bounds changed':116}: "
            "False / False / False / False"
        )

        print(
            f"{'Vertical / diagonal / second ring / adaptive growth':116}: "
            "False / False / False / False"
        )

        print(
            f"{'Plume fidelity / generalization claim':116}: "
            "False / False"
        )

        print(
            f"{'Integrated state SHA256':116}: "
            f"{state_sha}"
        )

        print(
            f"{'Further milestone authorized':116}: "
            "False"
        )

        print(
            f"{'NEXT':116}: "
            "Review and freeze the R7-R7E outcome before naming "
            "any subsequent milestone"
        )

        print(
            "="*196
        )

        return 0

    # =====================================================================
    # SCIENTIFIC FAIL
    # =====================================================================

    except ScientificFail as sf:

        decision={
            "milestone":
                MILESTONE,

            "status":
                STATUS_FAIL,

            "scientific_execution_pass":
                False,

            "failed_gate":
                sf.gate,

            "failure_detail":
                sf.detail,

            "occupancy_domain_protocol_id":
                R7R7D_PROTOCOL_ID,

            "canonical_arithmetic_protocol_id":
                NUMERICAL_PROTOCOL_ID,

            "physical_protocol_id":
                PHYSICAL_PROTOCOL_ID,

            "candidate_count":
                1,

            "completed_canonical_times":
                completed_times,

            "model_inference_performed":
                inference_performed,

            "reconciliation_started":
                reconciliation_started,

            # Immutable historical results.
            "R7R3_immutable_result":
                "FAIL",

            "R7R6_immutable_result":
                "FAIL",

            "R7R7B_immutable_result":
                "FAIL",

            "R7R3_retested":
                False,

            "R7R6_retested":
                False,

            "R7R7B_retested":
                False,

            # Frozen authorities remain unchanged.
            "accepted_checkpoint_modified":
                False,

            "B1_modified":
                False,

            "S0_support_graph_modified":
                False,

            "S0_primary_graph_cost_modified":
                False,

            "raw_SG7D_E37A_deposition_modified":
                False,

            "EOS_modified":
                False,

            "saturation_bounds_modified":
                False,

            "primary_envelope_changed":
                False,

            "constraint_scaling_applied":
                False,

            "canonical_arithmetic":
                (
                    "solver-native unscaled "
                    "secondary inequality residual"
                ),

            "independent_fsum_pass_fail_gate":
                False,

            # Frozen candidate identity.
            "occupancy_domain_extended":
                True,

            "occupancy_domain":
                "D1 = S0 union frozen H1",

            "halo_entry_cost_units":
                HALO_ENTRY_COST,

            "H1_reverse_arcs":
                False,

            "H1_to_H1_transit_arcs":
                False,

            "vertical_halo":
                False,

            "diagonal_halo":
                False,

            "second_ring_halo":
                False,

            "adaptive_domain_growth":
                False,

            # Prohibitions.
            "mass_clipping_or_discarding_used":
                False,

            "global_saturation_rescaling_used":
                False,

            "geology0031_used":
                False,

            "acceptance_truth_used":
                False,

            "alternate_candidate_authorized":
                False,

            "retuning_authorized":
                False,

            "domain_growth_authorized":
                False,

            "next_milestone_authorized":
                False,

            "next_action":
                (
                    "Freeze and audit this single prospectively frozen "
                    "R7-R7D occupancy-domain candidate. Do not add a "
                    "second ring, vertical or diagonal halo, H1 reverse "
                    "or H1-to-H1 transit, alter the S0 graph or costs, "
                    "relax saturation bounds, clip or discard mass, "
                    "globally rescale saturation, change the accepted "
                    "checkpoint or B1 representation, retune the candidate, "
                    "or execute an alternate occupancy-domain candidate."
                ),
        }

        files={
            "PAD_Stream_POSTV16_AV1_D_R7_R7E_Summary.json":
                json_bytes(
                    decision
                ),

            "POSTV16_AV1_D_R7_R7E_Final_Decision.json":
                json_bytes(
                    decision
                ),

            "POSTV16_AV1_D_R7_R7E_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate":k,
                            **v,
                        }
                        for k,v
                        in gates.items()
                    ]
                ),
        }

        if time_rows:
            files[
                "POSTV16_AV1_D_R7_R7E_Timewise_Strict_Certification_Audit.csv"
            ]=csv_bytes(
                time_rows
            )

        if component_rows:
            files[
                "POSTV16_AV1_D_R7_R7E_Component_Strict_LP_Audit.csv"
            ]=csv_bytes(
                component_rows
            )

        immutable_publish(
            out,
            files,
        )

        manifest=[]

        for p in sorted(
            out.iterdir()
        ):
            if (
                p.is_file()
                and p.name
                !=
                "POSTV16_AV1_D_R7_R7E_Artifact_Manifest.csv"
            ):
                manifest.append({
                    "file":
                        p.name,

                    "sha256":
                        sha256_file(p),

                    "bytes":
                        p.stat().st_size,
                })

        immutable_publish(
            out,
            {
                "POSTV16_AV1_D_R7_R7E_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest
                    ),
            },
        )

        print(
            "\n"
            + "="*196
        )

        print(
            "POSTV16-AV1-D-R7-R7E: SCIENTIFIC FAIL"
        )

        print(
            "="*196
        )

        print(
            "Status          :",
            STATUS_FAIL,
        )

        print(
            "Failed gate     :",
            sf.gate,
        )

        print(
            "Failure detail  :",
            sf.detail,
        )

        print(
            "Completed times :",
            completed_times,
        )

        print(
            "R7-R7B remains  : FAIL; not retested"
        )

        print(
            "Candidate action: freeze/audit only; "
            "no adaptation or alternate candidate authorized"
        )

        print(
            "="*196
        )

        return 0

    # =====================================================================
    # TECHNICAL BLOCK
    # =====================================================================

    except Exception as exc:

        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report={
            "milestone":
                MILESTONE,

            "status":
                STATUS_BLOCKED,

            "failed_stage":
                stage,

            "exception":
                repr(exc),

            "gates":
                gates,

            "model_inference_performed":
                inference_performed,

            "reconciliation_started":
                reconciliation_started,

            "completed_canonical_times":
                completed_times,

            "R7R3_result_changed":
                False,

            "R7R6_result_changed":
                False,

            "R7R7B_result_changed":
                False,

            "accepted_checkpoint_modified":
                False,

            "B1_modified":
                False,

            "S0_support_graph_modified":
                False,

            "R7R7D_domain_modified":
                False,

            "canonical_arithmetic_modified":
                False,

            "saturation_bounds_modified":
                False,

            "geology0031_used":
                False,

            "acceptance_truth_used":
                False,

            "scientific_final_decision_reached":
                False,

            "next_milestone_authorized":
                False,

            "next_action":
                (
                    "Audit only this technical execution failure. "
                    "Preserve the prospectively frozen R7-R7D D1 domain, "
                    "R7-R7A canonical arithmetic, R7-R2 S0 backbone and "
                    "costs, accepted transport checkpoint, B1 representation, "
                    "EOS, and saturation bounds exactly."
                ),
        }

        data=json_bytes(
            report
        )

        p=(
            blocked
            /
            "POSTV16_AV1_D_R7_R7E_Blocked_Report.json"
        )

        if (
            p.exists()
            and p.read_bytes()!=data
        ):
            p=(
                blocked
                /
                (
                    "POSTV16_AV1_D_R7_R7E_Blocked_Report_"
                    f"{hashlib.sha256(data).hexdigest()[:12]}.json"
                )
            )

        if not p.exists():
            p.write_bytes(
                data
            )

        print(
            "\n"
            + "="*196
        )

        print(
            "POSTV16-AV1-D-R7-R7E: TECHNICALLY BLOCKED"
        )

        print(
            "="*196
        )

        print(
            "Failed stage          :",
            stage,
        )

        print(
            "Exception             :",
            repr(exc),
        )

        print(
            "Model inference run   :",
            inference_performed,
        )

        print(
            "Reconciliation started:",
            reconciliation_started,
        )

        print(
            "Completed times       :",
            completed_times,
        )

        print(
            "Report                :",
            p,
        )

        print(
            "No scientific conclusion or subsequent milestone "
            "is authorized from a technical block."
        )

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
