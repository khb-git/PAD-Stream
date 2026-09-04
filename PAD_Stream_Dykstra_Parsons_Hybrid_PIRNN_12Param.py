# =============================================================================
# PHASE 1: LAYER DEFINITIONS & BUCKLEY-LEVERETT PER LAYER
# (Updated for 12-parameter PI-RNN with layer-specific krw_max/kro_max)
# =============================================================================

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

FT3_PER_BBL = 5.615
EPS = 1e-12

# -----------------------------------------------------------------------------
# 1.0 SHARED PARAMETERS (System-Wide)
# -----------------------------------------------------------------------------

@dataclass
class SharedParams:
    """System-wide parameters (constant across all layers)."""
    no: float = 2.0
    nw: float = 2.0
    sor: float = 0.2
    mu_w: float = 0.5
    mu_o: float = 0.7           # Within PI-RNN training range [0.3, 1.0]
    A_ft2: float = 160000.0
    x_ip_ft: float = 2000.0
    L_ft: float = 625.0
    q_total: float = 1000.0
    Bo: float = 1.25
    Bw: float = 1.02
    # NOTE: krw_max and kro_max removed from SharedParams
    #       Now layer-specific in LayerProperties


# -----------------------------------------------------------------------------
# 1.1 LAYER PROPERTIES
# -----------------------------------------------------------------------------

@dataclass
class LayerProperties:
    """Properties for a single layer."""
    layer_id: int
    h_ft: float
    k_md: float
    phi: float
    swc: float
    krw_max: float              # ADDED: Layer-specific endpoint
    kro_max: float              # ADDED: Layer-specific endpoint

    # Computed properties
    Ri: float = 0.0
    q_layer: float = 0.0


# -----------------------------------------------------------------------------
# 1.2 BUILD LAYERS FROM YOUR FORMATION
# -----------------------------------------------------------------------------

def build_layers_from_formation(shared: SharedParams) -> List[LayerProperties]:
    """
    Build layer list from your exact 8-layer formation.
    Now includes layer-specific krw_max and kro_max values.
    """
    data = {
        'Layer No.': [1, 2, 3, 4, 5, 6, 7, 8],
        'Height (ft)': [50, 48, 54, 44, 42, 48, 50, 40],
        'Permeability (mD)': [174, 103, 487, 73, 141, 904, 1223, 160],
        'Porosity': [0.22, 0.18, 0.21, 0.22, 0.18, 0.21, 0.20, 0.20],
        'Swc': [0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42],
        # ADDED: Layer-specific endpoint relative permeabilities
        'kro_max': [0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60],
        'krw_max': [0.05, 0.15, 0.20, 0.33, 0.05, 0.30, 0.40, 0.17],
    }

    layers = []
    for i in range(8):
        layer = LayerProperties(
            layer_id=data['Layer No.'][i],
            h_ft=data['Height (ft)'][i],
            k_md=data['Permeability (mD)'][i],
            phi=data['Porosity'][i],
            swc=data['Swc'][i],
            krw_max=data['krw_max'][i],  # ADDED
            kro_max=data['kro_max'][i],  # ADDED
        )
        delta_S = 1.0 - layer.swc - shared.sor
        layer.Ri = (layer.k_md * layer.h_ft) / (layer.phi * delta_S)
        layers.append(layer)

    # Allocate flow rates proportional to k*h
    total_kh = sum(L.k_md * L.h_ft for L in layers)
    for layer in layers:
        layer.q_layer = shared.q_total * (layer.k_md * layer.h_ft) / total_kh

    return layers


# -----------------------------------------------------------------------------
# 1.3 BUILD p_case FOR ANALYTICAL FUNCTIONS
# -----------------------------------------------------------------------------

def build_layer_p_case(layer: LayerProperties, shared: SharedParams) -> Dict:
    """
    Build Case-3 compatible p_case dict for a single layer.
    Now uses LAYER-SPECIFIC krw_max/kro_max (for 12-param PI-RNN).
    """
    return {
        'no': shared.no,
        'nw': shared.nw,
        'swc': layer.swc,           # Layer-specific
        'sor': shared.sor,
        'mu_w': shared.mu_w,
        'mu_o': shared.mu_o,
        'krw_max': layer.krw_max,   # CHANGED: Layer-specific (was shared)
        'kro_max': layer.kro_max,   # CHANGED: Layer-specific (was shared)
        'phi': layer.phi,           # Layer-specific
        'A': shared.A_ft2,
        'x_ip': shared.x_ip_ft,
        'i_w': layer.q_layer,       # Layer-specific allocated flow
        'bw': shared.Bw,
        'bo': shared.Bo,
        'injector_at_left': True,
    }


# -----------------------------------------------------------------------------
# 1.4 LAYER BL RESULT (for Phase 2 composite)
# -----------------------------------------------------------------------------

@dataclass
class LayerBLResult:
    """Buckley-Leverett results for a single layer."""
    layer_id: int
    t_BT_days: float
    Sw_star: float
    fw_star: float

    # Time series (layer PVI basis)
    t_days: np.ndarray = field(default_factory=lambda: np.array([]))
    PVI_layer: np.ndarray = field(default_factory=lambda: np.array([]))
    Np_layer_STB: np.ndarray = field(default_factory=lambda: np.array([]))
    Wp_layer_STB: np.ndarray = field(default_factory=lambda: np.array([]))
    fw_layer: np.ndarray = field(default_factory=lambda: np.array([]))
    qo_layer: np.ndarray = field(default_factory=lambda: np.array([]))
    qw_layer: np.ndarray = field(default_factory=lambda: np.array([]))
    WOR_layer: np.ndarray = field(default_factory=lambda: np.array([]))

    def PVI_to_system_PVI(self, layer_PV: float, system_PV: float) -> np.ndarray:
        """Convert layer PVI to system PVI."""
        return self.PVI_layer * (layer_PV / system_PV)


# -----------------------------------------------------------------------------
# MAIN: Build shared params and layers
# -----------------------------------------------------------------------------

shared = SharedParams()
layers = build_layers_from_formation(shared)

print("=" * 80)
print("PHASE 1: Layer Properties (Layer-Specific krw_max/kro_max for 12-param PI-RNN)")
print("=" * 80)
print(f"{'Layer':<8}{'k (mD)':<10}{'h (ft)':<10}{'φ':<8}{'Swc':<8}{'krw_max':<10}{'kro_max':<10}{'Ri':<12}{'q (bbl/d)':<12}")
print("-" * 100)
for L in sorted(layers, key=lambda x: x.layer_id):
    print(f"{L.layer_id:<8}{L.k_md:<10.0f}{L.h_ft:<10.0f}{L.phi:<8.2f}{L.swc:<8.2f}"
          f"{L.krw_max:<10.2f}{L.kro_max:<10.2f}{L.Ri:<12.1f}{L.q_layer:<12.1f}")
print("-" * 100)
print(f"Shared: no={shared.no}, nw={shared.nw}, sor={shared.sor}, mu_w={shared.mu_w}, mu_o={shared.mu_o}")

# =============================================================================
# PHASE 2: DYKSTRA-PARSONS COMPOSITE PRODUCTION
# =============================================================================

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict

# -----------------------------------------------------------------------------
# 2.0 ANALYTICAL FUNCTIONS (from Case 3)
# -----------------------------------------------------------------------------

def validate_params(p: Dict) -> None:
    required = ("nw", "no", "mu_w", "mu_o", "swc", "sor", "krw_max", "kro_max", "phi", "A", "x_ip", "i_w")
    missing = [k for k in required if k not in p]
    if missing:
        raise KeyError(f"Missing: {missing}")
    assert 0.0 <= p["swc"] < 1.0 and 0.0 <= p["sor"] < 1.0
    assert (p["swc"] + p["sor"]) < 1.0


def calculate_relative_permeability_np(sw, so, p):
    swc, sor = p['swc'], p['sor']
    denom = max(EPS, 1.0 - swc - sor)
    sw_norm = np.clip((sw - swc) / denom, 0.0, 1.0)
    so_norm = np.clip((so - sor) / denom, 0.0, 1.0)
    krw = p['krw_max'] * (sw_norm ** p['nw'])
    kro = p['kro_max'] * (so_norm ** p['no'])
    return krw, kro


def fractional_flow_np(Sw, p, eps=EPS):
    So = 1.0 - Sw
    krw, kro = calculate_relative_permeability_np(Sw, So, p)
    fw = 1.0 / (1.0 + (p['mu_w'] / p['mu_o']) * (kro / (krw + eps)))
    return fw


def dfw_dsw_np(Sw, p):
    fw = fractional_flow_np(Sw, p)
    d_fw = np.gradient(fw, Sw)
    return d_fw, fw


def welge_tangent(Sw_grid, fw, swc, eps=EPS):
    slopes = np.full_like(Sw_grid, -np.inf, dtype=float)
    denom = Sw_grid - swc
    valid = denom > 0.0
    slopes[valid] = fw[valid] / (denom[valid] + eps)
    diffs = np.diff(slopes)
    neg_idx = np.where(diffs < 0.0)[0]
    tangent_idx = int(neg_idx[0]) if len(neg_idx) > 0 else int(np.argmax(slopes))
    return float(Sw_grid[tangent_idx]), float(fw[tangent_idx]), float(slopes[tangent_idx]), tangent_idx


def breakthrough_time_days(p, Sw_grid=None):
    validate_params(p)
    if Sw_grid is None:
        Sw_grid = np.linspace(p['swc'], 1.0 - p['sor'], 400)
    d_fw, fw = dfw_dsw_np(Sw_grid, p)
    Sw_star, fw_star, slope_star, _ = welge_tangent(Sw_grid, fw, p['swc'])
    Sw_at_fw1 = p['swc'] + 1.0 / max(EPS, slope_star)
    Q_iBT = Sw_at_fw1 - p['swc']
    PV_rb = (p['phi'] * p['A'] * p['x_ip']) / FT3_PER_BBL
    PV_STB = PV_rb / p.get('bw', 1.02)
    W_iBT = Q_iBT * PV_STB
    return W_iBT / p['i_w']


# -----------------------------------------------------------------------------
# 2.1 SINGLE LAYER BL PRODUCTION
# -----------------------------------------------------------------------------

def compute_layer_bl_production(layer: LayerProperties, shared: SharedParams,
                                 t_max_days: float, n_points: int = 500) -> LayerBLResult:
    """Compute BL production for a single layer."""
    p_case = build_layer_p_case(layer, shared)

    Sw_grid = np.linspace(p_case['swc'], 1.0 - p_case['sor'], 400)
    d_fw, fw = dfw_dsw_np(Sw_grid, p_case)
    Sw_star, fw_star, slope_star, _ = welge_tangent(Sw_grid, fw, p_case['swc'])

    t_BT = breakthrough_time_days(p_case, Sw_grid)

    # Layer pore volume
    PV_rb = (layer.phi * shared.A_ft2 * shared.x_ip_ft) / FT3_PER_BBL
    PV_STB = PV_rb / shared.Bw

    # Mobile oil
    delta_S = 1.0 - layer.swc - shared.sor
    OOIP_layer = PV_STB * delta_S / shared.Bo

    t_days = np.linspace(1.0, t_max_days, n_points)
    Wi_STB = layer.q_layer * t_days
    PVI_layer = Wi_STB / PV_STB

    # Initialize arrays
    Np_STB = np.zeros_like(t_days)
    fw_arr = np.zeros_like(t_days)
    Sw_avg = np.zeros_like(t_days)

    PVI_BT = t_BT * layer.q_layer / PV_STB

    for i, pvi in enumerate(PVI_layer):
        if pvi <= PVI_BT:
            # Pre-breakthrough: piston-like
            Np_STB[i] = Wi_STB[i] / shared.Bo
            fw_arr[i] = 0.0
            Sw_avg[i] = layer.swc + pvi * delta_S
        else:
            # Post-breakthrough: Welge
            Np_STB[i] = min(OOIP_layer, PVI_BT * PV_STB / shared.Bo +
                           (pvi - PVI_BT) * PV_STB * (1 - fw_star) / shared.Bo)

            # Find Sw at outlet from fw curve
            target_slope = 1.0 / max(EPS, pvi)
            idx = np.argmin(np.abs(d_fw - target_slope))
            Sw_outlet = Sw_grid[idx]
            fw_arr[i] = fractional_flow_np(np.array([Sw_outlet]), p_case)[0]

    Wp_STB = Wi_STB / shared.Bw - Np_STB * shared.Bo / shared.Bw
    Wp_STB = np.maximum(0, Wp_STB)

    qo = np.gradient(Np_STB, t_days)
    qw = np.gradient(Wp_STB, t_days)
    qo = np.maximum(0, qo)
    qw = np.maximum(0, qw)

    WOR = np.divide(qw, qo, out=np.zeros_like(qw), where=qo > 1e-6)

    return LayerBLResult(
        layer_id=layer.layer_id,
        t_BT_days=t_BT,
        Sw_star=Sw_star,
        fw_star=fw_star,
        t_days=t_days,
        PVI_layer=PVI_layer,
        Np_layer_STB=Np_STB,
        Wp_layer_STB=Wp_STB,
        fw_layer=fw_arr,
        qo_layer=qo,
        qw_layer=qw,
        WOR_layer=WOR,
    )


# -----------------------------------------------------------------------------
# 2.2 COMPOSITE DP SYSTEM RESULT
# -----------------------------------------------------------------------------

@dataclass
class DPSystemResult:
    """Composite Dykstra-Parsons system results."""
    t_days: np.ndarray
    PVI_system: np.ndarray
    Np_total_STB: np.ndarray
    Wp_total_STB: np.ndarray
    qo_total: np.ndarray
    qw_total: np.ndarray
    fw_system: np.ndarray
    WOR_system: np.ndarray
    Recovery_factor: np.ndarray
    layer_results: List[LayerBLResult] = field(default_factory=list)


def composite_dp_production(layers: List[LayerProperties], shared: SharedParams,
                            t_max_days: float = None, n_points: int = 500) -> DPSystemResult:
    """Compute composite DP production from all layers."""

    # Compute each layer's BL production
    layer_results = []
    t_BT_max = 0.0

    for layer in layers:
        p_case = build_layer_p_case(layer, shared)
        t_BT = breakthrough_time_days(p_case)
        t_BT_max = max(t_BT_max, t_BT)

    if t_max_days is None:
        t_max_days = t_BT_max * 1.5

    for layer in layers:
        result = compute_layer_bl_production(layer, shared, t_max_days, n_points)
        layer_results.append(result)

    # Common time grid
    t_days = layer_results[0].t_days

    # System pore volume
    system_PV_rb = sum(L.phi * shared.A_ft2 * shared.x_ip_ft for L in layers) / FT3_PER_BBL
    system_PV_STB = system_PV_rb / shared.Bw

    # System OOIP
    system_OOIP = sum(
        (L.phi * shared.A_ft2 * shared.x_ip_ft / FT3_PER_BBL / shared.Bw) *
        (1.0 - L.swc - shared.sor) / shared.Bo
        for L in layers
    )

    # Sum layer contributions
    Np_total = np.zeros_like(t_days)
    Wp_total = np.zeros_like(t_days)

    for result in layer_results:
        Np_total += result.Np_layer_STB
        Wp_total += result.Wp_layer_STB

    Wi_total = shared.q_total * t_days
    PVI_system = Wi_total / system_PV_STB

    qo_total = np.gradient(Np_total, t_days)
    qw_total = np.gradient(Wp_total, t_days)
    qo_total = np.maximum(0, qo_total)
    qw_total = np.maximum(0, qw_total)

    q_total_liquid = qo_total + qw_total
    fw_system = np.divide(qw_total, q_total_liquid,
                          out=np.zeros_like(qw_total), where=q_total_liquid > 1e-6)

    WOR_system = np.divide(qw_total, qo_total,
                           out=np.zeros_like(qw_total), where=qo_total > 1e-6)

    RF = Np_total / system_OOIP

    return DPSystemResult(
        t_days=t_days,
        PVI_system=PVI_system,
        Np_total_STB=Np_total,
        Wp_total_STB=Wp_total,
        qo_total=qo_total,
        qw_total=qw_total,
        fw_system=fw_system,
        WOR_system=WOR_system,
        Recovery_factor=RF,
        layer_results=layer_results,
    )


# -----------------------------------------------------------------------------
# MAIN: Compute composite production
# -----------------------------------------------------------------------------

print("\n" + "=" * 80)
print("PHASE 2: Computing Composite DP Production")
print("=" * 80)

dp_result = composite_dp_production(layers, shared)

print(f"\nSystem Results:")
print(f"  Max time: {dp_result.t_days[-1]:.0f} days")
print(f"  Final Np: {dp_result.Np_total_STB[-1]:,.0f} STB")
print(f"  Final RF: {dp_result.Recovery_factor[-1]*100:.1f}%")

print(f"\nLayer Breakthrough Times:")
for lr in sorted(dp_result.layer_results, key=lambda x: x.t_BT_days):
    print(f"  Layer {lr.layer_id}: t_BT = {lr.t_BT_days:.0f} days")

# =============================================================================
# PHASE 3: PI-RNN INTEGRATION (12-PARAMETER MODEL - Layer-Specific krw_max/kro_max)
# =============================================================================

import numpy as np
import tensorflow as tf
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import pandas as pd

# -----------------------------------------------------------------------------
# 3.0 VALIDATED ANALYTICAL FUNCTIONS (FROM CASE 3 PI-RNN)
# -----------------------------------------------------------------------------

FT3_PER_BBL = 5.615
EPS = 1e-12

# Required keys for parameter dict
REQUIRED_KEYS = (
    "nw", "no", "mu_w", "mu_o", "swc", "sor", "krw_max", "kro_max",
    "phi", "A", "x_ip", "i_w",
)

def validate_params(p: Dict) -> None:
    """Validate parameter dict for BL calculations."""
    missing = [k for k in REQUIRED_KEYS if k not in p]
    if missing:
        raise KeyError(f"Missing required parameter(s): {missing}")

    assert 0.0 <= p["swc"] < 1.0, "swc must be in [0,1)"
    assert 0.0 <= p["sor"] < 1.0, "sor must be in [0,1)"
    assert (p["swc"] + p["sor"]) < 1.0, "swc + sor must be < 1"
    assert (1.0 - p["swc"] - p["sor"]) > EPS, "1 - swc - sor must be > 0"
    assert p["mu_w"] > 0.0 and p["mu_o"] > 0.0, "viscosities must be > 0"
    assert p["nw"] > 0.0 and p["no"] > 0.0, "Corey exponents must be > 0"
    assert 0.0 < p["krw_max"] <= 1.0 and 0.0 < p["kro_max"] <= 1.0, "endpoint kr must be in (0,1]"
    assert 0.0 < p["phi"] < 1.0, "phi must be in (0,1)"
    for k in ("A", "x_ip", "i_w"):
        assert p[k] > 0.0, f"{k} must be > 0"


def calculate_relative_permeability_np(sw_local: np.ndarray,
                                       so_local: np.ndarray,
                                       p: Dict) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate relative permeabilities using Corey model."""
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
    """Calculate fractional flow curve."""
    So = 1.0 - Sw
    mu_w, mu_o = p['mu_w'], p['mu_o']
    krw, kro = calculate_relative_permeability_np(Sw, So, p)
    viscosity_ratio = mu_w / mu_o
    perm_term = kro / (krw + eps)
    fw = 1.0 / (1.0 + viscosity_ratio * perm_term)
    return fw


def dfw_dsw_np(Sw: np.ndarray, p: Dict) -> Tuple[np.ndarray, np.ndarray]:
    """Numerical derivative dfw/dSw using numpy.gradient, plus fw itself."""
    fw = fractional_flow_np(Sw, p)
    d_fw = np.gradient(fw, Sw)
    return d_fw, fw


def welge_tangent(Sw_grid: np.ndarray, fw: np.ndarray, swc: float,
                  eps: float = EPS) -> Tuple[float, float, float, int]:
    """
    Welge tangent finder based on slope sequence and its first decrease.
    Returns (Sw*, fw*, slope*, index_on_grid).
    """
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


def calculate_x_sw(i_w: float, t: float, phi: float, A: float,
                   derivative: np.ndarray) -> np.ndarray:
    """Calculate characteristic distance x(Sw,t) using fractional flow derivative."""
    return ((5.615 * i_w * t) / (phi * A)) * derivative


def profile_at_time(
    t_days: float,
    p: Dict,
    Sw_grid: np.ndarray = None,
    add_plateau_points: int = 12
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Build the analytical BL profile at time t_days.
    Returns: xD_full, Sw_full, meta with segments for plotting.
    """
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

    # Left rarefaction
    x_left = xD[start_idx:end_idx + 1]
    S_left = Sw_grid[start_idx:end_idx + 1]
    ord_left = np.argsort(x_left)
    x_left = x_left[ord_left]
    S_left = S_left[ord_left]
    if x_left[0] > 0.0:
        x_left = np.insert(x_left, 0, 0.0)
        S_left = np.insert(S_left, 0, 1.0 - p['sor'])

    # Right plateau
    x_right = np.linspace(front_x_D, 1.0, add_plateau_points)
    S_right = np.full_like(x_right, p['swc'])

    # Shock marker
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
        'Sw_star': float(Sw_star),
        'fw_star': float(fw_star),
        'slope': float(slope_star),
        'xD_shock': float(front_x_D),
        't_days': float(t_days),
        't_D': float(t_D),
        'segments': {
            'rarefaction_left': (x_left, S_left),
            'shock_vertical': (x_shock, S_shock),
            'plateau_right': (x_right, S_right),
        }
    }
    return xD_full, Sw_full, meta


def build_fan_profiles(times_days: List[float], p: Dict,
                       Sw_grid: np.ndarray = None) -> List[Dict]:
    """
    Return only the left rarefaction fan, normalized by xD*:
      xi = x_left / xD_star in [0,1], Sw_fan_true aligned accordingly.
    """
    out = []
    for t in times_days:
        xD_full, Sw_full, meta = profile_at_time(float(t), p, Sw_grid=Sw_grid)
        xD_star = float(meta['xD_shock'])
        Sw_star = float(meta['Sw_star'])

        x_left, S_left = meta['segments']['rarefaction_left']
        xi = np.asarray(x_left, dtype=float) / max(EPS, xD_star)
        xi = np.clip(xi, 0.0, 1.0)

        out.append({
            't_days': float(meta['t_days']),
            't_D': float(meta['t_D']),
            'xi': xi.astype(np.float32),
            'Sw_fan_true': np.asarray(S_left, dtype=np.float32),
            'xD_star': xD_star,
            'Sw_star': Sw_star,
        })
    return out


def breakthrough_time_days(p: Dict, Sw_grid: np.ndarray = None) -> float:
    """Estimate t_BT (days) using Welge method."""
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


# -----------------------------------------------------------------------------
# 3.1 HELPER: BUILD LAYER-SPECIFIC P_CASE DICT
# -----------------------------------------------------------------------------

def build_layer_p_case(layer: 'LayerProperties', shared: 'SharedParams') -> Dict:
    """
    Build a parameter dict for a single layer compatible with profile_at_time().

    This creates a p_case with:
    - Layer-specific: swc, phi, i_w (= q_layer), krw_max, kro_max
    - Shared: no, nw, sor, mu_w, mu_o, A, x_ip

    NOTE: krw_max and kro_max are now LAYER-SPECIFIC for 12-param PI-RNN.
    """
    return {
        'no': shared.no,
        'nw': shared.nw,
        'swc': layer.swc,
        'sor': shared.sor,
        'mu_w': shared.mu_w,
        'mu_o': shared.mu_o,
        'krw_max': layer.krw_max,  # CHANGED: Layer-specific (was shared)
        'kro_max': layer.kro_max,  # CHANGED: Layer-specific (was shared)
        'phi': layer.phi,
        'A': shared.A_ft2,
        'x_ip': shared.x_ip_ft,
        'i_w': layer.q_layer,  # Layer's allocated flow rate
        'bw': shared.Bw,
        'bo': shared.Bo,
        'injector_at_left': True,
    }


# -----------------------------------------------------------------------------
# 3.2 PI-RNN MODEL LOADING (12-PARAMETER VERSION)
# -----------------------------------------------------------------------------

def load_pirnn_model(weights_path: str, config_path: Optional[str] = None) -> tf.keras.Model:
    """
    Load trained PI-RNN model with range_map layer.

    12-parameter conditioning vector layout:
      [no, nw, swc, sor, mu_w, mu_o, phi, krw_max, kro_max, tD, xD_star, Sw_star]
       0    1    2    3    4     5    6      7        8      9    10       11
    """
    # Updated defaults for 12-param model
    seq_length = 143      # UPDATED: Check your actual trained seq_length
    param_dim = 12        # UPDATED: Was 10
    hidden_units = 64
    num_layers = 2

    if config_path is not None:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        seq_length = config.get('seq_length', seq_length)
        param_dim = config.get('param_dim', param_dim)
        hidden_units = config.get('hidden', hidden_units)
        num_layers = config.get('layers', num_layers)

    # Build model architecture (must match training architecture)
    xi_input = tf.keras.Input(shape=(seq_length, 1), name='xi_input')
    param_input = tf.keras.Input(shape=(param_dim,), name='param_input')

    param_expanded = tf.keras.layers.RepeatVector(seq_length)(param_input)
    combined = tf.keras.layers.Concatenate(axis=-1)([xi_input, param_expanded])

    x = combined
    for i in range(num_layers):
        x = tf.keras.layers.LSTM(hidden_units, return_sequences=True)(x)

    z_out = tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(1))(x)

    # Range map to [swc, 1 - sor]
    # NOTE: swc is still at index 2, sor at index 3 in 12-param layout
    def range_map(args):
        z_raw, p = args
        swc = p[:, :, 2:3]  # Index 2 unchanged
        sor = p[:, :, 3:4]  # Index 3 unchanged
        span = tf.maximum(1e-8, 1.0 - swc - sor)
        return swc + span * tf.math.sigmoid(z_raw)

    output = tf.keras.layers.Lambda(range_map, name="range_map")([z_out, param_expanded])

    model = tf.keras.Model(inputs=[xi_input, param_input], outputs=output)
    model.load_weights(weights_path)

    print(f"Loaded PI-RNN weights from: {weights_path}")
    print(f"  Architecture: {num_layers} LSTM layers, {hidden_units} units")
    print(f"  param_dim={param_dim}, seq_length={seq_length}")
    print(f"  12-param layout: [no, nw, swc, sor, mu_w, mu_o, phi, krw_max, kro_max, tD, xD*, Sw*]")

    return model


# -----------------------------------------------------------------------------
# 3.3 PI-RNN INFERENCE FUNCTIONS (12-PARAMETER VERSION)
# -----------------------------------------------------------------------------

def predict_saturation_profile_pirnn(
    model: tf.keras.Model,
    layer: 'LayerProperties',
    shared: 'SharedParams',
    t_days: float,
    n_xi_points: int = 145  # UPDATED: Match trained seq_length
) -> Dict:
    """
    Run PI-RNN inference for a single layer at a single time.
    Uses validated build_fan_profiles() to get analytical xD_star and Sw_star.

    NOTE: Model output is ALREADY in [swc, 1-sor] range due to range_map layer.

    12-parameter conditioning vector:
      [no, nw, swc, sor, mu_w, mu_o, phi, krw_max, kro_max, tD, xD_star, Sw_star]
    """
    # Build layer-specific p_case (now includes layer-specific krw_max/kro_max)
    p_case = build_layer_p_case(layer, shared)

    # Get analytical fan profile for this time (provides xD_star, Sw_star)
    fan_profiles = build_fan_profiles([t_days], p_case)
    fan = fan_profiles[0]

    xD_star = float(fan['xD_star'])
    Sw_star = float(fan['Sw_star'])
    t_D = float(fan['t_D'])

    # Normalized coordinate for fan (fixed grid for model input)
    xi = np.linspace(0, 1, n_xi_points).astype(np.float32)

    # Build 12-element conditioning vector
    # [no, nw, swc, sor, mu_w, mu_o, phi, krw_max, kro_max, tD, xD_star, Sw_star]
    p12 = np.array([[
        shared.no,           # 0
        shared.nw,           # 1
        layer.swc,           # 2
        shared.sor,          # 3
        shared.mu_w,         # 4
        shared.mu_o,         # 5
        layer.phi,           # 6
        layer.krw_max,       # 7  ADDED
        layer.kro_max,       # 8  ADDED
        t_D,                 # 9
        xD_star,             # 10
        Sw_star,             # 11
    ]], dtype=np.float32)

    # Run inference
    xi_seq = xi.reshape(1, -1, 1)
    Sw_fan_pred = model([xi_seq, p12], training=False).numpy().squeeze()

    # Map xi to physical xD coordinates
    xD_fan = xi * xD_star

    return {
        'xi': xi,
        'xD_fan': xD_fan,
        'Sw_fan': Sw_fan_pred,  # No denormalization needed - model handles it
        'xD_star': xD_star,
        'Sw_star': Sw_star,
        't_days': t_days,
        't_D': t_D,
        'swc': layer.swc,
        'sor': shared.sor,
        'krw_max': layer.krw_max,  # ADDED for debugging
        'kro_max': layer.kro_max,  # ADDED for debugging
    }


def integrate_saturation_profile(profile: Dict) -> Tuple[float, float]:
    """Integrate saturation profile to get average saturation and recovery."""
    xD_fan = profile['xD_fan']
    Sw_fan = profile['Sw_fan']
    xD_star = profile['xD_star']
    swc = profile['swc']
    sor = profile['sor']

    if len(xD_fan) > 1 and xD_star > 0:
        integral_fan = np.trapz(Sw_fan, xD_fan)
    else:
        integral_fan = 0.0

    integral_plateau = swc * max(0, 1 - xD_star)
    sw_avg = integral_fan + integral_plateau

    mobile_saturation = 1 - sor - swc
    if mobile_saturation > 0:
        recovery_frac = (sw_avg - swc) / mobile_saturation
    else:
        recovery_frac = 0.0

    return sw_avg, np.clip(recovery_frac, 0.0, 1.0)


# -----------------------------------------------------------------------------
# 3.4 VISUALIZATION: SATURATION PROFILES (ANALYTICAL vs PI-RNN)
# -----------------------------------------------------------------------------

def plot_saturation_profiles_comparison(
    model: tf.keras.Model,
    layers: List['LayerProperties'],
    shared: 'SharedParams',
    n_times: int = 5,
    n_layers_to_plot: int = 8,
    n_xi_points: int = 145  # UPDATED: Match trained seq_length
):
    """
    Plot Analytical vs PI-RNN saturation profiles for all layers.

    - Solid lines: Analytical (validated profile_at_time)
    - Dashed lines: PI-RNN predictions

    Now uses layer-specific krw_max/kro_max for both analytical and PI-RNN.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    # Sort layers by Ri (highest first)
    layers_sorted = sorted(layers, key=lambda x: x.Ri, reverse=True)[:n_layers_to_plot]

    # Determine grid layout
    n_cols = min(4, n_layers_to_plot)
    n_rows = (n_layers_to_plot + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
    if n_layers_to_plot == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)
    elif n_cols == 1:
        axes = axes.reshape(-1, 1)
    axes = axes.flatten()

    for idx, layer in enumerate(layers_sorted):
        ax = axes[idx]
        lid = layer.layer_id

        # Build layer-specific p_case (now with layer krw_max/kro_max)
        p_case = build_layer_p_case(layer, shared)

        # Get breakthrough time for this layer
        t_bt = breakthrough_time_days(p_case)

        # Times to plot (fractions of breakthrough)
        time_fracs = np.linspace(0.2, 0.95, n_times)
        colors = plt.cm.viridis(np.linspace(0.2, 0.9, n_times))

        for t_frac, color in zip(time_fracs, colors):
            t_days = t_frac * t_bt

            # ----- ANALYTICAL PROFILE -----
            xD_anal, Sw_anal, meta = profile_at_time(t_days, p_case)
            Sw_star = meta['Sw_star']

            # Extract segments
            x_left, S_left = meta['segments']['rarefaction_left']
            x_shock, S_shock = meta['segments']['shock_vertical']
            x_right, S_right = meta['segments']['plateau_right']

            # Plot analytical (solid)
            ax.plot(x_left, S_left, color=color, linewidth=2, linestyle='-', alpha=0.9)
            ax.plot(x_shock, S_shock, color=color, linewidth=2, linestyle='-', alpha=0.9)
            ax.plot(x_right, S_right, color=color, linewidth=2, linestyle='-', alpha=0.9)

            # ----- PI-RNN PROFILE -----
            profile = predict_saturation_profile_pirnn(
                model, layer, shared, t_days, n_xi_points=n_xi_points
            )

            xD_fan = profile['xD_fan']
            Sw_fan = profile['Sw_fan']
            xD_star = profile['xD_star']
            swc = profile['swc']

            # Plot PI-RNN (dashed)
            ax.plot(xD_fan, Sw_fan, color=color, linewidth=2, linestyle='--', alpha=0.9)
            ax.plot([xD_star, xD_star], [swc, Sw_star], color=color, linewidth=2, linestyle='--', alpha=0.9)
            ax.plot([xD_star, 1.0], [swc, swc], color=color, linewidth=2, linestyle='--', alpha=0.9)

        ax.set_xlabel('$x_D$', fontsize=11)
        ax.set_ylabel('$S_w$', fontsize=11)
        # UPDATED: Show krw_max/kro_max in title
        ax.set_title(f'Layer {lid} (Swc={layer.swc:.2f}, krw={layer.krw_max:.2f}, kro={layer.kro_max:.2f})',
                     fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 1.05)
        ax.set_ylim(layer.swc - 0.05, 1 - shared.sor + 0.05)

        # Legend on first subplot only
        if idx == 0:
            legend_elements = [
                Line2D([0], [0], color='black', linestyle='-', linewidth=2, label='Analytical'),
                Line2D([0], [0], color='black', linestyle='--', linewidth=2, label='PI-RNN'),
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

    # Hide unused subplots
    for idx in range(len(layers_sorted), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle('Saturation Profiles: Analytical vs PI-RNN (Layer-Specific kr Endpoints)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

    # Print layer summary
    print("\n" + "=" * 90)
    print("LAYER SUMMARY (sorted by Ri) - 12-param PI-RNN with layer-specific endpoints")
    print("=" * 90)
    print(f"{'Layer':<8}{'Ri':<10}{'k (mD)':<10}{'h (ft)':<10}{'φ':<8}{'Swc':<8}"
          f"{'krw_max':<10}{'kro_max':<10}{'t_BT (days)':<12}")
    print("-" * 90)
    for layer in layers_sorted:
        p_case = build_layer_p_case(layer, shared)
        t_bt = breakthrough_time_days(p_case)
        print(f"{layer.layer_id:<8}{layer.Ri:<10.0f}{layer.k_md:<10.0f}{layer.h_ft:<10.0f}"
              f"{layer.phi:<8.2f}{layer.swc:<8.2f}{layer.krw_max:<10.2f}{layer.kro_max:<10.2f}"
              f"{t_bt:<12.1f}")


def plot_parity_by_layer(
    model: tf.keras.Model,
    layers: List['LayerProperties'],
    shared: 'SharedParams',
    n_layers_to_plot: int = 4,
    n_xi_points: int = 145  # UPDATED: Match trained seq_length
):
    """
    Parity plots comparing Analytical vs PI-RNN saturation values for selected layers.
    Now uses layer-specific krw_max/kro_max.
    """
    import matplotlib.pyplot as plt

    layers_sorted = sorted(layers, key=lambda x: x.Ri, reverse=True)[:n_layers_to_plot]

    n_cols = min(4, n_layers_to_plot)
    n_rows = (n_layers_to_plot + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 5*n_rows))
    if n_layers_to_plot == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    xi_common = np.linspace(0, 1, n_xi_points).astype(np.float32)

    overall_rmse = []
    overall_r2 = []

    for idx, layer in enumerate(layers_sorted):
        ax = axes[idx]
        lid = layer.layer_id

        p_case = build_layer_p_case(layer, shared)
        t_bt = breakthrough_time_days(p_case)

        sw_anal_all = []
        sw_pirnn_all = []

        for t_frac in np.linspace(0.1, 0.95, 20):
            t_days = t_frac * t_bt

            # Analytical fan profile
            fan_profiles = build_fan_profiles([t_days], p_case)
            fan = fan_profiles[0]
            xi_anal = fan['xi']
            Sw_fan_anal = fan['Sw_fan_true']

            # Interpolate onto common grid
            Sw_anal_interp = np.interp(xi_common, xi_anal, Sw_fan_anal)

            # PI-RNN prediction
            profile = predict_saturation_profile_pirnn(
                model, layer, shared, t_days, n_xi_points=n_xi_points
            )
            Sw_fan_pirnn = profile['Sw_fan']

            sw_anal_all.extend(Sw_anal_interp)
            sw_pirnn_all.extend(Sw_fan_pirnn)

        sw_anal_all = np.array(sw_anal_all)
        sw_pirnn_all = np.array(sw_pirnn_all)

        ax.scatter(sw_anal_all, sw_pirnn_all, alpha=0.3, s=5, c='blue')

        min_sw = min(sw_anal_all.min(), sw_pirnn_all.min())
        max_sw = max(sw_anal_all.max(), sw_pirnn_all.max())
        ax.plot([min_sw, max_sw], [min_sw, max_sw], 'r--', linewidth=2, label='1:1')

        # Statistics
        rmse = np.sqrt(np.mean((sw_pirnn_all - sw_anal_all)**2))
        ss_tot = np.sum((sw_anal_all - sw_anal_all.mean())**2)
        ss_res = np.sum((sw_pirnn_all - sw_anal_all)**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        overall_rmse.append(rmse)
        overall_r2.append(r2)

        ax.set_xlabel('Analytical $S_w$', fontsize=11)
        ax.set_ylabel('PI-RNN $S_w$', fontsize=11)
        # UPDATED: Show krw_max/kro_max in title
        ax.set_title(f'Layer {lid} (krw={layer.krw_max:.2f}, kro={layer.kro_max:.2f})\n'
                     f'RMSE={rmse:.4f}, R²={r2:.4f}', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        ax.set_xlim(min_sw - 0.02, max_sw + 0.02)
        ax.set_ylim(min_sw - 0.02, max_sw + 0.02)

    # Hide unused subplots
    for idx in range(len(layers_sorted), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle('Parity Plots: Analytical vs PI-RNN (12-param with layer-specific kr)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

    # Print overall statistics
    print("\n" + "=" * 50)
    print("OVERALL STATISTICS (12-param PI-RNN)")
    print("=" * 50)
    print(f"Mean RMSE: {np.mean(overall_rmse):.5f}")
    print(f"Mean R²:   {np.mean(overall_r2):.5f}")


# =============================================================================
# PHASE 3 MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    from tabulate import tabulate

    # SharedParams - NOTE: krw_max/kro_max REMOVED (now layer-specific)
    shared = SharedParams(
        mu_w=0.5,
        mu_o=0.7,           # Within training range [0.3, 1.0]
        Bo=1.25,
        Bw=1.02,
        A_ft2=160000.0,
        x_ip_ft=2000.0,
        q_total=1000.0,
        sor=0.2,
        no=2.0,
        nw=2.0,
        # krw_max and kro_max REMOVED - now in LayerProperties
    )

    print("Building layers (with layer-specific krw_max/kro_max)...")
    layers = build_layers_from_formation(shared)

    # Load PI-RNN Model
    print("\n" + "=" * 80)
    print("PHASE 3: Loading 12-Parameter PI-RNN Model")
    print("=" * 80)

    weights_path = "pi_rnn_fan_dp_12param.weights.h5"
    config_path = "pi_rnn_fan_dp_12param_config.json"

    try:
        model = load_pirnn_model(weights_path, config_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Using analytical model only for demonstration...")
        model = None

    # Run Visualization
    if model is not None:
        print("\n" + "=" * 80)
        print("Generating saturation profile comparison plots...")
        print("=" * 80)

        print("\n[Plot 1] Saturation Profiles: Analytical vs PI-RNN (all 8 layers)...")
        plot_saturation_profiles_comparison(model, layers, shared, n_times=5, n_layers_to_plot=8)

        print("\n[Plot 2] Parity Plots by Layer...")
        plot_parity_by_layer(model, layers, shared, n_layers_to_plot=4)

        print("\n" + "=" * 80)
        print("PHASE 3 COMPLETE!")
        print("=" * 80)

    else:
        print("\nSkipping PI-RNN comparison (model not loaded)")
        print("To run Phase 3, ensure weights file exists at:", weights_path)

# =============================================================================
# PHASE 3B: PI-RNN COMPOSITE PRODUCTION & COMPARISON PLOTS
# (Updated for 12-parameter PI-RNN with layer-specific krw_max/kro_max)
# (Fixed for dynamic layer counts in synthetic formations)
# =============================================================================

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

# -----------------------------------------------------------------------------
# 3B.1 PI-RNN LAYER BL PRODUCTION
# -----------------------------------------------------------------------------

def compute_layer_bl_production_pirnn(
    layer: LayerProperties,
    shared: SharedParams,
    model: tf.keras.Model,
    t_max_days: float,
    n_points: int = 500,
    n_xi_points: int = 145
) -> LayerBLResult:
    """
    Compute BL production for a single layer using PI-RNN for pre-breakthrough.
    Post-breakthrough uses standard Welge analytical solution.

    Now uses layer-specific krw_max/kro_max via build_layer_p_case().
    """
    p_case = build_layer_p_case(layer, shared)

    Sw_grid = np.linspace(p_case['swc'], 1.0 - p_case['sor'], 400)
    d_fw, fw = dfw_dsw_np(Sw_grid, p_case)
    Sw_star, fw_star, slope_star, _ = welge_tangent(Sw_grid, fw, p_case['swc'])

    t_BT = breakthrough_time_days(p_case, Sw_grid)

    # Layer pore volume
    PV_rb = (layer.phi * shared.A_ft2 * shared.x_ip_ft) / FT3_PER_BBL
    PV_STB = PV_rb / shared.Bw

    # Mobile oil
    delta_S = 1.0 - layer.swc - shared.sor
    OOIP_layer = PV_STB * delta_S / shared.Bo

    t_days = np.linspace(1.0, t_max_days, n_points)
    Wi_STB = layer.q_layer * t_days
    PVI_layer = Wi_STB / PV_STB

    # Initialize arrays
    Np_STB = np.zeros_like(t_days)
    fw_arr = np.zeros_like(t_days)

    PVI_BT = t_BT * layer.q_layer / PV_STB

    for i, (t, pvi) in enumerate(zip(t_days, PVI_layer)):
        if pvi <= PVI_BT:
            # Pre-breakthrough: Use PI-RNN saturation profile
            profile = predict_saturation_profile_pirnn(
                model, layer, shared, t, n_xi_points=n_xi_points
            )
            sw_avg, recovery_frac = integrate_saturation_profile(profile)

            Np_STB[i] = recovery_frac * OOIP_layer
            fw_arr[i] = 0.0
        else:
            # Post-breakthrough: Welge analytical
            Np_STB[i] = min(OOIP_layer, PVI_BT * PV_STB / shared.Bo +
                           (pvi - PVI_BT) * PV_STB * (1 - fw_star) / shared.Bo)

            # Find Sw at outlet from fw curve
            target_slope = 1.0 / max(EPS, pvi)
            idx = np.argmin(np.abs(d_fw - target_slope))
            Sw_outlet = Sw_grid[idx]
            fw_arr[i] = fractional_flow_np(np.array([Sw_outlet]), p_case)[0]

    Wp_STB = Wi_STB / shared.Bw - Np_STB * shared.Bo / shared.Bw
    Wp_STB = np.maximum(0, Wp_STB)

    qo = np.gradient(Np_STB, t_days)
    qw = np.gradient(Wp_STB, t_days)
    qo = np.maximum(0, qo)
    qw = np.maximum(0, qw)

    WOR = np.divide(qw, qo, out=np.zeros_like(qw), where=qo > 1e-6)

    return LayerBLResult(
        layer_id=layer.layer_id,
        t_BT_days=t_BT,
        Sw_star=Sw_star,
        fw_star=fw_star,
        t_days=t_days,
        PVI_layer=PVI_layer,
        Np_layer_STB=Np_STB,
        Wp_layer_STB=Wp_STB,
        fw_layer=fw_arr,
        qo_layer=qo,
        qw_layer=qw,
        WOR_layer=WOR,
    )


def composite_dp_production_pirnn(
    layers: List[LayerProperties],
    shared: SharedParams,
    model: tf.keras.Model,
    t_max_days: float = None,
    n_points: int = 500,
    n_xi_points: int = 145
) -> DPSystemResult:
    """
    Compute composite DP production using PI-RNN for pre-breakthrough.
    Now uses layer-specific krw_max/kro_max (12-param model).
    """

    # Find max breakthrough time
    t_BT_max = 0.0
    for layer in layers:
        p_case = build_layer_p_case(layer, shared)
        t_BT = breakthrough_time_days(p_case)
        t_BT_max = max(t_BT_max, t_BT)

    if t_max_days is None:
        t_max_days = t_BT_max * 1.5

    # Compute each layer's production with PI-RNN
    layer_results = []
    for layer in layers:
        print(f"  Layer {layer.layer_id} (krw={layer.krw_max:.2f}, kro={layer.kro_max:.2f})...",
              end=" ", flush=True)
        result = compute_layer_bl_production_pirnn(
            layer, shared, model, t_max_days, n_points, n_xi_points
        )
        layer_results.append(result)
        print(f"t_BT={result.t_BT_days:.0f} days")

    # Common time grid
    t_days = layer_results[0].t_days

    # System pore volume
    system_PV_rb = sum(L.phi * shared.A_ft2 * shared.x_ip_ft for L in layers) / FT3_PER_BBL
    system_PV_STB = system_PV_rb / shared.Bw

    # System OOIP
    system_OOIP = sum(
        (L.phi * shared.A_ft2 * shared.x_ip_ft / FT3_PER_BBL / shared.Bw) *
        (1.0 - L.swc - shared.sor) / shared.Bo
        for L in layers
    )

    # Sum layer contributions
    Np_total = np.zeros_like(t_days)
    Wp_total = np.zeros_like(t_days)

    for result in layer_results:
        Np_total += result.Np_layer_STB
        Wp_total += result.Wp_layer_STB

    Wi_total = shared.q_total * t_days
    PVI_system = Wi_total / system_PV_STB

    qo_total = np.gradient(Np_total, t_days)
    qw_total = np.gradient(Wp_total, t_days)
    qo_total = np.maximum(0, qo_total)
    qw_total = np.maximum(0, qw_total)

    q_total_liquid = qo_total + qw_total
    fw_system = np.divide(qw_total, q_total_liquid,
                          out=np.zeros_like(qw_total), where=q_total_liquid > 1e-6)

    WOR_system = np.divide(qw_total, qo_total,
                           out=np.zeros_like(qw_total), where=qo_total > 1e-6)

    RF = Np_total / system_OOIP

    return DPSystemResult(
        t_days=t_days,
        PVI_system=PVI_system,
        Np_total_STB=Np_total,
        Wp_total_STB=Wp_total,
        qo_total=qo_total,
        qw_total=qw_total,
        fw_system=fw_system,
        WOR_system=WOR_system,
        Recovery_factor=RF,
        layer_results=layer_results,
    )


# -----------------------------------------------------------------------------
# 3B.2 INDIVIDUAL COMPARISON PLOTS
# -----------------------------------------------------------------------------

def plot_recovery_factor_comparison(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult):
    """Plot 1: Recovery Factor vs System PVI."""
    plt.figure(figsize=(10, 6))
    plt.plot(dp_anal.PVI_system, dp_anal.Recovery_factor * 100,
             'b-', linewidth=2, label='Analytical')
    plt.plot(dp_pirnn.PVI_system, dp_pirnn.Recovery_factor * 100,
             'r--', linewidth=2, label='PI-RNN (12-param)')
    plt.xlabel('System PVI', fontsize=14)
    plt.ylabel('Volumetric Displacement', fontsize=14)
    plt.title('Volumetric Displacement: Analytical vs PI-RNN (Layer-Specific kr Endpoints)', fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, dp_anal.PVI_system.max())
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()


def plot_water_cut_comparison(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult):
    """Plot 2: System Water Cut vs System PVI."""
    plt.figure(figsize=(10, 6))
    plt.plot(dp_anal.PVI_system, dp_anal.fw_system * 100,
             'b-', linewidth=2, label='Analytical')
    plt.plot(dp_pirnn.PVI_system, dp_pirnn.fw_system * 100,
             'r--', linewidth=2, label='PI-RNN (12-param)')
    plt.xlabel('System PVI', fontsize=14)
    plt.ylabel('Water Cut (%)', fontsize=14)
    plt.title('System Water Cut: Analytical vs PI-RNN (Layer-Specific kr Endpoints)', fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, dp_anal.PVI_system.max())
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()


def plot_cumulative_oil_comparison(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult, shared: SharedParams):
    """Plot 3: Cumulative Oil vs Cumulative Water Injected."""
    Wi_anal = shared.q_total * dp_anal.t_days
    Wi_pirnn = shared.q_total * dp_pirnn.t_days

    plt.figure(figsize=(10, 6))
    plt.plot(Wi_anal, dp_anal.Np_total_STB,
             'b-', linewidth=2, label='Analytical')
    plt.plot(Wi_pirnn, dp_pirnn.Np_total_STB,
             'r--', linewidth=2, label='PI-RNN (12-param)')
    plt.xlabel('Cumulative Water Injected (STB)', fontsize=14)
    plt.ylabel('Cumulative Oil Produced (STB)', fontsize=14)
    plt.title('Cumulative Oil vs Water Injection', fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.ticklabel_format(style='scientific', axis='both', scilimits=(0, 0))
    plt.tight_layout()
    plt.show()


def plot_recovery_difference(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult):
    """Plot 4: Recovery Factor Difference (PI-RNN - Analytical)."""
    rf_diff = (dp_pirnn.Recovery_factor - dp_anal.Recovery_factor) * 100

    plt.figure(figsize=(10, 6))
    plt.plot(dp_anal.PVI_system, rf_diff, 'k-', linewidth=2)
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    plt.xlabel('System PVI', fontsize=14)
    plt.ylabel('Recovery Difference (PI-RNN - Analytical) [%]', fontsize=14)
    plt.title('Recovery Factor Difference (12-param PI-RNN)', fontsize=16)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, dp_anal.PVI_system.max())
    plt.tight_layout()
    plt.show()

    # Print statistics
    print(f"\nRecovery Difference Statistics (12-param PI-RNN):")
    print(f"  Max difference: {rf_diff.max():.4f}%")
    print(f"  Min difference: {rf_diff.min():.4f}%")
    print(f"  Mean difference: {rf_diff.mean():.4f}%")
    print(f"  Std difference: {rf_diff.std():.4f}%")


def plot_layer_recovery_comparison(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult,
                                   layers: List[LayerProperties], shared: SharedParams):
    """Plot 5: Per-Layer Recovery Comparison (dynamic grid for any number of layers)."""
    layers_sorted = sorted(layers, key=lambda x: x.Ri, reverse=True)
    n_layers = len(layers_sorted)

    # Dynamic grid sizing
    n_cols = min(4, n_layers)
    n_rows = (n_layers + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))

    # Handle single row/col cases
    if n_layers == 1:
        axes = np.array([axes])
    elif n_rows == 1 and n_cols > 1:
        axes = axes.reshape(1, -1)
    elif n_cols == 1 and n_rows > 1:
        axes = axes.reshape(-1, 1)
    axes = np.array(axes).flatten()

    for i, layer in enumerate(layers_sorted):
        lid = layer.layer_id
        ax = axes[i]

        # Find matching layer results
        lr_anal = next(lr for lr in dp_anal.layer_results if lr.layer_id == lid)
        lr_pirnn = next(lr for lr in dp_pirnn.layer_results if lr.layer_id == lid)

        # Compute layer recovery factor
        p_case = build_layer_p_case(layer, shared)
        PV_rb = (layer.phi * shared.A_ft2 * shared.x_ip_ft) / FT3_PER_BBL
        PV_STB = PV_rb / shared.Bw
        delta_S = 1.0 - layer.swc - shared.sor
        OOIP_layer = PV_STB * delta_S / shared.Bo

        rf_anal = lr_anal.Np_layer_STB / OOIP_layer * 100
        rf_pirnn = lr_pirnn.Np_layer_STB / OOIP_layer * 100

        ax.plot(lr_anal.PVI_layer, rf_anal, 'b-', linewidth=2, label='Analytical')
        ax.plot(lr_pirnn.PVI_layer, rf_pirnn, 'r--', linewidth=2, label='PI-RNN')

        # Mark breakthrough
        PVI_BT = lr_anal.t_BT_days * layer.q_layer / PV_STB
        ax.axvline(x=PVI_BT, color='g', linestyle=':', alpha=0.7, label='BT')

        ax.set_xlabel('Layer PVI', fontsize=10)
        ax.set_ylabel('Recovery (%)', fontsize=10)
        ax.set_title(f'Layer {lid} (krw={layer.krw_max:.2f}, kro={layer.kro_max:.2f})', fontsize=10)
        ax.legend(fontsize=8, loc='lower right')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 2)
        ax.set_ylim(0, 105)

    # Hide unused subplots
    for idx in range(n_layers, len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle(f'Per-Layer Recovery: Analytical vs PI-RNN ({n_layers} layers)', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()


def plot_recovery_parity(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult):
    """Plot 6: Recovery Factor Parity Plot."""
    rf_anal = dp_anal.Recovery_factor * 100
    rf_pirnn = dp_pirnn.Recovery_factor * 100

    plt.figure(figsize=(8, 8))
    scatter = plt.scatter(rf_anal, rf_pirnn, c=dp_anal.PVI_system, cmap='viridis',
                          alpha=0.7, s=20, edgecolors='none')

    max_val = max(rf_anal.max(), rf_pirnn.max())
    plt.plot([0, max_val], [0, max_val], 'r--', linewidth=2, label='1:1 Line')

    plt.xlabel('Analytical Recovery Factor (%)', fontsize=14)
    plt.ylabel('PI-RNN Recovery Factor (%)', fontsize=14)
    plt.title('Recovery Factor Parity (12-param PI-RNN)', fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, max_val * 1.05)
    plt.ylim(0, max_val * 1.05)
    plt.gca().set_aspect('equal')

    cbar = plt.colorbar(scatter)
    cbar.set_label('System PVI', fontsize=12)

    plt.tight_layout()
    plt.show()

    # Statistics
    rmse = np.sqrt(np.mean((rf_pirnn - rf_anal)**2))
    mae = np.mean(np.abs(rf_pirnn - rf_anal))
    ss_tot = np.sum((rf_anal - rf_anal.mean())**2)
    ss_res = np.sum((rf_pirnn - rf_anal)**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    print(f"\nRecovery Factor Parity Statistics (12-param PI-RNN):")
    print(f"  RMSE: {rmse:.4f}%")
    print(f"  MAE:  {mae:.4f}%")
    print(f"  R²:   {r2:.6f}")


def plot_water_cut_parity(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult):
    """Plot 7: Water Cut Parity Plot."""
    wc_anal = dp_anal.fw_system * 100
    wc_pirnn = dp_pirnn.fw_system * 100

    plt.figure(figsize=(8, 8))
    scatter = plt.scatter(wc_anal, wc_pirnn, c=dp_anal.PVI_system, cmap='viridis',
                          alpha=0.7, s=20, edgecolors='none')

    plt.plot([0, 100], [0, 100], 'r--', linewidth=2, label='1:1 Line')

    plt.xlabel('Analytical Water Cut (%)', fontsize=14)
    plt.ylabel('PI-RNN Water Cut (%)', fontsize=14)
    plt.title('Water Cut Parity (12-param PI-RNN)', fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 105)
    plt.ylim(0, 105)
    plt.gca().set_aspect('equal')

    cbar = plt.colorbar(scatter)
    cbar.set_label('System PVI', fontsize=12)

    plt.tight_layout()
    plt.show()

    # Statistics
    rmse = np.sqrt(np.mean((wc_pirnn - wc_anal)**2))
    mae = np.mean(np.abs(wc_pirnn - wc_anal))
    ss_tot = np.sum((wc_anal - wc_anal.mean())**2)
    ss_res = np.sum((wc_pirnn - wc_anal)**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    print(f"\nWater Cut Parity Statistics (12-param PI-RNN):")
    print(f"  RMSE: {rmse:.4f}%")
    print(f"  MAE:  {mae:.4f}%")
    print(f"  R²:   {r2:.6f}")


def plot_wor_comparison(dp_anal: DPSystemResult, dp_pirnn: DPSystemResult):
    """Plot 8: Water-Oil Ratio vs System PVI."""
    plt.figure(figsize=(10, 6))
    plt.semilogy(dp_anal.PVI_system, dp_anal.WOR_system + 0.01,
                 'b-', linewidth=2, label='Analytical')
    plt.semilogy(dp_pirnn.PVI_system, dp_pirnn.WOR_system + 0.01,
                 'r--', linewidth=2, label='PI-RNN (12-param)')
    plt.xlabel('System PVI', fontsize=14)
    plt.ylabel('Water-Oil Ratio (WOR)', fontsize=14)
    plt.title('Water-Oil Ratio: Analytical vs PI-RNN (Layer-Specific kr)', fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3, which='both')
    plt.xlim(0, dp_anal.PVI_system.max())
    plt.tight_layout()
    plt.show()


# -----------------------------------------------------------------------------
# 3B.3 RUN COMPARISON
# -----------------------------------------------------------------------------

def run_full_comparison(layers: List[LayerProperties], shared: SharedParams,
                        model: tf.keras.Model, t_max_days: float = None):
    """Run full analytical vs PI-RNN comparison with all plots."""

    print("\n" + "=" * 80)
    print("PHASE 3B: Full Analytical vs PI-RNN Comparison (12-param, Layer-Specific kr)")
    print("=" * 80)

    # Print layer endpoint summary
    print(f"\nLayer Endpoint Permeabilities ({len(layers)} layers):")
    print(f"{'Layer':<8}{'krw_max':<10}{'kro_max':<10}{'Swc':<8}{'φ':<8}")
    print("-" * 44)
    for layer in sorted(layers, key=lambda x: x.layer_id):
        print(f"{layer.layer_id:<8}{layer.krw_max:<10.2f}{layer.kro_max:<10.2f}"
              f"{layer.swc:<8.2f}{layer.phi:<8.2f}")

    # Run analytical
    print("\nRunning Analytical model...")
    dp_anal = composite_dp_production(layers, shared, t_max_days)

    # Run PI-RNN
    print("\nRunning PI-RNN model (12-param)...")
    dp_pirnn = composite_dp_production_pirnn(layers, shared, model, t_max_days)

    # Summary table
    print("\n" + "-" * 70)
    print("COMPARISON AT KEY PVI VALUES (12-param PI-RNN)")
    print("-" * 70)
    print(f"{'PVI':<8}{'RF_Anal(%)':<12}{'RF_PIRNN(%)':<12}{'Diff(%)':<10}{'WC_Anal(%)':<12}{'WC_PIRNN(%)':<12}")
    print("-" * 70)

    for target_pvi in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]:
        idx_anal = np.argmin(np.abs(dp_anal.PVI_system - target_pvi))
        idx_pirnn = np.argmin(np.abs(dp_pirnn.PVI_system - target_pvi))

        rf_a = dp_anal.Recovery_factor[idx_anal] * 100
        rf_p = dp_pirnn.Recovery_factor[idx_pirnn] * 100
        wc_a = dp_anal.fw_system[idx_anal] * 100
        wc_p = dp_pirnn.fw_system[idx_pirnn] * 100

        print(f"{target_pvi:<8.2f}{rf_a:<12.2f}{rf_p:<12.2f}{rf_p-rf_a:<10.3f}{wc_a:<12.2f}{wc_p:<12.2f}")

    # Generate all plots
    print("\n" + "=" * 80)
    print("Generating Comparison Plots...")
    print("=" * 80)

    print("\n[Plot 1] Recovery Factor Comparison...")
    plot_recovery_factor_comparison(dp_anal, dp_pirnn)

    print("\n[Plot 2] Water Cut Comparison...")
    plot_water_cut_comparison(dp_anal, dp_pirnn)

    print("\n[Plot 3] Cumulative Oil vs Water Injection...")
    plot_cumulative_oil_comparison(dp_anal, dp_pirnn, shared)

    print("\n[Plot 4] Recovery Factor Difference...")
    plot_recovery_difference(dp_anal, dp_pirnn)

    print("\n[Plot 5] Per-Layer Recovery Comparison...")
    plot_layer_recovery_comparison(dp_anal, dp_pirnn, layers, shared)  # FIXED: Added shared

    print("\n[Plot 6] Recovery Factor Parity...")
    plot_recovery_parity(dp_anal, dp_pirnn)

    print("\n[Plot 7] Water Cut Parity...")
    plot_water_cut_parity(dp_anal, dp_pirnn)

    print("\n[Plot 8] Water-Oil Ratio Comparison...")
    plot_wor_comparison(dp_anal, dp_pirnn)

    print("\n" + "=" * 80)
    print("PHASE 3B COMPLETE!")
    print("=" * 80)

    return dp_anal, dp_pirnn


# =============================================================================
# PHASE 3B MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Assumes Phase 1, Phase 2, and Phase 3 have been run
    # layers, shared, and model should already exist

    dp_anal, dp_pirnn = run_full_comparison(layers, shared, model, t_max_days=None)