"""
Physics-Informed Recurrent Neural Network for Buckley-Leverett Displacement
Multi-Case Training with Variable Corey Exponents and Convergence Plotting

STAGE 3: CAPILLARY PRESSURE ONLY. The governing equation gains a nonlinear
diffusion term (Brooks-Corey capillary pressure):

    dS/dt_D + dfw/dx_D = (phi / Pe_c) d/dx_D [ D_tilde(S) dS/dx_D ]

with the solver convention Pe_c = u_inj * x_ip * phi / D_ref and D_tilde
normalized to 1 at effective saturation Se = 0.5. Only Pe_c (magnitude) and
lambda_bc (shape) survive nondimensionalization beyond the rock-fluid
parameters already conditioned on; entry pressure and permeability enter
only through Pe_c (see pec_from_cap_props).

THE STRUCTURAL CHANGE: there is no shock in this stage. Capillary diffusion
replaces the discontinuity with a finite-width front, so the fan/shock/
plateau decomposition and the analytic tip anchor at Sw_star are RETIRED.
The network predicts the FULL profile Sw(x_D) on a gradient-adaptive grid
(dense at the front, sparse on the fan and plateau), and the characteristic
residual is replaced by the actual PDE residual. Every change is tagged
"# STAGE 3".

Summary of changes (searchable):
  [S3-1] Capillary physics: Brooks-Corey Pc, normalized diffusion shape
         D_tilde(S), Pe_c convention, pec_from_cap_props mapping
  [S3-2] Operator-splitting solver (upwind Godunov advection + implicit
         tridiagonal capillary diffusion), marching once with snapshots
  [S3-3] Gradient-adaptive grids (inverse-CDF sampling on |dS/dx|); the
         sequence input is x_D itself, not xi; T = 64 fixed, no padding
  [S3-4] Conditioning becomes 12-dim: xD_star becomes xD_front (a FEATURE,
         the hyperbolic front tD*slope, not a constraint) and inv_Pec
         (index 10) and lambda_bc (index 11) are appended. The sharp limit
         inv_Pec = 0 is an interior point of the conditioning space: it is
         NOT trained on (a discontinuous target would reintroduce the
         Stage 1 shock pathology), it is EVALUATED at, as an extrapolation
         test against the incompressible analytical solution
  [S3-5] tip_bc_loss at Sw_star is replaced by outlet_bc_loss against the
         truth's outlet value; anchors move to injector / mid-fan / front
         midpoint / outlet with targets from the solver
  [S3-6] physics_loss_char is replaced by pde_residual_loss: the full
         advection-diffusion residual. dS/dtD comes from central finite
         difference via TWO EXTRA FORWARD PASSES with tD (idx 7) and
         xD_front (idx 8) perturbed by the same factor (both are linear in
         t pre-breakthrough; perturbing tD alone would hand the network
         inconsistent features). Spatial derivatives are nonuniform finite
         differences along the sequence; the diffusion term is in
         conservative face form. phys_warmup_epochs is now actually used:
         the residual ramps in because a random-init network gives a
         meaningless dS/dtD estimate
  [S3-7] Dataset spans (case, Pe_c, lambda_bc); one solver march per combo
         (roughly 0.2-2 s depending on Pe_c), horizon 0.95 t_BT, max_cases
  [S3-8] Prediction/evaluation/diagnostics judge against a fine-grid
         capillary reference; the model evaluates on ANY x grid directly,
         no shock reconstruction step
  [S3-9] main: Pe_c and lambda_bc grids, sharp-limit extrapolation test,
         accuracy sweep over Pe_c, Stage 3 filenames

V2 FIXES (after the first training run; searchable "# V2"):
The first run failed with over-smeared, Pe_c-insensitive fronts. Diagnosis,
verified by evaluating the residual of the EXACT solver solution on the
training grid: the strong-form FD residual had O(1-10) truncation error at
the front at high Pe_c (mean squared residual of the TRUTH up to 14 at
Pe_c = 100), so the physics loss penalized the correct answer and the
network minimized it by smearing every front. Compounding: inv_Pec (0.01
to 0.1) was the numerically smallest feature in an unnormalized
conditioning vector containing mu_w up to 50, so it was easy to ignore,
and ignoring it was what the broken loss rewarded.
  [FIX-1] build_model normalizes the conditioning features seen by the
          LSTM (fixed scales; range_map still uses raw values). inv_Pec
          becomes O(1).
  [FIX-2] pde_residual_loss adds a distance-based exclusion zone around
          the hyperbolic front, sized to cover BOTH the physical front
          width (~8 x* / Pe_c) and the front displacement over the FD time
          interval (3 rel_dt x*), plus relative normalization so the
          residual is scale-free. The truth now scores 1e-5 to 4e-3 at all
          Pe_c (was up to 14). Physics is enforced on the fan and plateau;
          the data, shape, and anchor losses own the front.
  [FIX-3] lambda_phys default 0.05 -> 0.02. RECOMMENDED PROTOCOL: run once
          with lambda_phys = 0.0 (pure data control) to confirm the rest
          of the pipeline fits these smooth profiles (expect R2 > 0.99),
          then run with 0.02.
  [FIX-4] main reloads stage3_capillary_dataset.npz if present instead of
          rebuilding (the dataset was never the problem; save 15-45 min).

V3 FIXES (after the second training run; searchable "# V3"):
Second run: smearing and Pe_c-insensitivity resolved, but fronts are SHARP
AND MISPLACED, lagging the truth by 20-30 percent, with non-monotone fan
bulges and a ~25-epoch sawtooth in the loss curves.
  [FIX-5] Relative front coordinate as an input feature. Stages 1-2 never
          had to infer front position: the xi = x/x* coordinate built it
          in. Stage 3 dropped that and asked the LSTM to locate the front
          by comparing running x against one conditioning scalar; the v2
          results say it cannot. The model now receives (x, x - xD_front)
          so the front cue is a zero crossing. Implemented INSIDE
          build_model, so datasets, losses, and predict paths are
          unchanged and the saved npz is reused as-is.
  [FIX-6] Learning-rate step decay (halved at epochs 200 and 300) to kill
          the late-training sawtooth.
  [FIX-7] lambda_mono 0.2 -> 1.0: the v2 fan bulge is a visible
          monotonicity violation the old weight was too weak to punish.
  [FIX-9] Global mass-balance loss. The v2 diagnostics showed a NEGATIVE
          mean residual (-0.07 to -0.10): a lagging front deletes injected
          water. Front position and material balance are the same physics
          in this problem, and Stages 1-2 enforced it implicitly through
          the Welge construction. The loss matches trapz(S_pred, x) to
          trapz(S_true, x) on each sample's own grid (exact by
          construction, breakthrough-proof, no boundary-condition
          caveats), giving front misplacement a direct global gradient.
  [FIX-8] In-sample triage check after training: predict on rows stored in
          the training npz itself. If in-sample fronts are correct but
          held-out fronts lag, the problem is sampling density (raise
          max_cases or use stratified sampling); if in-sample fronts ALSO
          lag, the problem was the missing coordinate cue and [FIX-5] is
          the cure. This discriminates the two hypotheses in one run.

V4 FIXES (after the v3 run; searchable "# V4"):
The v3 in-sample triage returned front errors of +/-0.0009 on training rows
while held-out cases still lagged 0.07-0.10, with the lag proportional to
front position. Verdict: the network is partly reading front position from
the GRID GEOMETRY (training grids cluster at the true front, so spacing is
a shortcut feature), and every evaluation path used grids the network never
trained on (128 adaptive in predict_profile, 200 uniform in diagnostics).
Deeper: truth-adaptive grids are circular at deployment, since building
the grid requires the answer. Both problems have one fix: grids become a
deterministic function of quantities KNOWN at inference.
  [FIX-10] grid_from_conditioning(xD_front, inv_Pec): deterministic grid
           clustered around the ANALYTIC hyperbolic front with width set
           by Pe_c. Same function at training and inference; deployable
           with no access to the truth.
  [FIX-11] Dataset: each snapshot contributes TWO rows, one on the
           conditioning grid and one on a uniform-64 grid (anchors and
           targets resampled per grid). Mixed grids break the spacing
           shortcut and force reliance on x values and conditioning.
           DATASET MUST BE REBUILT: delete stage3_capillary_dataset.npz
           before running, or the reload guard will feed v4 the old
           truth-adaptive rows.
  [FIX-12] predict_profile, compute_residuals_over_times, and
           sharp_limit_test all evaluate on grid_from_conditioning at the
           TRAINING length (64), then interpolate for plotting/metrics.
           Train and test now speak the same grid dialect.

V5 CHANGES (polish run; searchable "# V5"):
V4 fixed generalization: R2 0.98 held-out, flat Pe_c sweep, fronts on the
line, mass balance closed, probe confirms grid-geometry invariance at the
native length. Remaining error mode is fan oscillation (+/-0.03-0.05
ringing behind the front). The PDE residual is exactly an anti-wiggle
penalty on the fan and, now that it is feasible (floor ~1e-3), it
converged to only 0.096 at weight 0.02: signal left on the table.
  [V5-1] lambda_phys 0.02 -> 0.10 (extract the remaining PDE signal)
  [V5-2] lambda_mono 1.0 -> 5.0 (wiggle up-segments are violations)
  [V5-3] epochs 400 -> 600, extra lr halving at 451 (Data and PDE were
         both still falling at 400)
  [V5-4] Interface contract documented on grid_from_conditioning: the
         surrogate is DEFINED on its native 64-node conditioning grid;
         off-length queries are out of spec (probe: -0.16/-0.25 front
         error at T=128/200 vs -0.008/-0.010 at T=64). Dense output by
         interpolation from the 64 nodes.
Watch: PDE should fall well below 0.05 toward ~1e-3; fan wiggles should
flatten; if Data RISES while PDE falls, 0.10 overshot, use 0.05.
Dataset: reloads stage3_capillary_dataset.npz unchanged. No rebuild.

V6 CHANGES (targeting the fan ringing; searchable "# V6"):
V5 halved the raw PDE loss but left the oscillations untouched, and the
reason is geometric: the wiggles sit INSIDE the residual's front-exclusion
zone (at Pe_c = 22 the zone spans ~0.20 around the front, exactly where
the ringing lives), so no lambda_phys can act on them. The fan bias and
pre-front dip are the same defect redistributed by mass conservation.
  [V6-1] Exclusion zone shrunk: rel_dt 0.02 -> 0.01 and width coefficient
         8 -> 4. Verified feasible: truth residual 3e-6 to 7e-4 on the
         reduced zone, point coverage rises to 35-77 percent, so the
         residual now reaches the former wiggle territory.
  [V6-2] Hinge curvature penalty on the masked-in region: relu(|d2S/dx2|
         - 200)^2. Measured: truth curvature peaks at |d2| ~ 156 across
         Pe_c while the v5 ringing sits near 400, so the hinge costs the
         correct answer nothing and penalizes only oscillation. Weight
         lambda_curv = 1e-6 (tuning range 5e-7 to 2e-6).
Success: wiggles visibly flatten, fan bias and pre-front dip shrink with
them, MAE holds ~0.02 or better. If v6 does not flatten the ringing, the
remaining lever is capacity (hidden 64 -> 96), and at that point weigh the
cost against sufficiency: R2 0.98 / MAE 2 percent may already meet the
CCUS bar.
  [V6-3] Two extra anchors at 0.65 and 0.85 of x_front (K = 4 -> 6),
         targets from the truth. The wiggle band was the longest
         anchor-free span, bracketed by two strongly pinned points, which
         is exactly where a flexible curve rings. Anchors are recomputed
         from the stored arrays at load time, so the old npz still works.
Dataset: reloads unchanged. No rebuild (anchors recomputed in memory).

V7 CHANGES (targeting the remaining SIGNED fan bias; searchable "# V7"):
V6 killed the ringing; what remains is a smooth signed bias concentrated
at the mu_w = 0.5 corner (Case 1 mean residual +0.012 vs Case 2 +0.002),
plus the undersampled early-time boundary layer. Signed bias is the
component that propagates into forecast uncertainty, so it is treated as
a defect, not documented behavior.
  [V7-1] Physics-informed conditioning: log10(M), M = mu_w/mu_o, appended
         as a 13th feature. Fractional flow depends on the viscosities
         ONLY through M (2.5 decades across the grid), which the network
         previously had to rediscover from two linear features. Appended
         at LOAD time from stored columns 4 and 5: existing npz upgrades
         in memory, no solver rebuild. All hardwired loss indices are
         <= 12 and untouched.
  [V7-2] Supplemental training slab: log-spaced low-M cases (mu_w in
         0.5/1/2/3.5, one training point previously) and geometric time
         sampling reaching t = 60 d (boundary-layer coverage). Built once
         to stage3_slab.npz (~10-20 min of marches), concatenated to the
         main dataset at load. Delete stage3_slab.npz to regenerate.
  [V7-3] Reserve lever, OFF by default: hidden = 96. In-sample MAE floor
         is 3-5e-3; if v7 closes the held-out gap to that floor and the
         floor itself is still above the acceptance bar, capacity is the
         binding constraint, and only then is it worth paying for.

V8 CHANGES (mask-edge kink and anchor pin-sag; searchable "# V8"):
The v7/1000-epoch run leaves two localized artifacts, each traceable to
loss geometry, not the network. Note on reading the loss plot: RAW loss
magnitudes are not comparable across components (L_curv is a squared
second derivative, naturally O(1e4+), hence its 1e-6 weight); the weighted
panel is the one that steers. There, anchor is now the LARGEST term and
curv plateaus, both diagnostic:
  [V8-1] Smooth taper mask. The binary exclusion zone switches penalties
         on like a wall at its boundary, and the optimizer concentrates
         distortion exactly there: the dip-bump at x ~ 0.4 in the Pe22
         profiles sits at the mask edge. Replaced by a sigmoid taper over
         a quarter of the zone width, applied to both the residual and
         the curvature hinge. Also relieves the standing hinge plateau
         from legitimate front-shoulder curvature at the hard edge.
  [V8-2] Anchor rebalance, lambda 10 -> 2. Weighted anchor had become the
         largest loss term: six points pinned 10x harder than their 64
         data neighbors, producing the near-contact-at-anchors,
         sag-between pattern in the fan. Anchors were a Stage 1 safeguard
         against shock-corrupted targets; with dense smooth truth they
         are a redundancy, kept at guard weight only.
  [V8-3] epochs 600 -> 1000 (empirical: the 1000-epoch run beat 600),
         extra lr halving at 701.

V9 CHANGES (injector hump; searchable "# V9"):
Diagnosis of the remaining systematic feature (the +0.01-0.03 hump at
x < 0.15): NOT the PDE loss (the truth's masked residual at the inlet is
1e-5 to 6e-4, feasible; the inlet-taper hypothesis is REJECTED) but grid
representation. The inlet boundary layer was the worst-represented region
of the whole profile (up to 0.06 Sw), so the training targets themselves
were inlet-blurred, and linear interpolation across sparse nodes on a
convex-decreasing curve sits systematically ABOVE it: the hump's location,
sign, and magnitude are all the chord-over-convex-curve artifact.
  [V9-1] Inlet-aware conditioning grid: second density bump at x = 0
         (injector boundary layer) and a front-bump width floor that
         scales down at small x* (tightens the early-time toe). Verified:
         inlet representation error improves 2-4x across the (Pe_c, t)
         range at a worst-case front cost of +0.0015.
  [V9-2] Module-level N_SEQ constant used by the builders and all predict
         paths. If the v9 hump is still visible, the next escalation is
         N_SEQ = 96, a renegotiation of the 64-node interface contract:
         one-line change plus rebuild plus retrain.
DATASET MUST BE REBUILT: the grids are baked into the arrays. Delete BOTH
stage3_capillary_dataset.npz AND stage3_slab.npz before running
(~45-60 min of marches, one time).

Author: Khalil
"""

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from dataclasses import dataclass
from typing import Dict, List, Tuple
from matplotlib import cm
import itertools
from scipy import stats
from scipy.linalg import solve_banded  # STAGE 3 [S3-2]

# ==============================================================================
# CONSTANTS
# ==============================================================================

FT3_PER_BBL = 5.615  # ft^3 per barrel (STB or rb)
EPS = 1e-12
EPS32 = 1e-8  # V6 hotfix: float32-scale epsilon used in the curvature term
DARCY_CONST = 6.328e-3  # STAGE 3 [S3-1]: mD cp psi ft day system

# ==============================================================================
# CONFIGURATION DATACLASSES
# ==============================================================================

@dataclass(frozen=True)
class RockFluid:
    nw: float = 2.0
    no: float = 2.0
    mu_w: float = 0.5
    mu_o: float = 5.0
    swc: float = 0.20
    sor: float = 0.20
    krw_max: float = 0.8
    kro_max: float = 0.8
    bw: float = 1.02
    bo: float = 1.25

    @property
    def swi(self) -> float:
        return self.swc

    @property
    def span(self) -> float:
        return 1.0 - self.swc - self.sor

    def viscosity_ratio(self) -> float:
        return self.mu_w / self.mu_o

    def validate(self) -> None:
        assert 0.0 <= self.swc < 1.0, "swc must be in [0,1)"
        assert 0.0 <= self.sor < 1.0, "sor must be in [0,1)"
        assert (self.swc + self.sor) < 1.0, "swc + sor must be < 1"
        assert self.span > EPS, "1 - swc - sor must be > 0"
        assert self.mu_w > 0 and self.mu_o > 0, "viscosities must be > 0"
        assert 0.0 < self.krw_max <= 1.0 and 0.0 < self.kro_max <= 1.0
        assert self.nw > 0 and self.no > 0, "Corey exponents must be > 0"
        assert self.bw > 0 and self.bo > 0, "FVFs must be > 0"


@dataclass(frozen=True)
class GeometryOps:
    A_ft2: float = 160_000.0
    x_ip_ft: float = 2_000.0
    phi: float = 0.20
    q_STB_per_day: float = 1_000.0
    injector_at_left: bool = True

    def C_day_inv(self) -> float:
        return (FT3_PER_BBL * self.q_STB_per_day) / (self.phi * self.A_ft2 * self.x_ip_ft)

    def tD(self, t_days: float) -> float:
        return self.C_day_inv() * t_days

    def PV_rb(self) -> float:
        return (self.phi * self.A_ft2 * self.x_ip_ft) / FT3_PER_BBL

    def PV_STB(self, bw: float = 1.02) -> float:
        return self.PV_rb() / bw

    def validate(self) -> None:
        assert self.A_ft2 > 0 and self.x_ip_ft > 0
        assert 0.0 < self.phi < 1.0
        assert self.q_STB_per_day >= 0.0


@dataclass(frozen=True)
class TrainConfig:
    lambda_data: float = 1.0
    lambda_phys: float = 0.10   # V5 [V5-1]: feasible residual, extract its signal
    lambda_bc: float = 5.0
    lambda_tip: float = 5.0        # STAGE 3 [S3-5]: now weights outlet_bc_loss
    lambda_anchor: float = 2.0  # V8 [V8-2]: guard weight; was dominating
    lambda_mono: float = 5.0    # V5 [V5-2]: penalize fan-ringing up-segments
    lambda_mass: float = 20.0   # V3 [FIX-9]: front position IS mass balance
    lambda_curv: float = 1e-6   # V6 [V6-2]: hinge curvature vs fan ringing
    lambda_shape: float = 0.5      # STAGE 3 [S3-5]: ON; it targets the front

    lr: float = 1e-3
    epochs: int = 2000          # V8 [V8-3]: empirical, 1000 beat 600
    batch_size: int = 16384
    phys_warmup_epochs: int = 100  # STAGE 3 [S3-6]: now actually used
    phys_final: float = 0.25

    hidden: int = 64
    layers: int = 2

    seed: int = 1337
    shuffle_buffer: int = 10_000

    # STAGE 3 [S3-4]: xD_star -> xD_front (feature, not constraint);
    # inv_Pec at index 10, lambda_bc at index 11. param_dim becomes 12.
    # These indices are hardwired in the losses; keep the order.
    condition_on: Tuple[str, ...] = (
        "no", "nw", "swi", "sor",
        "mu_w", "mu_o", "phi",
        "tD", "xD_front", "Sw_star",
        "inv_Pec", "lambda_bc",
    )

    def validate(self) -> None:
        for w in (self.lambda_data, self.lambda_phys, self.lambda_bc,
                  self.lambda_tip, self.lambda_anchor, self.lambda_mono,
                  self.lambda_shape):
            assert w >= 0.0
        assert self.lr > 0 and self.epochs > 0
        assert self.hidden > 0 and self.layers > 0
        assert self.phys_warmup_epochs >= 0
        assert self.phys_final >= 0.0
        assert self.batch_size > 0
        assert self.shuffle_buffer >= 0
        required = {"no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
                    "tD", "xD_front", "Sw_star", "inv_Pec", "lambda_bc"}
        assert required.issubset(set(self.condition_on))


@dataclass(frozen=True)
class ProjectParams:
    rock: RockFluid = RockFluid()
    geom: GeometryOps = GeometryOps()
    train: TrainConfig = TrainConfig()

    def validate(self) -> None:
        self.rock.validate()
        self.geom.validate()
        self.train.validate()

    def as_ml_dict(self) -> Dict[str, float]:
        return {
            "nw": self.rock.nw, "no": self.rock.no,
            "mu_w": self.rock.mu_w, "mu_o": self.rock.mu_o,
            "swc": self.rock.swc, "sor": self.rock.sor,
            "krw_max": self.rock.krw_max, "kro_max": self.rock.kro_max,
            "bw": self.rock.bw, "bo": self.rock.bo,
            "phi": self.geom.phi, "A": self.geom.A_ft2,
            "x_ip": self.geom.x_ip_ft, "i_w": self.geom.q_STB_per_day,
            "injector_at_left": self.geom.injector_at_left,
        }

    def conditioning_header(self) -> Tuple[str, ...]:
        return self.train.condition_on

    def param_dim(self) -> int:
        return len(self.train.condition_on)

    def C(self) -> float:
        return self.geom.C_day_inv()

    def PV_rb(self) -> float:
        return self.geom.PV_rb()

    def PV_STB(self) -> float:
        return self.geom.PV_STB(self.rock.bw)

    def tD(self, t_days: float) -> float:
        return self.geom.tD(t_days)


# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================

REQUIRED_KEYS = (
    "nw", "no", "mu_w", "mu_o", "swc", "sor", "krw_max", "kro_max",
    "phi", "A", "x_ip", "i_w",
)


def validate_params(p: Dict) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in p]
    if missing:
        raise KeyError(f"Missing required parameter(s): {missing}")
    assert 0.0 <= p["swc"] < 1.0
    assert 0.0 <= p["sor"] < 1.0
    assert (p["swc"] + p["sor"]) < 1.0
    assert (1.0 - p["swc"] - p["sor"]) > EPS
    assert p["mu_w"] > 0.0 and p["mu_o"] > 0.0
    assert p["nw"] > 0.0 and p["no"] > 0.0
    assert 0.0 < p["krw_max"] <= 1.0 and 0.0 < p["kro_max"] <= 1.0
    assert 0.0 < p["phi"] < 1.0
    for k in ("A", "x_ip", "i_w"):
        assert p[k] > 0.0


# ==============================================================================
# BUCKLEY-LEVERETT PHYSICS (hyperbolic core, unchanged from Stage 1)
# ==============================================================================

def calculate_relative_permeability_np(sw_local: np.ndarray, so_local: np.ndarray,
                                       p: Dict) -> tuple[np.ndarray, np.ndarray]:
    swc, sor = p['swc'], p['sor']
    nw, no = p['nw'], p['no']
    krw_max, kro_max = p['krw_max'], p['kro_max']
    denom = max(EPS, (1.0 - swc - sor))
    sw_norm = np.clip((sw_local - swc) / denom, 0.0, 1.0)
    so_norm = np.clip((so_local - sor) / denom, 0.0, 1.0)
    krw_local = krw_max * (sw_norm ** nw)
    kro_local = kro_max * (so_norm ** no)
    return krw_local, kro_local


def fractional_flow_np(Sw: np.ndarray, p: Dict, eps: float = EPS) -> np.ndarray:
    So = 1.0 - Sw
    mu_w, mu_o = p['mu_w'], p['mu_o']
    krw, kro = calculate_relative_permeability_np(Sw, So, p)
    viscosity_ratio = mu_w / mu_o
    perm_term = kro / (krw + eps)
    fw = 1.0 / (1.0 + viscosity_ratio * perm_term)
    return fw


def dfw_dsw_np(Sw: np.ndarray, p: Dict) -> tuple[np.ndarray, np.ndarray]:
    fw = fractional_flow_np(Sw, p)
    d_fw = np.gradient(fw, Sw)
    return d_fw, fw


def welge_tangent(Sw_grid: np.ndarray, fw: np.ndarray, swc: float,
                  eps: float = EPS) -> Tuple[float, float, float, int]:
    Sw = Sw_grid.astype(float)
    slopes = np.full_like(Sw, -np.inf, dtype=float)
    denom = Sw - swc
    valid = denom > 0.0
    slopes[valid] = fw[valid] / (denom[valid] + eps)
    diffs = np.diff(slopes)
    neg_idx = np.where(diffs < 0.0)[0]
    if len(neg_idx) > 0:
        tangent_idx = int(neg_idx[0])
    else:
        tangent_idx = int(np.argmax(slopes))
    Sw_star = float(Sw[tangent_idx])
    fw_star = float(fw[tangent_idx])
    slope_star = float(slopes[tangent_idx])
    return Sw_star, fw_star, slope_star, tangent_idx


def calculate_x_sw(i_w, t, phi, A, derivative):
    return ((FT3_PER_BBL * i_w * t) / (phi * A)) * derivative


def profile_at_time(t_days: float, p: Dict, Sw_grid: np.ndarray | None = None,
                    add_plateau_points: int = 12) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Incompressible analytical profile. KEPT: it is the Pe_c -> infinity
    limit and the referee for the sharp-limit extrapolation test [S3-4]."""
    validate_params(p)
    injector_at_left = bool(p.get('injector_at_left', True))
    if Sw_grid is None:
        Sw_grid = np.linspace(p['swc'], 1.0 - p['sor'], 200)
    d_fw, fw = dfw_dsw_np(Sw_grid, p)
    Sw_star, fw_star, slope_star, i_star = welge_tangent(Sw_grid, fw, p['swc'])
    x_sw = calculate_x_sw(p['i_w'], t_days, p['phi'], p['A'], d_fw)
    xD = np.clip(x_sw / p['x_ip'], 0.0, 1.0)
    start_idx = int(i_star)
    end_idx = len(Sw_grid) - 1
    front_x_D = float(xD[start_idx])
    x_left = xD[start_idx:end_idx + 1]
    S_left = Sw_grid[start_idx:end_idx + 1]
    ord_left = np.argsort(x_left)
    x_left = x_left[ord_left]
    S_left = S_left[ord_left]
    if x_left[0] > 0.0:
        x_left = np.insert(x_left, 0, 0.0)
        S_left = np.insert(S_left, 0, 1.0 - p['sor'])
    x_right = np.linspace(front_x_D, 1.0, add_plateau_points)
    S_right = np.full_like(x_right, p['swc'])
    xD_full = np.concatenate([x_left, x_right])
    Sw_full = np.concatenate([S_left, S_right])
    if not injector_at_left:
        xD_full = 1.0 - xD_full
        front_x_D = 1.0 - front_x_D
    order = np.argsort(xD_full)
    xD_full = np.clip(xD_full[order], 0.0, 1.0)
    Sw_full = Sw_full[order]
    C = (FT3_PER_BBL * p['i_w']) / (p['phi'] * p['A'] * p['x_ip'])
    t_D = C * t_days
    meta = {
        'Sw_star': float(Sw_star), 'xD_shock': float(front_x_D),
        't_days': float(t_days), 't_D': float(t_D),
    }
    return xD_full, Sw_full, meta


def breakthrough_time_days(p: Dict, Sw_grid: np.ndarray | None = None) -> float:
    validate_params(p)
    if Sw_grid is None:
        Sw_grid = np.linspace(p['swc'], 1.0 - p['sor'], 400)
    d_fw, fw = dfw_dsw_np(Sw_grid, p)
    Sw_star, fw_star, slope_star, i_star = welge_tangent(Sw_grid, fw, p['swc'])
    Sw_at_fw1 = p['swc'] + 1.0 / max(EPS, slope_star)
    Q_iBT = Sw_at_fw1 - p['swc']
    PV_rb = (p['phi'] * p['A'] * p['x_ip']) / FT3_PER_BBL
    bw = float(p.get('bw', 1.02))
    PV_STB = PV_rb / bw
    W_iBT = Q_iBT * PV_STB
    t_BT = W_iBT / p['i_w']
    return float(t_BT)


PARAM_DIM_V7 = 13  # V7 [V7-1]: 12 original features + log10(M)
N_SEQ = 64         # V9 [V9-2]: native grid length, the interface contract


def append_logM(p_arr: np.ndarray) -> np.ndarray:
    """V7 [V7-1]: append log10(mu_w / mu_o) to conditioning rows [N, 12]."""
    logM = np.log10(p_arr[:, 4:5] / np.maximum(p_arr[:, 5:6], 1e-12))
    return np.concatenate([p_arr, logM.astype(np.float32)], axis=1)


# ==============================================================================
# STAGE 3 [S3-1]: CAPILLARY DIFFUSION COEFFICIENT
# ==============================================================================
# D(S) = C_DARCY * k * (kro/mu_o) * fw(S) * (-dPc/dSw)   [ft^2/day]
# Pc(Se) = Pe_psi * Se^(-1/lambda_bc)                    (Brooks-Corey)
# Dimensionlessly only Pe_c and lambda_bc survive: entry pressure and
# permeability enter through Pe_c alone.

def d_shape_np(Sw, p: Dict, lambda_bc: float):
    """Normalized diffusion coefficient D_tilde(S), bell-shaped on
    (swc, 1-sor), equal to 1 at Se = 0.5."""
    span = max(EPS, 1.0 - p["swc"] - p["sor"])
    Se = np.clip((np.asarray(Sw, float) - p["swc"]) / span, 1e-6, 1.0 - 1e-6)

    def raw(Se_val, Sw_val):
        kro = p["kro_max"] * (1.0 - Se_val) ** p["no"]
        fw = fractional_flow_np(np.asarray(Sw_val, float), p)
        return kro * fw * Se_val ** (-1.0 / lambda_bc - 1.0)

    sw_mid = p["swc"] + 0.5 * span
    norm = raw(0.5, sw_mid)
    return raw(Se, Sw) / max(float(norm), EPS)


def pec_from_cap_props(p: Dict, Pe_psi: float, lambda_bc: float,
                       k_mD: float) -> float:
    """Map physical CapillaryProperties (Pe [psi], lambda_bc, k [mD]) to
    Pe_c = u_inj * x_ip * phi / D_ref, D_ref at S_mid (Se = 0.5)."""
    span = 1.0 - p["swc"] - p["sor"]
    sw_mid = p["swc"] + 0.5 * span
    Se = 0.5
    kro = p["kro_max"] * (1.0 - Se) ** p["no"]
    fw = float(fractional_flow_np(np.array([sw_mid]), p)[0])
    dpc_dsw = -(Pe_psi / lambda_bc) * Se ** (-1.0 / lambda_bc - 1.0) / span
    D_ref = DARCY_CONST * k_mD * (kro / p["mu_o"]) * fw * (-dpc_dsw)
    u_inj = FT3_PER_BBL * p["i_w"] / p["A"]
    return float(u_inj * p["x_ip"] * p["phi"] / max(D_ref, EPS))


# ==============================================================================
# STAGE 3 [S3-2]: CAPILLARY SOLVER (operator splitting, snapshot marching)
# ==============================================================================

def default_nx_for_pec(Pe_c: float) -> int:
    """Resolve the physical front (width ~ x*/Pe_c) with 15+ cells."""
    return int(np.clip(24 * Pe_c, 401, 2401)) | 1


def solve_capillary_snapshots(p: Dict, lambda_bc: float, Pe_c: float,
                              times_days: List[float], nx: int | None = None,
                              cfl: float = 0.4
                              ) -> Tuple[np.ndarray, List[np.ndarray]]:
    """
    March once, record profiles at each requested time (sorted).
    Advection: explicit upwind Godunov (fw monotone increasing).
    Diffusion: implicit tridiagonal solve with lagged coefficients,
    Dirichlet injector, held-value outlet row (mirrors CapillaryBLSolver).
    """
    validate_params(p)
    if nx is None:
        nx = default_nx_for_pec(Pe_c)

    L = p["x_ip"]
    xD = np.linspace(0.0, 1.0, nx)
    dx = L / (nx - 1)

    u_inj = FT3_PER_BBL * p["i_w"] / p["A"]
    D_ref = u_inj * L * p["phi"] / Pe_c  # ft^2/day, Pe_c convention

    sw_init = p["swc"] + 1e-3
    sw_inj = 1.0 - p["sor"] - 1e-3
    f_inj = fractional_flow_np(np.array([sw_inj]), p)[0]

    Sg = np.linspace(p["swc"], 1.0 - p["sor"], 400)
    dfw, _ = dfw_dsw_np(Sg, p)
    dt_cfl = cfl * p["phi"] * dx / (u_inj * np.abs(dfw).max() + EPS)

    S = np.full(nx, sw_init)
    S[0] = sw_inj
    F = np.empty(nx + 1)
    ab = np.zeros((3, nx))

    snapshots = []
    t_now = 0.0
    for t_target in sorted(float(t) for t in times_days):
        span_t = t_target - t_now
        if span_t <= 0:
            snapshots.append(S.copy())
            continue
        nt = max(1, int(np.ceil(span_t / dt_cfl)))
        dt = span_t / nt
        for _ in range(nt):
            # advection
            f = fractional_flow_np(S, p)
            F[0] = u_inj * f_inj
            F[1:nx] = u_inj * f[:-1]
            F[nx] = u_inj * f[-1]
            S[1:] -= (dt / (p["phi"] * dx)) * (F[2:] - F[1:-1])
            S[0] = sw_inj
            np.clip(S, p["swc"], 1.0 - p["sor"], out=S)

            # implicit capillary diffusion (lagged coefficients)
            D = D_ref * d_shape_np(S, p, lambda_bc)
            alpha = dt / (p["phi"] * dx**2)
            d_face = 0.5 * (D[:-1] + D[1:])

            lower = np.zeros(nx)
            diag = np.ones(nx)
            upper = np.zeros(nx)
            rhs = S.copy()
            lower[1:-1] = -alpha * d_face[:-1][: nx - 2]
            upper[1:-1] = -alpha * d_face[1:][: nx - 2]
            diag[1:-1] = 1.0 + alpha * (d_face[:-1][: nx - 2]
                                        + d_face[1:][: nx - 2])
            rhs[0] = sw_inj
            ab[0, 1:] = upper[:-1]
            ab[1, :] = diag
            ab[2, :-1] = lower[1:]
            S = solve_banded((1, 1), ab, rhs)
            np.clip(S, p["swc"], 1.0 - p["sor"], out=S)
            S[0] = sw_inj

        t_now = t_target
        snapshots.append(S.copy())

    return xD, snapshots


def front_mid_crossing(xD: np.ndarray, S: np.ndarray, Sw_star: float,
                       swc: float) -> float:
    """Numerical front locator: mid-jump crossing (robust to smearing)."""
    level = swc + 0.5 * (Sw_star - swc)
    below = np.where(S < level)[0]
    if len(below) == 0 or below[0] == 0:
        return float("nan")
    i = below[0]
    return float(np.interp(level, [S[i], S[i - 1]], [xD[i], xD[i - 1]]))


# ==============================================================================
# STAGE 3 [S3-3]: GRADIENT-ADAPTIVE GRID AND PROFILE PIPELINE
# ==============================================================================

def adaptive_grid(xD_solver: np.ndarray, Sw_solver: np.ndarray,
                  n_points: int = N_SEQ, alpha: float = 8.0) -> np.ndarray:
    """
    Inverse-CDF sampling: point density follows 1 + alpha*|dS/dx|/max|dS/dx|,
    concentrating points at the front where the physics lives. At Pe_c = 22,
    64 adaptive points represent the profile to ~0.017 max interpolation
    error versus ~0.050 for 64 uniform points. Endpoints 0 and 1 included;
    output strictly increasing.
    """
    dSdx = np.abs(np.gradient(Sw_solver, xD_solver))
    w = 1.0 + alpha * dSdx / (dSdx.max() + EPS)
    cdf = np.cumsum(w)
    cdf = (cdf - cdf[0]) / (cdf[-1] - cdf[0])
    u = np.linspace(0.0, 1.0, n_points)
    x = np.interp(u, cdf, xD_solver)
    x[0], x[-1] = 0.0, 1.0
    tiny = 1e-9 * np.arange(n_points)
    return np.maximum.accumulate(x + tiny)


def grid_from_conditioning(xD_front: float, inv_pec: float,
                           n_points: int = N_SEQ, amp: float = 6.0) -> np.ndarray:
    """
    V4 [FIX-10]: deterministic evaluation/training grid built ONLY from
    quantities known at inference: the analytic hyperbolic front and Pe_c.
    Gaussian density bump centered at xD_front with width covering the
    physical front (~5 x* / Pe_c) plus the capillary front offset (the true
    front runs slightly ahead of the hyperbolic one), inverse-CDF sampled.

    V5 [V5-4] INTERFACE CONTRACT: the trained surrogate is defined on this
    grid at n_points = 64. Grid-geometry invariance holds at that length
    (probe: conditioning/uniform/adaptive-64 all within ~0.02 front error)
    but NOT across lengths (T = 128/200 gave -0.16/-0.25). Query at 64
    nodes and interpolate for dense output; do not change n_points at
    inference without retraining.
    """
    xf = float(np.clip(xD_front, 0.0, 1.0))
    # V9 [V9-1]: front-bump width floor scales down at small x* (tighter
    # early-time toe), and a second density bump at x = 0 resolves the
    # injector boundary layer, previously the worst-represented region of
    # the profile (the source of the systematic inlet hump). Front-cell
    # interpolation floor at Pe_c = 100 remains ~0.05-0.07 in a one-cell
    # zone; judge runs on MAE and front error, not max error.
    w = 5.0 * max(xf, 1e-3) * max(inv_pec, 0.0) \
        + float(np.clip(0.1 * xf, 0.015, 0.05))
    x = np.linspace(0.0, 1.0, 4001)
    dens = (1.0 + amp * np.exp(-0.5 * ((x - xf) / w) ** 2)
            + 4.0 * np.exp(-0.5 * (x / 0.04) ** 2))
    cdf = np.cumsum(dens)
    cdf = (cdf - cdf[0]) / (cdf[-1] - cdf[0])
    u = np.linspace(0.0, 1.0, n_points)
    g = np.interp(u, cdf, x)
    g[0], g[-1] = 0.0, 1.0
    tiny = 1e-9 * np.arange(n_points)
    return np.maximum.accumulate(g + tiny)


def build_capillary_profiles(times_days: List[float], p: Dict,
                             Pe_c: float, lambda_bc: float,
                             n_seq: int = N_SEQ, alpha: float = 8.0,
                             nx: int | None = None) -> List[Dict]:
    """
    STAGE 3 [S3-3]: replaces build_fan_profiles. One solver march per call,
    snapshotting all requested times. Each snapshot is resampled onto its
    own gradient-adaptive grid. The conditioning feature xD_front is the
    HYPERBOLIC front min(1, tD * slope_star): analytic, and exactly linear
    in t pre-breakthrough, which the FD-in-time physics loss relies on.
    """
    grid = np.linspace(p["swc"], 1.0 - p["sor"], 800)
    _, fw = dfw_dsw_np(grid, p)
    Sw_star, _, slope_star, _ = welge_tangent(grid, fw, p["swc"])

    C = (FT3_PER_BBL * p["i_w"]) / (p["phi"] * p["A"] * p["x_ip"])
    xD_sol, snaps = solve_capillary_snapshots(p, lambda_bc, Pe_c,
                                              times_days, nx=nx)

    out = []
    for t, S_sol in zip(sorted(float(t) for t in times_days), snaps):
        t_D = C * t
        xD_front = float(min(1.0, t_D * slope_star))
        # V4 [FIX-11]: two rows per snapshot, conditioning grid + uniform.
        # Mixed grid geometries break the "front is where the spacing
        # shrinks" shortcut the v3 triage exposed.
        grids = [
            ("conditioning", grid_from_conditioning(xD_front, 1.0 / Pe_c,
                                                    n_points=n_seq)),
            ("uniform", np.linspace(0.0, 1.0, n_seq)),
        ]
        for grid_source, x_seq in grids:
            S_seq = np.interp(x_seq, xD_sol, S_sol)
            out.append({
                "t_days": float(t), "t_D": float(t_D),
                "x_seq": x_seq.astype(np.float32),
                "Sw_true": S_seq.astype(np.float32),
                "xD_front": xD_front,
                "xD_front_num": front_mid_crossing(xD_sol, S_sol, Sw_star,
                                                   p["swc"]),
                "Sw_star": float(Sw_star),
                "inv_Pec": float(1.0 / Pe_c), "lambda_bc": float(lambda_bc),
                "grid_source": grid_source,
            })
    return out


# ==============================================================================
# NEURAL NETWORK MODEL
# ==============================================================================

def build_model(input_features: int = 1, param_dim: int = 13,  # V7 [V7-1]
                hidden: int = 64, layers: int = 2) -> tf.keras.Model:
    x_in = tf.keras.Input(shape=(None, input_features), name="xD_seq")  # STAGE 3
    p_in = tf.keras.Input(shape=(param_dim,), name="p_vec")

    def repeat_params(args):
        x, p = args
        T = tf.shape(x)[1]
        p = tf.expand_dims(p, 1)
        return tf.tile(p, [1, T, 1])

    p_rep = tf.keras.layers.Lambda(repeat_params, name="repeat_params")([x_in, p_in])

    # V2 [FIX-1]: normalize the conditioning features the LSTM sees.
    # Scales chosen so each feature is O(1) over the training ranges;
    # inv_Pec (raw 0.01-0.1) was invisible next to mu_w (up to 50).
    # range_map below still receives RAW p_rep (it needs true swc/sor).
    feature_scale = tf.constant(
        [[[4.0, 4.0, 0.3, 0.4, 50.0, 1.0, 0.3,
           0.5, 1.0, 0.8, 0.05, 3.0, 2.0]]], dtype=tf.float32)  # V7: +logM

    def normalize_params(p):
        return p / feature_scale

    p_norm = tf.keras.layers.Lambda(normalize_params,
                                    name="normalize_params")(p_rep)

    # V3 [FIX-5]: relative front coordinate (x - xD_front) as a second
    # sequence feature. The front cue becomes a zero crossing instead of a
    # comparison the LSTM has to synthesize from a conditioning scalar.
    # Built inside the model: datasets, losses, and predict paths unchanged.
    def add_relative_coordinate(args):
        x, p_raw = args
        xf = p_raw[:, :, 8:9]
        return tf.concat([x, x - xf], axis=-1)

    x_feat = tf.keras.layers.Lambda(add_relative_coordinate,
                                    name="relative_coordinate")([x_in, p_rep])
    z = tf.keras.layers.Concatenate(axis=-1, name="concat_features")([x_feat, p_norm])

    y = z
    for i in range(layers):
        y = tf.keras.layers.LSTM(hidden, return_sequences=True,
                                  activation="tanh", name=f"lstm_{i+1}")(y)

    z_out = tf.keras.layers.TimeDistributed(
        tf.keras.layers.Dense(1), name="pre_activation")(y)

    def range_map(args):
        z_raw, p = args
        swc = p[:, :, 2:3]
        sor = p[:, :, 3:4]
        span = tf.maximum(1e-8, 1.0 - swc - sor)
        return swc + span * tf.math.sigmoid(z_raw)

    Sw_pred = tf.keras.layers.Lambda(range_map, name="range_map")([z_out, p_rep])
    return tf.keras.Model(inputs=[x_in, p_in], outputs=Sw_pred,
                          name="PI_RNN_FULLPROFILE")  # STAGE 3 [S3-3]


def fractional_flow_tf_param(S: tf.Tensor, p_vec: tf.Tensor,
                              params_fixed: Dict, eps: float = 1e-12) -> tf.Tensor:
    S = tf.convert_to_tensor(S, dtype=tf.float32)
    p_vec = tf.convert_to_tensor(p_vec, dtype=tf.float32)
    dtype = S.dtype

    krw_mx = tf.cast(params_fixed['krw_max'], dtype)
    kro_mx = tf.cast(params_fixed['kro_max'], dtype)
    eps_t = tf.cast(eps, dtype)

    def _expand(idx: int) -> tf.Tensor:
        v = p_vec[:, idx:idx+1]
        return v[:, tf.newaxis, :]

    no = _expand(0)
    nw = _expand(1)
    swc = _expand(2)
    sor = _expand(3)
    mu_w = _expand(4)
    mu_o = _expand(5)

    denom = tf.maximum(1e-8, 1.0 - swc - sor)
    Se = tf.clip_by_value((S - swc) / denom, 0.0, 1.0)

    krw = krw_mx * tf.pow(Se, nw)
    kro = kro_mx * tf.pow(1.0 - Se, no)

    M = mu_w / mu_o
    fw = 1.0 / (1.0 + M * (kro / (krw + eps_t)))
    return fw


def d_shape_tf(S: tf.Tensor, p_vec: tf.Tensor, params_fixed: Dict) -> tf.Tensor:
    """STAGE 3 [S3-6]: normalized Brooks-Corey diffusion coefficient in TF,
    D_tilde(Se = 0.5) = 1, differentiable in S. Mirrors d_shape_np."""
    no = p_vec[:, 0:1][:, tf.newaxis, :]
    swc = p_vec[:, 2:3][:, tf.newaxis, :]
    sor = p_vec[:, 3:4][:, tf.newaxis, :]
    lam = p_vec[:, 11:12][:, tf.newaxis, :]
    kro_mx = tf.cast(params_fixed["kro_max"], tf.float32)

    span = tf.maximum(1e-8, 1.0 - swc - sor)
    Se = tf.clip_by_value((S - swc) / span, 1e-6, 1.0 - 1e-6)

    expo = -1.0 / tf.maximum(lam, 1e-3) - 1.0
    kro = kro_mx * tf.pow(1.0 - Se, no)
    shape = kro * fractional_flow_tf_param(S, p_vec, params_fixed) \
        * tf.pow(Se, expo)

    sw_mid = swc + 0.5 * span
    kro_mid = kro_mx * tf.pow(tf.constant(0.5), no)
    norm = kro_mid * fractional_flow_tf_param(sw_mid, p_vec, params_fixed) \
        * tf.pow(tf.constant(0.5), expo)
    return shape / tf.maximum(norm, 1e-12)


# ==============================================================================
# STAGE 3 [S3-5]: ANCHOR GENERATION (injector / mid-fan / front-mid / outlet)
# ==============================================================================

def make_anchors_from_truth(x_seq: np.ndarray, Sw_true: np.ndarray,
                            swc: float, sor: float, Sw_star: float) -> tuple:
    """Replaces make_fan_anchors_from_truth. There is no shock tip: the
    front anchor is the mid-jump point, targets come from the solver."""
    S_mid = swc + 0.5 * (Sw_star - swc)
    i_front = int(np.argmin(np.abs(Sw_true - S_mid)))
    x_front = x_seq[i_front]
    xf = max(x_front, 1e-6)
    i_fan = int(np.argmin(np.abs(x_seq - 0.4 * xf)))
    # V6 [V6-3]: pin the former anchor desert where the ringing lives
    i_65 = int(np.argmin(np.abs(x_seq - 0.65 * xf)))
    i_85 = int(np.argmin(np.abs(x_seq - 0.85 * xf)))

    idxs = [0, i_fan, i_65, i_85, i_front, len(x_seq) - 1]
    targs = [1.0 - sor, float(Sw_true[i_fan]), float(Sw_true[i_65]),
             float(Sw_true[i_85]), float(Sw_true[i_front]),
             float(Sw_true[-1])]

    uniq, idxs_out, targs_out = set(), [], []
    for ix, tv in sorted(zip(idxs, targs)):
        if ix not in uniq:
            uniq.add(ix)
            idxs_out.append(int(ix))
            targs_out.append(float(tv))
    while len(idxs_out) < 6:
        idxs_out.append(idxs_out[-1])
        targs_out.append(targs_out[-1])
    return np.array(idxs_out, np.int32), np.array(targs_out, np.float32)


# ==============================================================================
# LOSS FUNCTIONS
# ==============================================================================

@tf.function
def data_loss(S_pred: tf.Tensor, S_true: tf.Tensor) -> tf.Tensor:
    return tf.reduce_mean(tf.square(S_pred - S_true))


@tf.function
def injector_bc_loss(S_pred: tf.Tensor, p_vec: tf.Tensor) -> tf.Tensor:
    sor = p_vec[:, 3:4]
    S_left = S_pred[:, 0, 0:1]
    target_left = 1.0 - sor
    return tf.reduce_mean(tf.square(S_left - target_left))


@tf.function
def outlet_bc_loss(S_pred: tf.Tensor, S_true: tf.Tensor) -> tf.Tensor:
    """STAGE 3 [S3-5]: replaces tip_bc_loss. There is no shock tip to pin at
    Sw_star; the last sequence point is the OUTLET, matched to the truth's
    outlet value (swc pre-breakthrough, whatever the solver says near it)."""
    return tf.reduce_mean(tf.square(S_pred[:, -1, 0:1] - S_true[:, -1, 0:1]))


def pde_residual_loss(model: tf.keras.Model, x_seq: tf.Tensor,
                      p_vec: tf.Tensor, params_fixed: dict,
                      rel_dt: float = 0.01):  # V6 [V6-1]
    """
    STAGE 3 [S3-6]: replaces physics_loss_char. Mean squared residual of

        dS/dtD + dfw/dxD - (phi / Pe_c) d/dxD [ D_tilde(S) dS/dxD ]

    on interior sequence points. dS/dtD by central FD: two extra forward
    passes with tD (idx 7) and xD_front (idx 8) scaled by the same factor
    (both linear in t pre-breakthrough). Spatial derivatives by nonuniform
    finite differences; diffusion in conservative face form. Returns
    (loss, S_pred at tD) so the training loop makes ONE nominal pass.
    Not @tf.function-wrapped: it calls the model three times.
    """
    P = p_vec.shape[-1]
    mask = tf.scatter_nd([[7], [8]], [1.0, 1.0], [P])[tf.newaxis, :]

    S0 = model([x_seq, p_vec], training=True)
    Sp = model([x_seq, p_vec * (1.0 + rel_dt * mask)], training=True)
    Sm = model([x_seq, p_vec * (1.0 - rel_dt * mask)], training=True)

    tD = p_vec[:, 7:8][:, tf.newaxis, :]
    dtD = tf.maximum(rel_dt * tD, 1e-6)
    S_t = (Sp - Sm) / (2.0 * dtD)

    F = fractional_flow_tf_param(S0, p_vec, params_fixed)
    x_c = x_seq[:, 2:, :] - x_seq[:, :-2, :]
    F_x = (F[:, 2:, :] - F[:, :-2, :]) / (x_c + 1e-8)

    h = x_seq[:, 1:, :] - x_seq[:, :-1, :]
    Dm = d_shape_tf(S0, p_vec, params_fixed)
    D_face = 0.5 * (Dm[:, 1:, :] + Dm[:, :-1, :])
    G = D_face * (S0[:, 1:, :] - S0[:, :-1, :]) / (h + 1e-8)
    div = (G[:, 1:, :] - G[:, :-1, :]) / (0.5 * x_c + 1e-8)

    phi = p_vec[:, 6:7][:, tf.newaxis, :]
    inv_pec = p_vec[:, 10:11][:, tf.newaxis, :]
    diff_term = phi * inv_pec * div

    res = S_t[:, 1:-1, :] + F_x - diff_term

    # V2 [FIX-2a]: distance-based exclusion zone around the front. The FD
    # residual has O(1) truncation error where the profile is unresolved,
    # so the TRUE solution scored up to ~14 there at Pe_c = 100 and the
    # network smeared every front to lower an unsatisfiable loss. The zone
    # covers the physical front width (~8 x*/Pe_c) AND the front's
    # displacement over the FD time interval (3 rel_dt x*); a gradient
    # threshold alone misses the latter. Physics acts on fan and plateau;
    # data, shape, and anchor losses own the front.
    xD_front = p_vec[:, 8:9][:, tf.newaxis, :]
    w_excl = xD_front * (3.0 * rel_dt) + 4.0 * xD_front * inv_pec  # V6 [V6-1]
    dist = tf.abs(x_seq[:, 1:-1, :] - xD_front)
    # V8 [V8-1]: sigmoid taper over ~a quarter of the zone width instead of
    # a hard cut; a discontinuous penalty concentrates model distortion at
    # its boundary (the x ~ 0.4 kink), a smooth one does not.
    edge = 0.25 * w_excl + 1e-4
    mask = tf.sigmoid((dist - w_excl) / edge)

    # V2 [FIX-2b]: relative normalization makes the residual scale-free,
    # so high-Pe_c samples cannot dominate the batch mean.
    scale = tf.abs(S_t[:, 1:-1, :]) + tf.abs(F_x) + tf.abs(diff_term) + 0.1
    r = res / scale

    loss = tf.reduce_sum(mask * tf.square(r)) / (tf.reduce_sum(mask) + 1e-8)

    # V6 [V6-2]: hinge curvature on the masked-in region. Plain second
    # derivative of S (not the D-weighted diffusion term): ringing carries
    # |d2| ~ 400, the truth peaks at ~156, hinge at 200 separates them.
    d2 = (( S0[:, 2:, :] - S0[:, 1:-1, :]) / (h[:, 1:, :] + EPS32)
          - (S0[:, 1:-1, :] - S0[:, :-2, :]) / (h[:, :-1, :] + EPS32)) \
        / (0.5 * x_c + EPS32)
    excess = tf.nn.relu(tf.abs(d2) - 200.0)
    curv = tf.reduce_sum(mask * tf.square(excess)) \
        / (tf.reduce_sum(mask) + 1e-8)
    return loss, curv, S0


@tf.function
def shape_loss(S_pred: tf.Tensor, S_true: tf.Tensor) -> tf.Tensor:
    grad = tf.abs(S_true[:, 1:, :] - S_true[:, :-1, :])
    grad = tf.pad(grad, [[0, 0], [0, 1], [0, 0]])
    w = 1.0 + 10.0 * grad / (tf.reduce_max(grad) + 1e-12)
    return tf.reduce_mean(w * tf.square(S_pred - S_true))


@tf.function
def monotonicity_loss(S_pred: tf.Tensor) -> tf.Tensor:
    dS = S_pred[:, 1:, :] - S_pred[:, :-1, :]
    viol = tf.nn.relu(dS)
    return tf.reduce_mean(tf.square(viol))


@tf.function
def mass_balance_loss(S_pred: tf.Tensor, S_true: tf.Tensor,
                      x_seq: tf.Tensor) -> tf.Tensor:
    """V3 [FIX-9]: nonuniform trapezoid integral of predicted vs true
    saturation over each sample's own grid. A misplaced front shows up as
    an integral mismatch of roughly (fan-plateau jump) x (misplacement),
    so this is the direct global penalty on front position."""
    h = x_seq[:, 1:, :] - x_seq[:, :-1, :]
    I_pred = tf.reduce_sum(0.5 * (S_pred[:, 1:, :] + S_pred[:, :-1, :]) * h,
                           axis=1)
    I_true = tf.reduce_sum(0.5 * (S_true[:, 1:, :] + S_true[:, :-1, :]) * h,
                           axis=1)
    return tf.reduce_mean(tf.square(I_pred - I_true))


@tf.function
def anchor_loss(S_pred: tf.Tensor, idxs_tf: tf.Tensor, targs_tf: tf.Tensor) -> tf.Tensor:
    S_pred = tf.convert_to_tensor(S_pred, dtype=tf.float32)
    idxs_tf = tf.cast(idxs_tf, tf.int32)
    targs_tf = tf.convert_to_tensor(targs_tf, dtype=tf.float32)
    S = S_pred[..., 0]
    B = tf.shape(S)[0]
    K = tf.shape(idxs_tf)[1]
    batch_ids = tf.reshape(tf.range(B), (B, 1))
    batch_ids = tf.tile(batch_ids, [1, K])
    idx = tf.stack([batch_ids, idxs_tf], axis=-1)
    S_sel = tf.gather_nd(S, idx)
    return tf.reduce_mean(tf.square(S_sel - targs_tf))


# ==============================================================================
# PARAMETER GRID GENERATION (WITH VARIABLE COREY EXPONENTS)
# ==============================================================================

def generate_param_grid(
    base_p: Dict,
    no_vals: np.ndarray | None = None,
    nw_vals: np.ndarray | None = None,
    sor_vals: np.ndarray | None = None,
    swc_vals: np.ndarray | None = None,
    mu_o_vals: np.ndarray | None = None,
    mu_w_vals: np.ndarray | None = None,
    phi_vals: np.ndarray | None = None,
) -> List[Dict]:
    if no_vals is None:
        no_vals = np.arange(2.0, 4.0 + 1e-9, 1.0, dtype=np.float32)
    if nw_vals is None:
        nw_vals = np.arange(2.0, 4.0 + 1e-9, 1.0, dtype=np.float32)
    if sor_vals is None:
        sor_vals = np.arange(0.10, 0.40 + 1e-9, 0.10, dtype=np.float32)
    if swc_vals is None:
        swc_vals = np.arange(0.10, 0.30 + 1e-9, 0.10, dtype=np.float32)
    if mu_o_vals is None:
        mu_o_vals = np.arange(0.3, 1.0 + 1e-9, 0.1, dtype=np.float32)
    if mu_w_vals is None:
        mu_w_vals = np.arange(0.5, 50.0 + 1e-9, 5.5, dtype=np.float32)
    if phi_vals is None:
        phi_vals = np.arange(0.10, 0.30 + 1e-9, 0.10, dtype=np.float32)

    param_grid = []
    for no, nw, swc, sor, mu_w, mu_o, phi in itertools.product(
        no_vals, nw_vals, swc_vals, sor_vals, mu_w_vals, mu_o_vals, phi_vals
    ):
        p = dict(base_p)
        p["no"] = float(no)
        p["nw"] = float(nw)
        p["swc"] = float(swc)
        p["sor"] = float(sor)
        p["mu_w"] = float(mu_w)
        p["mu_o"] = float(mu_o)
        p["phi"] = float(phi)
        try:
            validate_params(p)
        except AssertionError:
            continue
        param_grid.append(p)

    print(f"Generated {len(param_grid)} valid parameter combinations.")
    return param_grid


def build_multi_case_arrays(
    param_list: List[Dict],
    pec_vals: np.ndarray,
    lambda_vals: np.ndarray,
    num_times: int = 6,
    t_min_days: float = 100.0,
    n_seq: int = N_SEQ,
    alpha: float = 8.0,
    max_cases: int | None = 2_400,
    seed: int = 1337,
    verbose_every: int = 200,
) -> tuple:
    """
    STAGE 3 [S3-7]: replaces build_multi_case_fan_arrays. Loops over
    (case, Pe_c, lambda_bc) combos, one solver march per combo snapshotting
    all times, gradient-adaptive resample per snapshot. Sequences are all
    length n_seq: no padding. Cost: ~0.2 s per combo at Pe_c <= 50, a few
    seconds at Pe_c = 100 (nx scales with Pe_c). Budget max_cases
    accordingly; the arrays should be saved with np.savez and reloaded.
    """
    rng = np.random.default_rng(seed)
    combos = [(p, float(pe), float(lb)) for p in param_list
              for pe in pec_vals for lb in lambda_vals]
    if max_cases is not None and len(combos) > max_cases:
        pick = rng.choice(len(combos), size=max_cases, replace=False)
        combos = [combos[i] for i in pick]

    x_list, Sw_list, p12_list = [], [], []
    tD_list, ai_list, at_list = [], [], []

    for n_done, (p, Pe_c, lb) in enumerate(combos, 1):
        t_bt = breakthrough_time_days(p)
        if 0.95 * t_bt <= t_min_days:
            continue
        times = np.linspace(t_min_days, 0.95 * t_bt, num_times).tolist()
        try:
            profiles = build_capillary_profiles(times, p, Pe_c, lb,
                                                n_seq=n_seq, alpha=alpha)
        except Exception as e:
            print(f"  combo skipped ({e})")
            continue

        for prof in profiles:
            x_seq = prof["x_seq"]
            Sw_true = prof["Sw_true"]
            idxs_np, targs_np = make_anchors_from_truth(
                x_seq, Sw_true, swc=float(p["swc"]), sor=float(p["sor"]),
                Sw_star=prof["Sw_star"])

            # STAGE 3 [S3-4]: 12-dim conditioning
            p12 = np.array([
                p["no"], p["nw"], p["swc"], p["sor"],
                p["mu_w"], p["mu_o"], p["phi"],
                prof["t_D"], prof["xD_front"], prof["Sw_star"],
                prof["inv_Pec"], prof["lambda_bc"],
            ], dtype=np.float32)

            x_list.append(x_seq.reshape(-1, 1))
            Sw_list.append(Sw_true.reshape(-1, 1))
            p12_list.append(p12)
            tD_list.append(prof["t_D"])
            ai_list.append(idxs_np)
            at_list.append(targs_np)

        if verbose_every and n_done % verbose_every == 0:
            print(f"  {n_done}/{len(combos)} combo marches done")

    if len(x_list) == 0:
        raise RuntimeError("No valid capillary profiles generated.")

    x_all = np.stack(x_list, axis=0).astype(np.float32)
    Sw_all = np.stack(Sw_list, axis=0).astype(np.float32)
    p12_all = np.stack(p12_list, axis=0).astype(np.float32)
    tD_all = np.array(tD_list, dtype=np.float32)
    ai_all = np.stack(ai_list, axis=0).astype(np.int32)
    at_all = np.stack(at_list, axis=0).astype(np.float32)

    print(f"Multi-case dataset: N={x_all.shape[0]} profiles, "
          f"T={x_all.shape[1]}, K={ai_all.shape[1]}, "
          f"param_dim={p12_all.shape[1]}")
    return x_all, Sw_all, p12_all, tD_all, ai_all, at_all


def make_tf_datasets_from_arrays(
    x_all, Sw_all, p_vec_all, tD_all, anchor_idxs_all, anchor_targs_all,
    train_frac: float = 0.8, batch_size: int = 4096,
    shuffle_buffer: int = 10_000, seed: int = 1337,
):
    N = x_all.shape[0]
    rng = np.random.default_rng(seed)
    idx = np.arange(N)
    rng.shuffle(idx)
    N_train = int(train_frac * N)
    train_idx = idx[:N_train]
    test_idx = idx[N_train:]

    def _make_ds(sub_idx, shuffle=True):
        ds = tf.data.Dataset.from_tensor_slices((
            x_all[sub_idx], Sw_all[sub_idx], p_vec_all[sub_idx],
            tD_all[sub_idx], anchor_idxs_all[sub_idx], anchor_targs_all[sub_idx],
        ))
        if shuffle:
            ds = ds.shuffle(min(shuffle_buffer, len(sub_idx)))
        ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
        return ds

    train_ds = _make_ds(train_idx, shuffle=True)
    test_ds = _make_ds(test_idx, shuffle=False)
    print(f"Train profiles: {len(train_idx)} | Test profiles: {len(test_idx)}")
    return train_ds, test_ds


# ==============================================================================
# TRAINING WITH HISTORY LOGGING
# ==============================================================================

def train_pi_rnn_from_dataset_with_history(
    model: tf.keras.Model,
    params_fixed: Dict,
    train_ds: tf.data.Dataset,
    epochs: int,
    lambdas: Tuple[float, float, float, float],
    lambda_anchor: float,
    lambda_tip: float,
    lambda_mono: float,
    lambda_mass: float,
    lambda_curv: float,
    lr: float,
    log_every: int = 50,
    phys_warmup_epochs: int = 100,  # STAGE 3 [S3-6]
) -> Dict[str, List[float]]:
    """
    Training loop with history. STAGE 3 changes: the forward pass happens
    inside pde_residual_loss (3 model calls per step: nominal plus tD +/-),
    lambda_tip weights the outlet BC, and the PDE residual weight ramps
    from 0 to lambdas[1] over phys_warmup_epochs.
    """
    optimizer = tf.keras.optimizers.Adam(lr)

    history = {
        'epoch': [], 'data': [], 'physics': [],
        'bc_inj': [], 'bc_out': [], 'anchor': [],
        'mono': [], 'mass': [], 'curv': [], 'total': [],
    }

    for ep in range(1, epochs + 1):
        # V3 [FIX-6]: step decay kills the late-training sawtooth
        if ep in (201, 301, 451, 701):  # V8 [V8-3]
            new_lr = float(optimizer.learning_rate.numpy()) * 0.5
            optimizer.learning_rate.assign(new_lr)
            print(f"  [lr decay] epoch {ep}: lr -> {new_lr:.2e}")
        w_pde = lambdas[1] * min(1.0, ep / max(1, phys_warmup_epochs))
        Ld_sum = Lp_sum = Lbc_inj_sum = Lbc_out_sum = 0.0
        La_sum = Lmono_sum = Lmass_sum = Lcurv_sum = Ltotal_sum = 0.0
        count_samples = 0.0

        for (x_batch, S_true_batch, p_vec_batch, tD_batch,
             anchor_idxs_batch, anchor_targs_batch) in train_ds:

            B = tf.shape(x_batch)[0]

            with tf.GradientTape() as tape:
                # STAGE 3 [S3-6]: pde_residual_loss does the forward pass
                Lp, Lcurv, S_pred = pde_residual_loss(
                    model, x_batch, p_vec_batch, params_fixed)  # V6
                Ld = data_loss(S_pred, S_true_batch)
                Lbc_inj = injector_bc_loss(S_pred, p_vec_batch)
                Lbc_out = outlet_bc_loss(S_pred, S_true_batch)  # STAGE 3 [S3-5]
                Lsh = shape_loss(S_pred, S_true_batch)
                La = anchor_loss(S_pred, anchor_idxs_batch, anchor_targs_batch)
                Lmono = monotonicity_loss(S_pred)
                Lmass = mass_balance_loss(S_pred, S_true_batch, x_batch)  # V3 [FIX-9]

                L = (lambdas[0] * Ld + w_pde * Lp + lambdas[2] * Lbc_inj
                     + lambda_tip * Lbc_out + lambdas[3] * Lsh
                     + lambda_anchor * La + lambda_mono * Lmono
                     + lambda_mass * Lmass + lambda_curv * Lcurv)

            grads = tape.gradient(L, model.trainable_variables)
            optimizer.apply_gradients(zip(grads, model.trainable_variables))

            bsz = float(B.numpy())
            Ld_sum += float(Ld.numpy()) * bsz
            Lp_sum += float(Lp.numpy()) * bsz
            Lbc_inj_sum += float(Lbc_inj.numpy()) * bsz
            Lbc_out_sum += float(Lbc_out.numpy()) * bsz
            La_sum += float(La.numpy()) * bsz
            Lmono_sum += float(Lmono.numpy()) * bsz
            Lmass_sum += float(Lmass.numpy()) * bsz
            Lcurv_sum += float(Lcurv.numpy()) * bsz
            Ltotal_sum += float(L.numpy()) * bsz
            count_samples += bsz

        n = max(1.0, count_samples)
        history['epoch'].append(ep)
        history['data'].append(Ld_sum / n)
        history['physics'].append(Lp_sum / n)
        history['bc_inj'].append(Lbc_inj_sum / n)
        history['bc_out'].append(Lbc_out_sum / n)
        history['anchor'].append(La_sum / n)
        history['mono'].append(Lmono_sum / n)
        history['mass'].append(Lmass_sum / n)
        history['curv'].append(Lcurv_sum / n)
        history['total'].append(Ltotal_sum / n)

        if ep % log_every == 0:
            print(f"[Stage 3] Epoch {ep:04d} | "
                  f"Data {Ld_sum/n:.3e} | PDE {Lp_sum/n:.3e} (w={w_pde:.3f}) "
                  f"| BC_inj {Lbc_inj_sum/n:.3e} | BC_out {Lbc_out_sum/n:.3e} "
                  f"| Anchor {La_sum/n:.3e} | Mono {Lmono_sum/n:.3e} "
                  f"| Mass {Lmass_sum/n:.3e} | Curv {Lcurv_sum/n:.3e}")

    return history


# ==============================================================================
# CONVERGENCE PLOTTING
# ==============================================================================

def plot_training_convergence(
    history: Dict[str, List[float]],
    lambdas: Dict[str, float],
    save_path: str = None,
    figsize: Tuple[float, float] = (14, 5),
):
    epochs = history['epoch']

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    ax1 = axes[0]
    ax1.semilogy(epochs, history['data'], label=r'$\mathcal{L}_{data}$', linewidth=2)
    ax1.semilogy(epochs, history['physics'], label=r'$\mathcal{L}_{PDE}$', linewidth=2)
    ax1.semilogy(epochs, history['bc_inj'], label=r'$\mathcal{L}_{BC,inj}$', linewidth=2)
    ax1.semilogy(epochs, history['bc_out'], label=r'$\mathcal{L}_{BC,out}$', linewidth=2)
    ax1.semilogy(epochs, history['anchor'], label=r'$\mathcal{L}_{anchor}$', linewidth=2)
    ax1.semilogy(epochs, history['mono'], label=r'$\mathcal{L}_{mono}$', linewidth=2, linestyle='--')
    ax1.semilogy(epochs, history['mass'], label=r'$\mathcal{L}_{mass}$', linewidth=2, linestyle='-.')
    ax1.semilogy(epochs, history['curv'], label=r'$\mathcal{L}_{curv}$', linewidth=2, linestyle=':')

    ax1.set_xlabel('Epoch', fontsize=12)
    ax1.set_ylabel('Loss (log scale)', fontsize=12)
    ax1.set_title('(a) Individual Loss Components', fontsize=13)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3, which='both')
    ax1.set_xlim([0, max(epochs)])

    ax2 = axes[1]
    pairs = [('data', 'data'), ('physics', 'physics'), ('bc_inj', 'bc_inj'),
             ('bc_out', 'bc_out'), ('anchor', 'anchor'), ('mono', 'mono'),
             ('mass', 'mass'), ('curv', 'curv')]
    for key, lkey in pairs:
        weighted = [lambdas[lkey] * v for v in history[key]]
        ax2.semilogy(epochs, weighted,
                     label=rf'$\lambda \mathcal{{L}}_{{{key}}}$ '
                           rf'($\lambda$={lambdas[lkey]})',
                     linewidth=2,
                     linestyle='--' if key == 'mono' else '-')
    ax2.semilogy(epochs, history['total'],
                 label=r'$\mathcal{L}_{total}$', linewidth=2.5,
                 color='black', linestyle=':')

    ax2.set_xlabel('Epoch', fontsize=12)
    ax2.set_ylabel('Weighted Loss (log scale)', fontsize=12)
    ax2.set_title('(b) Weighted Contributions to Total Loss', fontsize=13)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3, which='both')
    ax2.set_xlim([0, max(epochs)])

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        pdf_path = save_path.replace('.png', '.pdf')
        plt.savefig(pdf_path, bbox_inches='tight')
        print(f"Saved convergence figure to {save_path} and {pdf_path}")

    plt.show()
    return fig


# ==============================================================================
# PREDICTION AND EVALUATION HELPERS
# ==============================================================================

def conditioning_vector_np(p_case: dict, t_D: float, xD_front: float,
                           Sw_star: float, inv_pec: float,
                           lambda_bc: float) -> np.ndarray:
    p12 = np.array([[
        p_case["no"], p_case["nw"], p_case["swc"], p_case["sor"],
        p_case["mu_w"], p_case["mu_o"], p_case["phi"],
        t_D, xD_front, Sw_star, inv_pec, lambda_bc,
    ]], dtype=np.float32)
    return append_logM(p12)  # V7 [V7-1]


def predict_profile(model: tf.keras.Model, p_case: dict, t_days: float,
                    Pe_c: float, lambda_bc: float,
                    nx_ref: int | None = None) -> dict:
    """
    STAGE 3 [S3-8]: replaces predict_profile_fan. The model evaluates on
    any x grid directly; no shock reconstruction. Truth is a fine-grid
    capillary reference (2x the training resolution by default).
    """
    if nx_ref is None:
        nx_ref = int(np.clip(48 * Pe_c, 801, 4801)) | 1

    xD_true, snaps = solve_capillary_snapshots(p_case, lambda_bc, Pe_c,
                                               [t_days], nx=nx_ref)
    Sw_true = snaps[0]

    grid = np.linspace(p_case["swc"], 1.0 - p_case["sor"], 800)
    _, fw = dfw_dsw_np(grid, p_case)
    Sw_star, _, slope_star, _ = welge_tangent(grid, fw, p_case["swc"])

    C = (FT3_PER_BBL * p_case["i_w"]) / (p_case["phi"] * p_case["A"]
                                         * p_case["x_ip"])
    t_D = C * t_days

    # V4 [FIX-12]: evaluate on the SAME grid family and length as training,
    # built without the truth. This is also the deployable inference path.
    x_eval = grid_from_conditioning(min(1.0, t_D * slope_star), 1.0 / Pe_c,
                                    n_points=N_SEQ)
    p12 = conditioning_vector_np(p_case, t_D, min(1.0, t_D * slope_star),
                                 Sw_star, 1.0 / Pe_c, lambda_bc)
    Sw_pred = model([x_eval.astype(np.float32).reshape(1, -1, 1), p12],
                    training=False).numpy().squeeze()

    return {
        "xD_true": xD_true, "Sw_true_true": Sw_true,
        "xD_pred": x_eval, "Sw_pred": Sw_pred,
        "t_days": float(t_days), "t_D": float(t_D),
        "Pe_c": float(Pe_c), "lambda_bc": float(lambda_bc),
        "xD_front_true": front_mid_crossing(xD_true, Sw_true, Sw_star,
                                            p_case["swc"]),
    }


def plot_profile(res: dict) -> None:
    plt.figure(figsize=(8, 5))
    plt.plot(res["xD_true"], res["Sw_true_true"], label="Capillary solver",
             linewidth=2)
    plt.plot(res["xD_pred"], res["Sw_pred"], "--", label="PI-RNN Pred",
             linewidth=2)
    plt.axvline(res["xD_front_true"], color="k", linestyle=":",
                linewidth=1, label="Front (mid-jump)")
    plt.title(f"t = {res['t_days']:.1f} days (t_D = {res['t_D']:.3f}, "
              f"$Pe_c$ = {res['Pe_c']:.0f}, $\\lambda$ = {res['lambda_bc']})")
    plt.xlabel("$x_D$")
    plt.ylabel("$S_w$")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


def evaluate_times_case(model, p_case, times, Pe_c, lambda_bc):
    try:
        import pandas as pd
    except ImportError:
        return None

    rows = []
    for t in times:
        res = predict_profile(model, p_case, float(t), Pe_c, lambda_bc)
        Sw_pred_interp = np.interp(res["xD_true"], res["xD_pred"],
                                   res["Sw_pred"])
        err = Sw_pred_interp - res["Sw_true_true"]
        rows.append({
            "t_days": res["t_days"], "t_D": res["t_D"],
            "Pe_c": res["Pe_c"],
            "xD_front_true": res["xD_front_true"],
            "mse": float(np.mean(err**2)),
            "mae": float(np.mean(np.abs(err))),
            "max_abs_err": float(np.max(np.abs(err))),
        })

    return pd.DataFrame(rows).sort_values("t_days").reset_index(drop=True)


def make_case_from_values(base_p, no, nw, swc, sor, mu_w, mu_o, phi) -> dict:
    p = dict(base_p)
    p["no"], p["nw"] = float(no), float(nw)
    p["swc"], p["sor"] = float(swc), float(sor)
    p["mu_w"], p["mu_o"] = float(mu_w), float(mu_o)
    p["phi"] = float(phi)
    validate_params(p)
    return p


# ==============================================================================
# STAGE 3 [S3-4]: SHARP-LIMIT EXTRAPOLATION TEST
# ==============================================================================

def sharp_limit_test(model, p_case: dict, t_days: float, lambda_bc: float,
                     inv_pec_seq=(0.1, 1 / 22, 0.02, 0.01, 0.005, 0.0)):
    """
    Evaluate (never train) the model toward inv_Pec = 0. The predicted
    front should sharpen monotonically, and at inv_Pec = 0 the fan region
    should converge to the incompressible analytical profile. This is how
    Stage 3 nests Stage 1 without ever training on a discontinuity.
    """
    xD_a, Sw_a, meta = profile_at_time(t_days, p_case)
    Sw_star = meta["Sw_star"]

    grid = np.linspace(p_case["swc"], 1.0 - p_case["sor"], 800)
    _, fw = dfw_dsw_np(grid, p_case)
    _, _, slope_star, _ = welge_tangent(grid, fw, p_case["swc"])
    C = (FT3_PER_BBL * p_case["i_w"]) / (p_case["phi"] * p_case["A"]
                                         * p_case["x_ip"])
    t_D = C * t_days

    x_fine = np.linspace(0.0, 1.0, 400)
    print(f"{'inv_Pec':>9} {'width_10_90':>12}")
    Sw0 = None
    for ip in inv_pec_seq:
        p12 = conditioning_vector_np(p_case, t_D,
                                     min(1.0, t_D * slope_star),
                                     Sw_star, float(ip), lambda_bc)
        # V4 [FIX-12]: training-family grid, then interpolate to x_fine
        g = grid_from_conditioning(min(1.0, t_D * slope_star), float(ip),
                                   n_points=N_SEQ)
        Sw_g = model([g.astype(np.float32).reshape(1, -1, 1), p12],
                     training=False).numpy().squeeze()
        Sw_p = np.interp(x_fine, g, Sw_g)
        S_hi = p_case["swc"] + 0.9 * (Sw_star - p_case["swc"])
        S_lo = p_case["swc"] + 0.1 * (Sw_star - p_case["swc"])

        def crossing(level):
            below = np.where(Sw_p < level)[0]
            if len(below) == 0 or below[0] == 0:
                return np.nan
            i = below[0]
            return float(np.interp(level, [Sw_p[i], Sw_p[i - 1]],
                                   [x_fine[i], x_fine[i - 1]]))

        width = crossing(S_lo) - crossing(S_hi)
        print(f"{ip:>9.4f} {width:>12.4f}")
        if ip == 0.0:
            Sw0 = Sw_p

    if Sw0 is not None:
        fan_mask = x_fine < 0.8 * meta["xD_shock"]
        Sa = np.interp(x_fine[fan_mask], xD_a, Sw_a)
        err_fan = float(np.max(np.abs(Sw0[fan_mask] - Sa)))
        print(f"Fan-region max|dSw| at inv_Pec = 0 vs Stage 1 analytical: "
              f"{err_fan:.4e}")
        return err_fan
    return None


# ==============================================================================
# V3 [FIX-8]: IN-SAMPLE TRIAGE CHECK
# ==============================================================================

def in_sample_check(model, npz_path: str = "stage3_capillary_dataset.npz",
                    n_rows: int = 6, seed: int = 0):
    """
    Predict on rows stored in the TRAINING dataset itself (exact grids and
    conditioning the network saw). Discriminates the two front-lag causes:
      in-sample good, held-out bad  -> sampling density (raise max_cases /
                                       stratify), the model class is fine
      in-sample ALSO lags           -> the coordinate cue was the problem
                                       and [FIX-5] is the cure
    """
    import os
    if not os.path.exists(npz_path):
        print("(no dataset npz found; skipping in-sample check)")
        return
    d = np.load(npz_path)
    x_all, Sw_all, p12_all = d["x"], d["Sw"], d["p12"]
    if p12_all.shape[1] == 12:  # V7 hotfix: disk stores 12-dim, model wants 13
        p12_all = append_logM(p12_all)
    rng = np.random.default_rng(seed)
    rows = rng.choice(x_all.shape[0], size=min(n_rows, x_all.shape[0]),
                      replace=False)
    print(f"{'row':>6} {'Pe_c':>6} {'tD':>7} {'MAE':>10} {'max':>10} "
          f"{'front err':>10}")
    for r in rows:
        x_seq = x_all[r:r+1]
        Sw_true = Sw_all[r, :, 0]
        p12 = p12_all[r:r+1]
        Sw_pred = model([x_seq, p12], training=False).numpy().squeeze()
        err = np.abs(Sw_pred - Sw_true)
        swc, Sw_star = p12[0, 2], p12[0, 9]
        level = swc + 0.5 * (Sw_star - swc)

        def crossing(S):
            below = np.where(S < level)[0]
            if len(below) == 0 or below[0] == 0:
                return np.nan
            i = below[0]
            return float(np.interp(level, [S[i], S[i-1]],
                                   [x_seq[0, i, 0], x_seq[0, i-1, 0]]))

        dfront = crossing(Sw_pred) - crossing(Sw_true)
        pe = 1.0 / max(p12[0, 10], 1e-9)
        print(f"{r:>6} {pe:>6.0f} {p12[0, 7]:>7.3f} {err.mean():>10.4e} "
              f"{err.max():>10.4e} {dfront:>+10.4f}")


# ==============================================================================
# DIAGNOSTIC PLOTTING FUNCTIONS
# ==============================================================================

def compute_residuals_over_times(
    model: tf.keras.Model,
    p_case: dict,
    times: list,
    Pe_c: float,          # STAGE 3 [S3-8]
    lambda_bc: float,     # STAGE 3 [S3-8]
    n_x: int = 200,
) -> dict:
    """
    Residuals (S_pred - S_true) over multiple times on a common x_D grid.
    STAGE 3: truth is a single fine-grid capillary march snapshotting all
    times; the model is evaluated directly on the common grid.
    """
    xD_grid = np.linspace(0.0, 1.0, n_x)

    nx_ref = int(np.clip(48 * Pe_c, 801, 4801)) | 1
    xD_ref, snaps = solve_capillary_snapshots(p_case, lambda_bc, Pe_c,
                                              times, nx=nx_ref)

    grid = np.linspace(p_case["swc"], 1.0 - p_case["sor"], 800)
    _, fw = dfw_dsw_np(grid, p_case)
    Sw_star, _, slope_star, _ = welge_tangent(grid, fw, p_case["swc"])
    C = (FT3_PER_BBL * p_case["i_w"]) / (p_case["phi"] * p_case["A"]
                                         * p_case["x_ip"])

    residuals_all, Sw_true_all, Sw_pred_all, xD_star_all = [], [], [], []

    for t_days, Sw_true_full in zip(sorted(float(t) for t in times), snaps):
        t_D = C * t_days
        xD_star_all.append(front_mid_crossing(xD_ref, Sw_true_full,
                                              Sw_star, p_case["swc"]))

        p12 = conditioning_vector_np(p_case, t_D,
                                     min(1.0, t_D * slope_star),
                                     Sw_star, 1.0 / Pe_c, lambda_bc)
        # V4 [FIX-12]: predict on the training-family grid, interpolate to
        # the common plotting grid afterwards
        x_eval = grid_from_conditioning(min(1.0, t_D * slope_star),
                                        1.0 / Pe_c, n_points=N_SEQ)
        Sw_on_eval = model(
            [x_eval.astype(np.float32).reshape(1, -1, 1), p12],
            training=False).numpy().squeeze()
        Sw_pred_interp = np.interp(xD_grid, x_eval, Sw_on_eval)

        Sw_true_interp = np.interp(xD_grid, xD_ref, Sw_true_full)
        residuals = Sw_pred_interp - Sw_true_interp

        residuals_all.append(residuals)
        Sw_true_all.append(Sw_true_interp)
        Sw_pred_all.append(Sw_pred_interp)

    return {
        'xD_grid': xD_grid,
        'residuals': np.array(residuals_all),
        'Sw_true_all': np.array(Sw_true_all),
        'Sw_pred_all': np.array(Sw_pred_all),
        'times_days': times,
        'xD_star_all': xD_star_all,
    }


def plot_diagnostic_panels(
    model: tf.keras.Model,
    p_case: dict,
    times: list,
    Pe_c: float,          # STAGE 3 [S3-8]
    lambda_bc: float,     # STAGE 3 [S3-8]
    case_name: str = "",
    save_path: str = None,
    figsize: tuple = (12, 10),
):
    """
    4-panel diagnostic figure:
      (a) Residual vs. position showing errors concentrated at the front
      (b) Residual histogram with near-zero mean
      (c) Q-Q plot for approximate normality
      (d) Parity plot with R2
    """
    data = compute_residuals_over_times(model, p_case, times,
                                        Pe_c=Pe_c, lambda_bc=lambda_bc)

    xD_grid = data['xD_grid']
    residuals = data['residuals']
    Sw_true_all = data['Sw_true_all']
    Sw_pred_all = data['Sw_pred_all']
    xD_star_all = data['xD_star_all']

    residuals_flat = residuals.flatten()
    Sw_true_flat = Sw_true_all.flatten()
    Sw_pred_flat = Sw_pred_all.flatten()

    mean_res = np.mean(residuals_flat)
    std_res = np.std(residuals_flat)

    ss_res = np.sum((Sw_true_flat - Sw_pred_flat) ** 2)
    ss_tot = np.sum((Sw_true_flat - np.mean(Sw_true_flat)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)

    fig, axes = plt.subplots(2, 2, figsize=figsize)

    # (a) residual vs position
    ax1 = axes[0, 0]
    cmap = plt.cm.viridis
    n_times = len(times)
    for i, (t, res, xD_star) in enumerate(zip(times, residuals, xD_star_all)):
        color = cmap(i / max(1, n_times - 1))
        ax1.plot(xD_grid, res, color=color, alpha=0.7, linewidth=1.5,
                 label=f't = {t:.0f} d' if i % max(1, n_times // 5) == 0 else None)
        if np.isfinite(xD_star):
            ax1.axvline(xD_star, color=color, linestyle=':', alpha=0.3,
                        linewidth=1)

    mean_residual = np.mean(residuals, axis=0)
    std_residual = np.std(residuals, axis=0)
    ax1.fill_between(xD_grid, mean_residual - 2*std_residual,
                     mean_residual + 2*std_residual,
                     alpha=0.2, color='gray', label='±2σ envelope')
    ax1.plot(xD_grid, mean_residual, 'k--', linewidth=2, label='Mean residual')
    ax1.axhline(0, color='k', linestyle='-', linewidth=0.5)
    ax1.set_xlabel('Dimensionless Position $x_D$', fontsize=11)
    ax1.set_ylabel('Residual $(S_w^{pred} - S_w^{true})$', fontsize=11)
    ax1.set_title('(a) Residual vs. Position', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim([0, 1])

    finite_stars = [x for x in xD_star_all if np.isfinite(x)]
    if finite_stars:
        ylim = ax1.get_ylim()
        ax1.annotate('Front\nregion', xy=(np.mean(finite_stars), ylim[1]*0.7),
                     fontsize=9, ha='center', style='italic', color='gray')

    # (b) histogram
    ax2 = axes[0, 1]
    ax2.hist(residuals_flat, bins=50, density=True,
             alpha=0.7, color='steelblue', edgecolor='white')
    x_norm = np.linspace(residuals_flat.min(), residuals_flat.max(), 200)
    ax2.plot(x_norm, stats.norm.pdf(x_norm, mean_res, std_res), 'r-',
             linewidth=2,
             label=f'Normal fit\n$\\mu$={mean_res:.2e}\n$\\sigma$={std_res:.2e}')
    ax2.axvline(mean_res, color='red', linestyle='--', linewidth=1.5,
                label='Mean')
    ax2.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax2.set_xlabel('Residual $(S_w^{pred} - S_w^{true})$', fontsize=11)
    ax2.set_ylabel('Probability Density', fontsize=11)
    ax2.set_title('(b) Residual Distribution', fontsize=12, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # (c) Q-Q
    ax3 = axes[1, 0]
    (osm, osr), (slope, intercept, r) = stats.probplot(residuals_flat,
                                                       dist="norm")
    ax3.scatter(osm, osr, alpha=0.5, s=10, c='steelblue', label='Residuals')
    x_line = np.array([osm.min(), osm.max()])
    ax3.plot(x_line, slope * x_line + intercept, 'r-', linewidth=2,
             label=f'Normal fit (r={r:.4f})')
    ax3.set_xlabel('Theoretical Quantiles', fontsize=11)
    ax3.set_ylabel('Sample Quantiles', fontsize=11)
    ax3.set_title('(c) Normal Q-Q Plot', fontsize=12, fontweight='bold')
    ax3.legend(loc='lower right', fontsize=9)
    ax3.grid(True, alpha=0.3)

    if len(residuals_flat) > 5000:
        sample_idx = np.random.choice(len(residuals_flat), 5000, replace=False)
        stat, p_value = stats.shapiro(residuals_flat[sample_idx])
    else:
        stat, p_value = stats.shapiro(residuals_flat)
    ax3.text(0.05, 0.95, f'Shapiro-Wilk\np = {p_value:.3f}',
             transform=ax3.transAxes, fontsize=9, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # (d) parity
    ax4 = axes[1, 1]
    if len(Sw_true_flat) > 5000:
        idx = np.random.choice(len(Sw_true_flat), 5000, replace=False)
        Sw_true_plot, Sw_pred_plot = Sw_true_flat[idx], Sw_pred_flat[idx]
    else:
        Sw_true_plot, Sw_pred_plot = Sw_true_flat, Sw_pred_flat
    ax4.scatter(Sw_true_plot, Sw_pred_plot, alpha=0.3, s=5, c='steelblue')
    sw_min = min(Sw_true_flat.min(), Sw_pred_flat.min())
    sw_max = max(Sw_true_flat.max(), Sw_pred_flat.max())
    ax4.plot([sw_min, sw_max], [sw_min, sw_max], 'r-', linewidth=2,
             label='Perfect prediction')
    margin = 0.05 * (sw_max - sw_min)
    ax4.plot([sw_min, sw_max], [sw_min + margin, sw_max + margin],
             'k--', linewidth=1, alpha=0.5)
    ax4.plot([sw_min, sw_max], [sw_min - margin, sw_max - margin],
             'k--', linewidth=1, alpha=0.5, label='±5% band')
    ax4.set_xlabel('True $S_w$', fontsize=11)
    ax4.set_ylabel('Predicted $S_w$', fontsize=11)
    ax4.set_title('(d) Parity Plot', fontsize=12, fontweight='bold')
    ax4.legend(loc='lower right', fontsize=9)
    ax4.grid(True, alpha=0.3)
    ax4.set_aspect('equal', adjustable='box')
    ax4.set_xlim([sw_min - 0.02, sw_max + 0.02])
    ax4.set_ylim([sw_min - 0.02, sw_max + 0.02])
    ax4.text(0.05, 0.95, f'$R^2$ = {r_squared:.6f}', transform=ax4.transAxes,
             fontsize=12, fontweight='bold', verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    if case_name:
        fig.suptitle(f'PI-RNN Diagnostic Analysis: {case_name}',
                     fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        pdf_path = save_path.replace('.png', '.pdf')
        plt.savefig(pdf_path, bbox_inches='tight')
        print(f"Saved diagnostic figure to {save_path} and {pdf_path}")

    plt.show()

    print("\n" + "="*50)
    print("DIAGNOSTIC SUMMARY")
    print("="*50)
    print(f"Number of evaluation points: {len(residuals_flat)}")
    print(f"Mean residual: {mean_res:.4e}")
    print(f"Std residual: {std_res:.4e}")
    print(f"Max |residual|: {np.max(np.abs(residuals_flat)):.4e}")
    print(f"R²: {r_squared:.6f}")
    print(f"Shapiro-Wilk p-value: {p_value:.4f}")

    return fig, {
        'mean_residual': mean_res,
        'std_residual': std_res,
        'max_abs_residual': np.max(np.abs(residuals_flat)),
        'r_squared': r_squared,
        'shapiro_p': p_value,
    }


# ==============================================================================
# V7 [V7-2]: SUPPLEMENTAL SLAB (low-M corner + early-time coverage)
# ==============================================================================

def build_supplemental_slab(base_p: Dict, seed: int = 1337,
                            n_rock: int = 60,
                            pec_vals=(10.0, 22.0, 50.0, 100.0),
                            lambda_vals=(1.5, 2.0, 3.0),
                            n_seq: int = N_SEQ, alpha: float = 8.0):
    """
    Log-spaced low-M cases (mu_w in 0.5/1/2/3.5, previously ONE grid point
    below 6.0) and geometric time sampling reaching t = 60 d for the
    boundary-layer regime. ~n_rock * 12 combos, one march each.
    """
    rng = np.random.default_rng(seed + 7)
    mu_w_low = np.array([0.5, 1.0, 2.0, 3.5], dtype=np.float32)

    rock = []
    for _ in range(n_rock):
        p = dict(base_p)
        p["no"] = float(rng.choice([2.0, 3.0, 4.0]))
        p["nw"] = float(rng.choice([2.0, 3.0, 4.0]))
        p["swc"] = float(rng.choice([0.10, 0.20, 0.30]))
        p["sor"] = float(rng.choice([0.10, 0.20, 0.30, 0.40]))
        p["mu_w"] = float(rng.choice(mu_w_low))
        p["mu_o"] = float(rng.choice(np.arange(0.3, 1.0 + 1e-9, 0.1)))
        p["phi"] = float(rng.choice([0.10, 0.20, 0.30]))
        try:
            validate_params(p)
        except AssertionError:
            continue
        rock.append(p)

    combos = [(p, float(pe), float(lb)) for p in rock
              for pe in pec_vals for lb in lambda_vals]
    rng.shuffle(combos)

    x_l, S_l, p_l, t_l, ai_l, at_l = [], [], [], [], [], []
    for n_done, (p, Pe_c, lb) in enumerate(combos, 1):
        t_bt = breakthrough_time_days(p)
        if 0.95 * t_bt <= 60.0:
            continue
        times = np.geomspace(60.0, 0.95 * t_bt, 8).tolist()  # early-heavy
        try:
            profiles = build_capillary_profiles(times, p, Pe_c, lb,
                                                n_seq=n_seq, alpha=alpha)
        except Exception as e:
            print(f"  slab combo skipped ({e})")
            continue
        for prof in profiles:
            idxs, targs = make_anchors_from_truth(
                prof["x_seq"], prof["Sw_true"], swc=float(p["swc"]),
                sor=float(p["sor"]), Sw_star=prof["Sw_star"])
            p12 = np.array([
                p["no"], p["nw"], p["swc"], p["sor"],
                p["mu_w"], p["mu_o"], p["phi"],
                prof["t_D"], prof["xD_front"], prof["Sw_star"],
                prof["inv_Pec"], prof["lambda_bc"],
            ], dtype=np.float32)
            x_l.append(prof["x_seq"].reshape(-1, 1))
            S_l.append(prof["Sw_true"].reshape(-1, 1))
            p_l.append(p12)
            t_l.append(prof["t_D"])
            ai_l.append(idxs)
            at_l.append(targs)
        if n_done % 100 == 0:
            print(f"  slab: {n_done}/{len(combos)} marches")

    slab = dict(x=np.stack(x_l).astype(np.float32),
                Sw=np.stack(S_l).astype(np.float32),
                p12=np.stack(p_l).astype(np.float32),
                tD=np.array(t_l, np.float32),
                ai=np.stack(ai_l).astype(np.int32),
                at=np.stack(at_l).astype(np.float32))
    print(f"Slab: N={slab['x'].shape[0]} profiles")
    return slab


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == '__main__':
    print("TensorFlow version:", tf.__version__)
    gpus = tf.config.list_physical_devices('GPU')
    print("GPUs available:", gpus if gpus else "None")

    # --- Project config ---
    P = ProjectParams()
    P.validate()
    base_p = P.as_ml_dict()

    tf.keras.utils.set_random_seed(P.train.seed)

    # STAGE 3 [S3-9]: capillary grids. Pe_c = 22 matches your comparison
    # figure; lambda_bc controls the D_tilde shape. The sharp limit
    # inv_Pec = 0 is deliberately NOT in the training grid.
    pec_vals = np.array([10.0, 22.0, 50.0, 100.0], dtype=np.float32)
    lambda_vals = np.array([1.5, 2.0, 3.0], dtype=np.float32)

    # --- Generate parameter grid (with variable Corey exponents) ---
    print("\n" + "="*60)
    print("GENERATING PARAMETER GRID")
    print("="*60)
    print("Corey exponents: n_o ∈ [2,3,4], n_w ∈ [2,3,4]")
    print(f"Pe_c ∈ {pec_vals.tolist()} | lambda_bc ∈ {lambda_vals.tolist()}")
    param_list = generate_param_grid(base_p)

    # --- Build multi-case arrays ---
    print("\n" + "="*60)
    print("BUILDING MULTI-CASE ARRAYS (CAPILLARY, ADAPTIVE GRIDS)")
    print("="*60)
    # STAGE 3 [S3-7]: each combo marches a solver; 2400 combos is a
    # 15-45 min one-time build. Saved to npz: reload instead of rebuilding.
    import os
    if os.path.exists("stage3_capillary_dataset.npz"):  # V2 [FIX-4]
        d = np.load("stage3_capillary_dataset.npz")
        x_all, Sw_all, p12_all = d["x"], d["Sw"], d["p12"]
        tD_all, anchor_idxs_all, anchor_targs_all = d["tD"], d["ai"], d["at"]
        print(f"Reloaded dataset: N={x_all.shape[0]} profiles "
              "(delete the npz to force a rebuild).")
        if anchor_idxs_all.shape[1] < 6:  # V6 [V6-3]: upgrade stored K=4
            print("Recomputing anchors at K=6 from stored arrays...")
            ai_l, at_l = [], []
            for i in range(x_all.shape[0]):
                ai, at = make_anchors_from_truth(
                    x_all[i, :, 0], Sw_all[i, :, 0],
                    swc=float(p12_all[i, 2]), sor=float(p12_all[i, 3]),
                    Sw_star=float(p12_all[i, 9]))
                ai_l.append(ai)
                at_l.append(at)
            anchor_idxs_all = np.stack(ai_l).astype(np.int32)
            anchor_targs_all = np.stack(at_l).astype(np.float32)
            print(f"Anchors: K={anchor_idxs_all.shape[1]}")

        # V7 [V7-2]: supplemental slab, generated once then reloaded
        if os.path.exists("stage3_slab.npz"):
            s = np.load("stage3_slab.npz")
            slab = {k: s[k] for k in ("x", "Sw", "p12", "tD", "ai", "at")}
            print(f"Reloaded slab: N={slab['x'].shape[0]} profiles")
        else:
            slab = build_supplemental_slab(base_p, seed=P.train.seed)
            np.savez_compressed("stage3_slab.npz", **slab)
            print("Saved stage3_slab.npz.")
        x_all = np.concatenate([x_all, slab["x"]])
        Sw_all = np.concatenate([Sw_all, slab["Sw"]])
        p12_all = np.concatenate([p12_all, slab["p12"]])
        tD_all = np.concatenate([tD_all, slab["tD"]])
        anchor_idxs_all = np.concatenate([anchor_idxs_all, slab["ai"]])
        anchor_targs_all = np.concatenate([anchor_targs_all, slab["at"]])
        print(f"Combined dataset: N={x_all.shape[0]} profiles")
    else:
        x_all, Sw_all, p12_all, tD_all, anchor_idxs_all, anchor_targs_all = \
            build_multi_case_arrays(param_list, pec_vals, lambda_vals,
                                    num_times=6, t_min_days=100.0,
                                    n_seq=64, alpha=8.0,
                                    max_cases=2_400, seed=P.train.seed)
        np.savez_compressed("stage3_capillary_dataset.npz",
                            x=x_all, Sw=Sw_all, p12=p12_all, tD=tD_all,
                            ai=anchor_idxs_all, at=anchor_targs_all)
        print("Saved stage3_capillary_dataset.npz.")

    # V7 [V7-1]: upgrade conditioning rows to 13-dim (idempotent)
    if p12_all.shape[1] == 12:
        p12_all = append_logM(p12_all)
        print(f"Conditioning upgraded with log10(M): param_dim = "
              f"{p12_all.shape[1]}")

    # --- Build train/test datasets ---
    print("\n" + "="*60)
    print("CREATING TRAIN/TEST DATASETS")
    print("="*60)
    # STAGE 3 [S3-6]: batch 4096 (the PDE residual makes 3 forward passes)
    train_ds, test_ds = make_tf_datasets_from_arrays(
        x_all, Sw_all, p12_all, tD_all, anchor_idxs_all, anchor_targs_all,
        train_frac=0.8, batch_size=4096,
        shuffle_buffer=P.train.shuffle_buffer, seed=P.train.seed,
    )

    # --- Build model ---
    model = build_model(
        input_features=1, param_dim=PARAM_DIM_V7,  # V7 [V7-1]: 13 with logM
        hidden=P.train.hidden, layers=P.train.layers,
    )

    params_fixed = {
        "mu_w": P.rock.mu_w, "mu_o": P.rock.mu_o,
        "krw_max": P.rock.krw_max, "kro_max": P.rock.kro_max,
    }

    # --- Train with history logging ---
    print("\n" + "="*60)
    print("TRAINING MULTI-CASE PI-RNN (STAGE 3: CAPILLARY)")
    print("="*60)
    history = train_pi_rnn_from_dataset_with_history(
        model, params_fixed, train_ds,
        epochs=P.train.epochs,
        lambdas=(P.train.lambda_data, P.train.lambda_phys,
                 P.train.lambda_bc, P.train.lambda_shape),
        lambda_anchor=P.train.lambda_anchor,
        lambda_tip=P.train.lambda_tip,
        lambda_mono=P.train.lambda_mono,
        lambda_mass=P.train.lambda_mass,
        lambda_curv=P.train.lambda_curv,
        lr=P.train.lr, log_every=25,
        phys_warmup_epochs=P.train.phys_warmup_epochs,
    )

    # --- Plot convergence ---
    print("\n" + "="*60)
    print("PLOTTING TRAINING CONVERGENCE")
    print("="*60)
    lambdas_dict = {
        'data': P.train.lambda_data, 'physics': P.train.lambda_phys,
        'bc_inj': P.train.lambda_bc, 'bc_out': P.train.lambda_tip,
        'anchor': P.train.lambda_anchor, 'mono': P.train.lambda_mono,
        'mass': P.train.lambda_mass, 'curv': P.train.lambda_curv,
    }
    plot_training_convergence(
        history, lambdas_dict,
        save_path='training_convergence_stage3_capillary_v9.png'
    )

    # --- Save weights and config ---
    model.save_weights("pi_rnn_stage3_capillary_v9.weights.h5")
    print("Saved weights to pi_rnn_stage3_capillary_v9.weights.h5")

    import json
    with open("pi_rnn_stage3_capillary_v9_config.json", "w") as f:
        json.dump({
            "stage": 3,
            "hidden": P.train.hidden, "layers": P.train.layers,
            "param_dim": P.param_dim(), "seed": P.train.seed,
            "condition_on": list(P.train.condition_on),
            "pec_vals": pec_vals.tolist(),
            "lambda_vals": lambda_vals.tolist(),
            "n_seq": 64, "alpha": 8.0, "max_cases": 2_400,
            "num_times": 6,
        }, f)
    print("Saved config to pi_rnn_stage3_capillary_v9_config.json")

    # --- Model summary ---
    print("\n" + "="*60)
    print("MODEL SUMMARY")
    print("="*60)
    model.summary()

    # --- Test cases ---
    print("\n" + "="*60)
    print("TEST CASES")
    print("="*60)

    p_case_1 = make_case_from_values(
        base_p, no=2.0, nw=2.0, swc=0.20, sor=0.20,
        mu_w=0.5, mu_o=0.7, phi=0.20,
    )
    p_case_2 = make_case_from_values(
        base_p, no=3.0, nw=2.0, swc=0.15, sor=0.25,
        mu_w=6.0, mu_o=0.9, phi=0.25,
    )

    # STAGE 3 [S3-9]: each case evaluated at your figure's Pe_c and a
    # sharper one.
    cases = [("Case 1 (symmetric, Pe_c=22, lambda=2)", p_case_1, 22.0, 2.0),
             ("Case 1 (symmetric, Pe_c=100, lambda=2)", p_case_1, 100.0, 2.0),
             ("Case 2 (asymmetric, Pe_c=22, lambda=2)", p_case_2, 22.0, 2.0),
             ("Case 2 (asymmetric, Pe_c=10, lambda=1.5)", p_case_2, 10.0, 1.5)]

    for case_name, p_case, pe, lb in cases:
        print(f"\n{'='*50}")
        print(case_name)
        print('='*50)
        for k in ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi"]:
            print(f"  {k} = {p_case[k]}")
        print(f"  Pe_c = {pe} | lambda_bc = {lb}")

        t_bt = breakthrough_time_days(p_case)
        times = np.linspace(100.0, 0.9 * t_bt, 15).tolist()
        idxs_5 = np.linspace(0, len(times) - 1, 5, dtype=int)
        selected_times = [times[i] for i in idxs_5]

        print(f"Plotting at times: {[f'{t:.1f}' for t in selected_times]}")

        for t in selected_times:
            res = predict_profile(model, p_case, float(t), pe, lb)
            plot_profile(res)

        df = evaluate_times_case(model, p_case, times, pe, lb)
        if df is not None:
            print(f"\nMetrics for {case_name}:")
            print(df.to_string(index=False))

    # STAGE 3 [S3-9]: accuracy sweep over Pe_c. MAE should stay roughly
    # flat; a strong rise at high Pe_c means the front is under-resolved
    # (raise n_seq or alpha) or the Pe_c conditioning is undertrained.
    print("\n" + "="*60)
    print("STAGE 3 ACCURACY SWEEP OVER Pe_c (Case 1, lambda_bc = 2)")
    print("="*60)
    t_bt_1 = breakthrough_time_days(p_case_1)
    for pe in (10.0, 22.0, 50.0, 100.0):
        errs = []
        for t in np.linspace(200.0, 0.9 * t_bt_1, 6):
            res = predict_profile(model, p_case_1, float(t), pe, 2.0)
            Sw_i = np.interp(res["xD_true"], res["xD_pred"], res["Sw_pred"])
            errs.append(np.abs(Sw_i - res["Sw_true_true"]))
        errs = np.concatenate(errs)
        print(f"Pe_c = {pe:>5.0f} | MAE = {errs.mean():.4e} | "
              f"max = {errs.max():.4e}")

    # V3 [FIX-8]: in-sample triage (rows the network trained on)
    print("\n" + "="*60)
    print("IN-SAMPLE TRIAGE CHECK (training rows)")
    print("="*60)
    in_sample_check(model)

    # STAGE 3 [S3-4]: sharp-limit extrapolation (evaluated, never trained)
    print("\n" + "="*60)
    print("SHARP-LIMIT EXTRAPOLATION TEST (Case 1, t = 1000 d)")
    print("="*60)
    sharp_limit_test(model, p_case_1, 1000.0, lambda_bc=2.0)

    # --- Diagnostic panels ---
    print("\n" + "="*60)
    print("DIAGNOSTIC ANALYSIS")
    print("="*60)

    t_bt_1 = breakthrough_time_days(p_case_1)
    times_diag_1 = np.linspace(100.0, 0.9 * t_bt_1, 15).tolist()
    fig1, stats1 = plot_diagnostic_panels(
        model, p_case_1, times_diag_1, Pe_c=22.0, lambda_bc=2.0,
        case_name="Case 1: Symmetric Corey, $Pe_c = 22$",
        save_path="diagnostic_case1_symmetric_pec22.png",
    )

    t_bt_2 = breakthrough_time_days(p_case_2)
    times_diag_2 = np.linspace(100.0, 0.9 * t_bt_2, 15).tolist()
    fig2, stats2 = plot_diagnostic_panels(
        model, p_case_2, times_diag_2, Pe_c=100.0, lambda_bc=2.0,
        case_name="Case 2: Asymmetric Corey, $Pe_c = 100$",
        save_path="diagnostic_case2_asymmetric_pec100.png",
    )