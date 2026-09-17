from pathlib import Path
import hashlib
import importlib.util
import json
import math
import random

import numpy as np
import torch


# =============================================================================
# PAD-Stream V16E-1B2CUDA8D-F1
#
# READ-ONLY Epoch-1 Optimization Forensic Diagnostic
#
# PURPOSE
# -------
# Diagnose the CUDA8D epoch-1 physics jump without modifying:
#   - COMP005
#   - COMP006 recovery
#   - production history
#   - production checkpoint selection
#
# The diagnostic reconstructs:
#
#   A. logical batch 1 at exact COMP005 initialization
#   B. logical batch 2 at exact COMP005 initialization
#   C. ephemeral optimizer step 1 on logical batch 1
#   D. logical batch 2 immediately after step 1
#   E. ephemeral optimizer step 2 on logical batch 2
#   F. reconstructed state vs frozen CUDA8D E0001 recovery
#
# HOLDOUT IS NEVER EVALUATED.
# NO OOD.
# NO TOF.
# NO B3.
#
# This script writes NOTHING to the production run directory.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8D-F1"
EXPERIMENT = "V16E-BLREP-COMP-CUDA-006"

REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")

CUDA8D = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8D_COMP006_Authorized_Production_Training_Runner.py"
)

CUDA6 = (
    REPO
    / "PAD_Stream_V16E1B2CUDA6_A100_COMP_CUDA_005_Authorized_Production_Runner.py"
)

DATASET = (
    DRIVE
    / "datasets"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)

RUN005 = (
    DRIVE
    / "runs"
    / "V16E-BLREP-COMP-CUDA-005"
)

COMP005 = (
    RUN005
    / "V16E_BLREP_COMP_CUDA_005.pt"
)

RECOVERY005_E0800 = (
    RUN005
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_005_RECOVERY_E0800.pt"
)

CUDA8BR_NORMALIZATION = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8BR_COMP006_REPAIR_IMPLEMENTATION_PREFLIGHT"
    / "V16E1B2CUDA8BR_COMP005_TrainingSplit_Nc_Physics_Normalization.json"
)

RUN006 = (
    DRIVE
    / "runs"
    / EXPERIMENT
)

RECOVERY_E0001 = (
    RUN006
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_006_RECOVERY_E0001.pt"
)

RECOVERY_LATEST = (
    RUN006
    / "recovery"
    / "V16E_BLREP_COMP_CUDA_006_RECOVERY_LATEST.json"
)


EXPECTED = {
    "CUDA8D":
        "be4dca13cf44a8c77caad7feae89b7e2a33e68eacbe339efdae6e951f35b05db",

    "CUDA6":
        "385e18b64ebf068a06e5daec11449e3700f69ad743627d4520905f273bf7c552",

    "dataset":
        "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c",

    "COMP005":
        "aaca2ae60d7a789bf6d3d2a177d1b3b5188181809597b1be6901ed7473e0906f",

    "RECOVERY005_E0800":
        "fbdbf6b7bff0b22625e7dbcd09500c258c6deeeec6ed4f846407f6e927435157",

    "CUDA8BR_NORMALIZATION":
        "ccd0e61fc8fc8f73890e83f537bb047aaa5f408c8f4125209cc36d0b79df3549",

    "B2S":
        "4bd70ab33dbf30ef4fd8a12037982724ea1bed6ef90684d326b3de71569e5bea",

    "BASE_M":
        "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18",

    "ETA_J":
        "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c",

    "CUDA3":
        "1065788f8f82d7f58aba873b8396cf70a17906571421315151640a0c879df886",

    "train_idx":
        "c3d1d9080af67a8ecfa018d3f757dac1fd9f19f7977f2cdf25622d613c7195b8",

    "holdout_idx":
        "4b64a27875ebe04f96d717f0e9eab43017a5325c352b5c4233284adafa308613",
}


SEED = 1337

NC_VALUES = (
    0.00,
    0.05,
    0.10,
    0.20,
    0.30,
)

NC_COUNT = len(NC_VALUES)

N_TRAIN = 11520

ADOPTED_CHUNK = 64
MICROBATCH = 1024
LOGICAL_BATCH = 8192
SECOND_LOGICAL_CHUNK = 3328

LR = 1.0e-3

LAMBDA_DATA = 1.0
LAMBDA_PHYS = 8.537526059395e-04
LAMBDA_BC = 5.0
LAMBDA_TIP = 5.0
LAMBDA_ANCHOR = 10.0
LAMBDA_MONO = 0.2


CUDA8C_PREFLIGHT_FIRST_LOGICAL = {
    "data": 4.516714716374e-05,
    "physics": 1.039421908557,
    "bc_inj": 0.0,
    "bc_tip": 0.0,
    "anchor": 1.108044284592e-05,
    "mono": 3.757063677767e-05,
    "total": 1.050894890795e-03,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def array_sha256(x) -> str:
    a = np.ascontiguousarray(
        np.asarray(x, dtype=np.int64)
    )

    return hashlib.sha256(
        a.tobytes(order="C")
    ).hexdigest()


def state_tensor_hash(state) -> str:
    h = hashlib.sha256()

    for name in sorted(state.keys()):
        t = state[name].detach().cpu().contiguous()

        h.update(name.encode("utf-8"))
        h.update(str(t.dtype).encode("utf-8"))
        h.update(str(tuple(t.shape)).encode("utf-8"))
        h.update(t.numpy().tobytes())

    return h.hexdigest()


def gate(name, condition):
    ok = bool(condition)

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8D-F1 forensic gate failed: {name}"
        )


def native_nc_mask_torch(values, nc):
    target = torch.as_tensor(
        nc,
        dtype=values.dtype,
        device=values.device,
    )

    return values == target


def finite_tensor(x):
    return bool(
        torch.isfinite(x).all().item()
    )


def model_finite(model):
    return all(
        finite_tensor(p)
        for p in model.parameters()
    )


def grad_summary(model):
    sq = 0.0
    max_abs = 0.0
    count = 0
    nonzero = 0

    for p in model.parameters():
        if p.grad is None:
            continue

        g = p.grad.detach()

        if not torch.isfinite(g).all():
            return {
                "finite": False,
                "global_norm": float("nan"),
                "max_abs": float("nan"),
                "tensor_count": count,
                "nonzero_tensor_count": nonzero,
            }

        count += 1

        if torch.any(g != 0):
            nonzero += 1

        sq += float(
            torch.sum(
                g.double() ** 2
            ).cpu().item()
        )

        max_abs = max(
            max_abs,
            float(
                torch.max(
                    torch.abs(g)
                ).cpu().item()
            ),
        )

    return {
        "finite": True,
        "global_norm": math.sqrt(sq),
        "max_abs": max_abs,
        "tensor_count": count,
        "nonzero_tensor_count": nonzero,
    }


def compare_states(a, b):
    if set(a.keys()) != set(b.keys()):
        raise RuntimeError(
            "State-dict keys differ."
        )

    max_abs = 0.0
    sum_sq = 0.0
    n = 0
    exact = True
    worst_name = None

    for name in sorted(a.keys()):
        x = a[name].detach().cpu()
        y = b[name].detach().cpu()

        if x.shape != y.shape or x.dtype != y.dtype:
            raise RuntimeError(
                f"State metadata differs for {name}."
            )

        d = (
            x.double()
            - y.double()
        )

        this_max = float(
            torch.max(
                torch.abs(d)
            ).item()
        )

        if this_max > max_abs:
            max_abs = this_max
            worst_name = name

        sum_sq += float(
            torch.sum(
                d ** 2
            ).item()
        )

        n += d.numel()

        if not torch.equal(x, y):
            exact = False

    rmse = math.sqrt(
        sum_sq / max(n, 1)
    )

    return {
        "exact": exact,
        "max_abs": max_abs,
        "rmse": rmse,
        "worst_tensor": worst_name,
    }


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8D-F1")
print("READ-ONLY Epoch-1 Optimization Forensic Diagnostic")
print("=" * 110)
print()
print("Production artifacts will not be modified.")
print("HOLDOUT EVALUATION: FORBIDDEN.")
print("No OOD.")
print("No TOF.")
print("B3 remains blocked.")
print()


# =============================================================================
# Authority
# =============================================================================

for name, path in {
    "CUDA8D": CUDA8D,
    "CUDA6": CUDA6,
    "dataset": DATASET,
    "COMP005": COMP005,
    "RECOVERY005_E0800": RECOVERY005_E0800,
    "CUDA8BR_NORMALIZATION": CUDA8BR_NORMALIZATION,
    "RECOVERY_E0001": RECOVERY_E0001,
}.items():
    gate(
        f"{name}_exists",
        path.exists(),
    )


for name, path in {
    "CUDA8D": CUDA8D,
    "CUDA6": CUDA6,
    "dataset": DATASET,
    "COMP005": COMP005,
    "RECOVERY005_E0800": RECOVERY005_E0800,
    "CUDA8BR_NORMALIZATION": CUDA8BR_NORMALIZATION,
}.items():
    gate(
        f"{name}_SHA_exact",
        sha256(path) == EXPECTED[name],
    )


# E0001 is the forensic authority even if a later recovery pointer now exists.
recovery006_path = RECOVERY_E0001

recovery006_header = torch.load(
    recovery006_path,
    map_location="cpu",
    weights_only=False,
)

gate(
    "E0001_experiment_exact",
    recovery006_header["experiment"] == EXPERIMENT,
)

gate(
    "E0001_runner_SHA_exact",
    recovery006_header["runner_sha256"] == EXPECTED["CUDA8D"],
)

gate(
    "E0001_completed_epoch_1",
    int(recovery006_header["completed_epoch"]) == 1,
)

gate(
    "E0001_optimizer_steps_2",
    int(recovery006_header["optimizer_steps_completed"]) == 2,
)

# If the latest pointer still targets E0001, verify its SHA. If production has
# advanced, report that fact but keep the forensic pinned to immutable E0001.
if RECOVERY_LATEST.exists():
    pointer = json.loads(
        RECOVERY_LATEST.read_text(encoding="utf-8")
    )

    latest_epoch = int(pointer["completed_epoch"])

    print(
        "Latest production recovery pointer epoch:",
        latest_epoch,
    )

    if latest_epoch == 1:
        gate(
            "E0001_recovery_SHA_matches_latest_pointer",
            sha256(recovery006_path) == pointer["recovery_sha256"],
        )
    else:
        print(
            "[INFO] Production pointer has advanced beyond E0001; "
            "forensic remains pinned read-only to E0001."
        )


# =============================================================================
# Runtime
# =============================================================================

gate(
    "CUDA_available",
    torch.cuda.is_available(),
)

device = torch.device("cuda")

gpu_name = torch.cuda.get_device_name(0)

gpu_total_gib = (
    torch.cuda.get_device_properties(0).total_memory
    / 1024 ** 3
)

print()
print("RUNTIME")
print("  PyTorch :", torch.__version__)
print("  GPU     :", gpu_name)
print("  Memory  :", f"{gpu_total_gib:.3f} GiB")

gate(
    "A100_runtime",
    "A100" in gpu_name,
)

gate(
    "A100_memory_at_least_70GiB",
    gpu_total_gib >= 70.0,
)

gate(
    "PyTorch_2_11_0_cu128",
    str(torch.__version__) == "2.11.0+cu128",
)

torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False


# =============================================================================
# Import frozen scientific engine
# =============================================================================

spec = importlib.util.spec_from_file_location(
    "cuda6_for_cuda8df1",
    CUDA6,
)

C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

B2S = C.import_module(
    C.B2S_SOURCE,
    "cuda8df1_B2S",
)

M = C.import_module(
    B2S.BASE_RUNNER,
    "cuda8df1_M",
)

J = C.import_module(
    B2S.B2J_SOURCE,
    "cuda8df1_J",
)

CUDA3 = C.import_module(
    C.CUDA3_SOURCE,
    "cuda8df1_CUDA3",
)


gate(
    "B2S_SHA_exact",
    sha256(Path(B2S.__file__)) == EXPECTED["B2S"],
)

gate(
    "BASE_M_SHA_exact",
    sha256(Path(M.__file__)) == EXPECTED["BASE_M"],
)

gate(
    "ETA_J_SHA_exact",
    sha256(Path(J.__file__)) == EXPECTED["ETA_J"],
)

gate(
    "CUDA3_SHA_exact",
    sha256(Path(CUDA3.__file__)) == EXPECTED["CUDA3"],
)


# =============================================================================
# Dataset and frozen split
# =============================================================================

with np.load(
    DATASET,
    allow_pickle=False,
) as d:
    xi_all = np.array(d["xi"], copy=True)
    Sw_all = np.array(d["Sw"], copy=True)
    p11_all = np.array(d["p11"], copy=True)
    ai_all = np.array(d["ai"], copy=True)
    at_all = np.array(d["at"], copy=True)


recovery005 = torch.load(
    RECOVERY005_E0800,
    map_location="cpu",
    weights_only=False,
)

train_idx = np.asarray(
    recovery005["train_idx"],
    dtype=np.int64,
)

holdout_idx = np.asarray(
    recovery005["holdout_idx"],
    dtype=np.int64,
)


gate(
    "train_idx_SHA_exact",
    array_sha256(train_idx)
    == EXPECTED["train_idx"],
)

gate(
    "holdout_idx_SHA_exact",
    array_sha256(holdout_idx)
    == EXPECTED["holdout_idx"],
)

gate(
    "train_count_11520",
    len(train_idx) == N_TRAIN,
)

# Holdout is checked only as an index authority. No holdout tensors are evaluated.


# =============================================================================
# Frozen Nc normalizers
# =============================================================================

norm_artifact = json.loads(
    CUDA8BR_NORMALIZATION.read_text(
        encoding="utf-8"
    )
)

T_INTERIOR = xi_all.shape[1] - 2

normalizer = {}
profile_counts = {}

for row in norm_artifact["Nc_strata"].values():
    nc = float(row["Nc"])
    residual_count = int(row["residual_count"])

    normalizer[nc] = float(row["residual_MSE"])
    profile_counts[nc] = (
        residual_count
        // T_INTERIOR
    )


gate(
    "five_Nc_normalizers",
    len(normalizer) == NC_COUNT,
)

gate(
    "Nc_profile_counts_cover_train",
    sum(profile_counts.values()) == N_TRAIN,
)


# =============================================================================
# Exact COMP006 lifted model / objective
# =============================================================================

BaseEtaModel = J.build_eta_model_class(M)


class COMP006LiftedModel(BaseEtaModel):

    def forward(
        self,
        xi_seq,
        p11_phys,
    ):
        S_raw = super().forward(
            xi_seq,
            p11_phys,
        )

        sor = (
            p11_phys[:, 3:4]
            .unsqueeze(1)
        )

        Sw_star = (
            p11_phys[:, 9:10]
            .unsqueeze(1)
        )

        S_inj = 1.0 - sor

        S0 = S_raw[:, 0:1, :]
        S1 = S_raw[:, -1:, :]

        return (
            S_raw

            + (1.0 - xi_seq)
            * (S_inj - S0)

            + xi_seq
            * (Sw_star - S1)
        )


def comp006_loss(
    model,
    xi,
    Sw,
    p11,
    ai,
    at,
):
    (
        S_hat,
        _unused_global_physics,
        residual,
    ) = B2S.corrected_physics_loss_training_graph(
        M,
        model,
        xi,
        p11,
    )

    Ldata = torch.mean(
        (S_hat - Sw) ** 2
    )

    profile_residual_mse = torch.mean(
        residual ** 2,
        dim=(1, 2),
    )

    nc = p11[:, 10]

    physics_weighted_sum = torch.zeros(
        (),
        device=xi.device,
        dtype=xi.dtype,
    )

    assignment_count = torch.zeros_like(
        nc,
        dtype=torch.int16,
    )

    for val in NC_VALUES:
        mask = native_nc_mask_torch(
            nc,
            val,
        )

        assignment_count = (
            assignment_count
            + mask.to(torch.int16)
        )

        if bool(torch.any(mask).item()):
            global_profile_weight = (
                float(N_TRAIN)
                /
                (
                    float(NC_COUNT)
                    * float(profile_counts[val])
                )
            )

            physics_weighted_sum = (
                physics_weighted_sum
                + global_profile_weight
                * torch.sum(
                    profile_residual_mse[mask]
                    /
                    normalizer[val]
                )
            )

    if not bool(
        torch.all(
            assignment_count == 1
        ).item()
    ):
        raise RuntimeError(
            "A profile did not map to exactly one frozen Nc stratum."
        )

    Lphys = (
        physics_weighted_sum
        /
        float(xi.shape[0])
    )

    Lbc = M.injector_bc_loss(
        S_hat,
        p11,
    )

    Ltip = M.tip_bc_loss(
        S_hat,
        p11,
    )

    Lanchor = M.anchor_loss(
        S_hat,
        ai,
        at,
    )

    dS = (
        S_hat[:, 1:, :]
        - S_hat[:, :-1, :]
    )

    Lmono = torch.mean(
        torch.relu(dS)
    )

    total = (
        LAMBDA_DATA * Ldata
        + LAMBDA_PHYS * Lphys
        + LAMBDA_BC * Lbc
        + LAMBDA_TIP * Ltip
        + LAMBDA_ANCHOR * Lanchor
        + LAMBDA_MONO * Lmono
    )

    parts = {
        "data": Ldata,
        "physics": Lphys,
        "bc_inj": Lbc,
        "bc_tip": Ltip,
        "anchor": Lanchor,
        "mono": Lmono,
        "total": total,
    }

    return (
        S_hat,
        residual,
        profile_residual_mse,
        nc,
        parts,
    )


def build_fresh():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)

    model = COMP006LiftedModel().to(device)

    ckpt005 = torch.load(
        COMP005,
        map_location="cpu",
        weights_only=False,
    )

    result = model.load_state_dict(
        ckpt005["model_state_dict"],
        strict=True,
    )

    gate(
        "fresh_model_COMP005_strict",
        len(result.missing_keys) == 0
        and len(result.unexpected_keys) == 0,
    )

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LR,
        foreach=False,
    )

    gate(
        "fresh_optimizer_has_no_state",
        len(optimizer.state) == 0,
    )

    return model, optimizer


# =============================================================================
# Exact epoch-1 logical batches
# =============================================================================

order = C.production_epoch_order(
    train_idx,
    1,
)

gate(
    "epoch1_order_count_11520",
    len(order) == N_TRAIN,
)

batch1 = order[:LOGICAL_BATCH]
batch2 = order[LOGICAL_BATCH:]

gate(
    "batch1_count_8192",
    len(batch1) == LOGICAL_BATCH,
)

gate(
    "batch2_count_3328",
    len(batch2) == SECOND_LOGICAL_CHUNK,
)


def run_logical(
    model,
    ids,
    *,
    backward,
    optimizer=None,
):
    if backward and optimizer is None:
        raise ValueError(
            "optimizer is required when backward=True"
        )

    model.train()

    if backward:
        optimizer.zero_grad(
            set_to_none=True
        )

    sums = {
        "data": 0.0,
        "physics": 0.0,
        "bc_inj": 0.0,
        "bc_tip": 0.0,
        "anchor": 0.0,
        "mono": 0.0,
        "total": 0.0,
    }

    nc_diag = {
        val: {
            "count": 0,
            "normalized_residual_sum": 0.0,
            "physics_contribution_sum": 0.0,
        }
        for val in NC_VALUES
    }

    logical_n = len(ids)

    for m0 in range(
        0,
        logical_n,
        MICROBATCH,
    ):
        mids = ids[
            m0:
            m0 + MICROBATCH
        ]

        m = len(mids)

        xi = (
            torch.from_numpy(
                xi_all[mids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        Sw = torch.from_numpy(
            Sw_all[mids]
        ).to(device)

        p11 = (
            torch.from_numpy(
                p11_all[mids]
            )
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        ai = torch.from_numpy(
            ai_all[mids]
        ).to(device)

        at = torch.from_numpy(
            at_all[mids]
        ).to(device)

        with torch.backends.cudnn.flags(
            enabled=False
        ):
            (
                S_hat,
                residual,
                profile_residual_mse,
                nc,
                parts,
            ) = comp006_loss(
                model,
                xi,
                Sw,
                p11,
                ai,
                at,
            )

        if not all(
            finite_tensor(x)
            for x in (
                S_hat,
                residual,
                *parts.values(),
            )
        ):
            raise RuntimeError(
                "Nonfinite quantity in forensic logical batch."
            )

        for key in sums:
            sums[key] += (
                float(
                    parts[key]
                    .detach()
                    .cpu()
                    .item()
                )
                * m
            )

        with torch.no_grad():
            for val in NC_VALUES:
                mask = native_nc_mask_torch(
                    nc,
                    val,
                )

                nmask = int(
                    torch.sum(mask)
                    .detach()
                    .cpu()
                    .item()
                )

                if nmask == 0:
                    continue

                normalized = (
                    profile_residual_mse[mask]
                    /
                    normalizer[val]
                )

                normalized_sum = float(
                    torch.sum(normalized)
                    .detach()
                    .cpu()
                    .item()
                )

                global_profile_weight = (
                    float(N_TRAIN)
                    /
                    (
                        float(NC_COUNT)
                        * float(profile_counts[val])
                    )
                )

                contribution_sum = (
                    global_profile_weight
                    * normalized_sum
                )

                nc_diag[val]["count"] += nmask

                nc_diag[val][
                    "normalized_residual_sum"
                ] += normalized_sum

                nc_diag[val][
                    "physics_contribution_sum"
                ] += contribution_sum

        if backward:
            scale = (
                float(m)
                /
                float(logical_n)
            )

            scaled_total = (
                parts["total"]
                * scale
            )

            with torch.backends.cudnn.flags(
                enabled=False
            ):
                scaled_total.backward()

            del scaled_total

        del (
            xi,
            Sw,
            p11,
            ai,
            at,
            S_hat,
            residual,
            profile_residual_mse,
            nc,
            parts,
        )

    result = {
        key:
            sums[key]
            / float(logical_n)
        for key in sums
    }

    result["Nc"] = {}

    for val in NC_VALUES:
        row = nc_diag[val]

        count = row["count"]

        result["Nc"][val] = {
            "count":
                count,

            "mean_normalized_residual":
                (
                    row[
                        "normalized_residual_sum"
                    ]
                    / count
                    if count > 0
                    else float("nan")
                ),

            "logical_physics_contribution":
                (
                    row[
                        "physics_contribution_sum"
                    ]
                    / float(logical_n)
                ),
        }

    result["Nc_contribution_sum"] = sum(
        result["Nc"][val][
            "logical_physics_contribution"
        ]
        for val in NC_VALUES
    )

    if backward:
        gs = grad_summary(model)

        gate(
            "ephemeral_gradients_finite",
            gs["finite"],
        )

        gate(
            "ephemeral_gradients_nonzero",
            gs["nonzero_tensor_count"] > 0,
        )

        before = {
            k: v.detach().cpu().clone()
            for k, v in model.state_dict().items()
        }

        optimizer.step()
        torch.cuda.synchronize()

        gate(
            "ephemeral_model_finite_after_step",
            model_finite(model),
        )

        after = {
            k: v.detach().cpu().clone()
            for k, v in model.state_dict().items()
        }

        update = compare_states(
            before,
            after,
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        result["gradient"] = gs
        result["update"] = update

    return result


def print_logical(title, result):
    print()
    print("-" * 110)
    print(title)
    print("-" * 110)

    for key in (
        "data",
        "physics",
        "bc_inj",
        "bc_tip",
        "anchor",
        "mono",
        "total",
    ):
        print(
            f"{key:<12}: "
            f"{result[key]:.12e}"
        )

    print()
    print("Nc-stratified corrected physics:")

    for val in NC_VALUES:
        row = result["Nc"][val]

        print(
            f"  Nc={val:>4.2f} "
            f"| n={row['count']:4d} "
            f"| mean normalized residual="
            f"{row['mean_normalized_residual']:.12e} "
            f"| logical contribution="
            f"{row['logical_physics_contribution']:.12e}"
        )

    print(
        "  contribution sum:",
        f"{result['Nc_contribution_sum']:.12e}",
    )

    if "gradient" in result:
        print()
        print(
            "Gradient global norm :",
            f"{result['gradient']['global_norm']:.12e}",
        )

        print(
            "Gradient max abs     :",
            f"{result['gradient']['max_abs']:.12e}",
        )

        print(
            "Nonzero grad tensors :",
            result["gradient"][
                "nonzero_tensor_count"
            ],
        )

        print(
            "Parameter update max :",
            f"{result['update']['max_abs']:.12e}",
        )

        print(
            "Parameter update RMSE:",
            f"{result['update']['rmse']:.12e}",
        )

        print(
            "Largest update tensor:",
            result["update"][
                "worst_tensor"
            ],
        )


# =============================================================================
# Patch exact CUDA3 higher-order derivative engine
# =============================================================================

engine = CUDA3.make_cuda3_chunked_batched_engine(
    ADOPTED_CHUNK
)

original_engine = (
    B2S.local_recurrent_derivatives_create_graph
)


try:
    B2S.local_recurrent_derivatives_create_graph = engine

    # -------------------------------------------------------------------------
    # A/B: both logical batches at exact initialization.
    # -------------------------------------------------------------------------

    model_init, _ = build_fresh()

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    batch1_init = run_logical(
        model_init,
        batch1,
        backward=False,
    )

    print_logical(
        "A. BATCH 1 AT EXACT COMP005 INITIALIZATION",
        batch1_init,
    )

    batch2_init = run_logical(
        model_init,
        batch2,
        backward=False,
    )

    print_logical(
        "B. BATCH 2 AT EXACT COMP005 INITIALIZATION",
        batch2_init,
    )

    del model_init
    torch.cuda.empty_cache()


    # -------------------------------------------------------------------------
    # C/D/E: exact ephemeral production reconstruction.
    # -------------------------------------------------------------------------

    model, optimizer = build_fresh()

    initial_state_hash = state_tensor_hash(
        model.state_dict()
    )

    print()
    print("Initial COMP005-loaded tensor SHA:")
    print(initial_state_hash)

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    batch1_step = run_logical(
        model,
        batch1,
        backward=True,
        optimizer=optimizer,
    )

    print_logical(
        "C. BATCH 1 PRE-STEP LOSS + EPHEMERAL ADAM STEP 1",
        batch1_step,
    )

    state_after_step1_hash = state_tensor_hash(
        model.state_dict()
    )

    print()
    print("State tensor SHA after ephemeral step 1:")
    print(state_after_step1_hash)

    batch2_after_step1 = run_logical(
        model,
        batch2,
        backward=False,
    )

    print_logical(
        "D. BATCH 2 IMMEDIATELY AFTER EPHEMERAL STEP 1",
        batch2_after_step1,
    )


    # Reconstruct the exact epoch-average history BEFORE step 2.
    reconstructed_epoch = {}

    for key in (
        "data",
        "physics",
        "bc_inj",
        "bc_tip",
        "anchor",
        "mono",
        "total",
    ):
        reconstructed_epoch[key] = (
            batch1_step[key]
            * len(batch1)
            +
            batch2_after_step1[key]
            * len(batch2)
        ) / float(N_TRAIN)


    # -------------------------------------------------------------------------
    # E. Step 2.
    # -------------------------------------------------------------------------

    batch2_step = run_logical(
        model,
        batch2,
        backward=True,
        optimizer=optimizer,
    )

    print_logical(
        "E. BATCH 2 PRE-STEP LOSS + EPHEMERAL ADAM STEP 2",
        batch2_step,
    )

    reconstructed_final_state = {
        k:
            v.detach().cpu().clone()
        for k, v in model.state_dict().items()
    }

    reconstructed_final_hash = state_tensor_hash(
        reconstructed_final_state
    )


finally:
    B2S.local_recurrent_derivatives_create_graph = (
        original_engine
    )


# =============================================================================
# Compare with saved E0001 authority
# =============================================================================

recovery006 = torch.load(
    recovery006_path,
    map_location="cpu",
    weights_only=False,
)

gate(
    "E0001_completed_epoch_exact",
    int(
        recovery006[
            "completed_epoch"
        ]
    ) == 1,
)

gate(
    "E0001_optimizer_steps_exact",
    int(
        recovery006[
            "optimizer_steps_completed"
        ]
    ) == 2,
)

saved_history = recovery006["history"]

print()
print("=" * 110)
print("F. RECONSTRUCTED EPOCH-1 HISTORY VS SAVED E0001")
print("=" * 110)

for key in (
    "data",
    "physics",
    "bc_inj",
    "bc_tip",
    "anchor",
    "mono",
    "total",
):
    saved = float(
        saved_history[key][0]
    )

    recon = float(
        reconstructed_epoch[key]
    )

    abs_diff = abs(
        recon - saved
    )

    rel_diff = (
        abs_diff
        / max(
            abs(saved),
            1.0e-30,
        )
    )

    print(
        f"{key:<12} "
        f"| reconstructed={recon:.12e} "
        f"| saved={saved:.12e} "
        f"| abs={abs_diff:.3e} "
        f"| rel={rel_diff:.3e}"
    )


saved_state = recovery006[
    "model_state_dict"
]

saved_state_hash = state_tensor_hash(
    saved_state
)

state_cmp = compare_states(
    reconstructed_final_state,
    saved_state,
)


print()
print("FINAL STATE COMPARISON")

print(
    "  reconstructed tensor SHA :",
    reconstructed_final_hash,
)

print(
    "  saved E0001 tensor SHA    :",
    saved_state_hash,
)

print(
    "  exact tensor equality     :",
    state_cmp["exact"],
)

print(
    "  max abs difference        :",
    f"{state_cmp['max_abs']:.12e}",
)

print(
    "  RMSE difference           :",
    f"{state_cmp['rmse']:.12e}",
)

print(
    "  worst tensor              :",
    state_cmp["worst_tensor"],
)


# =============================================================================
# CUDA8C preflight comparison
# =============================================================================

print()
print("=" * 110)
print("CUDA8C FIRST-LOGICAL-BATCH PREFLIGHT PARITY")
print("=" * 110)

for key, expected in CUDA8C_PREFLIGHT_FIRST_LOGICAL.items():
    observed = batch1_init[key]

    abs_diff = abs(
        observed - expected
    )

    rel_diff = (
        abs_diff
        / max(
            abs(expected),
            1.0e-30,
        )
    )

    print(
        f"{key:<12} "
        f"| CUDA8C={expected:.12e} "
        f"| forensic={observed:.12e} "
        f"| abs={abs_diff:.3e} "
        f"| rel={rel_diff:.3e}"
    )


# =============================================================================
# Automatic forensic classification
# =============================================================================

physics_batch1_init = batch1_init["physics"]
physics_batch2_init = batch2_init["physics"]
physics_batch2_post1 = batch2_after_step1["physics"]

composition_ratio = (
    physics_batch2_init
    / max(
        physics_batch1_init,
        1.0e-30,
    )
)

step1_amplification = (
    physics_batch2_post1
    / max(
        physics_batch2_init,
        1.0e-30,
    )
)


print()
print("=" * 110)
print("FORENSIC CLASSIFICATION")
print("=" * 110)

print(
    "Batch-2 / Batch-1 physics at initialization :",
    f"{composition_ratio:.6e}",
)

print(
    "Batch-2 post-step1 / initialization physics :",
    f"{step1_amplification:.6e}",
)


if (
    composition_ratio >= 10.0
    and step1_amplification < 10.0
):
    classification = (
        "BATCH_COMPOSITION_DOMINANT"
    )

elif (
    step1_amplification >= 10.0
    and composition_ratio < 10.0
):
    classification = (
        "FIRST_ADAM_STEP_DESTABILIZATION_DOMINANT"
    )

elif (
    composition_ratio >= 10.0
    and step1_amplification >= 10.0
):
    classification = (
        "BOTH_BATCH_COMPOSITION_AND_FIRST_STEP_DESTABILIZATION"
    )

else:
    classification = (
        "NO_ORDER_OF_MAGNITUDE_SINGLE_FACTOR_IDENTIFIED"
    )


print()
print("Classification:")
print(classification)

print()
print("READ-ONLY FORENSIC COMPLETE")
print("Production recovery was not modified.")
print("Holdout was not evaluated.")
print("No OOD.")
print("No TOF.")
print("B3 remains blocked.")
