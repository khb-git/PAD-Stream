# =============================================================================
# SYNTHETIC LAYER GENERATOR FOR 12-PARAMETER PI-RNN TESTING
# =============================================================================

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# TRAINING RANGES (from 12-param PI-RNN)
# -----------------------------------------------------------------------------

TRAINING_RANGES = {
    # Layer-specific properties
    'phi':     (0.10, 0.30),    # Porosity
    'swc':     (0.10, 0.45),    # Connate water saturation
    'krw_max': (0.05, 0.80),    # Endpoint water relative perm
    'kro_max': (0.20, 1.00),    # Endpoint oil relative perm

    # Shared properties (constant across layers in a formation)
    'no':      (2.0, 4.0),      # Corey oil exponent
    'nw':      (2.0, 4.0),      # Corey water exponent
    'sor':     (0.10, 0.40),    # Residual oil saturation
    'mu_w':    (0.5, 50.0),     # Water viscosity (cP)
    'mu_o':    (0.3, 1.0),      # Oil viscosity (cP)

    # Physical layer properties (not in PI-RNN, but needed for DP)
    'h_ft':    (20.0, 80.0),    # Layer thickness (ft)
    'k_md':    (50.0, 1500.0),  # Permeability (mD)
}


# -----------------------------------------------------------------------------
# HELPER: DYKSTRA-PARSONS COEFFICIENT
# -----------------------------------------------------------------------------

def calculate_vdp(k_vals) -> float:
    """
    Calculate Dykstra-Parsons coefficient.

    V_DP = (k_50 - k_84.1) / k_50

    Where:
    - k_50 = median permeability (50th percentile)
    - k_84.1 = permeability exceeded by 84.1% of layers (15.9th percentile)

    V_DP ranges from 0 (homogeneous) to ~1 (highly heterogeneous)

    Returns:
    --------
    float : V_DP clipped to [0, 1]
    """
    k_vals = np.asarray(k_vals)
    k_50 = np.percentile(k_vals, 50)       # Median
    k_84 = np.percentile(k_vals, 15.9)     # Value exceeded by 84.1% of layers

    if k_50 > 0:
        V_DP = (k_50 - k_84) / k_50
    else:
        V_DP = 0.0

    return float(np.clip(V_DP, 0.0, 1.0))


# -----------------------------------------------------------------------------
# SYNTHETIC FORMATION DATACLASS
# -----------------------------------------------------------------------------

@dataclass
class SyntheticFormation:
    """Container for a synthetic formation with N layers."""
    name: str
    n_layers: int
    layers: List[LayerProperties]
    shared: SharedParams
    seed: Optional[int] = None

    def summary(self) -> str:
        """Return a formatted summary string."""
        lines = [
            f"\n{'='*80}",
            f"SYNTHETIC FORMATION: {self.name}",
            f"{'='*80}",
            f"Layers: {self.n_layers} | Seed: {self.seed}",
            f"\nShared Parameters:",
            f"  no={self.shared.no:.2f}, nw={self.shared.nw:.2f}, sor={self.shared.sor:.2f}",
            f"  mu_w={self.shared.mu_w:.2f} cP, mu_o={self.shared.mu_o:.2f} cP",
            f"  q_total={self.shared.q_total:.0f} bbl/d",
            f"\nLayer Properties:",
            f"{'Layer':<6}{'k(mD)':<10}{'h(ft)':<8}{'φ':<8}{'Swc':<8}{'krw_max':<10}{'kro_max':<10}{'Ri':<12}{'q(bbl/d)':<10}",
            "-" * 90,
        ]
        for L in sorted(self.layers, key=lambda x: x.layer_id):
            lines.append(
                f"{L.layer_id:<6}{L.k_md:<10.1f}{L.h_ft:<8.1f}{L.phi:<8.3f}"
                f"{L.swc:<8.3f}{L.krw_max:<10.3f}{L.kro_max:<10.3f}"
                f"{L.Ri:<12.1f}{L.q_layer:<10.1f}"
            )

        # Statistics
        k_vals = [L.k_md for L in self.layers]
        h_vals = [L.h_ft for L in self.layers]
        phi_vals = [L.phi for L in self.layers]

        # Dykstra-Parsons coefficient (using helper function)
        V_DP = calculate_vdp(k_vals)

        lines.extend([
            "-" * 90,
            f"\nFormation Statistics:",
            f"  Total thickness: {sum(h_vals):.1f} ft",
            f"  Permeability: min={min(k_vals):.1f}, max={max(k_vals):.1f}, mean={np.mean(k_vals):.1f} mD",
            f"  Dykstra-Parsons coefficient: V_DP = {V_DP:.3f}",
            f"  Porosity range: {min(phi_vals):.3f} - {max(phi_vals):.3f}",
        ])

        return "\n".join(lines)


# -----------------------------------------------------------------------------
# SYNTHETIC LAYER GENERATOR
# -----------------------------------------------------------------------------

def generate_synthetic_formation(
    n_layers: int,
    name: str = "Synthetic",
    seed: Optional[int] = None,
    # Shared parameter overrides (if None, sample from ranges)
    no: Optional[float] = None,
    nw: Optional[float] = None,
    sor: Optional[float] = None,
    mu_w: Optional[float] = None,
    mu_o: Optional[float] = None,
    # Geometry (fixed)
    A_ft2: float = 160000.0,
    x_ip_ft: float = 2000.0,
    L_ft: float = 625.0,
    q_total: float = 1000.0,
    Bo: float = 1.25,
    Bw: float = 1.02,
    # Distribution options
    k_distribution: str = 'lognormal',  # 'uniform', 'lognormal'
    k_lognormal_mean: float = 300.0,
    k_lognormal_sigma: float = 1.0,
    # Correlation options
    correlate_swc_k: bool = False,      # Higher k -> lower Swc (realistic)
    correlate_kr_phi: bool = False,     # Higher phi -> higher kr endpoints
) -> SyntheticFormation:
    """
    Generate a synthetic formation with N layers.

    Parameters:
    -----------
    n_layers : int
        Number of layers to generate
    name : str
        Formation name for identification
    seed : int, optional
        Random seed for reproducibility
    no, nw, sor, mu_w, mu_o : float, optional
        Override shared parameters (if None, sample from training ranges)
    k_distribution : str
        'uniform' or 'lognormal' for permeability distribution
    correlate_swc_k : bool
        If True, higher permeability layers get lower Swc
    correlate_kr_phi : bool
        If True, higher porosity layers get higher kr endpoints

    Returns:
    --------
    SyntheticFormation : dataclass containing layers and shared params
    """
    if seed is not None:
        np.random.seed(seed)

    # Sample or use provided shared parameters
    shared_no = no if no is not None else np.random.uniform(*TRAINING_RANGES['no'])
    shared_nw = nw if nw is not None else np.random.uniform(*TRAINING_RANGES['nw'])
    shared_sor = sor if sor is not None else np.random.uniform(*TRAINING_RANGES['sor'])
    shared_mu_w = mu_w if mu_w is not None else np.random.uniform(*TRAINING_RANGES['mu_w'])
    shared_mu_o = mu_o if mu_o is not None else np.random.uniform(*TRAINING_RANGES['mu_o'])

    # Create SharedParams (no krw_max/kro_max - now layer-specific)
    shared = SharedParams(
        no=shared_no,
        nw=shared_nw,
        sor=shared_sor,
        mu_w=shared_mu_w,
        mu_o=shared_mu_o,
        A_ft2=A_ft2,
        x_ip_ft=x_ip_ft,
        L_ft=L_ft,
        q_total=q_total,
        Bo=Bo,
        Bw=Bw,
    )

    # Generate layer properties
    layers = []

    # Sample base properties for all layers
    h_vals = np.random.uniform(*TRAINING_RANGES['h_ft'], size=n_layers)
    phi_vals = np.random.uniform(*TRAINING_RANGES['phi'], size=n_layers)

    # Permeability distribution
    if k_distribution == 'lognormal':
        k_vals = np.random.lognormal(
            mean=np.log(k_lognormal_mean),
            sigma=k_lognormal_sigma,
            size=n_layers
        )
        # Clip to training range
        k_vals = np.clip(k_vals, TRAINING_RANGES['k_md'][0], TRAINING_RANGES['k_md'][1])
    else:  # uniform
        k_vals = np.random.uniform(*TRAINING_RANGES['k_md'], size=n_layers)

    # Swc - optionally correlated with k
    if correlate_swc_k:
        # Higher k -> lower Swc (inverse correlation)
        k_normalized = (k_vals - k_vals.min()) / (k_vals.max() - k_vals.min() + 1e-8)
        swc_min, swc_max = TRAINING_RANGES['swc']
        swc_vals = swc_max - k_normalized * (swc_max - swc_min) * 0.7  # 70% correlation strength
        swc_vals += np.random.uniform(-0.05, 0.05, size=n_layers)  # Add noise
        swc_vals = np.clip(swc_vals, swc_min, swc_max)
    else:
        swc_vals = np.random.uniform(*TRAINING_RANGES['swc'], size=n_layers)

    # Ensure swc + sor < 1 for all layers
    max_swc = 1.0 - shared_sor - 0.05  # Leave 5% margin
    swc_vals = np.minimum(swc_vals, max_swc)

    # kr endpoints - optionally correlated with phi
    if correlate_kr_phi:
        phi_normalized = (phi_vals - phi_vals.min()) / (phi_vals.max() - phi_vals.min() + 1e-8)

        krw_min, krw_max = TRAINING_RANGES['krw_max']
        krw_vals = krw_min + phi_normalized * (krw_max - krw_min) * 0.6
        krw_vals += np.random.uniform(-0.1, 0.1, size=n_layers)
        krw_vals = np.clip(krw_vals, krw_min, krw_max)

        kro_min, kro_max = TRAINING_RANGES['kro_max']
        kro_vals = kro_min + phi_normalized * (kro_max - kro_min) * 0.6
        kro_vals += np.random.uniform(-0.1, 0.1, size=n_layers)
        kro_vals = np.clip(kro_vals, kro_min, kro_max)
    else:
        krw_vals = np.random.uniform(*TRAINING_RANGES['krw_max'], size=n_layers)
        kro_vals = np.random.uniform(*TRAINING_RANGES['kro_max'], size=n_layers)

    # Create layer objects
    for i in range(n_layers):
        layer = LayerProperties(
            layer_id=i + 1,
            h_ft=float(h_vals[i]),
            k_md=float(k_vals[i]),
            phi=float(phi_vals[i]),
            swc=float(swc_vals[i]),
            krw_max=float(krw_vals[i]),
            kro_max=float(kro_vals[i]),
        )

        # Compute Ri
        delta_S = 1.0 - layer.swc - shared_sor
        layer.Ri = (layer.k_md * layer.h_ft) / (layer.phi * delta_S)

        layers.append(layer)

    # Allocate flow rates proportional to k*h
    total_kh = sum(L.k_md * L.h_ft for L in layers)
    for layer in layers:
        layer.q_layer = q_total * (layer.k_md * layer.h_ft) / total_kh

    return SyntheticFormation(
        name=name,
        n_layers=n_layers,
        layers=layers,
        shared=shared,
        seed=seed,
    )


# -----------------------------------------------------------------------------
# PRESET FORMATION GENERATORS
# -----------------------------------------------------------------------------

def generate_homogeneous_formation(n_layers: int = 8, seed: int = None) -> SyntheticFormation:
    """Generate a relatively homogeneous formation (low V_DP)."""
    if seed is not None:
        np.random.seed(seed)

    # Use narrow ranges for more homogeneity
    formation = generate_synthetic_formation(
        n_layers=n_layers,
        name=f"Homogeneous-{n_layers}L",
        seed=seed,
        k_distribution='lognormal',
        k_lognormal_mean=400.0,
        k_lognormal_sigma=0.3,  # Low variance
        no=2.5,    # Fixed Corey exponents
        nw=2.5,
        sor=0.20,
        mu_w=1.0,
        mu_o=0.7,
    )
    return formation


def generate_heterogeneous_formation(n_layers: int = 8, seed: int = None) -> SyntheticFormation:
    """Generate a highly heterogeneous formation (high V_DP)."""
    if seed is not None:
        np.random.seed(seed)

    formation = generate_synthetic_formation(
        n_layers=n_layers,
        name=f"Heterogeneous-{n_layers}L",
        seed=seed,
        k_distribution='lognormal',
        k_lognormal_mean=300.0,
        k_lognormal_sigma=1.2,  # High variance
        correlate_swc_k=True,   # Realistic correlations
        correlate_kr_phi=True,
    )
    return formation


def generate_layered_formation(
    n_layers: int = 10,
    n_high_k: int = 3,
    seed: int = None
) -> SyntheticFormation:
    """Generate a formation with distinct high-k and low-k layers (thief zones)."""
    if seed is not None:
        np.random.seed(seed)

    # Start with base formation
    formation = generate_synthetic_formation(
        n_layers=n_layers,
        name=f"Layered-{n_layers}L-{n_high_k}thief",
        seed=seed,
        k_distribution='uniform',
    )

    # Select random layers to be high-k "thief zones"
    thief_indices = np.random.choice(n_layers, size=n_high_k, replace=False)

    for idx in thief_indices:
        formation.layers[idx].k_md = np.random.uniform(1000, 1500)
        formation.layers[idx].swc = np.random.uniform(0.10, 0.20)  # Lower Swc
        formation.layers[idx].krw_max = np.random.uniform(0.5, 0.8)  # Higher kr
        formation.layers[idx].kro_max = np.random.uniform(0.7, 1.0)

    # Recalculate Ri and q_layer
    total_kh = sum(L.k_md * L.h_ft for L in formation.layers)
    for layer in formation.layers:
        delta_S = 1.0 - layer.swc - formation.shared.sor
        layer.Ri = (layer.k_md * layer.h_ft) / (layer.phi * delta_S)
        layer.q_layer = formation.shared.q_total * (layer.k_md * layer.h_ft) / total_kh

    return formation


# -----------------------------------------------------------------------------
# VISUALIZATION
# -----------------------------------------------------------------------------

def plot_formation_properties(formation: SyntheticFormation):
    """Visualize formation layer properties."""
    layers = sorted(formation.layers, key=lambda x: x.layer_id)
    n = len(layers)

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    layer_ids = [L.layer_id for L in layers]

    # Permeability
    ax = axes[0, 0]
    k_vals = [L.k_md for L in layers]
    ax.barh(layer_ids, k_vals, color='steelblue', edgecolor='black')
    ax.set_xlabel('Permeability (mD)')
    ax.set_ylabel('Layer')
    ax.set_title('Permeability Distribution')
    ax.invert_yaxis()

    # Thickness
    ax = axes[0, 1]
    h_vals = [L.h_ft for L in layers]
    ax.barh(layer_ids, h_vals, color='forestgreen', edgecolor='black')
    ax.set_xlabel('Thickness (ft)')
    ax.set_ylabel('Layer')
    ax.set_title('Layer Thickness')
    ax.invert_yaxis()

    # Porosity & Swc
    ax = axes[0, 2]
    phi_vals = [L.phi for L in layers]
    swc_vals = [L.swc for L in layers]
    x = np.arange(n)
    width = 0.35
    ax.bar(x - width/2, phi_vals, width, label='φ', color='orange')
    ax.bar(x + width/2, swc_vals, width, label='Swc', color='royalblue')
    ax.set_xlabel('Layer')
    ax.set_ylabel('Fraction')
    ax.set_title('Porosity & Connate Water')
    ax.set_xticks(x)
    ax.set_xticklabels(layer_ids)
    ax.legend()

    # kr endpoints
    ax = axes[1, 0]
    krw_vals = [L.krw_max for L in layers]
    kro_vals = [L.kro_max for L in layers]
    ax.bar(x - width/2, krw_vals, width, label='krw_max', color='cyan')
    ax.bar(x + width/2, kro_vals, width, label='kro_max', color='red')
    ax.set_xlabel('Layer')
    ax.set_ylabel('Relative Perm Endpoint')
    ax.set_title('Endpoint Relative Permeabilities')
    ax.set_xticks(x)
    ax.set_xticklabels(layer_ids)
    ax.legend()

    # Ri (displacement efficiency indicator)
    ax = axes[1, 1]
    Ri_vals = [L.Ri for L in layers]
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, n))  # Red=high Ri (fast), Green=low Ri
    sorted_idx = np.argsort(Ri_vals)[::-1]
    ax.barh([layer_ids[i] for i in sorted_idx],
            [Ri_vals[i] for i in sorted_idx],
            color=[colors[i] for i in range(n)], edgecolor='black')
    ax.set_xlabel('Ri (k·h / φ·ΔS)')
    ax.set_ylabel('Layer')
    ax.set_title('Displacement Rate Index (sorted)')
    ax.invert_yaxis()

    # Flow allocation
    ax = axes[1, 2]
    q_vals = [L.q_layer for L in layers]
    ax.pie(q_vals, labels=[f'L{L.layer_id}' for L in layers],
           autopct='%1.1f%%', startangle=90)
    ax.set_title(f'Flow Allocation (Total: {formation.shared.q_total:.0f} bbl/d)')

    fig.suptitle(f'{formation.name}\n(n={formation.n_layers}, seed={formation.seed})',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()


def plot_permeability_distribution(formation: SyntheticFormation):
    """Plot permeability distribution and calculate V_DP."""
    k_vals = np.array([L.k_md for L in formation.layers])
    k_sorted = np.sort(k_vals)[::-1]

    # Cumulative probability (percent greater than)
    n = len(k_sorted)
    cum_prob = np.arange(1, n + 1) / n * 100

    # V_DP calculation using helper function
    V_DP = calculate_vdp(k_vals)
    k_50 = np.percentile(k_vals, 50)
    k_84 = np.percentile(k_vals, 15.9)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Log-probability plot
    ax = axes[0]
    ax.semilogy(cum_prob, k_sorted, 'bo-', markersize=8)
    ax.axhline(y=k_50, color='r', linestyle='--', label=f'k₅₀ = {k_50:.1f} mD')
    ax.axhline(y=k_84, color='g', linestyle='--', label=f'k₈₄.₁ = {k_84:.1f} mD')
    ax.set_xlabel('Cumulative % Greater Than')
    ax.set_ylabel('Permeability (mD)')
    ax.set_title(f'Permeability Distribution\nV_DP = {V_DP:.3f}')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Histogram
    ax = axes[1]
    ax.hist(k_vals, bins=min(20, n), color='steelblue', edgecolor='black', alpha=0.7)
    ax.axvline(x=k_50, color='r', linestyle='--', linewidth=2, label=f'Median = {k_50:.1f} mD')
    ax.axvline(x=np.mean(k_vals), color='orange', linestyle='--', linewidth=2,
               label=f'Mean = {np.mean(k_vals):.1f} mD')
    ax.set_xlabel('Permeability (mD)')
    ax.set_ylabel('Count')
    ax.set_title('Permeability Histogram')
    ax.legend()

    fig.suptitle(formation.name, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()

    return V_DP


# -----------------------------------------------------------------------------
# FULL ANALYSIS PIPELINE
# -----------------------------------------------------------------------------

def run_synthetic_analysis(
    formation: SyntheticFormation,
    model: tf.keras.Model,
    t_max_days: float = None,
    n_points: int = 500,
    plot_formation: bool = True,
    plot_profiles: bool = True,
    plot_comparison: bool = True,
):
    """
    Run full DP analysis on a synthetic formation.

    Returns:
    --------
    dict with keys: 'formation', 'dp_anal', 'dp_pirnn', 'statistics'
    """
    print(formation.summary())

    if plot_formation:
        print("\n[Plotting formation properties...]")
        plot_formation_properties(formation)
        V_DP = plot_permeability_distribution(formation)

    layers = formation.layers
    shared = formation.shared

    # Saturation profile comparison
    if plot_profiles:
        print("\n[Plotting saturation profiles (Analytical vs PI-RNN)...]")
        plot_saturation_profiles_comparison(
            model, layers, shared,
            n_times=5,
            n_layers_to_plot=min(8, formation.n_layers),
            n_xi_points=145
        )

    # Full production comparison
    if plot_comparison:
        print("\n[Running full production comparison...]")
        dp_anal, dp_pirnn = run_full_comparison(layers, shared, model, t_max_days)
    else:
        # Just compute without all plots
        print("\nRunning Analytical model...")
        dp_anal = composite_dp_production(layers, shared, t_max_days, n_points)
        print("Running PI-RNN model...")
        dp_pirnn = composite_dp_production_pirnn(layers, shared, model, t_max_days, n_points)

    # Compute statistics
    rf_anal = dp_anal.Recovery_factor * 100
    rf_pirnn = dp_pirnn.Recovery_factor * 100

    rmse = np.sqrt(np.mean((rf_pirnn - rf_anal)**2))
    mae = np.mean(np.abs(rf_pirnn - rf_anal))
    max_err = np.max(np.abs(rf_pirnn - rf_anal))

    ss_tot = np.sum((rf_anal - rf_anal.mean())**2)
    ss_res = np.sum((rf_pirnn - rf_anal)**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    statistics = {
        'rmse': rmse,
        'mae': mae,
        'max_error': max_err,
        'r2': r2,
        'final_rf_anal': rf_anal[-1],
        'final_rf_pirnn': rf_pirnn[-1],
    }

    print("\n" + "=" * 60)
    print(f"SUMMARY: {formation.name}")
    print("=" * 60)
    print(f"  Layers: {formation.n_layers}")
    print(f"  Final RF (Analytical): {rf_anal[-1]:.2f}%")
    print(f"  Final RF (PI-RNN):     {rf_pirnn[-1]:.2f}%")
    print(f"  RMSE: {rmse:.4f}%")
    print(f"  MAE:  {mae:.4f}%")
    print(f"  R²:   {r2:.6f}")

    return {
        'formation': formation,
        'dp_anal': dp_anal,
        'dp_pirnn': dp_pirnn,
        'statistics': statistics,
    }


# -----------------------------------------------------------------------------
# BATCH TESTING
# -----------------------------------------------------------------------------

def run_batch_synthetic_tests(
    model: tf.keras.Model,
    n_formations: int = 10,
    layers_per_formation: int = 8,
    base_seed: int = 42,
    plot_individual: bool = False,
):
    """
    Run batch tests on multiple random formations.

    Returns DataFrame with statistics for each formation.
    """
    import pandas as pd

    results = []

    print("=" * 80)
    print(f"BATCH SYNTHETIC TESTING: {n_formations} formations, {layers_per_formation} layers each")
    print("=" * 80)

    for i in range(n_formations):
        seed = base_seed + i
        print(f"\n[Formation {i+1}/{n_formations}] Seed={seed}")

        # Generate random formation
        formation = generate_synthetic_formation(
            n_layers=layers_per_formation,
            name=f"Batch-{i+1}",
            seed=seed,
        )

        # Run analysis (minimal plotting)
        result = run_synthetic_analysis(
            formation, model,
            plot_formation=plot_individual,
            plot_profiles=plot_individual,
            plot_comparison=plot_individual,
        )

        # Collect statistics
        stats = result['statistics']

        # Add formation info (using helper function for V_DP)
        k_vals = [L.k_md for L in formation.layers]
        V_DP = calculate_vdp(k_vals)

        results.append({
            'formation': formation.name,
            'seed': seed,
            'n_layers': formation.n_layers,
            'V_DP': V_DP,
            'k_mean': np.mean(k_vals),
            'k_std': np.std(k_vals),
            'mu_ratio': formation.shared.mu_w / formation.shared.mu_o,
            'rmse': stats['rmse'],
            'mae': stats['mae'],
            'max_error': stats['max_error'],
            'r2': stats['r2'],
            'final_rf_anal': stats['final_rf_anal'],
            'final_rf_pirnn': stats['final_rf_pirnn'],
        })

    df = pd.DataFrame(results)

    # Summary statistics
    print("\n" + "=" * 80)
    print("BATCH TEST SUMMARY")
    print("=" * 80)
    print(f"\nOverall Statistics (n={n_formations} formations):")
    print(f"  Mean RMSE: {df['rmse'].mean():.4f}% ± {df['rmse'].std():.4f}%")
    print(f"  Mean MAE:  {df['mae'].mean():.4f}% ± {df['mae'].std():.4f}%")
    print(f"  Mean R²:   {df['r2'].mean():.6f}")
    print(f"  Max Error: {df['max_error'].max():.4f}%")

    # Plot summary
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # RMSE distribution
    ax = axes[0, 0]
    ax.hist(df['rmse'], bins=20, color='steelblue', edgecolor='black', alpha=0.7)
    ax.axvline(df['rmse'].mean(), color='red', linestyle='--', label=f'Mean={df["rmse"].mean():.4f}')
    ax.set_xlabel('RMSE (%)')
    ax.set_ylabel('Count')
    ax.set_title('RMSE Distribution')
    ax.legend()

    # R² distribution
    ax = axes[0, 1]
    ax.hist(df['r2'], bins=20, color='forestgreen', edgecolor='black', alpha=0.7)
    ax.axvline(df['r2'].mean(), color='red', linestyle='--', label=f'Mean={df["r2"].mean():.6f}')
    ax.set_xlabel('R²')
    ax.set_ylabel('Count')
    ax.set_title('R² Distribution')
    ax.legend()

    # RMSE vs V_DP
    ax = axes[1, 0]
    scatter = ax.scatter(df['V_DP'], df['rmse'], c=df['mu_ratio'], cmap='viridis', s=50, alpha=0.7)
    ax.set_xlabel('Dykstra-Parsons Coefficient (V_DP)')
    ax.set_ylabel('RMSE (%)')
    ax.set_title('RMSE vs Heterogeneity')
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('μw/μo')

    # Final RF comparison
    ax = axes[1, 1]
    scatter = ax.scatter(df['final_rf_anal'], df['final_rf_pirnn'], c=df['V_DP'], cmap='viridis', s=50, alpha=0.7)
    max_rf = max(df['final_rf_anal'].max(), df['final_rf_pirnn'].max())
    ax.plot([0, max_rf], [0, max_rf], 'r--', linewidth=2, label='1:1')
    ax.set_xlabel('Analytical Final RF (%)')
    ax.set_ylabel('PI-RNN Final RF (%)')
    ax.set_title('Final Recovery Factor Parity')
    ax.legend()
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('V_DP')

    fig.suptitle(f'Batch Test Results (n={n_formations} formations)', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

    return df


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Example 1: Single random formation
    print("\n" + "="*80)
    print("EXAMPLE 1: Single Random Formation")
    print("="*80)

    formation = generate_synthetic_formation(
        n_layers=10,
        name="Random-10L",
        seed=123,
    )

    result = run_synthetic_analysis(
        formation, model,
        plot_formation=True,
        plot_profiles=True,
        plot_comparison=True,
    )

    # Example 2: Heterogeneous formation
    print("\n" + "="*80)
    print("EXAMPLE 2: Heterogeneous Formation")
    print("="*80)

    formation_het = generate_heterogeneous_formation(n_layers=12, seed=456)
    result_het = run_synthetic_analysis(
        formation_het, model,
        plot_formation=True,
        plot_profiles=True,
        plot_comparison=True,
    )

    # Example 3: Batch testing (uncomment to run)
    # print("\n" + "="*80)
    # print("EXAMPLE 3: Batch Testing (10 formations)")
    # print("="*80)
    # df_batch = run_batch_synthetic_tests(model, n_formations=10, layers_per_formation=8)
    # print(df_batch)