"""
Physics-Informed Recurrent Neural Network for Buckley-Leverett Displacement
Multi-Case Training with Variable Corey Exponents and Convergence Plotting

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

# ==============================================================================
# CONSTANTS
# ==============================================================================

FT3_PER_BBL = 5.615  # ft^3 per barrel (STB or rb)
EPS = 1e-12

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

    def conditioning_vector(
        self,
        order: Tuple[str, ...] = ("no", "nw", "swi", "sor"),
        as_tensor: bool = False,
    ):
        values = {"no": self.no, "nw": self.nw, "swi": self.swi, "sor": self.sor}
        arr = np.array([[values[k] for k in order]], dtype=np.float32)
        if as_tensor:
            return tf.convert_to_tensor(arr, dtype=tf.float32)
        return arr

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
    lambda_phys: float = 0.05
    lambda_bc: float = 5.0
    lambda_tip: float = 5.0
    lambda_anchor: float = 10.0
    lambda_mono: float = 0.2
    lambda_shape: float = 0.0

    lr: float = 1e-3
    epochs: int = 400
    batch_size: int = 8192
    phys_warmup_epochs: int = 200
    phys_final: float = 0.25

    hidden: int = 64
    layers: int = 2

    seed: int = 1337
    shuffle_buffer: int = 10_000

    condition_on: Tuple[str, ...] = (
        "no", "nw", "swi", "sor",
        "mu_w", "mu_o", "phi",
        "tD", "xD_star", "Sw_star",
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
        required = {"no", "nw", "swi", "sor", "mu_w", "mu_o", "phi", "tD", "xD_star", "Sw_star"}
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

    def conditioning_vector(self, t_days: float | None = None,
                            xD_star: float | None = None,
                            Sw_star: float | None = None) -> List[float]:
        mapping = {
            "no": self.rock.no, "nw": self.rock.nw,
            "swi": self.rock.swc, "swc": self.rock.swc, "sor": self.rock.sor,
            "mu_w": self.rock.mu_w, "mu_o": self.rock.mu_o,
            "phi": self.geom.phi,
            "tD": (self.geom.tD(t_days) if t_days is not None else None),
            "xD_star": xD_star, "Sw_star": Sw_star,
            "mu_ratio": self.rock.viscosity_ratio(),
        }
        vec = []
        for key in self.train.condition_on:
            val = mapping.get(key, None)
            if val is None:
                raise ValueError(f"Missing value for '{key}'")
            vec.append(float(val))
        return vec

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
# BUCKLEY-LEVERETT PHYSICS
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
    x_shock = np.array([front_x_D, front_x_D], dtype=float)
    S_shock = np.array([p['swc'], Sw_star], dtype=float)
    xD_full = np.concatenate([x_left, x_right])
    Sw_full = np.concatenate([S_left, S_right])
    if not injector_at_left:
        xD_full = 1.0 - xD_full
        x_left = 1.0 - x_left
        x_right = 1.0 - x_right
        x_shock = 1.0 - x_shock
        front_x_D = 1.0 - front_x_D
    order = np.argsort(xD_full)
    xD_full = np.clip(xD_full[order], 0.0, 1.0)
    Sw_full = Sw_full[order]
    C = (FT3_PER_BBL * p['i_w']) / (p['phi'] * p['A'] * p['x_ip'])
    t_D = C * t_days
    meta = {
        'Sw_star': float(Sw_star), 'xD_shock': float(front_x_D),
        't_days': float(t_days), 't_D': float(t_D),
        'segments': {
            'rarefaction_left': (x_left, S_left),
            'shock_vertical': (x_shock, S_shock),
            'plateau_right': (x_right, S_right),
        }
    }
    return xD_full, Sw_full, meta


def build_profiles(times_days: List[float], p: Dict,
                   Sw_grid: np.ndarray | None = None) -> List[Dict]:
    profiles = []
    for t in times_days:
        xD, Sw_true, meta = profile_at_time(float(t), p, Sw_grid=Sw_grid)
        profiles.append({
            't_days': meta['t_days'], 't_D': meta['t_D'],
            'xD': xD, 'Sw_true': Sw_true,
            'xD_star': float(meta['xD_shock']), 'Sw_star': float(meta['Sw_star']),
        })
    return profiles


def build_fan_profiles(times_days: List[float], p: Dict,
                       Sw_grid: np.ndarray | None = None) -> List[Dict]:
    out = []
    for t in times_days:
        xD_full, Sw_full, meta = profile_at_time(float(t), p, Sw_grid=Sw_grid)
        xD_star = float(meta['xD_shock'])
        Sw_star = float(meta['Sw_star'])
        x_left, S_left = meta['segments']['rarefaction_left']
        xi = np.asarray(x_left, dtype=float) / max(EPS, xD_star)
        xi = np.clip(xi, 0.0, 1.0)
        out.append({
            't_days': float(meta['t_days']), 't_D': float(meta['t_D']),
            'xi': xi.astype(np.float32),
            'Sw_fan_true': np.asarray(S_left, dtype=np.float32),
            'xD_star': xD_star, 'Sw_star': Sw_star,
        })
    return out


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


# ==============================================================================
# NEURAL NETWORK MODEL
# ==============================================================================

def build_model(input_features: int = 1, param_dim: int = 10,
                hidden: int = 64, layers: int = 2) -> tf.keras.Model:
    x_in = tf.keras.Input(shape=(None, input_features), name="xi_seq")
    p_in = tf.keras.Input(shape=(param_dim,), name="p_vec")

    def repeat_params(args):
        x, p = args
        T = tf.shape(x)[1]
        p = tf.expand_dims(p, 1)
        return tf.tile(p, [1, T, 1])

    p_rep = tf.keras.layers.Lambda(repeat_params, name="repeat_params")([x_in, p_in])
    z = tf.keras.layers.Concatenate(axis=-1, name="concat_features")([x_in, p_rep])

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
    return tf.keras.Model(inputs=[x_in, p_in], outputs=Sw_pred, name="PI_RNN_FAN")


def fractional_flow_tf_param(S: tf.Tensor, p_vec: tf.Tensor,
                              params_fixed: Dict, eps: float = 1e-12) -> tf.Tensor:
    S = tf.convert_to_tensor(S, dtype=tf.float32)
    p_vec = tf.convert_to_tensor(p_vec, dtype=tf.float32)
    dtype = S.dtype

    mu_w_fixed = tf.cast(params_fixed['mu_w'], dtype)
    mu_o_fixed = tf.cast(params_fixed['mu_o'], dtype)
    krw_mx = tf.cast(params_fixed['krw_max'], dtype)
    kro_mx = tf.cast(params_fixed['kro_max'], dtype)
    eps_t = tf.cast(eps, dtype)

    def _expand(idx: int) -> tf.Tensor:
        v = p_vec[:, idx:idx+1]
        return v[:, tf.newaxis, :]

    param_dim = p_vec.shape[-1]

    if param_dim == 4:
        idx_no, idx_nw, idx_swc, idx_sor = 1, 0, 2, 3
        use_dynamic_mu = False
    elif param_dim >= 10:
        idx_no, idx_nw, idx_swc, idx_sor = 0, 1, 2, 3
        idx_mu_w, idx_mu_o = 4, 5
        use_dynamic_mu = True
    else:
        idx_no, idx_nw, idx_swc, idx_sor = 0, 1, 2, 3
        use_dynamic_mu = False

    nw = _expand(idx_nw)
    no = _expand(idx_no)
    swc = _expand(idx_swc)
    sor = _expand(idx_sor)

    if use_dynamic_mu:
        mu_w = _expand(idx_mu_w)
        mu_o = _expand(idx_mu_o)
    else:
        mu_w = mu_w_fixed
        mu_o = mu_o_fixed

    denom = tf.maximum(1e-8, 1.0 - swc - sor)
    Se = tf.clip_by_value((S - swc) / denom, 0.0, 1.0)

    krw = krw_mx * tf.pow(Se, nw)
    kro = kro_mx * tf.pow(1.0 - Se, no)

    M = mu_w / mu_o
    fw = 1.0 / (1.0 + M * (kro / (krw + eps_t)))
    return fw


# ==============================================================================
# ANCHOR GENERATION
# ==============================================================================

def make_fan_anchors_from_truth(xi: np.ndarray, Sw_fan_true: np.ndarray,
                                 swc: float, sor: float, Sw_star: float,
                                 k_interior: tuple = (0.25, 0.60)) -> tuple:
    xi = np.asarray(xi)
    Sw_fan_true = np.asarray(Sw_fan_true)
    n = len(xi)
    if n < 2:
        return np.array([0], np.int32), np.array([1.0 - sor], np.float32)
    i0 = 0
    iend = n - 1
    i1 = max(1, min(n - 2, int(round(k_interior[0] * (n - 1)))))
    i2 = max(i1 + 1, min(n - 2, int(round(k_interior[1] * (n - 1)))))
    idxs = [i0, i1, i2, iend]
    targs = [1.0 - sor, float(Sw_fan_true[i1]), float(Sw_fan_true[i2]), float(Sw_star)]
    uniq, idxs_out, targs_out = set(), [], []
    for ix, tv in sorted(zip(idxs, targs), key=lambda z: z[0]):
        if ix not in uniq:
            uniq.add(ix)
            idxs_out.append(int(ix))
            targs_out.append(float(tv))
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
def tip_bc_loss(S_pred: tf.Tensor, p_vec: tf.Tensor) -> tf.Tensor:
    param_dim = tf.shape(p_vec)[1]

    def _use_swstar():
        Sw_star = p_vec[:, -1:]
        S_tip = S_pred[:, -1, 0:1]
        return tf.reduce_mean(tf.square(S_tip - Sw_star))

    def _zero():
        return tf.constant(0.0, dtype=tf.float32)

    return tf.cond(param_dim > 4, _use_swstar, _zero)


@tf.function
def physics_loss_char(xi_seq: tf.Tensor, S_pred: tf.Tensor, S_true: tf.Tensor,
                      t_D: tf.Tensor, p_vec: tf.Tensor, params_fixed: dict) -> tf.Tensor:
    t_D = tf.reshape(t_D, [-1, 1, 1])

    with tf.GradientTape() as g:
        g.watch(S_pred)
        fw = fractional_flow_tf_param(S_pred, p_vec, params_fixed)
    dfdS = g.gradient(fw, S_pred)

    param_dim = tf.shape(p_vec)[1]

    def _xd_from_p():
        return p_vec[:, -2:-1]

    def _xd_one():
        return tf.ones_like(p_vec[:, :1], dtype=tf.float32)

    xD_star = tf.cond(param_dim > 4, _xd_from_p, _xd_one)
    xD_star = xD_star[:, tf.newaxis, :]

    res = xi_seq * xD_star - t_D * dfdS
    T = tf.shape(res)[1]

    def _core_residual(r):
        return r[:, 1:-1, :]

    def _all_residual(r):
        return r

    res_core = tf.cond(T > 2, lambda: _core_residual(res), lambda: _all_residual(res))
    return tf.reduce_mean(tf.square(res_core))


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
    """
    Generate parameter combinations including variable Corey exponents.

    Default ranges:
      - no   in [2.0, 4.0] step 1.0
      - nw   in [2.0, 4.0] step 1.0
      - sor  in [0.10, 0.40] step 0.10
      - swc  in [0.10, 0.30] step 0.10
      - mu_o in [0.3,  1.0]  step 0.1
      - mu_w in [0.5, 50.0]  step 5.5
      - phi  in [0.10, 0.30] step 0.10
    """
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


def build_multi_case_fan_arrays(
    param_list: List[Dict],
    num_times: int = 6,
    t_min_days: float = 100.0,
) -> tuple:
    xi_list_all, Sw_list_all, p10_list_all = [], [], []
    tD_list_all, anchor_idxs_all, anchor_targs_all = [], [], []
    max_T, max_K = 0, 0

    for p in param_list:
        t_bt = breakthrough_time_days(p)
        if t_bt <= t_min_days:
            continue
        times = np.linspace(t_min_days, t_bt, num_times).tolist()
        fan_profiles = build_fan_profiles(times, p)

        for prof in fan_profiles:
            xi = np.asarray(prof["xi"], dtype=np.float32)
            Sw_true = np.asarray(prof["Sw_fan_true"], dtype=np.float32)
            tD = float(prof["t_D"])
            xD_star = float(prof["xD_star"])
            Sw_star = float(prof["Sw_star"])

            T_fan = len(xi)
            if T_fan > max_T:
                max_T = T_fan

            swc_val = float(p["swc"])
            sor_val = float(p["sor"])
            idxs_np, targs_np = make_fan_anchors_from_truth(
                xi, Sw_true, swc=swc_val, sor=sor_val, Sw_star=Sw_star
            )

            K_here = idxs_np.shape[0]
            if K_here > max_K:
                max_K = K_here

            p10 = np.array([
                p["no"], p["nw"], p["swc"], p["sor"],
                p["mu_w"], p["mu_o"], p["phi"],
                tD, xD_star, Sw_star,
            ], dtype=np.float32)

            xi_list_all.append(xi)
            Sw_list_all.append(Sw_true)
            p10_list_all.append(p10)
            tD_list_all.append(tD)
            anchor_idxs_all.append(idxs_np)
            anchor_targs_all.append(targs_np)

    if len(xi_list_all) == 0:
        raise RuntimeError("No valid fan profiles generated.")

    def pad_seq(arr, L):
        pad = L - len(arr)
        if pad <= 0:
            return arr[:L]
        return np.pad(arr, (0, pad), mode="edge")

    def pad_anchor(arr, L):
        pad = L - len(arr)
        if pad <= 0:
            return arr[:L]
        return np.pad(arr, (0, pad), mode="edge")

    xi_padded = [pad_seq(xi, max_T).reshape(-1, 1) for xi in xi_list_all]
    Sw_padded = [pad_seq(Sw, max_T).reshape(-1, 1) for Sw in Sw_list_all]
    anchor_idxs_padded = [pad_anchor(idx, max_K) for idx in anchor_idxs_all]
    anchor_targs_padded = [pad_anchor(targ, max_K) for targ in anchor_targs_all]

    xi_all = np.stack(xi_padded, axis=0).astype(np.float32)
    Sw_all = np.stack(Sw_padded, axis=0).astype(np.float32)
    p10_all = np.stack(p10_list_all, axis=0).astype(np.float32)
    tD_all = np.array(tD_list_all, dtype=np.float32)
    anchor_idxs_all = np.stack(anchor_idxs_padded, axis=0).astype(np.int32)
    anchor_targs_all = np.stack(anchor_targs_padded, axis=0).astype(np.float32)

    print(f"Multi-case dataset: N={xi_all.shape[0]} profiles, "
          f"T={xi_all.shape[1]}, K={anchor_idxs_all.shape[1]}")
    return xi_all, Sw_all, p10_all, tD_all, anchor_idxs_all, anchor_targs_all


def make_tf_datasets_from_arrays(
    xi_all, Sw_all, p10_all, tD_all, anchor_idxs_all, anchor_targs_all,
    train_frac: float = 0.8, batch_size: int = 8192,
    shuffle_buffer: int = 10_000, seed: int = 1337,
):
    N = xi_all.shape[0]
    rng = np.random.default_rng(seed)
    idx = np.arange(N)
    rng.shuffle(idx)
    N_train = int(train_frac * N)
    train_idx = idx[:N_train]
    test_idx = idx[N_train:]

    def _make_ds(sub_idx, shuffle=True):
        ds = tf.data.Dataset.from_tensor_slices((
            xi_all[sub_idx], Sw_all[sub_idx], p10_all[sub_idx],
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
    lr: float,
    log_every: int = 50,
) -> Dict[str, List[float]]:
    """
    Training loop that returns loss history for plotting.
    """
    optimizer = tf.keras.optimizers.Adam(lr)

    history = {
        'epoch': [], 'data': [], 'physics': [],
        'bc_inj': [], 'bc_tip': [], 'anchor': [],
        'mono': [], 'total': [],
    }

    for ep in range(1, epochs + 1):
        Ld_sum = Lp_sum = Lbc_inj_sum = Lbc_tip_sum = 0.0
        La_sum = Lmono_sum = Ltotal_sum = 0.0
        count_samples = 0.0

        for (xi_batch, S_true_batch, p_vec_batch, tD_batch,
             anchor_idxs_batch, anchor_targs_batch) in train_ds:

            B = tf.shape(xi_batch)[0]

            with tf.GradientTape() as tape:
                S_pred = model([xi_batch, p_vec_batch], training=True)

                Ld = data_loss(S_pred, S_true_batch)
                Lp = physics_loss_char(xi_batch, S_pred, S_true_batch,
                                       tD_batch, p_vec_batch, params_fixed)
                Lbc_inj = injector_bc_loss(S_pred, p_vec_batch)
                Lbc_tip = tip_bc_loss(S_pred, p_vec_batch)
                Lsh = shape_loss(S_pred, S_true_batch)
                La = anchor_loss(S_pred, anchor_idxs_batch, anchor_targs_batch)
                Lmono = monotonicity_loss(S_pred)

                L = (lambdas[0] * Ld + lambdas[1] * Lp + lambdas[2] * Lbc_inj
                     + lambda_tip * Lbc_tip + lambdas[3] * Lsh
                     + lambda_anchor * La + lambda_mono * Lmono)

            grads = tape.gradient(L, model.trainable_variables)
            optimizer.apply_gradients(zip(grads, model.trainable_variables))

            bsz = float(B.numpy())
            Ld_sum += float(Ld.numpy()) * bsz
            Lp_sum += float(Lp.numpy()) * bsz
            Lbc_inj_sum += float(Lbc_inj.numpy()) * bsz
            Lbc_tip_sum += float(Lbc_tip.numpy()) * bsz
            La_sum += float(La.numpy()) * bsz
            Lmono_sum += float(Lmono.numpy()) * bsz
            Ltotal_sum += float(L.numpy()) * bsz
            count_samples += bsz

        n = max(1.0, count_samples)
        history['epoch'].append(ep)
        history['data'].append(Ld_sum / n)
        history['physics'].append(Lp_sum / n)
        history['bc_inj'].append(Lbc_inj_sum / n)
        history['bc_tip'].append(Lbc_tip_sum / n)
        history['anchor'].append(La_sum / n)
        history['mono'].append(Lmono_sum / n)
        history['total'].append(Ltotal_sum / n)

        if ep % log_every == 0:
            print(f"[Multi-case] Epoch {ep:04d} | "
                  f"Data {Ld_sum/n:.3e} | Phys {Lp_sum/n:.3e} "
                  f"| BC_inj {Lbc_inj_sum/n:.3e} | BC_tip {Lbc_tip_sum/n:.3e} "
                  f"| Anchor {La_sum/n:.3e} | Mono {Lmono_sum/n:.3e}")

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
    """
    Plot training convergence with two panels:
      (a) Raw loss components (log scale)
      (b) Weighted contributions to total loss
    """
    epochs = history['epoch']

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Panel (a): Raw loss components
    ax1 = axes[0]
    ax1.semilogy(epochs, history['data'], label=r'$\mathcal{L}_{data}$', linewidth=2)
    ax1.semilogy(epochs, history['physics'], label=r'$\mathcal{L}_{physics}$', linewidth=2)
    ax1.semilogy(epochs, history['bc_inj'], label=r'$\mathcal{L}_{BC,inj}$', linewidth=2)
    ax1.semilogy(epochs, history['bc_tip'], label=r'$\mathcal{L}_{BC,tip}$', linewidth=2)
    ax1.semilogy(epochs, history['anchor'], label=r'$\mathcal{L}_{anchor}$', linewidth=2)
    ax1.semilogy(epochs, history['mono'], label=r'$\mathcal{L}_{mono}$', linewidth=2, linestyle='--')

    ax1.set_xlabel('Epoch', fontsize=12)
    ax1.set_ylabel('Loss (log scale)', fontsize=12)
    ax1.set_title('(a) Individual Loss Components', fontsize=13)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3, which='both')
    ax1.set_xlim([0, max(epochs)])

    # Panel (b): Weighted contributions
    ax2 = axes[1]

    data_weighted = [lambdas['data'] * v for v in history['data']]
    phys_weighted = [lambdas['physics'] * v for v in history['physics']]
    bc_inj_weighted = [lambdas['bc_inj'] * v for v in history['bc_inj']]
    bc_tip_weighted = [lambdas['bc_tip'] * v for v in history['bc_tip']]
    anchor_weighted = [lambdas['anchor'] * v for v in history['anchor']]
    mono_weighted = [lambdas['mono'] * v for v in history['mono']]

    ax2.semilogy(epochs, data_weighted,
                 label=rf'$\lambda_{{data}} \mathcal{{L}}_{{data}}$ ($\lambda$={lambdas["data"]})', linewidth=2)
    ax2.semilogy(epochs, phys_weighted,
                 label=rf'$\lambda_{{phys}} \mathcal{{L}}_{{phys}}$ ($\lambda$={lambdas["physics"]})', linewidth=2)
    ax2.semilogy(epochs, bc_inj_weighted,
                 label=rf'$\lambda_{{BC}} \mathcal{{L}}_{{BC,inj}}$ ($\lambda$={lambdas["bc_inj"]})', linewidth=2)
    ax2.semilogy(epochs, bc_tip_weighted,
                 label=rf'$\lambda_{{tip}} \mathcal{{L}}_{{BC,tip}}$ ($\lambda$={lambdas["bc_tip"]})', linewidth=2)
    ax2.semilogy(epochs, anchor_weighted,
                 label=rf'$\lambda_{{anc}} \mathcal{{L}}_{{anchor}}$ ($\lambda$={lambdas["anchor"]})', linewidth=2)
    ax2.semilogy(epochs, mono_weighted,
                 label=rf'$\lambda_{{mono}} \mathcal{{L}}_{{mono}}$ ($\lambda$={lambdas["mono"]})', linewidth=2, linestyle='--')
    ax2.semilogy(epochs, history['total'],
                 label=r'$\mathcal{L}_{total}$', linewidth=2.5, color='black', linestyle=':')

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

def predict_profile_fan(model: tf.keras.Model, p_case: dict,
                        t_days: float, build_fan_profiles_fn) -> dict:
    profiles = build_fan_profiles_fn([t_days], p_case)
    prof = profiles[0]

    xi = prof["xi"].astype(np.float32)
    t_D = float(prof["t_D"])
    xD_star = float(prof["xD_star"])
    Sw_star = float(prof["Sw_star"])

    p10 = np.array([[
        p_case["no"], p_case["nw"], p_case["swc"], p_case["sor"],
        p_case["mu_w"], p_case["mu_o"], p_case["phi"],
        t_D, xD_star, Sw_star
    ]], dtype=np.float32)

    xi_seq = xi.reshape(1, -1, 1)
    Sw_fan_pred = model([xi_seq, p10], training=False).numpy().squeeze()

    xD_fan = xi * xD_star
    xD_pred = np.concatenate([xD_fan, [xD_star, 1.0]])
    Sw_pred = np.concatenate([Sw_fan_pred, [p_case["swc"], p_case["swc"]]])

    xD_true, Sw_true_true, meta = profile_at_time(t_days, p_case)

    return {
        "xD_true": xD_true, "Sw_true_true": Sw_true_true,
        "xD_pred": xD_pred, "Sw_pred": Sw_pred,
        "t_days": float(t_days), "t_D": float(t_D),
        "xD_star_true": float(meta["xD_shock"]),
    }


def plot_profile_fan(xD_true, Sw_true_true, xD_pred, Sw_pred,
                     t_days, t_D, xD_star_true) -> None:
    plt.figure(figsize=(8, 5))
    plt.plot(xD_true, Sw_true_true, label="True BL", linewidth=2)
    plt.plot(xD_pred, Sw_pred, "--", label="PI-RNN Pred", linewidth=2)
    plt.axvline(xD_star_true, color="k", linestyle=":", linewidth=1, label="Shock")
    plt.title(f"t = {t_days:.1f} days (t_D = {t_D:.3f})")
    plt.xlabel("$x_D$")
    plt.ylabel("$S_w$")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


def evaluate_times_fan_case(model, p_case, times, build_fan_profiles_fn):
    try:
        import pandas as pd
    except ImportError:
        return None

    rows = []
    for t in times:
        res = predict_profile_fan(model, p_case, float(t), build_fan_profiles_fn)
        xD_true, Sw_true = res["xD_true"], res["Sw_true_true"]
        xD_pred, Sw_pred = res["xD_pred"], res["Sw_pred"]
        Sw_pred_interp = np.interp(xD_true, xD_pred, Sw_pred)
        err = Sw_pred_interp - Sw_true
        rows.append({
            "t_days": res["t_days"], "t_D": res["t_D"],
            "xD_star_true": res["xD_star_true"],
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
# DIAGNOSTIC PLOTTING FUNCTIONS
# ==============================================================================

def compute_residuals_over_times(
    model: tf.keras.Model,
    p_case: dict,
    times: list,
    n_x: int = 200,
) -> dict:
    """
    Compute residuals (S_pred - S_true) over multiple times on a common x_D grid.

    Returns dict with xD_grid, residuals, Sw_true_all, Sw_pred_all, xD_star_all
    """
    xD_grid = np.linspace(0.0, 1.0, n_x)

    residuals_all = []
    Sw_true_all = []
    Sw_pred_all = []
    xD_star_all = []

    for t_days in times:
        # Get true profile
        xD_true, Sw_true_full, meta = profile_at_time(float(t_days), p_case)
        xD_star = float(meta['xD_shock'])
        xD_star_all.append(xD_star)

        # Get fan profile for prediction
        fan_profiles = build_fan_profiles([t_days], p_case)
        fan = fan_profiles[0]

        xi = fan["xi"].astype(np.float32)
        t_D = float(fan["t_D"])
        Sw_star = float(fan["Sw_star"])

        # Build conditioner
        p10 = np.array([[
            p_case["no"], p_case["nw"], p_case["swc"], p_case["sor"],
            p_case["mu_w"], p_case["mu_o"], p_case["phi"],
            t_D, xD_star, Sw_star
        ]], dtype=np.float32)

        # Predict
        xi_seq = xi.reshape(1, -1, 1)
        Sw_fan_pred = model([xi_seq, p10], training=False).numpy().squeeze()

        # Reconstruct full profile
        xD_fan = xi * xD_star
        xD_pred_full = np.concatenate([xD_fan, [xD_star, 1.0]])
        Sw_pred_full = np.concatenate([Sw_fan_pred, [p_case["swc"], p_case["swc"]]])

        # Interpolate both onto common grid
        Sw_true_interp = np.interp(xD_grid, xD_true, Sw_true_full)
        Sw_pred_interp = np.interp(xD_grid, xD_pred_full, Sw_pred_full)

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
    case_name: str = "",
    save_path: str = None,
    figsize: tuple = (12, 10),
):
    """
    Generate 4-panel diagnostic figure:
      (a) Residual vs. position showing maximum errors at shock front
      (b) Residual histogram with near-zero mean
      (c) Q-Q plot confirming approximately normal error distribution
      (d) Parity plot with R² demonstrating prediction accuracy
    """
    # Compute residuals
    data = compute_residuals_over_times(model, p_case, times)

    xD_grid = data['xD_grid']
    residuals = data['residuals']  # [n_times, n_x]
    Sw_true_all = data['Sw_true_all']
    Sw_pred_all = data['Sw_pred_all']
    xD_star_all = data['xD_star_all']

    # Flatten for histogram and Q-Q
    residuals_flat = residuals.flatten()
    Sw_true_flat = Sw_true_all.flatten()
    Sw_pred_flat = Sw_pred_all.flatten()

    # Compute statistics
    mean_res = np.mean(residuals_flat)
    std_res = np.std(residuals_flat)

    # R² for parity plot
    ss_res = np.sum((Sw_true_flat - Sw_pred_flat) ** 2)
    ss_tot = np.sum((Sw_true_flat - np.mean(Sw_true_flat)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=figsize)

    # =========================================================================
    # (a) Residual vs. position
    # =========================================================================
    ax1 = axes[0, 0]

    cmap = plt.cm.viridis
    n_times = len(times)

    for i, (t, res, xD_star) in enumerate(zip(times, residuals, xD_star_all)):
        color = cmap(i / max(1, n_times - 1))
        ax1.plot(xD_grid, res, color=color, alpha=0.7, linewidth=1.5,
                 label=f't = {t:.0f} d' if i % max(1, n_times // 5) == 0 else None)
        ax1.axvline(xD_star, color=color, linestyle=':', alpha=0.3, linewidth=1)

    # Mean residual envelope
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

    # Annotation for shock region
    mean_xD_star = np.mean(xD_star_all)
    ylim = ax1.get_ylim()
    ax1.annotate('Shock front\nregion', xy=(mean_xD_star, ylim[1]*0.7),
                 fontsize=9, ha='center', style='italic', color='gray')

    # =========================================================================
    # (b) Residual histogram
    # =========================================================================
    ax2 = axes[0, 1]

    n_bins = 50
    counts, bins, patches = ax2.hist(residuals_flat, bins=n_bins, density=True,
                                      alpha=0.7, color='steelblue', edgecolor='white')

    # Fit normal distribution
    x_norm = np.linspace(residuals_flat.min(), residuals_flat.max(), 200)
    pdf_norm = stats.norm.pdf(x_norm, mean_res, std_res)
    ax2.plot(x_norm, pdf_norm, 'r-', linewidth=2,
             label=f'Normal fit\n$\\mu$={mean_res:.2e}\n$\\sigma$={std_res:.2e}')

    ax2.axvline(mean_res, color='red', linestyle='--', linewidth=1.5, label='Mean')
    ax2.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)

    ax2.set_xlabel('Residual $(S_w^{pred} - S_w^{true})$', fontsize=11)
    ax2.set_ylabel('Probability Density', fontsize=11)
    ax2.set_title('(b) Residual Distribution', fontsize=12, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # Statistics text box
    textstr = f'n = {len(residuals_flat)}\nMean = {mean_res:.2e}\nStd = {std_res:.2e}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax2.text(0.05, 0.95, textstr, transform=ax2.transAxes, fontsize=9,
             verticalalignment='top', bbox=props)

    # =========================================================================
    # (c) Q-Q plot
    # =========================================================================
    ax3 = axes[1, 0]

    (osm, osr), (slope, intercept, r) = stats.probplot(residuals_flat, dist="norm")

    ax3.scatter(osm, osr, alpha=0.5, s=10, c='steelblue', label='Residuals')

    x_line = np.array([osm.min(), osm.max()])
    y_line = slope * x_line + intercept
    ax3.plot(x_line, y_line, 'r-', linewidth=2, label=f'Normal fit (r={r:.4f})')

    ax3.set_xlabel('Theoretical Quantiles', fontsize=11)
    ax3.set_ylabel('Sample Quantiles', fontsize=11)
    ax3.set_title('(c) Normal Q-Q Plot', fontsize=12, fontweight='bold')
    ax3.legend(loc='lower right', fontsize=9)
    ax3.grid(True, alpha=0.3)

    # Shapiro-Wilk test
    if len(residuals_flat) > 5000:
        sample_idx = np.random.choice(len(residuals_flat), 5000, replace=False)
        stat, p_value = stats.shapiro(residuals_flat[sample_idx])
    else:
        stat, p_value = stats.shapiro(residuals_flat)

    ax3.text(0.05, 0.95, f'Shapiro-Wilk\np = {p_value:.3f}',
             transform=ax3.transAxes, fontsize=9,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # =========================================================================
    # (d) Parity plot
    # =========================================================================
    ax4 = axes[1, 1]

    # Subsample for clarity
    if len(Sw_true_flat) > 5000:
        idx = np.random.choice(len(Sw_true_flat), 5000, replace=False)
        Sw_true_plot = Sw_true_flat[idx]
        Sw_pred_plot = Sw_pred_flat[idx]
    else:
        Sw_true_plot = Sw_true_flat
        Sw_pred_plot = Sw_pred_flat

    ax4.scatter(Sw_true_plot, Sw_pred_plot, alpha=0.3, s=5, c='steelblue')

    sw_min = min(Sw_true_flat.min(), Sw_pred_flat.min())
    sw_max = max(Sw_true_flat.max(), Sw_pred_flat.max())
    ax4.plot([sw_min, sw_max], [sw_min, sw_max], 'r-', linewidth=2, label='Perfect prediction')

    # ±5% error bands
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

    # R² annotation
    ax4.text(0.05, 0.95, f'$R^2$ = {r_squared:.6f}', transform=ax4.transAxes,
             fontsize=12, fontweight='bold', verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    # Overall title
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

    # Print summary
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

    # --- Generate parameter grid (with variable Corey exponents) ---
    print("\n" + "="*60)
    print("GENERATING PARAMETER GRID")
    print("="*60)
    print("Corey exponents: n_o ∈ [2,3,4], n_w ∈ [2,3,4]")
    param_list = generate_param_grid(base_p)

    # --- Build multi-case arrays ---
    print("\n" + "="*60)
    print("BUILDING MULTI-CASE FAN ARRAYS")
    print("="*60)
    xi_all, Sw_all, p10_all, tD_all, anchor_idxs_all, anchor_targs_all = \
        build_multi_case_fan_arrays(param_list, num_times=6, t_min_days=100.0)

    # --- Build train/test datasets ---
    print("\n" + "="*60)
    print("CREATING TRAIN/TEST DATASETS")
    print("="*60)
    train_ds, test_ds = make_tf_datasets_from_arrays(
        xi_all, Sw_all, p10_all, tD_all, anchor_idxs_all, anchor_targs_all,
        train_frac=0.8, batch_size=8192,
        shuffle_buffer=P.train.shuffle_buffer, seed=P.train.seed,
    )

    # --- Build model ---
    model = build_model(
        input_features=1, param_dim=P.param_dim(),
        hidden=P.train.hidden, layers=P.train.layers,
    )

    params_fixed = {
        "mu_w": P.rock.mu_w, "mu_o": P.rock.mu_o,
        "krw_max": P.rock.krw_max, "kro_max": P.rock.kro_max,
    }

    # --- Train with history logging ---
    print("\n" + "="*60)
    print("TRAINING MULTI-CASE PI-RNN")
    print("="*60)
    history = train_pi_rnn_from_dataset_with_history(
        model, params_fixed, train_ds,
        epochs=P.train.epochs,
        lambdas=(P.train.lambda_data, P.train.lambda_phys,
                 P.train.lambda_bc, P.train.lambda_shape),
        lambda_anchor=P.train.lambda_anchor,
        lambda_tip=P.train.lambda_tip,
        lambda_mono=P.train.lambda_mono,
        lr=P.train.lr, log_every=50,
    )

    # --- Plot convergence ---
    print("\n" + "="*60)
    print("PLOTTING TRAINING CONVERGENCE")
    print("="*60)
    lambdas_dict = {
        'data': P.train.lambda_data, 'physics': P.train.lambda_phys,
        'bc_inj': P.train.lambda_bc, 'bc_tip': P.train.lambda_tip,
        'anchor': P.train.lambda_anchor, 'mono': P.train.lambda_mono,
    }

    plot_training_convergence(
        history, lambdas_dict,
        save_path='training_convergence_multicase_corey.png'
    )

    # --- Save weights and config ---
    model.save_weights("pi_rnn_fan_multicase_corey.weights.h5")
    print("Saved weights to pi_rnn_fan_multicase_corey.weights.h5")

    import json
    with open("pi_rnn_fan_multicase_corey_config.json", "w") as f:
        json.dump({
            "hidden": P.train.hidden, "layers": P.train.layers,
            "param_dim": P.param_dim(), "seed": P.train.seed,
            "condition_on": list(P.train.condition_on),
            "no_range": [2.0, 4.0, 1.0],
            "nw_range": [2.0, 4.0, 1.0],
            "sor_range": [0.10, 0.40, 0.10],
            "swc_range": [0.10, 0.30, 0.10],
            "mu_o_range": [0.3, 1.0, 0.1],
            "mu_w_range": [0.5, 50.0, 5.5],
            "phi_range": [0.10, 0.30, 0.10],
            "num_times": 6,
        }, f)
    print("Saved config to pi_rnn_fan_multicase_corey_config.json")

    # --- Model summary ---
    print("\n" + "="*60)
    print("MODEL SUMMARY")
    print("="*60)
    model.summary()

    # --- Test cases ---
    print("\n" + "="*60)
    print("TEST CASES")
    print("="*60)

    # Case 1: Symmetric Corey (baseline)
    p_case_1 = make_case_from_values(
        base_p, no=2.0, nw=2.0, swc=0.20, sor=0.20,
        mu_w=0.5, mu_o=0.7, phi=0.20,
    )

    # Case 2: Asymmetric Corey
    p_case_2 = make_case_from_values(
        base_p, no=3.0, nw=2.0, swc=0.15, sor=0.25,
        mu_w=6.0, mu_o=0.9, phi=0.25,
    )

    cases = [("Case 1 (symmetric n_o=n_w=2)", p_case_1),
             ("Case 2 (asymmetric n_o=3, n_w=2)", p_case_2)]

    for case_name, p_case in cases:
        print(f"\n{'='*50}")
        print(case_name)
        print('='*50)
        for k in ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi"]:
            print(f"  {k} = {p_case[k]}")

        t_bt = breakthrough_time_days(p_case)
        times = np.linspace(100.0, t_bt, 15).tolist()
        idxs_5 = np.linspace(0, len(times) - 1, 5, dtype=int)
        selected_times = [times[i] for i in idxs_5]

        print(f"Plotting at times: {[f'{t:.1f}' for t in selected_times]}")

        for t in selected_times:
            res = predict_profile_fan(model, p_case, float(t), build_fan_profiles)
            plot_profile_fan(
                res["xD_true"], res["Sw_true_true"],
                res["xD_pred"], res["Sw_pred"],
                res["t_days"], res["t_D"], res["xD_star_true"],
            )

        df = evaluate_times_fan_case(model, p_case, times, build_fan_profiles)
        if df is not None:
            print(f"\nMetrics for {case_name}:")
            print(df.to_string(index=False))

    # --- Diagnostic panels ---
    print("\n" + "="*60)
    print("DIAGNOSTIC ANALYSIS")
    print("="*60)

    # Case 1 diagnostics
    t_bt_1 = breakthrough_time_days(p_case_1)
    times_diag_1 = np.linspace(100.0, t_bt_1, 15).tolist()

    fig1, stats1 = plot_diagnostic_panels(
        model, p_case_1, times_diag_1,
        case_name="Case 1: Symmetric Corey ($n_o = n_w = 2$)",
        save_path="diagnostic_case1_symmetric.png"
    )

    # Case 2 diagnostics
    t_bt_2 = breakthrough_time_days(p_case_2)
    times_diag_2 = np.linspace(100.0, t_bt_2, 15).tolist()

    fig2, stats2 = plot_diagnostic_panels(
        model, p_case_2, times_diag_2,
        case_name="Case 2: Asymmetric Corey ($n_o = 3, n_w = 2$)",
        save_path="diagnostic_case2_asymmetric.png"
    )