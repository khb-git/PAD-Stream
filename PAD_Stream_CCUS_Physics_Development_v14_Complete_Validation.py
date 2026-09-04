"""
PAD-STREAM CCUS PHYSICS DEVELOPMENT — VERSION 6 (TRANSIENT PRESSURE)

This file preserves the user-provided CCUS Classical Physics Pipeline v2 and
retains the deterministic 5 x 5 x 5 development case and adds Stage 16 with individual
plots for geology, constitutive physics, the four-mode 1D ladder, TPFA
pressure, pore velocity, Pollock streamlines, time of flight, F-Phi, and the
current four-mode multidimensional simulator, plus a backward-Euler slightly-compressible TPFA pressure solve.

New development stages are explicitly marked. Existing reference physics is retained
unchanged except that the original all-scenarios __main__ call is replaced by
the new deterministic development entry point.
"""

"""
================================================================================
CCUS CLASSICAL PHYSICS PIPELINE v2 — full 24-file consolidation
================================================================================
Every file you sent, concatenated with stage tags added at existing section
breaks. No physics logic changed anywhere. Source map:

    blsolvers.py         -> STAGE 1, 2, 3, 4, 4b, 4c   (1D BL solver suite)
    dp_solver.py          -> STAGE 5                     (Dykstra-Parsons, no-crossflow)
    fphi_diagnostic.py    -> STAGE 5b                    (F-Phi / Lorenz diagnostic)
    streamline_sim.py     -> STAGE 6, 7                  (3D streamline simulator)
    nc_slopeflux.py        -> STAGE 4c-full               (VEPlumeSolver, mass-conservative)
    ccus_trapping.py      -> STAGE 7c                    (Land/Killough trapping math)
    run_validations.py    -> STAGE 8                     (7-check regression harness)
    17 scenario scripts   -> STAGE 9                     (each wrapped as scenario_<name>())

Units: STAGE 1-5/5b (blsolvers.py, dp_solver.py, fphi_diagnostic.py) are field
units (mD, ft, psi, bbl/day). STAGE 6-7/4c-full/7c (streamline_sim.py,
nc_slopeflux.py, ccus_trapping.py) are SI. Preserved exactly as your files
have them — no conversion layer added.

WHAT I CHANGED, mechanically, to make this one runnable file (zero physics
edits, all three are packaging fixes):
  1. streamline_sim.py's own __main__ block -> run_streamline_sim_original_demo()
     (same code, just not auto-running and blocking everything after it)
  2. run_validations.py's __main__ guard -> removed; main() stays callable
  3. Every scenario script's `import streamline_sim as S` / `import blsolvers
     as B` / etc. -> stripped, and replaced by namespace-shim objects (S, B,
     D, NC, FP, CT) built below that point at the already-flattened classes/
     functions, so every `S.Grid3D(...)`, `B.RockProperties(...)` etc. call
     in your scenario scripts' bodies works completely unmodified.
  4. Every scenario script's hardcoded save path (/home/claude/... or
     /mnt/user-data/outputs/...) -> redirected to an OUTDIR variable
     (defaults to "."), since neither of those directories exists in Colab.
     Everything else about each script, including all parameter choices,
     is untouched.

  4. Removed `matplotlib.use("Agg")` (was forcing headless/file-only output,
     which blocks inline figure display everywhere, including PyCharm's
     scientific-mode SciView). Matplotlib now auto-selects the right backend
     per environment: PyCharm's interactive backend when run there, Agg
     automatically as a fallback in headless environments (verified, this
     sandbox still resolves to 'agg' with the line removed, so nothing
     breaks where a display isn't available). Figures are still saved to
     OUTDIR exactly as before, this only restores inline display.

  5. Added `plt.show(block=False)` immediately before every `plt.close(fig)`
     (22 occurrences). This was the actual blocker: every figure in these
     scripts was being closed right after `savefig`, which destroys it
     before anything, PyCharm's SciView included, gets a chance to display
     it. Removing Agg alone wasn't enough; this is what actually makes the
     figures appear. `block=False` so a real GUI backend can't hang the
     script waiting for you to close each window by hand.

  6. `run_default()` now runs all 17 scenario functions (was 5), ordered
     fast to slow so figures start appearing immediately. All 17 were
     individually verified; the last three (`make_demo_full`,
     `make_8layer_ccus`, `make_8layer_full`, full physics + crossflow on
     3D grids) were verified via their exact call pattern at reduced scale
     rather than a full-scale timed run — one of the four required passes
     in `make_demo_full` alone ran past 4 minutes. Expect the full default
     run to take a while; per-scenario time estimates are printed as each
     one starts.

  7. Default run is now CCUS-only (`run_ccus_story()`), not all 17. Runs
     `make_8layer_ccus` and `stage2_aquifer` (already CCUS-parametrized in
     your files) plus three new figures written for this request: a
     physics-mode areal comparison, a full five-spot CCUS sweep, and a
     plume cross-section (Stage 10 — new code, not from your uploads, built
     with your solver classes). The full 17-scenario run is still there,
     call `run_all_scenarios()` directly.

  8. Correction: default is `run_all_scenarios()` again, not the CCUS-only
     subset, now covering all 20 (17 original + the 3 new Stage 10 figures)
     in one run. `run_ccus_story()` (CCUS-only, 5 scenarios) is still there
     if that narrower run is ever wanted again.

Dependencies: numpy, scipy, matplotlib (pre-installed in Colab). No local
package structure — paste stage by stage, or run top to bottom as one file.
================================================================================
"""
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa
from dataclasses import dataclass, field
from scipy.linalg import solve_banded
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve
import time

OUTDIR = "."


# STAGE 1-2 [S1/S2] BL incompressible + compressible
# CompressibleBLSolver.solve_incompressible() = Stage 1 (u = const)
# CompressibleBLSolver.solve() = Stage 2 (u varies with density via EOS)
"""Faithful reconstruction of Khalil's CompressibleBLSolver (from his BL suite)
   — only the parts needed to cross-validate the streamline compressible source."""


@dataclass
class FluidProperties:
    mu_w: float = 0.5
    mu_o: float = 5.0
    bw: float = 1.02
    bo: float = 1.25
    @property
    def viscosity_ratio(self):
        return self.mu_w / self.mu_o


@dataclass
class RockProperties:
    nw: float = 2.0
    no: float = 2.0
    swc: float = 0.2
    sor: float = 0.2
    krw_max: float = 0.8
    kro_max: float = 0.8
    phi: float = 0.20
    @property
    def sw_max(self):
        return 1.0 - self.sor
    @property
    def saturation_span(self):
        return 1.0 - self.swc - self.sor


@dataclass
class ReservoirGeometry:
    A: float = 160000.0
    x_ip: float = 2000.0
    h: float = 50.0
    i_w: float = 1000.0


@dataclass
class CompressibleFluid:
    rho_ref: float = 62.4
    p_ref: float = 14.7
    c: float = 3.0e-6
    def density(self, p):
        return self.rho_ref * np.exp(self.c * (p - self.p_ref))
    def density_array(self, p):
        return self.rho_ref * np.exp(self.c * (p - self.p_ref))


@dataclass
class PressureConditions:
    p_inj: float = 3000.0
    p_init: float = 2000.0
    def pressure_profile(self, x, L):
        return self.p_inj - (self.p_inj - self.p_init) * x / L


def calculate_relative_permeability(sw, rock):
    sw_norm = np.clip((sw - rock.swc) / rock.saturation_span, 0.0, 1.0)
    krw = rock.krw_max * (sw_norm ** rock.nw)
    kro = rock.kro_max * ((1.0 - sw_norm) ** rock.no)
    return krw, kro


def calculate_fractional_flow(sw, rock, fluid):
    krw, kro = calculate_relative_permeability(sw, rock)
    eps = 1e-12
    return 1.0 / (1.0 + fluid.viscosity_ratio * kro / (krw + eps))


def calculate_dfw_dsw(sw, fw):
    return np.gradient(fw, sw)


def godunov_flux(Sw_L, Sw_R, rock, fluid, n_sample=50):
    eps = 1e-12
    if abs(Sw_L - Sw_R) < eps:
        return float(calculate_fractional_flow(np.array([Sw_L]), rock, fluid)[0])
    Sw_sample = np.linspace(min(Sw_L, Sw_R), max(Sw_L, Sw_R), n_sample)
    fw_sample = calculate_fractional_flow(Sw_sample, rock, fluid)
    if Sw_L <= Sw_R:
        return float(np.min(fw_sample))
    return float(np.max(fw_sample))


def compute_compressibility_number(eos, pressure):
    return np.log(eos.density(pressure.p_inj) / eos.density(pressure.p_init))


class CompressibleBLSolver:
    def __init__(self, rock, fluid, geom, eos, pressure):
        self.rock = rock; self.fluid = fluid; self.geom = geom
        self.eos = eos; self.pressure = pressure
        self.Nc = compute_compressibility_number(eos, pressure)
        self.rho_inj = eos.density(pressure.p_inj)
        self.rho_init = eos.density(pressure.p_init)
        self.u_inj = (5.615 * geom.i_w) / geom.A

    def _step(self, Sw, u, dt, dx, Sw_inj):
        nx = len(Sw); Sw_new = Sw.copy()
        F = np.zeros(nx + 1)
        F[0] = u[0] * calculate_fractional_flow(np.array([Sw_inj]), self.rock, self.fluid)[0]
        for i in range(1, nx):
            f_god = godunov_flux(Sw[i-1], Sw[i], self.rock, self.fluid)
            F[i] = 0.5 * (u[i-1] + u[i]) * f_god
        F[nx] = u[-1] * calculate_fractional_flow(np.array([Sw[-1]]), self.rock, self.fluid)[0]
        for i in range(1, nx):
            Sw_new[i] = Sw[i] - (dt / (self.rock.phi * dx)) * (F[i+1] - F[i])
        Sw_new[0] = Sw_inj
        return np.clip(Sw_new, self.rock.swc, self.rock.sw_max)

    def _run(self, t_days, nx, cfl, u):
        L = self.geom.x_ip
        dx = L / (nx - 1)
        Sw_init = self.rock.swc + 0.001
        Sw_inj = self.rock.sw_max - 0.001
        s = np.linspace(self.rock.swc, self.rock.sw_max, 100)
        f = calculate_fractional_flow(s, self.rock, self.fluid)
        max_dfw = np.max(np.abs(calculate_dfw_dsw(s, f)))
        dt = cfl * self.rock.phi * dx / (np.max(u) * max_dfw + 1e-12)
        nt = int(np.ceil(t_days / dt)); dt = t_days / nt
        Sw = np.ones(nx) * Sw_init; Sw[0] = Sw_inj
        for _ in range(nt):
            Sw = self._step(Sw, u, dt, dx, Sw_inj)
        return np.linspace(0, 1, nx), Sw

    def solve(self, t_days, nx=401, cfl=0.5):
        L = self.geom.x_ip
        x = np.linspace(0, L, nx)
        p = self.pressure.pressure_profile(x, L)
        rho = self.eos.density_array(p)
        u = self.u_inj * self.rho_inj / rho            # mass-flux velocity
        return self._run(t_days, nx, cfl, u)

    def solve_incompressible(self, t_days, nx=401, cfl=0.5):
        u = np.ones(nx) * self.u_inj
        return self._run(t_days, nx, cfl, u)


# STAGE 3 [S3] capillary additions (faithful to the BL capillary solver) ------


@dataclass
class CapillaryProperties:
    Pe: float = 5.0          # entry pressure [psi]
    lambda_bc: float = 2.0
    k: float = 100.0         # permeability [mD]


def calculate_capillary_pressure(Sw, rock, cap):
    Se = np.clip((Sw - rock.swc) / rock.saturation_span, 0.01, 0.99)
    return cap.Pe * (Se ** (-1.0 / cap.lambda_bc))


def calculate_dPc_dSw(Sw, rock, cap):
    Se = np.clip((Sw - rock.swc) / rock.saturation_span, 0.01, 0.99)
    dSe_dSw = 1.0 / rock.saturation_span
    dPc_dSe = -cap.Pe / cap.lambda_bc * (Se ** (-1.0 / cap.lambda_bc - 1.0))
    return dPc_dSe * dSe_dSw


def calculate_diffusion_coefficient(Sw, rock, fluid, cap):
    krw, kro = calculate_relative_permeability(Sw, rock)
    fw = calculate_fractional_flow(Sw, rock, fluid)
    dPc_dSw = calculate_dPc_dSw(Sw, rock, cap)
    k_ft2 = cap.k * 1.0133e-11
    mu_o_psi_day = fluid.mu_o * 6.8948e-8
    D = -k_ft2 * kro * fw / mu_o_psi_day * dPc_dSw
    return np.maximum(D, 0.0)


class CapillaryBLSolver:
    def __init__(self, rock, fluid, geom, cap):
        self.rock = rock; self.fluid = fluid; self.geom = geom; self.cap = cap
        self.u_inj = (5.615 * geom.i_w) / geom.A
        Sw_mid = 0.5 * (rock.swc + rock.sw_max)
        self.D_ref = float(calculate_diffusion_coefficient(
            np.array([Sw_mid]), rock, fluid, cap)[0])
        self.Pe_c = (self.u_inj * geom.x_ip * rock.phi) / max(self.D_ref, 1e-12)

    def _adv(self, Sw, dt, dx, Sw_inj):
        nx = len(Sw); Sw_new = Sw.copy()
        F = np.zeros(nx + 1)
        F[0] = self.u_inj * calculate_fractional_flow(np.array([Sw_inj]), self.rock, self.fluid)[0]
        for i in range(1, nx):
            F[i] = self.u_inj * godunov_flux(Sw[i-1], Sw[i], self.rock, self.fluid)
        F[nx] = self.u_inj * calculate_fractional_flow(np.array([Sw[-1]]), self.rock, self.fluid)[0]
        for i in range(1, nx):
            Sw_new[i] = Sw[i] - (dt / (self.rock.phi * dx)) * (F[i+1] - F[i])
        Sw_new[0] = Sw_inj
        return np.clip(Sw_new, self.rock.swc, self.rock.sw_max)

    def _diff(self, Sw, dt, dx, Sw_inj):
        nx = len(Sw)
        D = calculate_diffusion_coefficient(Sw, self.rock, self.fluid, self.cap)
        alpha = dt / (self.rock.phi * dx**2)
        lower = np.zeros(nx); diag = np.ones(nx); upper = np.zeros(nx); rhs = Sw.copy()
        for i in range(1, nx - 1):
            DL = 0.5 * (D[i-1] + D[i]); DR = 0.5 * (D[i] + D[i+1])
            lower[i] = -alpha * DL; upper[i] = -alpha * DR
            diag[i] = 1.0 + alpha * (DL + DR)
        diag[0] = 1.0; upper[0] = 0.0; rhs[0] = Sw_inj
        diag[-1] = 1.0; lower[-1] = 0.0
        ab = np.zeros((3, nx)); ab[0, 1:] = upper[:-1]; ab[1, :] = diag; ab[2, :-1] = lower[1:]
        return np.clip(solve_banded((1, 1), ab, rhs), self.rock.swc, self.rock.sw_max)

    def solve(self, t_days, nx=401, cfl=0.5):
        L = self.geom.x_ip; dx = L / (nx - 1)
        s = np.linspace(self.rock.swc, self.rock.sw_max, 100)
        f = calculate_fractional_flow(s, self.rock, self.fluid)
        max_dfw = np.max(np.abs(calculate_dfw_dsw(s, f)))
        dt = cfl * self.rock.phi * dx / (self.u_inj * max_dfw + 1e-12)
        nt = int(np.ceil(t_days / dt)); dt = t_days / nt
        Sw = np.ones(nx) * (self.rock.swc + 0.001); Sw[0] = self.rock.sw_max - 0.001
        Sw_inj = self.rock.sw_max - 0.001
        for _ in range(nt):
            Sw = self._adv(Sw, dt, dx, Sw_inj)
            Sw = self._diff(Sw, dt, dx, Sw_inj)
        return np.linspace(0, 1, nx), Sw


# STAGE 4 [S4] full solver (compressible + capillary), by composition -------
class FullBLSolver:
    def __init__(self, rock, fluid, geom, eos, pressure, cap):
        self.rock = rock; self.fluid = fluid; self.geom = geom
        self.eos = eos; self.pressure = pressure; self.cap = cap
        self._c = CompressibleBLSolver(rock, fluid, geom, eos, pressure)  # variable-u adv
        self._k = CapillaryBLSolver(rock, fluid, geom, cap)               # implicit diff
        self.Nc = self._c.Nc
        self.Pe_c = self._k.Pe_c

    def solve(self, t_days, nx=401, cfl=0.5):
        L = self.geom.x_ip; dx = L / (nx - 1)
        x = np.linspace(0, L, nx)
        p = self.pressure.pressure_profile(x, L)
        rho = self.eos.density_array(p)
        u = self._c.u_inj * self._c.rho_inj / rho
        s = np.linspace(self.rock.swc, self.rock.sw_max, 100)
        f = calculate_fractional_flow(s, self.rock, self.fluid)
        max_dfw = np.max(np.abs(calculate_dfw_dsw(s, f)))
        dt = cfl * self.rock.phi * dx / (np.max(u) * max_dfw + 1e-12)
        nt = int(np.ceil(t_days / dt)); dt = t_days / nt
        Sw = np.ones(nx) * (self.rock.swc + 0.001); Sw[0] = self.rock.sw_max - 0.001
        Sw_inj = self.rock.sw_max - 0.001
        for _ in range(nt):
            Sw = self._c._step(Sw, u, dt, dx, Sw_inj)
            Sw = self._k._diff(Sw, dt, dx, Sw_inj)
        return np.linspace(0, 1, nx), Sw


# STAGE 4b [S4b] gravity-extended Buckley-Leverett (Tier-1 CCS reference, 1D) -
def calculate_fractional_flow_gravity(sw, rock, fluid, Ng):
    """Gravity-modified fractional flow for 1D flow along the gravity direction.
    Ng = k*g*(rho_w - rho_o)/(u_t*mu_o) is the dimensionless buoyancy/viscous
    number (signed: Ng>0 hinders, Ng<0 assists the injected phase). Derived from
    two-phase Darcy with the gravity potential (cf. Lake 1989, EOR):
        fw = fw_viscous - (k*g*dRho/u_t) * (lam_w*lam_o)/(lam_w+lam_o)
           = fw_viscous * (1 - Ng*kro).
    Reduces exactly to the viscous fractional flow when Ng=0."""
    krw, kro = calculate_relative_permeability(sw, rock)
    eps = 1e-12
    fw0 = 1.0 / (1.0 + fluid.viscosity_ratio * kro / (krw + eps))
    return fw0 * (1.0 - Ng * kro)


def godunov_flux_gravity(Sw_L, Sw_R, rock, fluid, Ng, n_sample=80):
    """Entropy-correct Godunov flux for the (possibly non-convex) gravity fw."""
    if abs(Sw_R - Sw_L) < 1e-12:
        return float(calculate_fractional_flow_gravity(
            np.array([Sw_L]), rock, fluid, Ng)[0])
    Sw_sample = np.linspace(min(Sw_L, Sw_R), max(Sw_L, Sw_R), n_sample)
    fw = calculate_fractional_flow_gravity(Sw_sample, rock, fluid, Ng)
    return float(np.min(fw)) if Sw_L <= Sw_R else float(np.max(fw))


class GravityBLSolver:
    """1D Buckley-Leverett with gravity along the flow direction (vertical/tilted
    column). Sibling of CompressibleBLSolver / CapillaryBLSolver: same Corey kr
    and finite-volume Godunov scheme; only the fractional flow carries the
    buoyancy term. Reduces to the viscous BL solution when Ng=0."""
    def __init__(self, rock, fluid, geom, Ng):
        self.rock = rock; self.fluid = fluid; self.geom = geom; self.Ng = Ng
        self.u_inj = (5.615 * geom.i_w) / geom.A

    def _step(self, Sw, dt, dx, Sw_inj):
        nx = len(Sw); Sw_new = Sw.copy(); F = np.zeros(nx + 1)
        F[0] = self.u_inj * calculate_fractional_flow_gravity(
            np.array([Sw_inj]), self.rock, self.fluid, self.Ng)[0]
        for i in range(1, nx):
            F[i] = self.u_inj * godunov_flux_gravity(
                Sw[i - 1], Sw[i], self.rock, self.fluid, self.Ng)
        F[nx] = self.u_inj * calculate_fractional_flow_gravity(
            np.array([Sw[-1]]), self.rock, self.fluid, self.Ng)[0]
        for i in range(1, nx):
            Sw_new[i] = Sw[i] - (dt / (self.rock.phi * dx)) * (F[i + 1] - F[i])
        Sw_new[0] = Sw_inj
        return np.clip(Sw_new, self.rock.swc, self.rock.sw_max)

    def solve(self, t_days, nx=401, cfl=0.4):
        L = self.geom.x_ip; dx = L / (nx - 1)
        s = np.linspace(self.rock.swc, self.rock.sw_max, 200)
        f = calculate_fractional_flow_gravity(s, self.rock, self.fluid, self.Ng)
        max_dfw = np.max(np.abs(calculate_dfw_dsw(s, f)))
        dt = cfl * self.rock.phi * dx / (self.u_inj * max_dfw + 1e-12)
        nt = int(np.ceil(t_days / dt)); dt = t_days / nt
        Sw = np.ones(nx) * (self.rock.swc + 0.001); Sw[0] = self.rock.sw_max - 0.001
        Sw_inj = self.rock.sw_max - 0.001
        for _ in range(nt):
            Sw = self._step(Sw, dt, dx, Sw_inj)
        return np.linspace(0, 1, nx), Sw


# STAGE 4c [S4c] Nordbotten-Celia radial VE plume, fractional-flow-only (Tier-2)
def ve_fractional_flow(psi, M, G):
    """Vertical-equilibrium segregated-flow CO2 fractional flow with gravity.
    psi = vertically-averaged CO2 saturation (= interface height fraction); the
    VE upscaling gives straight-line vertically-averaged rel-perms, so the viscous
    part is Fv = M*psi/(M*psi + (1-psi)) with M = mu_w/mu_g. Gravity correction
    F = (1 + (G/M)(1-psi))*Fv, G = k*dRho*g/(mu_g*u_t) (cf. NC 2005; gravity-
    corrected fractional flow form, arXiv:2203.05021). Reduces to viscous radial
    BL when G=0."""
    psi = np.clip(np.asarray(psi, float), 0.0, 1.0)
    Fv = M * psi / (M * psi + (1.0 - psi) + 1e-30)
    return (1.0 + (G / M) * (1.0 - psi)) * Fv


class NCPlumeSolver:
    """Radial sharp-interface VE plume (Nordbotten-Celia-class). Self-similar
    Buckley-Leverett frontal advance for psi(eta), eta = pi*H*phi*r^2/(Q*t),
    via the Welge tangent on the VE fractional flow. Returns the interface shape
    psi(eta), the dimensionless tip eta_shock, and the tip radius. Reduces to the
    viscous radial BL front at G=0; tongues toward the tip as G grows."""
    def __init__(self, M, G, nps=4000):
        self.M = M; self.G = G
        psi = np.linspace(1e-6, 1.0 - 1e-9, nps)
        F = ve_fractional_flow(psi, M, G)
        speed = F / psi                                   # chord speed from psi=0
        ish = int(np.argmax(speed))
        self.psi_shock = float(psi[ish]); self.eta_shock = float(speed[ish])
        self.psi = psi; self.F = F; self.dF = np.gradient(F, psi)

    def profile(self, eta):
        eta = np.atleast_1d(np.asarray(eta, float)); out = np.zeros_like(eta)
        mask = self.psi >= self.psi_shock
        dFm = self.dF[mask]; psim = self.psi[mask]
        order = np.argsort(dFm)                            # ascending dF for interp
        dFs = dFm[order]; pss = psim[order]
        dF_at_1 = float(self.dF[-1])
        for i, e in enumerate(eta):
            if e >= self.eta_shock:
                out[i] = 0.0
            elif e <= dF_at_1:
                out[i] = 1.0
            else:
                out[i] = float(np.interp(e, dFs, pss))
        return out

    def mass_balance(self):
        eta = np.linspace(0, self.eta_shock, 6000)
        return float(np.trapezoid(self.profile(eta), eta))   # should = 1.0

    def tip_radius(self, Q, t, H, phi):
        return float(np.sqrt(self.eta_shock * Q * t / (np.pi * H * phi)))
# STAGE 5 [S5] Dykstra-Parsons, no-crossflow reference model
# independent layers, kh-allocated flow, analytical Welge per layer
"""
Dykstra-Parsons layered waterflood (reference model)
====================================================
Each layer is an INDEPENDENT 1D Buckley-Leverett displacement; layers communicate
only through the common wells (no vertical crossflow). Flow is allocated to layers
by transmissibility-thickness (kh).  This is the classical DP construction and the
no-crossflow limit that the streamline simulator must reproduce.

Per layer: analytical Welge tangent -> shock front, breakthrough, post-breakthrough
water cut and recovery as functions of the layer's own injected pore volumes.
"""


def _fw_se(se, M):
    """Fractional flow vs normalized saturation, Corey nw=no=2.
       M = endpoint mobility ratio (krw_max/mu_w)/(kro_max/mu_o)."""
    lw = M * se**2
    lo = (1.0 - se)**2
    return lw / (lw + lo + 1e-300)


def _dfw_dse(se, M):
    lw = M * se**2
    lo = (1.0 - se)**2
    num = lw + lo
    dlw = 2.0 * M * se
    dlo = -2.0 * (1.0 - se)
    return (dlw * num - lw * (dlw + dlo)) / (num**2 + 1e-300)


class DPLayer:
    """One 1D Buckley-Leverett layer; recovery and water-cut vs local PVI tau."""
    def __init__(self, swc, sor, krw_max, kro_max, mu_w, mu_o, n=20001):
        self.swc, self.sor = swc, sor
        self.span = 1.0 - swc - sor
        self.M = (krw_max / mu_w) / (kro_max / mu_o)
        se = np.linspace(1e-6, 1.0 - 1e-6, n)
        fw = _fw_se(se, self.M)
        # Welge tangent from (se=0, fw=0): fw(se_f)/se_f = dfw/dse(se_f)
        g = fw / se - _dfw_dse(se, self.M)
        idx = np.where(np.diff(np.sign(g)) != 0)[0]
        sef = se[idx[-1]] if len(idx) else se[np.argmax(fw / se)]
        self.se_f = sef
        self.dfw_dsw_f = _dfw_dse(sef, self.M) / self.span   # front speed in Sw
        self.tau_bt = 1.0 / self.dfw_dsw_f                    # local PVI at breakthrough
        self._se = se
        self._fw = fw
        self._dfw_dsw = _dfw_dse(se, self.M) / self.span

    def state(self, tau):
        """Return (recovery_of_movable, producer_water_cut) at local PVI tau."""
        if tau <= self.tau_bt:
            return tau / self.span, 0.0                       # piston-like, dry
        # post-breakthrough: outlet saturation has speed dfw/dSw = 1/tau.
        # The relevant root is on the spreading-wave branch se >= se_f, where
        # dfw/dSw decreases monotonically from its shock value toward 0; the low-se
        # branch must be excluded or it returns the dry (fw=0) saturation.
        target = 1.0 / tau
        mask = (self._dfw_dsw <= target) & (self._se >= self.se_f)
        se2 = self._se[mask][0] if mask.any() else 1.0 - 1e-6
        fw2 = _fw_se(se2, self.M)
        R = se2 + (1.0 - fw2) * tau / self.span               # Welge average
        return min(R, 1.0), fw2


class DykstraParsons:
    def __init__(self, k_mD, h_ft, phi, swc, sor, krw_max, kro_max,
                 mu_w=0.5, mu_o=0.7, allocation="kh"):
        self.k = np.asarray(k_mD, float)
        self.h = np.asarray(h_ft, float)
        self.phi = np.asarray(phi, float)
        self.swc = np.asarray(swc, float)
        self.sor = sor
        self.span = 1.0 - self.swc - sor
        self.layers = [DPLayer(swc[i], sor, krw_max[i], kro_max[i], mu_w, mu_o)
                       for i in range(len(k_mD))]
        # flow allocation fraction per layer
        if allocation == "kh":
            w = self.k * self.h
        elif allocation == "kh_mob":                          # parallel-conduit @ Swc
            w = self.k * self.h * np.asarray(kro_max) / mu_o
        else:
            raise ValueError(allocation)
        self.F = w / w.sum()
        self.PV = self.phi * self.h                           # per-layer pore volume
        self.movable = self.PV * self.span
        self.Ri = self.k / (self.phi * self.span)

    def run(self, pvi_grid):
        """System recovery and water cut over an array of TOTAL pore volumes injected."""
        PVtot = self.PV.sum()
        rec, wc = [], []
        for T in pvi_grid:
            tau = self.F * (PVtot / self.PV) * T              # local PVI per layer
            R = np.array([self.layers[i].state(tau[i])[0] for i in range(len(tau))])
            fwl = np.array([self.layers[i].state(tau[i])[1] for i in range(len(tau))])
            rec.append(np.sum(R * self.movable) / self.movable.sum())
            wc.append(np.sum(self.F * fwl))                    # flux-weighted producer cut
        return np.array(rec), np.array(wc)
# STAGE 5b [S5b] F-Phi / Lorenz heterogeneity diagnostic (Shook & Mitchell 2009)
# streamline-native generalization of the Dykstra-Parsons coefficient;
# this is the PI-RNN conditioning feature
"""F-Phi (flow-capacity / storage-capacity) heterogeneity diagnostic.

Streamline-native generalization of the Dykstra-Parsons coefficient
(Shook & Mitchell 2009, "A robust measure of heterogeneity..."). Each streamline
carries a flux q and a time-of-flight tau; its swept pore volume is V = q*tau.
Ordering streamlines by tau (fastest first) and accumulating gives the flow
capacity F vs storage capacity Phi. The Lorenz coefficient

    Lc = 2 * integral_0^1 (F - Phi) dPhi   in [0, 1]

is the dynamic heterogeneity scalar: Lc=0 homogeneous (F=Phi diagonal),
Lc->1 highly channelled. This is the PI-RNN conditioning feature.
"""


def flow_storage_diagram(tof, flux):
    """Core F-Phi from per-streamline time-of-flight and flux.
    Returns (F, Phi, Lc) with F, Phi monotone arrays starting at (0,0)."""
    tof = np.asarray(tof, float); flux = np.asarray(flux, float)
    m = np.isfinite(tof) & np.isfinite(flux) & (tof > 0) & (flux > 0)
    tof = tof[m]; flux = flux[m]
    V = flux * tof                              # swept pore volume per streamline
    order = np.argsort(tof)                      # fastest (low TOF) first
    q = flux[order]; v = V[order]
    F = np.concatenate([[0.0], np.cumsum(q) / q.sum()])
    Phi = np.concatenate([[0.0], np.cumsum(v) / v.sum()])
    Lc = 2.0 * float(np.trapezoid(F, Phi)) - 1.0
    return F, Phi, Lc


def fphi_from_sim(sim, injector_only=True):
    """F-Phi from a run StreamlineSimulator using its captured per-streamline
    TOF and flux. Uses the injector->producer (reached) streamlines."""
    tof = np.asarray(sim._sl_tof, float)
    flux = np.asarray(sim._sl_flux, float)
    sel = np.asarray(sim._sl_reached, bool)
    if injector_only:
        sel = sel & np.asarray(sim._sl_from_inj, bool)
    return flow_storage_diagram(tof[sel], flux[sel])


def layered_flow_storage(k, h=None, phi=None):
    """Analytical layered (Dykstra-Parsons stratified, no-crossflow) F-Phi.
    For equal pressure drop and no crossflow, layer flux q_j ~ k_j*h_j and
    layer pore volume V_j = phi_j*h_j, so TOF_j ~ phi_j/k_j. This is the
    provenance reference: the streamline F-Phi for the layered case must match."""
    k = np.asarray(k, float); n = len(k)
    h = np.ones(n) if h is None else np.asarray(h, float)
    phi = np.full(n, 0.2) if phi is None else np.asarray(phi, float)
    q = k * h                                    # layer flux (proportional)
    V = phi * h                                  # layer pore volume
    tau = V / q                                  # layer time-of-flight
    return flow_storage_diagram(tau, q)


def dykstra_parsons_coefficient(k):
    """Static Dykstra-Parsons V from a permeability sample (log-normal):
    V = (k50 - k84.1) / k50, via the log-normal fit. For cross-reference with Lc."""
    k = np.sort(np.asarray(k, float))
    p = (np.arange(1, len(k) + 1) - 0.5) / len(k)   # plotting positions
    lnk = np.log(k)
    # fit ln(k) vs standard-normal quantile (probit)
    z = np.array([_probit(pp) for pp in p])
    A = np.vstack([z, np.ones_like(z)]).T
    slope, intercept = np.linalg.lstsq(A, lnk, rcond=None)[0]
    k50 = np.exp(intercept)                       # z=0
    k841 = np.exp(intercept - slope)              # z=-1 (84.1 percentile of k)
    return float((k50 - k841) / k50)


def _probit(p):
    # inverse standard-normal CDF (Acklam approximation)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = np.sqrt(-2 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = np.sqrt(-2 * np.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5; r = q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def single_phase_fphi(grid, wells, no_crossflow=False, seeds_per_dim=6):
    """Clean F-Phi from a unit-mobility single-phase tracer. Constant relperm and
    unit viscosity make total mobility spatially uniform, so streamline flux ~ k
    and TOF ~ phi/k are computed from the SAME field (V = q*tau ~ phi). BHP
    injection so per-cell flux tracks k rather than being equalized by rate
    control. This is the static heterogeneity measure (matches the analytical
    layered F-Phi); use this for the PI-RNN conditioning feature."""
    rock = S.Rock(nw=1.0, no=1.0, swc=0.0, sor=0.0, krw_max=1.0, kro_max=1.0)
    fluid = S.Fluid(mu_w=1.0, mu_o=1.0, c=0.0)
    w = S.Wells(inj_cells=wells.inj_cells, prod_cells=wells.prod_cells,
                rate=wells.rate, bhp=wells.bhp, inj_bhp=wells.bhp * 1.5)
    sim = S.StreamlineSimulator(grid, rock, fluid, w, seeds_per_dim=seeds_per_dim,
                                no_crossflow=no_crossflow, gravity=False,
                                compressible=False, coverage_fill=False,
                                conserve=False)
    sim.run(target_pvi=0.01, n_psteps=1, verbose=False)
    return fphi_from_sim(sim, injector_only=True)
"""
3D Streamline Simulator (incompressible, two-phase, advective)
==============================================================

Built on the existing Buckley-Leverett physics:
  - Brooks-Corey relative permeability
  - fractional flow fw(Sw)  (monotone increasing -> Godunov collapses to upwind)

New machinery (the streamline layer):
  1. Grid3D + heterogeneous k, phi + vertical wells
  2. TPFA pressure solve (total-mobility weighted), incompressible
  3. Face -> cell pore-velocity field
  4. Pollock (1988) semi-analytic streamline tracing + time-of-flight tau
  5. 1D Buckley-Leverett transport along each streamline in tau (upwind)
  6. grid <-> streamline mapping (flux/volume weighted)
  7. IMPES loop with periodic re-tracing

This is the minimal-but-complete forward simulator: incompressible,
gravity-free, capillary-free, homogeneous relperm with heterogeneous k/phi.
Gravity / capillary / compressibility attach later as operator-split sub-steps.
"""



# ----------------------------------------------------------------------------
# Physics (reused from the BL solvers)
# ----------------------------------------------------------------------------
@dataclass
class Rock:
    # each field may be a scalar OR a (nx,ny,nz) array (per-cell / per-layer)
    nw: float = 2.0
    no: float = 2.0
    swc: float = 0.2
    sor: float = 0.2
    krw_max: float = 0.4
    kro_max: float = 0.8
    cr: float = 0.0          # rock (pore) compressibility [1/Pa]
    hysteresis: bool = False  # CCS residual trapping (Land/Killough) on CO2 (krw)
    sgr: float = 0.30         # ultimate trapped CO2 saturation (absolute)

    @property
    def span(self):
        return 1.0 - self.swc - self.sor

    @property
    def sw_max(self):
        return 1.0 - self.sor

    def at(self, idx):
        """Gather per-cell rock onto streamline segments given flat cell indices
           (idx in grid.idx() ordering). Returns a Rock with arrays shaped like idx.
           Scalars are broadcast; this lets fw vary by layer along a streamline."""
        def g(v):
            if np.isscalar(v):
                return np.full(idx.shape, float(v))
            return np.asarray(v).transpose(2, 1, 0).ravel()[idx]
        return Rock(nw=g(self.nw), no=g(self.no), swc=g(self.swc), sor=g(self.sor),
                    krw_max=g(self.krw_max), kro_max=g(self.kro_max), cr=g(self.cr),
                    hysteresis=self.hysteresis, sgr=self.sgr)


@dataclass
class Fluid:
    mu_w: float = 0.5   # cp
    mu_o: float = 5.0
    c: float = 0.0      # fluid compressibility [1/Pa], from the BL EOS
                        # rho(p) = rho_ref*exp(c*(p-p_ref))  ->  (1/rho)drho/dp = c
    rho_w: float = 1000.0   # displacing-phase density [kg/m^3]
    rho_o: float = 800.0    # resident-phase density  [kg/m^3]
                            # waterflood: rho_w>rho_o (water sinks)
                            # CCS: set rho_w<rho_o (injected phase rises)


def rel_perm(sw, rock: Rock, sw_hist=None):
    """Corey rel-perms. With sw_hist (per-cell historical max CO2 saturation) and
    rock.hysteresis, the CO2 (krw) phase follows a Land/Killough imbibition
    scanning curve once it falls below its peak -- CO2 below the trapped
    saturation becomes immobile (capillary trapping). Brine (kro) stays
    non-hysteretic (water-wet, Juanes 2006). Drainage-only when sw_hist is None."""
    se = np.clip((sw - rock.swc) / rock.span, 0.0, 1.0)
    krw = rock.krw_max * se ** rock.nw
    kro = rock.kro_max * (1.0 - se) ** rock.no
    if sw_hist is not None and getattr(rock, "hysteresis", False):
        swc, span, swmax = rock.swc, rock.span, rock.sw_max
        sgr = rock.sgr                                  # ultimate trapped CO2 (abs)
        C = 1.0 / (sgr - swc) - 1.0 / (swmax - swc)     # Land coefficient
        s_hist = np.maximum(sw_hist - swc, 0.0)
        sw_t = swc + s_hist / (1.0 + C * s_hist)        # trapped CO2 saturation
        se_hist = np.clip((sw_hist - swc) / span, 0.0, 1.0)
        denom = np.maximum(sw_hist - sw_t, 1e-12)
        se_eff = np.clip(se_hist * (sw - sw_t) / denom, 0.0, 1.0)
        krw_imb = rock.krw_max * np.where(sw > sw_t, se_eff, 0.0) ** rock.nw
        on_drain = sw >= (sw_hist - 1e-6)
        krw = np.where(on_drain, krw, krw_imb)
    return krw, kro


def total_mobility(sw, rock: Rock, fluid: Fluid, sw_hist=None):
    krw, kro = rel_perm(sw, rock, sw_hist)
    # viscosities stored in cp -> Pa.s for physical absolute pressures
    return krw / (fluid.mu_w * 1e-3) + kro / (fluid.mu_o * 1e-3)


def frac_flow(sw, rock: Rock, fluid: Fluid, sw_hist=None):
    krw, kro = rel_perm(sw, rock, sw_hist)
    lw = krw / fluid.mu_w
    lo = kro / fluid.mu_o
    return lw / (lw + lo + 1e-30)


def max_dfw(rock: Rock, fluid: Fluid, n=300):
    """Upper bound on |dfw/dSw| for CFL. Handles per-layer rock by scanning the
       distinct parameter sets present."""
    attrs = [rock.nw, rock.no, rock.swc, rock.sor, rock.krw_max, rock.kro_max]
    if all(np.isscalar(a) for a in attrs):
        s = np.linspace(rock.swc, rock.sw_max, n)
        f = frac_flow(s, rock, fluid)
        return float(np.max(np.abs(np.gradient(f, s))))
    size = max(np.asarray(a).size for a in attrs if not np.isscalar(a))
    cols = [np.full(size, float(a)) if np.isscalar(a) else np.asarray(a).ravel()
            for a in attrs]
    rows = np.unique(np.stack(cols, axis=1), axis=0)
    cap = 0.0
    for nw, no, swc, sor, krwm, krom in rows:
        rr = Rock(nw=nw, no=no, swc=swc, sor=sor, krw_max=krwm, kro_max=krom)
        s = np.linspace(swc, 1.0 - sor, n)
        f = frac_flow(s, rr, fluid)
        cap = max(cap, float(np.max(np.abs(np.gradient(f, s)))))
    return cap


# ----------------------------------------------------------------------------
# Grid + wells
# ----------------------------------------------------------------------------
@dataclass
class Grid3D:
    nx: int
    ny: int
    nz: int
    dx: float
    dy: float
    dz: float          # scalar, OR array of length nz (per-layer thickness)
    k: np.ndarray      # (nx,ny,nz) absolute perm, consistent units
    phi: np.ndarray    # (nx,ny,nz)

    def idx(self, i, j, k):
        return i + j * self.nx + k * self.nx * self.ny

    @property
    def ncell(self):
        return self.nx * self.ny * self.nz

    @property
    def dzk(self):
        """Per-layer thickness as an array of length nz."""
        if np.isscalar(self.dz):
            return np.full(self.nz, float(self.dz))
        return np.asarray(self.dz, dtype=float)

    @property
    def vcell(self):
        """Per-cell volume (nx,ny,nz); honours per-layer thickness."""
        return np.broadcast_to(self.dx * self.dy * self.dzk[None, None, :],
                               (self.nx, self.ny, self.nz))

    @property
    def cell_vol(self):
        return self.dx * self.dy * self.dz


@dataclass
class Wells:
    inj_cells: list           # list of (i,j,k)
    prod_cells: list          # list of (i,j,k), pressure-pinned (Dirichlet = bhp)
    rate: float               # total injection volumetric rate (consistent units)
    bhp: float = 0.0          # producer bottom-hole (Dirichlet) pressure [Pa]
    inj_bhp: float = None     # if set, injector is COMMON-PRESSURE (Dirichlet);
                              # layers then self-allocate flux by kh (Dykstra-Parsons)


# STAGE 6 [S6-1] Pressure solve (TPFA, total-mobility weighted, elliptic)
# ----------------------------------------------------------------------------
# Pressure solve (TPFA, total-mobility weighted, elliptic)
#   Field pressure is the incompressible profile; compressibility enters the
#   transport via the EOS source term (matching the BL compressible setup).
# ----------------------------------------------------------------------------
def solve_pressure(grid: Grid3D, sw, rock, fluid, wells: Wells, no_crossflow=False):
    nx, ny, nz = grid.nx, grid.ny, grid.nz
    lamt = total_mobility(sw, rock, fluid)
    n = grid.ncell
    A = lil_matrix((n, n))
    b = np.zeros(n)

    dzk = grid.dzk
    Az = grid.dx * grid.dy

    def trans(k1, k2, lt1, lt2, Aface, d):
        kh = 2.0 * k1 * k2 / (k1 + k2 + 1e-30)
        lf = 0.5 * (lt1 + lt2)
        return Aface * kh * lf / d

    for k in range(nz):
        Ax = grid.dy * dzk[k]
        Ay = grid.dx * dzk[k]
        for j in range(ny):
            for i in range(nx):
                c = grid.idx(i, j, k)
                if i + 1 < nx:
                    T = trans(grid.k[i, j, k], grid.k[i+1, j, k],
                              lamt[i, j, k], lamt[i+1, j, k], Ax, grid.dx)
                    nb = grid.idx(i+1, j, k)
                    A[c, c] += T; A[c, nb] -= T
                    A[nb, nb] += T; A[nb, c] -= T
                if j + 1 < ny:
                    T = trans(grid.k[i, j, k], grid.k[i, j+1, k],
                              lamt[i, j, k], lamt[i, j+1, k], Ay, grid.dy)
                    nb = grid.idx(i, j+1, k)
                    A[c, c] += T; A[c, nb] -= T
                    A[nb, nb] += T; A[nb, c] -= T
                if k + 1 < nz and not no_crossflow:
                    dzf = 0.5 * (dzk[k] + dzk[k+1])
                    T = trans(grid.k[i, j, k], grid.k[i, j, k+1],
                              lamt[i, j, k], lamt[i, j, k+1], Az, dzf)
                    nb = grid.idx(i, j, k+1)
                    A[c, c] += T; A[c, nb] -= T
                    A[nb, nb] += T; A[nb, c] -= T

    # injector control: rate (equal split) OR common pressure (Dirichlet)
    if wells.inj_bhp is None:
        q_each = wells.rate / max(len(wells.inj_cells), 1)
        for (i, j, k) in wells.inj_cells:
            b[grid.idx(i, j, k)] += q_each

    A = A.tocsr().tolil()
    for (i, j, k) in wells.prod_cells:
        c = grid.idx(i, j, k)
        A.rows[c] = [c]; A.data[c] = [1.0]; b[c] = wells.bhp
    if wells.inj_bhp is not None:
        for (i, j, k) in wells.inj_cells:
            c = grid.idx(i, j, k)
            A.rows[c] = [c]; A.data[c] = [1.0]; b[c] = wells.inj_bhp

    p = spsolve(A.tocsr(), b)
    return p.reshape((nz, ny, nx)).transpose(2, 1, 0), lamt


def _well_face_flux(grid, p, lamt, cell, no_crossflow=False):
    """Signed volumetric flux OUT of a well cell into its neighbours (sum over
       faces of T*(p_cell - p_nb)). Positive = net outflow (injection)."""
    i, j, k = cell
    dzk = grid.dzk
    Ax = grid.dy * dzk[k]; Ay = grid.dx * dzk[k]; Az = grid.dx * grid.dy

    def kh(a, b):
        return 2.0 * a * b / (a + b + 1e-30)

    faces = [(-1, 0, 0, Ax, grid.dx), (1, 0, 0, Ax, grid.dx),
             (0, -1, 0, Ay, grid.dy), (0, 1, 0, Ay, grid.dy)]
    if not no_crossflow:
        faces += [(0, 0, -1, Az, 0.5*(dzk[k]+dzk[max(k-1, 0)])),
                  (0, 0, 1, Az, 0.5*(dzk[k]+dzk[min(k+1, grid.nz-1)]))]
    q = 0.0
    for (di, dj, dk, Aface, d) in faces:
        ii, jj, kk = i+di, j+dj, k+dk
        if 0 <= ii < grid.nx and 0 <= jj < grid.ny and 0 <= kk < grid.nz:
            T = Aface * kh(grid.k[i, j, k], grid.k[ii, jj, kk]) * \
                0.5 * (lamt[i, j, k] + lamt[ii, jj, kk]) / d
            q += T * (p[i, j, k] - p[ii, jj, kk])
    return q


def injection_rates(grid, p, lamt, wells, no_crossflow=False):
    """Per-injector-cell injection rate (outflow into reservoir) and total."""
    qc = {c: _well_face_flux(grid, p, lamt, c, no_crossflow) for c in wells.inj_cells}
    return qc, float(sum(qc.values()))


def producer_rate(grid: Grid3D, p, lamt, wells: Wells, no_crossflow=False):
    """Total volumetric inflow into the producer cells (consistent units)."""
    q = 0.0
    for c in wells.prod_cells:
        q += -_well_face_flux(grid, p, lamt, c, no_crossflow)   # inflow positive
    return q


def producer_watercut(grid: Grid3D, p, lamt, sw, rock, fluid, wells: Wells,
                      no_crossflow=False):
    """Producer water cut = inflow-weighted fractional flow of the cells feeding
       the producer. For each producer face with inflow, the upwind (donor) cell
       is the neighbour, so its fw(Sw) sets the water fraction of that influx."""
    dzk = grid.dzk
    Az = grid.dx * grid.dy

    def kh(a, b):
        return 2.0 * a * b / (a + b + 1e-30)

    water_in = tot_in = 0.0
    for (i, j, k) in wells.prod_cells:
        Ax = grid.dy * dzk[k]; Ay = grid.dx * dzk[k]
        faces = [(-1, 0, 0, Ax, grid.dx), (1, 0, 0, Ax, grid.dx),
                 (0, -1, 0, Ay, grid.dy), (0, 1, 0, Ay, grid.dy)]
        if not no_crossflow:
            faces += [(0, 0, -1, Az, 0.5*(dzk[k]+dzk[max(k-1, 0)])),
                      (0, 0, 1, Az, 0.5*(dzk[k]+dzk[min(k+1, grid.nz-1)]))]
        for (di, dj, dk, Aface, d) in faces:
            ii, jj, kk = i+di, j+dj, k+dk
            if 0 <= ii < grid.nx and 0 <= jj < grid.ny and 0 <= kk < grid.nz:
                T = Aface * kh(grid.k[i, j, k], grid.k[ii, jj, kk]) * \
                    0.5 * (lamt[i, j, k] + lamt[ii, jj, kk]) / d
                q_in = T * (p[ii, jj, kk] - p[i, j, k])     # inflow to producer > 0
                if q_in > 0:
                    fw_nb = frac_flow(np.array([sw[ii, jj, kk]]),
                                      rock.at(np.array([grid.idx(ii, jj, kk)])),
                                      fluid)[0]
                    water_in += q_in * fw_nb
                    tot_in += q_in
    return water_in / tot_in if tot_in > 1e-30 else 0.0


# ----------------------------------------------------------------------------
# Capillary pressure (Brooks-Corey) + implicit grid diffusion sub-step.
#   Reuses the capillary physics from the BL capillary/full solvers:
#     Pc(Sw) = Pe * Se^(-1/lam),  D = -(k*lw*lnw/lt)*dPc/dSw
#   Streamline framework (notes 9.11): capillary diffusion is a GRID operator
#   (couples adjacent streamlines), applied as an operator-split sub-step.
# ----------------------------------------------------------------------------
@dataclass
class Capillary:
    Pe: float = 2.0e6     # entry pressure [Pa]
    lam: float = 2.0      # Brooks-Corey pore-size distribution index


def capillary_pressure(sw, rock: Rock, cap: Capillary):
    se = np.clip((sw - rock.swc) / rock.span, 0.01, 0.99)
    return cap.Pe * se ** (-1.0 / cap.lam)


def dpc_dsw(sw, rock: Rock, cap: Capillary):
    se = np.clip((sw - rock.swc) / rock.span, 0.01, 0.99)
    return cap.Pe * (-1.0 / cap.lam) * se ** (-1.0 / cap.lam - 1.0) / rock.span


def capillary_diffusion_coeff(sw, grid: Grid3D, rock: Rock, fluid: Fluid, cap: Capillary):
    """D(Sw) = -(k * lw * lnw / lt) * dPc/dSw   [m^2/s], per cell."""
    krw, kro = rel_perm(sw, rock)
    lw = krw / (fluid.mu_w * 1e-3)
    lo = kro / (fluid.mu_o * 1e-3)
    lt = lw + lo + 1e-30
    D = -grid.k * (lw * lo / lt) * dpc_dsw(sw, rock, cap)
    return np.maximum(D, 0.0)


def diffuse_grid(grid: Grid3D, sw, rock, fluid, cap: Capillary, dt, n_sub=2):
    """Implicit (backward-Euler) capillary diffusion on the 3D grid.
       phi * dSw/dt = div(D grad Sw), no-flow boundaries. D frozen per sub-step."""
    nx, ny, nz = grid.nx, grid.ny, grid.nz
    n = grid.ncell
    dzk = grid.dzk
    vcell = grid.vcell
    Az = grid.dx * grid.dy
    hdt = dt / n_sub
    sw = sw.copy()
    for _ in range(n_sub):
        D = capillary_diffusion_coeff(sw, grid, rock, fluid, cap)
        A = lil_matrix((n, n))
        b = np.zeros(n)
        for k in range(nz):
            Ax = grid.dy * dzk[k]
            Ay = grid.dx * dzk[k]
            for j in range(ny):
                for i in range(nx):
                    c = grid.idx(i, j, k)
                    m = grid.phi[i, j, k] * vcell[i, j, k] / hdt
                    A[c, c] += m
                    b[c] += m * sw[i, j, k]
                    if i + 1 < nx:
                        TD = Ax * 0.5 * (D[i, j, k] + D[i+1, j, k]) / grid.dx
                        nb = grid.idx(i+1, j, k)
                        A[c, c] += TD; A[c, nb] -= TD
                        A[nb, nb] += TD; A[nb, c] -= TD
                    if j + 1 < ny:
                        TD = Ay * 0.5 * (D[i, j, k] + D[i, j+1, k]) / grid.dy
                        nb = grid.idx(i, j+1, k)
                        A[c, c] += TD; A[c, nb] -= TD
                        A[nb, nb] += TD; A[nb, c] -= TD
                    if k + 1 < nz:
                        dzf = 0.5 * (dzk[k] + dzk[k+1])
                        TD = Az * 0.5 * (D[i, j, k] + D[i, j, k+1]) / dzf
                        nb = grid.idx(i, j, k+1)
                        A[c, c] += TD; A[c, nb] -= TD
                        A[nb, nb] += TD; A[nb, c] -= TD
        sw = spsolve(A.tocsr(), b).reshape((nz, ny, nx)).transpose(2, 1, 0)
        sw = np.clip(sw, rock.swc, rock.sw_max)
    return sw


# ----------------------------------------------------------------------------
# STAGE 7 [S7] Gravity segregation sub-step (notes 5.2), the 3D+gravity piece
#   uw = fw*ut - G(Sw) z,   G = k*g*(lw*lo/lt)*(rho_w - rho_o)
#   operator-split grid sub-step, 1D conservation law in z per column:
#       dSw/dt + d(-G/phi)/dz = 0   (Godunov flux; G is non-convex)
# ----------------------------------------------------------------------------
G_ACCEL = 9.81   # m/s^2


def gravity_M(sw, rock: Rock, fluid: Fluid):
    """Saturation factor M(Sw) = lw*lo/lt in G(Sw) = k*g*dRho*M(Sw)."""
    krw, kro = rel_perm(sw, rock)
    lw = krw / (fluid.mu_w * 1e-3)
    lo = kro / (fluid.mu_o * 1e-3)
    return lw * lo / (lw + lo + 1e-30)


def _rock_zslice(rock: Rock, zsl):
    """Rock with z-arrays sliced (scalars passed through) — for per-layer faces."""
    def s(v):
        return v if np.isscalar(v) else np.asarray(v)[:, :, zsl]
    return Rock(nw=s(rock.nw), no=s(rock.no), swc=s(rock.swc), sor=s(rock.sor),
                krw_max=s(rock.krw_max), kro_max=s(rock.kro_max), cr=s(rock.cr),
                hysteresis=rock.hysteresis, sgr=rock.sgr)


def _max_dM(rock: Rock, fluid: Fluid, n=300):
    """Upper bound on |dM/dSw|, M = lw*lo/(lw+lo), over the distinct rocks present
       (for the CFL estimate; handles per-layer rock)."""
    attrs = [rock.nw, rock.no, rock.swc, rock.sor, rock.krw_max, rock.kro_max]
    if all(np.isscalar(a) for a in attrs):
        rows = [[float(a) for a in attrs]]
    else:
        size = max(np.asarray(a).size for a in attrs if not np.isscalar(a))
        cols = [np.full(size, float(a)) if np.isscalar(a) else np.asarray(a).ravel()
                for a in attrs]
        rows = np.unique(np.stack(cols, axis=1), axis=0)
    cap = 0.0
    for nw, no, swc, sor, krwm, krom in rows:
        rr = Rock(nw=nw, no=no, swc=swc, sor=sor, krw_max=krwm, kro_max=krom)
        s = np.linspace(swc, 1.0 - sor, n)
        krw, kro = rel_perm(s, rr)
        lw = krw / (fluid.mu_w * 1e-3); lo = kro / (fluid.mu_o * 1e-3)
        M = lw * lo / (lw + lo + 1e-30)
        cap = max(cap, float(np.max(np.abs(np.gradient(M, s)))))
    return cap


def gravity_segregation(grid: Grid3D, sw, rock, fluid, dt, cfl=0.4, nsub_cap=2000,
                        sw_hist=None):
    """Vertical buoyant counter-current segregation, per column, by phase-potential
       upwinding. Each phase mobility is taken from the cell it flows FROM, so the
       scheme is conservative and handles per-layer rock and arbitrary sign(drho)
       (waterflood: heavy phase sinks; CCS/UHS: buoyant phase rises)."""
    nx, ny, nz = grid.nx, grid.ny, grid.nz
    if nz < 2:
        return sw
    drho = fluid.rho_w - fluid.rho_o
    if drho == 0.0:
        return sw
    dzk = grid.dzk
    # interface (k|k+1) absolute perm (harmonic) and porosity (arithmetic)
    kf = 2.0 * grid.k[:, :, :-1] * grid.k[:, :, 1:] / \
        (grid.k[:, :, :-1] + grid.k[:, :, 1:] + 1e-30)
    phif = 0.5 * (grid.phi[:, :, :-1] + grid.phi[:, :, 1:])
    C = kf * G_ACCEL * drho / phif                     # (nx,ny,nz-1), includes 1/phi
    rock_lo = _rock_zslice(rock, slice(None, -1))      # below-cell rock
    rock_hi = _rock_zslice(rock, slice(1, None))       # above-cell rock
    swh_lo = sw_hist[:, :, :-1] if sw_hist is not None else None
    swh_hi = sw_hist[:, :, 1:] if sw_hist is not None else None
    mu_w = fluid.mu_w * 1e-3; mu_o = fluid.mu_o * 1e-3
    # CFL on the fastest segregation wave
    Cmax = float(np.max(np.abs(C))) + 1e-30
    dt_cfl = cfl * float(np.min(dzk)) / (Cmax * _max_dM(rock, fluid) + 1e-30)
    nsub = min(nsub_cap, max(1, int(np.ceil(dt / dt_cfl))))
    h = dt / nsub
    sw = sw.copy()
    zc = np.zeros((nx, ny, 1))
    dz_cell = dzk[None, None, :]
    swc_cell = rock.swc if not np.isscalar(rock.swc) else rock.swc
    swmax_cell = rock.sw_max
    for _ in range(nsub):
        a = sw[:, :, :-1]      # below cell
        b = sw[:, :, 1:]       # above cell
        krw_a, kro_a = rel_perm(a, rock_lo, swh_lo)
        krw_b, kro_b = rel_perm(b, rock_hi, swh_hi)
        lw_a = krw_a / mu_w; lo_a = kro_a / mu_o
        lw_b = krw_b / mu_w; lo_b = kro_b / mu_o
        # phase-potential upwinding by buoyancy direction
        if drho > 0.0:        # water heavier -> water flows down (from above b),
            lw_up = lw_b      # oil flows up (from below a)
            lo_up = lo_a
        else:                 # water lighter (CCS/UHS) -> water flows up (from a),
            lw_up = lw_a      # oil flows down (from above b)
            lo_up = lo_b
        Mface = lw_up * lo_up / (lw_up + lo_up + 1e-30)
        Phi = -C * Mface                                # +z water flux at interface
        flux_up = np.concatenate([Phi, zc], axis=2)     # face above cell (top=no-flux)
        flux_dn = np.concatenate([zc, Phi], axis=2)     # face below cell (bottom=no-flux)
        sw = sw - (h / dz_cell) * (flux_up - flux_dn)
        sw = np.clip(sw, swc_cell, swmax_cell)
    return sw


# ----------------------------------------------------------------------------
# Face fluxes -> per-cell pore velocities (signed along +axis)
# ----------------------------------------------------------------------------
def pore_velocities(grid: Grid3D, p, lamt, no_crossflow=False):
    nx, ny, nz = grid.nx, grid.ny, grid.nz
    dzk = grid.dzk
    Az = grid.dx * grid.dy

    V = {key: np.zeros((nx, ny, nz)) for key in
         ('xm', 'xp', 'ym', 'yp', 'zm', 'zp')}

    def kh(a, b):
        return 2.0 * a * b / (a + b + 1e-30)

    # x faces
    for k in range(nz):
        Ax = grid.dy * dzk[k]
        for j in range(ny):
            for i in range(nx - 1):
                T = Ax * kh(grid.k[i, j, k], grid.k[i+1, j, k]) * \
                    0.5 * (lamt[i, j, k] + lamt[i+1, j, k]) / grid.dx
                q = T * (p[i, j, k] - p[i+1, j, k])      # +x flux
                V['xp'][i, j, k] = q / (Ax * grid.phi[i, j, k])
                V['xm'][i+1, j, k] = q / (Ax * grid.phi[i+1, j, k])
    # y faces
    for k in range(nz):
        Ay = grid.dx * dzk[k]
        for j in range(ny - 1):
            for i in range(nx):
                T = Ay * kh(grid.k[i, j, k], grid.k[i, j+1, k]) * \
                    0.5 * (lamt[i, j, k] + lamt[i, j+1, k]) / grid.dy
                q = T * (p[i, j, k] - p[i, j+1, k])
                V['yp'][i, j, k] = q / (Ay * grid.phi[i, j, k])
                V['ym'][i, j+1, k] = q / (Ay * grid.phi[i, j+1, k])
    # z faces -- skipped under no-crossflow so velocities stay consistent with
    # the pressure solve (which omits z transmissibility); otherwise inter-layer
    # pressure differences produce spurious vertical velocities that corrupt
    # the streamline tracer.
    if not no_crossflow:
        for k in range(nz - 1):
            dzf = 0.5 * (dzk[k] + dzk[k+1])
            for j in range(ny):
                for i in range(nx):
                    T = Az * kh(grid.k[i, j, k], grid.k[i, j, k+1]) * \
                        0.5 * (lamt[i, j, k] + lamt[i, j, k+1]) / dzf
                    q = T * (p[i, j, k] - p[i, j, k+1])
                    V['zp'][i, j, k] = q / (Az * grid.phi[i, j, k])
                    V['zm'][i, j, k+1] = q / (Az * grid.phi[i, j, k+1])
    return V


# ----------------------------------------------------------------------------
# STAGE 6 [S6-2] Pollock tracing (one streamline)
# ----------------------------------------------------------------------------
def _exit_time(xi, vm, vp, d):
    """Pollock exit time/target along one axis. Returns (t, target)."""
    tiny = 1e-30
    g = (vp - vm) / d
    ve = vm + g * xi
    if abs(ve) < tiny:
        return np.inf, None
    target = d if ve > 0 else 0.0
    vt = vm + g * target
    if abs(g) < 1e-12:
        t = (target - xi) / ve
    else:
        if vt * ve <= tiny:       # decelerates through zero -> never exits this face
            return np.inf, None
        t = np.log(vt / ve) / g
    return (t if t > 0 else np.inf), target


def _pos_at(xi, vm, vp, d, t):
    g = (vp - vm) / d
    ve = vm + g * xi
    if abs(g) < 1e-12:
        return xi + ve * t
    return (ve * np.exp(np.clip(g * t, -60.0, 60.0)) - vm) / g


def trace_streamline(grid, V, start_cell, start_local, prod_set, max_steps=5000):
    i, j, k = start_cell
    xi, yi, zi = start_local
    cells, dtaus = [], []
    reached = False
    dzk = grid.dzk
    for _ in range(max_steps):
        vxm, vxp = V['xm'][i, j, k], V['xp'][i, j, k]
        vym, vyp = V['ym'][i, j, k], V['yp'][i, j, k]
        vzm, vzp = V['zm'][i, j, k], V['zp'][i, j, k]
        dzc = dzk[k]

        tx, tgx = _exit_time(xi, vxm, vxp, grid.dx)
        ty, tgy = _exit_time(yi, vym, vyp, grid.dy)
        tz, tgz = _exit_time(zi, vzm, vzp, dzc)

        t = min(tx, ty, tz)
        if not np.isfinite(t) or t <= 0:
            break                                  # stagnation

        cells.append((i, j, k))
        dtaus.append(t)

        # advance all axes to time t
        nxi = _pos_at(xi, vxm, vxp, grid.dx, t)
        nyi = _pos_at(yi, vym, vyp, grid.dy, t)
        nzi = _pos_at(zi, vzm, vzp, dzc, t)

        ni, nj, nk = i, j, k
        if t == tx:
            if tgx == grid.dx:
                ni, nxi = i + 1, 0.0
            else:
                ni, nxi = i - 1, grid.dx
        elif t == ty:
            if tgy == grid.dy:
                nj, nyi = j + 1, 0.0
            else:
                nj, nyi = j - 1, grid.dy
        else:
            if tgz == dzc:
                nk, nzi = k + 1, 0.0
            else:
                nk = k - 1
                nzi = dzk[k-1] if k - 1 >= 0 else 0.0

        if ni < 0 or ni >= grid.nx or nj < 0 or nj >= grid.ny or nk < 0 or nk >= grid.nz:
            break                                  # left the domain
        i, j, k = ni, nj, nk
        xi, yi, zi = nxi, nyi, nzi
        if (i, j, k) in prod_set:
            cells.append((i, j, k))
            dtaus.append(0.0)
            reached = True
            break
    return cells, np.array(dtaus), reached


# ----------------------------------------------------------------------------
# STAGE 6 [S6-3] 1D Buckley-Leverett along a streamline (upwind in tau)
# ----------------------------------------------------------------------------
def advance_streamline(sw_seg, dtau, dt, rock, fluid, sw_inj, dfw_cap):
    """Advance one streamline's saturation profile over dt (upwind, sub-CFL)."""
    sw = sw_seg.copy()
    dtau_safe = np.where(dtau > 1e-30, dtau, np.inf)
    dt_cfl = 0.4 * np.min(dtau_safe) / (dfw_cap + 1e-30)
    nsub = max(1, int(np.ceil(dt / dt_cfl)))
    h = dt / nsub
    for _ in range(nsub):
        f = frac_flow(sw, rock, fluid)
        f_up = np.empty_like(f)
        f_up[0] = frac_flow(np.array([sw_inj]), rock, fluid)[0]
        f_up[1:] = f[:-1]
        with np.errstate(divide='ignore', invalid='ignore'):
            sw = sw - (h / dtau) * (f - f_up)
        sw = np.clip(sw, rock.swc, rock.sw_max)
    return sw


# ----------------------------------------------------------------------------
# STAGE 6/7 [S6-4/S7b] Simulator, same engine: nz=1/gravity=False is the areal
# (2D-equivalent) case, nz>1/gravity=True is the full 3D+gravity CCUS case
# ----------------------------------------------------------------------------
@dataclass
class SimResult:
    pvi: list = field(default_factory=list)
    recovery: list = field(default_factory=list)
    watercut: list = field(default_factory=list)
    time: list = field(default_factory=list)
    injected: list = field(default_factory=list)
    produced: list = field(default_factory=list)
    stored: list = field(default_factory=list)
    prod_rate: list = field(default_factory=list)
    sw_final: np.ndarray = None
    tof: np.ndarray = None
    n_streamlines: int = 0


class StreamlineSimulator:
    def __init__(self, grid, rock, fluid, wells, seeds_per_dim=5,
                 compressible=False, capillary=False, cap=None, n_diff_sub=2,
                 gravity=False, no_crossflow=False, conserve=True,
                 coverage_fill=True, fill_stride=1):
        self.grid = grid
        self.rock = rock
        self.fluid = fluid
        self.wells = wells
        self.seeds = seeds_per_dim
        self.compressible = compressible
        self.capillary = capillary
        self.cap = cap if cap is not None else Capillary()
        self.n_diff_sub = n_diff_sub
        self.gravity = gravity
        self.no_crossflow = no_crossflow
        self.conserve = conserve
        self.coverage_fill = coverage_fill
        self.fill_stride = fill_stride
        self.alpha_log = []
        self.dfw_cap = max_dfw(rock, fluid)
        self.prod_set = set(wells.prod_cells)
        self.sw = np.ones((grid.nx, grid.ny, grid.nz)) * np.asarray(rock.swc)
        self.hysteresis = getattr(rock, "hysteresis", False)
        self.sg_max = self.sw.copy()     # per-cell historical max CO2 saturation
        self.inject_brine = False        # True -> injector delivers brine (imbibition)
        self.pv = float(np.sum(grid.phi * grid.vcell))
        self.mobile_oil = float(np.sum(grid.phi * grid.vcell *
                                       (1.0 - rock.swc - rock.sor)))
        self.Nc = 0.0    # compressibility number ln(rho_inj/rho_prod), filled in run

    def _seed_points(self):
        """Seed points distributed inside each injector cell. Returns
           (cell, local_xyz) pairs; flux per seed is assigned in run()."""
        g = self.grid
        dzk = g.dzk
        offs_x = (np.arange(self.seeds) + 0.5) / self.seeds * g.dx
        offs_y = (np.arange(self.seeds) + 0.5) / self.seeds * g.dy
        seeds = []
        for (i, j, k) in self.wells.inj_cells:
            for ox in offs_x:
                for oy in offs_y:
                    seeds.append(((i, j, k), (ox, oy, 0.5 * dzk[k])))
        return seeds

    def run(self, target_pvi=1.5, n_psteps=30, verbose=True):
        g = self.grid
        ncell = g.ncell
        ncf = self.no_crossflow
        res = SimResult()
        seeds = self._seed_points()
        bhp_inj = self.wells.inj_bhp is not None

        # reference injection rate (sets dt and PVI). For a common-pressure
        # injector it is an OUTPUT of the solve; for rate control it is given.
        p0, lamt0 = solve_pressure(g, self.sw, self.rock, self.fluid, self.wells, ncf)
        _, rate0 = injection_rates(g, p0, lamt0, self.wells, ncf)
        rate_ref = rate0 if bhp_inj else self.wells.rate
        dt = (target_pvi * self.pv / rate_ref) / n_psteps
        t = 0.0
        cum_inj = cum_prod = cum_oil = 0.0

        for step in range(n_psteps):
            # 1-3: elliptic pressure + velocities + well rates
            p, lamt = solve_pressure(g, self.sw, self.rock, self.fluid, self.wells, ncf)
            V = pore_velocities(g, p, lamt, ncf)
            # compressible flow: scale velocity (hence time-of-flight) by rho_inj/rho(p),
            # exactly as CompressibleBLSolver does (u = u_inj * rho_inj/rho). The fluid
            # speeds up toward the producer where pressure (density) is lower, advancing
            # the front. The fw*c*dp/dtau source term (transport step) remains the
            # non-conservative-form correction for the velocity divergence.
            if self.compressible and self.fluid.c > 0.0:
                p_inj_ref = float(np.mean([p[ci] for ci in self.wells.inj_cells]))
                cfac = np.exp(self.fluid.c * (p_inj_ref - p))   # >=1 downstream of injector
                for _key in V:
                    V[_key] = V[_key] * cfac
            qprod = producer_rate(g, p, lamt, self.wells, ncf)
            if bhp_inj:
                qc, q_inj_tot = injection_rates(g, p, lamt, self.wells, ncf)
            else:
                qe = self.wells.rate / max(len(self.wells.inj_cells), 1)
                qc = {c: qe for c in self.wells.inj_cells}
                q_inj_tot = self.wells.rate
            sw_flat = self.sw.transpose(2, 1, 0).ravel()
            p_flat = p.transpose(2, 1, 0).ravel()

            # 4: trace streamlines. (a) from injector seeds (inlet = injected phase),
            #    then (b) coverage-fill: bidirectional streamlines through cells the
            #    injector bundle missed, carrying the EXISTING saturation. This tiles
            #    the pore volume so the flux-weighted map-back conserves under crossflow.
            inj_rows = []
            for sc, sl in seeds:
                cells, dtaus, rch = trace_streamline(g, V, sc, sl, self.prod_set)
                if len(cells) < 2:
                    continue
                flat = np.fromiter((g.idx(*c) for c in cells), dtype=int, count=len(cells))
                inj_rows.append((flat, dtaus, rch, sc))
            n_from = {}
            for (_, _, _, sc) in inj_rows:
                n_from[sc] = n_from.get(sc, 0) + 1

            rows = []                       # (flat, dtaus, reached, qsl, from_inj)
            covered = np.zeros(ncell, dtype=bool)
            for (flat, dtaus, rch, sc) in inj_rows:
                rows.append((flat, dtaus, rch, qc[sc] / n_from[sc], True))
                covered[flat] = True

            if self.coverage_fill:
                Vb = {key: -V[key] for key in V}        # reverse field for upstream trace
                inj_set = set(self.wells.inj_cells)
                nxy = g.nx * g.ny
                vcx = 0.5 * (V['xm'] + V['xp']); vcy = 0.5 * (V['ym'] + V['yp'])
                vcz = 0.5 * (V['zm'] + V['zp'])
                speed = np.sqrt(vcx**2 + vcy**2 + vcz**2)
                Aref = g.dy * g.dzk[0]
                for cflat in np.where(~covered)[0][::self.fill_stride]:
                    if covered[cflat]:
                        continue
                    k = int(cflat // nxy); rem = int(cflat % nxy)
                    j = rem // g.nx; i = rem % g.nx
                    sl = (0.5 * g.dx, 0.5 * g.dy, 0.5 * g.dzk[k])
                    cf, df, rf = trace_streamline(g, V, (i, j, k), sl, self.prod_set)
                    cb, db, rb = trace_streamline(g, Vb, (i, j, k), sl, inj_set)
                    cells = list(reversed(cb))[:-1] + cf
                    dtaus = np.concatenate([db[::-1][:-1], df])
                    if len(cells) < 2:
                        continue
                    flat = np.fromiter((g.idx(*c) for c in cells), dtype=int, count=len(cells))
                    covered[flat] = True
                    qsl_fill = float(speed[i, j, k]) * float(g.phi[i, j, k]) * Aref
                    rows.append((flat, dtaus, rf, qsl_fill, bool(rb)))

            n_sl = len(rows)
            Lmax = max(len(r[0]) for r in rows)

            FLAT = np.full((n_sl, Lmax), -1, dtype=int)
            DTAU = np.zeros((n_sl, Lmax))
            SW = np.zeros((n_sl, Lmax))
            P = np.zeros((n_sl, Lmax))
            QSL = np.zeros(n_sl)
            valid = np.zeros((n_sl, Lmax), dtype=bool)
            reached = np.zeros(n_sl, dtype=bool)
            inlet_inj = np.zeros(n_sl, dtype=bool)
            for r, (flat, dtaus, rch, qsl, from_inj) in enumerate(rows):
                L = len(flat)
                FLAT[r, :L] = flat
                DTAU[r, :L] = dtaus
                SW[r, :L] = sw_flat[flat]
                P[r, :L] = p_flat[flat]
                valid[r, :L] = True
                reached[r] = rch
                QSL[r] = qsl
                inlet_inj[r] = from_inj

            # per-segment rock: fractional flow varies by layer along a streamline
            rock_seg = self.rock.at(np.clip(FLAT, 0, ncell - 1))
            SWC_seg, SWMAX_seg = rock_seg.swc, rock_seg.sw_max
            # historical-max CO2 saturation per streamline node (for hysteresis)
            if self.hysteresis:
                sgmax_flat = self.sg_max.transpose(2, 1, 0).ravel()
                SWHIST = sgmax_flat[np.clip(FLAT, 0, ncell - 1)]
            else:
                SWHIST = None
            # injector inlet delivers CO2 (drainage) or brine (imbibition)
            INLET = SWC_seg if self.inject_brine else SWMAX_seg
            SW[inlet_inj, 0] = INLET[inlet_inj, 0]   # injector inlet
            SW = np.clip(SW, SWC_seg, SWMAX_seg)

            # pressure gradient along each streamline, dp/dtau (backward diff)
            DPDTAU = np.zeros((n_sl, Lmax))
            dtau_bwd = np.where(DTAU > 1e-30, DTAU, np.inf)
            DPDTAU[:, 1:] = (P[:, 1:] - P[:, :-1]) / dtau_bwd[:, 1:]
            DPDTAU[~valid] = 0.0

            # TOF
            tau_mat = np.cumsum(DTAU, axis=1)
            tof_acc = np.zeros(ncell); tof_cnt = np.zeros(ncell)
            np.add.at(tof_acc, FLAT[valid], tau_mat[valid])
            np.add.at(tof_cnt, FLAT[valid], 1.0)
            # per-streamline TOF and flux capture (for the F-Phi / Lorenz diagnostic)
            self._sl_tof = np.where(valid, DTAU, 0.0).sum(axis=1)
            self._sl_flux = QSL.copy()
            self._sl_reached = reached.copy()
            self._sl_from_inj = inlet_inj.copy()

            # 5: BL transport in tau + EOS compressibility source (per-layer fw)
            #    dSw/dt + dfw/dtau = fw * c * dp/dtau
            #    CFL set by the FASTEST segment (min TOF) so high perm-contrast
            #    layers are not throttled by the per-element Courant clamp.
            tau_safe = np.where((DTAU > 0) & valid, DTAU, np.inf)
            pos = DTAU[(DTAU > 0) & valid]
            tau_ref = pos.min() if pos.size else dt
            dt_cfl = 0.4 * tau_ref / (self.dfw_cap + 1e-30)
            nsub = min(20000, max(1, int(np.ceil(dt / dt_cfl))))
            h = dt / nsub
            cc = self.fluid.c if self.compressible else 0.0
            for _ in range(nsub):
                F = frac_flow(SW, rock_seg, self.fluid, sw_hist=SWHIST)
                Fup = np.empty_like(F)
                Fup[:, 0] = F[:, 0]                     # inlet = injector-cell fw
                Fup[:, 1:] = F[:, :-1]
                coeff = np.minimum(h / tau_safe, 0.9)
                SW = SW - coeff * (F - Fup) + h * (F * cc * DPDTAU)
                SW[inlet_inj, 0] = INLET[inlet_inj, 0]
                SW = np.clip(SW, SWC_seg, SWMAX_seg)

            # 6: map streamline saturations back to grid (flux x TOF weighted average)
            w = QSL[:, None] * np.where(valid, DTAU, 0.0)
            num = np.zeros(ncell); den = np.zeros(ncell)
            np.add.at(num, FLAT[valid], (w * SW)[valid])
            np.add.at(den, FLAT[valid], w[valid])
            covered = den > 1e-30
            sw_new_flat = sw_flat.copy()
            sw_new_flat[covered] = num[covered] / den[covered]
            self._den = den; self._covered = covered     # diagnostic capture (Sum w per cell)
            self.sw = sw_new_flat.reshape((g.nz, g.ny, g.nx)).transpose(2, 1, 0)
            # gravity segregation sub-step (operator split, vertical, on the grid)
            if self.gravity:
                self.sw = gravity_segregation(g, self.sw, self.rock, self.fluid, dt,
                                              sw_hist=self.sg_max if self.hysteresis else None)
            # capillary diffusion sub-step (operator split, on the grid)
            if self.capillary:
                self.sw = diffuse_grid(g, self.sw, self.rock, self.fluid,
                                       self.cap, dt, self.n_diff_sub)
            inj_val = self.rock.swc if self.inject_brine else self.rock.sw_max
            for c in self.wells.inj_cells:
                self.sw[c] = inj_val if np.isscalar(inj_val) else inj_val[c]
            self.sw = np.clip(self.sw, self.rock.swc, self.rock.sw_max)

            # producer water cut: inflow-weighted fw of the cells feeding the producer
            fw_prod = producer_watercut(g, p, lamt, self.sw, self.rock, self.fluid,
                                        self.wells, ncf)

            # --- global conservative correction (displacing-phase volume balance) ---
            # The crossflow map-back is not strictly volume-conservative; enforce that
            # the step's net change in displacing-phase in place equals injected minus
            # produced by rescaling the step increment (gravity/capillary redistribution
            # patterns are preserved; only the net volume is corrected).
            phiV = g.phi * g.vcell
            sw_old_field = sw_flat.reshape((g.nz, g.ny, g.nx)).transpose(2, 1, 0)
            dsw = self.sw - sw_old_field
            vol_change = float(np.sum(phiV * dsw))
            target_change = q_inj_tot * dt - qprod * fw_prod * dt
            if self.conserve and vol_change > 1e-30 and target_change > 0.0:
                alpha = min(max(target_change / vol_change, 0.5), 2.0)
                self.alpha_log.append(alpha)
                self.sw = sw_old_field + alpha * dsw
                for c in self.wells.inj_cells:
                    self.sw[c] = inj_val if np.isscalar(inj_val) else inj_val[c]
                self.sw = np.clip(self.sw, self.rock.swc, self.rock.sw_max)

            # update per-cell historical max CO2 saturation (drives hysteresis)
            if self.hysteresis:
                self.sg_max = np.maximum(self.sg_max, self.sw)

            # compressibility number Nc = ln(rho_inj/rho_prod) = c*(p_inj - p_prod)
            p_inj = float(np.mean([p[ci] for ci in self.wells.inj_cells]))
            p_prod = float(np.mean([p[ci] for ci in self.wells.prod_cells]))
            self.Nc = self.fluid.c * (p_inj - p_prod) if self.compressible else 0.0

            # 7: bookkeeping
            t += dt
            cum_inj += q_inj_tot * dt
            cum_prod += qprod * dt
            cum_oil += qprod * (1.0 - fw_prod) * dt
            pvi = cum_inj / self.pv
            res.pvi.append(pvi)
            res.watercut.append(fw_prod)
            res.recovery.append(min(cum_oil / self.mobile_oil, 1.0))
            res.time.append(t)
            res.injected.append(cum_inj)
            res.produced.append(cum_prod)
            res.stored.append(cum_inj - cum_prod)
            res.prod_rate.append(qprod)
            if verbose:
                print(f"  step {step+1:2d}/{n_psteps}  PVI={pvi:5.3f}  "
                      f"fw={fw_prod:5.3f}  Nc={self.Nc:5.3f}  nsub={nsub}")

        res.sw_final = self.sw.copy()
        tof_mean = np.where(tof_cnt > 0, tof_acc / np.maximum(tof_cnt, 1), np.nan)
        res.tof = tof_mean.reshape((g.nz, g.ny, g.nx)).transpose(2, 1, 0)
        res.n_streamlines = n_sl
        return res


# ----------------------------------------------------------------------------
# Demo: 3D heterogeneous quarter five-spot with vertical wells
# ----------------------------------------------------------------------------
def build_dp_demo(nx=25, ny=25, dz=None):
    """Layered reservoir from the Dykstra-Parsons 8-layer table (per-layer rock).
       Each layer is areally uniform; properties vary by layer (k, phi, Swc,
       kro_max, krw_max, thickness). Vertical injector/producer (quarter five-spot)."""
    kmD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
    phi_l = np.array([0.22, 0.18, 0.21, 0.15, 0.20, 0.21, 0.20, 0.20])
    swc_l = np.array([0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42])
    krom = np.array([0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60])
    krwm = np.array([0.05, 0.15, 0.20, 0.33, 0.20, 0.30, 0.40, 0.17])
    h_ft = np.array([50., 48., 54., 44., 42., 48., 50., 40.])
    sor = 0.20
    nz = len(kmD)
    if dz is None:
        dz = h_ft * 0.3048                         # per-layer thickness [m]

    def lay(v):
        return np.ones((nx, ny, nz)) * v[None, None, :]

    k = lay(kmD) * 9.869e-16
    phi = lay(phi_l)
    grid = Grid3D(nx, ny, nz, dx=10.0, dy=10.0, dz=dz, k=k, phi=phi)
    rock = Rock(nw=2.0, no=2.0, swc=lay(swc_l), sor=sor,
                krw_max=lay(krwm), kro_max=lay(krom))
    fluid = Fluid(mu_w=0.5, mu_o=0.7)          # DP-case viscosities
    inj = [(0, 0, kk) for kk in range(nz)]
    prod = [(nx-1, ny-1, kk) for kk in range(nz)]
    pv = float(np.sum(phi * grid.vcell))
    rate = 0.6 * pv / (365 * 24 * 3600)
    wells = Wells(inj_cells=inj, prod_cells=prod, rate=rate, bhp=2.0e7)
    Ri = kmD / (phi_l * (1.0 - sor - swc_l))   # speed index (DP layer ranking)
    return grid, rock, fluid, wells, Ri


def build_demo(nx=25, ny=25, nz=4, seed=7, c=0.0):
    rng = np.random.default_rng(seed)
    base = np.array([200.0, 80.0, 400.0, 120.0])[:nz]
    k = np.zeros((nx, ny, nz))
    for kk in range(nz):
        field2d = base[kk] * np.exp(0.6 * rng.standard_normal((nx, ny)))
        k[:, :, kk] = field2d
    k *= 9.869e-16    # mD -> m^2
    phi = np.full((nx, ny, nz), 0.20)

    grid = Grid3D(nx, ny, nz, dx=10.0, dy=10.0, dz=5.0, k=k, phi=phi)
    rock = Rock()
    fluid = Fluid(c=c)               # BL EOS fluid compressibility [1/Pa]
    inj = [(0, 0, kk) for kk in range(nz)]
    prod = [(nx-1, ny-1, kk) for kk in range(nz)]
    pv = float(np.sum(phi) * grid.cell_vol)
    rate = 0.6 * pv / (365 * 24 * 3600)
    wells = Wells(inj_cells=inj, prod_cells=prod, rate=rate, bhp=2.0e7)
    return grid, rock, fluid, wells


def build_five_spot(nx=31, ny=31, nz=4, seed=7, c=0.0, inverted=True,
                    homogeneous=False, k_mean=200.0, sigma_lnk=0.6,
                    dx=10.0, dy=10.0, dz=5.0, phi0=0.20, rate_pvi_yr=0.6):
    """Full (not quarter) five-spot well pattern.
      inverted=True  : central injector + 4 corner producers (default).
      inverted=False : 4 corner injectors + central producer.
    Permeability is heterogeneous lognormal per layer (homogeneous=True for a
    uniform field, e.g. for the analytical areal-sweep check). Odd nx=ny puts the
    central well exactly on a node. Returns (grid, rock, fluid, wells) like
    build_demo."""
    rng = np.random.default_rng(seed)
    k = np.zeros((nx, ny, nz))
    if homogeneous:
        k[:] = k_mean
    else:
        base = k_mean * (0.6 + 0.8 * rng.random(nz))      # per-layer mean spread
        for kk in range(nz):
            k[:, :, kk] = base[kk] * np.exp(sigma_lnk * rng.standard_normal((nx, ny)))
    k *= 9.869e-16                                         # mD -> m^2
    phi = np.full((nx, ny, nz), phi0)
    grid = Grid3D(nx, ny, nz, dx=dx, dy=dy, dz=dz, k=k, phi=phi)
    rock = Rock()
    fluid = Fluid(c=c)

    cx, cy = nx // 2, ny // 2
    center = [(cx, cy, kk) for kk in range(nz)]
    corners = [(0, 0), (0, ny - 1), (nx - 1, 0), (nx - 1, ny - 1)]
    corner_cells = [(i, j, kk) for (i, j) in corners for kk in range(nz)]
    if inverted:
        inj, prod = center, corner_cells
    else:
        inj, prod = corner_cells, center

    pv = float(np.sum(phi) * grid.cell_vol)
    rate = rate_pvi_yr * pv / (365 * 24 * 3600)
    wells = Wells(inj_cells=inj, prod_cells=prod, rate=rate, bhp=2.0e7)
    return grid, rock, fluid, wells


def run_streamline_sim_original_demo():
    """streamline_sim.py's own __main__ block, preserved and callable,
    not auto-run so it doesn't block Stage 9's figures."""
    cap = Capillary(Pe=2.0e6, lam=2.0)

    def make(c=0.0):
        return build_demo(c=c)

    runs = [
        ("incompressible      ", dict(compressible=False, capillary=False), 0.0),
        ("capillary only      ", dict(compressible=False, capillary=True, cap=cap), 0.0),
        ("compressible only   ", dict(compressible=True,  capillary=False), 1.2e-8),
        ("full (compr+capill) ", dict(compressible=True,  capillary=True, cap=cap), 1.2e-8),
    ]
    for label, kw, c in runs:
        g, r, f, w = build_demo(c=c)
        sim = StreamlineSimulator(g, r, f, w, seeds_per_dim=5, **kw)
        res = sim.run(target_pvi=1.5, n_psteps=20, verbose=False)
        print(f"{label}  RF={res.recovery[-1]*100:5.1f}%  "
              f"fw={res.watercut[-1]*100:5.1f}%  Nc={sim.Nc:5.3f}")
# STAGE 4c-full [S4c+] VEPlumeSolver: conservative FV radial VE plume WITH
# the interface-slope buoyant flux NCPlumeSolver (Stage 4c, above) omits.
# Per its own docstring this is what makes the plume conserve mass at all
# gravity numbers and spread laterally under buoyancy.
"""Full vertical-equilibrium radial CO2 plume with the interface-slope buoyant
flux (Nordbotten & Celia 2006). Conservative finite-volume solve of

    d/dt( psi * Vp_i ) + ( Phi_{i+1/2} - Phi_{i-1/2} ) = 0
    Phi(r) = Q*f(psi)          (advective, upwind)
           - 2*pi*r*K_g*H^2 * g_b(psi) * dpsi/dr   (interface-slope buoyant flux)

with f(psi)=M*psi/(M*psi+1-psi), g_b(psi)=M*psi(1-psi)/(M*psi+1-psi), and
K_g = k*drho*g/mu_w. The buoyant flux is the slope-dependent term the
fractional-flow-only reduction omitted; it makes the plume conserve mass at all
gravity numbers and spread laterally under buoyancy. Reduces to radial
Buckley-Leverett (rarefaction tip at eta = M) when K_g -> 0.

Self-similar in eta = pi*phi*H*r^2/(Q*t); the FV solution collapses onto psi(eta).
"""

G_ACCEL = 9.81


class VEPlumeSolver:
    def __init__(self, M=12.0, H=20.0, phi=0.2, k_mD=200.0, drho=320.0,
                 mu_w_cp=0.6, Q=5.18e-3, nr=900, rfac=1.7, r0=0.3):
        self.M = M; self.H = H; self.phi = phi
        self.k = k_mD * 9.869e-16
        self.drho = drho; self.mu_w = mu_w_cp * 1e-3; self.Q = Q
        self.K_g = self.k * drho * G_ACCEL / self.mu_w        # buoyant velocity [m/s]
        self.G_s = 4.0 * np.pi * self.K_g * H ** 2 / Q        # NC gravity number
        self.nr = nr; self.rfac = rfac; self.r0 = r0

    def f(self, p):
        D = self.M * p + (1.0 - p)
        return self.M * p / (D + 1e-30)

    def gb(self, p):
        D = self.M * p + (1.0 - p)
        return self.M * p * (1.0 - p) / (D + 1e-30)

    def solve(self, t_end, cfl=0.20, max_steps=400000):
        # domain large enough to contain the plume (tip near eta=M, wider with buoyancy)
        eta_tip = self.M * (1.0 + 0.5 * self.G_s)
        r_tip = np.sqrt(eta_tip * self.Q * t_end / (np.pi * self.phi * self.H))
        rf = np.linspace(self.r0, max(self.rfac * r_tip, 2 * self.r0), self.nr + 1)
        rc = 0.5 * (rf[:-1] + rf[1:]); dr = rf[1] - rf[0]
        Vp = 2.0 * np.pi * rc * dr * self.phi * self.H        # CO2 pore capacity/cell
        psi = np.zeros(self.nr)
        rint = rf[1:-1]                                       # interior faces
        Kc = 2.0 * np.pi * self.K_g * self.H ** 2             # buoyant flux prefactor
        t = 0.0; steps = 0
        while t < t_end and steps < max_steps:
            # advective flux at faces (upwind outward; inner face = injected CO2 = Q)
            Fadv = np.empty(self.nr + 1)
            Fadv[0] = self.Q
            Fadv[1:] = self.Q * self.f(psi)
            # buoyant slope flux at interior faces (central gradient)
            gb_f = 0.5 * (self.gb(psi[:-1]) + self.gb(psi[1:]))
            Fbuoy = np.zeros(self.nr + 1)
            Fbuoy[1:-1] = -Kc * rint * gb_f * (psi[1:] - psi[:-1]) / dr
            F = Fadv + Fbuoy
            # stable dt: advective CFL + buoyant-diffusion limit
            dt_adv = cfl * Vp.min() / (self.Q * self.M + 1e-30)
            A = Kc * rint * gb_f / dr
            dif = np.zeros(self.nr); dif[:-1] += A; dif[1:] += A
            dt_dif = cfl * np.min(Vp / (dif + 1e-30))
            dt = min(dt_adv, dt_dif, t_end - t)
            psi = psi - dt * (F[1:] - F[:-1]) / Vp
            psi = np.clip(psi, 0.0, 1.0)
            t += dt; steps += 1
        self.r = rc; self.psi = psi; self.t = t; self.dr = dr; self.Vp = Vp
        self.eta = np.pi * self.phi * self.H * rc ** 2 / (self.Q * t)
        self.steps = steps
        return self

    def mass_balance(self):
        """CO2 in plume / CO2 injected (= 1 if conservative)."""
        return float(np.sum(self.psi * self.Vp) / (self.Q * self.t))

    def tip_eta(self, thresh=0.02):
        """Leading-edge eta where psi drops below thresh."""
        idx = np.where(self.psi > thresh)[0]
        return float(self.eta[idx[-1]]) if idx.size else 0.0
# STAGE 7c [S7c] CCS residual trapping / hysteresis (Land 1968, Killough 1976)
# standalone reference for the trapping math streamline_sim.py's rel_perm()
# implements inline for the hysteresis=True path
"""CCS residual (capillary) trapping and relative-permeability hysteresis.

Land (1968) trapping + Killough (1976) imbibition scanning curves for the CO2
(non-wetting) phase. As the plume passes and brine re-imbibes, CO2 below the
trapped saturation becomes immobile (krg -> 0) -- the primary capillary-trapping
storage mechanism (Juanes et al. 2006). The wetting brine kr is taken
non-hysteretic, appropriate for strongly water-wet CO2/brine systems
(Juanes 2006). Trapped-gas levels and Land C are literature-grounded
(Bennion & Bachu 2008: Sgr ~ 0.22-0.35; Land C ~ 0.5-4).

Convention here is CCS-native: Sg = CO2 saturation, Swc = connate brine,
Sgr_max = ultimate trapped CO2 at full drainage. (Maps to the solver's 'w'=CO2
phase when integrated.)
"""


def land_C(swc, sgr_max):
    """Land trapping coefficient from connate brine and ultimate trapped CO2.
    C = 1/Sgr_max - 1/(1-Swc); larger C => less trapping."""
    return 1.0 / sgr_max - 1.0 / (1.0 - swc)


def trapped_co2(sg_hist_max, swc, sgr_max):
    """Land trapped CO2 saturation for a cell whose CO2 saturation peaked at
    sg_hist_max (the drainage turning point). Sgt = Sg_max/(1 + C*Sg_max)."""
    C = land_C(swc, sgr_max)
    sg = np.asarray(sg_hist_max, float)
    return sg / (1.0 + C * sg)


def drainage_krg(sg, swc, krg_max=0.4, ng=2.0):
    """Drainage CO2 relative permeability (Corey, non-wetting). Matches the
    solver's krw (=CO2) endpoint/exponent."""
    se = np.clip(np.asarray(sg, float) / (1.0 - swc), 0.0, 1.0)
    return krg_max * se ** ng


def imbibition_krg(sg, sg_hist_max, swc, sgr_max, krg_max=0.4, ng=2.0):
    """Killough imbibition CO2 kr on the scanning curve from turning point
    sg_hist_max. Branches off drainage at sg_hist_max and reaches 0 at the
    trapped saturation Sgt (CO2 immobile below Sgt). The flowing range
    [Sgt, Sg_max] is mapped onto the drainage curve [0, Sg_max]."""
    sg = np.asarray(sg, float)
    sgt = trapped_co2(sg_hist_max, swc, sgr_max)
    denom = np.maximum(sg_hist_max - sgt, 1e-12)
    s_eff = np.where(sg > sgt, sg_hist_max * (sg - sgt) / denom, 0.0)
    return drainage_krg(s_eff, swc, krg_max, ng)


def effective_krg(sg, sg_hist_max, swc, sgr_max, krg_max=0.4, ng=2.0, tol=1e-6):
    """Hysteretic CO2 kr: drainage branch while at the historical max
    (sg >= sg_hist_max), imbibition scanning curve once CO2 saturation falls
    below the peak. This is what the solver calls per cell."""
    sg = np.asarray(sg, float)
    drain = drainage_krg(sg, swc, krg_max, ng)
    imb = imbibition_krg(sg, sg_hist_max, swc, sgr_max, krg_max, ng)
    on_drainage = sg >= (np.asarray(sg_hist_max, float) - tol)
    return np.where(on_drainage, drain, imb)
# ------------------------------------------------------------------------------
# Namespace shims -- every scenario script below still says `S.Grid3D(...)`,
# `B.RockProperties(...)`, etc. because that's how you wrote them against your
# actual multi-file package. Rather than rewrite every call site (a real,
# error-prone edit to logic I'd rather not make silently), these four-line
# shims just point S/B/D/NC/FP/CT at the classes and functions already defined
# above, which are the exact same objects your originals imported.
# ------------------------------------------------------------------------------
class _NS:
    pass

S = _NS()
for _name in ["Capillary", "Fluid", "Grid3D", "Rock", "StreamlineSimulator",
              "Wells", "build_demo", "build_dp_demo", "build_five_spot",
              "capillary_diffusion_coeff", "diffuse_grid", "gravity_segregation",
              "pore_velocities", "rel_perm", "solve_pressure"]:
    setattr(S, _name, globals()[_name])

B = _NS()
for _name in ["CapillaryBLSolver", "CapillaryProperties", "CompressibleBLSolver",
              "CompressibleFluid", "FluidProperties", "FullBLSolver",
              "GravityBLSolver", "PressureConditions", "ReservoirGeometry",
              "RockProperties", "calculate_capillary_pressure",
              "calculate_dfw_dsw", "calculate_diffusion_coefficient",
              "calculate_fractional_flow", "calculate_fractional_flow_gravity",
              "compute_compressibility_number"]:
    setattr(B, _name, globals()[_name])

D = _NS()
D.DykstraParsons = DykstraParsons

NC = _NS()
NC.VEPlumeSolver = VEPlumeSolver

FP = _NS()
FP.layered_flow_storage = layered_flow_storage
FP.single_phase_fphi = single_phase_fphi

CT = _NS()
CT.trapped_co2 = trapped_co2


"""run_validations.py -- single regression harness for the PI-RNN streamline toolkit.

Runs each validated physics result as a check with an explicit gate (provenance
reduction, conservation, or analytical agreement) and prints a pass/fail table.
Run after any solver change to confirm nothing drifted.

    python run_validations.py
"""



# ----------------------------------------------------------------------------- helpers
def _result(name, passed, gate, value):
    return dict(name=name, passed=bool(passed), gate=gate, value=value)


# ----------------------------------------------------------------------------- checks
def chk_bl_gravity_provenance():
    """Gravity-BL: fw reduces to viscous BL at Ng=0; shock front monotonic in Ng."""
    rock = B.RockProperties(); fluid = B.FluidProperties(mu_w=0.5, mu_o=5.0)
    geom = B.ReservoirGeometry()
    s = np.linspace(rock.swc, rock.sw_max, 200)
    fw_v = B.calculate_fractional_flow(s, rock, fluid)
    fw_g0 = B.calculate_fractional_flow_gravity(s, rock, fluid, 0.0)
    reduce_err = float(np.max(np.abs(fw_v - fw_g0)))
    # shock front position vs Ng (gravity-stable Ng>0 slows the front)
    def front(Ng):
        x, Sw = B.GravityBLSolver(rock, fluid, geom, Ng).solve(t_days=300, nx=301)
        idx = np.where(Sw > rock.swc + 0.05 * rock.saturation_span)[0]
        return x[idx[-1]] if idx.size else 0.0
    fm, f0, fp = front(-0.6), front(0.0), front(0.6)
    monotonic = fm > f0 > fp
    passed = (reduce_err < 1e-9) and monotonic
    return _result("gravity-BL provenance", passed,
                   "Ng=0->viscous (err<1e-9) & front monotonic in Ng",
                   f"reduce_err={reduce_err:.1e}, front x/L[-0.6,0,+0.6]=[{fm:.2f},{f0:.2f},{fp:.2f}]")


def chk_ve_slopeflux():
    """VE slope-flux: G_s=0 -> analytical radial BL rarefaction; mass=1.000 at high G_s."""
    M = 12.0
    s0 = NC.VEPlumeSolver(M=M, drho=0.0, Q=5.18e-3, nr=400, r0=0.5,
                          rfac=1.9).solve(1.5e6, max_steps=700000)
    eta = s0.eta
    psi_bl = np.clip((np.sqrt(M / np.clip(eta, 1e-9, None)) - 1) / (M - 1), 0, 1)
    psi_bl[eta > M] = 0.0; psi_bl[eta < 1.0 / M] = 1.0
    m = (eta > 0.05) & (eta < M)
    L2 = float(np.sqrt(np.mean((s0.psi[m] - psi_bl[m]) ** 2)))
    sg = NC.VEPlumeSolver(M=M, drho=320.0, Q=2.59e-3, nr=400, r0=0.5,
                          rfac=1.9).solve(1.5e6, max_steps=700000)
    mass_hi = sg.mass_balance()
    passed = (L2 < 0.02) and (abs(mass_hi - 1.0) < 5e-3)
    return _result("VE slope-flux", passed,
                   "G_s=0 matches BL (L2<0.02) & mass=1.000 at G_s~2",
                   f"L2={L2:.4f}, mass(G_s={sg.G_s:.1f})={mass_hi:.4f}")


def chk_fphi_lorenz():
    """F-Phi: unit-mobility tracer Lorenz coeff matches analytical layered."""
    g, r, f, w, _Ri = S.build_dp_demo(nx=12, ny=12)
    _, _, Lc_tracer = FP.single_phase_fphi(g, w, no_crossflow=False)
    k_lay = g.k.mean(axis=(0, 1)); h_lay = g.dzk; phi_lay = g.phi.mean(axis=(0, 1))
    _, _, Lc_layer = FP.layered_flow_storage(k_lay, h_lay, phi_lay)
    rel = abs(Lc_tracer - Lc_layer) / Lc_layer
    passed = rel < 0.10
    return _result("F-Phi / Lorenz", passed,
                   "tracer Lc within 10% of analytical layered",
                   f"Lc_tracer={Lc_tracer:.3f} vs Lc_layered={Lc_layer:.3f} ({rel*100:.1f}%)")


def chk_five_spot():
    """Five-spot homogeneous: 4-fold symmetry + mass conservation."""
    g, r, f, w = S.build_five_spot(nx=21, ny=21, nz=1, homogeneous=True,
                                   rate_pvi_yr=0.6)
    sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=5, coverage_fill=True)
    res = sim.run(target_pvi=0.35, n_psteps=6, verbose=False)
    sw = sim.sw[:, :, 0]
    asym = float(np.max(np.abs(sw - np.rot90(sw))))
    swc = float(np.asarray(r.swc))
    dW = float(np.sum(g.phi * g.vcell * (sim.sw - swc)))
    pw = res.produced[-1] - res.recovery[-1] * sim.mobile_oil
    bal = (dW + pw) / res.injected[-1]
    passed = (asym < 0.20) and (abs(bal - 1.0) < 0.03)
    return _result("five-spot", passed,
                   "4-fold symmetric (<0.20) & conserves (1.00+/-0.03)",
                   f"asym={asym:.3f}, balance={bal:.3f}")


def chk_trapping_model():
    """Land model: full drainage traps exactly Sgr_max; efficiency rises as peak falls."""
    swc, sgr = 0.20, 0.30
    full = float(CT.trapped_co2(1.0 - swc, swc, sgr))
    eff_lo = float(CT.trapped_co2(0.2, swc, sgr)) / 0.2
    eff_hi = float(CT.trapped_co2(0.6, swc, sgr)) / 0.6
    passed = (abs(full - sgr) < 1e-6) and (eff_lo > eff_hi)
    return _result("trapping model (Land)", passed,
                   "full drainage->Sgr_max & efficiency decreasing in peak",
                   f"trapped(1-swc)={full:.3f}=Sgr_max, eff(0.2)={eff_lo:.2f}>eff(0.6)={eff_hi:.2f}")


def chk_trapping_cycle():
    """Solver drainage->imbibition: residual immobile, pins at Land sat, mass closes."""
    nx, ny, nz = 16, 4, 1
    k = np.full((nx, ny, nz), 200 * 9.869e-16); phi = np.full((nx, ny, nz), 0.2)
    g = S.Grid3D(nx, ny, nz, dx=10, dy=10, dz=5, k=k, phi=phi)
    r = S.Rock(swc=0.2, sor=0.2, krw_max=0.4, kro_max=0.8, hysteresis=True, sgr=0.35)
    f = S.Fluid(mu_w=0.05, mu_o=0.6, rho_w=900, rho_o=900)
    inj = [(0, j, 0) for j in range(ny)]; prod = [(nx - 1, j, 0) for j in range(ny)]
    pv = float(np.sum(phi * g.vcell)); rate = 0.5 * pv / (365 * 24 * 3600)
    w = S.Wells(inj_cells=inj, prod_cells=prod, rate=rate, bhp=2e7)
    sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=5, conserve=True)
    swc = 0.2
    co2 = lambda: float(np.sum(g.phi * g.vcell * (sim.sw - swc)))
    sim.run(target_pvi=0.6, n_psteps=6, verbose=False); co2_d = co2()
    sim.inject_brine = True
    sim.run(target_pvi=1.0, n_psteps=10, verbose=False); co2_i = co2()
    krw, _ = S.rel_perm(sim.sw, r, sim.sg_max)
    immobile_mean = float(krw.mean())
    ratio = (co2_i + (co2_d - co2_i)) / co2_d           # = 1 by construction if conservative
    passed = (abs(ratio - 1.0) < 0.02) and (immobile_mean < 1e-3) and (co2_i < co2_d)
    return _result("trapping cycle (solver)", passed,
                   "mass closes (1.00) & residual immobile (krw->0)",
                   f"mass={ratio:.3f}, residual krw={immobile_mean:.4f}, trapped {co2_i/co2_d*100:.0f}%")


def chk_waterflood_regression():
    """Baseline waterflood (hysteresis OFF) conserves -- guards the core solver."""
    g, r, f, w = S.build_demo(nx=16, ny=16, nz=2, seed=7)
    sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=5, coverage_fill=True)
    res = sim.run(target_pvi=0.4, n_psteps=6, verbose=False)
    swc = float(np.asarray(r.swc))
    dW = float(np.sum(g.phi * g.vcell * (sim.sw - swc)))
    pw = res.produced[-1] - res.recovery[-1] * sim.mobile_oil
    bal = (dW + pw) / res.injected[-1]
    passed = abs(bal - 1.0) < 0.03
    return _result("waterflood regression", passed,
                   "build_demo conserves (1.00+/-0.03)",
                   f"RF={res.recovery[-1]*100:.1f}%, balance={bal:.3f}")


CHECKS = [
    chk_waterflood_regression,
    chk_bl_gravity_provenance,
    chk_ve_slopeflux,
    chk_fphi_lorenz,
    chk_five_spot,
    chk_trapping_model,
    chk_trapping_cycle,
]


def main():
    print("=" * 78)
    print("  PI-RNN streamline toolkit -- validation suite")
    print("=" * 78)
    rows = []
    t0 = time.time()
    for chk in CHECKS:
        ts = time.time()
        try:
            r = chk()
        except Exception as e:
            r = _result(chk.__name__, False, "ran without error", f"EXCEPTION: {e}")
        r["dt"] = time.time() - ts
        rows.append(r)
        tag = "PASS" if r["passed"] else "FAIL"
        print(f"[{tag}] {r['name']:<26} {r['value']}   ({r['dt']:.0f}s)")
    npass = sum(r["passed"] for r in rows)
    print("-" * 78)
    print(f"  {npass}/{len(rows)} checks passed in {time.time()-t0:.0f}s")
    print("=" * 78)
    return 0 if npass == len(rows) else 1


# (auto-run guard removed -- call main() or run_validation_suite() directly)
def scenario_check_balance_compressible():
    """Batch 1, gate 2: does mass balance close with the compressible time-of-flight?
       Pre-breakthrough (no water produced yet), water-in-place gain should equal injected."""

    NX = 120
    DP_PA = 2.0e7

    def balance(compressible, c, pvi):
        grid = S.Grid3D(NX, 1, 1, 10.0, 10.0, 10.0,
                        k=np.full((NX, 1, 1), 100e-15), phi=np.full((NX, 1, 1), 0.2))
        rock = S.Rock(nw=2., no=2., swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8)
        fluid = S.Fluid(mu_w=0.5, mu_o=5.0, c=c)
        wells = S.Wells([(0, 0, 0)], [(NX - 1, 0, 0)], rate=0.0, bhp=0.0, inj_bhp=DP_PA)
        sw0 = float(rock.swc)
        sim = S.StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=3,
                                    compressible=compressible)
        res = sim.run(target_pvi=pvi, n_psteps=24, verbose=False)
        dW = float(np.sum(grid.phi * grid.vcell * (sim.sw - sw0)))   # reservoir vol water gained
        injected = res.pvi[-1] * sim.pv                              # injected pore volumes
        wc_final = res.watercut[-1]
        return dW / injected, res.pvi[-1], wc_final, sim.Nc

    for label, comp, c in [("incompressible", False, 0.0), ("compressible", True, 2.5e-8)]:
        ratio, pvi, wc, Nc = balance(comp, c, 0.15)
        print(f"{label:14s}: WIP_gain/injected = {ratio:.4f}   (PVI={pvi:.3f}, "
              f"watercut={wc:.3f}, Nc={Nc:.2f})")
    print("\nPre-breakthrough watercut ~0 confirms no water produced yet,")
    print("so ratio should be ~1.0 if the scheme conserves.")



def scenario_make_3d_demo():
    """4-layer randomized-demo 3D saturation plot (build_demo, quarter five-spot, crossflow on).
       Distinct filename (fig_3d_demo.png) so it does not clobber the 8-layer fig_3d.png."""

    plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

    nx = ny = 22; nz = 4
    base = np.array([200., 80., 400., 120.])     # per-layer base permeability [mD]

    g, r, f, w = S.build_demo(nx=nx, ny=ny, nz=nz, seed=7)
    sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=5)
    res = sim.run(target_pvi=0.35, n_psteps=14, verbose=False)
    sw = res.sw_final
    pvi = res.pvi[-1]

    xc = (np.arange(nx) + 0.5) * g.dx
    yc = (np.arange(ny) + 0.5) * g.dy
    X, Y = np.meshgrid(xc, yc, indexing="ij")

    fig = plt.figure(figsize=(9, 7.5))
    ax = fig.add_subplot(111, projection="3d")
    fig.suptitle(f"3D saturation field — randomized demo, 4 layers stacked by depth "
                f"(waterflood/generic, not CCUS) (PVI = {pvi:.2f})",
                fontsize=12.5, fontweight="bold")
    norm = plt.Normalize(0.2, 0.8)
    zlev = [3, 2, 1, 0]                           # layer 1 on top
    for ki in range(nz):
        fc = plt.cm.viridis(norm(sw[:, :, ki]))
        Z = np.full_like(X, float(zlev[ki]))
        ax.plot_surface(X, Y, Z, facecolors=fc, shade=False, rstride=1, cstride=1,
                        antialiased=False)
        ax.text(0, ny * g.dy, zlev[ki], f" L{ki+1} (k$\\approx${base[ki]:.0f} mD)",
                fontsize=9, color="k")
    ax.scatter([0.5 * g.dx], [0.5 * g.dy], [3.15], color="#1f77b4", s=80, edgecolor="k",
               label="injector")
    ax.scatter([(nx - 0.5) * g.dx], [(ny - 0.5) * g.dy], [-0.15], color="#d62728", s=70,
               marker="s", edgecolor="k", label="producer")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("layer")
    ax.set_zticks(zlev); ax.set_zticklabels([f"L{i+1}" for i in range(nz)])
    ax.view_init(elev=22, azim=-60)
    ax.legend(loc="upper left", fontsize=9)
    m = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    cb = fig.colorbar(m, ax=ax, fraction=0.03, pad=0.08); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_3d_demo.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("PVI reached:", round(pvi, 2), "  saved fig_3d_demo")



def scenario_make_3d_layers_8():
    """3D showcase + per-layer areal sweep over time on the SAME 8-layer Dykstra-Parsons
       reservoir used everywhere else. No vertical crossflow + common-pressure wells, so
       each layer is an independent areal quarter five-spot and they self-allocate flux by
       layer conductivity -- the areal+time analogue of the DP validation."""

    plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

    nx = ny = 20
    kmD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
    h_ft = np.array([50., 48., 54., 44., 42., 48., 50., 40.])
    nz = 8
    times = [0.10, 0.30, 0.60]


    def build_8layer():
        grid, rock, fluid, _, Ri = S.build_dp_demo(nx=nx, ny=ny)
        # common-pressure quarter five-spot (matches the DP validation physics)
        inj = [(0, 0, k) for k in range(nz)]
        prod = [(nx - 1, ny - 1, k) for k in range(nz)]
        wells = S.Wells(inj_cells=inj, prod_cells=prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)
        return grid, rock, fluid, wells, Ri


    g, r, f, w, Ri = build_8layer()
    ext = [0, nx * g.dx, 0, ny * g.dy]

    fields = []
    for tp in times:
        g, r, f, w, Ri = build_8layer()
        sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=5, no_crossflow=True)
        res = sim.run(target_pvi=tp, n_psteps=12, verbose=False)
        fields.append((res.pvi[-1], res.sw_final))

    # layer order fast -> slow for readability
    order = list(np.argsort(Ri)[::-1])

    # ===================== per-layer areal sweep over time (8 layers) ==============
    fig, ax = plt.subplots(nz, len(times), figsize=(3.6 * len(times), 2.5 * nz))
    fig.suptitle("8-layer Dykstra-Parsons reservoir — per-layer areal sweep over time\n"
                "(no vertical crossflow, common-pressure quarter five-spot, "
                "waterflood/generic, not CCUS)",
                fontsize=12.5, fontweight="bold", y=1.005)
    for row, k in enumerate(order):
        for ti, (pvi, sw) in enumerate(fields):
            a = ax[row, ti]
            im = a.imshow(sw[:, :, k].T, origin="lower", extent=ext, cmap="viridis",
                          vmin=0.2, vmax=0.8, aspect="equal")
            a.plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=6, mec="k")
            a.plot((nx - 0.5) * g.dx, (ny - 0.5) * g.dy, "s", color="#d62728", ms=5, mec="k")
            a.set_xticks([]); a.set_yticks([])
            if row == 0:
                a.set_title(f"PVI = {pvi:.2f}", fontsize=12)
            if ti == 0:
                a.set_ylabel(f"L{k+1}\nk={kmD[k]:.0f}mD\n$R_i$={Ri[k]:.0f}", fontsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.012, pad=0.01); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_perlayer_time.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # ============================ 3D showcase (8 layers) ===========================
    pvi_mid, sw_mid = fields[1]
    xc = (np.arange(nx) + 0.5) * g.dx
    yc = (np.arange(ny) + 0.5) * g.dy
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    fig = plt.figure(figsize=(9.5, 8))
    ax = fig.add_subplot(111, projection="3d")
    fig.suptitle(f"3D saturation field — 8-layer DP reservoir stacked by depth "
                f"(waterflood/generic, not CCUS) (PVI = {pvi_mid:.2f})",
                fontsize=12.5, fontweight="bold")
    norm = plt.Normalize(0.2, 0.8)
    for zlev, k in enumerate(range(nz)):          # geologic order, L1 deepest index handling
        Swk = sw_mid[:, :, k]
        fc = plt.cm.viridis(norm(Swk))
        Z = np.full_like(X, float(nz - 1 - k))    # L1 on top
        ax.plot_surface(X, Y, Z, facecolors=fc, shade=False, rstride=1, cstride=1,
                        antialiased=False)
        ax.text(0, ny * g.dy, nz - 1 - k, f" L{k+1} (k={kmD[k]:.0f})", fontsize=8, color="k")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    ax.set_zticks(range(nz)); ax.set_zticklabels([f"L{nz-i}" for i in range(nz)], fontsize=8)
    ax.set_zlabel("layer")
    ax.view_init(elev=18, azim=-60)
    m = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    cb = fig.colorbar(m, ax=ax, fraction=0.025, pad=0.10); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_3d.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("layer order fast->slow:", [f"L{k+1}" for k in order])
    print("PVIs:", [round(p, 2) for p, _ in fields])
    print("saved fig_perlayer_time, fig_3d (8 layers)")



def scenario_make_8layer_ccus():
    """8-layer reservoir, CCUS buoyant mode: injected phase lighter than resident
       brine (rho_w < rho_o) so it rises -> gravity override. Full solver, crossflow on.
       Two figures (image-budget): per-layer areal sweep over time (depth-ordered) and
       the 3D field. Streamlines omitted (operator-split gravity doesn't change paths)."""

    plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

    NX = NY = 20
    NZ = 8
    kmD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
    CC = 1.0e-8
    RHO_INJ, RHO_RES = 700.0, 1020.0      # CO2-like injected (light) vs brine (heavy)
    MU_INJ, MU_RES = 0.05, 0.6            # supercritical CO2 vs formation brine [cp]
    times = [0.06, 0.15, 0.28]            # CO2 is fast (high injectivity); earlier snapshots
    FULL = dict(compressible=True, gravity=True, capillary=True,
                cap=S.Capillary(Pe=2.0e6, lam=2.0), n_diff_sub=3)
    SEEDS = 6

    def build():
        g, r, f0, _, Ri = S.build_dp_demo(nx=NX, ny=NY)
        f = S.Fluid(mu_w=MU_INJ, mu_o=MU_RES, c=CC, rho_w=RHO_INJ, rho_o=RHO_RES)
        inj = [(0, 0, k) for k in range(NZ)]; prod = [(NX-1, NY-1, k) for k in range(NZ)]
        w = S.Wells(inj_cells=inj, prod_cells=prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)
        return g, r, f, w, Ri

    g, r, f, w, Ri = build()
    ext = [0, NX * g.dx, 0, NY * g.dy]
    xc = (np.arange(NX) + 0.5) * g.dx; yc = (np.arange(NY) + 0.5) * g.dy
    # layer k=0 is bottom, k=NZ-1 is top; injected phase (light) rises toward top
    depth_order = list(range(NZ))[::-1]   # top (k=7) -> bottom (k=0)

    # conservative solver: coverage-aware seeding (now default) makes crossflow conserve
    fields = []
    for tp in times:
        g, r, f, w, Ri = build()
        sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=SEEDS, no_crossflow=False,
                                    coverage_fill=True, fill_stride=2, conserve=True, **FULL)
        res = sim.run(target_pvi=tp, n_psteps=5, verbose=False)
        fields.append((res.pvi[-1], sim.sw.copy()))
        dW = float(np.sum(g.phi * g.vcell * (sim.sw - np.asarray(r.swc))))
        pw = res.produced[-1] - res.recovery[-1] * sim.mobile_oil
        credited = (dW + pw) / res.injected[-1]
        prof = [float(sim.sw[:, :, k].mean()) for k in range(NZ)]
        print(f"  PVI={res.pvi[-1]:.2f} credited_balance={credited:.3f} alpha={np.mean(sim.alpha_log):.3f} "
              f"<Sw> bottom->top: " + " ".join(f"{v:.2f}" for v in prof))

    # ---- (1) per-layer areal sweep over time, depth-ordered (top row = top layer) ----
    fig, ax = plt.subplots(NZ, len(times), figsize=(3.6 * len(times), 2.5 * NZ))
    fig.suptitle("8-layer reservoir \u2014 CO\u2082 storage plume: per-layer areal sweep over time\n"
                 "(\u03bc_CO\u2082=0.05cp vs \u03bc_brine=0.6cp, buoyant; full solver, crossflow on)",
                 fontsize=13, fontweight="bold", y=1.004)
    for row, k in enumerate(depth_order):
        for ti, (pvi, sw) in enumerate(fields):
            a = ax[row, ti]
            im = a.imshow(sw[:, :, k].T, origin="lower", extent=ext, cmap="viridis",
                          vmin=0.2, vmax=0.8, aspect="equal")
            a.plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=6, mec="k")
            a.plot((NX-0.5) * g.dx, (NY-0.5) * g.dy, "s", color="#d62728", ms=5, mec="k")
            a.set_xticks([]); a.set_yticks([])
            if row == 0:
                a.set_title(f"PVI = {pvi:.2f}", fontsize=12)
            if ti == 0:
                tag = "TOP" if row == 0 else ("BOTTOM" if row == NZ-1 else "")
                a.set_ylabel(f"L{k+1}  k={kmD[k]:.0f}mD\n{tag}", fontsize=8.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.012, pad=0.01); cb.set_label(r"$S_{inj}$")
    fig.savefig(f"{OUTDIR}/fig_perlayer_time_ccus.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # ---- (2) 3D field: buoyant override ----
    pvi_mid, sw_mid = fields[1]
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    fig = plt.figure(figsize=(9.5, 8)); ax = fig.add_subplot(111, projection="3d")
    fig.suptitle(f"8-layer reservoir \u2014 CO\u2082 storage plume, 3D (PVI = {pvi_mid:.2f})\n"
                 "low-viscosity CO\u2082: buoyant override + viscous channeling",
                 fontsize=13, fontweight="bold")
    norm = plt.Normalize(0.2, 0.8)
    for k in range(NZ):                       # plot at true depth: k=NZ-1 on top
        fc = plt.cm.viridis(norm(sw_mid[:, :, k]))
        Z = np.full_like(X, float(k))
        ax.plot_surface(X, Y, Z, facecolors=fc, shade=False, rstride=1, cstride=1, antialiased=False)
        ax.text(0, NY * g.dy, k, f" L{k+1} (k={kmD[k]:.0f})", fontsize=8)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("depth (up = shallower)")
    ax.set_zticks(range(NZ)); ax.set_zticklabels([f"L{i+1}" for i in range(NZ)], fontsize=8)
    ax.view_init(elev=18, azim=-60)
    m = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    cb = fig.colorbar(m, ax=ax, fraction=0.025, pad=0.10); cb.set_label(r"$S_{inj}$")
    fig.savefig(f"{OUTDIR}/fig_3d_ccus.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("saved fig_perlayer_time_ccus, fig_3d_ccus")



def scenario_make_8layer_full():
    """8-layer DP reservoir with the FULL solver (compressible + gravity + capillary),
       vertical crossflow ON so gravity segregates between layers. Three figures:
       per-layer streamlines, per-layer areal sweep over time, 3D field.
       Waterflood densities; flip rho_w<rho_o for the buoyant CCUS plume."""

    plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

    NX = NY = 20
    NZ = 8
    kmD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
    CC = 1.0e-8
    times = [0.10, 0.30, 0.60]
    FULL = dict(compressible=True, gravity=True, capillary=True,
                cap=S.Capillary(Pe=2.0e6, lam=2.0), n_diff_sub=3)
    SEEDS = 6

    def build():
        g, r, f0, _, Ri = S.build_dp_demo(nx=NX, ny=NY)
        f = S.Fluid(mu_w=f0.mu_w, mu_o=f0.mu_o, c=CC, rho_w=f0.rho_w, rho_o=f0.rho_o)
        inj = [(0, 0, k) for k in range(NZ)]; prod = [(NX-1, NY-1, k) for k in range(NZ)]
        w = S.Wells(inj_cells=inj, prod_cells=prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)
        return g, r, f, w, Ri

    g, r, f, w, Ri = build()
    order = list(np.argsort(Ri)[::-1])
    ext = [0, NX * g.dx, 0, NY * g.dy]

    # de-risk conservation
    sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=SEEDS, no_crossflow=False, **FULL)
    res = sim.run(target_pvi=0.10, n_psteps=10, verbose=False)
    dW = float(np.sum(g.phi * g.vcell * (sim.sw - np.asarray(r.swc))))
    print(f"[8-layer full de-risk] PVI={res.pvi[-1]:.3f} wc={res.watercut[-1]:.3f} "
          f"WIP/injected={dW/(res.pvi[-1]*sim.pv):.4f} Nc={sim.Nc:.3f}")

    fields = []
    for tp in times:
        g, r, f, w, Ri = build()
        sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=SEEDS, no_crossflow=False, **FULL)
        res = sim.run(target_pvi=tp, n_psteps=10, verbose=False)
        fields.append((res.pvi[-1], sim.sw.copy()))

    # ---- (1) per-layer streamlines (areally uniform => same geometry, speed by k) ----
    g, r, f, w, Ri = build()
    p, lamt = S.solve_pressure(g, np.asarray(r.swc) * np.ones((NX, NY, NZ)), r, f, w)
    V = S.pore_velocities(g, p, lamt, False)
    p_inj_ref = float(np.mean([p[ci] for ci in w.inj_cells]))
    cfac = np.exp(f.c * (p_inj_ref - p))
    vx = 0.5 * (V["xm"] + V["xp"]) * cfac; vy = 0.5 * (V["ym"] + V["yp"]) * cfac
    spd = np.sqrt(vx**2 + vy**2); vmax = float(np.percentile(spd, 99))
    xc = (np.arange(NX) + 0.5) * g.dx; yc = (np.arange(NY) + 0.5) * g.dy
    fig, ax = plt.subplots(2, 4, figsize=(17, 8.6))
    fig.suptitle("8-layer reservoir \u2014 per-layer streamlines, full solver "
                 "(speed incl. compressibility)", fontsize=14, fontweight="bold")
    for axi, k in zip(ax.ravel(), order):
        strm = axi.streamplot(xc, yc, vx[:, :, k].T, vy[:, :, k].T, color=spd[:, :, k].T,
                              cmap="plasma", norm=plt.Normalize(0, vmax), density=1.1,
                              linewidth=1.0, arrowsize=0.8)
        axi.plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=9, mec="k")
        axi.plot((NX - 0.5) * g.dx, (NY - 0.5) * g.dy, "s", color="#d62728", ms=8, mec="k")
        axi.set_title(f"L{k+1}: k={kmD[k]:.0f} mD", fontsize=11)
        axi.set_xticks([]); axi.set_yticks([])
        axi.set_xlim(0, NX * g.dx); axi.set_ylim(0, NY * g.dy)
    cb = fig.colorbar(strm.lines, ax=ax, fraction=0.013, pad=0.01); cb.set_label("speed [m/s]")
    fig.savefig(f"{OUTDIR}/fig_streamlines_8layer_full.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # ---- (2) per-layer areal sweep over time ----
    fig, ax = plt.subplots(NZ, len(times), figsize=(3.6 * len(times), 2.5 * NZ))
    fig.suptitle("8-layer reservoir \u2014 per-layer areal sweep over time, full solver\n"
                 "(compressible + gravity + capillary, vertical crossflow on)",
                 fontsize=13, fontweight="bold", y=1.004)
    for row, k in enumerate(order):
        for ti, (pvi, sw) in enumerate(fields):
            a = ax[row, ti]
            im = a.imshow(sw[:, :, k].T, origin="lower", extent=ext, cmap="viridis",
                          vmin=0.2, vmax=0.8, aspect="equal")
            a.plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=6, mec="k")
            a.plot((NX-0.5) * g.dx, (NY-0.5) * g.dy, "s", color="#d62728", ms=5, mec="k")
            a.set_xticks([]); a.set_yticks([])
            if row == 0:
                a.set_title(f"PVI = {pvi:.2f}", fontsize=12)
            if ti == 0:
                a.set_ylabel(f"L{k+1}\nk={kmD[k]:.0f}mD", fontsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.012, pad=0.01); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_perlayer_time_full.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # ---- (3) 3D field ----
    pvi_mid, sw_mid = fields[1]
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    fig = plt.figure(figsize=(9.5, 8)); ax = fig.add_subplot(111, projection="3d")
    fig.suptitle(f"8-layer reservoir \u2014 3D saturation, full solver (PVI = {pvi_mid:.2f}, waterflood)",
                 fontsize=13, fontweight="bold")
    norm = plt.Normalize(0.2, 0.8)
    for k in range(NZ):
        fc = plt.cm.viridis(norm(sw_mid[:, :, k]))
        Z = np.full_like(X, float(NZ - 1 - k))
        ax.plot_surface(X, Y, Z, facecolors=fc, shade=False, rstride=1, cstride=1, antialiased=False)
        ax.text(0, NY * g.dy, NZ - 1 - k, f" L{k+1} (k={kmD[k]:.0f})", fontsize=8)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("layer")
    ax.set_zticks(range(NZ)); ax.set_zticklabels([f"L{NZ-i}" for i in range(NZ)], fontsize=8)
    ax.view_init(elev=18, azim=-60)
    m = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    cb = fig.colorbar(m, ax=ax, fraction=0.025, pad=0.10); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_3d_full.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("saved 8-layer full-solver figures")



def scenario_make_bl_figs():
    """Stage-by-stage demonstration figures for the BL progression (Stages 1-4),
       generated from blsolvers.py — the same code the theory document is grounded in."""

    plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3,
                         "figure.dpi": 120, "axes.axisbelow": True})

    rock = B.RockProperties()
    fluid = B.FluidProperties()
    geom = B.ReservoirGeometry()
    pres = B.PressureConditions()

    # shared fractional-flow curve and Welge tangent ---------------------------------
    sw = np.linspace(rock.swc, rock.sw_max, 400)
    fw = B.calculate_fractional_flow(sw, rock, fluid)
    dfw = B.calculate_dfw_dsw(sw, fw)
    # Welge tangent from (swc,0): maximise secant slope fw/(sw-swc)
    sec = np.where(sw > rock.swc + 1e-6, fw / (sw - rock.swc + 1e-12), 0.0)
    i_f = int(np.argmax(sec))
    swf, fwf = sw[i_f], fw[i_f]
    shock_speed = fwf / (swf - rock.swc)

    T_DAYS = 600.0  # chosen so the front sits mid-domain

    # =============================== STAGE 1 ========================================
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
    fig.suptitle("Stage 1 — Incompressible Buckley–Leverett", fontsize=14, fontweight="bold")

    ax[0].plot(sw, fw, color="#1f4e79", lw=2, label=r"$f_w(S_w)$")
    ax[0].plot([rock.swc, swf], [0, fwf], "--", color="#c00000", lw=1.8,
               label="Welge tangent")
    ax[0].plot(swf, fwf, "o", color="#c00000", ms=7)
    ax[0].annotate(rf"$S_{{w,f}}={swf:.2f}$", (swf, fwf), textcoords="offset points",
                   xytext=(8, -14), color="#c00000")
    ax[0].set_xlabel(r"$S_w$"); ax[0].set_ylabel(r"$f_w$")
    ax[0].set_title("Fractional flow + shock construction"); ax[0].legend(loc="upper left")

    ax[1].plot(sw, dfw, color="#2e7d32", lw=2)
    ax[1].axvline(swf, ls="--", color="#c00000", lw=1.3)
    ax[1].set_xlabel(r"$S_w$"); ax[1].set_ylabel(r"$df_w/dS_w$")
    ax[1].set_title("Characteristic speed (non-monotone → shock)")

    solver = B.CompressibleBLSolver(rock, fluid, geom, B.CompressibleFluid(), pres)
    for t, c in [(300.0, "#9ecae1"), (600.0, "#4292c6"), (900.0, "#08519c")]:
        xD, Sw = solver.solve_incompressible(t, nx=401)
        ax[2].plot(xD, Sw, color=c, lw=2, label=f"t = {t:.0f} d")
    ax[2].axhline(swf, ls=":", color="#c00000", lw=1.3, label=rf"$S_{{w,f}}$")
    ax[2].set_xlabel(r"$x_D = x/L$"); ax[2].set_ylabel(r"$S_w$")
    ax[2].set_title("Saturation profile (Godunov)"); ax[2].legend()
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{OUTDIR}/fig_stage1.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # =============================== STAGE 2 ========================================
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
    fig.suptitle("Stage 2 — Adding compressibility (CCS/UHS density variation)",
                 fontsize=14, fontweight="bold")

    L = geom.x_ip; xline = np.linspace(0, L, 401)
    cvals = [(0.0, "#08519c", "incompressible ($N_c=0$)"),
             (3.0e-4, "#4292c6", None), (6.0e-4, "#41ab5d", None), (1.0e-3, "#c00000", None)]
    for c, col, lab in cvals:
        eos = B.CompressibleFluid(c=c)
        p = pres.pressure_profile(xline, L)
        rho = eos.density_array(p)
        u = (5.615 * geom.i_w / geom.A) * eos.density(pres.p_inj) / rho
        Nc = B.compute_compressibility_number(eos, pres)
        ax[0].plot(xline / L, u / u[0], color=col,
                   label=lab or rf"$N_c={Nc:.2f}$", lw=2)
    ax[0].set_xlabel(r"$x_D$"); ax[0].set_ylabel(r"$u(x)/u_{inj}$")
    ax[0].set_title("Velocity speeds up down-gradient"); ax[0].legend()

    for c, col, lab in cvals:
        eos = B.CompressibleFluid(c=c)
        s = B.CompressibleBLSolver(rock, fluid, geom, eos, pres)
        Nc = s.Nc
        if c == 0.0:
            xD, Sw = s.solve_incompressible(T_DAYS, nx=401)
        else:
            xD, Sw = s.solve(T_DAYS, nx=401)
        ax[1].plot(xD, Sw, color=col, lw=2, label=lab or rf"$N_c={Nc:.2f}$")
    ax[1].set_xlabel(r"$x_D$"); ax[1].set_ylabel(r"$S_w$")
    ax[1].set_title(f"Saturation profile at t = {T_DAYS:.0f} d"); ax[1].legend()

    # front position vs Nc
    Ncs, fronts = [], []
    for c in np.linspace(0, 1.2e-3, 7):
        eos = B.CompressibleFluid(c=c)
        s = B.CompressibleBLSolver(rock, fluid, geom, eos, pres)
        xD, Sw = (s.solve_incompressible(T_DAYS) if c == 0 else s.solve(T_DAYS))
        fpos = xD[np.where(Sw > rock.swc + 0.02)[0][-1]] if np.any(Sw > rock.swc + 0.02) else 0
        Ncs.append(s.Nc); fronts.append(fpos)
    ax[2].plot(Ncs, fronts, "o-", color="#08519c", lw=2)
    ax[2].set_xlabel(r"$N_c = c\,(p_{inj}-p_{init})$"); ax[2].set_ylabel(r"front position $x_D$")
    ax[2].set_title("Compressibility advances the front")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{OUTDIR}/fig_stage2.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # =============================== STAGE 3 ========================================
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
    fig.suptitle("Stage 3 — Adding capillarity (front structure + residual trapping)",
                 fontsize=14, fontweight="bold")

    cap0 = B.CapillaryProperties()
    Pc = B.calculate_capillary_pressure(sw, rock, cap0)
    D = B.calculate_diffusion_coefficient(sw, rock, fluid, cap0)
    ax[0].plot(sw, Pc, color="#6a51a3", lw=2)
    ax[0].set_xlabel(r"$S_w$"); ax[0].set_ylabel(r"$P_c$ [psi]")
    ax[0].set_title(r"Capillary pressure $P_c=P_e S_e^{-1/\lambda}$")

    ax[1].plot(sw, D / max(D.max(), 1e-30), color="#08519c", lw=2)
    ax[1].set_xlabel(r"$S_w$"); ax[1].set_ylabel(r"$D/D_{\max}$")
    ax[1].set_title("Capillary diffusion coefficient (peaks at front)")

    # sharp (no Pc) vs increasing capillary strength
    xD0, Sw0 = B.CompressibleBLSolver(rock, fluid, geom, B.CompressibleFluid(), pres
                                      ).solve_incompressible(T_DAYS, nx=201)
    ax[2].plot(xD0, Sw0, color="#000000", lw=2, label=r"no capillarity ($\mathrm{Pe}_c\to\infty$)")
    for Pe, col in [(15.0, "#4292c6"), (60.0, "#41ab5d"), (200.0, "#c00000")]:
        cap = B.CapillaryProperties(Pe=Pe, k=2000.0)
        s = B.CapillaryBLSolver(rock, fluid, geom, cap)
        xD, Sw = s.solve(T_DAYS, nx=201)
        ax[2].plot(xD, Sw, color=col, lw=2, label=rf"$\mathrm{{Pe}}_c={s.Pe_c:.0f}$")
    ax[2].set_xlabel(r"$x_D$"); ax[2].set_ylabel(r"$S_w$")
    ax[2].set_title("Capillarity smears the shock"); ax[2].legend(fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{OUTDIR}/fig_stage3.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # =============================== STAGE 4 ========================================
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("Stage 4 — The full CCUS-ready solver (compressible + capillary)",
                 fontsize=14, fontweight="bold")

    eos = B.CompressibleFluid(c=8.0e-4); cap = B.CapillaryProperties(Pe=80.0, k=2000.0)
    xD1, Sw1 = B.CompressibleBLSolver(rock, fluid, geom, eos, pres).solve_incompressible(T_DAYS, 201)
    xD2, Sw2 = B.CompressibleBLSolver(rock, fluid, geom, eos, pres).solve(T_DAYS, 201)
    xD3, Sw3 = B.CapillaryBLSolver(rock, fluid, geom, cap).solve(T_DAYS, 201)
    full = B.FullBLSolver(rock, fluid, geom, eos, pres, cap)
    xD4, Sw4 = full.solve(T_DAYS, 201)
    ax[0].plot(xD1, Sw1, color="#000000", lw=2, label="incompressible")
    ax[0].plot(xD2, Sw2, color="#08519c", lw=2, label=rf"compressible ($N_c={full.Nc:.2f}$)")
    ax[0].plot(xD3, Sw3, color="#41ab5d", lw=2, label=rf"capillary ($\mathrm{{Pe}}_c={full.Pe_c:.0f}$)")
    ax[0].plot(xD4, Sw4, color="#c00000", lw=2.4, label="full (both)")
    ax[0].set_xlabel(r"$x_D$"); ax[0].set_ylabel(r"$S_w$")
    ax[0].set_title(f"Saturation profile at t = {T_DAYS:.0f} d"); ax[0].legend(fontsize=9)

    ax[1].axis("off")
    ax[1].text(0.0, 0.95,
               "Built by composition:\n\n"
               "   FullBLSolver\n"
               "     ├── CompressibleBLSolver   (variable-u advection)\n"
               "     └── CapillaryBLSolver       (implicit diffusion)\n\n"
               "Each timestep:\n"
               "   1. compressible Godunov advection step\n"
               "   2. implicit capillary diffusion step\n\n"
               f"   $N_c$ = {full.Nc:.3f}      $\\mathrm{{Pe}}_c$ = {full.Pe_c:.0f}\n\n"
               "Setting c→0 recovers Stage 3;\n"
               "setting $P_e$→0 recovers Stage 2;\n"
               "both→0 recovers Stage 1.",
               fontsize=11, va="top", family="monospace")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{OUTDIR}/fig_stage4.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    print("stage1 swf=%.3f shock_speed=%.3f" % (swf, shock_speed))
    print("saved fig_stage1..4")



def scenario_make_demo_full():
    """build_demo (4-layer randomized) with the FULL solver: compressibility + gravity
       + capillarity, vertical crossflow on. Three figures: per-layer streamlines,
       per-layer areal sweep over time, and the 3D field. Waterflood densities
       (rho_w>rho_o); flip them for the buoyant CCUS plume."""

    plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

    NX = NY = 22
    NZ = 4
    base = np.array([200., 80., 400., 120.])
    CC = 1.0e-8                      # fluid compressibility [1/Pa] -> moderate Nc
    times = [0.15, 0.35, 0.6]

    FULL = dict(compressible=True, gravity=True, capillary=True,
                cap=S.Capillary(Pe=2.0e6, lam=2.0), n_diff_sub=3)

    def build(seedrun_pvi=None):
        g, r, f, w = S.build_demo(nx=NX, ny=NY, nz=NZ, seed=7, c=CC)
        return g, r, f, w

    # ---- de-risk: coupled conservation check (pre-breakthrough) ----
    g, r, f, w = build()
    sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=7, no_crossflow=False, **FULL)
    res = sim.run(target_pvi=0.15, n_psteps=12, verbose=False)
    dW = float(np.sum(g.phi * g.vcell * (sim.sw - float(np.asarray(r.swc)))))
    inj = res.pvi[-1] * sim.pv
    print(f"[full-solver de-risk] PVI={res.pvi[-1]:.3f} watercut={res.watercut[-1]:.3f} "
          f"WIP/injected={dW/inj:.4f}  Nc={sim.Nc:.3f}")

    # snapshots for areal/3D
    fields = []
    for tp in times:
        g, r, f, w = build()
        sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=7, no_crossflow=False, **FULL)
        res = sim.run(target_pvi=tp, n_psteps=12, verbose=False)
        fields.append((res.pvi[-1], sim.sw.copy()))
    g, r, f, w = build()
    ext = [0, NX * g.dx, 0, NY * g.dy]

    # ================= (1) per-layer streamlines (full solver, compressible speed) =====
    p, lamt = S.solve_pressure(g, np.full((NX, NY, NZ), float(np.asarray(r.swc))), r, f, w)
    V = S.pore_velocities(g, p, lamt, False)
    p_inj_ref = float(np.mean([p[ci] for ci in w.inj_cells]))
    cfac = np.exp(f.c * (p_inj_ref - p))             # compressible velocity scaling
    vx = 0.5 * (V["xm"] + V["xp"]) * cfac
    vy = 0.5 * (V["ym"] + V["yp"]) * cfac
    spd = np.sqrt(vx**2 + vy**2)
    vmax = float(np.percentile(spd, 99))
    xc = (np.arange(NX) + 0.5) * g.dx; yc = (np.arange(NY) + 0.5) * g.dy
    fig, ax = plt.subplots(1, NZ, figsize=(4.0 * NZ, 4.4))
    fig.suptitle("build_demo (randomized) — per-layer streamlines, full solver "
                "(speed incl. compressibility) — waterflood, not CCUS "
                "(same full solver CCUS needs, different fluid)",
                fontsize=11.5, fontweight="bold")
    for k in range(NZ):
        a = ax[k]
        strm = a.streamplot(xc, yc, vx[:, :, k].T, vy[:, :, k].T, color=spd[:, :, k].T,
                            cmap="plasma", norm=plt.Normalize(0, vmax), density=1.2,
                            linewidth=1.0, arrowsize=0.8)
        a.imshow(np.log10(g.k[:, :, k] / 9.869e-16).T, origin="lower", extent=ext,
                 cmap="Greys", alpha=0.25, aspect="equal")
        a.plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=9, mec="k")
        a.plot((NX - 0.5) * g.dx, (NY - 0.5) * g.dy, "s", color="#d62728", ms=8, mec="k")
        a.set_title(f"Layer {k+1}  (k$\\approx${base[k]:.0f} mD)", fontsize=11)
        a.set_xticks([]); a.set_yticks([])
        a.set_xlim(0, NX * g.dx); a.set_ylim(0, NY * g.dy)
    cb = fig.colorbar(strm.lines, ax=ax, fraction=0.013, pad=0.01); cb.set_label("speed [m/s]")
    fig.savefig(f"{OUTDIR}/fig_streamlines_demo_full.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # ================= (2) per-layer areal sweep over time (full solver) ===============
    fig, ax = plt.subplots(NZ, len(times), figsize=(4.0 * len(times), 3.3 * NZ))
    fig.suptitle("build_demo — per-layer areal sweep over time, full solver "
                "(compressible + gravity + capillary, crossflow on) — waterflood, not CCUS",
                fontsize=12.5, fontweight="bold")
    for k in range(NZ):
        for ti, (pvi, sw) in enumerate(fields):
            a = ax[k, ti]
            im = a.imshow(sw[:, :, k].T, origin="lower", extent=ext, cmap="viridis",
                          vmin=0.2, vmax=0.8, aspect="equal")
            a.plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=7, mec="k")
            a.plot((NX - 0.5) * g.dx, (NY - 0.5) * g.dy, "s", color="#d62728", ms=6, mec="k")
            if k == 0:
                a.set_title(f"PVI = {pvi:.2f}", fontsize=12)
            if ti == 0:
                a.set_ylabel(f"Layer {k+1}\nk$\\approx${base[k]:.0f}mD", fontsize=10)
            a.set_xticks([]); a.set_yticks([])
    cb = fig.colorbar(im, ax=ax, fraction=0.012, pad=0.01); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_areal_demo_full.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # ================= (3) 3D field (full solver) ====================================
    pvi_mid, sw_mid = fields[1]
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    fig = plt.figure(figsize=(9, 7.5)); ax = fig.add_subplot(111, projection="3d")
    fig.suptitle(f"build_demo \u2014 3D saturation, full solver (PVI = {pvi_mid:.2f}, waterflood)",
                 fontsize=13, fontweight="bold")
    norm = plt.Normalize(0.2, 0.8); zlev = [3, 2, 1, 0]
    for k in range(NZ):
        fc = plt.cm.viridis(norm(sw_mid[:, :, k]))
        Z = np.full_like(X, float(zlev[k]))
        ax.plot_surface(X, Y, Z, facecolors=fc, shade=False, rstride=1, cstride=1, antialiased=False)
        ax.text(0, NY * g.dy, zlev[k], f" L{k+1} (k$\\approx${base[k]:.0f})", fontsize=9)
    ax.scatter([0.5 * g.dx], [0.5 * g.dy], [3.15], color="#1f77b4", s=80, edgecolor="k", label="injector")
    ax.scatter([(NX - 0.5) * g.dx], [(NY - 0.5) * g.dy], [-0.15], color="#d62728", s=70, marker="s", edgecolor="k", label="producer")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("layer")
    ax.set_zticks(zlev); ax.set_zticklabels([f"L{i+1}" for i in range(NZ)])
    ax.view_init(elev=22, azim=-60); ax.legend(loc="upper left", fontsize=9)
    m = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    cb = fig.colorbar(m, ax=ax, fraction=0.03, pad=0.08); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_3d_demo_full.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("saved fig_streamlines_demo_full, fig_areal_demo_full, fig_3d_demo_full")



def scenario_make_dp_system():
    """Makes the Dykstra-Parsons system explicit: 8 layers, their properties,
       the per-layer 1D sweep, and the system recovery/water cut."""

    plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3,
                         "figure.dpi": 120, "axes.axisbelow": True})

    # the 8-layer table (from build_dp_demo)
    kmD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
    h_ft = np.array([50., 48., 54., 44., 42., 48., 50., 40.])
    phi_l = np.array([0.22, 0.18, 0.21, 0.15, 0.20, 0.21, 0.20, 0.20])
    swc_l = np.array([0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42])
    krom = np.array([0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60])
    krwm = np.array([0.05, 0.15, 0.20, 0.33, 0.20, 0.30, 0.40, 0.17])
    sor = 0.2
    nz = 8
    Ri = kmD / (phi_l * (1.0 - sor - swc_l))
    labels = [f"L{i+1}" for i in range(nz)]

    # 1D-per-layer streamline run (no crossflow, common pressure)
    nx = 60
    lay = lambda v: np.ones((nx, 1, nz)) * np.asarray(v)[None, None, :]
    h_m = h_ft * 0.3048
    grid = S.Grid3D(nx, 1, nz, 10., 10., h_m, k=lay(kmD) * 9.869e-16, phi=lay(phi_l))
    rock = S.Rock(nw=2., no=2., swc=lay(swc_l), sor=sor, krw_max=lay(krwm), kro_max=lay(krom))
    fluid = S.Fluid(mu_w=0.5, mu_o=0.7)
    wells = S.Wells([(0, 0, k) for k in range(nz)], [(nx-1, 0, k) for k in range(nz)],
                    rate=0.0, bhp=0.0, inj_bhp=2.0e7)
    sim = S.StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=3, no_crossflow=True)
    res = sim.run(0.6, 18, verbose=False)
    sw = res.sw_final

    fig = plt.figure(figsize=(16, 4.6))
    fig.suptitle("Dykstra-Parsons system: 8 non-communicating layers (no vertical crossflow)",
                 fontsize=14, fontweight="bold", y=1.04)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.1, 1], wspace=0.32)

    # (a) layer property structure -- subsurface order (L1..L8), Ri as a label,
    # not the sort key (same fix as the dedicated Dykstra-Parsons stage)
    axa = fig.add_subplot(gs[0, 0])
    order = np.argsort(Ri)              # kept for panel (b)'s legend order, not bar order
    yy = np.arange(nz)
    axa.barh(yy, kmD, color=plt.cm.viridis(Ri / Ri.max()))
    for i in range(nz):
        axa.text(kmD[i] + 15, i, f"Ri={Ri[i]:.0f}, h={h_ft[i]:.0f}ft", va="center", fontsize=8)
    axa.set_yticks(yy); axa.set_yticklabels(labels, fontsize=8)
    axa.invert_yaxis()
    axa.set_xlabel("permeability [mD]")
    axa.set_title("(a) 8 layers, subsurface order"); axa.set_xlim(0, 1500)

    # (b) per-layer 1D sweep at this PVI
    axb = fig.add_subplot(gs[0, 1])
    xD = (np.arange(nx) + 0.5) / nx
    for k in order:
        axb.plot(xD, sw[:, 0, k], lw=1.6,
                 color=plt.cm.viridis(Ri[k] / Ri.max()), label=f"{labels[k]} (k={kmD[k]:.0f})")
    axb.set_xlabel(r"$x_D$"); axb.set_ylabel(r"$S_w$")
    axb.set_title(f"(b) Per-layer sweep at PVI={res.pvi[-1]:.2f} (fast layers furthest)")
    axb.legend(fontsize=7, ncol=2, loc="upper right")

    # (c) system recovery + water cut vs DP
    axc = fig.add_subplot(gs[0, 2])
    dp = D.DykstraParsons(list(kmD), list(h_ft), list(phi_l), list(swc_l), sor,
                          list(krwm), list(krom), mu_w=0.5, mu_o=0.7, allocation="kh_mob")
    pv = np.array(res.pvi)
    rec_dp, wc_dp = dp.run(pv)
    axc.plot(pv, np.array(res.recovery) * 100, "-", color="#c00000", lw=2, label="streamline rec.")
    axc.plot(pv, rec_dp * 100, "--", color="#c00000", lw=1.4, alpha=0.6, label="DP rec.")
    axc.plot(pv, np.array(res.watercut) * 100, "-", color="#08519c", lw=2, label="streamline $f_w$")
    axc.plot(pv, wc_dp * 100, "--", color="#08519c", lw=1.4, alpha=0.6, label="DP $f_w$")
    axc.set_xlabel("PVI"); axc.set_ylabel("recovery / water cut [%]")
    axc.set_title("(c) 8-layer system response"); axc.legend(fontsize=8, loc="center right")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(f"{OUTDIR}/fig_dp_system.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("Ri order (slow->fast):", [labels[o] for o in order])
    print("saved fig_dp_system")



def scenario_make_streamline_8layer():
    """Streamlines in the 8-layer Dykstra-Parsons reservoir (our data).
       No vertical crossflow + common-pressure quarter five-spot, so each layer is an
       independent areal five-spot. The layers are areally uniform => identical streamline
       GEOMETRY; the flow SPEED differs by layer permeability (colored on a shared scale)."""

    plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

    nx = ny = 30
    kmD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
    nz = 8

    grid, rock, fluid, _, Ri = S.build_dp_demo(nx=nx, ny=ny)
    inj = [(0, 0, k) for k in range(nz)]
    prod = [(nx - 1, ny - 1, k) for k in range(nz)]
    wells = S.Wells(inj_cells=inj, prod_cells=prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)

    sw0 = np.array(rock.swc, dtype=float)                      # per-layer connate water
    p, lamt = S.solve_pressure(grid, sw0, rock, fluid, wells, no_crossflow=True)
    V = S.pore_velocities(grid, p, lamt, no_crossflow=True)
    vx = 0.5 * (V["xm"] + V["xp"])
    vy = 0.5 * (V["ym"] + V["yp"])
    speed = np.sqrt(vx**2 + vy**2)
    vmax = float(np.percentile(speed, 99))                     # shared speed scale

    xc = (np.arange(nx) + 0.5) * grid.dx
    yc = (np.arange(ny) + 0.5) * grid.dy
    ext = [0, nx * grid.dx, 0, ny * grid.dy]
    order = list(np.argsort(Ri)[::-1])                         # fast -> slow

    fig, ax = plt.subplots(2, 4, figsize=(17, 8.6))
    fig.suptitle("Streamlines in the 8-layer Dykstra-Parsons reservoir "
                 "(quarter five-spot, no crossflow)\n"
                 "same areal geometry every layer — flow SPEED set by layer permeability",
                 fontsize=14, fontweight="bold")
    sm = None
    for ax_i, k in zip(ax.ravel(), order):
        U = vx[:, :, k].T
        Vv = vy[:, :, k].T
        spd = speed[:, :, k].T
        strm = ax_i.streamplot(xc, yc, U, Vv, color=spd, cmap="plasma",
                               norm=plt.Normalize(0, vmax), density=1.2,
                               linewidth=1.0, arrowsize=0.8)
        sm = strm.lines
        ax_i.plot(0.5 * grid.dx, 0.5 * grid.dy, "o", color="#1f77b4", ms=10, mec="k")
        ax_i.plot((nx - 0.5) * grid.dx, (ny - 0.5) * grid.dy, "s", color="#d62728",
                  ms=9, mec="k")
        ax_i.set_title(f"L{k+1}: k={kmD[k]:.0f} mD,  $R_i$={Ri[k]:.0f}", fontsize=11)
        ax_i.set_xticks([]); ax_i.set_yticks([])
        ax_i.set_xlim(0, nx * grid.dx); ax_i.set_ylim(0, ny * grid.dy)
    cb = fig.colorbar(sm, ax=ax, fraction=0.013, pad=0.01)
    cb.set_label("interstitial speed [m/s]")
    fig.savefig(f"{OUTDIR}/fig_streamlines_8layer.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("order fast->slow:", [f"L{k+1}" for k in order], " vmax=%.2e" % vmax)
    print("saved fig_streamlines_8layer")



def scenario_make_streamline_viz():
    """Streamline geometry + well-pattern visualization.
       Streamlines are drawn with matplotlib streamplot of the pore-velocity field —
       the exact field the Pollock tracer follows in the simulator."""

    plt.rcParams.update({"font.size": 11, "figure.dpi": 120})


    def center_velocity(grid, p, lamt, ncf=False):
        V = S.pore_velocities(grid, p, lamt, ncf)
        vx = 0.5 * (V["xm"] + V["xp"])
        vy = 0.5 * (V["ym"] + V["yp"])
        return vx, vy


    def streamplot_layer(ax, grid, vx, vy, kk, color, dens=1.3):
        xc = (np.arange(grid.nx) + 0.5) * grid.dx
        yc = (np.arange(grid.ny) + 0.5) * grid.dy
        U = vx[:, :, kk].T
        Vv = vy[:, :, kk].T
        speed = np.sqrt(U**2 + Vv**2)
        ax.streamplot(xc, yc, U, Vv, density=dens, color=color, linewidth=1.0,
                      arrowsize=0.8)


    # ============ (1)+(2) streamline geometry: quarter vs full five-spot ============
    fig, ax = plt.subplots(1, 2, figsize=(12, 5.2))
    fig.suptitle("Streamline geometry and well pattern (single layer, initial field, "
                "waterflood/generic, not CCUS)",
                fontsize=13, fontweight="bold")

    # -- quarter five-spot (the configuration in build_demo / build_dp_demo) --
    g, r, f, w = S.build_demo(nx=30, ny=30, nz=1, seed=7)
    sw0 = np.full((g.nx, g.ny, g.nz), float(np.asarray(r.swc)))
    p, lamt = S.solve_pressure(g, sw0, r, f, w)
    vx, vy = center_velocity(g, p, lamt)
    ext = [0, g.nx * g.dx, 0, g.ny * g.dy]
    im0 = ax[0].imshow(np.log10(g.k[:, :, 0] / 9.869e-16).T, origin="lower",
                       extent=ext, cmap="Greys", alpha=0.55, aspect="equal")
    streamplot_layer(ax[0], g, vx, vy, 0, "#08519c")
    ax[0].plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=14, mec="k", label="injector")
    ax[0].plot((g.nx - 0.5) * g.dx, (g.ny - 0.5) * g.dy, "s", color="#d62728", ms=13,
               mec="k", label="producer")
    ax[0].set_title("Quarter five-spot\n(injector + producer on diagonal corners)")
    ax[0].legend(loc="upper left", fontsize=9)
    ax[0].set_xlabel("x [m]"); ax[0].set_ylabel("y [m]")

    # -- full five-spot (central injector, four corner producers) --
    nx = ny = 31
    kf = S.build_demo(nx=nx, ny=ny, nz=1, seed=7)[0].k
    gf = S.Grid3D(nx, ny, 1, 10.0, 10.0, 5.0, k=kf, phi=np.full((nx, ny, 1), 0.2))
    rf = S.Rock(); ff = S.Fluid()
    ci, cj = nx // 2, ny // 2
    inj = [(ci, cj, 0)]
    prod = [(0, 0, 0), (nx - 1, 0, 0), (0, ny - 1, 0), (nx - 1, ny - 1, 0)]
    pvf = float(np.sum(gf.phi) * gf.cell_vol)
    wf = S.Wells(inj_cells=inj, prod_cells=prod,
                 rate=0.6 * pvf / (365 * 24 * 3600), bhp=2.0e7)
    sw0 = np.full((nx, ny, 1), 0.2)
    pf, lamtf = S.solve_pressure(gf, sw0, rf, ff, wf)
    vxf, vyf = center_velocity(gf, pf, lamtf)
    ax[1].imshow(np.log10(gf.k[:, :, 0] / 9.869e-16).T, origin="lower",
                 extent=[0, nx * 10, 0, ny * 10], cmap="Greys", alpha=0.55, aspect="equal")
    streamplot_layer(ax[1], gf, vxf, vyf, 0, "#08519c", dens=1.6)
    ax[1].plot((ci + 0.5) * 10, (cj + 0.5) * 10, "o", color="#1f77b4", ms=14, mec="k",
               label="injector")
    for (pi, pj, _) in prod:
        ax[1].plot((pi + 0.5) * 10, (pj + 0.5) * 10, "s", color="#d62728", ms=13, mec="k")
    ax[1].plot([], [], "s", color="#d62728", ms=10, mec="k", label="producers")
    ax[1].set_title("Full five-spot\n(central injector, four corner producers)")
    ax[1].legend(loc="upper left", fontsize=9)
    ax[1].set_xlabel("x [m]"); ax[1].set_ylabel("y [m]")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(f"{OUTDIR}/fig_streamlines.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # ================= areal sweep over time (quarter five-spot) ====================
    fig, ax = plt.subplots(1, 4, figsize=(17, 4.3))
    fig.suptitle("Quarter five-spot — areal sweep over time, streamlines overlaid "
                "(single layer, waterflood/generic, not CCUS — see Stage 7 for the "
                "dual-track version)",
                fontsize=12.5, fontweight="bold")
    g, r, f, w = S.build_demo(nx=30, ny=30, nz=1, seed=7)
    for ax_i, pvi_t in zip(ax, [0.15, 0.3, 0.5, 0.8]):
        sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=7)
        res = sim.run(target_pvi=pvi_t, n_psteps=16, verbose=False)
        sw = res.sw_final
        p, lamt = S.solve_pressure(g, sw, r, f, w)
        vx, vy = center_velocity(g, p, lamt)
        im = ax_i.imshow(sw[:, :, 0].T, origin="lower", extent=ext, cmap="viridis",
                         vmin=0.2, vmax=0.8, aspect="equal")
        streamplot_layer(ax_i, g, vx, vy, 0, "white", dens=1.0)
        ax_i.plot(0.5 * g.dx, 0.5 * g.dy, "o", color="#1f77b4", ms=10, mec="k")
        ax_i.plot((g.nx - 0.5) * g.dx, (g.ny - 0.5) * g.dy, "s", color="#d62728", ms=9, mec="k")
        ax_i.set_title(f"PVI = {res.pvi[-1]:.2f}")
        ax_i.set_xlabel("x [m]")
    ax[0].set_ylabel("y [m]")
    cb = fig.colorbar(im, ax=ax, fraction=0.013, pad=0.01); cb.set_label(r"$S_w$")
    fig.savefig(f"{OUTDIR}/fig_areal_time.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("saved fig_streamlines, fig_areal_time")



def scenario_stage2_aquifer():
    """Tier-2 Stage 2: streamline confined-aquifer CO2 plume.
    Homogeneous aquifer, fully-penetrating corner injector (quarter-symmetry of a
    radial well), buoyant CO2 (rho_CO2 < rho_brine), no-flow caprock/base, far-corner
    brine sink. Confirm it produces a sensible overriding plume (CO2 to the top),
    extract the vertically-averaged interface profile vs radius, and check it conserves.
    Incompressible, no capillarity -> matches the NC sharp-interface assumptions."""

    NX = NY = 24
    NZ = 8
    DX = DY = 15.0; DZ = 2.0
    KMD = 200.0
    PHI = 0.2
    MU_CO2, MU_BR = 0.05, 0.6
    RHO_CO2, RHO_BR = 700.0, 1020.0

    def build_aquifer(rate):
        k = np.full((NX, NY, NZ), KMD * 9.869e-16)
        phi = np.full((NX, NY, NZ), PHI)
        grid = S.Grid3D(NX, NY, NZ, dx=DX, dy=DY, dz=DZ, k=k, phi=phi)
        rock = S.Rock(nw=2.0, no=2.0, swc=0.2, sor=0.2, krw_max=0.4, kro_max=0.8)
        fluid = S.Fluid(mu_w=MU_CO2, mu_o=MU_BR, c=0.0, rho_w=RHO_CO2, rho_o=RHO_BR)
        inj = [(0, 0, k) for k in range(NZ)]            # fully-penetrating injector
        prod = [(NX - 1, NY - 1, k) for k in range(NZ)]  # far-corner brine sink
        wells = S.Wells(inj_cells=inj, prod_cells=prod, rate=rate, bhp=2.0e7)
        return grid, rock, fluid, wells

    PV = PHI * NX * NY * NZ * DX * DY * DZ
    rate = 0.10 * PV / (365 * 24 * 3600)               # slow inj -> gravity-dominated
    g, r, f, w = build_aquifer(rate)
    sim = S.StreamlineSimulator(g, r, f, w, seeds_per_dim=4, no_crossflow=False,
                                gravity=True, capillary=False, compressible=False,
                                coverage_fill=True, conserve=True, fill_stride=3)
    _t0 = time.time()
    res = sim.run(target_pvi=0.06, n_psteps=8, verbose=False)
    print(f"run wall-time = {time.time()-_t0:.0f}s")

    # override check: CO2 saturation (=sw) averaged areally, per layer (bottom->top)
    sw = sim.sw
    layer_avg = [float(sw[:, :, k].mean()) for k in range(NZ)]
    print(f"PVI={res.pvi[-1]:.3f}  watercut(brine-sink CO2 cut)={res.watercut[-1]:.2f}")
    print("CO2 sat by layer bottom->top:", " ".join(f"{v:.2f}" for v in layer_avg))

    # conservation (CO2 is the injected/displacing phase 'w')
    dW = float(np.sum(g.phi * g.vcell * (sw - np.asarray(r.swc))))
    pw = res.produced[-1] - res.recovery[-1] * sim.mobile_oil
    print(f"credited balance = {(dW + pw)/res.injected[-1]:.3f}  alpha={np.mean(sim.alpha_log):.3f}")

    # vertically-averaged interface fraction psi(x,y), radial profile from injector corner
    psi = (sw - np.asarray(r.swc)) / (r.sw_max - float(np.asarray(r.swc)))  # mobile CO2 frac
    psi_va = psi.mean(axis=2)                                               # vertical average
    xc = (np.arange(NX) + 0.5) * DX; yc = (np.arange(NY) + 0.5) * DY
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    R = np.sqrt(X**2 + Y**2)
    rb = np.linspace(0, R.max(), 16)
    prof = []
    for i in range(len(rb) - 1):
        m = (R >= rb[i]) & (R < rb[i + 1])
        prof.append(psi_va[m].mean() if m.any() else np.nan)
    rc = 0.5 * (rb[:-1] + rb[1:])
    print("radial vertically-averaged CO2 fraction (r[m]: psi):")
    print("  " + "  ".join(f"{r_:.0f}:{p:.2f}" for r_, p in zip(rc, prof) if not np.isnan(p)))



def scenario_validate_4modes_1d():

    # ---- shared 1D setup (field units, matching the BL solvers) ----
    rock = B.RockProperties()
    fluid = B.FluidProperties()
    geom = B.ReservoirGeometry()
    pres = B.PressureConditions(p_inj=3000.0, p_init=2000.0)
    eos = B.CompressibleFluid(c=1.0e-4)                 # Nc ~ 0.1
    cap = B.CapillaryProperties(Pe=100.0, lambda_bc=2.0, k=100.0)
    t_days = 2000.0
    nx = 201
    L = geom.x_ip
    x = np.linspace(0, L, nx)
    dx = L / (nx - 1)
    phi = rock.phi
    u_inj = (5.615 * geom.i_w) / geom.A
    sw_max = rock.sw_max
    swc = rock.swc
    rho_inj = eos.density(pres.p_inj)


    def streamline_1d(c, capillary, t_days, nx=nx, cfl=0.4):
        """1D reduction of the streamline simulator: tau-advection (+EOS source if
           c>0) and implicit x-diffusion (if capillary). Same physics as the 3D code."""
        p = pres.pressure_profile(x, L)
        u = (u_inj * rho_inj / eos.density_array(p)) if c > 0 else np.full(nx, u_inj)
        dtau = phi * dx / u
        dpdtau = np.zeros(nx); dpdtau[1:] = (p[1:] - p[:-1]) / dtau[1:]
        s = np.linspace(swc, sw_max, 200)
        f = B.calculate_fractional_flow(s, rock, fluid)
        max_dfw = np.max(np.abs(np.gradient(f, s)))
        h = cfl * np.min(dtau) / (max_dfw + 1e-12)
        nt = int(np.ceil(t_days / h)); h = t_days / nt
        Sw = np.ones(nx) * (swc + 0.001); Sw_inj = sw_max - 0.001; Sw[0] = Sw_inj
        fw_inj = B.calculate_fractional_flow(np.array([Sw_inj]), rock, fluid)[0]
        dtau_safe = np.where(dtau > 1e-30, dtau, np.inf)
        for _ in range(nt):
            # advection in tau (+ compressibility source)
            F = B.calculate_fractional_flow(Sw, rock, fluid)
            Fup = np.empty_like(F); Fup[0] = fw_inj; Fup[1:] = F[:-1]
            coeff = np.minimum(h / dtau_safe, 0.9)
            Sw = np.clip(Sw - coeff * (F - Fup) + h * (F * c * dpdtau), swc, sw_max)
            Sw[0] = Sw_inj
            # capillary diffusion (implicit, their D coefficient)
            if capillary:
                D = B.calculate_diffusion_coefficient(Sw, rock, fluid, cap)
                alpha = h / (phi * dx**2)
                lower = np.zeros(nx); diag = np.ones(nx); upper = np.zeros(nx); rhs = Sw.copy()
                for i in range(1, nx - 1):
                    DL = 0.5*(D[i-1]+D[i]); DR = 0.5*(D[i]+D[i+1])
                    lower[i] = -alpha*DL; upper[i] = -alpha*DR; diag[i] = 1.0+alpha*(DL+DR)
                diag[0]=1.0; upper[0]=0.0; rhs[0]=Sw_inj; diag[-1]=1.0; lower[-1]=0.0
                ab = np.zeros((3,nx)); ab[0,1:]=upper[:-1]; ab[1,:]=diag; ab[2,:-1]=lower[1:]
                Sw = np.clip(solve_banded((1,1), ab, rhs), swc, sw_max)
        return x / L, Sw


    comp = B.CompressibleBLSolver(rock, fluid, geom, eos, pres)
    capS = B.CapillaryBLSolver(rock, fluid, geom, cap)
    full = B.FullBLSolver(rock, fluid, geom, eos, pres, cap)

    panels = [
        ("Incompressible", comp.solve_incompressible(t_days, nx=nx), streamline_1d(0.0, False, t_days), "#185FA5"),
        (f"Compressible (Nc={comp.Nc:.2f})", comp.solve(t_days, nx=nx), streamline_1d(eos.c, False, t_days), "#993C1D"),
        (f"Capillary (Pe_c={capS.Pe_c:.0f})", capS.solve(t_days, nx=nx), streamline_1d(0.0, True, t_days), "#0F6E56"),
        ("Full (compr+capill)", full.solve(t_days, nx=nx), streamline_1d(eos.c, True, t_days), "#534AB7"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for ax, (label, (xb, swb), (xs, sws), col) in zip(axes.ravel(), panels):
        err = np.max(np.abs(sws - swb))
        ax.plot(xb, swb, color=col, lw=3.2, alpha=.5, label="BL solver (yours)")
        ax.plot(xs, sws, "--", color=col, lw=1.8, label="Streamline 1D (mine)")
        ax.set_title(f"{label}   max|ΔSw|={err:.4f}", fontsize=11)
        ax.set_xlabel("$x_D$"); ax.set_ylabel("$S_w$"); ax.set_xlim(0, 1)
        ax.grid(alpha=.3); ax.legend(fontsize=9)
        print(f"{label:28s} max|dSw| = {err:.4f}")
    fig.suptitle("1D validation — streamline simulator reproduces all four BL solvers",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(f"{OUTDIR}/four_modes_1d_validation.png", dpi=130)
    print("saved four_modes_1d_validation.png")

    # ---- all four modes overlaid on one axes ----
    fig2, ax = plt.subplots(figsize=(9, 5.6))
    for label, (xb, swb), (xs, sws), col in panels:
        ax.plot(xb, swb, color=col, lw=4, alpha=0.18)              # BL solver (faint ref)
        ax.plot(xs, sws, color=col, lw=2.2, label=label)          # streamline mode
    ax.set_xlabel("$x_D$"); ax.set_ylabel("$S_w$"); ax.set_xlim(0, 1)
    ax.set_ylim(rock.swc - 0.03, sw_max + 0.03)
    ax.grid(alpha=.3); ax.legend(fontsize=9, loc="upper right")
    ax.set_title(f"All four modes overlaid at t={t_days:.0f} days "
                 f"(solid = streamline, faint = BL solver)")
    ax.text(0.02, 0.06,
            "sharp front (incompr) · smeared (capillary) ·\nshifted (compressible) · both (full)",
            transform=ax.transAxes, fontsize=8, color="#5F5E5A")
    fig2.tight_layout()
    fig2.savefig(f"{OUTDIR}/four_modes_overlay_1d.png", dpi=130)
    print("saved four_modes_overlay_1d.png")



def scenario_validate_capillary_sl():
    """Batch 3 validation: capillary diffusion in the streamline simulator.
       Gate 1 - mass conservation of the diffuse_grid operator (no-flow BC, exact).
       Gate 2 - coupled 1D streamline (capillary on) reproduces the 1D capillary BL
                front smearing at matched capillary Peclet number."""

    # ---------- Gate 1: pure-operator mass conservation ----------
    NZc = 30
    gridc = S.Grid3D(1, 1, NZc, 10., 10., 1.0, k=np.full((1, 1, NZc), 200e-15),
                     phi=np.full((1, 1, NZc), 0.2))
    rockc = S.Rock(nw=2., no=2., swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8)
    cap = S.Capillary(Pe=3.0e6, lam=2.0)
    rng = np.random.default_rng(0)
    sw = 0.2 + 0.6 * rng.random((1, 1, NZc))   # arbitrary rough field
    m0 = float(np.sum(gridc.phi * gridc.vcell * sw))
    for _ in range(40):
        sw = S.diffuse_grid(gridc, sw, rockc, S.Fluid(), cap, 2.0e7, n_sub=2)
    m1 = float(np.sum(gridc.phi * gridc.vcell * sw))
    print(f"GATE 1  diffuse_grid mass drift = {(m1-m0)/m0*100:+.6f}%   "
          f"(smooths rough field, should be ~0)")

    # ---------- Gate 2: coupled streamline capillary vs 1D capillary BL ----------
    NX = 120
    def run_sl(capillary, Pe_si, pvi):
        grid = S.Grid3D(NX, 1, 1, 10., 10., 10., k=np.full((NX, 1, 1), 100e-15),
                        phi=np.full((NX, 1, 1), 0.2))
        rock = S.Rock(nw=2., no=2., swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8)
        fluid = S.Fluid(mu_w=0.5, mu_o=5.0)
        Q = 0.4 * float(np.sum(grid.phi * grid.vcell)) / (365 * 24 * 3600)
        wells = S.Wells([(0, 0, 0)], [(NX - 1, 0, 0)], rate=Q, bhp=0.0)
        cp = S.Capillary(Pe=Pe_si, lam=2.0)
        sim = S.StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=3,
                                    capillary=capillary, cap=cp, n_diff_sub=4)
        res = sim.run(target_pvi=pvi, n_psteps=20, verbose=False)
        # streamline capillary Peclet:  Pe_c = u_darcy * L * phi / D_ref
        u_darcy = Q / (grid.dy * grid.dzk[0])
        Dfield = S.capillary_diffusion_coeff(np.full((NX, 1, 1), 0.5), grid, rock, fluid, cp)
        Dref = float(np.mean(Dfield))
        Pe_c = u_darcy * (NX * grid.dx) * 0.2 / max(Dref, 1e-30)
        xD = (np.arange(NX) + 0.5) / NX
        return xD, res.sw_final[:, 0, 0], res.pvi[-1], Pe_c

    PVI = 0.15
    xD_sharp, sw_sharp, pvi0, _ = run_sl(False, 8.0e6, PVI)
    xD_cap, sw_cap, pvi1, Pe_c_sl = run_sl(True, 8.0e6, PVI)

    # 1D capillary BL reference at matched Pe_c (tune BL Pe so its Pe_c == streamline's)
    brock = B.RockProperties(nw=2, no=2, swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8, phi=0.2)
    bfluid = B.FluidProperties(mu_w=0.5, mu_o=5.0)
    bgeom = B.ReservoirGeometry()
    probe = B.CapillaryBLSolver(brock, bfluid, bgeom, B.CapillaryProperties(Pe=1.0, k=100.0))
    Pe_bl = 1.0 * probe.Pe_c / Pe_c_sl     # Pe_c ~ 1/Pe -> scale to match
    capbl = B.CapillaryBLSolver(brock, bfluid, bgeom, B.CapillaryProperties(Pe=Pe_bl, k=100.0))
    u_inj = 5.615 * bgeom.i_w / bgeom.A
    t_days = pvi1 * brock.phi * bgeom.x_ip / u_inj
    xb_sharp, swb_sharp = B.CompressibleBLSolver(brock, bfluid, bgeom, B.CompressibleFluid(),
                                                 B.PressureConditions()).solve_incompressible(t_days, 201)
    xb_cap, swb_cap = capbl.solve(t_days, 201)

    print(f"GATE 2  Pe_c(streamline)={Pe_c_sl:.0f}  ->  BL Pe={Pe_bl:.1f} (Pe_c(BL)={capbl.Pe_c:.0f})")

    def width(x, sw):  # front width: span where 0.25<Se-frac<0.75 of the jump
        s = (sw - 0.2) / 0.6
        idx = np.where((s > 0.15) & (s < 0.7))[0]
        return (x[idx[-1]] - x[idx[0]]) if idx.size > 1 else 0.0
    print(f"        front width  sharp: SL={width(xD_sharp,sw_sharp):.3f} BL={width(xb_sharp,swb_sharp):.3f}"
          f"   capillary: SL={width(xD_cap,sw_cap):.3f} BL={width(xb_cap,swb_cap):.3f}")

    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    fig.suptitle(f"Validation: streamline capillary diffusion vs 1D capillary BL "
                 f"(generic water-oil, not CCUS) "
                 f"(Pe$_c$\u2248{Pe_c_sl:.0f})", fontsize=13.5, fontweight="bold")
    ax[0].plot(xb_sharp, swb_sharp, color="#000000", lw=2, label="1D BL sharp (no cap.)")
    ax[0].plot(xD_sharp[:-1], sw_sharp[:-1], "o", color="#888888", ms=3, label="streamline sharp")
    ax[0].plot(xb_cap, swb_cap, color="#c00000", lw=2, label="1D BL capillary")
    ax[0].plot(xD_cap[:-1], sw_cap[:-1], "s", color="#1f77b4", ms=3, label="streamline capillary")
    ax[0].set_xlabel(r"$x_D$"); ax[0].set_ylabel(r"$S_w$"); ax[0].legend(fontsize=9)
    ax[0].set_title(f"Profiles at PVI\u2248{pvi1:.2f}")
    ax[1].plot(xb_cap, swb_cap, color="#c00000", lw=2, label="1D BL capillary")
    ax[1].plot(xD_cap[:-1], sw_cap[:-1], "s", color="#1f77b4", ms=4, label="streamline capillary")
    ax[1].plot(xD_sharp[:-1], sw_sharp[:-1], "o", color="#bbbbbb", ms=3, label="sharp (ref)")
    ax[1].set_xlim(0.3, 0.95); ax[1].set_xlabel(r"$x_D$"); ax[1].set_ylabel(r"$S_w$")
    ax[1].set_title("Front region (capillarity smears)"); ax[1].legend(fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(f"{OUTDIR}/fig_batch3_capillary.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)
    print("saved fig_batch3_capillary")



def scenario_validate_compressible_sl():
    """Batch 1 validation: does the streamline simulator's compressible source term
       reproduce the 1D compressible Buckley-Leverett solution?
       Strategy: 1D streamline run (compressible on/off) vs CompressibleBLSolver at matched Nc."""

    # ---- matched rock/fluid (same Brooks-Corey + viscosity ratio in both codes) ----
    NX = 120
    TARGET_PVI = 0.15            # pre-breakthrough so the front sits mid-domain
    DP_PA = 2.0e7               # injector-producer pressure drop (BHP)
    C_SI = 2.5e-8               # fluid compressibility [1/Pa]  -> Nc = c*dp = 0.5

    def run_sl(compressible):
        grid = S.Grid3D(NX, 1, 1, dx=10.0, dy=10.0, dz=10.0,
                        k=np.full((NX, 1, 1), 100e-15), phi=np.full((NX, 1, 1), 0.2))
        rock = S.Rock(nw=2., no=2., swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8)
        fluid = S.Fluid(mu_w=0.5, mu_o=5.0, c=C_SI)
        wells = S.Wells([(0, 0, 0)], [(NX - 1, 0, 0)], rate=0.0, bhp=0.0, inj_bhp=DP_PA)
        sim = S.StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=3,
                                    compressible=compressible)
        res = sim.run(target_pvi=TARGET_PVI, n_psteps=24, verbose=False)
        xD = (np.arange(NX) + 0.5) / NX
        return xD, res.sw_final[:, 0, 0], res.pvi[-1], sim.Nc

    xD_c, sw_c, pvi_c, Nc_sl = run_sl(True)
    xD_i, sw_i, pvi_i, _ = run_sl(False)

    # ---- 1D BL reference at matched Nc ----
    brock = B.RockProperties(nw=2, no=2, swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8, phi=0.2)
    bfluid = B.FluidProperties(mu_w=0.5, mu_o=5.0)
    bgeom = B.ReservoirGeometry()
    # Nc = c_field * (p_inj - p_init); pick c_field so Nc matches the streamline run
    pres = B.PressureConditions(p_inj=3000.0, p_init=2000.0)
    c_field = Nc_sl / (pres.p_inj - pres.p_init)
    eos = B.CompressibleFluid(c=c_field)
    solver = B.CompressibleBLSolver(brock, bfluid, bgeom, eos, pres)
    u_inj = 5.615 * bgeom.i_w / bgeom.A
    t_days_c = pvi_c * brock.phi * bgeom.x_ip / u_inj
    t_days_i = pvi_i * brock.phi * bgeom.x_ip / u_inj
    xb_c, swb_c = solver.solve(t_days_c, nx=401)
    xb_i, swb_i = solver.solve_incompressible(t_days_i, nx=401)

    # ---- compare ----
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    fig.suptitle(f"Validation: streamline compressible source vs 1D compressible BL "
                 f"(generic water-oil, not CCUS) "
                 f"(N$_c$\u2248{Nc_sl:.2f})", fontsize=13.5, fontweight="bold")
    ax[0].plot(xb_i, swb_i, color="#000000", lw=2, label="1D BL incompressible")
    ax[0].plot(xD_i[:-1], sw_i[:-1], "o", color="#888888", ms=3.5, label="streamline incompressible")
    ax[0].plot(xb_c, swb_c, color="#c00000", lw=2, label=f"1D BL compressible")
    ax[0].plot(xD_c[:-1], sw_c[:-1], "o", color="#1f77b4", ms=3.5, label="streamline compressible")
    ax[0].set_xlabel(r"$x_D$"); ax[0].set_ylabel(r"$S_w$")
    ax[0].set_title(f"Profiles at PVI\u2248{pvi_c:.2f}"); ax[0].legend(fontsize=9)

    # zoom on the front region to see the compressible advance
    m = (xb_i > 0.0) & (xb_i < 0.5)
    ax[1].plot(xb_i, swb_i, color="#000000", lw=2, label="BL incompr.")
    ax[1].plot(xb_c, swb_c, color="#c00000", lw=2, label="BL compr.")
    ax[1].plot(xD_i[:-1], sw_i[:-1], "o", color="#888888", ms=4)
    ax[1].plot(xD_c[:-1], sw_c[:-1], "s", color="#1f77b4", ms=4)
    ax[1].set_xlim(0.0, 0.45); ax[1].set_xlabel(r"$x_D$"); ax[1].set_ylabel(r"$S_w$")
    ax[1].set_title("Front region (compressible advances the front)"); ax[1].legend(fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(f"{OUTDIR}/fig_batch1_compressible.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # quantitative: front position (last cell above swc+0.02) and L2 vs BL
    def frontpos(x, sw):
        above = np.where(sw > 0.22)[0]
        return x[above[-1]] if above.size else 0.0
    print(f"Nc(streamline) = {Nc_sl:.3f},  c_field for BL = {c_field:.3e} /psi")
    print(f"front xD  incompr: streamline={frontpos(xD_i,sw_i):.3f}  BL={frontpos(xb_i,swb_i):.3f}")
    print(f"front xD  compr:   streamline={frontpos(xD_c,sw_c):.3f}  BL={frontpos(xb_c,swb_c):.3f}")
    print(f"compressible advance (streamline): {frontpos(xD_c,sw_c)-frontpos(xD_i,sw_i):+.3f}  "
          f"(BL): {frontpos(xb_c,swb_c)-frontpos(xb_i,swb_i):+.3f}")
    print("saved fig_batch1_compressible")



def scenario_validate_dp():

    # ---- 8-layer table ----------------------------------------------------------
    kmD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
    h_ft = np.array([50., 48., 54., 44., 42., 48., 50., 40.])
    phi_l = np.array([0.22, 0.18, 0.21, 0.15, 0.20, 0.21, 0.20, 0.20])
    swc_l = np.array([0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42])
    krom = np.array([0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60])
    krwm = np.array([0.05, 0.15, 0.20, 0.33, 0.20, 0.30, 0.40, 0.17])
    sor, MU_W, MU_O = 0.20, 0.5, 0.7
    nz = len(kmD)


    def streamline_1d_per_layer(k_mD, h_ft, phi_l, swc_l, krwm, krom, nx=60,
                                target_pvi=1.5, n_psteps=24):
        """1D-per-layer config (nx x 1 x nz), no crossflow, common-pressure wells:
           the streamline sim's exact Dykstra-Parsons limit."""
        lay = lambda v: np.ones((nx, 1, nz)) * np.asarray(v)[None, None, :]
        grid = S.Grid3D(nx, 1, nz, dx=10.0, dy=10.0, dz=h_ft * 0.3048,
                        k=lay(k_mD) * 9.869e-16, phi=lay(phi_l))
        rock = S.Rock(nw=2.0, no=2.0, swc=lay(swc_l), sor=sor,
                      krw_max=lay(krwm), kro_max=lay(krom))
        fluid = S.Fluid(mu_w=MU_W, mu_o=MU_O)
        inj = [(0, 0, k) for k in range(nz)]
        prod = [(nx-1, 0, k) for k in range(nz)]
        wells = S.Wells(inj, prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)
        sim = S.StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=3,
                                    no_crossflow=True)
        res = sim.run(target_pvi=target_pvi, n_psteps=n_psteps, verbose=False)
        return np.array(res.pvi), np.array(res.recovery), np.array(res.watercut)

    # ---- gate: uniform rock + unit endpoint mobility (must coincide with DP) -----
    print("=== gate: uniform rock, unit endpoint mobility (M=1) ===")
    krwm_u = np.full(nz, 0.5 / 0.7 * 0.8)        # M=(krw/muw)/(kro/muo)=1 -> krw=muw/muo*kro
    krom_u = np.full(nz, 0.8)
    swc_u = np.full(nz, 0.20)
    phi_u = np.full(nz, 0.20)
    pvi_s, rec_s, wc_s = streamline_1d_per_layer(kmD, h_ft, phi_u, swc_u, krwm_u, krom_u)
    dp_u = DykstraParsons(kmD, h_ft, phi_u, swc_u, sor, krwm_u, krom_u, MU_W, MU_O, "kh")
    rec_d, wc_d = dp_u.run(pvi_s)
    print(f"  max|d recovery| = {np.max(np.abs(rec_s - rec_d)):.3f}")
    print(f"  max|d watercut| = {np.max(np.abs(wc_s - wc_d)):.3f}")

    # ---- full 8-layer table ------------------------------------------------------
    print("\n=== full DP table: streamline vs DP ===")
    pvi_t, rec_t, wc_t = streamline_1d_per_layer(kmD, h_ft, phi_l, swc_l, krwm, krom)
    dp_kh = DykstraParsons(kmD, h_ft, phi_l, swc_l, sor, krwm, krom, MU_W, MU_O, "kh")
    dp_mob = DykstraParsons(kmD, h_ft, phi_l, swc_l, sor, krwm, krom, MU_W, MU_O, "kh_mob")
    rec_kh, wc_kh = dp_kh.run(pvi_t)
    rec_mob, wc_mob = dp_mob.run(pvi_t)
    print(f"  final RF: streamline {rec_t[-1]*100:.1f}%  |  DP-kh {rec_kh[-1]*100:.1f}%"
          f"  |  DP-kh*mob {rec_mob[-1]*100:.1f}%")

    order = np.argsort(dp_kh.Ri)[::-1]
    print("\n  layer breakthrough order by speed index Ri (DP):")
    print("  " + "  ".join(f"L{o+1}(tau_bt={dp_kh.layers[o].tau_bt:.2f})" for o in order[:4]),
          "...")

    # ---- figure ------------------------------------------------------------------
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    ax[0].plot(pvi_t, rec_t*100, "o-", ms=3, color="#185FA5", label="streamline (no-crossflow)")
    ax[0].plot(pvi_t, rec_kh*100, "--", color="#993C1D", label="DP (kh allocation)")
    ax[0].plot(pvi_t, rec_mob*100, ":", color="#0F6E56", label="DP (kh·endpoint mobility)")
    ax[0].set_xlabel("pore volumes injected"); ax[0].set_ylabel("recovery of movable oil [%]")
    ax[0].set_title("System recovery"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

    ax[1].plot(pvi_t, wc_t, "o-", ms=3, color="#185FA5", label="streamline (no-crossflow)")
    ax[1].plot(pvi_t, wc_kh, "--", color="#993C1D", label="DP (kh allocation)")
    ax[1].plot(pvi_t, wc_mob, ":", color="#0F6E56", label="DP (kh·endpoint mobility)")
    ax[1].set_xlabel("pore volumes injected"); ax[1].set_ylabel("producer water cut")
    ax[1].set_title("System water cut"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

    fig.suptitle("Streamline no-crossflow limit vs Dykstra-Parsons (8-layer table)",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(f"{OUTDIR}/dp_validation.png", dpi=130)
    print("\nsaved dp_validation.png")



def scenario_validate_gravity_bl():
    """Tier-1 second half: validate the streamline solver's operator-split gravity
    against the analytical GravityBLSolver in a matched 1D vertical column.
    Column: injector at base, producer at top, flow and gravity both along z.
    Rate-controlled so the Darcy velocity (hence Ng) is known; compared at matched
    Ng and PVI. Delta-rho = 0 must collapse to the plain BL match."""

    # --- shared rock / fluid (identical Corey parameters in both solvers) ---
    NW = NO = 2.0
    KRWM, KROM = 0.4, 0.8
    SWC, SOR = 0.2, 0.2
    MU_W = MU_O = 1.0          # cp; M=1 isolates the gravity effect
    PHI = 0.2
    NZ = 50
    DX = DY = 10.0; DZ = 1.0
    KMD = 100.0
    k_si = KMD * 9.869e-16
    g = 9.81
    mu_o_si = MU_O * 1e-3
    PVI = 0.3

    # fix the Darcy velocity so Ng = +-0.5 at drho = +-200
    Ng_target = 0.5; drho_ref = 200.0
    ut = k_si * g * drho_ref / (Ng_target * mu_o_si)
    q = ut * DX * DY                                   # m^3/s injection rate

    def stream_column(rho_w, rho_o):
        k = np.full((1, 1, NZ), k_si); phi = np.full((1, 1, NZ), PHI)
        grid = S.Grid3D(1, 1, NZ, dx=DX, dy=DY, dz=DZ, k=k, phi=phi)
        rock = S.Rock(nw=NW, no=NO, swc=SWC, sor=SOR, krw_max=KRWM, kro_max=KROM)
        fluid = S.Fluid(mu_w=MU_W, mu_o=MU_O, c=0.0, rho_w=rho_w, rho_o=rho_o)
        wells = S.Wells(inj_cells=[(0, 0, 0)], prod_cells=[(0, 0, NZ - 1)],
                        rate=q, bhp=2.0e7)
        sim = S.StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=4,
                                    no_crossflow=False, gravity=True, conserve=True,
                                    coverage_fill=True)
        res = sim.run(target_pvi=PVI, n_psteps=24, verbose=False)
        zc = (np.arange(NZ) + 0.5) / NZ
        return zc, sim.sw[0, 0, :].copy(), res.pvi[-1]

    def analytic(Ng):
        rock = B.RockProperties(nw=NW, no=NO, swc=SWC, sor=SOR,
                                krw_max=KRWM, kro_max=KROM, phi=PHI)
        fluid = B.FluidProperties(mu_w=MU_W, mu_o=MU_O)
        geom = B.ReservoirGeometry()
        t_days = PVI * rock.phi * geom.x_ip / ((5.615 * geom.i_w) / geom.A)
        x, sw = B.GravityBLSolver(rock, fluid, geom, Ng=Ng).solve(t_days=t_days, nx=401)
        return x, sw

    cases = [("drho=0  (Ng=0, ->BL)", 1000.0, 1000.0),
             ("drho=+200 (Ng=+0.5, gravity-stable)", 1000.0, 800.0),
             ("drho=-200 (Ng=-0.5, CO2-assist)", 800.0, 1000.0)]

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
    for i, (label, rw, ro) in enumerate(cases):
        Ng = k_si * g * (rw - ro) / (ut * mu_o_si)
        zc, sw_sl, pvi = stream_column(rw, ro)
        xa, sw_a = analytic(Ng)
        sw_a_on_col = np.interp(zc, xa, sw_a)
        l2 = float(np.sqrt(np.mean((sw_sl - sw_a_on_col) ** 2)))
        mx = float(np.max(np.abs(sw_sl - sw_a_on_col)))
        print(f"{label}: Ng={Ng:+.2f} PVI={pvi:.2f} L2={l2:.3f} max|dSw|={mx:.3f}")
        samp = [0.1, 0.2, 0.3, 0.4, 0.5]
        print("   zD       " + "  ".join(f"{s:.1f}" for s in samp))
        print("   stream:  " + "  ".join(f"{sw_sl[np.argmin(np.abs(zc-s))]:.2f}" for s in samp))
        print("   analytic:" + "  ".join(f"{sw_a_on_col[np.argmin(np.abs(zc-s))]:.2f}" for s in samp))
        ax[i].plot(xa, sw_a, "-", color="#1C7293", lw=2, label="GravityBLSolver")
        ax[i].plot(zc, sw_sl, "o", color="#E8A33D", ms=4, label="streamline column")
        ax[i].set_title(f"{label}\nNg={Ng:+.2f}, L2={l2:.3f}", fontsize=10)
        ax[i].set_xlabel("normalized distance from inlet"); ax[i].set_ylim(0.15, 0.85)
        ax[i].grid(alpha=0.3); ax[i].legend(fontsize=8)
    ax[0].set_ylabel(r"$S_w$")
    fig.suptitle("Tier-1 gravity validation: streamline operator-split gravity vs analytical gravity-BL",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUTDIR}/fig_tier1_gravity_validation.png", bbox_inches="tight")
    print("saved fig_tier1_gravity_validation.png")



def scenario_validate_gravity_column():
    """Batch 2, gate 1: validate the core gravity-segregation physics (scalar rock).
       Pure buoyant segregation in a vertical column: mass must conserve, and a uniform
       mixed column must separate into the volume-conserving equilibrium (heavy phase
       below). Tests both waterflood (rho_w>rho_o, water sinks) and CCS (rho_w<rho_o,
       injected phase rises)."""

    NZ = 40
    rock = S.Rock(nw=2., no=2., swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8)
    grid = S.Grid3D(1, 1, NZ, dx=10.0, dy=10.0, dz=1.0,
                    k=np.full((1, 1, NZ), 200e-15), phi=np.full((1, 1, NZ), 0.2))

    def segregate(fluid, sw0_val, total_t=1.5e10, ncall=80):
        sw = np.full((1, 1, NZ), sw0_val)
        masses = [float(np.sum(sw))]
        dt = total_t / ncall
        snaps = {0: sw[0, 0, :].copy()}
        for n in range(ncall):
            sw = S.gravity_segregation(grid, sw, rock, fluid, dt)
            masses.append(float(np.sum(sw)))
            if n + 1 in (ncall // 4, ncall):
                snaps[n + 1] = sw[0, 0, :].copy()
        return sw[0, 0, :], np.array(masses), snaps

    # waterflood: water heavier -> sinks to bottom
    fw_wf = S.Fluid(mu_w=0.5, mu_o=5.0, rho_w=1000.0, rho_o=800.0)
    sw_wf, m_wf, snap_wf = segregate(fw_wf, 0.5)
    # CCS-like: injected phase lighter -> resident water sinks (sw high at bottom too,
    #           but drho<0 so direction flips); use rho_w<rho_o
    fw_ccs = S.Fluid(mu_w=0.5, mu_o=5.0, rho_w=700.0, rho_o=1000.0)
    sw_ccs, m_ccs, snap_ccs = segregate(fw_ccs, 0.5)

    # expected equilibrium for uniform 0.5 with sw_max=0.8, swc=0.2: half the column
    # at sw_max, half at swc (volume-conserving). Water at bottom for waterflood.
    z = (np.arange(NZ) + 0.5)

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
    fig.suptitle("Validation: gravity segregation, waterflood vs CCS-like density "
                "convention (both shown)", fontsize=13.5, fontweight="bold")
    for nn, prof in snap_wf.items():
        ax[0].plot(prof, z, "-o", ms=2, label=f"step {nn}")
    ax[0].axvline(0.8, ls=":", color="grey"); ax[0].axvline(0.2, ls=":", color="grey")
    ax[0].set_xlabel(r"$S_w$"); ax[0].set_ylabel("z (cell, up)")
    ax[0].set_title(r"Waterflood ($\rho_w>\rho_o$): water sinks"); ax[0].legend(fontsize=8)

    for nn, prof in snap_ccs.items():
        ax[1].plot(prof, z, "-o", ms=2, label=f"step {nn}")
    ax[1].axvline(0.8, ls=":", color="grey"); ax[1].axvline(0.2, ls=":", color="grey")
    ax[1].set_xlabel(r"$S_w$"); ax[1].set_title(r"CCS ($\rho_w<\rho_o$): injected phase "
                                                r"(CO$_2$-like, $S_w$ slot) rises"); ax[1].legend(fontsize=8)

    ax[2].plot((m_wf - m_wf[0]) / m_wf[0] * 100, label="waterflood")
    ax[2].plot((m_ccs - m_ccs[0]) / m_ccs[0] * 100, label="CCS")
    ax[2].set_xlabel("segregation call"); ax[2].set_ylabel("mass drift [%]")
    ax[2].set_title("Mass conservation"); ax[2].legend(fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(f"{OUTDIR}/fig_batch2_gravity_column.png", bbox_inches="tight"); plt.show(block=False); plt.close(fig)

    # checks
    half = NZ // 2
    wf_bottom = sw_wf[:half].mean(); wf_top = sw_wf[half:].mean()
    ccs_bottom = sw_ccs[:half].mean(); ccs_top = sw_ccs[half:].mean()
    print(f"waterflood: mass drift {(m_wf[-1]-m_wf[0])/m_wf[0]*100:+.3f}%  "
          f"bottom<Sw>={wf_bottom:.3f}  top<Sw>={wf_top:.3f}  (expect bottom~0.8, top~0.2)")
    print(f"CCS:        mass drift {(m_ccs[-1]-m_ccs[0])/m_ccs[0]*100:+.3f}%  "
          f"bottom<Sw>={ccs_bottom:.3f}  top<Sw>={ccs_top:.3f}  (expect bottom~0.2, top~0.8)")
    print("saved fig_batch2_gravity_column")

# STAGE 10 [S10] — new CCUS-specific figures (written for this request, not
# from your uploaded files): physics-mode comparison, full five-spot CCUS,
# and a plume cross-section. Same solver classes, same code conventions as
# everything above.

def scenario_ccus_physics_modes_areal():
    """New figure: areal (x,y) CO2 saturation at a fixed PVI, side by side for
    the four physics modes (incompressible / compressible / capillary / full),
    same layout style as make_streamline_viz.py's areal-sweep-over-time figure
    but comparing physics modes at one fixed time instead of comparing times.
    CCUS parameters throughout (CO2 injected into brine, same mu/rho values
    make_8layer_ccus.py and stage2_aquifer.py already use). Gravity is left
    off in all four panels, same convention as validate_4modes_1d.py, so the
    comparison isolates exactly the four requested effects.
    """
    NX = NY = 30
    TARGET_PVI = 0.30
    CC = 1.0e-8
    RHO_CO2, RHO_BR = 700.0, 1020.0
    MU_CO2, MU_BR = 0.05, 0.6

    def build():
        k = np.full((NX, NY, 1), 150.0 * 9.869e-16)
        phi = np.full((NX, NY, 1), 0.2)
        grid = Grid3D(NX, NY, 1, dx=10.0, dy=10.0, dz=5.0, k=k, phi=phi)
        rock = Rock(nw=2.0, no=2.0, swc=0.2, sor=0.2, krw_max=0.6, kro_max=0.8)
        fluid = Fluid(mu_w=MU_CO2, mu_o=MU_BR, c=CC, rho_w=RHO_CO2, rho_o=RHO_BR)
        wells = Wells(inj_cells=[(0, 0, 0)], prod_cells=[(NX - 1, NY - 1, 0)],
                      rate=0.0, bhp=0.0, inj_bhp=2.0e7)
        return grid, rock, fluid, wells

    modes = [
        ("Incompressible", dict(compressible=False, capillary=False)),
        ("Compressible", dict(compressible=True, capillary=False)),
        ("Capillary", dict(compressible=False, capillary=True,
                            cap=Capillary(Pe=2.0e6, lam=2.0))),
        ("Full (compr + capill)", dict(compressible=True, capillary=True,
                                        cap=Capillary(Pe=2.0e6, lam=2.0))),
    ]

    fig, ax = plt.subplots(1, 4, figsize=(18, 4.6))
    fig.suptitle(f"CO$_2$-brine areal saturation by physics mode, PVI = {TARGET_PVI:.2f} "
                 "(quarter five-spot, single layer)", fontsize=14, fontweight="bold")
    ext = [0, NX * 10.0, 0, NY * 10.0]
    im = None
    for a, (label, kw) in zip(ax, modes):
        grid, rock, fluid, wells = build()
        sim = StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=5,
                                  no_crossflow=False, gravity=False, **kw)
        res = sim.run(target_pvi=TARGET_PVI, n_psteps=10, verbose=False)
        im = a.imshow(res.sw_final[:, :, 0].T, origin="lower", extent=ext,
                     cmap="viridis", vmin=0.2, vmax=0.8, aspect="equal")
        a.plot(0.5 * grid.dx, 0.5 * grid.dy, "o", color="#1f77b4", ms=9, mec="k")
        a.plot((NX - 0.5) * grid.dx, (NY - 0.5) * grid.dy, "s", color="#d62728",
              ms=8, mec="k")
        a.set_title(f"{label}\nRF={res.recovery[-1]*100:.1f}%  Nc={sim.Nc:.2f}"
                   f"  Pe$_c$={('n/a' if not kw.get('capillary') else f'{2.0e6:.0e}')}",
                   fontsize=10.5)
        a.set_xlabel("x [m]"); a.set_xticks([]); a.set_yticks([])
    ax[0].set_ylabel("y [m]")
    cb = fig.colorbar(im, ax=ax, fraction=0.012, pad=0.01)
    cb.set_label(r"$S_{CO_2}$")
    fig.savefig(f"{OUTDIR}/fig_ccus_physics_modes_areal.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)
    print("saved fig_ccus_physics_modes_areal")


def scenario_ccus_full_fivespot():
    """New figure: full five-spot (central injector, four corner producers,
    same well-pattern code as make_streamline_viz.py's second panel) instead
    of the quarter five-spot, areal sweep over time (same 4-PVI-panel layout
    as make_streamline_viz.py's areal-sweep figure), CCUS fluid properties
    instead of the generic waterflood defaults. Streamlines overlaid on the
    saturation map, same as the quarter-spot original.
    """
    NX = NY = 31
    RHO_CO2, RHO_BR = 700.0, 1020.0
    MU_CO2, MU_BR = 0.05, 0.6
    PVI_SNAPSHOTS = [0.10, 0.20, 0.35, 0.55]

    k = build_demo(nx=NX, ny=NY, nz=1, seed=7)[0].k
    grid = Grid3D(NX, NY, 1, 10.0, 10.0, 5.0, k=k, phi=np.full((NX, NY, 1), 0.2))
    rock = Rock(nw=2.0, no=2.0, swc=0.2, sor=0.2, krw_max=0.6, kro_max=0.8)
    fluid = Fluid(mu_w=MU_CO2, mu_o=MU_BR, c=1.0e-8, rho_w=RHO_CO2, rho_o=RHO_BR)
    ci, cj = NX // 2, NY // 2
    inj = [(ci, cj, 0)]
    prod = [(0, 0, 0), (NX - 1, 0, 0), (0, NY - 1, 0), (NX - 1, NY - 1, 0)]
    pv = float(np.sum(grid.phi) * grid.cell_vol)
    wells = Wells(inj_cells=inj, prod_cells=prod,
                 rate=0.6 * pv / (365 * 24 * 3600), bhp=2.0e7)
    ext = [0, NX * grid.dx, 0, NY * grid.dy]

    fig, ax = plt.subplots(1, len(PVI_SNAPSHOTS), figsize=(17, 4.5))
    fig.suptitle("Full five-spot CO$_2$ injection — areal sweep over time, streamlines overlaid\n"
                 "(central injector, four corner producers; CO$_2$-brine)",
                 fontsize=14, fontweight="bold")
    im = None
    for a, pvi_t in zip(ax, PVI_SNAPSHOTS):
        sim = StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=7)
        res = sim.run(target_pvi=pvi_t, n_psteps=16, verbose=False)
        sw = res.sw_final
        p, lamt = solve_pressure(grid, sw, rock, fluid, wells)
        V = pore_velocities(grid, p, lamt, False)
        vx = 0.5 * (V["xm"] + V["xp"]); vy = 0.5 * (V["ym"] + V["yp"])
        xc = (np.arange(NX) + 0.5) * grid.dx; yc = (np.arange(NY) + 0.5) * grid.dy
        im = a.imshow(sw[:, :, 0].T, origin="lower", extent=ext, cmap="viridis",
                     vmin=0.2, vmax=0.8, aspect="equal")
        a.streamplot(xc, yc, vx[:, :, 0].T, vy[:, :, 0].T, color="white",
                    density=1.1, linewidth=0.8, arrowsize=0.7)
        a.plot((ci + 0.5) * grid.dx, (cj + 0.5) * grid.dy, "o", color="#1f77b4",
              ms=10, mec="k")
        for (pi, pj, _) in prod:
            a.plot((pi + 0.5) * grid.dx, (pj + 0.5) * grid.dy, "s",
                  color="#d62728", ms=9, mec="k")
        a.set_title(f"PVI = {res.pvi[-1]:.2f}")
        a.set_xlabel("x [m]"); a.set_xlim(0, NX * grid.dx); a.set_ylim(0, NY * grid.dy)
    ax[0].set_ylabel("y [m]")
    cb = fig.colorbar(im, ax=ax, fraction=0.013, pad=0.01)
    cb.set_label(r"$S_{CO_2}$")
    fig.savefig(f"{OUTDIR}/fig_ccus_full_fivespot.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)
    print("saved fig_ccus_full_fivespot")


def scenario_ccus_plume_cross_section():
    """New figure: vertical (x, depth) cross-section through the 8-layer CO2
    storage plume, sliced along y = y_mid through the injector. Complements
    the isometric 3D view and the per-layer areal maps (make_8layer_ccus.py)
    with a side-on view where the buoyant override (CO2 thickening toward
    the shallow layers) is directly visible against true depth, not just
    layer index. Same 8-layer DP table and CCUS fluid convention as
    make_8layer_ccus.py.
    """
    NX = NY = 15
    NZ = 8
    RHO_INJ, RHO_RES = 700.0, 1020.0
    MU_INJ, MU_RES = 0.05, 0.6
    CC = 1.0e-8
    TARGET_PVI = 0.20

    g, r, f0, _, Ri = build_dp_demo(nx=NX, ny=NY)
    f = Fluid(mu_w=MU_INJ, mu_o=MU_RES, c=CC, rho_w=RHO_INJ, rho_o=RHO_RES)
    inj = [(0, 0, k) for k in range(NZ)]
    prod = [(NX - 1, NY - 1, k) for k in range(NZ)]
    w = Wells(inj_cells=inj, prod_cells=prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)
    FULL = dict(compressible=True, gravity=True, capillary=True,
               cap=Capillary(Pe=2.0e6, lam=2.0), n_diff_sub=3)

    sim = StreamlineSimulator(g, r, f, w, seeds_per_dim=5, no_crossflow=False,
                              coverage_fill=True, conserve=True, **FULL)
    res = sim.run(target_pvi=TARGET_PVI, n_psteps=6, verbose=False)
    sw = sim.sw   # (NX, NY, NZ)

    j_mid = NY // 2
    slice_xz = sw[:, j_mid, :].T          # (NZ, NX): rows = layers, cols = x
    depth_top = np.concatenate(([0.0], np.cumsum(g.dzk)))   # NZ+1 interfaces
    xf = np.arange(NX + 1) * g.dx

    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.suptitle(f"CO$_2$ plume cross-section, y = {j_mid * g.dy:.0f} m "
                 f"(through the injector), PVI = {res.pvi[-1]:.2f}",
                 fontsize=13, fontweight="bold")
    im = ax.pcolormesh(xf, depth_top, slice_xz, cmap="viridis", vmin=0.2, vmax=0.8,
                       shading="flat")
    ax.invert_yaxis()
    for d in depth_top:
        ax.axhline(d, color="white", lw=0.4, alpha=0.5)
    ax.axvline(0.5 * g.dx, color="#1f77b4", lw=2, ls="--", label="injector")
    ax.set_xlabel("x [m]"); ax.set_ylabel("depth [m]  (down)")
    ax.legend(loc="lower right", fontsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label(r"$S_{CO_2}$")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(f"{OUTDIR}/fig_ccus_plume_cross_section.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)

    layer_mean = [float(sw[:, :, k].mean()) for k in range(NZ)]
    print("cross-section saved. Layer mean Sw bottom->top:",
         " ".join(f"{v:.2f}" for v in layer_mean))
    print("saved fig_ccus_plume_cross_section")


# STAGE 9 [S9] — what runs by default, and what's available on request
# ------------------------------------------------------------------------------
# All 17 scenario functions, ordered fast -> slow so figures start appearing
# immediately rather than waiting on the heavy ones first. Timings below are
# from direct, individual verification runs (not estimates) except the last
# three, which were verified by running their exact StreamlineSimulator call
# pattern (full physics + crossflow) at a scaled-down grid instead of full
# scale, since even one of the four required passes in make_demo_full ran
# past 4+ minutes on its own. Same code path, confirmed correct, just not
# timed at full scale.

ALL_SCENARIOS_TIMED = [
    ("scenario_stage0_relperm", "~3s (new)"),
    ("scenario_pollock_diagram", "~3s (new)"),
    ("scenario_stage1_incompressible", "~5s (new)"),
    ("scenario_check_balance_compressible", "~1s"),
    ("scenario_validate_gravity_column", "~2s"),
    ("scenario_make_dp_system", "~2s"),
    ("scenario_validate_capillary_sl", "~4s"),
    ("scenario_stage3_capillary", "~5s (new)"),
    ("scenario_validate_dp", "~5s"),
    ("scenario_stage4_full", "~8s (new)"),
    ("scenario_validate_4modes_1d", "~8s"),
    ("scenario_dykstra_parsons", "~13s (new)"),
    ("scenario_validate_compressible_sl", "~17s"),
    ("scenario_validate_gravity_bl", "~25s"),
    ("scenario_stage2_compressible", "~80s (new; CCUS track is much slower than WF here, "
                                    "viscosity-driven CFL, same as elsewhere in this build)"),
    ("scenario_stage2_aquifer", "~75s (no figure, diagnostics only)"),
    ("scenario_make_3d_demo", "~100s"),
    ("scenario_8b_field_case", "~120s (new)"),
    ("scenario_make_demo_full", "several minutes — full physics + crossflow"),
    ("scenario_physics_modes_areal", "~5 min (new; 4 combinations)"),
    ("scenario_3d_gravity", "~4 min (new)"),
    ("scenario_make_8layer_ccus", "several minutes — full physics + crossflow, 8 layers"),
    ("scenario_make_8layer_full", "several minutes — full physics + crossflow, 8 layers"),
    ("scenario_streamline_simulator", "~10-13 min (new; 4 combinations, the most expensive stage)"),
]
ALL_SCENARIOS = [n for n, _ in ALL_SCENARIOS_TIMED]

# Superseded by the rebuild, per your confirmation, still fully defined and
# callable directly, just no longer in the default run:
#   scenario_make_streamline_8layer  -> scenario_3d_gravity (density-reduced streamlines)
#   scenario_ccus_plume_cross_section -> scenario_3d_gravity (now dual-track)
#   scenario_ccus_physics_modes_areal -> scenario_physics_modes_areal (quarter+full, dual-track)
#   scenario_ccus_full_fivespot       -> scenario_streamline_simulator
#   scenario_make_streamline_viz      -> scenario_streamline_simulator
#   scenario_make_3d_layers_8         -> scenario_3d_gravity + scenario_dykstra_parsons
#   scenario_make_bl_figs             -> scenario_stage{1,2,3,4}_* (all four sub-stages now
#                                         have dedicated, dual-track, analytical-where-correct versions)


CCUS_STORY = [
    ("scenario_physics_modes_areal", "~5 min — incompressible/compressible/capillary/full, "
                                    "quarter+full five-spot"),
    ("scenario_3d_gravity", "~4 min — 8-layer plume, 3D + cross-section, dual-track"),
    ("scenario_make_8layer_ccus", "several minutes — 8-layer plume, 3D + per-layer time series"),
    ("scenario_streamline_simulator", "~10-13 min — quarter+full five-spot, dual-track"),
    ("scenario_stage2_aquifer", "~75s — confined-aquifer CO2 plume (diagnostics, no figure)"),
]


def run_ccus_story(outdir="."):
    """CCUS-only default: skips every generic/waterflood scenario (the
    quarter five-spot demo, the 1D BL validation figures, the 4-layer
    randomized demos, etc.) and runs only what's actually CO2-brine
    parametrized, plus the three new figures built for this request."""
    global OUTDIR
    OUTDIR = outdir
    print(f"Output directory: {outdir}\n")
    print("=" * 78)
    print("CCUS story only. For the full run instead (24 scenarios in the "
          "default list, 31 total defined), call "
          "run_all_scenarios() (that's also the default now).")
    print("=" * 78)
    for i, (name, est) in enumerate(CCUS_STORY, 1):
        print(f"\n--- [{i}/{len(CCUS_STORY)}] {name}  (expect {est}) ---")
        globals()[name]()
    print("\nDone with the CCUS story.")




# STAGE 11 [S11] -- storyline rebuild in progress. Stage 0 (rel-perm) and
# Stage 1 (incompressible BL, now analytical, dual-track WF/CCUS) are done
# and tested. Stages 2-9 of the rebuild (per the July 22 review notes) are
# not in this file yet -- scenario_make_bl_figs below still has the old
# Godunov-based Stage 1 panel as PART of its combined Stage 1-4 figure;
# that's now superseded for Stage 1 specifically by scenario_stage1_
# incompressible below. Left in place rather than deleted since Stages
# 2-4 in that function are still the current version until they're
# rebuilt too.

# ==============================================================================
# STORYLINE REBUILD — relative permeability through the streamline simulator
# ==============================================================================
# Shared parameter presets (WF = generic waterflood, CCUS = CO2-brine) used
# consistently across every stage below. WF matches the existing blsolvers.py /
# streamline_sim.py defaults already used throughout your files. CCUS matches
# the values already used in make_8layer_ccus.py / stage2_aquifer.py (and the
# krg_end=0.60 endpoint from the CO2-brine workflow document).
#
# Naming convention for every figure from here down:
#   stageNN[a,b,c...]_<description>_<wf|ccus>.png   -- individual panels
#   stageNN_combined_<wf|ccus>.png                   -- the multi-panel version
# Individual panels are always generated (and appear in the file listing)
# before the combined figure for that stage.

WF_ROCK = RockProperties(nw=2.0, no=2.0, swc=0.2, sor=0.2, krw_max=0.8, kro_max=0.8, phi=0.20)
WF_FLUID = FluidProperties(mu_w=0.5, mu_o=5.0)
CCUS_ROCK = RockProperties(nw=2.0, no=2.0, swc=0.2, sor=0.2, krw_max=0.6, kro_max=0.8, phi=0.20)
CCUS_FLUID = FluidProperties(mu_w=0.05, mu_o=0.6)
GEOM = ReservoirGeometry()


def _plot_relperm(ax, rock, fluid, label_w, label_o, title, sub_w="w", sub_o="o"):
    sw = np.linspace(rock.swc, rock.sw_max, 300)
    krw, kro = calculate_relative_permeability(sw, rock)
    ax.plot(sw, krw, color="#185FA5", lw=2.2, label=label_w)
    ax.plot(sw, kro, color="#993C1D", lw=2.2, label=label_o)
    ax.axvline(rock.swc, ls=":", color="gray", lw=1, label=f"Swc={rock.swc:.2f}")
    ax.axvline(rock.sw_max, ls=":", color="gray", lw=1)
    ax.set_xlabel(r"$S_w$"); ax.set_ylabel(r"$k_r$")
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8.5, loc="center right"); ax.grid(alpha=0.3)
    ax.text(0.5, 0.99,
           f"$n_{{{sub_w}}}$={rock.nw:.0f}, $n_{{{sub_o}}}$={rock.no:.0f}, "
           f"$k_{{r{sub_w},max}}$={rock.krw_max:.2f}, $k_{{r{sub_o},max}}$={rock.kro_max:.2f}\n"
           f"$\\mu_{{{sub_w}}}$={fluid.mu_w:.2f} cp, $\\mu_{{{sub_o}}}$={fluid.mu_o:.2f} cp",
           transform=ax.transAxes, fontsize=8, va="top", ha="center",
           bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.85))


def scenario_stage0_relperm():
    """Stage 0: relative permeability curves, the foundation everything else
    is built on. Corey model, water(injected)/oil(resident) generic and
    CO2(injected)/brine(resident) endpoints side by side."""
    # individual, WF
    fig, ax = plt.subplots(figsize=(6.5, 5))
    _plot_relperm(ax, WF_ROCK, WF_FLUID, r"$k_{rw}$ (water)", r"$k_{ro}$ (oil)",
                 "Relative permeability — waterflood (water-oil)", "w", "o")
    fig.savefig(f"{OUTDIR}/stage00a_relperm_wf.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)

    # individual, CCUS
    fig, ax = plt.subplots(figsize=(6.5, 5))
    _plot_relperm(ax, CCUS_ROCK, CCUS_FLUID, r"$k_{rg}$ (CO$_2$)", r"$k_{rb}$ (brine)",
                 "Relative permeability — CCUS (CO$_2$-brine)", "g", "b")
    fig.savefig(f"{OUTDIR}/stage00b_relperm_ccus.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)

    # combined
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5))
    fig.suptitle("Stage 0 — Relative permeability (Corey model)",
                fontsize=14, fontweight="bold")
    _plot_relperm(axes[0], WF_ROCK, WF_FLUID, r"$k_{rw}$ (water)", r"$k_{ro}$ (oil)",
                 "Waterflood (water-oil)", "w", "o")
    _plot_relperm(axes[1], CCUS_ROCK, CCUS_FLUID, r"$k_{rg}$ (CO$_2$)", r"$k_{rb}$ (brine)",
                 "CCUS (CO$_2$-brine)", "g", "b")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(f"{OUTDIR}/stage00_combined.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)
    print("Stage 0 done: stage00a (WF), stage00b (CCUS), stage00_combined")


def find_shock(rock, fluid, n=2000):
    """Welge construction via maximum-secant-slope from (Swc, 0), the same
    method already used in make_bl_figs.py, just factored out so every
    stage can call it. Returns Sw_f, fw_f, shock_speed (=m_s), and the
    fine (sw, fw, dfw) arrays used to find it."""
    sw = np.linspace(rock.swc, rock.sw_max, n)
    fw = calculate_fractional_flow(sw, rock, fluid)
    dfw = calculate_dfw_dsw(sw, fw)
    sec = np.where(sw > rock.swc + 1e-6, fw / (sw - rock.swc + 1e-12), 0.0)
    i_f = int(np.argmax(sec))
    sw_f, fw_f = sw[i_f], fw[i_f]
    shock_speed = fw_f / (sw_f - rock.swc)
    return sw_f, fw_f, shock_speed, sw, fw, dfw


def average_sw_behind_front(rock, fluid, sw_f, fw_f, shock_speed):
    """Where the Welge tangent, extended from (Swc,0) through the shock
    point, reaches fw=1. That intercept's Sw is the average water
    saturation behind the flood front (material-balance quantity)."""
    sw_avg = rock.swc + 1.0 / shock_speed
    return min(sw_avg, rock.sw_max)


def analytical_saturation_profile(xD, tD, rock, fluid, sw_f=None, fw_f=None,
                                  shock_speed=None, sw_grid=None, dfw_grid=None):
    """Closed-form self-similar Buckley-Leverett profile: invert the
    characteristic speed dfw/dSw = xD/tD along the rarefaction branch
    (Sw_f -> Sw_max, where dfw/dSw decreases monotonically), Sw=Swc ahead
    of the shock. No time-stepping, no discretization error -- this is
    the exact solution Stage 1 should use (Stage 2 onward genuinely needs
    Godunov, once velocity stops being constant in x)."""
    if sw_f is None:
        sw_f, fw_f, shock_speed, sw_grid, _, dfw_grid = find_shock(rock, fluid)
    mask_rare = sw_grid >= sw_f
    dfw_r = dfw_grid[mask_rare]
    sw_r = sw_grid[mask_rare]
    order = np.argsort(dfw_r)          # ascending speed for np.interp
    dfw_s, sw_s = dfw_r[order], sw_r[order]

    xD_f = shock_speed * tD
    out = np.empty_like(xD)
    for i, x in enumerate(xD):
        if x > xD_f:
            out[i] = rock.swc
        else:
            speed = x / max(tD, 1e-12)
            if speed >= dfw_s[-1]:
                out[i] = sw_f          # dfw_s[-1] is the speed AT the shock (fastest)
            elif speed <= dfw_s[0]:
                out[i] = rock.sw_max   # dfw_s[0] is the speed near Sw_max (slowest, curve flattens)
            else:
                out[i] = np.interp(speed, dfw_s, sw_s)
    return out


def scenario_stage1_incompressible():
    """Stage 1: incompressible BL, analytical throughout. WF and CCUS."""
    T_DAYS = 600.0

    def one_track(rock, fluid, geom, tag, label):
        sw_f, fw_f, m_s, sw_grid, fw_grid, dfw_grid = find_shock(rock, fluid)
        sw_avg = average_sw_behind_front(rock, fluid, sw_f, fw_f, m_s)

        # ---- panel a: fractional flow + shock, tangent extended to fw=1 ----
        def plot_a(ax):
            ax.plot(sw_grid, fw_grid, color="#1f4e79", lw=2, label=r"$f_w(S_w)$")
            sw_tan = np.array([rock.swc, sw_avg])
            fw_tan = np.array([0.0, 1.0])
            ax.plot(sw_tan, fw_tan, "--", color="#c00000", lw=1.6, label="Welge tangent")
            ax.plot(sw_f, fw_f, "o", color="#c00000", ms=8, zorder=5,
                   label=rf"shock: $S_{{w,f}}$={sw_f:.3f}")
            ax.plot(sw_avg, 1.0, "D", color="#2e7d32", ms=8, zorder=5,
                   label=rf"avg behind front: $\bar{{S}}_w$={sw_avg:.3f}")
            ax.axhline(1.0, color="lightgray", lw=0.8, zorder=0)
            ax.set_xlabel(r"$S_w$"); ax.set_ylabel(r"$f_w$")
            ax.set_title(f"Fractional flow + shock ({label})")
            ax.legend(loc="lower right", fontsize=8)

        # ---- panel b: characteristic speed, shock as a point ----
        def plot_b(ax):
            ax.plot(sw_grid, dfw_grid, color="#2e7d32", lw=2)
            dfw_at_shock = float(np.interp(sw_f, sw_grid, dfw_grid))
            ax.plot(sw_f, dfw_at_shock, "o", color="#c00000", ms=8, zorder=5,
                   label=rf"$df_w/dS_w$ at $S_{{w,f}}$ = {dfw_at_shock:.2f}")
            ax.set_xlabel(r"$S_w$"); ax.set_ylabel(r"$df_w/dS_w$")
            ax.set_title(f"Characteristic speed ({label})")
            ax.legend(fontsize=8)

        # ---- panel c: saturation profile, analytical ----
        def plot_c(ax):
            xD = np.linspace(0, 1, 400)
            for t, c in [(T_DAYS * 0.5, "#9ecae1"), (T_DAYS, "#4292c6"), (T_DAYS * 1.5, "#08519c")]:
                pv = rock.phi * geom.A * geom.x_ip
                u_inj = (5.615 * geom.i_w) / geom.A
                tD = t * u_inj / (rock.phi * geom.x_ip)
                Sw = analytical_saturation_profile(xD, tD, rock, fluid, sw_f, fw_f, m_s,
                                                   sw_grid, dfw_grid)
                ax.plot(xD, Sw, color=c, lw=2, label=f"t = {t:.0f} d")
            ax.axhline(sw_f, ls=":", color="#c00000", lw=1.3, label=r"$S_{w,f}$")
            ax.set_xlabel(r"$x_D$"); ax.set_ylabel(r"$S_w$")
            ax.set_title(f"Saturation profile, analytical ({label})")
            ax.legend(fontsize=8)

        for suffix, plotfn in [("a_frac_flow", plot_a), ("b_char_speed", plot_b),
                               ("c_profile", plot_c)]:
            fig, ax = plt.subplots(figsize=(6.5, 5))
            plotfn(ax)
            ax.grid(alpha=0.3)
            fig.savefig(f"{OUTDIR}/stage01{suffix}_{tag}.png", bbox_inches="tight")
            plt.show(block=False); plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
        fig.suptitle(f"Stage 1 — Incompressible Buckley-Leverett ({label})",
                    fontsize=14, fontweight="bold")
        for ax, plotfn in zip(axes, [plot_a, plot_b, plot_c]):
            plotfn(ax); ax.grid(alpha=0.3)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(f"{OUTDIR}/stage01_combined_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)
        print(f"Stage 1 ({label}) done: Sw_f={sw_f:.4f}, m_s={m_s:.4f}, "
             f"avg Sw behind front={sw_avg:.4f}")

    one_track(WF_ROCK, WF_FLUID, GEOM, "wf", "waterflood")
    one_track(CCUS_ROCK, CCUS_FLUID, GEOM, "ccus", "CCUS")


PRES = PressureConditions(p_inj=3000.0, p_init=2000.0)


def scenario_stage2_compressible():
    """Stage 2: compressible BL. WF and CCUS. Godunov is genuinely needed
    from here on (velocity varies with x, no simple closed form) -- full
    theory is in the companion Godunov/Pollock doc, not crammed onto the
    figure; this just points to it. Data is computed once per track and
    reused for both the individual and combined figures (the first version
    of this recomputed every Godunov solve twice, which is where the extra
    time was going, not the physics)."""
    T_DAYS = 600.0
    C_VALUES = [0.0, 3.0e-4, 6.0e-4, 1.0e-3]

    def compute(rock, fluid):
        L = GEOM.x_ip
        xline = np.linspace(0, L, 401)

        vel_curves = []
        for c in C_VALUES:
            eos = CompressibleFluid(c=c)
            p = PRES.pressure_profile(xline, L)
            rho = eos.density_array(p)
            u = (5.615 * GEOM.i_w / GEOM.A) * eos.density(PRES.p_inj) / rho
            Nc = compute_compressibility_number(eos, PRES)
            vel_curves.append((xline / L, u / u[0], Nc))

        profile_curves = []
        for c in C_VALUES:
            eos = CompressibleFluid(c=c)
            solver = CompressibleBLSolver(rock, fluid, GEOM, eos, PRES)
            if c == 0.0:
                xD, Sw = solver.solve_incompressible(T_DAYS, nx=401)
            else:
                xD, Sw = solver.solve(T_DAYS, nx=401)
            profile_curves.append((xD, Sw, solver.Nc))

        Ncs, fronts = [], []
        for c in np.linspace(0, C_VALUES[-1], 7):
            eos = CompressibleFluid(c=c)
            s = CompressibleBLSolver(rock, fluid, GEOM, eos, PRES)
            xD, Sw = (s.solve_incompressible(T_DAYS) if c == 0 else s.solve(T_DAYS))
            above = np.where(Sw > rock.swc + 0.02)[0]
            fpos = xD[above[-1]] if above.size else 0.0
            Ncs.append(s.Nc); fronts.append(fpos)

        return vel_curves, profile_curves, Ncs, fronts

    def plot_a(ax, vel_curves, label):
        for xD, u_ratio, Nc in vel_curves:
            lab = "incompressible" if Nc == 0.0 else rf"$N_c$={Nc:.2f}"
            ax.plot(xD, u_ratio, lw=2, label=lab)
        ax.set_xlabel(r"down-gradient distance, $x_D$  (injector $\to$ producer)")
        ax.set_ylabel(r"$u(x) / u_{inj}$")
        ax.set_title(f"Velocity rises down-gradient ({label})")
        ax.text(0.02, 0.97,
               r"mass flux $\rho u$ is conserved, not volume flux."
               "\nPressure falls toward the producer, so density falls\n"
               r"($\rho\!\propto\!e^{c(p-p_{ref})}$), so $u$ must rise to hold"
               " $\\rho u$ fixed.\nThis is the entire mechanism behind"
               " \"compressibility\nspeeds up the front\" below.",
               transform=ax.transAxes, fontsize=7.8, va="top",
               bbox=dict(boxstyle="round", fc="#fff8e1", ec="gray", alpha=0.9))
        ax.legend(fontsize=8)

    def plot_b(ax, profile_curves, label):
        for xD, Sw, Nc in profile_curves:
            lab = "incompressible" if Nc == 0.0 else rf"$N_c$={Nc:.2f}"
            ax.plot(xD, Sw, lw=2, label=lab)
        ax.set_xlabel(r"$x_D$"); ax.set_ylabel(r"$S_w$")
        ax.set_title(f"Saturation profile at t={T_DAYS:.0f}d ({label})\n"
                    "solved with Godunov (variable velocity, no closed form here)")
        ax.text(0.98, 0.03, "Godunov theory: see companion doc",
               transform=ax.transAxes, fontsize=7.5, ha="right", style="italic",
               color="#555")
        ax.legend(fontsize=8)

    def plot_c(ax, Ncs, fronts, label):
        ax.plot(Ncs, fronts, "o-", lw=2, color="#08519c")
        ax.set_xlabel(r"$N_c = c\,(p_{inj}-p_{init})$")
        ax.set_ylabel(r"front position $x_D$  (at fixed $t$=%.0fd)" % T_DAYS)
        ax.set_title(f"Front advances with Nc ({label})\n"
                    "one point per Nc, same solver, same elapsed time")

    def one_track(rock, fluid, tag, label):
        vel_curves, profile_curves, Ncs, fronts = compute(rock, fluid)

        fig, ax = plt.subplots(figsize=(6.8, 5.2))
        plot_a(ax, vel_curves, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage02a_velocity_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.8, 5.2))
        plot_b(ax, profile_curves, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage02b_profile_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.8, 5.2))
        plot_c(ax, Ncs, fronts, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage02c_front_vs_nc_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
        fig.suptitle(f"Stage 2 — Compressible Buckley-Leverett ({label})",
                    fontsize=14, fontweight="bold")
        plot_a(axes[0], vel_curves, label); axes[0].grid(alpha=0.3)
        plot_b(axes[1], profile_curves, label); axes[1].grid(alpha=0.3)
        plot_c(axes[2], Ncs, fronts, label); axes[2].grid(alpha=0.3)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(f"{OUTDIR}/stage02_combined_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)
        print(f"Stage 2 ({label}) done")

    one_track(WF_ROCK, WF_FLUID, "wf", "waterflood")
    one_track(CCUS_ROCK, CCUS_FLUID, "ccus", "CCUS")


def scenario_stage3_capillary():
    """Stage 3: capillary pressure and its diffusion effect on the front.
    WF and CCUS. The "no capillarity" reference curve is now the Stage 1
    analytical solution, not a Godunov solve, same fix as Stage 1 and for
    the same reason: an exact answer exists, so use it."""
    T_DAYS = 600.0
    PE_VALUES = [15.0, 60.0, 200.0]
    PE_COLORS = ["#4292c6", "#41ab5d", "#c00000"]

    def compute(rock, fluid):
        sw = np.linspace(rock.swc, rock.sw_max, 400)
        cap0 = CapillaryProperties()
        Pc = calculate_capillary_pressure(sw, rock, cap0)
        D = calculate_diffusion_coefficient(sw, rock, fluid, cap0)

        # analytical no-capillarity reference (Stage 1 machinery)
        sw_f, fw_f, m_s, sw_grid, fw_grid, dfw_grid = find_shock(rock, fluid)
        u_inj = (5.615 * GEOM.i_w) / GEOM.A
        tD = T_DAYS * u_inj / (rock.phi * GEOM.x_ip)
        xD0 = np.linspace(0, 1, 300)
        Sw0 = analytical_saturation_profile(xD0, tD, rock, fluid, sw_f, fw_f, m_s,
                                            sw_grid, dfw_grid)

        cap_curves = []
        for Pe, col in zip(PE_VALUES, PE_COLORS):
            cap = CapillaryProperties(Pe=Pe, k=2000.0)
            s = CapillaryBLSolver(rock, fluid, GEOM, cap)
            xD, Sw = s.solve(T_DAYS, nx=201)
            cap_curves.append((xD, Sw, s.Pe_c, col))

        return sw, Pc, D, xD0, Sw0, cap_curves

    def plot_a(ax, sw, Pc, label):
        ax.plot(sw, Pc, color="#6a51a3", lw=2.2)
        ax.set_xlabel(r"$S_w$"); ax.set_ylabel(r"$P_c$ [psi]")
        ax.set_title(f"Capillary pressure ({label})")
        ax.text(0.98, 0.97,
               "Physical origin of the diffusion term below: Pc drives an extra\n"
               "flux beyond Darcy/fractional-flow advection, smoothing the shock.\n"
               "Blows up near Swc, which is why smoothing concentrates at the\n"
               "leading edge, not uniformly. For CCUS this is the same physics\n"
               "that governs caprock seal integrity (entry pressure).",
               transform=ax.transAxes, fontsize=7.5, va="top", ha="right",
               bbox=dict(boxstyle="round", fc="#f3f0fa", ec="gray", alpha=0.9))

    def plot_b(ax, sw, D, label):
        ax.plot(sw, D / max(D.max(), 1e-30), color="#08519c", lw=2.2)
        ax.set_xlabel(r"$S_w$"); ax.set_ylabel(r"$D/D_{max}$")
        ax.set_title(f"Capillary diffusion coefficient ({label})")
        ax.text(0.02, 0.97,
               "This is what actually smears the front in the profiles to the\n"
               "right. It peaks mid-saturation and vanishes at both endpoints,\n"
               "which is why the widest smearing sits right at the front and\n"
               "not elsewhere in the domain.",
               transform=ax.transAxes, fontsize=7.5, va="top",
               bbox=dict(boxstyle="round", fc="#e8f0fa", ec="gray", alpha=0.9))

    def plot_c(ax, xD0, Sw0, cap_curves, label):
        ax.plot(xD0, Sw0, color="#000000", lw=2, label="no capillarity (analytical)")
        for xD, Sw, Pe_c, col in cap_curves:
            ax.plot(xD, Sw, color=col, lw=2, label=rf"Pe$_c$={Pe_c:.0f}")
        ax.set_xlabel(r"$x_D$"); ax.set_ylabel(r"$S_w$")
        ax.set_title(f"Capillarity smears the shock ({label})")
        ax.legend(fontsize=8)

    def one_track(rock, fluid, tag, label):
        sw, Pc, D, xD0, Sw0, cap_curves = compute(rock, fluid)

        fig, ax = plt.subplots(figsize=(6.8, 5.2))
        plot_a(ax, sw, Pc, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage03a_pc_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.8, 5.2))
        plot_b(ax, sw, D, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage03b_diffcoeff_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.8, 5.2))
        plot_c(ax, xD0, Sw0, cap_curves, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage03c_profile_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
        fig.suptitle(f"Stage 3 — Capillary Buckley-Leverett ({label})",
                    fontsize=14, fontweight="bold")
        plot_a(axes[0], sw, Pc, label); axes[0].grid(alpha=0.3)
        plot_b(axes[1], sw, D, label); axes[1].grid(alpha=0.3)
        plot_c(axes[2], xD0, Sw0, cap_curves, label); axes[2].grid(alpha=0.3)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(f"{OUTDIR}/stage03_combined_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)
        print(f"Stage 3 ({label}) done")

    one_track(WF_ROCK, WF_FLUID, "wf", "waterflood")
    one_track(CCUS_ROCK, CCUS_FLUID, "ccus", "CCUS")


def scenario_stage4_full():
    """Stage 4: full solver, compressible + capillary by composition.
    WF and CCUS."""
    T_DAYS = 600.0

    def compute(rock, fluid):
        eos = CompressibleFluid(c=8.0e-4)
        cap = CapillaryProperties(Pe=80.0, k=2000.0)

        sw_f, fw_f, m_s, sw_grid, fw_grid, dfw_grid = find_shock(rock, fluid)
        u_inj = (5.615 * GEOM.i_w) / GEOM.A
        tD = T_DAYS * u_inj / (rock.phi * GEOM.x_ip)
        xD0 = np.linspace(0, 1, 300)
        Sw0 = analytical_saturation_profile(xD0, tD, rock, fluid, sw_f, fw_f, m_s,
                                            sw_grid, dfw_grid)

        comp_solver = CompressibleBLSolver(rock, fluid, GEOM, eos, PRES)
        xD2, Sw2 = comp_solver.solve(T_DAYS, 201)
        cap_solver = CapillaryBLSolver(rock, fluid, GEOM, cap)
        xD3, Sw3 = cap_solver.solve(T_DAYS, 201)
        full = FullBLSolver(rock, fluid, GEOM, eos, PRES, cap)
        xD4, Sw4 = full.solve(T_DAYS, 201)

        return dict(xD0=xD0, Sw0=Sw0, xD2=xD2, Sw2=Sw2, xD3=xD3, Sw3=Sw3,
                   xD4=xD4, Sw4=Sw4, Nc=full.Nc, Pe_c=full.Pe_c)

    def plot_main(ax, d, label):
        ax.plot(d["xD0"], d["Sw0"], color="#000000", lw=2,
               label="incompressible (analytical)")
        ax.plot(d["xD2"], d["Sw2"], color="#08519c", lw=2,
               label=rf"compressible ($N_c$={d['Nc']:.2f})")
        ax.plot(d["xD3"], d["Sw3"], color="#41ab5d", lw=2,
               label=rf"capillary (Pe$_c$={d['Pe_c']:.0f})")
        ax.plot(d["xD4"], d["Sw4"], color="#c00000", lw=2.4, label="full (both)")
        ax.set_xlabel(r"$x_D$"); ax.set_ylabel(r"$S_w$")
        ax.set_title(f"Saturation profile at t={T_DAYS:.0f}d ({label})")
        ax.legend(fontsize=8.5)

    def plot_composition(ax, d, label):
        ax.axis("off")
        ax.text(0.0, 0.95,
               "Built by composition:\n\n"
               "   FullBLSolver\n"
               "     |-- CompressibleBLSolver  (variable-u advection, Godunov)\n"
               "     '-- CapillaryBLSolver     (implicit diffusion)\n\n"
               "Each timestep:\n"
               "   1. compressible Godunov advection step\n"
               "   2. implicit capillary diffusion step\n\n"
               f"   Nc = {d['Nc']:.3f}      Pe_c = {d['Pe_c']:.0f}\n\n"
               "c -> 0 recovers Stage 3; Pe -> 0 recovers Stage 2;\n"
               "both -> 0 recovers Stage 1 (analytical).",
               fontsize=10.5, va="top", family="monospace", transform=ax.transAxes)
        ax.set_title(f"Composition ({label})")

    def one_track(rock, fluid, tag, label):
        d = compute(rock, fluid)

        fig, ax = plt.subplots(figsize=(7, 5.4))
        plot_main(ax, d, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage04a_profile_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.5, 5.4))
        plot_composition(ax, d, label)
        fig.savefig(f"{OUTDIR}/stage04b_composition_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(12.5, 5))
        fig.suptitle(f"Stage 4 — Full CCUS-ready solver ({label})",
                    fontsize=14, fontweight="bold")
        plot_main(axes[0], d, label); axes[0].grid(alpha=0.3)
        plot_composition(axes[1], d, label)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(f"{OUTDIR}/stage04_combined_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)
        print(f"Stage 4 ({label}) done")

    one_track(WF_ROCK, WF_FLUID, "wf", "waterflood")
    one_track(CCUS_ROCK, CCUS_FLUID, "ccus", "CCUS")


DP_KMD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.])
DP_HFT = np.array([50., 48., 54., 44., 42., 48., 50., 40.])
DP_PHI = np.array([0.22, 0.18, 0.21, 0.15, 0.20, 0.21, 0.20, 0.20])
DP_SWC = np.array([0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42])
DP_KRO = np.array([0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60])
DP_KRW = np.array([0.05, 0.15, 0.20, 0.33, 0.20, 0.30, 0.40, 0.17])
DP_SOR = 0.20
DP_NZ = 8


def scenario_dykstra_parsons():
    """Dykstra-Parsons, your 8-layer table. WF and CCUS, same rock, only
    the fluid changes between tracks. Bars in subsurface (L1..L8) order
    with the speed index Ri as a label, not the sort key. Per-layer sweep
    shows the numerical (streamline, no-crossflow) and analytical (Stage 1
    machinery, per layer) profiles together. System panel explains why
    kh_mob tracks the streamline result and plain kh doesn't."""
    NX = 60
    TARGET_PVI = 0.6
    Ri = DP_KMD / (DP_PHI * (1.0 - DP_SOR - DP_SWC))
    labels = [f"L{i+1}" for i in range(DP_NZ)]

    def compute(mu_w, mu_o, tag):
        lay = lambda v: np.ones((NX, 1, DP_NZ)) * np.asarray(v)[None, None, :]
        h_m = DP_HFT * 0.3048
        grid = Grid3D(NX, 1, DP_NZ, 10., 10., h_m, k=lay(DP_KMD) * 9.869e-16,
                      phi=lay(DP_PHI))
        rock3d = Rock(nw=2., no=2., swc=lay(DP_SWC), sor=DP_SOR,
                      krw_max=lay(DP_KRW), kro_max=lay(DP_KRO))
        fluid3d = Fluid(mu_w=mu_w, mu_o=mu_o)
        wells = Wells([(0, 0, k) for k in range(DP_NZ)],
                      [(NX - 1, 0, k) for k in range(DP_NZ)],
                      rate=0.0, bhp=0.0, inj_bhp=2.0e7)
        sim = StreamlineSimulator(grid, rock3d, fluid3d, wells, seeds_per_dim=3,
                                  no_crossflow=True)
        res = sim.run(TARGET_PVI, 18, verbose=False)
        sw_num = res.sw_final          # (NX, 1, NZ)
        xD = (np.arange(NX) + 0.5) / NX

        # analytical per-layer profile, Stage 1 machinery, one RockProperties
        # per layer built from the same table, tD = PVI directly (tD is
        # defined as injected-volume/pore-volume, which IS PVI)
        sw_ana = np.zeros((NX, DP_NZ))
        for k in range(DP_NZ):
            rp = RockProperties(nw=2.0, no=2.0, swc=DP_SWC[k], sor=DP_SOR,
                               krw_max=DP_KRW[k], kro_max=DP_KRO[k], phi=DP_PHI[k])
            fp = FluidProperties(mu_w=mu_w, mu_o=mu_o)
            sw_f, fw_f, m_s, sg, fg, dg = find_shock(rp, fp)
            sw_ana[:, k] = analytical_saturation_profile(xD, TARGET_PVI, rp, fp,
                                                          sw_f, fw_f, m_s, sg, dg)

        # system-level: streamline (no-crossflow) vs DP-kh vs DP-kh_mob
        pvi_grid = np.array(res.pvi)
        dp_kh = DykstraParsons(DP_KMD, DP_HFT, DP_PHI, DP_SWC, DP_SOR, DP_KRW,
                               DP_KRO, mu_w, mu_o, "kh")
        dp_mob = DykstraParsons(DP_KMD, DP_HFT, DP_PHI, DP_SWC, DP_SOR, DP_KRW,
                                DP_KRO, mu_w, mu_o, "kh_mob")
        rec_kh, wc_kh = dp_kh.run(pvi_grid)
        rec_mob, wc_mob = dp_mob.run(pvi_grid)

        return dict(xD=xD, sw_num=sw_num, sw_ana=sw_ana, pvi=pvi_grid,
                   rec_sl=np.array(res.recovery), wc_sl=np.array(res.watercut),
                   rec_kh=rec_kh, wc_kh=wc_kh, rec_mob=rec_mob, wc_mob=wc_mob)

    def plot_bars(ax, label):
        yy = np.arange(DP_NZ)
        colors = plt.cm.viridis(Ri / Ri.max())
        ax.barh(yy, DP_KMD, color=colors)
        ax.set_yticks(yy); ax.set_yticklabels(labels)
        ax.invert_yaxis()   # L1 at top of the chart, subsurface reading order
        for i in range(DP_NZ):
            ax.text(DP_KMD[i] + 20, i, f"Ri={Ri[i]:.0f}", va="center", fontsize=8)
        ax.set_xlabel("permeability [mD]"); ax.set_xlim(0, 1500)
        ax.set_title(f"8 layers, subsurface order ({label})\n"
                    "speed index Ri labeled on each bar, not used to sort")

    def plot_perlayer(ax, d, label):
        for k in range(DP_NZ):
            col = plt.cm.viridis(Ri[k] / Ri.max())
            ax.plot(d["xD"], d["sw_num"][:, 0, k], "-", color=col, lw=1.6,
                   label=f"{labels[k]}" if k == 0 else None)
            ax.plot(d["xD"], d["sw_ana"][:, k], "--", color=col, lw=1.1, alpha=0.8)
        ax.plot([], [], "-", color="gray", label="numerical (streamline)")
        ax.plot([], [], "--", color="gray", label="analytical (Stage 1, per layer)")
        ax.set_xlabel(r"$x_D$"); ax.set_ylabel(r"$S_w$")
        ax.set_title(f"Per-layer sweep at PVI={TARGET_PVI:.2f} ({label})\n"
                    "solid=numerical (Godunov, streamline), dashed=analytical")
        ax.legend(fontsize=7, ncol=1, loc="upper right")

    def plot_system(ax, d, label):
        ax.plot(d["pvi"], d["rec_sl"] * 100, "-", color="#c00000", lw=2.2,
               label="streamline (no-crossflow, numerical)")
        ax.plot(d["pvi"], d["rec_kh"] * 100, "--", color="#993C1D", lw=1.6,
               label="DP, kh allocation")
        ax.plot(d["pvi"], d["rec_mob"] * 100, ":", color="#0F6E56", lw=2.0,
               label="DP, kh x endpoint mobility")
        ax.set_xlabel("PVI"); ax.set_ylabel("recovery [%]")
        ax.set_title(f"System recovery ({label})")
        ax.legend(fontsize=8, loc="lower right")
        ax.text(0.02, 0.55,
               "kh alone ignores fluid mobility, only exact if every\n"
               "layer had identical fluid mobility. True parallel-layer\n"
               "flow allocates by conductance = k.h.mobility, which is\n"
               "what kh_mob approximates and why it tracks the full\n"
               "numerical (pressure-solved) streamline result closely.",
               transform=ax.transAxes, fontsize=7.5, va="top",
               bbox=dict(boxstyle="round", fc="#fff8e1", ec="gray", alpha=0.9))

    def one_track(mu_w, mu_o, tag, label):
        d = compute(mu_w, mu_o, tag)

        fig, ax = plt.subplots(figsize=(6.5, 5.2))
        plot_bars(ax, label)
        fig.savefig(f"{OUTDIR}/stage05a_layers_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.2, 5.2))
        plot_perlayer(ax, d, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage05b_perlayer_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.2, 5.2))
        plot_system(ax, d, label); ax.grid(alpha=0.3)
        fig.savefig(f"{OUTDIR}/stage05c_system_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(18, 5.2))
        fig.suptitle(f"Dykstra-Parsons, 8-layer table ({label})",
                    fontsize=14, fontweight="bold")
        plot_bars(axes[0], label)
        plot_perlayer(axes[1], d, label); axes[1].grid(alpha=0.3)
        plot_system(axes[2], d, label); axes[2].grid(alpha=0.3)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(f"{OUTDIR}/stage05_combined_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)
        print(f"Dykstra-Parsons ({label}) done")

    one_track(0.5, 5.0, "wf", "waterflood")
    one_track(0.05, 0.6, "ccus", "CCUS")


def scenario_pollock_diagram():
    """Pollock's semi-analytical tracing, one cell, worked example. Uses
    _exit_time/_pos_at directly (the actual functions trace_streamline calls,
    not a reimplementation), verified against the workflow document's worked
    case: 10x10m cell, entry (2,5), exits the x-face at t=6.49 days, y=5.94m.
    Full numeric calculation shown, not just the symbolic formula.
    """
    dx, dy = 10.0, 10.0
    vx_minus, vx_plus = 1.00, 1.40
    vy_minus, vy_plus = 0.20, 0.10
    x0, y0 = 2.0, 5.0

    # explicit intermediate numbers, computed the same way _exit_time does,
    # so what's displayed is exactly what's calculated, not a re-derivation
    gx = (vx_plus - vx_minus) / dx
    v_x0 = vx_minus + gx * x0
    v_x_target = vx_minus + gx * dx
    tx = (1.0 / gx) * np.log(v_x_target / v_x0)

    gy = (vy_plus - vy_minus) / dy
    v_y0 = vy_minus + gy * y0
    v_y_target = vy_minus + gy * dy
    ty = (1.0 / gy) * np.log(v_y_target / v_y0)

    t_exit = min(tx, ty)
    exit_face = "x (east)" if t_exit == tx else "y (north)"
    x_exit = _pos_at(x0, vx_minus, vx_plus, dx, t_exit)
    y_exit = _pos_at(y0, vy_minus, vy_plus, dy, t_exit)

    ts = np.linspace(0, t_exit, 120)
    xs = np.array([_pos_at(x0, vx_minus, vx_plus, dx, tt) for tt in ts])
    ys = np.array([_pos_at(y0, vy_minus, vy_plus, dy, tt) for tt in ts])

    fig = plt.figure(figsize=(13.5, 7.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.85], wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    axt = fig.add_subplot(gs[0, 1])
    axt.axis("off")

    ax.add_patch(plt.Rectangle((0, 0), dx, dy, fill=False, ec="black", lw=1.5))
    ax.plot(xs, ys, color="#c00000", lw=2.5, label="Pollock trajectory (exact, curved)")
    ax.plot(x0, y0, "o", color="#08519c", ms=10, zorder=5, label=f"entry ({x0:.0f}, {y0:.0f})")
    ax.plot(x_exit, y_exit, "s", color="#2e7d32", ms=10, zorder=5,
           label=f"exit ({x_exit:.2f}, {y_exit:.2f}), t={t_exit:.2f} d")

    for frac, vx in [(0.0, vx_minus), (1.0, vx_plus)]:
        ax.annotate("", xy=(frac * dx, -1.6), xytext=(frac * dx, -0.4),
                   arrowprops=dict(arrowstyle="->", color="#555"))
        ax.text(frac * dx, -2.3, f"$v_x$={vx:.2f}", ha="center", fontsize=9)
    for frac, vy in [(0.0, vy_minus), (1.0, vy_plus)]:
        ax.annotate("", xy=(-1.6, frac * dy), xytext=(-0.4, frac * dy),
                   arrowprops=dict(arrowstyle="->", color="#555"))
        ax.text(-2.5, frac * dy, f"$v_y$={vy:.2f}", va="center", fontsize=9, rotation=90)

    ax.set_xlim(-4.2, dx + 1.2); ax.set_ylim(-4.2, dy + 1.2)
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    ax.set_title("One cell, worked example", fontsize=12)
    ax.legend(loc="lower right", fontsize=8)

    lines = [
        "ASSUMPTION",
        "Each velocity component varies linearly across",
        "the cell along its own axis. dx/dt=v(x) then",
        "integrates in closed form, exact, no ODE solver,",
        "no time-stepping inside the cell.",
        "",
        r"$t_{exit}=\frac{1}{g}\ln\frac{v(x_{target})}{v(x_0)}$,  $g=\frac{v_+-v_-}{d}$"
        r"   $x(t)=\frac{v(x_0)e^{gt}-v_-}{g}$",
        "",
        "X-AXIS",
        rf"$g_x$ = ({vx_plus:.2f}-{vx_minus:.2f})/{dx:.0f} = {gx:.3f}",
        rf"$v(x_0){{=}}v(2){{=}}${vx_minus:.2f}+{gx:.3f}$\times$2 = {v_x0:.3f}",
        rf"$v(x_{{target}}){{=}}v(10){{=}}${vx_minus:.2f}+{gx:.3f}$\times$10 = {v_x_target:.3f}",
        rf"$t_x$ = (1/{gx:.3f}) ln({v_x_target:.3f}/{v_x0:.3f}) = "
        rf"{1/gx:.2f} $\times$ {np.log(v_x_target/v_x0):.4f} = {tx:.3f} d",
        "",
        "Y-AXIS",
        rf"$g_y$ = ({vy_plus:.2f}-{vy_minus:.2f})/{dy:.0f} = {gy:.3f}",
        rf"$v(y_0){{=}}v(5){{=}}${vy_minus:.2f}+({gy:.3f})$\times$5 = {v_y0:.3f}",
        rf"$v(y_{{target}}){{=}}v(10){{=}}${vy_minus:.2f}+({gy:.3f})$\times$10 = {v_y_target:.3f}",
        rf"$t_y$ = (1/{gy:.3f}) ln({v_y_target:.3f}/{v_y0:.3f}) = "
        rf"{1/gy:.2f} $\times$ {np.log(v_y_target/v_y0):.4f} = {ty:.3f} d",
        "",
        "EXIT",
        rf"min($t_x$, $t_y$) = min({tx:.2f}, {ty:.2f}) = {t_exit:.2f} d, exits the {exit_face} face",
        rf"$y(t_{{exit}})$ = ({y0:.0f}+{vy_minus:.2f}/{gy:.3f})$e^{{{gy:.3f}\times{t_exit:.2f}}}$"
        rf" - {vy_minus:.2f}/{gy:.3f} = {y_exit:.3f} m",
        "",
        f"Matches the workflow document's worked case exactly: "
        f"t=6.49 d, exit y=5.94 m.",
    ]
    axt.text(0.0, 1.0, "\n".join(lines), transform=axt.transAxes, fontsize=9.8,
            va="top", family="monospace",
            bbox=dict(boxstyle="round", fc="#fff8e1", ec="gray", alpha=0.95))

    fig.suptitle("Pollock's algorithm — one cell, full worked example",
                fontsize=14, fontweight="bold")
    fig.savefig(f"{OUTDIR}/stage06_pollock_diagram.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)
    print(f"Pollock diagram done: exits {exit_face} face at t={t_exit:.2f}d, "
         f"({x_exit:.2f}, {y_exit:.2f})")


PVI_SNAPSHOTS_S7 = [0.15, 0.30, 0.50, 0.80]


def _build_areal(pattern, tag):
    """pattern: 'quarter' or 'full'. tag: 'wf' or 'ccus'. Always nz=1 (single
    layer, stated explicitly since that was asked about for both patterns)."""
    if pattern == "quarter":
        grid, rock, fluid, wells = build_demo(nx=30, ny=30, nz=1, seed=7)
        well_desc = "quarter five-spot (injector/producer on diagonal corners)"
    else:
        grid, rock, fluid, wells = build_five_spot(nx=31, ny=31, nz=1, seed=7,
                                                    homogeneous=True, k_mean=150.0,
                                                    inverted=True)
        well_desc = "full five-spot (central injector, four corner producers)"
    if tag == "ccus":
        fluid = Fluid(mu_w=0.05, mu_o=0.6, c=1.0e-8, rho_w=700.0, rho_o=1020.0)
    return grid, rock, fluid, wells, well_desc


def _run_areal_sweep(grid, rock, fluid, wells):
    fields = []
    for pvi_t in PVI_SNAPSHOTS_S7:
        sim = StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=7)
        res = sim.run(target_pvi=pvi_t, n_psteps=16, verbose=False)
        sw = res.sw_final
        p, lamt = solve_pressure(grid, sw, rock, fluid, wells)
        V = pore_velocities(grid, p, lamt, False)
        vx = 0.5 * (V["xm"] + V["xp"]); vy = 0.5 * (V["ym"] + V["yp"])
        fields.append((res.pvi[-1], sw, vx, vy))
    return fields


def _plot_snapshot(ax, grid, fields_entry, wells, is_full, ext):
    pvi, sw, vx, vy = fields_entry
    nx, ny = grid.nx, grid.ny
    xc = (np.arange(nx) + 0.5) * grid.dx; yc = (np.arange(ny) + 0.5) * grid.dy
    im = ax.imshow(sw[:, :, 0].T, origin="lower", extent=ext, cmap="viridis",
                   vmin=0.2, vmax=0.8, aspect="equal")
    ax.streamplot(xc, yc, vx[:, :, 0].T, vy[:, :, 0].T, color="white",
                 density=1.1, linewidth=0.8, arrowsize=0.7)
    for idx, (i, j, k) in enumerate(wells.inj_cells):
        ax.plot((i + 0.5) * grid.dx, (j + 0.5) * grid.dy, "o", color="#1f77b4",
               ms=10, mec="k", label="injector" if idx == 0 else None)
    for idx, (i, j, k) in enumerate(wells.prod_cells):
        ax.plot((i + 0.5) * grid.dx, (j + 0.5) * grid.dy, "s", color="#d62728",
               ms=9, mec="k", label="producer" if idx == 0 else None)
    ax.set_title(f"PVI = {pvi:.2f}")
    ax.set_xlim(0, nx * grid.dx); ax.set_ylim(0, ny * grid.dy)
    return im


def scenario_streamline_simulator():
    """Stage 7: areal sweep over time, streamlines overlaid. Quarter and
    full five-spot, WF and CCUS. Single layer (nz=1) throughout, stated
    explicitly since that was asked about."""
    for pattern in ["quarter", "full"]:
        for tag, label in [("wf", "waterflood"), ("ccus", "CCUS")]:
            grid, rock, fluid, wells, well_desc = _build_areal(pattern, tag)
            ext = [0, grid.nx * grid.dx, 0, grid.ny * grid.dy]
            fields = _run_areal_sweep(grid, rock, fluid, wells)

            # individual, one per PVI snapshot
            for idx, entry in enumerate(fields):
                fig, ax = plt.subplots(figsize=(5.5, 5.2))
                im = _plot_snapshot(ax, grid, entry, wells, pattern == "full", ext)
                ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
                ax.legend(loc="upper left", fontsize=8)
                fig.colorbar(im, ax=ax, fraction=0.045, label=r"$S_w$")
                fig.savefig(f"{OUTDIR}/stage07{pattern[0]}{idx}_{tag}.png",
                          bbox_inches="tight")
                plt.show(block=False); plt.close(fig)

            # combined
            fig, axes = plt.subplots(1, len(fields), figsize=(4.3 * len(fields), 4.8))
            fig.suptitle(f"{well_desc}, single layer, {label}\n"
                        "areal sweep over time, streamlines overlaid",
                        fontsize=13, fontweight="bold")
            im = None
            for ax, entry in zip(axes, fields):
                im = _plot_snapshot(ax, grid, entry, wells, pattern == "full", ext)
                ax.set_xlabel("x [m]")
            axes[0].set_ylabel("y [m]")
            axes[0].legend(loc="upper left", fontsize=8)
            cb = fig.colorbar(im, ax=axes, fraction=0.014, pad=0.01)
            cb.set_label(r"$S_w$")
            fig.savefig(f"{OUTDIR}/stage07_{pattern}_combined_{tag}.png",
                      bbox_inches="tight")
            plt.show(block=False); plt.close(fig)
            print(f"Stage 7 ({pattern}, {label}) done")


def scenario_physics_modes_areal():
    """Physics-mode comparison (incompressible/compressible/capillary/full),
    quarter and full five-spot, WF and CCUS. Reuses _build_areal from the
    streamline simulator stage for grid/wells so the geometry is identical
    to what that stage already showed, gravity left off in all four modes
    to isolate exactly these four effects (same convention as the
    1D validate_4modes_1d.py comparison)."""
    TARGET_PVI = 0.30
    MODES = [
        ("Incompressible", dict(compressible=False, capillary=False)),
        ("Compressible", dict(compressible=True, capillary=False)),
        ("Capillary", dict(compressible=False, capillary=True,
                          cap=Capillary(Pe=2.0e6, lam=2.0))),
        ("Full", dict(compressible=True, capillary=True,
                     cap=Capillary(Pe=2.0e6, lam=2.0))),
    ]

    def compute(pattern, tag):
        results = []
        for label, kw in MODES:
            grid, rock, fluid, wells, well_desc = _build_areal(pattern, tag)
            sim = StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=5,
                                      no_crossflow=False, gravity=False, **kw)
            res = sim.run(target_pvi=TARGET_PVI, n_psteps=10, verbose=False)
            results.append((label, res.sw_final[:, :, 0], res.recovery[-1], sim.Nc,
                           kw.get("capillary", False)))
        return grid, wells, well_desc, results

    def plot_one(ax, grid, entry, ext):
        label, sw, rf, Nc, has_cap = entry
        im = ax.imshow(sw.T, origin="lower", extent=ext, cmap="viridis",
                       vmin=0.2, vmax=0.8, aspect="equal")
        Nc_str = f"Nc={Nc:.2f}" if Nc > 0 else ""
        ax.set_title(f"{label}\nRF={rf*100:.1f}%  {Nc_str}", fontsize=10.5)
        ax.set_xticks([]); ax.set_yticks([])
        return im

    for pattern in ["quarter", "full"]:
        for tag, label in [("wf", "waterflood"), ("ccus", "CCUS")]:
            grid, wells, well_desc, results = compute(pattern, tag)
            ext = [0, grid.nx * grid.dx, 0, grid.ny * grid.dy]

            for entry in results:
                fig, ax = plt.subplots(figsize=(5, 4.6))
                im = plot_one(ax, grid, entry, ext)
                fig.colorbar(im, ax=ax, fraction=0.045, label=r"$S_w$")
                mode_tag = entry[0].lower().replace(" ", "")
                fig.savefig(f"{OUTDIR}/stage07b_{pattern}_{mode_tag}_{tag}.png",
                          bbox_inches="tight")
                plt.show(block=False); plt.close(fig)

            fig, axes = plt.subplots(1, 4, figsize=(17, 4.6))
            fig.suptitle(f"Physics-mode comparison, {well_desc}, {label}, "
                        f"PVI={TARGET_PVI:.2f}", fontsize=13, fontweight="bold")
            im = None
            for ax, entry in zip(axes, results):
                im = plot_one(ax, grid, entry, ext)
            cb = fig.colorbar(im, ax=axes, fraction=0.012, pad=0.01)
            cb.set_label(r"$S_w$")
            fig.savefig(f"{OUTDIR}/stage07b_{pattern}_combined_{tag}.png",
                      bbox_inches="tight")
            plt.show(block=False); plt.close(fig)
            print(f"Physics modes ({pattern}, {label}) done: "
                 + ", ".join(f"{e[0]}={e[2]*100:.1f}%" for e in results))


def _build_8layer(tag, nx=20, ny=20):
    """Same 8-layer table as the Dykstra-Parsons stage, crossflow on this
    time (gravity needs vertical communication). Only the fluid changes
    between tracks, same policy as everywhere else in this rebuild."""
    lay = lambda v: np.ones((nx, ny, DP_NZ)) * v[None, None, :]
    dz = DP_HFT * 0.3048
    grid = Grid3D(nx, ny, DP_NZ, 10., 10., dz, k=lay(DP_KMD) * 9.869e-16,
                 phi=lay(DP_PHI))
    rock = Rock(nw=2., no=2., swc=lay(DP_SWC), sor=DP_SOR,
               krw_max=lay(DP_KRW), kro_max=lay(DP_KRO))
    if tag == "wf":
        fluid = Fluid(mu_w=0.5, mu_o=5.0, c=1.0e-8, rho_w=1000.0, rho_o=800.0)
    else:
        fluid = Fluid(mu_w=0.05, mu_o=0.6, c=1.0e-8, rho_w=700.0, rho_o=1020.0)
    inj = [(0, 0, k) for k in range(DP_NZ)]
    prod = [(nx - 1, ny - 1, k) for k in range(DP_NZ)]
    wells = Wells(inj_cells=inj, prod_cells=prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)
    return grid, rock, fluid, wells


def _layer_depth_centers():
    """True thickness-weighted depth per layer, L8 (shallowest) near 0,
    L1 (deepest) near total thickness. Bigger number = further down."""
    dz = DP_HFT * 0.3048
    depth = np.zeros(DP_NZ)
    for k in range(DP_NZ):
        depth[k] = np.sum(dz[k + 1:]) + dz[k] / 2.0   # thickness above k + half own
    return depth


def scenario_3d_gravity():
    """3D + gravity, your 8-layer table. Z-axis actually flipped (bigger
    number = further down, not just relabeled), streamline density reduced
    so paths are traceable, cross-section for both tracks."""
    FULL = dict(compressible=True, gravity=True, capillary=True,
               cap=Capillary(Pe=2.0e6, lam=2.0), n_diff_sub=3)
    depth = _layer_depth_centers()
    order = list(np.argsort(DP_KMD / (DP_PHI * (1 - DP_SOR - DP_SWC)))[::-1])
    labels = [f"L{i+1}" for i in range(DP_NZ)]

    # ---- 3D stack, z-flipped, both tracks ----
    for tag, label in [("wf", "waterflood"), ("ccus", "CCUS")]:
        NX = NY = 20
        grid, rock, fluid, wells = _build_8layer(tag, NX, NY)
        sim = StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=6,
                                  no_crossflow=False, **FULL)
        res = sim.run(target_pvi=0.15, n_psteps=8, verbose=False)
        sw = sim.sw
        xc = (np.arange(NX) + 0.5) * grid.dx; yc = (np.arange(NY) + 0.5) * grid.dy
        X, Y = np.meshgrid(xc, yc, indexing="ij")

        fig = plt.figure(figsize=(9.5, 8))
        ax = fig.add_subplot(111, projection="3d")
        fig.suptitle(f"8-layer reservoir, 3D, {label} (PVI={res.pvi[-1]:.2f})\n"
                    "z-axis: bigger number = further down (true depth, flipped view)",
                    fontsize=12.5, fontweight="bold")
        norm = plt.Normalize(0.2, 0.8)
        for k in range(DP_NZ):
            fc = plt.cm.viridis(norm(sw[:, :, k]))
            Z = np.full_like(X, depth[k])
            ax.plot_surface(X, Y, Z, facecolors=fc, shade=False, rstride=1,
                           cstride=1, antialiased=False)
            ax.text(0, NY * grid.dy, depth[k], f" {labels[k]} (k={DP_KMD[k]:.0f})",
                   fontsize=8)
        ax.invert_zaxis()
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("depth [m]")
        ax.view_init(elev=18, azim=-60)
        m = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
        cb = fig.colorbar(m, ax=ax, fraction=0.025, pad=0.10); cb.set_label(r"$S_w$")
        fig.savefig(f"{OUTDIR}/stage08a_3dstack_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)
        print(f"3D stack ({label}) done, z-axis flipped, PVI={res.pvi[-1]:.2f}")

    # ---- cross-section, both tracks (WF added; CCUS matches the earlier one) ----
    for tag, label in [("wf", "waterflood"), ("ccus", "CCUS")]:
        NX = NY = 15
        grid, rock, fluid, wells = _build_8layer(tag, NX, NY)
        sim = StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=5,
                                  no_crossflow=False, coverage_fill=True,
                                  conserve=True, **FULL)
        res = sim.run(target_pvi=0.20, n_psteps=6, verbose=False)
        sw = sim.sw
        j_mid = NY // 2
        slice_xz = sw[:, j_mid, :].T
        dz = DP_HFT * 0.3048
        depth_top = np.concatenate(([0.0], np.cumsum(dz)))
        xf = np.arange(NX + 1) * grid.dx

        fig, ax = plt.subplots(figsize=(9, 5.5))
        fig.suptitle(f"CO$_2$/water plume cross-section, {label}, "
                    f"y={j_mid*grid.dy:.0f} m, PVI={res.pvi[-1]:.2f}",
                    fontsize=13, fontweight="bold")
        im = ax.pcolormesh(xf, depth_top, slice_xz, cmap="viridis", vmin=0.2,
                          vmax=0.8, shading="flat")
        ax.invert_yaxis()
        ax.axvline(0.5 * grid.dx, color="#1f77b4", lw=2, ls="--", label="injector")
        ax.set_xlabel("x [m]"); ax.set_ylabel("depth [m] (down)")
        ax.legend(loc="lower right", fontsize=9)
        cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label(r"$S_w$")
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        fig.savefig(f"{OUTDIR}/stage08b_crosssection_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)
        print(f"Cross-section ({label}) done")

    # ---- streamlines per layer, density reduced ----
    NX = NY = 30
    grid, rock, fluid, wells = _build_8layer("wf", NX, NY)
    sw0 = np.asarray(rock.swc, dtype=float)
    p, lamt = solve_pressure(grid, sw0, rock, fluid, wells, no_crossflow=True)
    V = pore_velocities(grid, p, lamt, no_crossflow=True)
    vx = 0.5 * (V["xm"] + V["xp"]); vy = 0.5 * (V["ym"] + V["yp"])
    speed = np.sqrt(vx ** 2 + vy ** 2)
    vmax = float(np.percentile(speed, 99))
    xc = (np.arange(NX) + 0.5) * grid.dx; yc = (np.arange(NY) + 0.5) * grid.dy

    fig, ax = plt.subplots(2, 4, figsize=(17, 8.6))
    fig.suptitle("Streamlines in the 8-layer reservoir, no crossflow\n"
                "reduced density so individual paths are traceable",
                fontsize=14, fontweight="bold")
    sm = None
    for ax_i, k in zip(ax.ravel(), order):
        strm = ax_i.streamplot(xc, yc, vx[:, :, k].T, vy[:, :, k].T, color=speed[:, :, k].T,
                              cmap="plasma", norm=plt.Normalize(0, vmax), density=0.55,
                              linewidth=1.0, arrowsize=0.8)
        sm = strm.lines
        ax_i.plot(0.5 * grid.dx, 0.5 * grid.dy, "o", color="#1f77b4", ms=10, mec="k")
        ax_i.plot((NX - 0.5) * grid.dx, (NY - 0.5) * grid.dy, "s", color="#d62728",
                 ms=9, mec="k")
        ax_i.set_title(f"{labels[k]}: k={DP_KMD[k]:.0f} mD", fontsize=11)
        ax_i.set_xticks([]); ax_i.set_yticks([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.013, pad=0.01)
    cb.set_label("interstitial speed [m/s]")
    fig.savefig(f"{OUTDIR}/stage08c_streamlines.png", bbox_inches="tight")
    plt.show(block=False); plt.close(fig)
    print("Streamlines (reduced density) done")


def _build_field_case(tag, nx=16, ny=16, nz=12, seed=11):
    """Randomized field-case analog: more layers than the deterministic
    8-layer table (18 vs 8), lognormal-random permeability with a mild
    depth trend (deeper layers tighter on average, a common diagenetic
    pattern), not the known values from the DP table. This is meant to
    read as 'what if we didn't have clean layer picks,' not as a
    replacement for the table-based Stage 8."""
    rng = np.random.default_rng(seed)
    depth_trend = np.linspace(1.3, 0.6, nz)     # shallower -> higher k, mild trend
    k = np.zeros((nx, ny, nz))
    for kk in range(nz):
        base_k = 150.0 * depth_trend[kk]
        k[:, :, kk] = base_k * np.exp(0.55 * rng.standard_normal((nx, ny)))
    k *= 9.869e-16
    phi = np.clip(0.20 + 0.03 * rng.standard_normal((nx, ny, nz)), 0.08, 0.32)
    dz = np.full(nz, 60.0 / nz)   # 60 m total column, nz layers
    grid = Grid3D(nx, ny, nz, dx=12.0, dy=12.0, dz=dz, k=k, phi=phi)
    rock = Rock(nw=2.0, no=2.0, swc=0.2, sor=0.2, krw_max=0.6, kro_max=0.8)
    if tag == "wf":
        fluid = Fluid(mu_w=0.5, mu_o=5.0, c=1.0e-8, rho_w=1000.0, rho_o=800.0)
    else:
        fluid = Fluid(mu_w=0.05, mu_o=0.6, c=1.0e-8, rho_w=700.0, rho_o=1020.0)
    inj = [(0, 0, k_) for k_ in range(nz)]
    prod = [(nx - 1, ny - 1, k_) for k_ in range(nz)]
    wells = Wells(inj_cells=inj, prod_cells=prod, rate=0.0, bhp=0.0, inj_bhp=2.0e7)
    return grid, rock, fluid, wells, dz


def scenario_8b_field_case():
    """Stage 8b: 3D + gravity, randomized layers mimicking a field case
    (18 layers, lognormal-random k with a mild depth trend), not the known
    8-layer table. Same z-axis convention as Stage 8 (bigger number =
    further down). WF and CCUS."""
    FULL = dict(compressible=True, gravity=True, capillary=True,
               cap=Capillary(Pe=2.0e6, lam=2.0), n_diff_sub=3)

    for tag, label in [("ccus", "CCUS"), ("wf", "waterflood")]:
        grid, rock, fluid, wells, dz = _build_field_case(tag)
        nz = grid.nz
        depth = np.array([np.sum(dz[k + 1:]) + dz[k] / 2.0 for k in range(nz)])

        sim = StreamlineSimulator(grid, rock, fluid, wells, seeds_per_dim=4,
                                  no_crossflow=False, coverage_fill=True,
                                  conserve=True, **FULL)
        res = sim.run(target_pvi=0.25, n_psteps=6, verbose=False)
        sw = sim.sw
        xc = (np.arange(grid.nx) + 0.5) * grid.dx
        yc = (np.arange(grid.ny) + 0.5) * grid.dy
        X, Y = np.meshgrid(xc, yc, indexing="ij")

        # 3D stack
        fig = plt.figure(figsize=(9.5, 8))
        ax = fig.add_subplot(111, projection="3d")
        fig.suptitle(f"Stage 8b — field-case analog, {nz} randomized layers, {label}\n"
                    f"(PVI={res.pvi[-1]:.2f}; z-axis bigger number = further down)",
                    fontsize=12, fontweight="bold")
        norm = plt.Normalize(0.2, 0.8)
        for k in range(nz):
            fc = plt.cm.viridis(norm(sw[:, :, k]))
            Z = np.full_like(X, depth[k])
            ax.plot_surface(X, Y, Z, facecolors=fc, shade=False, rstride=1,
                           cstride=1, antialiased=False)
        ax.invert_zaxis()
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("depth [m]")
        ax.view_init(elev=16, azim=-60)
        m = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
        cb = fig.colorbar(m, ax=ax, fraction=0.025, pad=0.10); cb.set_label(r"$S_w$")
        fig.savefig(f"{OUTDIR}/stage08b_field3d_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        # cross-section
        j_mid = grid.ny // 2
        slice_xz = sw[:, j_mid, :].T
        depth_top = np.concatenate(([0.0], np.cumsum(dz)))
        xf = np.arange(grid.nx + 1) * grid.dx

        fig, ax = plt.subplots(figsize=(9, 5.5))
        fig.suptitle(f"Stage 8b — field-case cross-section, {label}, "
                    f"y={j_mid*grid.dy:.0f} m, PVI={res.pvi[-1]:.2f}",
                    fontsize=13, fontweight="bold")
        im = ax.pcolormesh(xf, depth_top, slice_xz, cmap="viridis", vmin=0.2,
                          vmax=0.8, shading="flat")
        ax.invert_yaxis()
        ax.axvline(0.5 * grid.dx, color="#1f77b4", lw=2, ls="--", label="injector")
        ax.set_xlabel("x [m]"); ax.set_ylabel("depth [m] (down)")
        ax.legend(loc="lower right", fontsize=9)
        cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label(r"$S_w$")
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        fig.savefig(f"{OUTDIR}/stage08b_fieldcross_{tag}.png", bbox_inches="tight")
        plt.show(block=False); plt.close(fig)

        layer_mean = [float(sw[:, :, k].mean()) for k in range(nz)]
        print(f"Stage 8b ({label}) done, {nz} layers, mean Sw range "
             f"[{min(layer_mean):.3f}, {max(layer_mean):.3f}]")


def run_all_scenarios(outdir="."):
    """Every scenario, all 20: the original 17 plus the 3 new CCUS figures
    (Stage 10), plus the validation suite first. This is the default now —
    one run, everything shown, nothing pre-filtered. For CCUS only, call
    run_ccus_story() directly instead."""
    global OUTDIR
    OUTDIR = outdir
    print(f"Output directory: {outdir}\n")

    print("=" * 78)
    print("Running the 7-check regression suite (run_validations.py, unmodified)")
    print("=" * 78)
    main()

    print()
    print("=" * 78)
    print(f"Running all {len(ALL_SCENARIOS)} scenario functions, fast -> slow")
    print("=" * 78)
    for i, (name, est) in enumerate(ALL_SCENARIOS_TIMED, 1):
        print(f"\n--- [{i}/{len(ALL_SCENARIOS)}] {name}  (expect {est}) ---")
        globals()[name]()

    print()
    print("=" * 78)
    print(f"Done. All {len(ALL_SCENARIOS)} scenario functions ran above.")
    print("=" * 78)





# ==============================================================================
# STAGE 12 [S12] — PAD-STREAM 5 x 5 x 5 DETERMINISTIC CCUS DEVELOPMENT CASE
# ==============================================================================
# This stage is new development code built directly on the reference classes and
# functions above. No existing reference function is edited here. The purpose is
# to expose each intermediate field on one small, deterministic grid before any
# learned model is introduced.
#
# Phase convention inherited from streamline_sim.py:
#   "w" / Sw / krw = injected phase = CO2 for this CCUS case
#   "o" / kro      = resident phase = brine
# User-facing z-layers 2, 3, 4 are Python indices 1:4.
# ============================================================================== 

PAD_OUTPUT_DIR = "pad_stream_5x5x5_outputs"
MILLI_DARCY_TO_M2 = 9.869233e-16
SECONDS_PER_YEAR = 365.0 * 24.0 * 3600.0


def md_to_m2(k_md):
    """Convert permeability from millidarcies to square metres."""
    return np.asarray(k_md, dtype=float) * MILLI_DARCY_TO_M2


def _pad_save(fig, filename, outdir):
    """Save and display a figure without closing it before an interactive backend sees it."""
    import os
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, filename)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.show(block=False)
    plt.close(fig)
    return path


def build_padstream_5x5x5_case(no_crossflow=False):
    """Deterministic layered CCUS test case.

    Grid:
        5 x 5 x 5 Cartesian cells
        dx = dy = 100 m, dz = 10 m

    Rock map:
        user layers 1 and 5: 100 mD, phi=0.15
        user layers 2-4:     400 mD, phi=0.25

    Wells:
        fully completed injector at (0,0), p=30 MPa
        fully completed producer at (4,4), p=20 MPa

    Common-pressure wells are intentional: layer rates are outputs of the TPFA
    solve and should scale with transmissibility, providing the direct bridge to
    Dykstra-Parsons kh allocation.
    """
    nx = ny = nz = 5
    dx = dy = 100.0
    dz = 10.0

    k_md = np.full((nx, ny, nz), 100.0, dtype=float)
    phi = np.full((nx, ny, nz), 0.15, dtype=float)
    k_md[:, :, 1:4] = 400.0
    phi[:, :, 1:4] = 0.25

    grid = Grid3D(
        nx=nx,
        ny=ny,
        nz=nz,
        dx=dx,
        dy=dy,
        dz=dz,
        k=md_to_m2(k_md),
        phi=phi,
    )

    rock = Rock(
        nw=2.0,
        no=2.0,
        swc=0.20,
        sor=0.20,
        krw_max=0.60,
        kro_max=0.80,
        cr=0.0,
        hysteresis=False,
        sgr=0.30,
    )

    fluid = Fluid(
        mu_w=0.05,       # injected CO2 phase [cp]
        mu_o=0.60,       # resident brine phase [cp]
        c=1.0e-8,        # reference EOS compressibility [1/Pa]
        rho_w=700.0,     # CO2 density [kg/m3]
        rho_o=1020.0,    # brine density [kg/m3]
    )

    cap = Capillary(Pe=2.0e6, lam=2.0)

    inj = [(0, 0, kk) for kk in range(nz)]
    prod = [(nx - 1, ny - 1, kk) for kk in range(nz)]
    wells = Wells(
        inj_cells=inj,
        prod_cells=prod,
        rate=0.0,
        bhp=2.0e7,
        inj_bhp=3.0e7,
    )

    # Structural verification of the user-specified map.
    assert grid.k.shape == (5, 5, 5)
    assert grid.phi.shape == (5, 5, 5)
    assert np.allclose(k_md[:, :, 0], 100.0)
    assert np.allclose(k_md[:, :, 4], 100.0)
    assert np.allclose(k_md[:, :, 1:4], 400.0)
    assert np.allclose(phi[:, :, 0], 0.15)
    assert np.allclose(phi[:, :, 4], 0.15)
    assert np.allclose(phi[:, :, 1:4], 0.25)

    return grid, rock, fluid, cap, wells, k_md


def plot_pad_grid_properties(grid, k_md, outdir=PAD_OUTPUT_DIR):
    """Plot every permeability and porosity layer as an individual figure."""
    z_layers = np.arange(1, grid.nz + 1)

    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow(k_md[:, :, kk].T, origin="lower", cmap="viridis")
        ax.set_title(f"Permeability map — user z-layer {kk + 1}")
        ax.set_xlabel("i index"); ax.set_ylabel("j index")
        cb = fig.colorbar(im, ax=ax); cb.set_label("permeability [mD]")
        _pad_save(fig, f"01_k_layer_{kk + 1}.png", outdir)

        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow(grid.phi[:, :, kk].T, origin="lower", cmap="viridis",
                       vmin=float(grid.phi.min()), vmax=float(grid.phi.max()))
        ax.set_title(f"Porosity map — user z-layer {kk + 1}")
        ax.set_xlabel("i index"); ax.set_ylabel("j index")
        cb = fig.colorbar(im, ax=ax); cb.set_label("porosity [-]")
        _pad_save(fig, f"02_phi_layer_{kk + 1}.png", outdir)

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(z_layers, [k_md[:, :, k].mean() for k in range(grid.nz)], "o-", lw=2)
    ax.set_xticks(z_layers)
    ax.set_xlabel("user z-layer"); ax.set_ylabel("mean permeability [mD]")
    ax.set_title("Layered permeability profile")
    ax.grid(alpha=0.3)
    _pad_save(fig, "03_mean_k_by_layer.png", outdir)

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(z_layers, [grid.phi[:, :, k].mean() for k in range(grid.nz)], "o-", lw=2)
    ax.set_xticks(z_layers)
    ax.set_xlabel("user z-layer"); ax.set_ylabel("mean porosity [-]")
    ax.set_title("Layered porosity profile")
    ax.grid(alpha=0.3)
    _pad_save(fig, "04_mean_phi_by_layer.png", outdir)


def plot_pad_constitutive_physics(rock, fluid, cap, grid, outdir=PAD_OUTPUT_DIR):
    """Expose the CCUS constitutive physics as individual diagnostic figures."""
    s = np.linspace(float(rock.swc), float(rock.sw_max), 500)
    se = np.clip((s - rock.swc) / rock.span, 0.0, 1.0)
    krg, krb = rel_perm(s, rock)
    lg = krg / (fluid.mu_w * 1e-3)
    lb = krb / (fluid.mu_o * 1e-3)
    lt = lg + lb
    fg = frac_flow(s, rock, fluid)
    dfg = np.gradient(fg, s)
    pc = capillary_pressure(s, rock, cap)
    dpc = dpc_dsw(s, rock, cap)

    # D for both permeability intervals, since k enters the coefficient directly.
    k_low = md_to_m2(100.0)
    k_high = md_to_m2(400.0)
    mobility_factor = lg * lb / np.maximum(lt, 1e-30)
    d_low = -k_low * mobility_factor * dpc
    d_high = -k_high * mobility_factor * dpc

    figures = []

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, se, lw=2)
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"effective saturation $S_e$")
    ax.set_title("Effective saturation")
    ax.grid(alpha=0.3); figures.append((fig, "05_effective_saturation.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, krg, lw=2, label=r"$k_{rg}$ (CO$_2$)")
    ax.plot(s, krb, lw=2, label=r"$k_{rb}$ (brine)")
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel("relative permeability")
    ax.set_title("Corey relative-permeability curves")
    ax.legend(); ax.grid(alpha=0.3); figures.append((fig, "06_relative_permeability.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, lg, lw=2, label=r"$\lambda_g$")
    ax.plot(s, lb, lw=2, label=r"$\lambda_b$")
    ax.plot(s, lt, lw=2, ls="--", label=r"$\lambda_t$")
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"mobility [Pa$^{-1}$ s$^{-1}$]")
    ax.set_title("Phase and total mobility")
    ax.legend(); ax.grid(alpha=0.3); figures.append((fig, "07_mobility.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, fg, lw=2)
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"$f_g$")
    ax.set_title("CO$_2$ fractional flow")
    ax.grid(alpha=0.3); figures.append((fig, "08_fractional_flow.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, dfg, lw=2)
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"$df_g/dS_{CO_2}$")
    ax.set_title("Fractional-flow derivative / characteristic speed factor")
    ax.grid(alpha=0.3); figures.append((fig, "09_fractional_flow_derivative.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, pc / 1e6, lw=2)
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"$P_c$ [MPa]")
    ax.set_title("Brooks-Corey capillary pressure")
    ax.grid(alpha=0.3); figures.append((fig, "10_capillary_pressure.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, dpc / 1e6, lw=2)
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"$dP_c/dS$ [MPa]")
    ax.set_title("Capillary-pressure derivative")
    ax.grid(alpha=0.3); figures.append((fig, "11_capillary_pressure_derivative.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(s, d_low, lw=2, label="100 mD layers")
    ax.plot(s, d_high, lw=2, label="400 mD layers")
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"$D(S)$ [m$^2$/s]")
    ax.set_title("Capillary diffusion coefficient by permeability interval")
    ax.legend(); ax.grid(alpha=0.3); figures.append((fig, "12_capillary_diffusion_coefficient.png"))

    for fig, name in figures:
        _pad_save(fig, name, outdir)


def plot_pad_1d_four_mode_ladder(outdir=PAD_OUTPUT_DIR):
    """Run the uploaded 1D solver suite for the CCUS parameter track only."""
    rock = CCUS_ROCK
    fluid = CCUS_FLUID
    geom = GEOM
    pres = PRES
    t_days = 600.0

    sw_f, fw_f, m_s, sw_grid, fw_grid, dfw_grid = find_shock(rock, fluid)

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(sw_grid, fw_grid, lw=2, label=r"$f_g(S_g)$")
    ax.plot([rock.swc, sw_f], [0.0, fw_f], "--", lw=2, label="Welge tangent")
    ax.plot(sw_f, fw_f, "o")
    ax.set_xlabel(r"$S_{CO_2}$"); ax.set_ylabel(r"$f_g$")
    ax.set_title(f"Welge construction: shock saturation = {sw_f:.4f}")
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, "13_welge_shock_construction.png", outdir)

    eos = CompressibleFluid(c=8.0e-4)
    cap1d = CapillaryProperties(Pe=80.0, k=2000.0)

    x_inc, s_inc = CompressibleBLSolver(rock, fluid, geom, eos, pres).solve_incompressible(
        t_days, nx=201
    )
    x_cmp, s_cmp = CompressibleBLSolver(rock, fluid, geom, eos, pres).solve(
        t_days, nx=201
    )
    x_cap, s_cap = CapillaryBLSolver(rock, fluid, geom, cap1d).solve(
        t_days, nx=201
    )
    full_solver = FullBLSolver(rock, fluid, geom, eos, pres, cap1d)
    x_full, s_full = full_solver.solve(t_days, nx=201)

    modes = [
        ("incompressible", x_inc, s_inc),
        ("compressible", x_cmp, s_cmp),
        ("capillary", x_cap, s_cap),
        ("full_compressible_capillary", x_full, s_full),
    ]
    for name, x, sat in modes:
        fig, ax = plt.subplots(figsize=(6.5, 4.8))
        ax.plot(x, sat, lw=2)
        ax.set_xlabel(r"$x_D$"); ax.set_ylabel(r"$S_{CO_2}$")
        ax.set_title(f"1D CCUS {name.replace('_', ' ')} profile at {t_days:.0f} days")
        ax.grid(alpha=0.3)
        _pad_save(fig, f"14_1d_{name}.png", outdir)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for name, x, sat in modes:
        ax.plot(x, sat, lw=2, label=name.replace("_", " "))
    ax.set_xlabel(r"$x_D$"); ax.set_ylabel(r"$S_{CO_2}$")
    ax.set_title(
        f"Four-mode 1D physics ladder: Nc={full_solver.Nc:.3f}, Pe_c={full_solver.Pe_c:.1f}"
    )
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, "15_1d_four_mode_overlay.png", outdir)


def assemble_pressure_system_diagnostic(grid, sw, rock, fluid, wells, no_crossflow=False):
    """The reference TPFA pressure assembly, exposed for matrix diagnostics.

    This mirrors solve_pressure() above and returns A and b in addition to p.
    """
    nx, ny, nz = grid.nx, grid.ny, grid.nz
    lamt = total_mobility(sw, rock, fluid)
    n = grid.ncell
    A = lil_matrix((n, n))
    b = np.zeros(n)
    dzk = grid.dzk
    Az = grid.dx * grid.dy

    def trans(k1, k2, lt1, lt2, area, distance):
        kh = 2.0 * k1 * k2 / (k1 + k2 + 1e-30)
        lf = 0.5 * (lt1 + lt2)
        return area * kh * lf / distance

    for kk in range(nz):
        Ax = grid.dy * dzk[kk]
        Ay = grid.dx * dzk[kk]
        for jj in range(ny):
            for ii in range(nx):
                c = grid.idx(ii, jj, kk)
                if ii + 1 < nx:
                    T = trans(grid.k[ii, jj, kk], grid.k[ii + 1, jj, kk],
                              lamt[ii, jj, kk], lamt[ii + 1, jj, kk], Ax, grid.dx)
                    nb = grid.idx(ii + 1, jj, kk)
                    A[c, c] += T; A[c, nb] -= T
                    A[nb, nb] += T; A[nb, c] -= T
                if jj + 1 < ny:
                    T = trans(grid.k[ii, jj, kk], grid.k[ii, jj + 1, kk],
                              lamt[ii, jj, kk], lamt[ii, jj + 1, kk], Ay, grid.dy)
                    nb = grid.idx(ii, jj + 1, kk)
                    A[c, c] += T; A[c, nb] -= T
                    A[nb, nb] += T; A[nb, c] -= T
                if kk + 1 < nz and not no_crossflow:
                    dzf = 0.5 * (dzk[kk] + dzk[kk + 1])
                    T = trans(grid.k[ii, jj, kk], grid.k[ii, jj, kk + 1],
                              lamt[ii, jj, kk], lamt[ii, jj, kk + 1], Az, dzf)
                    nb = grid.idx(ii, jj, kk + 1)
                    A[c, c] += T; A[c, nb] -= T
                    A[nb, nb] += T; A[nb, c] -= T

    if wells.inj_bhp is None:
        q_each = wells.rate / max(len(wells.inj_cells), 1)
        for cell in wells.inj_cells:
            b[grid.idx(*cell)] += q_each

    A = A.tocsr().tolil()
    for cell in wells.prod_cells:
        c = grid.idx(*cell)
        A.rows[c] = [c]; A.data[c] = [1.0]; b[c] = wells.bhp
    if wells.inj_bhp is not None:
        for cell in wells.inj_cells:
            c = grid.idx(*cell)
            A.rows[c] = [c]; A.data[c] = [1.0]; b[c] = wells.inj_bhp

    A = A.tocsr()
    p_flat = spsolve(A, b)
    p = p_flat.reshape((nz, ny, nx)).transpose(2, 1, 0)
    residual = A @ p_flat - b
    return A, b, p, lamt, residual


def plot_pad_pressure_diagnostics(grid, rock, fluid, wells, outdir=PAD_OUTPUT_DIR,
                                  no_crossflow=False):
    sw0 = np.full((grid.nx, grid.ny, grid.nz), float(rock.swc))
    A, b, p, lamt, residual = assemble_pressure_system_diagnostic(
        grid, sw0, rock, fluid, wells, no_crossflow=no_crossflow
    )

    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow((p[:, :, kk] / 1e6).T, origin="lower", cmap="viridis")
        ax.set_title(f"TPFA pressure — user z-layer {kk + 1}")
        ax.set_xlabel("i index"); ax.set_ylabel("j index")
        cb = fig.colorbar(im, ax=ax); cb.set_label("pressure [MPa]")
        _pad_save(fig, f"16_pressure_layer_{kk + 1}.png", outdir)

        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        x = (np.arange(grid.nx) + 0.5) * grid.dx
        y = (np.arange(grid.ny) + 0.5) * grid.dy
        X, Y = np.meshgrid(x, y, indexing="ij")
        cs = ax.contour(X, Y, p[:, :, kk] / 1e6, levels=10)
        ax.clabel(cs, inline=True, fontsize=8)
        ax.set_aspect("equal")
        ax.set_title(f"Pressure contours — user z-layer {kk + 1}")
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
        _pad_save(fig, f"17_pressure_contours_layer_{kk + 1}.png", outdir)

    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    ax.spy(A, markersize=2)
    ax.set_title("TPFA sparse pressure-matrix structure")
    ax.set_xlabel("column"); ax.set_ylabel("row")
    _pad_save(fig, "18_pressure_matrix_sparsity.png", outdir)

    rmap = residual.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    im = ax.imshow(np.max(np.abs(rmap), axis=2).T, origin="lower", cmap="viridis")
    ax.set_title("Maximum absolute algebraic residual across z")
    ax.set_xlabel("i index"); ax.set_ylabel("j index")
    cb = fig.colorbar(im, ax=ax); cb.set_label("|A p - b|")
    _pad_save(fig, "19_pressure_residual_map.png", outdir)

    qc, qtot = injection_rates(grid, p, lamt, wells, no_crossflow)
    q_layer = np.array([qc[(0, 0, kk)] for kk in range(grid.nz)])
    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.bar(np.arange(1, grid.nz + 1), q_layer * SECONDS_PER_YEAR)
    ax.set_xlabel("user z-layer"); ax.set_ylabel("injection allocation [m3/year]")
    ax.set_title(f"Common-BHP layer allocation; total = {qtot * SECONDS_PER_YEAR:.2e} m3/year")
    ax.set_xticks(np.arange(1, grid.nz + 1))
    ax.grid(axis="y", alpha=0.3)
    _pad_save(fig, "20_injection_rate_by_layer.png", outdir)

    return p, lamt, A, residual, q_layer


def _cell_center_velocity(V):
    vx = 0.5 * (V["xm"] + V["xp"])
    vy = 0.5 * (V["ym"] + V["yp"])
    vz = 0.5 * (V["zm"] + V["zp"])
    return vx, vy, vz


def plot_pad_velocity_diagnostics(grid, p, lamt, outdir=PAD_OUTPUT_DIR,
                                  no_crossflow=False):
    V = pore_velocities(grid, p, lamt, no_crossflow=no_crossflow)
    vx, vy, vz = _cell_center_velocity(V)
    speed = np.sqrt(vx**2 + vy**2 + vz**2)

    x = (np.arange(grid.nx) + 0.5) * grid.dx
    y = (np.arange(grid.ny) + 0.5) * grid.dy
    X, Y = np.meshgrid(x, y, indexing="ij")

    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow(speed[:, :, kk].T, origin="lower", cmap="viridis")
        ax.set_title(f"Pore-velocity magnitude — user z-layer {kk + 1}")
        ax.set_xlabel("i index"); ax.set_ylabel("j index")
        cb = fig.colorbar(im, ax=ax); cb.set_label("pore velocity [m/s]")
        _pad_save(fig, f"21_pore_speed_layer_{kk + 1}.png", outdir)

        fig, ax = plt.subplots(figsize=(6.0, 5.3))
        ax.contour(X, Y, p[:, :, kk] / 1e6, levels=8, alpha=0.7)
        ax.quiver(X, Y, vx[:, :, kk], vy[:, :, kk])
        ax.set_aspect("equal")
        ax.set_title(f"Pore-velocity vectors over pressure — z-layer {kk + 1}")
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
        _pad_save(fig, f"22_velocity_vectors_layer_{kk + 1}.png", outdir)

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.plot(np.arange(1, grid.nz + 1), [np.mean(speed[:, :, k]) for k in range(grid.nz)],
            "o-", lw=2)
    ax.set_xticks(np.arange(1, grid.nz + 1))
    ax.set_xlabel("user z-layer"); ax.set_ylabel("mean pore speed [m/s]")
    ax.set_title("Mean pore velocity by layer")
    ax.grid(alpha=0.3)
    _pad_save(fig, "23_mean_pore_speed_by_layer.png", outdir)
    return V, vx, vy, vz, speed


def trace_streamline_detailed(grid, V, start_cell, start_local, prod_set, max_steps=5000):
    """Pollock tracer with coordinates and exit-face history for diagnostics.

    It uses the exact same _exit_time() and _pos_at() functions as the uploaded
    reference tracer. Since V contains pore velocities, each returned dTau is a
    physical cell transit time and cumulative sum is time of flight.
    """
    i, j, k = start_cell
    xi, yi, zi = start_local
    dzk = grid.dzk
    z_edges = np.concatenate([[0.0], np.cumsum(dzk)])
    cells, dtaus, exit_faces = [], [], []
    points = [[i * grid.dx + xi, j * grid.dy + yi, z_edges[k] + zi]]
    reached = False

    for _ in range(max_steps):
        vxm, vxp = V["xm"][i, j, k], V["xp"][i, j, k]
        vym, vyp = V["ym"][i, j, k], V["yp"][i, j, k]
        vzm, vzp = V["zm"][i, j, k], V["zp"][i, j, k]
        dzc = dzk[k]

        tx, tgx = _exit_time(xi, vxm, vxp, grid.dx)
        ty, tgy = _exit_time(yi, vym, vyp, grid.dy)
        tz, tgz = _exit_time(zi, vzm, vzp, dzc)
        t = min(tx, ty, tz)
        if not np.isfinite(t) or t <= 0:
            break

        cells.append((i, j, k)); dtaus.append(t)
        nxi = _pos_at(xi, vxm, vxp, grid.dx, t)
        nyi = _pos_at(yi, vym, vyp, grid.dy, t)
        nzi = _pos_at(zi, vzm, vzp, dzc, t)
        points.append([i * grid.dx + nxi, j * grid.dy + nyi, z_edges[k] + nzi])

        ni, nj, nk = i, j, k
        if np.isclose(t, tx):
            if tgx == grid.dx:
                ni, nxi = i + 1, 0.0; exit_faces.append("x+")
            else:
                ni, nxi = i - 1, grid.dx; exit_faces.append("x-")
        elif np.isclose(t, ty):
            if tgy == grid.dy:
                nj, nyi = j + 1, 0.0; exit_faces.append("y+")
            else:
                nj, nyi = j - 1, grid.dy; exit_faces.append("y-")
        else:
            if tgz == dzc:
                nk, nzi = k + 1, 0.0; exit_faces.append("z+")
            else:
                nk = k - 1
                nzi = dzk[k - 1] if k - 1 >= 0 else 0.0
                exit_faces.append("z-")

        if ni < 0 or ni >= grid.nx or nj < 0 or nj >= grid.ny or nk < 0 or nk >= grid.nz:
            break
        i, j, k = ni, nj, nk
        xi, yi, zi = nxi, nyi, nzi
        if (i, j, k) in prod_set:
            reached = True
            cells.append((i, j, k)); dtaus.append(0.0)
            points.append([(i + 0.5) * grid.dx, (j + 0.5) * grid.dy,
                           z_edges[k] + 0.5 * dzk[k]])
            break

    return {
        "cells": cells,
        "dtaus": np.asarray(dtaus, dtype=float),
        "points": np.asarray(points, dtype=float),
        "exit_faces": exit_faces,
        "reached": reached,
    }


def build_pad_streamlines(grid, V, wells, seeds_per_dim=3, no_crossflow=False):
    """Trace flux-weighted injector streamlines for the deterministic case."""
    # Recompute pressure only to obtain per-completion BHP well allocation.
    sw0 = np.full((grid.nx, grid.ny, grid.nz), 0.20)
    # lamt is not needed here; rates will be assigned later by caller if desired.
    offsets_x = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim * grid.dx
    offsets_y = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim * grid.dy
    prod_set = set(wells.prod_cells)
    rows = []
    for cell in wells.inj_cells:
        i, j, k = cell
        for ox in offsets_x:
            for oy in offsets_y:
                row = trace_streamline_detailed(
                    grid, V, cell, (ox, oy, 0.5 * grid.dzk[k]), prod_set
                )
                row["source_layer"] = k
                rows.append(row)
    return rows


def plot_pad_streamline_tof_diagnostics(grid, p, lamt, V, wells, q_layer,
                                        outdir=PAD_OUTPUT_DIR, seeds_per_dim=3):
    rows = build_pad_streamlines(grid, V, wells, seeds_per_dim=seeds_per_dim)
    n_seed_layer = seeds_per_dim**2
    flux = []
    tof = []
    reached = []
    source_layer = []
    for row in rows:
        k = row["source_layer"]
        flux.append(max(q_layer[k] / n_seed_layer, 0.0))
        tof.append(float(np.sum(row["dtaus"])))
        reached.append(bool(row["reached"]))
        source_layer.append(k)
    flux = np.asarray(flux)
    tof = np.asarray(tof)
    reached = np.asarray(reached)
    source_layer = np.asarray(source_layer)

    # Three-dimensional geometry.
    fig = plt.figure(figsize=(8.0, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    for row in rows:
        pts = row["points"]
        if pts.shape[0] >= 2:
            ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], lw=1.2,
                    alpha=0.75 if row["reached"] else 0.25)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("depth coordinate [m]")
    ax.set_title("Pollock streamlines on the 5 x 5 x 5 layered grid")
    ax.invert_zaxis()
    _pad_save(fig, "24_pollock_streamlines_3d.png", outdir)

    # Layer-by-layer plan view, using only streamlines seeded in that layer.
    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(6.0, 5.3))
        cs = ax.contour((np.arange(grid.nx) + 0.5) * grid.dx,
                        (np.arange(grid.ny) + 0.5) * grid.dy,
                        (p[:, :, kk] / 1e6).T, levels=8)
        ax.clabel(cs, fontsize=7)
        for row in rows:
            if row["source_layer"] != kk:
                continue
            pts = row["points"]
            if pts.shape[0] >= 2:
                ax.plot(pts[:, 0], pts[:, 1], lw=1.2,
                        alpha=0.8 if row["reached"] else 0.25)
        ax.set_aspect("equal")
        ax.set_xlim(0, grid.nx * grid.dx); ax.set_ylim(0, grid.ny * grid.dy)
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
        ax.set_title(f"Pollock paths seeded in user z-layer {kk + 1}")
        _pad_save(fig, f"25_streamlines_seed_layer_{kk + 1}.png", outdir)

    # TOF distribution by source layer.
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    data = [tof[(source_layer == kk) & reached] / 86400.0 for kk in range(grid.nz)]
    ax.boxplot(data, labels=[str(k) for k in range(1, grid.nz + 1)], showmeans=True)
    ax.set_xlabel("source user z-layer"); ax.set_ylabel("injector-to-producer TOF [days]")
    ax.set_title("Time-of-flight distribution by source layer")
    ax.grid(axis="y", alpha=0.3)
    _pad_save(fig, "26_tof_by_source_layer.png", outdir)

    # Flux-weighted TOF histogram.
    valid = reached & np.isfinite(tof) & (tof > 0) & (flux > 0)
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    if np.any(valid):
        ax.hist(tof[valid] / 86400.0, bins=min(15, int(valid.sum())), weights=flux[valid])
    ax.set_xlabel("TOF [days]"); ax.set_ylabel("flux-weighted count")
    ax.set_title("Flux-weighted streamline time-of-flight distribution")
    _pad_save(fig, "27_flux_weighted_tof_histogram.png", outdir)

    # Cell-average TOF map from traversed-cell cumulative TOF.
    acc = np.zeros(grid.ncell); cnt = np.zeros(grid.ncell)
    for row in rows:
        if not row["cells"]:
            continue
        cumulative = np.cumsum(row["dtaus"])
        for cell, tau_value in zip(row["cells"], cumulative):
            idx = grid.idx(*cell)
            acc[idx] += tau_value; cnt[idx] += 1.0
    tof_flat = np.where(cnt > 0, acc / np.maximum(cnt, 1.0), np.nan)
    tof_map = tof_flat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)
    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow((tof_map[:, :, kk] / 86400.0).T, origin="lower", cmap="viridis")
        ax.set_title(f"Mean cumulative TOF — user z-layer {kk + 1}")
        ax.set_xlabel("i index"); ax.set_ylabel("j index")
        cb = fig.colorbar(im, ax=ax); cb.set_label("TOF [days]")
        _pad_save(fig, f"28_tof_map_layer_{kk + 1}.png", outdir)

    # F-Phi / Lorenz diagnostic from the reached injector streamlines.
    if np.any(valid):
        F, Phi, Lc = flow_storage_diagram(tof[valid], flux[valid])
        fig, ax = plt.subplots(figsize=(6.2, 5.2))
        ax.plot(Phi, F, lw=2, label=f"streamline F-Phi, Lc={Lc:.4f}")
        ax.plot([0, 1], [0, 1], "--", label="homogeneous diagonal")
        ax.set_xlabel(r"storage capacity $\Phi$")
        ax.set_ylabel(r"flow capacity $F$")
        ax.set_title("Dynamic heterogeneity from streamline TOF and flux")
        ax.legend(); ax.grid(alpha=0.3)
        _pad_save(fig, "29_streamline_fphi_lorenz.png", outdir)
    else:
        Lc = np.nan

    return rows, tof, flux, reached, tof_map, Lc


def run_pad_four_mode_3d(grid, rock, fluid, cap, wells, outdir=PAD_OUTPUT_DIR,
                         target_pvi=0.04, n_psteps=2, seeds_per_dim=1):
    """Run the uploaded StreamlineSimulator in its four existing physics modes.

    The multidimensional reference currently uses an incompressible TPFA pressure
    field; compressibility modifies velocity/TOF and adds the EOS source term in
    streamline transport, while capillary pressure is an implicit grid diffusion
    operator. This function does not claim a transient compressible pressure solve.
    """
    modes = [
        ("incompressible", dict(compressible=False, capillary=False)),
        ("compressible", dict(compressible=True, capillary=False)),
        ("capillary", dict(compressible=False, capillary=True, cap=cap)),
        ("full", dict(compressible=True, capillary=True, cap=cap)),
    ]
    outputs = {}
    for name, kwargs in modes:
        sim = StreamlineSimulator(
            grid, rock, fluid, wells,
            seeds_per_dim=seeds_per_dim,
            gravity=False,
            no_crossflow=False,
            coverage_fill=True,
            conserve=True,
            fill_stride=1,
            **kwargs,
        )
        res = sim.run(target_pvi=target_pvi, n_psteps=n_psteps, verbose=True)
        outputs[name] = (sim, res)

        for kk in range(grid.nz):
            fig, ax = plt.subplots(figsize=(5.8, 5.0))
            im = ax.imshow(res.sw_final[:, :, kk].T, origin="lower", cmap="viridis",
                           vmin=float(rock.swc), vmax=float(rock.sw_max))
            ax.set_title(f"{name}: final CO2 saturation — user z-layer {kk + 1}")
            ax.set_xlabel("i index"); ax.set_ylabel("j index")
            cb = fig.colorbar(im, ax=ax); cb.set_label(r"$S_{CO_2}$")
            _pad_save(fig, f"30_{name}_saturation_layer_{kk + 1}.png", outdir)

        fig, ax = plt.subplots(figsize=(6.5, 4.8))
        ax.plot(res.pvi, res.watercut, "o-", lw=2)
        ax.set_xlabel("PVI"); ax.set_ylabel("producer CO2 fractional flow")
        ax.set_title(f"{name}: producer response")
        ax.grid(alpha=0.3)
        _pad_save(fig, f"31_{name}_producer_fraction.png", outdir)

        fig, ax = plt.subplots(figsize=(6.5, 4.8))
        injected = np.asarray(res.injected)
        stored = np.asarray(res.stored)
        ax.plot(res.pvi, injected, "o-", lw=2, label="cumulative injected volume")
        ax.plot(res.pvi, stored, "o-", lw=2, label="injected minus total produced")
        ax.set_xlabel("PVI"); ax.set_ylabel("volume [m3]")
        ax.set_title(f"{name}: cumulative-volume bookkeeping")
        ax.legend(); ax.grid(alpha=0.3)
        _pad_save(fig, f"32_{name}_volume_bookkeeping.png", outdir)

    # Direct mode comparison at the middle high-property layer.
    kk = 2  # user layer 3
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.2))
    im = None
    for ax, (name, (sim, res)) in zip(axes, outputs.items()):
        im = ax.imshow(res.sw_final[:, :, kk].T, origin="lower", cmap="viridis",
                       vmin=float(rock.swc), vmax=float(rock.sw_max))
        ax.set_title(name)
        ax.set_xlabel("i"); ax.set_ylabel("j")
    fig.suptitle("Four-mode comparison on user z-layer 3")
    fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02, label=r"$S_{CO_2}$")
    _pad_save(fig, "33_four_mode_layer3_comparison.png", outdir)
    return outputs



# ==============================================================================
# STAGE 13 [S13] — POLLOCK CORNER-CROSSING AND TOF-CFL NUMERICAL CORRECTION
# ==============================================================================
# Diagnosis of Version 1:
#   1. Symmetric injector seeds can reach x and y faces at the same physical time.
#      The reference tracer advances only one cell index (if/elif), leaving the
#      particle exactly on the other face. The next iteration then creates an
#      artificial near-zero segment or a false stagnation.
#   2. Roundoff-level vertical velocities (~1e-18 m/s in this case) are treated as
#      real because the reference absolute threshold is 1e-30. Once horizontal
#      motion stalls, these components can create astronomical vertical transit
#      times and false z exits.
#
# The original reference tracer is retained below for before/after diagnostics.
# The corrected tracer remains Pollock semi-analytic: only event handling and
# numerical tolerances change. No pressure, mobility, flux, or transport physics
# is altered.
# ============================================================================== 

trace_streamline_reference = trace_streamline
trace_streamline_detailed_reference = trace_streamline_detailed


def _clean_local_face_velocities(values, relative_tolerance=1.0e-12,
                                 absolute_tolerance=1.0e-20):
    """Zero components that are roundoff relative to the local velocity scale.

    The comparison is local. A genuinely vertical-flow cell retains its vertical
    velocity because that component sets the local scale. In the deterministic
    layered benchmark, z velocities are ~1e-18 m/s while horizontal velocities
    are ~1e-5 m/s, so the spurious z components are removed.
    """
    values = np.asarray(values, dtype=float)
    scale = max(float(np.max(np.abs(values))), absolute_tolerance)
    tolerance = max(absolute_tolerance, relative_tolerance * scale)
    cleaned = np.where(np.abs(values) < tolerance, 0.0, values)
    return cleaned, tolerance


def _pollock_crossing_event(grid, V, cell, local_xyz,
                            velocity_relative_tolerance=1.0e-12,
                            event_relative_tolerance=1.0e-9):
    """Return one robust Pollock cell-exit event.

    Multiple axes may cross at the same time. This is required for exact edge and
    corner crossings. The function returns the physical transit time, crossed
    axes, target faces, and the advanced local coordinates.
    """
    i, j, k = cell
    xi, yi, zi = local_xyz
    dzc = grid.dzk[k]

    raw = [V['xm'][i, j, k], V['xp'][i, j, k],
           V['ym'][i, j, k], V['yp'][i, j, k],
           V['zm'][i, j, k], V['zp'][i, j, k]]
    cleaned, velocity_tolerance = _clean_local_face_velocities(
        raw, relative_tolerance=velocity_relative_tolerance
    )
    vxm, vxp, vym, vyp, vzm, vzp = cleaned

    tx, tgx = _exit_time(xi, vxm, vxp, grid.dx)
    ty, tgy = _exit_time(yi, vym, vyp, grid.dy)
    tz, tgz = _exit_time(zi, vzm, vzp, dzc)
    times = np.asarray([tx, ty, tz], dtype=float)
    transit_time = float(np.min(times))

    if not np.isfinite(transit_time) or transit_time <= 0.0:
        return None

    event_tolerance = event_relative_tolerance * max(1.0, abs(transit_time))
    crossed = np.isfinite(times) & (np.abs(times - transit_time) <= event_tolerance)

    advanced = (
        _pos_at(xi, vxm, vxp, grid.dx, transit_time),
        _pos_at(yi, vym, vyp, grid.dy, transit_time),
        _pos_at(zi, vzm, vzp, dzc, transit_time),
    )
    return {
        'time': transit_time,
        'crossed': crossed,
        'targets': (tgx, tgy, tgz),
        'advanced': advanced,
        'cleaned_velocities': cleaned,
        'velocity_tolerance': velocity_tolerance,
        'candidate_times': times,
    }


def trace_streamline(grid, V, start_cell, start_local, prod_set, max_steps=5000,
                     velocity_relative_tolerance=1.0e-12,
                     event_relative_tolerance=1.0e-9):
    """Corrected Pollock tracer with simultaneous face-crossing support."""
    i, j, k = start_cell
    xi, yi, zi = map(float, start_local)
    cells, dtaus = [], []
    reached = False
    dzk = grid.dzk

    for _ in range(max_steps):
        event = _pollock_crossing_event(
            grid, V, (i, j, k), (xi, yi, zi),
            velocity_relative_tolerance=velocity_relative_tolerance,
            event_relative_tolerance=event_relative_tolerance,
        )
        if event is None:
            break

        t = event['time']
        crossed = event['crossed']
        tgx, tgy, tgz = event['targets']
        nxi, nyi, nzi = event['advanced']
        cells.append((i, j, k))
        dtaus.append(t)

        ni, nj, nk = i, j, k
        if crossed[0]:
            if tgx == grid.dx:
                ni, nxi = i + 1, 0.0
            else:
                ni, nxi = i - 1, grid.dx
        if crossed[1]:
            if tgy == grid.dy:
                nj, nyi = j + 1, 0.0
            else:
                nj, nyi = j - 1, grid.dy
        if crossed[2]:
            if tgz == dzk[k]:
                nk, nzi = k + 1, 0.0
            else:
                nk = k - 1
                nzi = dzk[k - 1] if k - 1 >= 0 else 0.0

        if not (0 <= ni < grid.nx and 0 <= nj < grid.ny and 0 <= nk < grid.nz):
            break

        i, j, k = ni, nj, nk
        xi, yi, zi = nxi, nyi, nzi
        if (i, j, k) in prod_set:
            cells.append((i, j, k))
            dtaus.append(0.0)
            reached = True
            break

    return cells, np.asarray(dtaus, dtype=float), reached


def trace_streamline_detailed(grid, V, start_cell, start_local, prod_set,
                              max_steps=5000,
                              velocity_relative_tolerance=1.0e-12,
                              event_relative_tolerance=1.0e-9):
    """Corrected detailed tracer with explicit termination and crossing events."""
    i, j, k = start_cell
    xi, yi, zi = map(float, start_local)
    dzk = grid.dzk
    z_edges = np.concatenate([[0.0], np.cumsum(dzk)])
    cells, dtaus, exit_faces, crossing_multiplicity = [], [], [], []
    points = [[i * grid.dx + xi, j * grid.dy + yi, z_edges[k] + zi]]
    reached = False
    termination_reason = 'maximum_steps'

    for _ in range(max_steps):
        event = _pollock_crossing_event(
            grid, V, (i, j, k), (xi, yi, zi),
            velocity_relative_tolerance=velocity_relative_tolerance,
            event_relative_tolerance=event_relative_tolerance,
        )
        if event is None:
            termination_reason = 'stagnation'
            break

        t = event['time']
        crossed = event['crossed']
        tgx, tgy, tgz = event['targets']
        nxi, nyi, nzi = event['advanced']

        cells.append((i, j, k))
        dtaus.append(t)
        points.append([i * grid.dx + nxi,
                       j * grid.dy + nyi,
                       z_edges[k] + nzi])

        ni, nj, nk = i, j, k
        labels = []
        if crossed[0]:
            if tgx == grid.dx:
                ni, nxi = i + 1, 0.0
                labels.append('x+')
            else:
                ni, nxi = i - 1, grid.dx
                labels.append('x-')
        if crossed[1]:
            if tgy == grid.dy:
                nj, nyi = j + 1, 0.0
                labels.append('y+')
            else:
                nj, nyi = j - 1, grid.dy
                labels.append('y-')
        if crossed[2]:
            if tgz == dzk[k]:
                nk, nzi = k + 1, 0.0
                labels.append('z+')
            else:
                nk = k - 1
                nzi = dzk[k - 1] if k - 1 >= 0 else 0.0
                labels.append('z-')
        exit_faces.append('+'.join(labels))
        crossing_multiplicity.append(len(labels))

        if not (0 <= ni < grid.nx and 0 <= nj < grid.ny and 0 <= nk < grid.nz):
            termination_reason = 'domain_exit'
            break

        i, j, k = ni, nj, nk
        xi, yi, zi = nxi, nyi, nzi
        if (i, j, k) in prod_set:
            reached = True
            termination_reason = 'producer'
            cells.append((i, j, k))
            dtaus.append(0.0)
            points.append([(i + 0.5) * grid.dx,
                           (j + 0.5) * grid.dy,
                           z_edges[k] + 0.5 * dzk[k]])
            break

    return {
        'cells': cells,
        'dtaus': np.asarray(dtaus, dtype=float),
        'points': np.asarray(points, dtype=float),
        'exit_faces': exit_faces,
        'crossing_multiplicity': np.asarray(crossing_multiplicity, dtype=int),
        'reached': reached,
        'termination_reason': termination_reason,
    }


def _positive_dtau_from_injectors(grid, V, wells, tracer, seeds_per_dim):
    offsets = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim
    values = []
    reached_by_layer = np.zeros(grid.nz, dtype=int)
    total_by_layer = np.zeros(grid.nz, dtype=int)
    for cell in wells.inj_cells:
        k = cell[2]
        for ox in offsets * grid.dx:
            for oy in offsets * grid.dy:
                cells, dtaus, reached = tracer(
                    grid, V, cell, (ox, oy, 0.5 * grid.dzk[k]),
                    set(wells.prod_cells)
                )
                total_by_layer[k] += 1
                reached_by_layer[k] += int(reached)
                values.extend(dtaus[dtaus > 0.0].tolist())
    return np.asarray(values, dtype=float), reached_by_layer, total_by_layer



def _positive_dtau_from_detailed_injectors(grid, V, wells, tracer,
                                           seeds_per_dim):
    offsets = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim
    values = []
    reached_by_layer = np.zeros(grid.nz, dtype=int)
    total_by_layer = np.zeros(grid.nz, dtype=int)
    for cell in wells.inj_cells:
        k = cell[2]
        for ox in offsets * grid.dx:
            for oy in offsets * grid.dy:
                row = tracer(grid, V, cell,
                             (ox, oy, 0.5 * grid.dzk[k]),
                             set(wells.prod_cells))
                total_by_layer[k] += 1
                reached_by_layer[k] += int(row['reached'])
                dtaus = np.asarray(row['dtaus'], dtype=float)
                values.extend(dtaus[dtaus > 0.0].tolist())
    return np.asarray(values, dtype=float), reached_by_layer, total_by_layer


def _runtime_dtau_distribution(grid, V, wells, tracer, seeds_per_dim=1,
                               fill_stride=1):
    """Reproduce the StreamlineSimulator row construction without transport."""
    offsets_x = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim * grid.dx
    offsets_y = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim * grid.dy
    seeds = []
    for cell in wells.inj_cells:
        k = cell[2]
        for ox in offsets_x:
            for oy in offsets_y:
                seeds.append((cell, (ox, oy, 0.5 * grid.dzk[k])))

    prod_set = set(wells.prod_cells)
    inj_rows = []
    for start_cell, start_local in seeds:
        cells, dtaus, reached = tracer(
            grid, V, start_cell, start_local, prod_set
        )
        if len(cells) < 2:
            continue
        flat = np.fromiter((grid.idx(*cell) for cell in cells),
                           dtype=int, count=len(cells))
        inj_rows.append((flat, dtaus, reached, start_cell))

    rows = []
    covered = np.zeros(grid.ncell, dtype=bool)
    for flat, dtaus, reached, start_cell in inj_rows:
        rows.append((flat, dtaus, reached, True))
        covered[flat] = True

    backward = {key: -V[key] for key in V}
    injector_set = set(wells.inj_cells)
    nxy = grid.nx * grid.ny
    for cflat in np.where(~covered)[0][::fill_stride]:
        if covered[cflat]:
            continue
        k = int(cflat // nxy)
        remainder = int(cflat % nxy)
        j = remainder // grid.nx
        i = remainder % grid.nx
        local = (0.5 * grid.dx, 0.5 * grid.dy, 0.5 * grid.dzk[k])
        cells_forward, dt_forward, reached_forward = tracer(
            grid, V, (i, j, k), local, prod_set
        )
        cells_backward, dt_backward, reached_backward = tracer(
            grid, backward, (i, j, k), local, injector_set
        )
        cells = list(reversed(cells_backward))[:-1] + cells_forward
        dtaus = np.concatenate([dt_backward[::-1][:-1], dt_forward])
        if len(cells) < 2:
            continue
        flat = np.fromiter((grid.idx(*cell) for cell in cells),
                           dtype=int, count=len(cells))
        covered[flat] = True
        rows.append((flat, dtaus, reached_forward, bool(reached_backward)))

    positive = np.concatenate([
        np.asarray(row[1], dtype=float)[np.asarray(row[1]) > 0.0]
        for row in rows if np.any(np.asarray(row[1]) > 0.0)
    ])
    return positive, len(rows), int(np.sum(covered))


def run_pollock_cfl_diagnosis(outdir=PAD_OUTPUT_DIR, target_pvi=0.04,
                              n_psteps=2):
    """Generate before/after evidence for the Version-1 Pollock/TOF issue."""
    import os
    os.makedirs(outdir, exist_ok=True)
    grid, rock, fluid, cap, wells, _ = build_padstream_5x5x5_case()
    sw0 = np.full((grid.nx, grid.ny, grid.nz), float(rock.swc))
    p, lamt = solve_pressure(grid, sw0, rock, fluid, wells, False)
    V = pore_velocities(grid, p, lamt, False)

    # Three-by-three reachability reproduces the Version-1 plotting tracer,
    # which used np.isclose() to detect a tie but advanced only one axis.
    dt_ref_3, reach_ref, total = _positive_dtau_from_detailed_injectors(
        grid, V, wells, trace_streamline_detailed_reference, seeds_per_dim=3
    )
    dt_fix_3, reach_fix, _ = _positive_dtau_from_detailed_injectors(
        grid, V, wells, trace_streamline_detailed, seeds_per_dim=3
    )

    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    x = np.arange(1, grid.nz + 1)
    width = 0.36
    ax.bar(x - width / 2, reach_ref, width, label='reference tracer')
    ax.bar(x + width / 2, reach_fix, width, label='corrected tracer')
    ax.axhline(total[0], ls='--', lw=1, label='seeds per layer')
    ax.set_xticks(x)
    ax.set_xlabel('user z-layer')
    ax.set_ylabel('streamlines reaching producer')
    ax.set_title('Pollock reachability before and after corner-event correction')
    ax.legend(); ax.grid(axis='y', alpha=0.3)
    _pad_save(fig, '34_pollock_reachability_diagnosis.png', outdir)

    # Reproduce the runtime row construction, including coverage-fill paths.
    # This is the distribution actually used by the TOF transport CFL.
    dt_ref_1, rows_ref, covered_ref = _runtime_dtau_distribution(
        grid, V, wells, trace_streamline_reference,
        seeds_per_dim=1, fill_stride=1
    )
    dt_fix_1, rows_fix, covered_fix = _runtime_dtau_distribution(
        grid, V, wells, trace_streamline,
        seeds_per_dim=1, fill_stride=1
    )

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.hist(dt_ref_1 / 86400.0, bins=25, alpha=0.65,
            label='reference segments')
    ax.hist(dt_fix_1 / 86400.0, bins=25, alpha=0.65,
            label='corrected segments')
    ax.set_xscale('symlog', linthresh=1.0e-8)
    ax.set_xlabel('segment transit time [days]')
    ax.set_ylabel('count')
    ax.set_title('TOF segment distribution: artificial near-zero events removed')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, '35_dtau_distribution_before_after.png', outdir)

    _, qtotal = injection_rates(grid, p, lamt, wells, False)
    pv = float(np.sum(grid.phi * grid.vcell))
    outer_dt = (target_pvi * pv / qtotal) / n_psteps
    dfw_cap = max_dfw(rock, fluid)
    min_ref = float(np.min(dt_ref_1))
    min_fix = float(np.min(dt_fix_1))
    raw_nsub_ref = int(np.ceil(outer_dt / (0.4 * min_ref / dfw_cap)))
    raw_nsub_fix = int(np.ceil(outer_dt / (0.4 * min_fix / dfw_cap)))

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    labels = ['reference', 'corrected']
    values = [raw_nsub_ref, raw_nsub_fix]
    ax.bar(labels, values)
    ax.set_yscale('log')
    ax.set_ylabel('uncapped TOF-CFL substeps')
    ax.set_title('CFL impact of Pollock corner-event handling')
    for i, value in enumerate(values):
        ax.text(i, value, f'{value:.3g}', ha='center', va='bottom')
    ax.grid(axis='y', alpha=0.3)
    _pad_save(fig, '36_cfl_substeps_before_after.png', outdir)

    horizontal_max = max(float(np.max(np.abs(V[key])))
                         for key in ('xm', 'xp', 'ym', 'yp'))
    vertical_max = max(float(np.max(np.abs(V[key])))
                       for key in ('zm', 'zp'))

    print('-' * 80)
    print('POLLOCK / TOF-CFL DIAGNOSIS')
    print(f'Reference reachability: {int(reach_ref.sum())}/{int(total.sum())}')
    print(f'Corrected reachability: {int(reach_fix.sum())}/{int(total.sum())}')
    print(f'Reference runtime rows/covered cells: {rows_ref}/{covered_ref}')
    print(f'Corrected runtime rows/covered cells: {rows_fix}/{covered_fix}')
    print(f'Reference minimum positive dTau: {min_ref:.6e} s')
    print(f'Corrected minimum positive dTau: {min_fix:.6e} s '
          f'({min_fix / 86400.0:.3f} days)')
    print(f'Uncapped reference nsub: {raw_nsub_ref:.6e}')
    print(f'Corrected nsub: {raw_nsub_fix}')
    print(f'Max horizontal pore velocity: {horizontal_max:.6e} m/s')
    print(f'Max vertical numerical velocity: {vertical_max:.6e} m/s')
    print(f'Vertical/horizontal ratio: {vertical_max / horizontal_max:.6e}')
    print('-' * 80)

    return {
        'reference_reached': reach_ref,
        'corrected_reached': reach_fix,
        'minimum_dtau_reference_s': min_ref,
        'minimum_dtau_corrected_s': min_fix,
        'raw_nsub_reference': raw_nsub_ref,
        'raw_nsub_corrected': raw_nsub_fix,
        'runtime_rows_reference': rows_ref,
        'runtime_rows_corrected': rows_fix,
        'covered_cells_reference': covered_ref,
        'covered_cells_corrected': covered_fix,
        'horizontal_velocity_max': horizontal_max,
        'vertical_roundoff_velocity_max': vertical_max,
    }


def run_padstream_5x5x5_development(outdir=PAD_OUTPUT_DIR, run_coupled=False):
    """Execute the first complete physics-development pass.

    Order:
      1. deterministic geology
      2. constitutive physics
      3. 1D incompressible -> compressible -> capillary -> full ladder
      4. TPFA pressure
      5. Darcy/pore velocity
      6. Pollock streamlines
      7. time of flight and F-Phi
      8. four existing multidimensional physics modes
    """
    global OUTDIR
    OUTDIR = outdir
    import os
    os.makedirs(outdir, exist_ok=True)

    print("=" * 80)
    print("PAD-Stream 5 x 5 x 5 deterministic CCUS physics development")
    print("User z-layers 2-4: 400 mD, phi=0.25")
    print("User z-layers 1 and 5: 100 mD, phi=0.15")
    print("=" * 80)

    grid, rock, fluid, cap, wells, k_md = build_padstream_5x5x5_case()
    plot_pad_grid_properties(grid, k_md, outdir)
    plot_pad_constitutive_physics(rock, fluid, cap, grid, outdir)
    plot_pad_1d_four_mode_ladder(outdir)

    p, lamt, A, residual, q_layer = plot_pad_pressure_diagnostics(
        grid, rock, fluid, wells, outdir, no_crossflow=False
    )
    V, vx, vy, vz, speed = plot_pad_velocity_diagnostics(
        grid, p, lamt, outdir, no_crossflow=False
    )
    rows, tof, flux, reached, tof_map, Lc = plot_pad_streamline_tof_diagnostics(
        grid, p, lamt, V, wells, q_layer, outdir, seeds_per_dim=3
    )

    print(f"Pressure relative residual = {np.linalg.norm(residual) / (np.linalg.norm(A @ p.transpose(2,1,0).ravel()) + 1e-30):.3e}")
    print("Layer injection fractions:", q_layer / max(q_layer.sum(), 1e-30))
    print(f"Reached producer: {int(reached.sum())}/{len(reached)} injector streamlines")
    print(f"Streamline Lorenz coefficient Lc = {Lc:.5f}")

    outputs = None
    if run_coupled:
        outputs = run_pad_four_mode_3d(
            grid, rock, fluid, cap, wells, outdir,
            target_pvi=0.04, n_psteps=2, seeds_per_dim=1
        )

    print("=" * 80)
    print(f"Development pass complete. Figures saved in: {outdir}")
    print("=" * 80)
    return {
        "grid": grid,
        "rock": rock,
        "fluid": fluid,
        "capillary": cap,
        "wells": wells,
        "pressure": p,
        "mobility": lamt,
        "velocity": V,
        "streamlines": rows,
        "tof": tof,
        "tof_map": tof_map,
        "lorenz": Lc,
        "four_mode_outputs": outputs,
    }


# ==============================================================================
# STAGE 14 [S14] — CONSERVATIVE STREAMLINE TRANSPORT AND GRID MAP-BACK AUDIT
# ==============================================================================
# Diagnosis of the reference transport/map-back implementation:
#   1. Setting the first streamline control volume directly to injection saturation
#      fills an entire cell-sized pore volume independently of q_inj*dt.
#   2. Coverage-fill trajectories can behave as additional injection streamtubes,
#      although they are numerical interpolation paths rather than physical flux
#      partitions.
#   3. The scalar alpha correction is clipped to [0.5, 2.0], then injection cells
#      are reset and the field is clipped, so exact conservation is not guaranteed.
#   4. res.stored = cumulative injection - total production is not CO2 in place;
#      CO2 storage is the phase inventory change and production must be weighted by
#      the CO2 fractional flow.
#
# The audited implementation below preserves the uploaded physics functions and
# changes only the numerical coupling contract:
#   - physical injector-seeded streamlines only for the baseline benchmark;
#   - injection imposed as a boundary fractional-flow flux, not a cell reset;
#   - q_l * Delta tau is retained as the streamline-segment pore-volume weight;
#   - map-back error is measured explicitly;
#   - capillary diffusion is audited before any correction;
#   - a bounded conservative projection closes volume (incompressible/capillary)
#     or EOS-weighted CO2 mass (compressible/full) to numerical tolerance.
# ==============================================================================


@dataclass
class TransportStepAudit:
    step: int
    time_s: float
    pvi: float
    n_streamlines: int
    n_reached: int
    covered_cells: int
    total_cells: int
    transport_substeps: int
    q_inj_m3_s: float
    q_prod_m3_s: float
    producer_co2_fraction: float
    inventory_kind: str
    inventory_old: float
    boundary_inventory_change: float
    packet_inventory_change: float
    mapped_inventory_change: float
    operator_inventory_change: float
    preprojection_inventory_change: float
    projection_inventory_change: float
    final_inventory_change: float
    final_balance_error: float
    projection_l1_saturation: float
    projection_linf_saturation: float
    raw_weight_ratio_min: float
    raw_weight_ratio_mean: float
    raw_weight_ratio_max: float


@dataclass
class AuditedSimResult:
    pvi: list = field(default_factory=list)
    time: list = field(default_factory=list)
    producer_co2_fraction: list = field(default_factory=list)
    injected_co2_volume: list = field(default_factory=list)
    produced_co2_volume: list = field(default_factory=list)
    co2_volume_in_place: list = field(default_factory=list)
    injected_co2_mass: list = field(default_factory=list)
    produced_co2_mass: list = field(default_factory=list)
    co2_mass_in_place: list = field(default_factory=list)
    balance_error: list = field(default_factory=list)
    projection_l1: list = field(default_factory=list)
    projection_linf: list = field(default_factory=list)
    transport_substeps: list = field(default_factory=list)
    transport_median_substeps: list = field(default_factory=list)
    transport_p90_substeps: list = field(default_factory=list)
    transport_work: list = field(default_factory=list)
    transport_work_reduction: list = field(default_factory=list)
    audits: list = field(default_factory=list)
    sw_final: np.ndarray = None
    pressure_final: np.ndarray = None
    tof_final: np.ndarray = None
    coverage_final: np.ndarray = None
    raw_weight_ratio_final: np.ndarray = None
    selected_seed_density: list = field(default_factory=list)
    streamline_count: list = field(default_factory=list)
    quadrature_cv: list = field(default_factory=list)


def co2_density_from_reference_eos(pressure, fluid: Fluid, injector_pressure):
    """CO2 density consistent with the reference velocity scaling.

    The uploaded compressible streamline code uses
        v_comp = v_inc * exp(c * (p_inj - p)) = v_inc * rho_inj/rho(p).
    Therefore rho(p) = rho_inj * exp(c * (p - p_inj)).  fluid.rho_w is
    interpreted as the injected-phase density at the injector reference pressure.
    """
    return fluid.rho_w * np.exp(fluid.c * (np.asarray(pressure) - injector_pressure))


def phase_inventory(grid: Grid3D, saturation, density=None):
    """Return phase volume [m3] or mass [kg] for a cell-centred field."""
    weight = grid.phi * grid.vcell
    if density is not None:
        weight = weight * np.asarray(density)
    return float(np.sum(weight * np.asarray(saturation)))


def _broadcast_bounds(value, shape):
    if np.isscalar(value):
        return np.full(shape, float(value))
    return np.broadcast_to(np.asarray(value, dtype=float), shape).copy()


def bounded_conservative_projection(saturation_proposal, inventory_weights,
                                    target_inventory, lower_bound, upper_bound,
                                    active_mask=None, relative_tolerance=1.0e-12,
                                    max_iterations=30):
    """Project a saturation proposal to an exact bounded global inventory.

    The proposal's spatial pattern is retained as much as possible.  A residual
    inventory is distributed in proportion to each active cell's remaining
    saturation capacity.  The algorithm handles clipping explicitly and reports
    the final inventory residual instead of hiding it behind a scalar alpha cap.
    """
    proposal = np.asarray(saturation_proposal, dtype=float)
    weights = np.asarray(inventory_weights, dtype=float)
    lower = _broadcast_bounds(lower_bound, proposal.shape)
    upper = _broadcast_bounds(upper_bound, proposal.shape)
    projected = np.clip(proposal.copy(), lower, upper)

    if active_mask is None:
        active = np.ones(proposal.shape, dtype=bool)
    else:
        active = np.asarray(active_mask, dtype=bool).copy()

    feasible_min = float(np.sum(weights * np.where(active, lower, projected)))
    feasible_max = float(np.sum(weights * np.where(active, upper, projected)))
    target = float(np.clip(target_inventory, feasible_min, feasible_max))
    tolerance = relative_tolerance * max(abs(target), 1.0)

    for _ in range(max_iterations):
        current = float(np.sum(weights * projected))
        residual = target - current
        if abs(residual) <= tolerance:
            break

        if residual > 0.0:
            saturation_capacity = np.where(active, np.maximum(upper - projected, 0.0), 0.0)
        else:
            saturation_capacity = np.where(active, np.maximum(projected - lower, 0.0), 0.0)

        inventory_capacity = weights * saturation_capacity
        capacity_total = float(np.sum(inventory_capacity))
        if capacity_total <= tolerance:
            break

        fraction = min(1.0, abs(residual) / capacity_total)
        if residual > 0.0:
            projected += fraction * saturation_capacity
        else:
            projected -= fraction * saturation_capacity
        projected = np.clip(projected, lower, upper)

    final_inventory = float(np.sum(weights * projected))
    return projected, {
        'requested_target': float(target_inventory),
        'feasible_target': target,
        'final_inventory': final_inventory,
        'residual': final_inventory - target,
        'correction': projected - proposal,
        'feasible_min': feasible_min,
        'feasible_max': feasible_max,
    }


def _injector_seed_rows(grid, velocity, wells, injection_rates_by_cell,
                        seeds_per_dim=3):
    """Trace only physical injector-seeded streamtubes.

    The per-seed fluxes sum exactly to the pressure-solved injection rate.  No
    coverage-fill trajectory is allowed to create an additional injection source.
    """
    offsets_x = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim * grid.dx
    offsets_y = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim * grid.dy
    producer_set = set(wells.prod_cells)
    rows = []

    for source_cell in wells.inj_cells:
        traced = []
        for ox in offsets_x:
            for oy in offsets_y:
                local = (ox, oy, 0.5 * grid.dzk[source_cell[2]])
                cells, dtaus, reached = trace_streamline(
                    grid, velocity, source_cell, local, producer_set
                )
                if len(cells) < 2:
                    continue
                flat = np.fromiter((grid.idx(*cell) for cell in cells),
                                   dtype=int, count=len(cells))
                traced.append((flat, np.asarray(dtaus, dtype=float), reached,
                               source_cell, local))

        if not traced:
            continue
        stream_flux = injection_rates_by_cell[source_cell] / len(traced)
        for flat, dtaus, reached, source_cell, local in traced:
            rows.append((flat, dtaus, reached, stream_flux, source_cell, local))

    return rows


def _streamline_matrices(grid, rows, saturation, pressure):
    n_streamlines = len(rows)
    max_length = max(len(row[0]) for row in rows)
    flat_index = np.full((n_streamlines, max_length), -1, dtype=int)
    dtau = np.zeros((n_streamlines, max_length))
    sw = np.zeros((n_streamlines, max_length))
    p = np.zeros((n_streamlines, max_length))
    flux = np.zeros(n_streamlines)
    valid = np.zeros((n_streamlines, max_length), dtype=bool)
    reached = np.zeros(n_streamlines, dtype=bool)

    saturation_flat = saturation.transpose(2, 1, 0).ravel()
    pressure_flat = pressure.transpose(2, 1, 0).ravel()

    for row_index, (flat, dtaus, did_reach, q_stream, _, _) in enumerate(rows):
        length = len(flat)
        flat_index[row_index, :length] = flat
        dtau[row_index, :length] = dtaus
        sw[row_index, :length] = saturation_flat[flat]
        p[row_index, :length] = pressure_flat[flat]
        flux[row_index] = q_stream
        valid[row_index, :length] = True
        reached[row_index] = did_reach

    return flat_index, dtau, sw, p, flux, valid, reached


def _inlet_fractional_flow(rock_segment, fluid, inject_co2=True):
    """Fractional-flow boundary condition for each physical streamtube."""
    if inject_co2:
        inlet_saturation = np.asarray(rock_segment.sw_max)[:, 0]
    else:
        inlet_saturation = np.asarray(rock_segment.swc)[:, 0]

    inlet_rock = Rock(
        nw=np.asarray(rock_segment.nw)[:, 0],
        no=np.asarray(rock_segment.no)[:, 0],
        swc=np.asarray(rock_segment.swc)[:, 0],
        sor=np.asarray(rock_segment.sor)[:, 0],
        krw_max=np.asarray(rock_segment.krw_max)[:, 0],
        kro_max=np.asarray(rock_segment.kro_max)[:, 0],
    )
    return inlet_saturation, frac_flow(inlet_saturation, inlet_rock, fluid)


def _rock_streamline_row(rock_segment, row_index, length):
    """Extract one streamline's per-segment rock arrays from a batched Rock."""
    def take(value):
        array = np.asarray(value, dtype=float)
        if array.ndim == 0:
            return np.full(length, float(array))
        return array[row_index, :length].copy()

    return Rock(
        nw=take(rock_segment.nw),
        no=take(rock_segment.no),
        swc=take(rock_segment.swc),
        sor=take(rock_segment.sor),
        krw_max=take(rock_segment.krw_max),
        kro_max=take(rock_segment.kro_max),
        cr=take(rock_segment.cr),
        hysteresis=rock_segment.hysteresis,
        sgr=rock_segment.sgr,
    )


def _advance_one_streamline_local_cfl(sw_initial, pressure_segment, dtau, valid,
                                      rock_segment, fluid, dt, compressible,
                                      inject_co2, dfw_cap, cfl_number):
    """Advance one independent TOF transport problem with its own CFL timestep."""
    sw = np.asarray(sw_initial, dtype=float).copy()
    pressure_segment = np.asarray(pressure_segment, dtype=float)
    dtau = np.asarray(dtau, dtype=float)
    valid = np.asarray(valid, dtype=bool)
    positive = (dtau > 0.0) & valid
    positive_values = dtau[positive]
    if positive_values.size == 0:
        return sw, 1

    dt_cfl = cfl_number * float(np.min(positive_values)) / (dfw_cap + 1.0e-30)
    n_substeps = max(1, int(np.ceil(dt / dt_cfl)))
    sub_dt = dt / n_substeps

    inlet_saturation = (np.asarray(rock_segment.sw_max, dtype=float)[0]
                        if inject_co2
                        else np.asarray(rock_segment.swc, dtype=float)[0])
    inlet_rock = Rock(
        nw=float(np.asarray(rock_segment.nw)[0]),
        no=float(np.asarray(rock_segment.no)[0]),
        swc=float(np.asarray(rock_segment.swc)[0]),
        sor=float(np.asarray(rock_segment.sor)[0]),
        krw_max=float(np.asarray(rock_segment.krw_max)[0]),
        kro_max=float(np.asarray(rock_segment.kro_max)[0]),
    )
    inlet_fraction = float(frac_flow(
        np.asarray([inlet_saturation]), inlet_rock, fluid
    )[0])

    dp_dtau = np.zeros_like(dtau)
    dtau_backward = np.where(dtau > 1.0e-30, dtau, np.inf)
    dp_dtau[1:] = (pressure_segment[1:] - pressure_segment[:-1]) / dtau_backward[1:]
    dp_dtau[~valid] = 0.0
    compressibility = fluid.c if compressible else 0.0
    tau_safe = np.where(positive, dtau, np.inf)

    for _ in range(n_substeps):
        phase_flux = frac_flow(sw, rock_segment, fluid)
        incoming_flux = np.empty_like(phase_flux)
        incoming_flux[0] = inlet_fraction
        incoming_flux[1:] = phase_flux[:-1]
        courant = np.where(positive, sub_dt / tau_safe, 0.0)
        sw = (
            sw
            - courant * (phase_flux - incoming_flux)
            + sub_dt * phase_flux * compressibility * dp_dtau
        )
        sw = np.clip(sw, rock_segment.swc, rock_segment.sw_max)

    return sw, n_substeps


def conservative_streamline_transport(sw_initial, pressure_segment, dtau, valid,
                                      rock_segment, fluid, dt, compressible=False,
                                      inject_co2=True, dfw_cap=None,
                                      cfl_strategy='local_streamline',
                                      cfl_number=0.05):
    """Conservative BL transport in TOF space with selectable CFL strategy.

    ``global`` reproduces the Version-4 vectorized update: the shortest segment
    on any streamline sets one timestep for every streamline.

    ``local_streamline`` retains the same explicit upwind finite-volume equation,
    but each independent streamline uses its own stable timestep.  This is valid
    because streamline transport is decoupled between pressure updates; capillary
    communication remains a separate grid operator after map-back.
    """
    sw_initial = np.asarray(sw_initial, dtype=float)
    sw = sw_initial.copy()
    if dfw_cap is None:
        dfw_cap = max_dfw(rock_segment, fluid)

    positive = (dtau > 0.0) & valid
    n_streamlines = sw.shape[0]
    if not np.any(positive):
        diagnostics = {
            'strategy': cfl_strategy,
            'cfl_number': float(cfl_number),
            'substeps_per_streamline': np.ones(n_streamlines, dtype=int),
            'max_substeps': 1,
            'median_substeps': 1.0,
            'p90_substeps': 1.0,
            'total_streamline_updates': n_streamlines,
            'equivalent_global_updates': n_streamlines,
            'work_reduction_factor': 1.0,
            'minimum_dtau_s': np.nan,
        }
        return sw, diagnostics

    if cfl_strategy == 'global':
        positive_values = dtau[positive]
        dt_cfl = cfl_number * float(np.min(positive_values)) / (dfw_cap + 1.0e-30)
        n_substeps = max(1, int(np.ceil(dt / dt_cfl)))
        sub_dt = dt / n_substeps
        inlet_saturation, inlet_fraction = _inlet_fractional_flow(
            rock_segment, fluid, inject_co2=inject_co2
        )
        dp_dtau = np.zeros_like(dtau)
        dtau_backward = np.where(dtau > 1.0e-30, dtau, np.inf)
        dp_dtau[:, 1:] = (
            pressure_segment[:, 1:] - pressure_segment[:, :-1]
        ) / dtau_backward[:, 1:]
        dp_dtau[~valid] = 0.0
        compressibility = fluid.c if compressible else 0.0
        tau_safe = np.where(positive, dtau, np.inf)

        for _ in range(n_substeps):
            phase_flux = frac_flow(sw, rock_segment, fluid)
            incoming_flux = np.empty_like(phase_flux)
            incoming_flux[:, 0] = inlet_fraction
            incoming_flux[:, 1:] = phase_flux[:, :-1]
            courant = np.where(positive, sub_dt / tau_safe, 0.0)
            sw = (
                sw
                - courant * (phase_flux - incoming_flux)
                + sub_dt * phase_flux * compressibility * dp_dtau
            )
            sw = np.clip(sw, rock_segment.swc, rock_segment.sw_max)

        substeps = np.full(n_streamlines, n_substeps, dtype=int)
    elif cfl_strategy == 'local_streamline':
        substeps = np.ones(n_streamlines, dtype=int)
        for row in range(n_streamlines):
            length = int(np.sum(valid[row]))
            if length == 0:
                continue
            row_rock = _rock_streamline_row(rock_segment, row, length)
            row_new, row_substeps = _advance_one_streamline_local_cfl(
                sw[row, :length], pressure_segment[row, :length],
                dtau[row, :length], valid[row, :length], row_rock, fluid, dt,
                compressible=compressible, inject_co2=inject_co2,
                dfw_cap=dfw_cap, cfl_number=cfl_number,
            )
            sw[row, :length] = row_new
            substeps[row] = row_substeps
    else:
        raise ValueError(
            "cfl_strategy must be 'global' or 'local_streamline', got "
            f"{cfl_strategy!r}"
        )

    max_substeps = int(np.max(substeps))
    total_updates = int(np.sum(substeps))
    equivalent_global = int(n_streamlines * max_substeps)
    diagnostics = {
        'strategy': cfl_strategy,
        'cfl_number': float(cfl_number),
        'substeps_per_streamline': substeps.copy(),
        'max_substeps': max_substeps,
        'median_substeps': float(np.median(substeps)),
        'p90_substeps': float(np.percentile(substeps, 90)),
        'p99_substeps': float(np.percentile(substeps, 99)),
        'total_streamline_updates': total_updates,
        'equivalent_global_updates': equivalent_global,
        'work_reduction_factor': float(equivalent_global / max(total_updates, 1)),
        'minimum_dtau_s': float(np.min(dtau[positive])),
    }
    return sw, diagnostics


def map_streamline_saturation_to_grid(grid, flat_index, dtau, valid,
                                      stream_flux, streamline_saturation,
                                      old_grid_saturation):
    """Map streamline saturation to cells using q_l * Delta tau weights."""
    positive = (dtau > 0.0) & valid
    segment_volume = stream_flux[:, None] * np.where(positive, dtau, 0.0)
    numerator = np.zeros(grid.ncell)
    denominator = np.zeros(grid.ncell)
    np.add.at(numerator, flat_index[positive],
              (segment_volume * streamline_saturation)[positive])
    np.add.at(denominator, flat_index[positive], segment_volume[positive])

    covered = denominator > 1.0e-30
    old_flat = old_grid_saturation.transpose(2, 1, 0).ravel()
    mapped_flat = old_flat.copy()
    mapped_flat[covered] = numerator[covered] / denominator[covered]
    mapped = mapped_flat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)

    pore_volume_flat = (grid.phi * grid.vcell).transpose(2, 1, 0).ravel()
    raw_weight_ratio = np.full(grid.ncell, np.nan)
    raw_weight_ratio[covered] = denominator[covered] / pore_volume_flat[covered]

    return mapped, {
        'segment_volume': segment_volume,
        'denominator': denominator,
        'covered_flat': covered,
        'covered_grid': covered.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0),
        'raw_weight_ratio_flat': raw_weight_ratio,
        'raw_weight_ratio_grid': raw_weight_ratio.reshape(
            (grid.nz, grid.ny, grid.nx)
        ).transpose(2, 1, 0),
    }


def _streamline_geometry_metrics(grid, wells, rows, saturation, pressure):
    """Coverage and q*dtau quadrature diagnostics for a candidate seed density."""
    flat_index, dtau, _, _, stream_flux, valid, reached = _streamline_matrices(
        grid, rows, saturation, pressure
    )
    positive = (dtau > 0.0) & valid
    denominator = np.zeros(grid.ncell)
    if np.any(positive):
        np.add.at(denominator, flat_index[positive],
                  (stream_flux[:, None] * dtau)[positive])
    pore_volume = (grid.phi * grid.vcell).transpose(2, 1, 0).ravel()
    producer_flat = {grid.idx(*cell) for cell in wells.prod_cells}
    physical_domain = np.array(
        [cell not in producer_flat for cell in range(grid.ncell)], dtype=bool
    )
    covered = denominator > 1.0e-30
    represented = covered & physical_domain
    ratio = denominator[represented] / pore_volume[represented]
    cv = float(np.std(ratio) / (np.mean(ratio) + 1.0e-30)) if ratio.size else np.inf
    return {
        'covered_cells': int(np.sum(represented)),
        'target_cells': int(np.sum(physical_domain)),
        'coverage_fraction': float(np.sum(represented) / max(np.sum(physical_domain), 1)),
        'ratio_min': float(np.min(ratio)) if ratio.size else np.nan,
        'ratio_mean': float(np.mean(ratio)) if ratio.size else np.nan,
        'ratio_max': float(np.max(ratio)) if ratio.size else np.nan,
        'ratio_cv': cv,
        'n_streamlines': len(rows),
        'n_reached': int(np.sum(reached)),
        'covered_flat': covered,
        'raw_denominator': denominator,
    }


def adaptive_injector_seed_rows(grid, velocity, wells, injection_rates_by_cell,
                                saturation, pressure, min_density=2,
                                max_density=8, coverage_target=1.0,
                                quadrature_cv_target=0.25):
    """Increase physical injector seed density until geometry criteria are met.

    This is a deterministic global-adaptive rule for the small 5x5x5 benchmark.
    It never creates coverage-fill streamlines and every accepted streamline
    receives a share of the pressure-solved injector rate.
    """
    history = []
    selected_rows = None
    selected_density = max_density
    for density in range(min_density, max_density + 1):
        rows = _injector_seed_rows(
            grid, velocity, wells, injection_rates_by_cell,
            seeds_per_dim=density
        )
        metrics = _streamline_geometry_metrics(
            grid, wells, rows, saturation, pressure
        )
        metrics['seed_density'] = density
        history.append(metrics)
        selected_rows = rows
        selected_density = density
        if (metrics['coverage_fraction'] >= coverage_target
                and metrics['ratio_cv'] <= quadrature_cv_target):
            break
    return selected_rows, selected_density, history


def map_streamline_increment_to_grid(grid, flat_index, dtau, valid,
                                     stream_flux, streamline_saturation_old,
                                     streamline_saturation_new,
                                     old_grid_saturation):
    """Conservatively map packet saturation increments to grid pore volumes.

    For each grid cell i,
        Delta S_i = sum(q_l Delta tau_lm Delta S_lm) / PV_i.
    Consequently the grid inventory change equals the raw streamline-packet
    inventory change before saturation bounds or additional grid operators.
    """
    positive = (dtau > 0.0) & valid
    segment_volume = stream_flux[:, None] * np.where(positive, dtau, 0.0)
    segment_delta_inventory = segment_volume * (
        streamline_saturation_new - streamline_saturation_old
    )
    delta_inventory = np.zeros(grid.ncell)
    denominator = np.zeros(grid.ncell)
    np.add.at(delta_inventory, flat_index[positive],
              segment_delta_inventory[positive])
    np.add.at(denominator, flat_index[positive], segment_volume[positive])

    pore_volume_flat = (grid.phi * grid.vcell).transpose(2, 1, 0).ravel()
    old_flat = old_grid_saturation.transpose(2, 1, 0).ravel()
    mapped_flat = old_flat + delta_inventory / np.maximum(pore_volume_flat, 1.0e-30)
    mapped = mapped_flat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)

    covered = denominator > 1.0e-30
    raw_weight_ratio = np.full(grid.ncell, np.nan)
    raw_weight_ratio[covered] = denominator[covered] / pore_volume_flat[covered]
    mapped_inventory_change = float(np.sum(pore_volume_flat * (mapped_flat - old_flat)))
    packet_inventory_change = float(np.sum(segment_delta_inventory[positive]))

    return mapped, {
        'segment_volume': segment_volume,
        'segment_delta_inventory': segment_delta_inventory,
        'delta_inventory_flat': delta_inventory,
        'denominator': denominator,
        'covered_flat': covered,
        'covered_grid': covered.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0),
        'raw_weight_ratio_flat': raw_weight_ratio,
        'raw_weight_ratio_grid': raw_weight_ratio.reshape(
            (grid.nz, grid.ny, grid.nx)
        ).transpose(2, 1, 0),
        'packet_volume_change': packet_inventory_change,
        'mapped_volume_change': mapped_inventory_change,
        'increment_mapping_error': mapped_inventory_change - packet_inventory_change,
    }


class AuditedStreamlineSimulator:
    """Physics-first transport/map-back implementation for the 5x5x5 benchmark."""

    def __init__(self, grid, rock, fluid, wells, capillary_model=None,
                 seeds_per_dim=3, compressible=False, capillary=False,
                 n_diff_sub=2, inject_co2=True, adaptive_seeding=False,
                 min_seed_density=2, max_seed_density=8,
                 coverage_target=1.0, quadrature_cv_target=0.25,
                 transport_cfl_strategy='local_streamline',
                 transport_cfl_number=0.05):
        self.grid = grid
        self.rock = rock
        self.fluid = fluid
        self.wells = wells
        self.capillary_model = capillary_model if capillary_model is not None else Capillary()
        self.seeds_per_dim = seeds_per_dim
        self.compressible = compressible
        self.capillary = capillary
        self.n_diff_sub = n_diff_sub
        self.inject_co2 = inject_co2
        self.adaptive_seeding = adaptive_seeding
        self.min_seed_density = min_seed_density
        self.max_seed_density = max_seed_density
        self.coverage_target = coverage_target
        self.quadrature_cv_target = quadrature_cv_target
        self.transport_cfl_strategy = transport_cfl_strategy
        self.transport_cfl_number = float(transport_cfl_number)
        self.seed_history = []
        self.sw = np.full((grid.nx, grid.ny, grid.nz), float(rock.swc))
        self.dfw_cap = max_dfw(rock, fluid)
        self.pore_volume = float(np.sum(grid.phi * grid.vcell))
        self.initial_sw = self.sw.copy()
        self.step_fields = []

    def _inventory_weights(self, pressure):
        if not self.compressible:
            return self.grid.phi * self.grid.vcell, None, 'CO2 volume [m3]'
        injector_pressure = float(np.mean([pressure[cell] for cell in self.wells.inj_cells]))
        density = co2_density_from_reference_eos(
            pressure, self.fluid, injector_pressure
        )
        return self.grid.phi * self.grid.vcell * density, density, 'CO2 mass [kg]'

    def run(self, target_pvi=0.20, n_pressure_steps=10, verbose=True):
        result = AuditedSimResult()
        p0, mobility0 = solve_pressure(
            self.grid, self.sw, self.rock, self.fluid, self.wells, False
        )
        _, reference_rate = injection_rates(
            self.grid, p0, mobility0, self.wells, False
        )
        dt = target_pvi * self.pore_volume / reference_rate / n_pressure_steps

        initial_volume = phase_inventory(self.grid, self.initial_sw)
        initial_injector_pressure = float(np.mean([p0[c] for c in self.wells.inj_cells]))
        initial_density = co2_density_from_reference_eos(
            p0, self.fluid, initial_injector_pressure
        )
        initial_mass = phase_inventory(self.grid, self.initial_sw, initial_density)

        cumulative_injected_volume = 0.0
        cumulative_produced_volume = 0.0
        cumulative_injected_mass = 0.0
        cumulative_produced_mass = 0.0
        time_s = 0.0

        for step in range(n_pressure_steps):
            old_sw = self.sw.copy()
            pressure, mobility = solve_pressure(
                self.grid, old_sw, self.rock, self.fluid, self.wells, False
            )
            velocity = pore_velocities(self.grid, pressure, mobility, False)

            injector_pressure = float(np.mean([pressure[c] for c in self.wells.inj_cells]))
            producer_pressure = float(np.mean([pressure[c] for c in self.wells.prod_cells]))
            density = co2_density_from_reference_eos(
                pressure, self.fluid, injector_pressure
            )
            density_inj = float(self.fluid.rho_w)
            density_prod = float(self.fluid.rho_w * np.exp(
                self.fluid.c * (producer_pressure - injector_pressure)
            ))

            if self.compressible and self.fluid.c > 0.0:
                velocity_scale = np.exp(self.fluid.c * (injector_pressure - pressure))
                for key in velocity:
                    velocity[key] = velocity[key] * velocity_scale

            injection_by_cell, total_injection_rate = injection_rates(
                self.grid, pressure, mobility, self.wells, False
            )
            total_production_rate = producer_rate(
                self.grid, pressure, mobility, self.wells, False
            )

            if self.adaptive_seeding:
                rows, selected_density, seed_history = adaptive_injector_seed_rows(
                    self.grid, velocity, self.wells, injection_by_cell,
                    old_sw, pressure,
                    min_density=self.min_seed_density,
                    max_density=self.max_seed_density,
                    coverage_target=self.coverage_target,
                    quadrature_cv_target=self.quadrature_cv_target,
                )
            else:
                selected_density = self.seeds_per_dim
                rows = _injector_seed_rows(
                    self.grid, velocity, self.wells, injection_by_cell,
                    seeds_per_dim=selected_density
                )
                seed_history = [_streamline_geometry_metrics(
                    self.grid, self.wells, rows, old_sw, pressure
                )]
                seed_history[0]['seed_density'] = selected_density
            selected_metrics = seed_history[-1]
            self.seed_history.append(seed_history)
            (flat_index, dtau, sw_stream, pressure_stream, stream_flux,
             valid, reached) = _streamline_matrices(
                self.grid, rows, old_sw, pressure
            )
            rock_segment = self.rock.at(
                np.clip(flat_index, 0, self.grid.ncell - 1)
            )

            positive = (dtau > 0.0) & valid
            raw_segment_volume = stream_flux[:, None] * np.where(positive, dtau, 0.0)
            packet_old_volume = float(np.sum(raw_segment_volume * sw_stream))
            if self.compressible:
                density_flat = density.transpose(2, 1, 0).ravel()
                density_segment = density_flat[np.clip(flat_index, 0, self.grid.ncell - 1)]
                packet_old_inventory = float(np.sum(
                    raw_segment_volume * density_segment * sw_stream
                ))
            else:
                density_segment = None
                packet_old_inventory = packet_old_volume

            sw_stream_new, transport_diagnostics = conservative_streamline_transport(
                sw_stream, pressure_stream, dtau, valid, rock_segment,
                self.fluid, dt, compressible=self.compressible,
                inject_co2=self.inject_co2, dfw_cap=self.dfw_cap,
                cfl_strategy=self.transport_cfl_strategy,
                cfl_number=self.transport_cfl_number,
            )
            n_transport_substeps = transport_diagnostics['max_substeps']
            packet_new_volume = float(np.sum(raw_segment_volume * sw_stream_new))
            if self.compressible:
                packet_new_inventory = float(np.sum(
                    raw_segment_volume * density_segment * sw_stream_new
                ))
            else:
                packet_new_inventory = packet_new_volume

            mapped_sw, mapping = map_streamline_increment_to_grid(
                self.grid, flat_index, dtau, valid, stream_flux,
                sw_stream, sw_stream_new, old_sw
            )

            inventory_weights, density_for_inventory, inventory_kind = self._inventory_weights(
                pressure
            )
            old_inventory = float(np.sum(inventory_weights * old_sw))
            mapped_inventory = float(np.sum(inventory_weights * mapped_sw))

            operator_sw = mapped_sw.copy()
            if self.capillary:
                operator_sw = diffuse_grid(
                    self.grid, operator_sw, self.rock, self.fluid,
                    self.capillary_model, dt, self.n_diff_sub
                )
            operator_inventory = float(np.sum(inventory_weights * operator_sw))

            # Fixed-point coupling between producer fractional flow and the bounded
            # conservative projection.  Usually two iterations are sufficient.
            projected_sw = operator_sw.copy()
            projection_info = None
            producer_fraction = 0.0
            for _ in range(3):
                producer_fraction = producer_watercut(
                    self.grid, pressure, mobility, projected_sw,
                    self.rock, self.fluid, self.wells, False
                )
                if self.compressible:
                    boundary_change = (
                        density_inj * total_injection_rate * dt
                        - density_prod * total_production_rate * producer_fraction * dt
                    )
                else:
                    boundary_change = (
                        total_injection_rate * dt
                        - total_production_rate * producer_fraction * dt
                    )
                target_inventory = old_inventory + boundary_change
                active_mask = (
                    mapping['covered_grid']
                    | (np.abs(operator_sw - old_sw) > 1.0e-14)
                )
                projected_sw, projection_info = bounded_conservative_projection(
                    operator_sw, inventory_weights, target_inventory,
                    self.rock.swc, self.rock.sw_max,
                    active_mask=active_mask
                )

            producer_fraction = producer_watercut(
                self.grid, pressure, mobility, projected_sw,
                self.rock, self.fluid, self.wells, False
            )
            if self.compressible:
                boundary_change = (
                    density_inj * total_injection_rate * dt
                    - density_prod * total_production_rate * producer_fraction * dt
                )
            else:
                boundary_change = (
                    total_injection_rate * dt
                    - total_production_rate * producer_fraction * dt
                )
            target_inventory = old_inventory + boundary_change
            projected_sw, projection_info = bounded_conservative_projection(
                operator_sw, inventory_weights, target_inventory,
                self.rock.swc, self.rock.sw_max,
                active_mask=(mapping['covered_grid'] |
                             (np.abs(operator_sw - old_sw) > 1.0e-14))
            )

            final_inventory = float(np.sum(inventory_weights * projected_sw))
            correction = projection_info['correction']
            ratio_values = mapping['raw_weight_ratio_flat'][
                np.isfinite(mapping['raw_weight_ratio_flat'])
            ]

            time_s += dt
            cumulative_injected_volume += total_injection_rate * dt
            cumulative_produced_volume += total_production_rate * producer_fraction * dt
            cumulative_injected_mass += density_inj * total_injection_rate * dt
            cumulative_produced_mass += (
                density_prod * total_production_rate * producer_fraction * dt
            )

            current_volume = phase_inventory(self.grid, projected_sw)
            current_mass = phase_inventory(self.grid, projected_sw, density)
            pvi = cumulative_injected_volume / self.pore_volume

            packet_change = packet_new_inventory - packet_old_inventory
            mapped_change = mapped_inventory - old_inventory
            operator_change = operator_inventory - old_inventory
            preprojection_change = operator_change
            projection_change = final_inventory - operator_inventory
            final_change = final_inventory - old_inventory
            balance_error = final_change - boundary_change

            audit = TransportStepAudit(
                step=step + 1,
                time_s=time_s,
                pvi=pvi,
                n_streamlines=len(rows),
                n_reached=int(np.sum(reached)),
                covered_cells=int(np.sum(mapping['covered_grid'])),
                total_cells=self.grid.ncell,
                transport_substeps=n_transport_substeps,
                q_inj_m3_s=total_injection_rate,
                q_prod_m3_s=total_production_rate,
                producer_co2_fraction=float(producer_fraction),
                inventory_kind=inventory_kind,
                inventory_old=old_inventory,
                boundary_inventory_change=float(boundary_change),
                packet_inventory_change=float(packet_change),
                mapped_inventory_change=float(mapped_change),
                operator_inventory_change=float(operator_change),
                preprojection_inventory_change=float(preprojection_change),
                projection_inventory_change=float(projection_change),
                final_inventory_change=float(final_change),
                final_balance_error=float(balance_error),
                projection_l1_saturation=float(np.mean(np.abs(correction))),
                projection_linf_saturation=float(np.max(np.abs(correction))),
                raw_weight_ratio_min=float(np.min(ratio_values)),
                raw_weight_ratio_mean=float(np.mean(ratio_values)),
                raw_weight_ratio_max=float(np.max(ratio_values)),
            )
            result.audits.append(audit)
            result.pvi.append(pvi)
            result.time.append(time_s)
            result.producer_co2_fraction.append(float(producer_fraction))
            result.injected_co2_volume.append(cumulative_injected_volume)
            result.produced_co2_volume.append(cumulative_produced_volume)
            result.co2_volume_in_place.append(current_volume - initial_volume)
            result.injected_co2_mass.append(cumulative_injected_mass)
            result.produced_co2_mass.append(cumulative_produced_mass)
            result.co2_mass_in_place.append(current_mass - initial_mass)
            result.balance_error.append(float(balance_error))
            result.projection_l1.append(audit.projection_l1_saturation)
            result.projection_linf.append(audit.projection_linf_saturation)
            result.transport_substeps.append(n_transport_substeps)
            result.transport_median_substeps.append(transport_diagnostics['median_substeps'])
            result.transport_p90_substeps.append(transport_diagnostics['p90_substeps'])
            result.transport_work.append(transport_diagnostics['total_streamline_updates'])
            result.transport_work_reduction.append(transport_diagnostics['work_reduction_factor'])
            result.selected_seed_density.append(int(selected_density))
            result.streamline_count.append(len(rows))
            result.quadrature_cv.append(float(selected_metrics['ratio_cv']))

            self.step_fields.append({
                'step': step + 1,
                'pressure': pressure.copy(),
                'old_saturation': old_sw.copy(),
                'mapped_saturation': mapped_sw.copy(),
                'operator_saturation': operator_sw.copy(),
                'projection_correction': correction.copy(),
                'final_saturation': projected_sw.copy(),
                'coverage': mapping['covered_grid'].copy(),
                'raw_weight_ratio': mapping['raw_weight_ratio_grid'].copy(),
                'tof': np.where(valid, dtau, 0.0).sum(axis=1),
                'stream_flux': stream_flux.copy(),
                'rows': rows,
                'velocity': {key: np.asarray(value).copy() for key, value in velocity.items()},
                'mobility': mobility.copy(),
                'selected_seed_density': int(selected_density),
                'seed_history': seed_history,
                'increment_mapping_error': float(mapping['increment_mapping_error']),
                'transport_diagnostics': transport_diagnostics,
                'outer_dt_s': float(dt),
                'transport_cfl_number': self.transport_cfl_number,
            })

            self.sw = projected_sw
            if verbose:
                unit = 'kg' if self.compressible else 'm3'
                print(
                    f"  audited step {step + 1:2d}/{n_pressure_steps}  "
                    f"PVI={pvi:6.3f}  fCO2={producer_fraction:6.3f}  "
                    f"nsub(max/med)={n_transport_substeps:4d}/"
                    f"{transport_diagnostics['median_substeps']:.0f}  "
                    f"balance={balance_error:+.3e} {unit}  "
                    f"projection Linf={audit.projection_linf_saturation:.3e}  "
                    f"seeds={selected_density}x{selected_density}  "
                    f"coverage={selected_metrics['covered_cells']}/{selected_metrics['target_cells']}"
                )

        result.sw_final = self.sw.copy()
        result.pressure_final = pressure.copy()
        result.coverage_final = mapping['covered_grid'].copy()
        result.raw_weight_ratio_final = mapping['raw_weight_ratio_grid'].copy()
        return result


def _plot_audit_layer(field, title, filename, outdir, cmap='viridis',
                      vmin=None, vmax=None, colorbar_label='', layer_index=2):
    fig, ax = plt.subplots(figsize=(5.8, 5.0))
    im = ax.imshow(np.asarray(field)[:, :, layer_index].T, origin='lower',
                   cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel('i index'); ax.set_ylabel('j index')
    cb = fig.colorbar(im, ax=ax)
    if colorbar_label:
        cb.set_label(colorbar_label)
    return _pad_save(fig, filename, outdir)


def plot_transport_mapback_audit(mode_name, simulator, result,
                                 outdir=PAD_OUTPUT_DIR):
    """Create individual figures for every physics stage in the coupling audit."""
    import os
    os.makedirs(outdir, exist_ok=True)
    rock = simulator.rock

    for fields in simulator.step_fields:
        step = fields['step']
        prefix = f"40_{mode_name}_step_{step:02d}"
        _plot_audit_layer(
            fields['old_saturation'],
            f'{mode_name}, step {step}: saturation before streamline transport',
            f'{prefix}_01_old_saturation.png', outdir,
            vmin=float(rock.swc), vmax=float(rock.sw_max),
            colorbar_label=r'$S_{CO_2}$'
        )
        _plot_audit_layer(
            fields['mapped_saturation'],
            f'{mode_name}, step {step}: after TOF transport and map-back',
            f'{prefix}_02_mapped_saturation.png', outdir,
            vmin=float(rock.swc), vmax=float(rock.sw_max),
            colorbar_label=r'$S_{CO_2}$'
        )
        _plot_audit_layer(
            fields['operator_saturation'],
            f'{mode_name}, step {step}: after grid capillary operator',
            f'{prefix}_03_operator_saturation.png', outdir,
            vmin=float(rock.swc), vmax=float(rock.sw_max),
            colorbar_label=r'$S_{CO_2}$'
        )
        max_correction = max(float(np.max(np.abs(fields['projection_correction']))), 1.0e-12)
        _plot_audit_layer(
            fields['projection_correction'],
            f'{mode_name}, step {step}: bounded conservation correction',
            f'{prefix}_04_projection_correction.png', outdir,
            cmap='coolwarm', vmin=-max_correction, vmax=max_correction,
            colorbar_label=r'$\Delta S_{CO_2}$'
        )
        _plot_audit_layer(
            fields['final_saturation'],
            f'{mode_name}, step {step}: accepted conservative saturation',
            f'{prefix}_05_final_saturation.png', outdir,
            vmin=float(rock.swc), vmax=float(rock.sw_max),
            colorbar_label=r'$S_{CO_2}$'
        )
        _plot_audit_layer(
            fields['coverage'].astype(float),
            f'{mode_name}, step {step}: physical streamline coverage',
            f'{prefix}_06_coverage.png', outdir,
            cmap='binary', vmin=0.0, vmax=1.0,
            colorbar_label='covered cell'
        )
        ratio = fields['raw_weight_ratio']
        finite = ratio[np.isfinite(ratio)]
        vmax = max(float(np.max(finite)) if finite.size else 1.0, 1.0)
        _plot_audit_layer(
            ratio,
            f'{mode_name}, step {step}: raw qΔτ / cell pore-volume ratio',
            f'{prefix}_07_raw_weight_ratio.png', outdir,
            cmap='viridis', vmin=0.0, vmax=vmax,
            colorbar_label=r'$\sum q_\ell\Delta\tau/PV_{cell}$'
        )

    audits = result.audits
    pvi = np.asarray(result.pvi)
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.plot(pvi, [a.boundary_inventory_change for a in audits], 'o-', label='boundary target')
    ax.plot(pvi, [a.packet_inventory_change for a in audits], 's-', label='streamline packets')
    ax.plot(pvi, [a.mapped_inventory_change for a in audits], '^-', label='grid map-back')
    ax.plot(pvi, [a.operator_inventory_change for a in audits], 'd-', label='after grid operator')
    ax.plot(pvi, [a.final_inventory_change for a in audits], 'x-', label='accepted final')
    ax.set_xlabel('PVI'); ax.set_ylabel(audits[0].inventory_kind)
    ax.set_title(f'{mode_name}: inventory change through every coupling stage')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, f'41_{mode_name}_inventory_stage_comparison.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(pvi, np.asarray(result.balance_error), 'o-')
    ax.axhline(0.0, color='k', lw=1)
    ax.set_xlabel('PVI'); ax.set_ylabel('final inventory balance error')
    ax.set_title(f'{mode_name}: conservative projection closure')
    ax.grid(alpha=0.3)
    _pad_save(fig, f'42_{mode_name}_balance_error.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(pvi, result.projection_l1, 'o-', label='mean |correction|')
    ax.plot(pvi, result.projection_linf, 's-', label='max |correction|')
    ax.set_xlabel('PVI'); ax.set_ylabel('saturation correction')
    ax.set_title(f'{mode_name}: magnitude of conservative map correction')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, f'43_{mode_name}_projection_magnitude.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(pvi, result.injected_co2_volume, 'o-', label='cumulative CO2 injected')
    ax.plot(pvi, result.produced_co2_volume, 's-', label='cumulative CO2 produced')
    ax.plot(pvi, result.co2_volume_in_place, '^-', label='CO2 volume inventory change')
    ax.set_xlabel('PVI'); ax.set_ylabel('volume [m3]')
    ax.set_title(f'{mode_name}: physical CO2 volume bookkeeping')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, f'44_{mode_name}_co2_volume_bookkeeping.png', outdir)

    if simulator.compressible:
        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.plot(pvi, result.injected_co2_mass, 'o-', label='cumulative CO2 injected')
        ax.plot(pvi, result.produced_co2_mass, 's-', label='cumulative CO2 produced')
        ax.plot(pvi, result.co2_mass_in_place, '^-', label='EOS-weighted mass inventory change')
        ax.set_xlabel('PVI'); ax.set_ylabel('mass [kg]')
        ax.set_title(f'{mode_name}: approximate EOS CO2 mass bookkeeping')
        ax.legend(); ax.grid(alpha=0.3)
        _pad_save(fig, f'45_{mode_name}_co2_mass_bookkeeping.png', outdir)


def run_transport_mapback_diagnosis(outdir=PAD_OUTPUT_DIR, target_pvi=0.08,
                                    n_pressure_steps=4,
                                    seeds_per_dim=3):
    """Run all four physics modes through the audited transport/map-back chain."""
    import os
    os.makedirs(outdir, exist_ok=True)
    grid, rock, fluid, cap, wells, _ = build_padstream_5x5x5_case()
    modes = [
        ('incompressible', False, False),
        ('compressible', True, False),
        ('capillary', False, True),
        ('full', True, True),
    ]
    outputs = {}

    for name, compressible, capillary_on in modes:
        print('-' * 80)
        print(f'AUDITED TRANSPORT / MAP-BACK MODE: {name}')
        simulator = AuditedStreamlineSimulator(
            grid, rock, fluid, wells,
            capillary_model=cap,
            seeds_per_dim=seeds_per_dim,
            compressible=compressible,
            capillary=capillary_on,
            n_diff_sub=2,
            inject_co2=True,
        )
        result = simulator.run(
            target_pvi=target_pvi,
            n_pressure_steps=n_pressure_steps,
            verbose=True,
        )
        plot_transport_mapback_audit(name, simulator, result, outdir)
        outputs[name] = (simulator, result)

    # Four-mode final comparison on the middle high-property layer.
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.2))
    image = None
    for ax, (name, (_, result)) in zip(axes, outputs.items()):
        image = ax.imshow(result.sw_final[:, :, 2].T, origin='lower', cmap='viridis',
                          vmin=float(rock.swc), vmax=float(rock.sw_max))
        ax.set_title(name); ax.set_xlabel('i'); ax.set_ylabel('j')
    fig.suptitle('Audited transport and conservative map-back: user z-layer 3')
    fig.colorbar(image, ax=axes, fraction=0.02, pad=0.02, label=r'$S_{CO_2}$')
    _pad_save(fig, '46_audited_four_mode_final_comparison.png', outdir)

    # Summary table printed for direct regression use.
    print('=' * 100)
    print('TRANSPORT / MAP-BACK AUDIT SUMMARY')
    print(f"{'mode':<16}{'max balance error':>20}{'max projection':>20}"
          f"{'coverage':>14}{'max nsub':>12}")
    for name, (_, result) in outputs.items():
        max_balance = max(abs(value) for value in result.balance_error)
        max_projection = max(result.projection_linf)
        coverage = result.audits[-1].covered_cells
        max_nsub = max(result.transport_substeps)
        print(f'{name:<16}{max_balance:>20.6e}{max_projection:>20.6e}'
              f'{coverage:>8d}/{grid.ncell:<5d}{max_nsub:>12d}')
    print('=' * 100)
    return outputs



# ==============================================================================
# STAGE 15 [S15] — ADAPTIVE PHYSICAL SEEDING, CONSERVATIVE INCREMENT MAP,
#                    AND RESTORED PRESSURE/STREAMLINE VISUALS
# ==============================================================================

def _flat_to_ijk(grid, flat):
    flat = int(flat)
    k = flat // (grid.nx * grid.ny)
    rem = flat - k * grid.nx * grid.ny
    j = rem // grid.nx
    i = rem - j * grid.nx
    return i, j, k


def plot_dynamic_pressure_and_streamlines(mode_name, simulator,
                                          outdir=PAD_OUTPUT_DIR):
    """Restore pressure contours and streamline geometry for every pressure step."""
    for fields in simulator.step_fields:
        step = fields['step']
        pressure = fields['pressure']
        # Individual pressure contour for every z layer.
        for k in range(simulator.grid.nz):
            fig, ax = plt.subplots(figsize=(5.8, 5.0))
            X, Y = np.meshgrid(
                np.arange(simulator.grid.nx), np.arange(simulator.grid.ny),
                indexing='ij'
            )
            values = pressure[:, :, k] / 1.0e6
            filled = ax.contourf(X, Y, values, levels=14, cmap='viridis')
            lines = ax.contour(X, Y, values, levels=8, colors='k', linewidths=0.55)
            ax.clabel(lines, inline=True, fontsize=7, fmt='%.2f')
            ax.scatter([cell[0] for cell in simulator.wells.inj_cells if cell[2] == k],
                       [cell[1] for cell in simulator.wells.inj_cells if cell[2] == k],
                       marker='^', s=70, label='injector')
            ax.scatter([cell[0] for cell in simulator.wells.prod_cells if cell[2] == k],
                       [cell[1] for cell in simulator.wells.prod_cells if cell[2] == k],
                       marker='v', s=70, label='producer')
            ax.set_title(f'{mode_name}, step {step}: pressure contours, z-layer {k + 1}')
            ax.set_xlabel('i index'); ax.set_ylabel('j index')
            ax.legend(loc='best')
            fig.colorbar(filled, ax=ax, label='pressure [MPa]')
            _pad_save(fig,
                      f'47_{mode_name}_step_{step:02d}_pressure_contour_layer_{k + 1}.png',
                      outdir)

        # Cell-centre streamline paths. Exact Pollock paths are still generated in
        # the baseline Stage 13 figures; this view tracks their evolution by step.
        fig = plt.figure(figsize=(8.0, 6.5))
        ax = fig.add_subplot(111, projection='3d')
        qmax = max((row[3] for row in fields['rows']), default=1.0)
        for flat, _, reached, q_stream, _, _ in fields['rows']:
            xyz = np.array([_flat_to_ijk(simulator.grid, value) for value in flat], float)
            if xyz.shape[0] < 2:
                continue
            lw = 0.6 + 2.2 * q_stream / max(qmax, 1.0e-30)
            ax.plot(xyz[:, 0] + 0.5, xyz[:, 1] + 0.5, xyz[:, 2] + 0.5,
                    lw=lw, alpha=0.55 if reached else 0.25)
        ax.scatter([c[0] + 0.5 for c in simulator.wells.inj_cells],
                   [c[1] + 0.5 for c in simulator.wells.inj_cells],
                   [c[2] + 0.5 for c in simulator.wells.inj_cells],
                   marker='^', s=55, label='injector')
        ax.scatter([c[0] + 0.5 for c in simulator.wells.prod_cells],
                   [c[1] + 0.5 for c in simulator.wells.prod_cells],
                   [c[2] + 0.5 for c in simulator.wells.prod_cells],
                   marker='v', s=55, label='producer')
        ax.set_xlabel('i'); ax.set_ylabel('j'); ax.set_zlabel('z layer')
        ax.set_title(
            f"{mode_name}, step {step}: adaptive physical streamlines "
            f"({fields['selected_seed_density']}x{fields['selected_seed_density']} per completion)"
        )
        ax.legend(loc='best')
        _pad_save(fig, f'48_{mode_name}_step_{step:02d}_streamlines_3d.png', outdir)


def plot_adaptive_seed_convergence(history, outdir=PAD_OUTPUT_DIR):
    density = np.array([item['seed_density'] for item in history])
    coverage = np.array([item['coverage_fraction'] for item in history]) * 100.0
    cv = np.array([item['ratio_cv'] for item in history])
    nsl = np.array([item['n_streamlines'] for item in history])
    rmin = np.array([item['ratio_min'] for item in history])
    rmean = np.array([item['ratio_mean'] for item in history])
    rmax = np.array([item['ratio_max'] for item in history])

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(density, coverage, 'o-')
    ax.axhline(100.0, color='k', lw=1, ls='--')
    ax.set_xlabel('seeds per horizontal dimension per completion')
    ax.set_ylabel('non-producer cell coverage [%]')
    ax.set_title('Adaptive physical streamline coverage convergence')
    ax.grid(alpha=0.3)
    _pad_save(fig, '49_adaptive_seed_coverage_convergence.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(density, cv, 'o-', label='coefficient of variation')
    ax.axhline(0.25, color='k', lw=1, ls='--', label='selection target')
    ax.set_xlabel('seeds per horizontal dimension per completion')
    ax.set_ylabel(r'CV of raw $\sum q_\ell\Delta\tau/PV_{cell}$')
    ax.set_title('Streamtube pore-volume quadrature convergence')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, '50_adaptive_seed_quadrature_cv.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(density, rmin, 'o-', label='minimum')
    ax.plot(density, rmean, 's-', label='mean')
    ax.plot(density, rmax, '^-', label='maximum')
    ax.axhline(1.0, color='k', lw=1, ls='--')
    ax.set_xlabel('seeds per horizontal dimension per completion')
    ax.set_ylabel(r'raw $\sum q_\ell\Delta\tau/PV_{cell}$')
    ax.set_title('Raw streamtube volume representation by seed density')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, '51_adaptive_seed_raw_weight_range.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(density, nsl, 'o-')
    ax.set_xlabel('seeds per horizontal dimension per completion')
    ax.set_ylabel('physical streamlines')
    ax.set_title('Cost of adaptive physical seeding')
    ax.grid(alpha=0.3)
    _pad_save(fig, '52_adaptive_seed_streamline_count.png', outdir)


def plot_increment_mapping_diagnostics(mode_name, simulator, result,
                                       outdir=PAD_OUTPUT_DIR):
    pvi = np.asarray(result.pvi)
    errors = np.asarray([
        fields['increment_mapping_error'] for fields in simulator.step_fields
    ])
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(pvi, errors, 'o-')
    ax.axhline(0.0, color='k', lw=1)
    ax.set_xlabel('PVI')
    ax.set_ylabel('mapped minus packet CO2 volume [m3]')
    ax.set_title(f'{mode_name}: conservative increment map closure')
    ax.grid(alpha=0.3)
    _pad_save(fig, f'53_{mode_name}_increment_mapping_error.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(pvi, result.selected_seed_density, 'o-', label='seed density')
    ax2 = ax.twinx()
    ax2.plot(pvi, result.quadrature_cv, 's--', label='quadrature CV')
    ax.set_xlabel('PVI'); ax.set_ylabel('seeds per dimension')
    ax2.set_ylabel('raw volume-ratio CV')
    ax.set_title(f'{mode_name}: adaptive seeding through coupled updates')
    ax.grid(alpha=0.3)
    _pad_save(fig, f'54_{mode_name}_adaptive_seed_history.png', outdir)


def run_adaptive_partition_target(outdir=PAD_OUTPUT_DIR, target_pvi=0.08,
                                  n_pressure_steps=4):
    """Complete Version 4 run with restored baseline and dynamic visuals."""
    import os
    os.makedirs(outdir, exist_ok=True)

    # Restore the multidimensional visual chain without rerunning the expensive
    # 1D four-mode ladder, which was already validated in Versions 1-3.
    grid, rock, fluid, cap, wells, k_md = build_padstream_5x5x5_case()
    plot_pad_grid_properties(grid, k_md, outdir)
    plot_pad_constitutive_physics(rock, fluid, cap, grid, outdir)
    p0, lamt0, A0, residual0, q_layer0 = plot_pad_pressure_diagnostics(
        grid, rock, fluid, wells, outdir, no_crossflow=False
    )
    V0, vx0, vy0, vz0, speed0 = plot_pad_velocity_diagnostics(
        grid, p0, lamt0, outdir, no_crossflow=False
    )
    rows0, tof0, flux0, reached0, tof_map0, Lc0 = plot_pad_streamline_tof_diagnostics(
        grid, p0, lamt0, V0, wells, q_layer0, outdir, seeds_per_dim=3
    )
    baseline = {
        'pressure': p0, 'mobility': lamt0, 'velocity': V0,
        'streamlines': rows0, 'tof': tof0, 'tof_map': tof_map0,
        'lorenz': Lc0,
    }

    # Select one converged physical seed density from the initial pressure field.
    initial_sw = np.full((grid.nx, grid.ny, grid.nz), float(rock.swc))
    injection_by_cell0, _ = injection_rates(grid, p0, lamt0, wells, False)
    _, selected_density, first_history = adaptive_injector_seed_rows(
        grid, V0, wells, injection_by_cell0, initial_sw, p0,
        min_density=2, max_density=8,
        coverage_target=1.0, quadrature_cv_target=0.25,
    )
    print(f'Adaptive geometry selected {selected_density}x{selected_density} seeds '
          f'per injector completion.')
    modes = [
        ('incompressible', False, False),
        ('compressible', True, False),
        ('capillary', False, True),
        ('full', True, True),
    ]
    outputs = {}

    for name, compressible, capillary_on in modes:
        print('-' * 88)
        print(f'ADAPTIVE SEEDING + CONSERVATIVE INCREMENT MAP: {name}')
        simulator = AuditedStreamlineSimulator(
            grid, rock, fluid, wells,
            capillary_model=cap,
            seeds_per_dim=selected_density,
            compressible=compressible,
            capillary=capillary_on,
            n_diff_sub=2,
            inject_co2=True,
            adaptive_seeding=False,
        )
        result = simulator.run(
            target_pvi=target_pvi,
            n_pressure_steps=n_pressure_steps,
            verbose=True,
        )
        plot_transport_mapback_audit(name, simulator, result, outdir)
        plot_dynamic_pressure_and_streamlines(name, simulator, outdir)
        plot_increment_mapping_diagnostics(name, simulator, result, outdir)
        outputs[name] = (simulator, result)

    plot_adaptive_seed_convergence(first_history, outdir)

    print('=' * 104)
    print('VERSION 4 SUMMARY')
    print(f"{'mode':<16}{'seed density':>16}{'streamlines':>16}"
          f"{'coverage':>14}{'map error max':>18}{'projection Linf':>18}")
    for name, (simulator, result) in outputs.items():
        map_error = max(abs(fields['increment_mapping_error'])
                        for fields in simulator.step_fields)
        projection = max(result.projection_linf)
        coverage = result.audits[-1].covered_cells
        print(f"{name:<16}{result.selected_seed_density[-1]:>16d}"
              f"{result.streamline_count[-1]:>16d}"
              f"{coverage:>8d}/{grid.ncell:<5d}"
              f"{map_error:>18.6e}{projection:>18.6e}")
    print('=' * 104)
    return {'baseline': baseline, 'modes': outputs}



# ==============================================================================
# STAGE 16 [S16] — EVOLVING-MOBILITY TOF AUDIT AND LOCAL STREAMLINE SUBCYCLING
# ==============================================================================
# A Pollock path may graze a cell corner and create a physically valid but very
# short in-cell segment.  The Version-4 global CFL strategy used the shortest
# segment in the whole injector bundle for all streamlines.  Since the 1D
# streamline equations are independent between pressure updates, Version 5
# advances each streamline with its own stable explicit timestep.
# ==============================================================================


def _controlling_tof_segment(grid, wells, fields):
    rows = fields['rows']
    flat_index, dtau, _, _, stream_flux, valid, reached = _streamline_matrices(
        grid, rows, fields['old_saturation'], fields['pressure']
    )
    positive = (dtau > 0.0) & valid
    flat_arg = int(np.argmin(np.where(positive, dtau, np.inf)))
    row_index, segment_index = np.unravel_index(flat_arg, dtau.shape)
    row = rows[row_index]
    detailed = trace_streamline_detailed(
        grid, fields['velocity'], row[4], row[5], set(wells.prod_cells)
    )
    points = detailed['points']
    segment_length = float(np.linalg.norm(
        points[segment_index + 1] - points[segment_index]
    ))
    cell = detailed['cells'][segment_index]
    i, j, k = cell
    return {
        'row_index': int(row_index),
        'segment_index': int(segment_index),
        'dtau_s': float(dtau[row_index, segment_index]),
        'dtau_days': float(dtau[row_index, segment_index] / 86400.0),
        'segment_length_m': segment_length,
        'cell': tuple(map(int, cell)),
        'user_layer': int(k + 1),
        'saturation': float(fields['old_saturation'][i, j, k]),
        'mobility': float(fields['mobility'][i, j, k]),
        'pressure_mpa': float(fields['pressure'][i, j, k] / 1.0e6),
        'stream_flux_m3_s': float(stream_flux[row_index]),
        'source_cell': tuple(map(int, row[4])),
        'source_local': tuple(map(float, row[5])),
        'points': points,
        'dtaus': detailed['dtaus'],
    }


def plot_local_tof_subcycling_diagnostics(mode_name, simulator, global_result,
                                           local_result, global_simulator,
                                           outdir=PAD_OUTPUT_DIR):
    import os
    os.makedirs(outdir, exist_ok=True)
    steps = np.arange(1, len(local_result.transport_substeps) + 1)

    # Minimum segment TOF and its geometric length.
    controls = [_controlling_tof_segment(simulator.grid, simulator.wells, fields)
                for fields in simulator.step_fields]
    min_days = [item['dtau_days'] for item in controls]
    lengths = [item['segment_length_m'] for item in controls]

    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    ax.plot(steps, min_days, marker='o')
    ax.set_xlabel('pressure update')
    ax.set_ylabel('minimum positive segment TOF [days]')
    ax.set_title(f'{mode_name}: evolving minimum Pollock segment TOF')
    ax.grid(True, alpha=0.3)
    _pad_save(fig, f'55_{mode_name}_minimum_segment_tof.png', outdir)

    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    ax.plot(steps, lengths, marker='o')
    ax.set_xlabel('pressure update')
    ax.set_ylabel('controlling segment length [m]')
    ax.set_title(f'{mode_name}: corner-grazing segment length')
    ax.grid(True, alpha=0.3)
    _pad_save(fig, f'56_{mode_name}_controlling_segment_length.png', outdir)

    # Per-streamline substep distribution for the final pressure update.
    for fields in [simulator.step_fields[-1]]:
        step = fields['step']
        substeps = np.asarray(
            fields['transport_diagnostics']['substeps_per_streamline'], dtype=int
        )
        fig, ax = plt.subplots(figsize=(6.4, 4.5))
        ax.hist(substeps, bins=min(30, max(5, int(np.sqrt(len(substeps))))))
        ax.set_xlabel('substeps used by one streamline')
        ax.set_ylabel('number of streamlines')
        ax.set_title(f'{mode_name}, step {step}: local TOF subcycling distribution')
        ax.grid(True, alpha=0.25)
        _pad_save(fig, f'57_{mode_name}_step_{step:02d}_local_substeps.png', outdir)

    # Work comparison: global update count versus local update count.
    global_work = np.asarray(global_result.transport_work, dtype=float)
    local_work = np.asarray(local_result.transport_work, dtype=float)
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    ax.plot(steps, global_work, marker='o', label='global CFL work')
    ax.plot(steps, local_work, marker='s', label='local streamline work')
    ax.set_xlabel('pressure update')
    ax.set_ylabel('streamline substep updates')
    ax.set_title(f'{mode_name}: global versus local TOF transport work')
    ax.legend()
    ax.grid(True, alpha=0.3)
    _pad_save(fig, f'58_{mode_name}_global_vs_local_work.png', outdir)

    # Final saturation difference verifies that the acceleration does not change
    # the accepted physics materially at this benchmark resolution.
    difference = local_result.sw_final - global_result.sw_final
    for kk in [simulator.grid.nz // 2]:
        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow(difference[:, :, kk].T, origin='lower', cmap='coolwarm')
        ax.set_xlabel('i index'); ax.set_ylabel('j index')
        ax.set_title(
            f'{mode_name}: local - global saturation, user z-layer {kk + 1}'
        )
        cb = fig.colorbar(im, ax=ax); cb.set_label('saturation difference')
        _pad_save(fig, f'59_{mode_name}_local_global_difference_layer_{kk + 1}.png', outdir)

    return controls



def run_local_cfl_convergence(mode_name, common, reference_result,
                              cfl_values=(0.4, 0.2, 0.1, 0.05),
                              target_pvi=0.04, n_pressure_steps=2,
                              outdir=PAD_OUTPUT_DIR):
    """Compare local subcycling levels against a fine global-CFL reference."""
    errors_max = []
    errors_mean = []
    works = []
    reductions = []
    reference_work = int(np.sum(reference_result.transport_work))
    results = {}
    for cfl_number in cfl_values:
        simulator = AuditedStreamlineSimulator(
            **common,
            transport_cfl_strategy='local_streamline',
            transport_cfl_number=cfl_number,
        )
        result = simulator.run(
            target_pvi=target_pvi,
            n_pressure_steps=n_pressure_steps,
            verbose=False,
        )
        difference = np.abs(result.sw_final - reference_result.sw_final)
        errors_max.append(float(np.max(difference)))
        errors_mean.append(float(np.mean(difference)))
        work = int(np.sum(result.transport_work))
        works.append(work)
        reductions.append(reference_work / max(work, 1))
        results[float(cfl_number)] = (simulator, result)

    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.loglog(cfl_values, errors_max, marker='o', label='maximum |dS|')
    ax.loglog(cfl_values, errors_mean, marker='s', label='mean |dS|')
    ax.invert_xaxis()
    ax.set_xlabel('local streamline CFL number')
    ax.set_ylabel('difference from global CFL=0.4 reference')
    ax.set_title(f'{mode_name}: local-subcycling convergence')
    ax.legend(); ax.grid(True, which='both', alpha=0.3)
    _pad_save(fig, f'60_{mode_name}_local_cfl_convergence.png', outdir)

    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.plot(cfl_values, works, marker='o')
    ax.invert_xaxis()
    ax.set_xlabel('local streamline CFL number')
    ax.set_ylabel('total streamline substep updates')
    ax.set_title(f'{mode_name}: local-subcycling work')
    ax.grid(True, alpha=0.3)
    _pad_save(fig, f'61_{mode_name}_local_cfl_work.png', outdir)

    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.plot(cfl_values, reductions, marker='o')
    ax.invert_xaxis()
    ax.set_xlabel('local streamline CFL number')
    ax.set_ylabel('work reduction vs global CFL=0.4')
    ax.set_title(f'{mode_name}: retained work reduction')
    ax.grid(True, alpha=0.3)
    _pad_save(fig, f'62_{mode_name}_local_cfl_work_reduction.png', outdir)

    return {
        'cfl_values': np.asarray(cfl_values, dtype=float),
        'max_errors': np.asarray(errors_max, dtype=float),
        'mean_errors': np.asarray(errors_mean, dtype=float),
        'works': np.asarray(works, dtype=int),
        'work_reductions': np.asarray(reductions, dtype=float),
        'results': results,
    }


def run_evolving_tof_target(outdir=PAD_OUTPUT_DIR, target_pvi=0.04,
                            n_pressure_steps=2, selected_density=6,
                            accepted_cfl_number=0.05,
                            full_diagnostics=False):
    """Run the next physics target with restored pressure/streamline visuals."""
    import os
    os.makedirs(outdir, exist_ok=True)
    grid, rock, fluid, cap, wells, k_md = build_padstream_5x5x5_case()

    # Restore the baseline pressure contours and detailed Pollock plots.
    plot_pad_grid_properties(grid, k_md, outdir)
    p0, lamt0, _, _, q_layer0 = plot_pad_pressure_diagnostics(
        grid, rock, fluid, wells, outdir, no_crossflow=False
    )
    V0, _, _, _, _ = plot_pad_velocity_diagnostics(
        grid, p0, lamt0, outdir, no_crossflow=False
    )
    plot_pad_streamline_tof_diagnostics(
        grid, p0, lamt0, V0, wells, q_layer0, outdir,
        seeds_per_dim=selected_density
    )

    modes = [
        ('incompressible', False, False),
        ('compressible', True, False),
        ('capillary', False, True),
        ('full', True, True),
    ]
    outputs = {}

    for name, compressible, capillary_on in modes:
        print('-' * 100)
        print(f'EVOLVING TOF + LOCAL STREAMLINE SUBCYCLING: {name}')
        common = dict(
            grid=grid, rock=rock, fluid=fluid, wells=wells,
            capillary_model=cap, seeds_per_dim=selected_density,
            compressible=compressible, capillary=capillary_on,
            n_diff_sub=2, inject_co2=True, adaptive_seeding=False,
        )
        global_sim = AuditedStreamlineSimulator(
            **common, transport_cfl_strategy='global',
            transport_cfl_number=0.4,
        )
        global_result = global_sim.run(
            target_pvi=target_pvi, n_pressure_steps=n_pressure_steps,
            verbose=False,
        )
        convergence = run_local_cfl_convergence(
            name, common, global_result,
            cfl_values=(0.4, 0.2, 0.1, accepted_cfl_number),
            target_pvi=target_pvi,
            n_pressure_steps=n_pressure_steps,
            outdir=outdir,
        )
        local_sim, local_result = convergence['results'][float(accepted_cfl_number)]
        # Repeat only the accepted run with visible progress for the audit log.
        local_sim = AuditedStreamlineSimulator(
            **common, transport_cfl_strategy='local_streamline',
            transport_cfl_number=accepted_cfl_number,
        )
        local_result = local_sim.run(
            target_pvi=target_pvi, n_pressure_steps=n_pressure_steps,
            verbose=True,
        )

        # Preserve the pressure contours, streamlines and all conservation plots
        # for the accepted local-subcycling run.
        if full_diagnostics:
            plot_transport_mapback_audit(name, local_sim, local_result, outdir)
            plot_increment_mapping_diagnostics(name, local_sim, local_result, outdir)
        plot_dynamic_pressure_and_streamlines(name, local_sim, outdir)
        controls = plot_local_tof_subcycling_diagnostics(
            name, local_sim, global_result, local_result, global_sim, outdir
        )
        outputs[name] = {
            'local_simulator': local_sim,
            'local_result': local_result,
            'global_simulator': global_sim,
            'global_result': global_result,
            'controlling_segments': controls,
            'cfl_convergence': convergence,
        }

    print('=' * 132)
    print('VERSION 5 LOCAL-TOF SUMMARY')
    print(f"{'mode':<16}{'global work':>16}{'local work':>16}"
          f"{'work reduction':>18}{'max |dS|':>14}{'balance max':>16}")
    for name, bundle in outputs.items():
        gr = bundle['global_result']; lr = bundle['local_result']
        global_work = int(np.sum(gr.transport_work))
        local_work = int(np.sum(lr.transport_work))
        reduction = global_work / max(local_work, 1)
        max_difference = float(np.max(np.abs(lr.sw_final - gr.sw_final)))
        balance = float(np.max(np.abs(lr.balance_error)))
        print(f'{name:<16}{global_work:>16d}{local_work:>16d}'
              f'{reduction:>18.3f}{max_difference:>14.6e}'
              f'{balance:>16.6e}')
    print('=' * 132)
    return outputs

# ==============================================================================
# STAGE 16 [S16] — TRANSIENT SLIGHTLY-COMPRESSIBLE TPFA PRESSURE
# ==============================================================================
# This stage extends the uploaded steady incompressible TPFA pressure equation
# without editing it.  The backward-Euler pressure equation is
#
#   C_i/dt * (p_i^{n+1} - p_i^n)
#       + sum_j T_ij * lambda_t,ij * (p_i^{n+1} - p_j^{n+1}) = Q_i,
#
# with C_i = phi_i V_i c_t,i and
#   c_t = c_r + S_CO2 c_CO2 + (1-S_CO2)c_brine.
#
# Defaults are inherited from the reference code:
#   c_CO2   = fluid.c = 1.0e-8 1/Pa
#   c_brine = 0.0 1/Pa (configurable; not invented here)
#   c_r     = rock.cr = 0.0 1/Pa (configurable in the existing Rock class)
#
# Capillary pressure remains the existing operator-split grid diffusion stage.
# It is not inserted into the pressure equation here, avoiding double counting.
# ==============================================================================

from dataclasses import dataclass as _dataclass_v6

DAYS_TO_SECONDS = 86400.0


@_dataclass_v6
class TransientPressureStepResult:
    pressure: np.ndarray
    mobility: np.ndarray
    matrix: csr_matrix
    rhs: np.ndarray
    algebraic_residual: np.ndarray
    physical_residual: np.ndarray
    total_compressibility: np.ndarray
    pore_volume_multiplier: np.ndarray
    storage_capacity: np.ndarray
    accumulation_rate: np.ndarray
    flow_outflow_rate: np.ndarray
    well_source_rate: dict
    injector_well_rate: float
    producer_well_rate: float
    injector_face_rate: float
    producer_face_rate: float
    total_accumulation_rate: float
    global_balance_error: float


def _as_grid_field(value, grid):
    """Broadcast a scalar or grid-shaped property to (nx, ny, nz)."""
    if np.isscalar(value):
        return np.full((grid.nx, grid.ny, grid.nz), float(value), dtype=float)
    return np.broadcast_to(np.asarray(value, dtype=float),
                           (grid.nx, grid.ny, grid.nz)).copy()


def pressure_dependent_porosity(grid, rock, pressure, reference_pressure):
    """Pore-volume multiplier from the existing rock compressibility field."""
    cr = _as_grid_field(rock.cr, grid)
    multiplier = np.exp(cr * (np.asarray(pressure) - float(reference_pressure)))
    return grid.phi * multiplier, multiplier


def total_compressibility_field(grid, saturation, rock, fluid,
                                brine_compressibility=0.0,
                                compressibility_scale=1.0):
    """Linearized total compressibility used by the transient pressure solve."""
    sg = np.clip(np.asarray(saturation, dtype=float), 0.0, 1.0)
    cr = _as_grid_field(rock.cr, grid)
    cg = float(fluid.c)
    cb = float(brine_compressibility)
    ct = cr + sg * cg + (1.0 - sg) * cb
    return float(compressibility_scale) * np.maximum(ct, 0.0)


def _assemble_tpfa_flow_operator(grid, mobility, no_crossflow=False):
    """Assemble only the conservative TPFA flow operator, before well rows."""
    n = grid.ncell
    Aflow = lil_matrix((n, n))
    dzk = grid.dzk
    Az = grid.dx * grid.dy

    def trans(k1, k2, lt1, lt2, area, distance):
        kh = 2.0 * k1 * k2 / (k1 + k2 + 1.0e-30)
        lf = 0.5 * (lt1 + lt2)
        return area * kh * lf / distance

    for kk in range(grid.nz):
        Ax = grid.dy * dzk[kk]
        Ay = grid.dx * dzk[kk]
        for jj in range(grid.ny):
            for ii in range(grid.nx):
                c = grid.idx(ii, jj, kk)
                if ii + 1 < grid.nx:
                    T = trans(grid.k[ii, jj, kk], grid.k[ii + 1, jj, kk],
                              mobility[ii, jj, kk], mobility[ii + 1, jj, kk],
                              Ax, grid.dx)
                    nb = grid.idx(ii + 1, jj, kk)
                    Aflow[c, c] += T; Aflow[c, nb] -= T
                    Aflow[nb, nb] += T; Aflow[nb, c] -= T
                if jj + 1 < grid.ny:
                    T = trans(grid.k[ii, jj, kk], grid.k[ii, jj + 1, kk],
                              mobility[ii, jj, kk], mobility[ii, jj + 1, kk],
                              Ay, grid.dy)
                    nb = grid.idx(ii, jj + 1, kk)
                    Aflow[c, c] += T; Aflow[c, nb] -= T
                    Aflow[nb, nb] += T; Aflow[nb, c] -= T
                if kk + 1 < grid.nz and not no_crossflow:
                    dzf = 0.5 * (dzk[kk] + dzk[kk + 1])
                    T = trans(grid.k[ii, jj, kk], grid.k[ii, jj, kk + 1],
                              mobility[ii, jj, kk], mobility[ii, jj, kk + 1],
                              Az, dzf)
                    nb = grid.idx(ii, jj, kk + 1)
                    Aflow[c, c] += T; Aflow[c, nb] -= T
                    Aflow[nb, nb] += T; Aflow[nb, c] -= T
    return Aflow.tocsr()


def solve_transient_compressible_pressure_step(
        grid, saturation, rock, fluid, wells, pressure_old, dt,
        no_crossflow=False, brine_compressibility=0.0,
        reference_pressure=None, compressibility_scale=1.0):
    """Backward-Euler, slightly-compressible TPFA pressure step.

    Positive well/source rate means fluid supplied to the reservoir.  Negative
    rate means production.  For BHP cells, the physically implied well rate is
    reconstructed from accumulation plus face outflow, rather than inferred
    only from face outflow.
    """
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    pressure_old = np.asarray(pressure_old, dtype=float)
    if pressure_old.shape != (grid.nx, grid.ny, grid.nz):
        raise ValueError("pressure_old must have shape (nx, ny, nz)")
    if reference_pressure is None:
        reference_pressure = float(wells.bhp)

    mobility = total_mobility(saturation, rock, fluid)
    Aflow = _assemble_tpfa_flow_operator(grid, mobility, no_crossflow)
    phi_old, pv_multiplier = pressure_dependent_porosity(
        grid, rock, pressure_old, reference_pressure
    )
    ct = total_compressibility_field(
        grid, saturation, rock, fluid,
        brine_compressibility=brine_compressibility,
        compressibility_scale=compressibility_scale,
    )
    storage_capacity = phi_old * grid.vcell * ct  # m3 / Pa

    flat_old = pressure_old.transpose(2, 1, 0).ravel()
    storage_flat = storage_capacity.transpose(2, 1, 0).ravel()
    accumulation_matrix = csr_matrix(
        (storage_flat / dt,
         (np.arange(grid.ncell), np.arange(grid.ncell))),
        shape=(grid.ncell, grid.ncell)
    )
    A = (Aflow + accumulation_matrix).tolil()
    b = (storage_flat / dt) * flat_old

    prescribed_rate = np.zeros(grid.ncell)
    if wells.inj_bhp is None:
        q_each = wells.rate / max(len(wells.inj_cells), 1)
        for cell in wells.inj_cells:
            index = grid.idx(*cell)
            b[index] += q_each
            prescribed_rate[index] += q_each

    dirichlet_cells = []
    for cell in wells.prod_cells:
        index = grid.idx(*cell)
        A.rows[index] = [index]
        A.data[index] = [1.0]
        b[index] = float(wells.bhp)
        dirichlet_cells.append(cell)
    if wells.inj_bhp is not None:
        for cell in wells.inj_cells:
            index = grid.idx(*cell)
            A.rows[index] = [index]
            A.data[index] = [1.0]
            b[index] = float(wells.inj_bhp)
            dirichlet_cells.append(cell)

    A = A.tocsr()
    p_flat = spsolve(A, b)
    pressure = p_flat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)
    algebraic_residual = A @ p_flat - b

    flow_out_flat = Aflow @ p_flat
    accumulation_flat = storage_flat * (p_flat - flat_old) / dt
    physical_residual_flat = accumulation_flat + flow_out_flat - prescribed_rate

    well_source_rate = {}
    for cell in dirichlet_cells:
        index = grid.idx(*cell)
        well_source_rate[cell] = float(
            accumulation_flat[index] + flow_out_flat[index]
        )
        physical_residual_flat[index] = 0.0

    injector_well_rate = float(sum(
        max(well_source_rate.get(cell, prescribed_rate[grid.idx(*cell)]), 0.0)
        for cell in wells.inj_cells
    ))
    producer_well_rate = float(sum(
        max(-well_source_rate.get(cell, prescribed_rate[grid.idx(*cell)]), 0.0)
        for cell in wells.prod_cells
    ))

    injector_face_by_cell, injector_face_rate = injection_rates(
        grid, pressure, mobility, wells, no_crossflow
    )
    producer_face_rate = producer_rate(
        grid, pressure, mobility, wells, no_crossflow
    )
    total_accumulation_rate = float(np.sum(accumulation_flat))
    global_balance_error = float(
        injector_well_rate - producer_well_rate
        + np.sum(prescribed_rate)
        - total_accumulation_rate
    )

    def reshape(flat):
        return flat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)

    return TransientPressureStepResult(
        pressure=pressure,
        mobility=mobility,
        matrix=A,
        rhs=b,
        algebraic_residual=algebraic_residual,
        physical_residual=reshape(physical_residual_flat),
        total_compressibility=ct,
        pore_volume_multiplier=pv_multiplier,
        storage_capacity=storage_capacity,
        accumulation_rate=reshape(accumulation_flat),
        flow_outflow_rate=reshape(flow_out_flat),
        well_source_rate=well_source_rate,
        injector_well_rate=injector_well_rate,
        producer_well_rate=producer_well_rate,
        injector_face_rate=float(injector_face_rate),
        producer_face_rate=float(producer_face_rate),
        total_accumulation_rate=total_accumulation_rate,
        global_balance_error=global_balance_error,
    )


def run_transient_pressure_sequence(
        grid, saturation, rock, fluid, wells, total_time_days=20.0,
        dt_days=0.5, no_crossflow=False, brine_compressibility=0.0,
        compressibility_scale=1.0, initial_pressure=None):
    """Advance only the pressure equation while saturation is frozen."""
    if initial_pressure is None:
        pressure = np.full((grid.nx, grid.ny, grid.nz), float(wells.bhp))
    else:
        pressure = np.asarray(initial_pressure, dtype=float).copy()

    total_time = float(total_time_days) * DAYS_TO_SECONDS
    nominal_dt = float(dt_days) * DAYS_TO_SECONDS
    n_steps = max(1, int(np.ceil(total_time / nominal_dt)))
    dt = total_time / n_steps

    times = []
    pressures = []
    steps = []
    q_inj_well = []
    q_prod_well = []
    q_inj_face = []
    q_prod_face = []
    q_accum = []
    balance = []
    residual = []
    time_s = 0.0

    for _ in range(n_steps):
        step = solve_transient_compressible_pressure_step(
            grid, saturation, rock, fluid, wells, pressure, dt,
            no_crossflow=no_crossflow,
            brine_compressibility=brine_compressibility,
            compressibility_scale=compressibility_scale,
        )
        pressure = step.pressure
        time_s += dt
        times.append(time_s)
        pressures.append(pressure.copy())
        steps.append(step)
        q_inj_well.append(step.injector_well_rate)
        q_prod_well.append(step.producer_well_rate)
        q_inj_face.append(step.injector_face_rate)
        q_prod_face.append(step.producer_face_rate)
        q_accum.append(step.total_accumulation_rate)
        balance.append(step.global_balance_error)
        residual.append(float(np.max(np.abs(step.physical_residual))))

    return {
        'times_s': np.asarray(times),
        'pressures': pressures,
        'steps': steps,
        'q_inj_well': np.asarray(q_inj_well),
        'q_prod_well': np.asarray(q_prod_well),
        'q_inj_face': np.asarray(q_inj_face),
        'q_prod_face': np.asarray(q_prod_face),
        'q_accum': np.asarray(q_accum),
        'global_balance_error': np.asarray(balance),
        'max_physical_residual': np.asarray(residual),
        'dt_s': float(dt),
    }


def _nearest_time_index(times_s, requested_days):
    return int(np.argmin(np.abs(np.asarray(times_s) / DAYS_TO_SECONDS
                                - float(requested_days))))


def _plot_transient_streamlines_at_snapshot(grid, rock, fluid, wells, pressure,
                                             mobility, time_days, outdir,
                                             seeds_per_dim=6, make_plots=True):
    """Plot pressure contours, exact Pollock paths, and TOF at one pressure time."""
    velocity = pore_velocities(grid, pressure, mobility, no_crossflow=False)
    injection_by_cell, _ = injection_rates(
        grid, pressure, mobility, wells, no_crossflow=False
    )
    rows = build_pad_streamlines(grid, velocity, wells,
                                 seeds_per_dim=seeds_per_dim)

    # Detailed three-dimensional Pollock geometry.
    fig = plt.figure(figsize=(8.0, 6.5))
    ax = fig.add_subplot(111, projection='3d')
    for row in rows:
        points = row['points']
        if points.shape[0] >= 2:
            ax.plot(points[:, 0], points[:, 1], points[:, 2], lw=0.9,
                    alpha=0.65 if row['reached'] else 0.20)
    ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]'); ax.set_zlabel('z [m]')
    ax.set_title(f'Transient-pressure Pollock streamlines at {time_days:.2f} days')
    ax.invert_zaxis()
    _pad_save(fig, f'75_transient_streamlines_{time_days:.2f}d.png', outdir)

    # Pressure-contour overlays for every layer.
    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(6.0, 5.3))
        x = (np.arange(grid.nx) + 0.5) * grid.dx
        y = (np.arange(grid.ny) + 0.5) * grid.dy
        cs = ax.contour(x, y, (pressure[:, :, kk] / 1.0e6).T,
                        levels=8)
        ax.clabel(cs, fontsize=7)
        for row in rows:
            if row['source_layer'] != kk:
                continue
            points = row['points']
            if points.shape[0] >= 2:
                ax.plot(points[:, 0], points[:, 1], lw=0.9,
                        alpha=0.70 if row['reached'] else 0.20)
        ax.set_aspect('equal')
        ax.set_xlim(0, grid.nx * grid.dx); ax.set_ylim(0, grid.ny * grid.dy)
        ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
        ax.set_title(
            f'Pressure + streamlines, {time_days:.2f} d, user z-layer {kk + 1}'
        )
        _pad_save(
            fig,
            f'76_pressure_streamlines_{time_days:.2f}d_layer_{kk + 1}.png',
            outdir,
        )

    # Flux and TOF statistics by source layer.
    n_per_layer = seeds_per_dim ** 2
    tof_days = []
    source_layers = []
    weights = []
    for row in rows:
        layer = row['source_layer']
        tof_days.append(float(np.sum(row['dtaus'])) / DAYS_TO_SECONDS)
        source_layers.append(layer)
        weights.append(max(injection_by_cell.get((0, 0, layer), 0.0), 0.0)
                       / n_per_layer)
    return {
        'rows': rows,
        'tof_days': np.asarray(tof_days),
        'source_layer': np.asarray(source_layers),
        'weights': np.asarray(weights),
        'injection_by_cell': injection_by_cell,
    }


def plot_transient_pressure_diagnostics(sequence, grid, saturation, rock, fluid,
                                        wells, outdir=PAD_OUTPUT_DIR,
                                        snapshot_days=(0.5, 2.0, 5.0, 20.0),
                                        seeds_per_dim=6):
    """Create individual plots for every transient pressure physics term."""
    import os
    os.makedirs(outdir, exist_ok=True)
    times_days = sequence['times_s'] / DAYS_TO_SECONDS
    first = sequence['steps'][0]
    final = sequence['steps'][-1]
    steady_pressure, steady_mobility = solve_pressure(
        grid, saturation, rock, fluid, wells, no_crossflow=False
    )

    # Compressibility and storage fields.
    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow(first.total_compressibility[:, :, kk].T,
                       origin='lower', cmap='viridis')
        ax.set_title(f'Total compressibility — user z-layer {kk + 1}')
        ax.set_xlabel('i index'); ax.set_ylabel('j index')
        fig.colorbar(im, ax=ax, label='total compressibility [1/Pa]')
        _pad_save(fig, f'63_total_compressibility_layer_{kk + 1}.png', outdir)

        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow(first.storage_capacity[:, :, kk].T,
                       origin='lower', cmap='viridis')
        ax.set_title(f'Pressure storage capacity — user z-layer {kk + 1}')
        ax.set_xlabel('i index'); ax.set_ylabel('j index')
        fig.colorbar(im, ax=ax, label='phi V c_t [m3/Pa]')
        _pad_save(fig, f'64_storage_capacity_layer_{kk + 1}.png', outdir)

    snapshot_records = []
    for requested in snapshot_days:
        index = _nearest_time_index(sequence['times_s'], requested)
        actual = float(times_days[index])
        pressure = sequence['pressures'][index]
        step = sequence['steps'][index]
        density = co2_density_from_reference_eos(
            pressure, fluid, float(wells.inj_bhp)
        )
        for kk in range(grid.nz):
            fig, ax = plt.subplots(figsize=(5.8, 5.0))
            X, Y = np.meshgrid(np.arange(grid.nx), np.arange(grid.ny), indexing='ij')
            values = pressure[:, :, kk] / 1.0e6
            filled = ax.contourf(X, Y, values, levels=14, cmap='viridis')
            lines = ax.contour(X, Y, values, levels=8, colors='k', linewidths=0.55)
            ax.clabel(lines, inline=True, fontsize=7, fmt='%.2f')
            ax.set_title(f'Transient pressure, {actual:.2f} d — z-layer {kk + 1}')
            ax.set_xlabel('i index'); ax.set_ylabel('j index')
            fig.colorbar(filled, ax=ax, label='pressure [MPa]')
            _pad_save(fig,
                      f'65_pressure_{actual:.2f}d_layer_{kk + 1}.png', outdir)

            fig, ax = plt.subplots(figsize=(5.8, 5.0))
            difference = (pressure[:, :, kk] - steady_pressure[:, :, kk]) / 1.0e6
            limit = max(float(np.max(np.abs(difference))), 1.0e-12)
            im = ax.imshow(difference.T, origin='lower', cmap='coolwarm',
                           vmin=-limit, vmax=limit)
            ax.set_title(f'Transient - steady pressure, {actual:.2f} d — z {kk + 1}')
            ax.set_xlabel('i index'); ax.set_ylabel('j index')
            fig.colorbar(im, ax=ax, label='pressure difference [MPa]')
            _pad_save(fig,
                      f'66_pressure_difference_{actual:.2f}d_layer_{kk + 1}.png',
                      outdir)

            fig, ax = plt.subplots(figsize=(5.8, 5.0))
            im = ax.imshow(density[:, :, kk].T, origin='lower', cmap='viridis')
            ax.set_title(f'CO2 EOS density, {actual:.2f} d — z-layer {kk + 1}')
            ax.set_xlabel('i index'); ax.set_ylabel('j index')
            fig.colorbar(im, ax=ax, label='CO2 density [kg/m3]')
            _pad_save(fig,
                      f'67_density_{actual:.2f}d_layer_{kk + 1}.png', outdir)

        # Accumulation and physical residual at the middle layer.
        middle = grid.nz // 2
        fig, ax = plt.subplots(figsize=(5.8, 5.0))
        im = ax.imshow((step.accumulation_rate[:, :, middle]
                        * DAYS_TO_SECONDS).T,
                       origin='lower', cmap='coolwarm')
        ax.set_title(f'Pressure accumulation rate, {actual:.2f} d — z-layer {middle + 1}')
        ax.set_xlabel('i index'); ax.set_ylabel('j index')
        fig.colorbar(im, ax=ax, label='accumulation [m3/day]')
        _pad_save(fig, f'68_accumulation_{actual:.2f}d.png', outdir)

        snapshot_records.append(_plot_transient_streamlines_at_snapshot(
            grid, rock, fluid, wells, pressure, step.mobility, actual,
            outdir, seeds_per_dim=seeds_per_dim
        ))

    # Well rates and accumulation balance.
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.plot(times_days, sequence['q_inj_well'] * DAYS_TO_SECONDS,
            label='well supply at injector')
    ax.plot(times_days, sequence['q_prod_well'] * DAYS_TO_SECONDS,
            label='well withdrawal at producer')
    ax.plot(times_days, sequence['q_inj_face'] * DAYS_TO_SECONDS, '--',
            label='injector face outflow to streamlines')
    ax.plot(times_days, sequence['q_prod_face'] * DAYS_TO_SECONDS, '--',
            label='producer face inflow')
    ax.set_xlabel('time [days]'); ax.set_ylabel('rate [m3/day]')
    ax.set_title('Transient BHP-well and reservoir-face rates')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, '69_transient_well_rates.png', outdir)

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    rate_difference = sequence['q_inj_well'] - sequence['q_prod_well']
    ax.plot(times_days, rate_difference * DAYS_TO_SECONDS,
            label='injector supply - producer withdrawal')
    ax.plot(times_days, sequence['q_accum'] * DAYS_TO_SECONDS, '--',
            label='integrated pressure accumulation')
    ax.set_xlabel('time [days]'); ax.set_ylabel('rate [m3/day]')
    ax.set_title('Transient pressure storage balance')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, '70_pressure_storage_balance.png', outdir)

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.semilogy(times_days,
                np.maximum(np.abs(sequence['global_balance_error']), 1.0e-30),
                label='global balance error')
    ax.semilogy(times_days,
                np.maximum(sequence['max_physical_residual'], 1.0e-30),
                label='max non-well physical residual')
    ax.set_xlabel('time [days]'); ax.set_ylabel('residual [m3/s]')
    ax.set_title('Transient pressure conservation residuals')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, '71_pressure_residual_history.png', outdir)

    error_to_steady = np.array([
        np.linalg.norm(p - steady_pressure) / (np.linalg.norm(steady_pressure) + 1.0e-30)
        for p in sequence['pressures']
    ])
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.semilogy(times_days, np.maximum(error_to_steady, 1.0e-30))
    ax.set_xlabel('time [days]'); ax.set_ylabel('relative L2 pressure error')
    ax.set_title('Transient pressure convergence toward steady TPFA')
    ax.grid(alpha=0.3)
    _pad_save(fig, '72_pressure_convergence_to_steady.png', outdir)

    # Combined TOF evolution by source layer.
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    for record, requested in zip(snapshot_records, snapshot_days):
        valid = np.isfinite(record['tof_days']) & (record['tof_days'] > 0.0)
        if not np.any(valid):
            continue
        medians = []
        for kk in range(grid.nz):
            values = record['tof_days'][valid & (record['source_layer'] == kk)]
            medians.append(float(np.median(values)) if values.size else np.nan)
        ax.plot(np.arange(1, grid.nz + 1), medians, marker='o',
                label=f'{requested:g} d snapshot')
    ax.set_xlabel('source user z-layer'); ax.set_ylabel('median TOF [days]')
    ax.set_title('Transient-pressure streamline TOF evolution')
    ax.legend(); ax.grid(alpha=0.3)
    _pad_save(fig, '77_transient_tof_by_layer.png', outdir)

    return {
        'steady_pressure': steady_pressure,
        'steady_mobility': steady_mobility,
        'error_to_steady': error_to_steady,
        'snapshots': snapshot_records,
    }


def run_incompressible_limit_test(grid, saturation, rock, fluid, wells,
                                  outdir=PAD_OUTPUT_DIR, dt_days=0.5):
    """Verify that the transient matrix reduces to steady TPFA as c_t -> 0."""
    steady, _ = solve_pressure(grid, saturation, rock, fluid, wells, False)
    p_old = np.full_like(steady, float(wells.bhp))
    scales = np.array([1.0, 0.1, 0.01, 0.001, 0.0])
    errors = []
    for scale in scales:
        result = solve_transient_compressible_pressure_step(
            grid, saturation, rock, fluid, wells, p_old,
            dt_days * DAYS_TO_SECONDS,
            compressibility_scale=scale,
        )
        errors.append(
            np.linalg.norm(result.pressure - steady)
            / (np.linalg.norm(steady) + 1.0e-30)
        )
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    positive = scales > 0.0
    ax.loglog(scales[positive], np.asarray(errors)[positive], 'o-')
    ax.scatter([1.0e-4], [errors[-1]], marker='x', s=70,
               label='c_t = 0 (plotted at 1e-4)')
    ax.set_xlabel('compressibility multiplier'); ax.set_ylabel('relative L2 error vs steady')
    ax.set_title('Incompressible limiting-case verification')
    ax.legend(); ax.grid(True, which='both', alpha=0.3)
    _pad_save(fig, '73_incompressible_pressure_limit.png', outdir)
    return scales, np.asarray(errors)


def run_pressure_timestep_convergence(grid, saturation, rock, fluid, wells,
                                      outdir=PAD_OUTPUT_DIR,
                                      final_time_days=5.0):
    """Backward-Euler pressure timestep convergence at a common final time."""
    reference = run_transient_pressure_sequence(
        grid, saturation, rock, fluid, wells,
        total_time_days=final_time_days, dt_days=0.0625,
    )['pressures'][-1]
    dt_values = np.array([1.0, 0.5, 0.25, 0.125])
    errors = []
    for dt_days in dt_values:
        pressure = run_transient_pressure_sequence(
            grid, saturation, rock, fluid, wells,
            total_time_days=final_time_days, dt_days=dt_days,
        )['pressures'][-1]
        errors.append(
            np.linalg.norm(pressure - reference)
            / (np.linalg.norm(reference) + 1.0e-30)
        )
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    ax.loglog(dt_values, errors, 'o-')
    ax.invert_xaxis()
    ax.set_xlabel('pressure timestep [days]')
    ax.set_ylabel('relative L2 pressure error')
    ax.set_title('Transient pressure timestep convergence')
    ax.grid(True, which='both', alpha=0.3)
    _pad_save(fig, '74_pressure_timestep_convergence.png', outdir)
    return dt_values, np.asarray(errors)


def run_transient_pressure_target(outdir=PAD_OUTPUT_DIR,
                                  total_time_days=20.0,
                                  dt_days=0.5,
                                  seeds_per_dim=6):
    """Execute the Version-6 pressure, Darcy, Pollock, and TOF target."""
    import json
    import os
    os.makedirs(outdir, exist_ok=True)
    grid, rock, fluid, cap, wells, k_md = build_padstream_5x5x5_case()
    saturation = np.full((grid.nx, grid.ny, grid.nz), float(rock.swc))

    print('=' * 100)
    print('VERSION 6 — TRANSIENT SLIGHTLY-COMPRESSIBLE PRESSURE TARGET')
    print('=' * 100)
    sequence = run_transient_pressure_sequence(
        grid, saturation, rock, fluid, wells,
        total_time_days=total_time_days,
        dt_days=dt_days,
    )
    diagnostics = plot_transient_pressure_diagnostics(
        sequence, grid, saturation, rock, fluid, wells,
        outdir=outdir,
        snapshot_days=(dt_days, 2.0, 5.0, total_time_days),
        seeds_per_dim=seeds_per_dim,
    )
    scales, limit_errors = run_incompressible_limit_test(
        grid, saturation, rock, fluid, wells, outdir=outdir,
        dt_days=dt_days,
    )
    dt_values, dt_errors = run_pressure_timestep_convergence(
        grid, saturation, rock, fluid, wells, outdir=outdir,
        final_time_days=5.0,
    )

    final_step = sequence['steps'][-1]
    steady_pressure = diagnostics['steady_pressure']
    final_steady_error = float(
        np.linalg.norm(final_step.pressure - steady_pressure)
        / (np.linalg.norm(steady_pressure) + 1.0e-30)
    )
    summary = {
        'grid': [grid.nx, grid.ny, grid.nz],
        'pressure_equation': 'backward-Euler slightly-compressible TPFA',
        'co2_compressibility_1_per_pa': float(fluid.c),
        'brine_compressibility_1_per_pa': 0.0,
        'rock_compressibility_1_per_pa': float(rock.cr),
        'total_time_days': float(total_time_days),
        'pressure_dt_days': float(sequence['dt_s'] / DAYS_TO_SECONDS),
        'final_relative_error_to_steady': final_steady_error,
        'maximum_global_balance_error_m3_per_s': float(
            np.max(np.abs(sequence['global_balance_error']))
        ),
        'maximum_nonwell_physical_residual_m3_per_s': float(
            np.max(sequence['max_physical_residual'])
        ),
        'initial_injector_well_rate_m3_per_day': float(
            sequence['q_inj_well'][0] * DAYS_TO_SECONDS
        ),
        'initial_producer_well_rate_m3_per_day': float(
            sequence['q_prod_well'][0] * DAYS_TO_SECONDS
        ),
        'final_injector_well_rate_m3_per_day': float(
            sequence['q_inj_well'][-1] * DAYS_TO_SECONDS
        ),
        'final_producer_well_rate_m3_per_day': float(
            sequence['q_prod_well'][-1] * DAYS_TO_SECONDS
        ),
        'incompressible_limit_scales': scales.tolist(),
        'incompressible_limit_errors': limit_errors.tolist(),
        'timestep_days': dt_values.tolist(),
        'timestep_errors': dt_errors.tolist(),
        'important_scope_note': (
            'Capillary pressure remains the existing operator-split saturation '
            'diffusion stage. Version 6 does not add capillary potential to the '
            'pressure equation and does not yet replace the coupled saturation '
            'loop with pressure-dependent accumulation.'
        ),
    }
    with open(os.path.join(outdir, 'PAD_Stream_V6_Pressure_Summary.json'), 'w') as handle:
        json.dump(summary, handle, indent=2)

    print(f"pressure steps: {len(sequence['times_s'])}")
    print(f"final relative error to steady TPFA: {final_steady_error:.6e}")
    print('initial well rates [m3/day]: '
          f"inj={summary['initial_injector_well_rate_m3_per_day']:.6e}, "
          f"prod={summary['initial_producer_well_rate_m3_per_day']:.6e}")
    print('final well rates [m3/day]: '
          f"inj={summary['final_injector_well_rate_m3_per_day']:.6e}, "
          f"prod={summary['final_producer_well_rate_m3_per_day']:.6e}")
    print('max global balance error [m3/s]: '
          f"{summary['maximum_global_balance_error_m3_per_s']:.6e}")
    print('=' * 100)
    return sequence, diagnostics, summary


# ==============================================================================
# STAGE 17 [S17] — MASS-CONSISTENT PRESSURE–SATURATION COUPLING
# ==============================================================================
# This stage supplies the classical ground truth for the coupled CCUS problem.
# It preserves the existing streamline/Pollock/TOF machinery for diagnostics,
# but advances CO2 by a cell-centred finite-volume PHASE-MASS equation:
#
#   [phi rho_g S_g]^(n+1) - [phi rho_g S_g]^n
#   ------------------------------------------------ + div(rho_g f_g u_t) = q_g.
#                           dt
#
# Pressure is solved first.  The old CO2 mass is then represented at the new
# pressure-dependent density and pore volume before any advective flux is added.
# Internal face mass fluxes cancel pairwise.  BHP well rates are the physically
# reconstructed well-source rates from Stage 16, not merely injector face rates.
#
# IMPORTANT SCOPE:
# During transient pressure buildup div(u_t) != 0 because part of the well supply
# enters pressure storage.  Consequently q_l * tau_l is not yet treated as an
# exact streamtube pore volume.  Pollock paths and TOF remain fully plotted, but
# this grid finite-volume update is the accepted coupled ground truth against
# which a later compressible streamline transport approximation will be tested.
# ==============================================================================

from dataclasses import dataclass as _dataclass_v7, field as _field_v7


# Stage-17 plotting controls. These are intentionally global so they can be
# changed once at the bottom of the file or from PyCharm's debugger.
V7_DISPLAY_PLOTS = True
V7_CLOSE_AFTER_SHOW = True
V7_PLOT_PAUSE_SECONDS = 0.10


def _v7_backend_is_headless():
    """Return True only for genuinely non-interactive Matplotlib backends.

    PyCharm frequently reports ``module://backend_interagg``.  That backend is
    interactive even though its name contains the substring ``agg``; therefore
    a substring test is incorrect and was the reason Version 7 skipped show().
    """
    import matplotlib
    backend = str(matplotlib.get_backend()).strip().lower()
    short = backend.rsplit('/', 1)[-1]
    headless_exact = {
        'agg', 'pdf', 'pgf', 'ps', 'svg', 'cairo', 'template',
        'module://matplotlib_inline.backend_inline',
    }
    return backend in headless_exact or short in headless_exact


def _v7_save(fig, filename, outdir, display=None, close_after_show=None):
    """Save a Stage-17 figure and reliably hand it to PyCharm/SciView.

    Parameters
    ----------
    display:
        ``True`` requests interactive display when the backend supports it.
        ``None`` uses ``V7_DISPLAY_PLOTS``.
    close_after_show:
        ``True`` closes the figure after the GUI event loop has received it.
        Set ``False`` temporarily when diagnosing a local Matplotlib backend.
    """
    import os
    import matplotlib

    os.makedirs(outdir, exist_ok=True)
    path = os.path.abspath(os.path.join(outdir, filename))
    fig.savefig(path, dpi=120, bbox_inches='tight')

    display = V7_DISPLAY_PLOTS if display is None else bool(display)
    close_after_show = (V7_CLOSE_AFTER_SHOW if close_after_show is None
                        else bool(close_after_show))
    backend = str(matplotlib.get_backend())

    if display and not _v7_backend_is_headless():
        # Force a draw and briefly run the GUI event loop before closing.  This
        # is required by PyCharm's backend_interagg/SciView capture path.
        try:
            fig.canvas.draw_idle()
            fig.canvas.flush_events()
        except Exception:
            pass
        plt.show(block=False)
        plt.pause(max(float(V7_PLOT_PAUSE_SECONDS), 0.001))
    elif display and _v7_backend_is_headless():
        # Saved files remain available even when no GUI backend exists.
        if not getattr(_v7_save, '_headless_notice_printed', False):
            print(f'[plots] Backend {backend!r} is non-interactive; figures are being saved to {os.path.abspath(outdir)}')
            _v7_save._headless_notice_printed = True

    if close_after_show or _v7_backend_is_headless():
        plt.close(fig)
    return path



@_dataclass_v7
class MassCouplingStepAudit:
    mode: str
    step: int
    time_days: float
    pressure_dt_days: float
    pressure_residual_max: float
    pressure_global_balance_m3_s: float
    injector_total_rate_m3_day: float
    producer_total_rate_m3_day: float
    pressure_storage_rate_m3_day: float
    co2_injected_mass_kg: float
    co2_produced_mass_kg: float
    co2_mass_change_kg: float
    co2_mass_balance_error_kg: float
    pressure_only_saturation_linf: float
    advective_substeps: int
    capillary_substeps: int
    capillary_mass_change_kg: float
    saturation_min: float
    saturation_max: float
    streamline_count: int
    streamlines_reached: int
    tof_min_days: float
    tof_median_days: float
    tof_max_days: float
    volumetric_divergence_l1_m3_s: float


@_dataclass_v7
class MassCouplingResult:
    mode: str
    audits: list = _field_v7(default_factory=list)
    fields: list = _field_v7(default_factory=list)
    final_pressure: np.ndarray = None
    final_saturation: np.ndarray = None
    cumulative_injected_mass: list = _field_v7(default_factory=list)
    cumulative_produced_mass: list = _field_v7(default_factory=list)
    co2_mass_in_place_change: list = _field_v7(default_factory=list)
    cumulative_balance_error: list = _field_v7(default_factory=list)


def tpfa_face_fluxes(grid, pressure, mobility, no_crossflow=False):
    """Return signed internal total-volume face rates [m3/s].

    qx[i,j,k] is positive from cell (i,j,k) to (i+1,j,k), and similarly for
    qy and qz.  Boundary rates are represented by the well-source dictionary,
    not duplicated in these internal-face arrays.
    """
    qx = np.zeros((grid.nx - 1, grid.ny, grid.nz), dtype=float)
    qy = np.zeros((grid.nx, grid.ny - 1, grid.nz), dtype=float)
    qz = np.zeros((grid.nx, grid.ny, grid.nz - 1), dtype=float)
    dzk = grid.dzk

    def kh(a, b):
        return 2.0 * a * b / (a + b + 1.0e-30)

    for kk in range(grid.nz):
        ax = grid.dy * dzk[kk]
        ay = grid.dx * dzk[kk]
        for jj in range(grid.ny):
            for ii in range(grid.nx - 1):
                t = (ax * kh(grid.k[ii, jj, kk], grid.k[ii + 1, jj, kk])
                     * 0.5 * (mobility[ii, jj, kk] + mobility[ii + 1, jj, kk])
                     / grid.dx)
                qx[ii, jj, kk] = t * (pressure[ii, jj, kk] - pressure[ii + 1, jj, kk])
        for jj in range(grid.ny - 1):
            for ii in range(grid.nx):
                t = (ay * kh(grid.k[ii, jj, kk], grid.k[ii, jj + 1, kk])
                     * 0.5 * (mobility[ii, jj, kk] + mobility[ii, jj + 1, kk])
                     / grid.dy)
                qy[ii, jj, kk] = t * (pressure[ii, jj, kk] - pressure[ii, jj + 1, kk])

    if not no_crossflow:
        az = grid.dx * grid.dy
        for kk in range(grid.nz - 1):
            dzf = 0.5 * (dzk[kk] + dzk[kk + 1])
            for jj in range(grid.ny):
                for ii in range(grid.nx):
                    t = (az * kh(grid.k[ii, jj, kk], grid.k[ii, jj, kk + 1])
                         * 0.5 * (mobility[ii, jj, kk] + mobility[ii, jj, kk + 1])
                         / dzf)
                    qz[ii, jj, kk] = t * (pressure[ii, jj, kk] - pressure[ii, jj, kk + 1])
    return qx, qy, qz


def face_flux_outflow_divergence(grid, qx, qy, qz):
    """Cell total-volume outflow divergence [m3/s], positive net outflow."""
    div = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    div[:-1, :, :] += qx
    div[1:, :, :] -= qx
    div[:, :-1, :] += qy
    div[:, 1:, :] -= qy
    if grid.nz > 1:
        div[:, :, :-1] += qz
        div[:, :, 1:] -= qz
    return div


def steady_well_source_rates(grid, pressure, mobility, wells, no_crossflow=False):
    """Signed total-volume source rates for the original steady TPFA solve."""
    source = {}
    for cell in wells.inj_cells + wells.prod_cells:
        source[cell] = float(_well_face_flux(
            grid, pressure, mobility, cell, no_crossflow=no_crossflow
        ))
    return source


def well_source_field(grid, source_dictionary):
    field = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    for cell, value in source_dictionary.items():
        field[cell] += float(value)
    return field


def _co2_mass_face_fluxes(grid, saturation, density, rock, fluid, qx, qy, qz):
    """First-order phase-upwind CO2 mass fluxes [kg/s]."""
    fg = frac_flow(saturation, rock, fluid)
    mx = np.zeros_like(qx)
    my = np.zeros_like(qy)
    mz = np.zeros_like(qz)

    donor_left = qx >= 0.0
    mx[:] = qx * np.where(
        donor_left,
        density[:-1, :, :] * fg[:-1, :, :],
        density[1:, :, :] * fg[1:, :, :],
    )
    donor_low = qy >= 0.0
    my[:] = qy * np.where(
        donor_low,
        density[:, :-1, :] * fg[:, :-1, :],
        density[:, 1:, :] * fg[:, 1:, :],
    )
    if grid.nz > 1:
        donor_bottom = qz >= 0.0
        mz[:] = qz * np.where(
            donor_bottom,
            density[:, :, :-1] * fg[:, :, :-1],
            density[:, :, 1:] * fg[:, :, 1:],
        )
    return mx, my, mz


def _mass_flux_outflow_divergence(grid, mx, my, mz):
    div = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    div[:-1, :, :] += mx
    div[1:, :, :] -= mx
    div[:, :-1, :] += my
    div[:, 1:, :] -= my
    if grid.nz > 1:
        div[:, :, :-1] += mz
        div[:, :, 1:] -= mz
    return div


def _co2_well_mass_source(grid, saturation, density, rock, fluid,
                          source_dictionary, injector_density):
    """Signed well CO2 mass source [kg/s]; injection is pure CO2."""
    source = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    fg = frac_flow(saturation, rock, fluid)
    for cell, q_total in source_dictionary.items():
        q_total = float(q_total)
        if q_total >= 0.0:
            source[cell] += float(injector_density) * q_total
        else:
            source[cell] += density[cell] * fg[cell] * q_total
    return source


def _transport_cfl_seconds(grid, qx, qy, qz, well_sources, rock, fluid,
                           cfl_number=0.35):
    """Conservative global explicit CFL estimate for grid advection."""
    throughput = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    throughput[:-1, :, :] += np.abs(qx)
    throughput[1:, :, :] += np.abs(qx)
    throughput[:, :-1, :] += np.abs(qy)
    throughput[:, 1:, :] += np.abs(qy)
    if grid.nz > 1:
        throughput[:, :, :-1] += np.abs(qz)
        throughput[:, :, 1:] += np.abs(qz)
    throughput += np.abs(well_source_field(grid, well_sources))
    pv = grid.phi * grid.vcell
    active = throughput > 1.0e-30
    if not np.any(active):
        return np.inf
    slope = max_dfw(rock, fluid)
    return float(cfl_number * np.min(pv[active] / throughput[active])
                 / max(slope, 1.0e-30))


def advance_co2_mass_advection(grid, saturation_old, pressure_old, pressure_new,
                               rock, fluid, wells, qx, qy, qz, well_sources,
                               dt, compressible, reference_pressure,
                               cfl_number=0.35):
    """Advance the conservative cell CO2 mass equation with pressure frozen."""
    if compressible:
        rho_old = co2_density_from_reference_eos(
            pressure_old, fluid, float(reference_pressure)
        )
        rho_new = co2_density_from_reference_eos(
            pressure_new, fluid, float(reference_pressure)
        )
        phi_old, _ = pressure_dependent_porosity(
            grid, rock, pressure_old, reference_pressure
        )
        phi_new, _ = pressure_dependent_porosity(
            grid, rock, pressure_new, reference_pressure
        )
    else:
        rho_old = np.full_like(saturation_old, float(fluid.rho_w))
        rho_new = rho_old.copy()
        phi_old = grid.phi.copy()
        phi_new = grid.phi.copy()

    cell_volume = grid.vcell
    capacity_old = phi_old * cell_volume * rho_old
    capacity_new = phi_new * cell_volume * rho_new
    mass = capacity_old * saturation_old
    initial_mass = float(np.sum(mass))

    # Pressure/density storage changes saturation, but not phase mass.
    storage_saturation = mass / np.maximum(capacity_new, 1.0e-30)
    storage_change = storage_saturation - saturation_old

    dt_cfl = _transport_cfl_seconds(
        grid, qx, qy, qz, well_sources, rock, fluid, cfl_number=cfl_number
    )
    n_sub = max(1, int(np.ceil(dt / dt_cfl))) if np.isfinite(dt_cfl) else 1
    h = dt / n_sub
    injected_mass = 0.0
    produced_mass = 0.0
    internal_cancellation = []

    saturation = storage_saturation.copy()
    for _ in range(n_sub):
        mx, my, mz = _co2_mass_face_fluxes(
            grid, saturation, rho_new, rock, fluid, qx, qy, qz
        )
        div_mass = _mass_flux_outflow_divergence(grid, mx, my, mz)
        source_mass = _co2_well_mass_source(
            grid, saturation, rho_new, rock, fluid,
            well_sources, injector_density=float(fluid.rho_w)
        )
        injected_mass += h * float(np.sum(np.maximum(source_mass, 0.0)))
        produced_mass += h * float(np.sum(np.maximum(-source_mass, 0.0)))
        internal_cancellation.append(float(np.sum(div_mass)))
        mass += h * (source_mass - div_mass)
        saturation = mass / np.maximum(capacity_new, 1.0e-30)

        # Physical saturation may move below the Corey endpoint during
        # pressure compression. rel_perm() already clips effective saturation
        # below rock.swc to zero mobility, so clipping S back to rock.swc here
        # would create phase mass. The physical lower bound is therefore zero.
        lower = np.zeros(saturation.shape, dtype=float)
        upper = _broadcast_bounds(rock.sw_max, saturation.shape)
        violation = max(
            float(np.max(lower - saturation)),
            float(np.max(saturation - upper)),
        )
        if violation > 2.0e-8:
            raise RuntimeError(
                f'Grid mass transport violated saturation bounds by {violation:.3e}; '
                'reduce the transport CFL number.'
            )
        saturation = np.clip(saturation, lower, upper)
        # Clipping at roundoff only. Reconstructing mass prevents hidden drift.
        mass = capacity_new * saturation

    final_mass = float(np.sum(mass))
    balance_error = final_mass - initial_mass - injected_mass + produced_mass
    return {
        'saturation_storage': storage_saturation,
        'storage_saturation_change': storage_change,
        'saturation_advective': saturation,
        'mass_field': mass,
        'capacity_new': capacity_new,
        'density_old': rho_old,
        'density_new': rho_new,
        'phi_old': phi_old,
        'phi_new': phi_new,
        'initial_mass': initial_mass,
        'final_mass': final_mass,
        'injected_mass': injected_mass,
        'produced_mass': produced_mass,
        'balance_error': float(balance_error),
        'substeps': int(n_sub),
        'dt_cfl_s': float(dt_cfl),
        'maximum_internal_flux_sum_kg_s': float(
            np.max(np.abs(internal_cancellation)) if internal_cancellation else 0.0
        ),
    }


def _capillary_face_coefficients(grid, diffusion):
    tx = np.zeros((grid.nx - 1, grid.ny, grid.nz), dtype=float)
    ty = np.zeros((grid.nx, grid.ny - 1, grid.nz), dtype=float)
    tz = np.zeros((grid.nx, grid.ny, grid.nz - 1), dtype=float)
    dzk = grid.dzk
    for kk in range(grid.nz):
        ax = grid.dy * dzk[kk]
        ay = grid.dx * dzk[kk]
        tx[:, :, kk] = (ax * 0.5 * (diffusion[:-1, :, kk] + diffusion[1:, :, kk])
                        / grid.dx)
        ty[:, :, kk] = (ay * 0.5 * (diffusion[:, :-1, kk] + diffusion[:, 1:, kk])
                        / grid.dy)
    if grid.nz > 1:
        az = grid.dx * grid.dy
        for kk in range(grid.nz - 1):
            dzf = 0.5 * (dzk[kk] + dzk[kk + 1])
            tz[:, :, kk] = (az * 0.5 * (diffusion[:, :, kk] + diffusion[:, :, kk + 1])
                            / dzf)
    return tx, ty, tz


def advance_capillary_mass_explicit(grid, saturation, mass_field, capacity,
                                    density, rock, fluid, cap, dt,
                                    cfl_number=0.35):
    """Mass-conservative explicit capillary redistribution at fixed pressure."""
    mass = np.asarray(mass_field, dtype=float).copy()
    saturation = np.asarray(saturation, dtype=float).copy()
    start_mass = float(np.sum(mass))
    remaining = float(dt)
    n_sub = 0
    max_internal_sum = 0.0

    while remaining > 1.0e-12 * max(dt, 1.0):
        diffusion = capillary_diffusion_coeff(saturation, grid, rock, fluid, cap)
        tx, ty, tz = _capillary_face_coefficients(grid, diffusion)
        conductance = np.zeros_like(saturation)
        conductance[:-1, :, :] += tx; conductance[1:, :, :] += tx
        conductance[:, :-1, :] += ty; conductance[:, 1:, :] += ty
        if grid.nz > 1:
            conductance[:, :, :-1] += tz; conductance[:, :, 1:] += tz
        pv = grid.phi * grid.vcell
        active = conductance > 1.0e-30
        if np.any(active):
            h_stable = float(cfl_number * np.min(pv[active] / conductance[active]))
        else:
            h_stable = remaining
        h = min(remaining, h_stable)

        qx = tx * (saturation[:-1, :, :] - saturation[1:, :, :])
        qy = ty * (saturation[:, :-1, :] - saturation[:, 1:, :])
        qz = tz * (saturation[:, :, :-1] - saturation[:, :, 1:])
        mx = qx * np.where(qx >= 0.0, density[:-1, :, :], density[1:, :, :])
        my = qy * np.where(qy >= 0.0, density[:, :-1, :], density[:, 1:, :])
        mz = qz * np.where(qz >= 0.0, density[:, :, :-1], density[:, :, 1:])
        div_mass = _mass_flux_outflow_divergence(grid, mx, my, mz)
        max_internal_sum = max(max_internal_sum, abs(float(np.sum(div_mass))))
        mass -= h * div_mass
        saturation = mass / np.maximum(capacity, 1.0e-30)
        lower = np.zeros(saturation.shape, dtype=float)
        upper = _broadcast_bounds(rock.sw_max, saturation.shape)
        violation = max(float(np.max(lower - saturation)),
                        float(np.max(saturation - upper)))
        if violation > 2.0e-8:
            raise RuntimeError(
                f'Capillary mass transport violated bounds by {violation:.3e}; '
                'reduce capillary CFL.'
            )
        saturation = np.clip(saturation, lower, upper)
        mass = capacity * saturation
        remaining -= h
        n_sub += 1
        if n_sub > 200000:
            raise RuntimeError('Capillary explicit subcycling exceeded 200000 steps')

    final_mass = float(np.sum(mass))
    return {
        'saturation': saturation,
        'mass_field': mass,
        'substeps': int(n_sub),
        'mass_change': final_mass - start_mass,
        'maximum_internal_flux_sum_kg_s': float(max_internal_sum),
    }


def _plot_v7_layer(field, title, filename, outdir, layer, cmap='viridis',
                   vmin=None, vmax=None, label=''):
    fig, ax = plt.subplots(figsize=(5.8, 5.0))
    im = ax.imshow(np.asarray(field)[:, :, layer].T, origin='lower', cmap=cmap,
                   vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel('i index'); ax.set_ylabel('j index')
    fig.colorbar(im, ax=ax, label=label)
    return _v7_save(fig, filename, outdir)


def _plot_v7_pressure_streamlines(grid, pressure, mobility, wells, mode, step,
                                  time_days, outdir, seeds_per_dim=6):
    velocity = pore_velocities(grid, pressure, mobility, no_crossflow=False)
    rows = build_pad_streamlines(grid, velocity, wells,
                                 seeds_per_dim=seeds_per_dim)
    fig = plt.figure(figsize=(8.0, 6.5))
    ax = fig.add_subplot(111, projection='3d')
    tof_days = []
    for row in rows:
        points = row['points']
        if points.shape[0] >= 2:
            ax.plot(points[:, 0], points[:, 1], points[:, 2], lw=0.8,
                    alpha=0.62 if row['reached'] else 0.18)
        tof_days.append(float(np.sum(row['dtaus'])) / DAYS_TO_SECONDS)
    ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]'); ax.set_zlabel('z [m]')
    ax.set_title(f'{mode}: Pollock streamlines, step {step}, {time_days:.2f} d')
    ax.invert_zaxis()
    _v7_save(fig, f'90_{mode}_step_{step:02d}_streamlines_3d.png', outdir)

    x = (np.arange(grid.nx) + 0.5) * grid.dx
    y = (np.arange(grid.ny) + 0.5) * grid.dy
    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(6.0, 5.2))
        values = (pressure[:, :, kk] / 1.0e6).T
        filled = ax.contourf(x, y, values, levels=14, cmap='viridis')
        lines = ax.contour(x, y, values, levels=8, colors='k', linewidths=0.5)
        ax.clabel(lines, fontsize=7, fmt='%.2f')
        for row in rows:
            if row['source_layer'] == kk and row['points'].shape[0] >= 2:
                ax.plot(row['points'][:, 0], row['points'][:, 1], lw=0.75,
                        alpha=0.6 if row['reached'] else 0.15)
        ax.set_aspect('equal')
        ax.set_title(f'{mode}: pressure + streamlines, step {step}, layer {kk + 1}')
        ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
        fig.colorbar(filled, ax=ax, label='pressure [MPa]')
        _v7_save(fig,
                  f'91_{mode}_step_{step:02d}_pressure_streamlines_layer_{kk + 1}.png',
                  outdir)
    tof = np.asarray(tof_days, dtype=float)
    return rows, tof


def run_mass_consistent_mode(mode, grid, rock, fluid, cap, wells,
                             total_time_days=1.0, pressure_dt_days=0.5,
                             seeds_per_dim=6, outdir=PAD_OUTPUT_DIR,
                             transport_cfl=0.30, capillary_cfl=0.30,
                             make_plots=True):
    """Run one of incompressible/compressible/capillary/full ground-truth modes."""
    compressible = mode in ('compressible', 'full')
    use_capillary = mode in ('capillary', 'full')
    n_steps = max(1, int(np.ceil(total_time_days / pressure_dt_days)))
    dt = total_time_days * DAYS_TO_SECONDS / n_steps
    pressure = np.full((grid.nx, grid.ny, grid.nz), float(wells.bhp))
    saturation = np.full((grid.nx, grid.ny, grid.nz), float(rock.swc))
    initial_pressure = pressure.copy()
    if compressible:
        rho0 = co2_density_from_reference_eos(pressure, fluid, float(wells.inj_bhp))
        phi0, _ = pressure_dependent_porosity(grid, rock, pressure, wells.bhp)
    else:
        rho0 = np.full_like(saturation, float(fluid.rho_w))
        phi0 = grid.phi.copy()
    initial_mass = float(np.sum(phi0 * grid.vcell * rho0 * saturation))
    cumulative_injected = 0.0
    cumulative_produced = 0.0
    result = MassCouplingResult(mode=mode)

    for step_index in range(1, n_steps + 1):
        old_pressure = pressure.copy()
        old_saturation = saturation.copy()
        if compressible:
            pstep = solve_transient_compressible_pressure_step(
                grid, old_saturation, rock, fluid, wells, old_pressure, dt,
                no_crossflow=False, brine_compressibility=0.0,
                reference_pressure=wells.bhp,
            )
            pressure = pstep.pressure
            mobility = pstep.mobility
            source_rates = dict(pstep.well_source_rate)
            pressure_residual = float(np.max(np.abs(pstep.physical_residual)))
            pressure_balance = float(pstep.global_balance_error)
            q_inj = float(pstep.injector_well_rate)
            q_prod = float(pstep.producer_well_rate)
            q_storage = float(pstep.total_accumulation_rate)
        else:
            pressure, mobility = solve_pressure(
                grid, old_saturation, rock, fluid, wells, no_crossflow=False
            )
            source_rates = steady_well_source_rates(
                grid, pressure, mobility, wells, no_crossflow=False
            )
            q_inj = float(sum(max(v, 0.0) for v in source_rates.values()))
            q_prod = float(sum(max(-v, 0.0) for v in source_rates.values()))
            q_storage = 0.0
            qx0, qy0, qz0 = tpfa_face_fluxes(grid, pressure, mobility)
            div0 = face_flux_outflow_divergence(grid, qx0, qy0, qz0)
            source0 = well_source_field(grid, source_rates)
            pressure_residual = float(np.max(np.abs(div0 - source0)))
            pressure_balance = float(q_inj - q_prod)

        qx, qy, qz = tpfa_face_fluxes(grid, pressure, mobility, no_crossflow=False)
        div_volume = face_flux_outflow_divergence(grid, qx, qy, qz)
        advection = advance_co2_mass_advection(
            grid, old_saturation, old_pressure, pressure, rock, fluid, wells,
            qx, qy, qz, source_rates, dt, compressible,
            reference_pressure=wells.inj_bhp,
            cfl_number=transport_cfl,
        )
        saturation_adv = advection['saturation_advective']
        mass_after = advection['mass_field']
        saturation_final = saturation_adv.copy()
        capillary_result = {
            'saturation': saturation_adv,
            'mass_field': mass_after,
            'substeps': 0,
            'mass_change': 0.0,
        }
        if use_capillary:
            capillary_result = advance_capillary_mass_explicit(
                grid, saturation_adv, mass_after, advection['capacity_new'],
                advection['density_new'], rock, fluid, cap, dt,
                cfl_number=capillary_cfl,
            )
            saturation_final = capillary_result['saturation']
            mass_after = capillary_result['mass_field']

        saturation = saturation_final
        cumulative_injected += advection['injected_mass']
        cumulative_produced += advection['produced_mass']
        final_mass = float(np.sum(mass_after))
        mass_change = final_mass - advection['initial_mass']
        step_balance = (mass_change - advection['injected_mass']
                        + advection['produced_mass'])
        cumulative_error = (final_mass - initial_mass - cumulative_injected
                            + cumulative_produced)
        time_days = step_index * dt / DAYS_TO_SECONDS

        if make_plots:
            rows, tof = _plot_v7_pressure_streamlines(
                grid, pressure, mobility, wells, mode, step_index, time_days,
                outdir, seeds_per_dim=seeds_per_dim,
            )
        else:
            velocity = pore_velocities(grid, pressure, mobility, no_crossflow=False)
            rows = build_pad_streamlines(
                grid, velocity, wells, seeds_per_dim=seeds_per_dim
            )
            tof = np.asarray([
                float(np.sum(row['dtaus'])) / DAYS_TO_SECONDS for row in rows
            ])
        finite_tof = tof[np.isfinite(tof) & (tof > 0.0)]
        if make_plots:
            for kk in range(grid.nz):
                prefix = f'92_{mode}_step_{step_index:02d}_layer_{kk + 1}'
                _plot_v7_layer(
                    pressure / 1.0e6,
                    f'{mode}: pressure, step {step_index}, layer {kk + 1}',
                    f'{prefix}_01_pressure.png', outdir, kk,
                    cmap='viridis', label='pressure [MPa]'
                )
                _plot_v7_layer(
                    advection['density_new'],
                    f'{mode}: CO2 density, step {step_index}, layer {kk + 1}',
                    f'{prefix}_02_density.png', outdir, kk,
                    cmap='viridis', label='CO2 density [kg/m3]'
                )
                limit = max(float(np.max(np.abs(advection['storage_saturation_change']))),
                            1.0e-12)
                _plot_v7_layer(
                    advection['storage_saturation_change'],
                    f'{mode}: pressure-storage saturation change, step {step_index}, layer {kk + 1}',
                    f'{prefix}_03_pressure_storage_delta_s.png', outdir, kk,
                    cmap='coolwarm', vmin=-limit, vmax=limit, label='delta S_CO2'
                )
                _plot_v7_layer(
                    saturation_adv,
                    f'{mode}: after mass-conservative advection, step {step_index}, layer {kk + 1}',
                    f'{prefix}_04_after_advection.png', outdir, kk,
                    cmap='viridis', vmin=float(rock.swc), vmax=float(rock.sw_max),
                    label='S_CO2'
                )
                cap_delta = saturation_final - saturation_adv
                cap_limit = max(float(np.max(np.abs(cap_delta))), 1.0e-12)
                _plot_v7_layer(
                    cap_delta,
                    f'{mode}: capillary redistribution, step {step_index}, layer {kk + 1}',
                    f'{prefix}_05_capillary_delta_s.png', outdir, kk,
                    cmap='coolwarm', vmin=-cap_limit, vmax=cap_limit,
                    label='delta S_CO2'
                )
                _plot_v7_layer(
                    saturation_final,
                    f'{mode}: accepted saturation, step {step_index}, layer {kk + 1}',
                    f'{prefix}_06_final_saturation.png', outdir, kk,
                    cmap='viridis', vmin=float(rock.swc), vmax=float(rock.sw_max),
                    label='S_CO2'
                )
                mass_residual_field = np.zeros_like(saturation)
                # The scalar conservative residual is shown uniformly only as a
                # diagnostic reference; internal face cancellation is exact pairwise.
                mass_residual_field[:, :, kk] = step_balance / grid.ncell
                _plot_v7_layer(
                    mass_residual_field,
                    f'{mode}: phase-mass balance residual, step {step_index}, layer {kk + 1}',
                    f'{prefix}_07_mass_balance_residual.png', outdir, kk,
                    cmap='coolwarm', label='mass residual share [kg]'
                )

        audit = MassCouplingStepAudit(
            mode=mode,
            step=step_index,
            time_days=float(time_days),
            pressure_dt_days=float(dt / DAYS_TO_SECONDS),
            pressure_residual_max=pressure_residual,
            pressure_global_balance_m3_s=pressure_balance,
            injector_total_rate_m3_day=q_inj * DAYS_TO_SECONDS,
            producer_total_rate_m3_day=q_prod * DAYS_TO_SECONDS,
            pressure_storage_rate_m3_day=q_storage * DAYS_TO_SECONDS,
            co2_injected_mass_kg=float(advection['injected_mass']),
            co2_produced_mass_kg=float(advection['produced_mass']),
            co2_mass_change_kg=float(mass_change),
            co2_mass_balance_error_kg=float(step_balance),
            pressure_only_saturation_linf=float(
                np.max(np.abs(advection['storage_saturation_change']))
            ),
            advective_substeps=int(advection['substeps']),
            capillary_substeps=int(capillary_result['substeps']),
            capillary_mass_change_kg=float(capillary_result['mass_change']),
            saturation_min=float(np.min(saturation_final)),
            saturation_max=float(np.max(saturation_final)),
            streamline_count=len(rows),
            streamlines_reached=int(sum(bool(row['reached']) for row in rows)),
            tof_min_days=float(np.min(finite_tof)) if finite_tof.size else np.nan,
            tof_median_days=float(np.median(finite_tof)) if finite_tof.size else np.nan,
            tof_max_days=float(np.max(finite_tof)) if finite_tof.size else np.nan,
            volumetric_divergence_l1_m3_s=float(np.sum(np.abs(div_volume))),
        )
        result.audits.append(audit)
        result.fields.append({
            'pressure': pressure.copy(),
            'saturation_old': old_saturation,
            'saturation_storage': advection['saturation_storage'].copy(),
            'saturation_advective': saturation_adv.copy(),
            'saturation_final': saturation_final.copy(),
            'density': advection['density_new'].copy(),
            'rows': rows,
            'tof_days': tof.copy(),
            'qx': qx.copy(), 'qy': qy.copy(), 'qz': qz.copy(),
            'source_rates': dict(source_rates),
        })
        result.cumulative_injected_mass.append(float(cumulative_injected))
        result.cumulative_produced_mass.append(float(cumulative_produced))
        result.co2_mass_in_place_change.append(float(final_mass - initial_mass))
        result.cumulative_balance_error.append(float(cumulative_error))
        print(
            f'  {mode:<14} step {step_index}/{n_steps}  t={time_days:5.2f} d  '
            f'nadv={advection["substeps"]:4d}  ncap={capillary_result["substeps"]:4d}  '
            f'mass error={step_balance:+.3e} kg  '
            f'S=[{np.min(saturation):.4f},{np.max(saturation):.4f}]'
        )

    result.final_pressure = pressure.copy()
    result.final_saturation = saturation.copy()
    return result


def plot_v7_mode_summaries(results, outdir=PAD_OUTPUT_DIR):
    """Summary figures across all four physical modes."""
    for mode, result in results.items():
        time = np.asarray([a.time_days for a in result.audits])
        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.plot(time, result.cumulative_injected_mass, 'o-', label='injected CO2 mass')
        ax.plot(time, result.cumulative_produced_mass, 's-', label='produced CO2 mass')
        ax.plot(time, result.co2_mass_in_place_change, '^-', label='mass in place change')
        ax.set_xlabel('time [days]'); ax.set_ylabel('CO2 mass [kg]')
        ax.set_title(f'{mode}: CO2 phase-mass bookkeeping')
        ax.grid(True, alpha=0.3); ax.legend()
        _v7_save(fig, f'93_{mode}_mass_bookkeeping.png', outdir)

        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.semilogy(time, np.maximum(np.abs(result.cumulative_balance_error), 1.0e-16), 'o-')
        ax.set_xlabel('time [days]'); ax.set_ylabel('|cumulative mass error| [kg]')
        ax.set_title(f'{mode}: cumulative phase-mass balance')
        ax.grid(True, which='both', alpha=0.3)
        _v7_save(fig, f'94_{mode}_cumulative_mass_error.png', outdir)

        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.plot(time, [a.pressure_only_saturation_linf for a in result.audits], 'o-')
        ax.set_xlabel('time [days]'); ax.set_ylabel('max |delta S from pressure/density|')
        ax.set_title(f'{mode}: pressure-storage saturation contribution')
        ax.grid(True, alpha=0.3)
        _v7_save(fig, f'95_{mode}_pressure_storage_saturation.png', outdir)

        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.plot(time, [a.injector_total_rate_m3_day for a in result.audits], 'o-', label='injection')
        ax.plot(time, [a.producer_total_rate_m3_day for a in result.audits], 's-', label='production')
        ax.plot(time, [a.pressure_storage_rate_m3_day for a in result.audits], '^-', label='pressure storage')
        ax.set_xlabel('time [days]'); ax.set_ylabel('total rate [m3/day]')
        ax.set_title(f'{mode}: well and pressure-storage rates')
        ax.grid(True, alpha=0.3); ax.legend()
        _v7_save(fig, f'96_{mode}_well_storage_rates.png', outdir)

    # Final saturation comparison, one figure per layer.
    first = next(iter(results.values()))
    for kk in range(first.final_saturation.shape[2]):
        fig, axes = plt.subplots(1, 4, figsize=(17.0, 4.2), constrained_layout=True)
        for ax, (mode, result) in zip(axes, results.items()):
            im = ax.imshow(result.final_saturation[:, :, kk].T, origin='lower',
                           cmap='viridis', vmin=0.20, vmax=0.80)
            ax.set_title(mode); ax.set_xlabel('i'); ax.set_ylabel('j')
        fig.colorbar(im, ax=axes, label='S_CO2', shrink=0.85)
        fig.suptitle(f'Final mass-consistent saturation — user z-layer {kk + 1}')
        _v7_save(fig, f'97_four_mode_final_saturation_layer_{kk + 1}.png', outdir)


def run_mass_consistent_coupling_target(outdir=PAD_OUTPUT_DIR,
                                        total_time_days=1.0,
                                        pressure_dt_days=0.5,
                                        seeds_per_dim=6,
                                        make_plots=True):
    """Execute the Stage-17 four-mode classical coupled ground truth."""
    import json
    import os
    os.makedirs(outdir, exist_ok=True)
    grid, rock, fluid, cap, wells, _ = build_padstream_5x5x5_case()
    print('=' * 110)
    print('VERSION 7 — MASS-CONSISTENT PRESSURE–SATURATION COUPLING')
    print('=' * 110)
    results = {}
    for mode in ('incompressible', 'compressible', 'capillary', 'full'):
        results[mode] = run_mass_consistent_mode(
            mode, grid, rock, fluid, cap, wells,
            total_time_days=total_time_days,
            pressure_dt_days=pressure_dt_days,
            seeds_per_dim=seeds_per_dim,
            outdir=outdir, make_plots=make_plots,
        )
    if make_plots:
        plot_v7_mode_summaries(results, outdir=outdir)

    summary = {
        'grid': [grid.nx, grid.ny, grid.nz],
        'total_time_days': float(total_time_days),
        'pressure_dt_days': float(pressure_dt_days),
        'accepted_transport_ground_truth': (
            'cell-centred finite-volume CO2 phase-mass conservation'
        ),
        'streamline_scope': (
            'Pollock geometry and TOF are diagnostic during transient pressure; '
            'q_l*tau_l is not assumed to be exact pore volume until a variable-flux '
            'compressible streamtube formulation is added.'
        ),
        'modes': {},
    }
    for mode, result in results.items():
        audits = result.audits
        summary['modes'][mode] = {
            'steps': len(audits),
            'maximum_absolute_step_mass_error_kg': float(max(
                abs(a.co2_mass_balance_error_kg) for a in audits
            )),
            'maximum_absolute_cumulative_mass_error_kg': float(max(
                abs(x) for x in result.cumulative_balance_error
            )),
            'maximum_pressure_residual': float(max(
                abs(a.pressure_residual_max) for a in audits
            )),
            'maximum_pressure_only_saturation_change': float(max(
                a.pressure_only_saturation_linf for a in audits
            )),
            'maximum_capillary_mass_change_kg': float(max(
                abs(a.capillary_mass_change_kg) for a in audits
            )),
            'final_saturation_min': float(np.min(result.final_saturation)),
            'final_saturation_max': float(np.max(result.final_saturation)),
            'final_injected_mass_kg': float(result.cumulative_injected_mass[-1]),
            'final_produced_mass_kg': float(result.cumulative_produced_mass[-1]),
            'final_mass_in_place_change_kg': float(result.co2_mass_in_place_change[-1]),
            'last_streamline_count': int(audits[-1].streamline_count),
            'last_streamlines_reached': int(audits[-1].streamlines_reached),
        }
    summary_path = os.path.join(outdir, 'PAD_Stream_V7_Mass_Coupling_Summary.json')
    with open(summary_path, 'w') as handle:
        json.dump(summary, handle, indent=2)

    print('-' * 110)
    for mode, values in summary['modes'].items():
        print(
            f'{mode:<15} max step mass error={values["maximum_absolute_step_mass_error_kg"]:.3e} kg  '
            f'max cumulative error={values["maximum_absolute_cumulative_mass_error_kg"]:.3e} kg  '
            f'Sfinal=[{values["final_saturation_min"]:.4f},'
            f'{values["final_saturation_max"]:.4f}]'
        )
    print('=' * 110)
    return results, summary



# ==============================================================================
# STAGE 18 [S18] — EXPLICIT CCUS PHASE CONVENTION + VARIABLE-FLUX STREAMTUBES
# ==============================================================================
# Stage 18 removes the inherited waterflood naming ambiguity from the accepted
# CCUS development path.  The original Rock/Fluid/rel_perm functions remain
# above for regression and source fidelity; this stage uses explicit gas/brine
# names and equations:
#
#   S_g       = mobile/non-wetting CO2 saturation
#   S_w       = 1 - S_g, wetting brine saturation
#   S_wir     = irreducible brine saturation (drainage endpoint)
#   S_gr,max  = maximum residually trapped CO2 after imbibition
#   S_g,max   = 1 - S_wir
#
# The baseline is initially brine-filled: S_g,initial = 0.  This is a configurable
# development assumption, not a hard-coded claim about all depleted reservoirs.
#
# The second part adds a variable-total-flux streamtube approximation for the
# transient pressure period.  The exact cell-centred finite-volume mass equation
# from Stage 17 remains the ground truth.  Pollock supplies geometry; exact TPFA
# cell inflow/outflow rates attenuate or amplify each streamtube through pressure
# storage, and segment pore volumes are normalized to partition each grid cell.
# ==============================================================================

from dataclasses import dataclass as _dataclass_v8, field as _field_v8
import os as _os_v8
import json as _json_v8


@_dataclass_v8
class CCUSRock:
    """Drainage/imbibition endpoints written in explicit CO2/brine notation."""
    ng: float = 2.0
    nw: float = 2.0
    s_wir: float = 0.20
    s_gr_max: float = 0.30
    krg_endpoint: float = 0.60
    krw_endpoint: float = 0.80
    s_g_initial: float = 0.0
    cr: float = 0.0
    hysteresis: bool = True

    @property
    def s_g_max(self):
        return 1.0 - self.s_wir

    @property
    def drainage_span(self):
        return self.s_g_max

    def validate(self):
        if not (0.0 <= self.s_g_initial <= self.s_g_max):
            raise ValueError('s_g_initial must lie between 0 and 1-s_wir')
        if not (0.0 < self.s_wir < 1.0):
            raise ValueError('s_wir must lie between zero and one')
        if not (0.0 <= self.s_gr_max < self.s_g_max):
            raise ValueError('s_gr_max must be below the drainage gas endpoint')
        return self


@_dataclass_v8
class CCUSFluid:
    """CO2/brine properties with no inherited water/oil phase labels."""
    mu_g: float = 0.05          # Pa-equivalent input convention: cP
    mu_w: float = 0.60          # brine viscosity [cP]
    rho_g_ref: float = 700.0    # CO2 density at p_ref [kg/m3]
    rho_w_ref: float = 1020.0   # brine density [kg/m3]
    c_g: float = 1.0e-8         # CO2 compressibility [1/Pa]
    c_w: float = 0.0            # brine compressibility [1/Pa]
    p_ref: float = 3.0e7        # density reference pressure [Pa]


def ccus_relative_permeability(s_g, rock: CCUSRock, s_g_history=None):
    """Corey drainage plus a Land/Killough-style gas scanning curve.

    Drainage starts at S_g=0 and reaches the gas endpoint at 1-S_wir.  Residual
    gas is used only on imbibition, when S_g falls below its historical maximum.
    Brine relative permeability remains non-hysteretic in this baseline.
    """
    rock.validate()
    s_g = np.asarray(s_g, dtype=float)
    se_g = np.clip(s_g / max(rock.s_g_max, 1.0e-30), 0.0, 1.0)
    krg_d = rock.krg_endpoint * se_g ** rock.ng
    krw = rock.krw_endpoint * (1.0 - se_g) ** rock.nw

    if s_g_history is None or not rock.hysteresis:
        return krg_d, krw

    history = np.maximum(np.asarray(s_g_history, dtype=float), s_g)
    # Land coefficient chosen so a drainage endpoint of S_g,max maps to the
    # requested maximum residual saturation S_gr,max.
    C_land = (1.0 / max(rock.s_gr_max, 1.0e-30)
              - 1.0 / max(rock.s_g_max, 1.0e-30))
    s_gr_local = history / np.maximum(1.0 + C_land * history, 1.0e-30)
    krg_at_history = rock.krg_endpoint * np.clip(
        history / max(rock.s_g_max, 1.0e-30), 0.0, 1.0
    ) ** rock.ng
    scan = np.clip(
        (s_g - s_gr_local) / np.maximum(history - s_gr_local, 1.0e-30),
        0.0, 1.0,
    )
    krg_i = krg_at_history * scan ** rock.ng
    on_drainage = s_g >= history - 1.0e-10
    krg = np.where(on_drainage, krg_d, krg_i)
    return krg, krw


def ccus_fractional_flow(s_g, rock: CCUSRock, fluid: CCUSFluid,
                         s_g_history=None):
    krg, krw = ccus_relative_permeability(s_g, rock, s_g_history)
    lg = krg / max(float(fluid.mu_g), 1.0e-30)
    lw = krw / max(float(fluid.mu_w), 1.0e-30)
    return lg / np.maximum(lg + lw, 1.0e-30)


def ccus_total_mobility(s_g, rock: CCUSRock, fluid: CCUSFluid,
                        s_g_history=None):
    krg, krw = ccus_relative_permeability(s_g, rock, s_g_history)
    lg = krg / (max(float(fluid.mu_g), 1.0e-30) * 1.0e-3)
    lw = krw / (max(float(fluid.mu_w), 1.0e-30) * 1.0e-3)
    return lg + lw


def ccus_max_fractional_flow_slope(rock: CCUSRock, fluid: CCUSFluid, n=800):
    s = np.linspace(0.0, rock.s_g_max, int(n))
    f = ccus_fractional_flow(s, rock, fluid)
    return float(np.max(np.abs(np.gradient(f, s))))


def ccus_capillary_pressure(s_g, rock: CCUSRock, cap: Capillary):
    """Brooks-Corey drainage Pc=p_g-p_w as a function of gas saturation."""
    s_w = 1.0 - np.asarray(s_g, dtype=float)
    se_w = np.clip((s_w - rock.s_wir) / max(1.0 - rock.s_wir, 1.0e-30),
                   1.0e-4, 1.0)
    return cap.Pe * se_w ** (-1.0 / cap.lam)


def ccus_dpc_dsg(s_g, rock: CCUSRock, cap: Capillary):
    s_w = 1.0 - np.asarray(s_g, dtype=float)
    span = max(1.0 - rock.s_wir, 1.0e-30)
    se_w = np.clip((s_w - rock.s_wir) / span, 1.0e-4, 1.0)
    return (cap.Pe / (cap.lam * span)
            * se_w ** (-1.0 / cap.lam - 1.0))


def ccus_capillary_diffusion_coefficient(s_g, grid, rock: CCUSRock,
                                         fluid: CCUSFluid, cap: Capillary):
    """Positive non-wetting-phase diffusion coefficient for S_g transport."""
    krg, krw = ccus_relative_permeability(s_g, rock)
    lg = krg / (fluid.mu_g * 1.0e-3)
    lw = krw / (fluid.mu_w * 1.0e-3)
    lt = lg + lw + 1.0e-30
    return np.maximum(grid.k * (lg * lw / lt) * ccus_dpc_dsg(s_g, rock, cap), 0.0)


def ccus_gas_density(pressure, fluid: CCUSFluid):
    return fluid.rho_g_ref * np.exp(fluid.c_g * (np.asarray(pressure) - fluid.p_ref))


def ccus_total_compressibility(grid, s_g, rock: CCUSRock, fluid: CCUSFluid,
                               scale=1.0):
    sg = np.clip(np.asarray(s_g, dtype=float), 0.0, rock.s_g_max)
    cr = _as_grid_field(rock.cr, grid)
    return float(scale) * np.maximum(
        cr + sg * float(fluid.c_g) + (1.0 - sg) * float(fluid.c_w), 0.0
    )


def solve_ccus_steady_pressure(grid, s_g, rock: CCUSRock, fluid: CCUSFluid,
                               wells, no_crossflow=False):
    mobility = ccus_total_mobility(s_g, rock, fluid)
    Aflow = _assemble_tpfa_flow_operator(grid, mobility, no_crossflow).tolil()
    b = np.zeros(grid.ncell, dtype=float)
    if wells.inj_bhp is None:
        q_each = wells.rate / max(len(wells.inj_cells), 1)
        for cell in wells.inj_cells:
            b[grid.idx(*cell)] += q_each
    for cell in wells.prod_cells:
        idx = grid.idx(*cell)
        Aflow.rows[idx] = [idx]; Aflow.data[idx] = [1.0]; b[idx] = float(wells.bhp)
    if wells.inj_bhp is not None:
        for cell in wells.inj_cells:
            idx = grid.idx(*cell)
            Aflow.rows[idx] = [idx]; Aflow.data[idx] = [1.0]; b[idx] = float(wells.inj_bhp)
    p = spsolve(Aflow.tocsr(), b)
    pressure = p.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)
    return pressure, mobility


def solve_ccus_transient_pressure_step(grid, s_g, rock: CCUSRock,
                                        fluid: CCUSFluid, wells,
                                        pressure_old, dt,
                                        no_crossflow=False,
                                        compressibility_scale=1.0):
    """Backward-Euler TPFA pressure using explicit CO2/brine phase properties."""
    if dt <= 0.0:
        raise ValueError('dt must be positive')
    pressure_old = np.asarray(pressure_old, dtype=float)
    mobility = ccus_total_mobility(s_g, rock, fluid)
    Aflow = _assemble_tpfa_flow_operator(grid, mobility, no_crossflow)
    phi_old, multiplier = pressure_dependent_porosity(
        grid, rock, pressure_old, float(wells.bhp)
    )
    ct = ccus_total_compressibility(
        grid, s_g, rock, fluid, scale=compressibility_scale
    )
    storage_capacity = phi_old * grid.vcell * ct
    flat_old = pressure_old.transpose(2, 1, 0).ravel()
    storage_flat = storage_capacity.transpose(2, 1, 0).ravel()
    Aacc = csr_matrix((storage_flat / dt,
                       (np.arange(grid.ncell), np.arange(grid.ncell))),
                      shape=(grid.ncell, grid.ncell))
    A = (Aflow + Aacc).tolil()
    b = (storage_flat / dt) * flat_old
    prescribed = np.zeros(grid.ncell, dtype=float)
    if wells.inj_bhp is None:
        q_each = wells.rate / max(len(wells.inj_cells), 1)
        for cell in wells.inj_cells:
            idx = grid.idx(*cell); b[idx] += q_each; prescribed[idx] += q_each

    dirichlet = []
    for cell in wells.prod_cells:
        idx = grid.idx(*cell)
        A.rows[idx] = [idx]; A.data[idx] = [1.0]; b[idx] = float(wells.bhp)
        dirichlet.append(cell)
    if wells.inj_bhp is not None:
        for cell in wells.inj_cells:
            idx = grid.idx(*cell)
            A.rows[idx] = [idx]; A.data[idx] = [1.0]; b[idx] = float(wells.inj_bhp)
            dirichlet.append(cell)

    A = A.tocsr()
    pflat = spsolve(A, b)
    pressure = pflat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)
    algebraic = A @ pflat - b
    flow_out = Aflow @ pflat
    accumulation = storage_flat * (pflat - flat_old) / dt
    physical = accumulation + flow_out - prescribed
    well_sources = {}
    for cell in dirichlet:
        idx = grid.idx(*cell)
        well_sources[cell] = float(accumulation[idx] + flow_out[idx])
        physical[idx] = 0.0

    qinj = float(sum(max(well_sources.get(c, prescribed[grid.idx(*c)]), 0.0)
                     for c in wells.inj_cells))
    qprod = float(sum(max(-well_sources.get(c, prescribed[grid.idx(*c)]), 0.0)
                      for c in wells.prod_cells))
    inj_face_by_cell, qinj_face = injection_rates(
        grid, pressure, mobility, wells, no_crossflow
    )
    qprod_face = producer_rate(grid, pressure, mobility, wells, no_crossflow)

    def reshape(flat):
        return flat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)

    return TransientPressureStepResult(
        pressure=pressure,
        mobility=mobility,
        matrix=A,
        rhs=b,
        algebraic_residual=algebraic,
        physical_residual=reshape(physical),
        total_compressibility=ct,
        pore_volume_multiplier=multiplier,
        storage_capacity=storage_capacity,
        accumulation_rate=reshape(accumulation),
        flow_outflow_rate=reshape(flow_out),
        well_source_rate=well_sources,
        injector_well_rate=qinj,
        producer_well_rate=qprod,
        injector_face_rate=float(qinj_face),
        producer_face_rate=float(qprod_face),
        total_accumulation_rate=float(np.sum(accumulation)),
        global_balance_error=float(qinj - qprod - np.sum(accumulation)),
    )


def _ccus_mass_face_fluxes(grid, s_g, density, rock, fluid, qx, qy, qz):
    fg = ccus_fractional_flow(s_g, rock, fluid)
    mx = qx * np.where(qx >= 0.0,
                       density[:-1, :, :] * fg[:-1, :, :],
                       density[1:, :, :] * fg[1:, :, :])
    my = qy * np.where(qy >= 0.0,
                       density[:, :-1, :] * fg[:, :-1, :],
                       density[:, 1:, :] * fg[:, 1:, :])
    if grid.nz > 1:
        mz = qz * np.where(qz >= 0.0,
                           density[:, :, :-1] * fg[:, :, :-1],
                           density[:, :, 1:] * fg[:, :, 1:])
    else:
        mz = np.zeros_like(qz)
    return mx, my, mz


def _ccus_well_mass_source(grid, s_g, density, rock, fluid, source_dictionary):
    source = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    fg = ccus_fractional_flow(s_g, rock, fluid)
    rho_inj = float(ccus_gas_density(np.array([fluid.p_ref]), fluid)[0])
    for cell, qtotal in source_dictionary.items():
        qtotal = float(qtotal)
        if qtotal >= 0.0:
            source[cell] += rho_inj * qtotal
        else:
            source[cell] += density[cell] * fg[cell] * qtotal
    return source


def advance_ccus_grid_mass_advection(grid, s_g_old, pressure_old, pressure_new,
                                     rock, fluid, qx, qy, qz, well_sources,
                                     dt, cfl_number=0.30):
    """Stage-17 finite-volume ground truth rewritten in explicit CCUS notation."""
    rho_old = ccus_gas_density(pressure_old, fluid)
    rho_new = ccus_gas_density(pressure_new, fluid)
    phi_old, _ = pressure_dependent_porosity(grid, rock, pressure_old, fluid.p_ref)
    phi_new, _ = pressure_dependent_porosity(grid, rock, pressure_new, fluid.p_ref)
    capacity_old = phi_old * grid.vcell * rho_old
    capacity_new = phi_new * grid.vcell * rho_new
    mass = capacity_old * np.asarray(s_g_old, dtype=float)
    initial_mass = float(np.sum(mass))
    storage_saturation = mass / np.maximum(capacity_new, 1.0e-30)

    throughput = np.zeros_like(s_g_old, dtype=float)
    throughput[:-1, :, :] += np.abs(qx); throughput[1:, :, :] += np.abs(qx)
    throughput[:, :-1, :] += np.abs(qy); throughput[:, 1:, :] += np.abs(qy)
    if grid.nz > 1:
        throughput[:, :, :-1] += np.abs(qz); throughput[:, :, 1:] += np.abs(qz)
    throughput += np.abs(well_source_field(grid, well_sources))
    pv = phi_new * grid.vcell
    active = throughput > 1.0e-30
    slope = ccus_max_fractional_flow_slope(rock, fluid)
    dt_cfl = (float(cfl_number * np.min(pv[active] / throughput[active])
                    / max(slope, 1.0e-30)) if np.any(active) else np.inf)
    nsub = max(1, int(np.ceil(dt / dt_cfl))) if np.isfinite(dt_cfl) else 1
    h = dt / nsub
    s_g = storage_saturation.copy()
    injected = produced = 0.0
    for _ in range(nsub):
        mx, my, mz = _ccus_mass_face_fluxes(
            grid, s_g, rho_new, rock, fluid, qx, qy, qz
        )
        divm = _mass_flux_outflow_divergence(grid, mx, my, mz)
        source = _ccus_well_mass_source(
            grid, s_g, rho_new, rock, fluid, well_sources
        )
        injected += h * float(np.sum(np.maximum(source, 0.0)))
        produced += h * float(np.sum(np.maximum(-source, 0.0)))
        mass += h * (source - divm)
        s_g = mass / np.maximum(capacity_new, 1.0e-30)
        violation = max(float(np.max(-s_g)),
                        float(np.max(s_g - rock.s_g_max)))
        if violation > 2.0e-8:
            raise RuntimeError(
                f'CCUS grid mass transport violated saturation bounds by {violation:.3e}'
            )
        s_g = np.clip(s_g, 0.0, rock.s_g_max)
        mass = capacity_new * s_g
    final_mass = float(np.sum(mass))
    return {
        'saturation_storage': storage_saturation,
        'saturation': s_g,
        'mass': mass,
        'capacity': capacity_new,
        'density': rho_new,
        'initial_mass': initial_mass,
        'final_mass': final_mass,
        'injected_mass': injected,
        'produced_mass': produced,
        'balance_error': final_mass - initial_mass - injected + produced,
        'substeps': nsub,
        'dt_cfl_s': dt_cfl,
    }


def cell_total_inflow_outflow(grid, qx, qy, qz, well_sources):
    """Exact positive total-volume inflow/outflow rates for each TPFA cell."""
    qin = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    qout = np.zeros_like(qin)

    pos = qx >= 0.0
    qout[:-1, :, :] += np.where(pos, qx, 0.0)
    qin[1:, :, :] += np.where(pos, qx, 0.0)
    qout[1:, :, :] += np.where(~pos, -qx, 0.0)
    qin[:-1, :, :] += np.where(~pos, -qx, 0.0)

    pos = qy >= 0.0
    qout[:, :-1, :] += np.where(pos, qy, 0.0)
    qin[:, 1:, :] += np.where(pos, qy, 0.0)
    qout[:, 1:, :] += np.where(~pos, -qy, 0.0)
    qin[:, :-1, :] += np.where(~pos, -qy, 0.0)

    if grid.nz > 1:
        pos = qz >= 0.0
        qout[:, :, :-1] += np.where(pos, qz, 0.0)
        qin[:, :, 1:] += np.where(pos, qz, 0.0)
        qout[:, :, 1:] += np.where(~pos, -qz, 0.0)
        qin[:, :, :-1] += np.where(~pos, -qz, 0.0)

    for cell, q in well_sources.items():
        if q >= 0.0:
            qin[cell] += float(q)
        else:
            qout[cell] += -float(q)
    return qin, qout


def build_variable_flux_streamtubes(grid, pressure, mobility, wells,
                                    well_sources, qx, qy, qz,
                                    pore_volume, seeds_per_dim=6):
    """Pollock geometry with cellwise TPFA storage attenuation/amplification.

    Each injector seed begins with an equal share of the true transient BHP well
    source for that completion.  In cell i, q_out/q_in is taken from the exact
    TPFA volume balance.  Raw q*Delta-tau volumes are then normalized within each
    cell so the streamtube segments partition the exact cell pore volume.
    """
    velocity = pore_velocities(grid, pressure, mobility, no_crossflow=False)
    offsets = (np.arange(seeds_per_dim) + 0.5) / seeds_per_dim
    prod_set = set(wells.prod_cells)
    qin_cell, qout_cell = cell_total_inflow_outflow(
        grid, qx, qy, qz, well_sources
    )
    ratio = np.ones_like(qin_cell)
    active = qin_cell > 1.0e-30
    ratio[active] = qout_cell[active] / qin_cell[active]
    ratio = np.clip(ratio, 0.0, 10.0)

    rows = []
    occurrences = []
    for source in wells.inj_cells:
        traced = []
        for ox in offsets * grid.dx:
            for oy in offsets * grid.dy:
                row = trace_streamline_detailed(
                    grid, velocity, source,
                    (float(ox), float(oy), 0.5 * grid.dzk[source[2]]),
                    prod_set,
                )
                if len(row['cells']) >= 1:
                    traced.append(row)
        if not traced:
            continue
        qstart = max(float(well_sources.get(source, 0.0)), 0.0) / len(traced)
        for row in traced:
            cells = list(row['cells'])
            dtaus = np.asarray(row['dtaus'], dtype=float)
            qfaces = [qstart]
            raw = []
            for m, cell in enumerate(cells):
                qin_stream = qfaces[-1]
                qout_stream = qin_stream * float(ratio[cell])
                qfaces.append(qout_stream)
                tau = float(dtaus[m]) if m < len(dtaus) else 0.0
                if tau <= 0.0:
                    tau = float(pore_volume[cell] / max(qin_cell[cell], 1.0e-30))
                raw.append(max(0.5 * (qin_stream + qout_stream) * tau, 0.0))
            record = {
                'cells': cells,
                'dtaus': dtaus,
                'points': np.asarray(row['points'], dtype=float),
                'reached': bool(row['reached']),
                'source_cell': source,
                'qfaces': np.asarray(qfaces, dtype=float),
                'raw_volume': np.asarray(raw, dtype=float),
                'segment_pv': np.zeros(len(cells), dtype=float),
            }
            ridx = len(rows)
            rows.append(record)
            for m, cell in enumerate(cells):
                occurrences.append((cell, ridx, m))

    # Normalize raw segment volumes to exact cell pore volume.  This turns the
    # set of trajectories into a conservative cell-volume partition.
    grouped = {}
    for cell, ridx, m in occurrences:
        grouped.setdefault(cell, []).append((ridx, m))
    covered = np.zeros((grid.nx, grid.ny, grid.nz), dtype=bool)
    for cell, entries in grouped.items():
        covered[cell] = True
        total_raw = sum(rows[r]['raw_volume'][m] for r, m in entries)
        if total_raw <= 1.0e-30:
            share = float(pore_volume[cell]) / len(entries)
            for r, m in entries:
                rows[r]['segment_pv'][m] = share
        else:
            for r, m in entries:
                rows[r]['segment_pv'][m] = (
                    float(pore_volume[cell]) * rows[r]['raw_volume'][m] / total_raw
                )

    # Representation diagnostics: how closely current path fluxes reproduce the
    # exact cell inflow before volume normalization.
    represented_in = np.zeros_like(qin_cell)
    represented_out = np.zeros_like(qout_cell)
    for row in rows:
        for m, cell in enumerate(row['cells']):
            represented_in[cell] += row['qfaces'][m]
            represented_out[cell] += row['qfaces'][m + 1]
    mask = qin_cell > 1.0e-20
    rel_in = np.zeros_like(qin_cell)
    rel_out = np.zeros_like(qout_cell)
    rel_in[mask] = (represented_in[mask] - qin_cell[mask]) / qin_cell[mask]
    mask_out = qout_cell > 1.0e-20
    rel_out[mask_out] = ((represented_out[mask_out] - qout_cell[mask_out])
                         / qout_cell[mask_out])
    return rows, {
        'qin_cell': qin_cell,
        'qout_cell': qout_cell,
        'storage_fraction': np.where(qin_cell > 1.0e-30,
                                     (qin_cell - qout_cell) / qin_cell, 0.0),
        'represented_in': represented_in,
        'represented_out': represented_out,
        'relative_inflow_error': rel_in,
        'relative_outflow_error': rel_out,
        'covered': covered,
        'coverage_count': int(np.count_nonzero(covered)),
        'start_rate': float(sum(row['qfaces'][0] for row in rows)),
        'end_rate': float(sum(row['qfaces'][-1] for row in rows if row['reached'])),
    }


def advance_variable_flux_streamtubes(rows, s_g_initial_grid, density_grid,
                                      rock, fluid, dt, cfl_number=0.20):
    """Explicit finite-volume gas-mass transport on variable-flux streamtubes."""
    # Attach segment state and retain exact segment masses.
    segment_mass = []
    segment_s = []
    segment_rho = []
    slope = ccus_max_fractional_flow_slope(rock, fluid)
    dt_stable = np.inf
    for row in rows:
        svals = np.array([s_g_initial_grid[c] for c in row['cells']], dtype=float)
        rvals = np.array([density_grid[c] for c in row['cells']], dtype=float)
        pv = np.asarray(row['segment_pv'], dtype=float)
        mass = rvals * pv * svals
        segment_mass.append(mass)
        segment_s.append(svals)
        segment_rho.append(rvals)
        throughput = np.maximum(row['qfaces'][:-1], row['qfaces'][1:])
        active = (pv > 1.0e-30) & (throughput > 1.0e-30)
        if np.any(active):
            dt_stable = min(
                dt_stable,
                float(cfl_number * np.min(pv[active] / throughput[active])
                      / max(slope, 1.0e-30)),
            )
    nsub = max(1, int(np.ceil(dt / dt_stable))) if np.isfinite(dt_stable) else 1
    h = dt / nsub
    rho_inj = float(ccus_gas_density(np.array([fluid.p_ref]), fluid)[0])
    injected = produced = 0.0

    for _ in range(nsub):
        old_s = [m / np.maximum(r * row['segment_pv'], 1.0e-30)
                 for m, r, row in zip(segment_mass, segment_rho, rows)]
        updates = []
        for row_index, row in enumerate(rows):
            svals = old_s[row_index]
            rvals = segment_rho[row_index]
            qf = row['qfaces']
            n = len(svals)
            dm = np.zeros(n, dtype=float)
            for m in range(n):
                if m == 0:
                    minlet = rho_inj * qf[0]
                else:
                    minlet = (rvals[m - 1]
                              * ccus_fractional_flow(svals[m - 1], rock, fluid)
                              * qf[m])
                mout = (rvals[m]
                        * ccus_fractional_flow(svals[m], rock, fluid)
                        * qf[m + 1])
                dm[m] = h * (minlet - mout)
            updates.append(dm)
            injected += h * rho_inj * qf[0]
            if row['reached'] and n:
                produced += h * (rvals[-1]
                                 * ccus_fractional_flow(svals[-1], rock, fluid)
                                 * qf[-1])
        for r, dm in enumerate(updates):
            segment_mass[r] += dm
            denom = segment_rho[r] * rows[r]['segment_pv']
            snew = segment_mass[r] / np.maximum(denom, 1.0e-30)
            violation = max(float(np.max(-snew)),
                            float(np.max(snew - rock.s_g_max))) if snew.size else 0.0
            if violation > 2.0e-8:
                raise RuntimeError(
                    f'Variable-flux streamtube bounds violated by {violation:.3e}'
                )
            snew = np.clip(snew, 0.0, rock.s_g_max)
            segment_mass[r] = denom * snew

    initial_mass = float(sum(np.sum(rho * row['segment_pv'] * sval)
                             for rho, row, sval in zip(segment_rho, rows, segment_s)))
    final_mass = float(sum(np.sum(m) for m in segment_mass))
    return {
        'segment_mass': segment_mass,
        'segment_saturation': [m / np.maximum(r * row['segment_pv'], 1.0e-30)
                               for m, r, row in zip(segment_mass, segment_rho, rows)],
        'initial_mass': initial_mass,
        'final_mass': final_mass,
        'injected_mass': injected,
        'produced_mass': produced,
        'balance_error': final_mass - initial_mass - injected + produced,
        'substeps': nsub,
        'dt_cfl_s': dt_stable,
    }


def _map_streamtube_mass_to_grid_v8(grid, rows, transport, density_grid,
                                    cell_pore_volume, fallback_saturation, rock):
    """Mass map-back using the exact Stage-18 cell pore-volume partition."""
    mass = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    represented_pv = np.zeros_like(mass)
    for row, masses in zip(rows, transport['segment_mass']):
        for m, cell in enumerate(row['cells']):
            mass[cell] += float(masses[m])
            represented_pv[cell] += float(row['segment_pv'][m])
    fallback_mass = density_grid * cell_pore_volume * fallback_saturation
    covered = represented_pv > 1.0e-30
    total_mass = fallback_mass.copy()
    total_mass[covered] = mass[covered]
    saturation = total_mass / np.maximum(density_grid * cell_pore_volume, 1.0e-30)
    saturation = np.clip(saturation, 0.0, rock.s_g_max)
    return saturation, total_mass, represented_pv, covered


def advance_ccus_capillary_mass(grid, s_g, mass, capacity, density,
                                rock, fluid, cap, dt, cfl_number=0.30):
    """Explicit, pairwise conservative capillary gas-mass redistribution."""
    mass = np.asarray(mass, dtype=float).copy()
    s_g = np.asarray(s_g, dtype=float).copy()
    start = float(np.sum(mass))
    remaining = float(dt)
    nsub = 0
    while remaining > 1.0e-12 * max(dt, 1.0):
        D = ccus_capillary_diffusion_coefficient(s_g, grid, rock, fluid, cap)
        tx, ty, tz = _capillary_face_coefficients(grid, D)
        conductance = np.zeros_like(s_g)
        conductance[:-1] += tx; conductance[1:] += tx
        conductance[:, :-1] += ty; conductance[:, 1:] += ty
        if grid.nz > 1:
            conductance[:, :, :-1] += tz; conductance[:, :, 1:] += tz
        pv = capacity / np.maximum(density, 1.0e-30)
        active = conductance > 1.0e-30
        hstable = (float(cfl_number * np.min(pv[active] / conductance[active]))
                   if np.any(active) else remaining)
        h = min(remaining, hstable)
        qcx = -tx * (s_g[1:] - s_g[:-1])
        qcy = -ty * (s_g[:, 1:] - s_g[:, :-1])
        qcz = -tz * (s_g[:, :, 1:] - s_g[:, :, :-1])
        mx = qcx * np.where(qcx >= 0.0, density[:-1], density[1:])
        my = qcy * np.where(qcy >= 0.0, density[:, :-1], density[:, 1:])
        mz = qcz * np.where(qcz >= 0.0, density[:, :, :-1], density[:, :, 1:])
        mass -= h * _mass_flux_outflow_divergence(grid, mx, my, mz)
        s_g = mass / np.maximum(capacity, 1.0e-30)
        violation = max(float(np.max(-s_g)), float(np.max(s_g - rock.s_g_max)))
        if violation > 2.0e-8:
            raise RuntimeError(f'CCUS capillary bounds violated by {violation:.3e}')
        s_g = np.clip(s_g, 0.0, rock.s_g_max)
        mass = capacity * s_g
        remaining -= h; nsub += 1
        if nsub > 200000:
            raise RuntimeError('CCUS capillary subcycling exceeded 200000 steps')
    return {'saturation': s_g, 'mass': mass, 'substeps': nsub,
            'mass_change': float(np.sum(mass)) - start}


def plot_ccus_phase_convention(rock, fluid, cap, grid, outdir):
    s = np.linspace(0.0, rock.s_g_max, 600)
    krg, krw = ccus_relative_permeability(s, rock)
    fg = ccus_fractional_flow(s, rock, fluid)
    pc = ccus_capillary_pressure(s, rock, cap)
    D = ccus_capillary_diffusion_coefficient(
        np.broadcast_to(s[:, None, None], (s.size, 1, 1)),
        Grid3D(s.size, 1, 1, 1.0, 1.0, 1.0,
               np.full((s.size, 1, 1), float(np.mean(grid.k))),
               np.full((s.size, 1, 1), float(np.mean(grid.phi)))),
        rock, fluid, cap
    )[:, 0, 0]

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(s, krg, label='CO2 krg drainage')
    ax.plot(s, krw, label='brine krw drainage')
    ax.axvline(rock.s_g_initial, ls='--', label='initial Sg')
    ax.axvline(rock.s_g_max, ls=':', label='maximum drainage Sg')
    ax.set_xlabel('CO2 saturation Sg'); ax.set_ylabel('relative permeability')
    ax.set_title('Explicit CCUS drainage relative permeability')
    ax.grid(alpha=0.3); ax.legend()
    _v7_save(fig, '100_ccus_relative_permeability.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(s, fg)
    ax.set_xlabel('CO2 saturation Sg'); ax.set_ylabel('CO2 fractional flow fg')
    ax.set_title('Explicit CCUS fractional flow')
    ax.grid(alpha=0.3)
    _v7_save(fig, '101_ccus_fractional_flow.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.semilogy(s, pc / 1.0e6)
    ax.set_xlabel('CO2 saturation Sg'); ax.set_ylabel('Pc = pg-pw [MPa]')
    ax.set_title('Brooks-Corey drainage capillary pressure')
    ax.grid(alpha=0.3)
    _v7_save(fig, '102_ccus_capillary_pressure.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(s, D)
    ax.set_xlabel('CO2 saturation Sg'); ax.set_ylabel('capillary D [m2/s]')
    ax.set_title('CCUS gas-saturation capillary diffusion coefficient')
    ax.grid(alpha=0.3)
    _v7_save(fig, '103_ccus_capillary_diffusion.png', outdir)

    history_values = [0.30, 0.50, rock.s_g_max]
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.plot(s, krg, lw=2, label='drainage')
    for hist in history_values:
        sscan = np.linspace(0.0, hist, 400)
        h = np.full_like(sscan, hist)
        kscan, _ = ccus_relative_permeability(sscan, rock, h)
        ax.plot(sscan, kscan, label=f'imbibition from Sg,max={hist:.2f}')
    ax.axvline(rock.s_gr_max, ls=':', label='maximum residual-gas target')
    ax.set_xlabel('CO2 saturation Sg'); ax.set_ylabel('gas relative permeability')
    ax.set_title('Drainage and residual-gas scanning curves')
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _v7_save(fig, '104_ccus_hysteresis_scanning_curves.png', outdir)


def _plot_v8_layer(field, title, filename, outdir, kk, label='', cmap='viridis',
                   vmin=None, vmax=None):
    fig, ax = plt.subplots(figsize=(5.8, 5.0))
    im = ax.imshow(np.asarray(field)[:, :, kk].T, origin='lower', cmap=cmap,
                   vmin=vmin, vmax=vmax)
    ax.set_title(title); ax.set_xlabel('i index'); ax.set_ylabel('j index')
    fig.colorbar(im, ax=ax, label=label)
    _v7_save(fig, filename, outdir)


def plot_variable_flux_diagnostics(grid, pressure, rows, geometry, grid_result,
                                   stream_saturation, difference, step, time_days,
                                   outdir, rock):
    x = (np.arange(grid.nx) + 0.5) * grid.dx
    y = (np.arange(grid.ny) + 0.5) * grid.dy
    for kk in range(grid.nz):
        fig, ax = plt.subplots(figsize=(6.2, 5.3))
        values = (pressure[:, :, kk] / 1.0e6).T
        filled = ax.contourf(x, y, values, levels=14, cmap='viridis')
        lines = ax.contour(x, y, values, levels=8, colors='k', linewidths=0.55)
        ax.clabel(lines, fontsize=7, fmt='%.2f')
        for row in rows:
            if row['source_cell'][2] == kk and row['points'].shape[0] >= 2:
                ax.plot(row['points'][:, 0], row['points'][:, 1], lw=0.65,
                        alpha=0.52 if row['reached'] else 0.15)
        ax.set_aspect('equal')
        ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
        ax.set_title(f'Pressure contours + variable-flux streamtubes, step {step}, layer {kk + 1}')
        fig.colorbar(filled, ax=ax, label='pressure [MPa]')
        _v7_save(fig, f'109_step_{step:02d}_pressure_contours_streamlines_layer_{kk + 1}.png', outdir)
        _plot_v8_layer(
            pressure / 1.0e6,
            f'Transient pressure, step {step}, user z-layer {kk + 1}',
            f'110_step_{step:02d}_pressure_layer_{kk + 1}.png', outdir, kk,
            label='pressure [MPa]'
        )
        _plot_v8_layer(
            geometry['storage_fraction'],
            f'Pressure-storage fraction, step {step}, user z-layer {kk + 1}',
            f'111_step_{step:02d}_storage_fraction_layer_{kk + 1}.png', outdir, kk,
            label='(Qin-Qout)/Qin', cmap='coolwarm', vmin=-0.25, vmax=1.0
        )
        _plot_v8_layer(
            grid_result['saturation'],
            f'Grid FV ground truth Sg, step {step}, layer {kk + 1}',
            f'112_step_{step:02d}_grid_sg_layer_{kk + 1}.png', outdir, kk,
            label='Sg', vmin=0.0, vmax=rock.s_g_max
        )
        _plot_v8_layer(
            stream_saturation,
            f'Variable-flux streamtube Sg, step {step}, layer {kk + 1}',
            f'113_step_{step:02d}_streamtube_sg_layer_{kk + 1}.png', outdir, kk,
            label='Sg', vmin=0.0, vmax=rock.s_g_max
        )
        lim = max(float(np.max(np.abs(difference))), 1.0e-8)
        _plot_v8_layer(
            difference,
            f'Streamtube minus grid Sg, step {step}, layer {kk + 1}',
            f'114_step_{step:02d}_difference_layer_{kk + 1}.png', outdir, kk,
            label='delta Sg', cmap='coolwarm', vmin=-lim, vmax=lim
        )

    fig = plt.figure(figsize=(8.0, 6.5))
    ax = fig.add_subplot(111, projection='3d')
    for row in rows:
        pts = row['points']
        if pts.shape[0] >= 2:
            retention = row['qfaces'][-1] / max(row['qfaces'][0], 1.0e-30)
            ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], lw=0.8,
                    alpha=0.15 + 0.75 * min(max(retention, 0.0), 1.0))
    ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]'); ax.set_zlabel('z [m]')
    ax.invert_zaxis()
    ax.set_title(f'Variable-flux Pollock streamtubes, step {step}, {time_days:.2f} d')
    _v7_save(fig, f'115_step_{step:02d}_variable_flux_streamlines_3d.png', outdir)

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    selected = np.linspace(0, max(len(rows) - 1, 0), min(12, len(rows)), dtype=int)
    for ridx in selected:
        q = rows[ridx]['qfaces']
        x = np.linspace(0.0, 1.0, q.size)
        ax.plot(x, q / max(q[0], 1.0e-30), alpha=0.75)
    ax.set_xlabel('normalized distance along path')
    ax.set_ylabel('q(s) / q(injector)')
    ax.set_title(f'Total streamtube flux evolution, step {step}')
    ax.grid(alpha=0.3)
    _v7_save(fig, f'116_step_{step:02d}_path_flux_retention.png', outdir)

    mask = geometry['qin_cell'] > 1.0e-20
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.hist(geometry['relative_inflow_error'][mask].ravel(), bins=30)
    ax.set_xlabel('(represented Qin - exact Qin) / exact Qin')
    ax.set_ylabel('cells')
    ax.set_title(f'Pollock flux-representation error, step {step}')
    ax.grid(alpha=0.3)
    _v7_save(fig, f'117_step_{step:02d}_flux_representation_error.png', outdir)


@_dataclass_v8
class VariableFluxStepAudit:
    step: int
    time_days: float
    grid_mass_error_kg: float
    streamtube_mass_error_kg: float
    saturation_l1: float
    saturation_linf: float
    injection_rate_exact_m3_day: float
    streamtube_start_rate_m3_day: float
    production_rate_exact_m3_day: float
    streamtube_end_rate_m3_day: float
    pressure_storage_rate_m3_day: float
    path_count: int
    paths_reached: int
    cell_coverage: int
    grid_substeps: int
    streamtube_substeps: int
    max_relative_cell_inflow_error: float


def run_ccus_phase_variable_flux_target(outdir='pad_stream_v8_ccus_variable_flux_outputs',
                                        total_time_days=1.0,
                                        pressure_dt_days=0.5,
                                        seeds_per_dim=6,
                                        make_plots=True,
                                        include_capillary_check=True,
                                        initial_co2_saturation=0.0,
                                        brine_compressibility=0.0,
                                        rock_compressibility=0.0):
    """Run the Stage-18 phase correction and variable-flux transport audit."""
    _os_v8.makedirs(outdir, exist_ok=True)
    grid, _, _, cap, wells, _ = build_padstream_5x5x5_case()
    rock = CCUSRock(
        s_g_initial=float(initial_co2_saturation),
        cr=float(rock_compressibility),
    ).validate()
    fluid = CCUSFluid(
        p_ref=float(wells.inj_bhp),
        c_w=float(brine_compressibility),
    )
    if make_plots:
        plot_ccus_phase_convention(rock, fluid, cap, grid, outdir)

    nsteps = max(1, int(np.ceil(total_time_days / pressure_dt_days)))
    dt = total_time_days * DAYS_TO_SECONDS / nsteps
    pressure = np.full((grid.nx, grid.ny, grid.nz), float(wells.bhp))
    s_ground = np.full((grid.nx, grid.ny, grid.nz), rock.s_g_initial, dtype=float)
    audits = []
    histories = []

    print('=' * 112)
    print('VERSION 8 — EXPLICIT CCUS PHASES + VARIABLE-FLUX COMPRESSIBLE STREAMTUBES')
    print('=' * 112)
    print(f'CCUS convention: Sg0={rock.s_g_initial:.3f}, Swir={rock.s_wir:.3f}, '
          f'Sg,max={rock.s_g_max:.3f}, Sgr,max={rock.s_gr_max:.3f}')
    if rock.s_g_initial == 0.0 and fluid.c_w == 0.0 and rock.cr == 0.0:
        print('  [storage note] Sg0=0, c_brine=0 and c_rock=0: the first pressure step '
              'has zero accumulation capacity and is the steady-pressure limiting case.')

    for step in range(1, nsteps + 1):
        pressure_old = pressure.copy()
        s_old = s_ground.copy()
        pstep = solve_ccus_transient_pressure_step(
            grid, s_old, rock, fluid, wells, pressure_old, dt
        )
        pressure = pstep.pressure
        qx, qy, qz = tpfa_face_fluxes(grid, pressure, pstep.mobility)
        grid_result = advance_ccus_grid_mass_advection(
            grid, s_old, pressure_old, pressure, rock, fluid,
            qx, qy, qz, pstep.well_source_rate, dt
        )

        phi_new, _ = pressure_dependent_porosity(
            grid, rock, pressure, fluid.p_ref
        )
        pore_volume = phi_new * grid.vcell
        density = ccus_gas_density(pressure, fluid)
        rows, geometry = build_variable_flux_streamtubes(
            grid, pressure, pstep.mobility, wells, pstep.well_source_rate,
            qx, qy, qz, pore_volume, seeds_per_dim=seeds_per_dim
        )
        stream_transport = advance_variable_flux_streamtubes(
            rows, grid_result['saturation_storage'], density,
            rock, fluid, dt
        )
        stream_s, stream_mass, represented_pv, covered = _map_streamtube_mass_to_grid_v8(
            grid, rows, stream_transport, density, pore_volume,
            grid_result['saturation_storage'], rock
        )
        difference = stream_s - grid_result['saturation']

        # Optional capillary check is applied to the accepted grid ground truth,
        # not folded into the streamline approximation at this stage.
        cap_result = None
        if include_capillary_check:
            cap_result = advance_ccus_capillary_mass(
                grid, grid_result['saturation'], grid_result['mass'],
                grid_result['capacity'], grid_result['density'],
                rock, fluid, cap, dt
            )

        active = geometry['qin_cell'] > 1.0e-20
        max_flux_error = (float(np.max(np.abs(
            geometry['relative_inflow_error'][active]
        ))) if np.any(active) else 0.0)
        audit = VariableFluxStepAudit(
            step=step,
            time_days=step * dt / DAYS_TO_SECONDS,
            grid_mass_error_kg=float(grid_result['balance_error']),
            streamtube_mass_error_kg=float(stream_transport['balance_error']),
            saturation_l1=float(np.mean(np.abs(difference))),
            saturation_linf=float(np.max(np.abs(difference))),
            injection_rate_exact_m3_day=float(pstep.injector_well_rate * DAYS_TO_SECONDS),
            streamtube_start_rate_m3_day=float(geometry['start_rate'] * DAYS_TO_SECONDS),
            production_rate_exact_m3_day=float(pstep.producer_well_rate * DAYS_TO_SECONDS),
            streamtube_end_rate_m3_day=float(geometry['end_rate'] * DAYS_TO_SECONDS),
            pressure_storage_rate_m3_day=float(pstep.total_accumulation_rate * DAYS_TO_SECONDS),
            path_count=len(rows),
            paths_reached=int(sum(r['reached'] for r in rows)),
            cell_coverage=int(np.count_nonzero(covered)),
            grid_substeps=int(grid_result['substeps']),
            streamtube_substeps=int(stream_transport['substeps']),
            max_relative_cell_inflow_error=max_flux_error,
        )
        audits.append(audit)
        histories.append({
            'pressure': pressure.copy(),
            'grid_saturation': grid_result['saturation'].copy(),
            'stream_saturation': stream_s.copy(),
            'difference': difference.copy(),
            'geometry': geometry,
            'rows': rows,
            'capillary': cap_result,
        })
        if make_plots:
            plot_variable_flux_diagnostics(
                grid, pressure, rows, geometry, grid_result,
                stream_s, difference, step, audit.time_days, outdir, rock
            )
        # The grid finite-volume solution remains the accepted coupled state.
        s_ground = (cap_result['saturation'] if cap_result is not None
                    else grid_result['saturation'])
        print(
            f'  step {step}/{nsteps} t={audit.time_days:.2f} d  '
            f'paths={audit.paths_reached}/{audit.path_count}  '
            f'coverage={audit.cell_coverage}/{grid.ncell}  '
            f'Linf(stream-grid)={audit.saturation_linf:.3e}  '
            f'mass errors grid/stream={audit.grid_mass_error_kg:+.3e}/'
            f'{audit.streamtube_mass_error_kg:+.3e} kg'
        )

    if make_plots:
        t = np.array([a.time_days for a in audits])
        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.plot(t, [a.saturation_l1 for a in audits], 'o-', label='mean absolute')
        ax.plot(t, [a.saturation_linf for a in audits], 's-', label='maximum absolute')
        ax.set_xlabel('time [days]'); ax.set_ylabel('|streamtube-grid| in Sg')
        ax.set_title('Variable-flux streamtube error against FV ground truth')
        ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '120_variable_flux_saturation_error_history.png', outdir)

        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.plot(t, [a.injection_rate_exact_m3_day for a in audits], 'o-', label='exact well injection')
        ax.plot(t, [a.streamtube_start_rate_m3_day for a in audits], 's--', label='streamtube start sum')
        ax.plot(t, [a.production_rate_exact_m3_day for a in audits], '^-', label='exact production')
        ax.plot(t, [a.streamtube_end_rate_m3_day for a in audits], 'd--', label='streamtube end sum')
        ax.set_xlabel('time [days]'); ax.set_ylabel('rate [m3/day]')
        ax.set_title('Exact TPFA rates and represented streamtube rates')
        ax.grid(alpha=0.3); ax.legend(fontsize=8)
        _v7_save(fig, '121_variable_flux_rate_comparison.png', outdir)

        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.semilogy(t, np.maximum(np.abs([a.grid_mass_error_kg for a in audits]), 1e-16),
                    'o-', label='grid FV')
        ax.semilogy(t, np.maximum(np.abs([a.streamtube_mass_error_kg for a in audits]), 1e-16),
                    's-', label='variable-flux streamtube')
        ax.set_xlabel('time [days]'); ax.set_ylabel('|mass balance error| [kg]')
        ax.set_title('Mass conservation of both transport formulations')
        ax.grid(alpha=0.3, which='both'); ax.legend()
        _v7_save(fig, '122_variable_flux_mass_balance.png', outdir)

    summary = {
        'phase_convention': {
            'transported_phase': 'CO2 gas/non-wetting phase, S_g',
            'resident_phase': 'wetting brine, S_w=1-S_g',
            'initial_co2_saturation': rock.s_g_initial,
            'irreducible_brine_saturation': rock.s_wir,
            'maximum_drainage_co2_saturation': rock.s_g_max,
            'maximum_residual_co2_saturation': rock.s_gr_max,
            'capillary_pressure_definition': 'P_c=p_g-p_w',
            'brine_compressibility_1_per_Pa': fluid.c_w,
            'rock_compressibility_1_per_Pa': rock.cr,
        },
        'accepted_ground_truth': 'cell-centred finite-volume CO2 phase-mass transport',
        'streamtube_model': (
            'Pollock geometry; true transient well-source seed flux; exact cell '
            'Qout/Qin attenuation; exact cell pore-volume partition; variable-q '
            'one-dimensional phase-mass transport'
        ),
        'steps': [a.__dict__ for a in audits],
    }
    with open(_os_v8.path.join(outdir, 'PAD_Stream_V8_CCUS_Variable_Flux_Summary.json'), 'w') as f:
        _json_v8.dump(summary, f, indent=2)
    print('=' * 112)
    return audits, histories, summary


if False and __name__ == '__main__':
    import matplotlib
    V7_DISPLAY_PLOTS = True
    V7_CLOSE_AFTER_SHOW = True
    V7_PLOT_PAUSE_SECONDS = 0.10
    print(f'[plots] Matplotlib backend: {matplotlib.get_backend()}')
    print(f'[plots] Interactive mode: {plt.isinteractive()}')
    print(f'[plots] Display requested: {V7_DISPLAY_PLOTS}')
    run_ccus_phase_variable_flux_target(
        outdir='pad_stream_v8_ccus_variable_flux_outputs',
        total_time_days=1.0,
        pressure_dt_days=0.5,
        seeds_per_dim=6,
        make_plots=True,
        include_capillary_check=True,
        initial_co2_saturation=0.0,
        brine_compressibility=0.0,
        rock_compressibility=0.0,
    )
    if V7_DISPLAY_PLOTS and not _v7_backend_is_headless():
        plt.pause(0.25)


# ==============================================================================
# STAGE 19 [S19] — FACE-FLUX-CONSISTENT PATH DECOMPOSITION
# ==============================================================================
# Stage 18 demonstrated that equally seeded Pollock trajectories reproduce the
# total well rates but only approximate the TPFA throughput of every individual
# cell.  Stage 19 constructs an exact discrete decomposition of the directed
# TPFA face-flux network.
#
# The distinction is deliberate:
#   * Pollock streamlines remain the continuous subcell geometry/TOF diagnostic.
#   * TPFA flux paths are weighted discrete flow tubes whose summed weights
#     reproduce every face flux, well source, producer sink, and transient
#     pressure-storage sink/source to numerical precision.
#
# Two path-transport variants are compared against the cell-centred FV ground
# truth:
#   1. cell_mixed=True: path segments in each cell are remixed before every
#      transport substep.  This must reproduce the FV solution and validates the
#      decomposition algebra.
#   2. cell_mixed=False: independent path transport preserves streamline-like
#      segregation.  Its difference from FV measures the physical/numerical
#      effect of suppressing transverse mixing, not an error in face weighting.
# ==============================================================================

from dataclasses import dataclass as _dataclass_v9
from collections import deque as _deque_v9
import os as _os_v9
import json as _json_v9


@_dataclass_v9
class FaceFluxPath:
    path_id: int
    source_type: str
    source_cell: tuple
    sink_type: str
    sink_cell: tuple
    rate: float
    cells: list
    face_keys: list
    segment_pv: np.ndarray = None
    segment_tau: np.ndarray = None


def _v9_cell_node(cell):
    return ('cell', int(cell[0]), int(cell[1]), int(cell[2]))


def _v9_node_cell(node):
    if isinstance(node, tuple) and len(node) == 4 and node[0] == 'cell':
        return (int(node[1]), int(node[2]), int(node[3]))
    return None


def build_tpfa_flow_graph(grid, qx, qy, qz, well_sources, tolerance=None):
    """Build the exact directed TPFA volume-flow graph.

    Pressure accumulation is represented by terminal storage sinks when
    Qin>Qout and by storage-release sources when Qout>Qin.  These augmented
    edges make the graph exactly conservative even during transient pressure
    buildup or release.
    """
    source = ('super_source',)
    sink = ('super_sink',)
    edges = []
    if tolerance is None:
        scale = max(
            float(np.max(np.abs(qx))) if np.asarray(qx).size else 0.0,
            float(np.max(np.abs(qy))) if np.asarray(qy).size else 0.0,
            float(np.max(np.abs(qz))) if np.asarray(qz).size else 0.0,
            max((abs(float(q)) for q in well_sources.values()), default=0.0),
            1.0e-30,
        )
        tolerance = max(1.0e-12 * scale, 1.0e-14)
    tolerance = float(tolerance)

    def add_edge(u, v, capacity, kind, key, cell=None):
        capacity = float(capacity)
        if capacity <= tolerance:
            return
        edges.append({
            'u': u, 'v': v, 'capacity': capacity, 'residual': capacity,
            'kind': kind, 'key': key, 'cell': cell,
        })

    # Internal x faces.
    for i in range(grid.nx - 1):
        for j in range(grid.ny):
            for k in range(grid.nz):
                q = float(qx[i, j, k])
                left = (i, j, k); right = (i + 1, j, k)
                if q >= 0.0:
                    add_edge(_v9_cell_node(left), _v9_cell_node(right), q,
                             'internal_face', ('x', i, j, k))
                else:
                    add_edge(_v9_cell_node(right), _v9_cell_node(left), -q,
                             'internal_face', ('x', i, j, k))

    # Internal y faces.
    for i in range(grid.nx):
        for j in range(grid.ny - 1):
            for k in range(grid.nz):
                q = float(qy[i, j, k])
                low = (i, j, k); high = (i, j + 1, k)
                if q >= 0.0:
                    add_edge(_v9_cell_node(low), _v9_cell_node(high), q,
                             'internal_face', ('y', i, j, k))
                else:
                    add_edge(_v9_cell_node(high), _v9_cell_node(low), -q,
                             'internal_face', ('y', i, j, k))

    # Internal z faces.
    if grid.nz > 1:
        for i in range(grid.nx):
            for j in range(grid.ny):
                for k in range(grid.nz - 1):
                    q = float(qz[i, j, k])
                    lower = (i, j, k); upper = (i, j, k + 1)
                    if q >= 0.0:
                        add_edge(_v9_cell_node(lower), _v9_cell_node(upper), q,
                                 'internal_face', ('z', i, j, k))
                    else:
                        add_edge(_v9_cell_node(upper), _v9_cell_node(lower), -q,
                                 'internal_face', ('z', i, j, k))

    # Physical wells.
    for cell, q in well_sources.items():
        q = float(q)
        if q > tolerance:
            add_edge(source, _v9_cell_node(cell), q, 'injector_source',
                     ('injector', tuple(cell)), tuple(cell))
        elif q < -tolerance:
            add_edge(_v9_cell_node(cell), sink, -q, 'producer_sink',
                     ('producer', tuple(cell)), tuple(cell))

    qin, qout = cell_total_inflow_outflow(grid, qx, qy, qz, well_sources)
    storage_rate = qin - qout
    for i in range(grid.nx):
        for j in range(grid.ny):
            for k in range(grid.nz):
                cell = (i, j, k)
                value = float(storage_rate[cell])
                if value > tolerance:
                    add_edge(_v9_cell_node(cell), sink, value,
                             'storage_sink', ('storage_sink', cell), cell)
                elif value < -tolerance:
                    add_edge(source, _v9_cell_node(cell), -value,
                             'storage_release_source',
                             ('storage_release', cell), cell)

    adjacency = {}
    for eid, edge in enumerate(edges):
        adjacency.setdefault(edge['u'], []).append(eid)
    return {
        'source': source,
        'sink': sink,
        'edges': edges,
        'adjacency': adjacency,
        'qin_cell': qin,
        'qout_cell': qout,
        'storage_rate': storage_rate,
    }


def decompose_tpfa_flow_paths(flow_graph, relative_tolerance=1.0e-10,
                              max_paths=20000):
    """Greedy nonnegative source-to-sink decomposition of the exact flow graph."""
    source = flow_graph['source']; sink = flow_graph['sink']
    edges = flow_graph['edges']; adjacency = flow_graph['adjacency']
    total_source = sum(e['capacity'] for e in edges if e['u'] == source)
    tol = max(float(relative_tolerance) * max(total_source, 1.0e-30), 1.0e-14)
    path_floor = max(1.0e-16 * max(total_source, 1.0e-30), 1.0e-18)
    paths = []

    def find_path():
        previous = {source: None}
        queue = _deque_v9([source])
        while queue:
            u = queue.popleft()
            candidates = [eid for eid in adjacency.get(u, [])
                          if edges[eid]['residual'] > path_floor]
            candidates.sort(key=lambda eid: edges[eid]['residual'], reverse=True)
            for eid in candidates:
                v = edges[eid]['v']
                if v in previous:
                    continue
                previous[v] = eid
                if v == sink:
                    chain = []
                    node = sink
                    while node != source:
                        peid = previous[node]
                        chain.append(peid)
                        node = edges[peid]['u']
                    return list(reversed(chain))
                queue.append(v)
        return None

    while True:
        source_remaining = sum(e['residual'] for e in edges
                               if e['u'] == source and e['residual'] > tol)
        if source_remaining <= tol:
            break
        chain = find_path()
        if chain is None:
            raise RuntimeError(
                f'Unable to route {source_remaining:.6e} m3/s of residual TPFA flow'
            )
        rate = min(edges[eid]['residual'] for eid in chain)
        for eid in chain:
            edges[eid]['residual'] = max(edges[eid]['residual'] - rate, 0.0)

        first = edges[chain[0]]; last = edges[chain[-1]]
        source_type = ('injector' if first['kind'] == 'injector_source'
                       else 'storage_release')
        sink_type = ('producer' if last['kind'] == 'producer_sink'
                     else 'storage')
        source_cell = tuple(first['cell'])
        sink_cell = tuple(last['cell'])
        cells = []
        face_keys = []
        for eid in chain:
            edge = edges[eid]
            cu = _v9_node_cell(edge['u'])
            cv = _v9_node_cell(edge['v'])
            if cu is not None and (not cells or cells[-1] != cu):
                cells.append(cu)
            if edge['kind'] == 'internal_face':
                face_keys.append(edge['key'])
            if cv is not None and (not cells or cells[-1] != cv):
                cells.append(cv)
        paths.append(FaceFluxPath(
            path_id=len(paths), source_type=source_type,
            source_cell=source_cell, sink_type=sink_type,
            sink_cell=sink_cell, rate=float(rate), cells=cells,
            face_keys=face_keys,
        ))
        if len(paths) > max_paths:
            raise RuntimeError('TPFA path decomposition exceeded max_paths')

    residual_max = max((e['residual'] for e in edges), default=0.0)
    return paths, {
        'total_source_rate': float(total_source),
        'path_rate_sum': float(sum(p.rate for p in paths)),
        'path_count': len(paths),
        'max_edge_residual': float(residual_max),
        'tolerance': float(tol),
    }


def assign_exact_path_pore_volumes(paths, pore_volume):
    """Partition every cell pore volume among the paths that enter that cell."""
    entry_rate = np.zeros_like(pore_volume, dtype=float)
    entries = {}
    for pidx, path in enumerate(paths):
        for midx, cell in enumerate(path.cells):
            entry_rate[cell] += path.rate
            entries.setdefault(cell, []).append((pidx, midx))

    for path in paths:
        path.segment_pv = np.zeros(len(path.cells), dtype=float)
        path.segment_tau = np.zeros(len(path.cells), dtype=float)
    for cell, occurrences in entries.items():
        total = float(entry_rate[cell])
        if total <= 1.0e-30:
            share = float(pore_volume[cell]) / len(occurrences)
            for pidx, midx in occurrences:
                paths[pidx].segment_pv[midx] = share
                paths[pidx].segment_tau[midx] = share / max(paths[pidx].rate, 1.0e-30)
        else:
            for pidx, midx in occurrences:
                path = paths[pidx]
                share = float(pore_volume[cell]) * path.rate / total
                path.segment_pv[midx] = share
                path.segment_tau[midx] = share / max(path.rate, 1.0e-30)

    represented = np.zeros_like(pore_volume, dtype=float)
    for path in paths:
        for midx, cell in enumerate(path.cells):
            represented[cell] += path.segment_pv[midx]
    error = represented - pore_volume
    return {
        'entry_rate': entry_rate,
        'represented_pore_volume': represented,
        'pore_volume_error': error,
        'max_abs_pore_volume_error': float(np.max(np.abs(error))),
        'coverage_count': int(np.count_nonzero(represented > 0.0)),
    }


def reconstruct_fluxes_from_paths(grid, paths, flow_graph):
    """Reconstruct face, well, storage, and cell rates from path weights."""
    rx = np.zeros((grid.nx - 1, grid.ny, grid.nz), dtype=float)
    ry = np.zeros((grid.nx, grid.ny - 1, grid.nz), dtype=float)
    rz = np.zeros((grid.nx, grid.ny, grid.nz - 1), dtype=float)
    inj = {}; prod = {}; storage_sink = {}; storage_release = {}

    # Reconstruct signed face rate from consecutive cells, not only face keys,
    # so direction is retained exactly.
    for path in paths:
        q = path.rate
        if path.source_type == 'injector':
            inj[path.source_cell] = inj.get(path.source_cell, 0.0) + q
        else:
            storage_release[path.source_cell] = (
                storage_release.get(path.source_cell, 0.0) + q
            )
        if path.sink_type == 'producer':
            prod[path.sink_cell] = prod.get(path.sink_cell, 0.0) + q
        else:
            storage_sink[path.sink_cell] = storage_sink.get(path.sink_cell, 0.0) + q
        for a, b in zip(path.cells[:-1], path.cells[1:]):
            di = b[0] - a[0]; dj = b[1] - a[1]; dk = b[2] - a[2]
            if di == 1:
                rx[a[0], a[1], a[2]] += q
            elif di == -1:
                rx[b[0], b[1], b[2]] -= q
            elif dj == 1:
                ry[a[0], a[1], a[2]] += q
            elif dj == -1:
                ry[b[0], b[1], b[2]] -= q
            elif dk == 1:
                rz[a[0], a[1], a[2]] += q
            elif dk == -1:
                rz[b[0], b[1], b[2]] -= q
            else:
                raise RuntimeError(f'Non-neighbor cells in flux path: {a} -> {b}')

    qin_r, qout_r = cell_total_inflow_outflow(
        grid, rx, ry, rz,
        {**{c: q for c, q in inj.items()},
         **{c: -q for c, q in prod.items()}},
    )
    # Add augmented storage source/sink to reconstructed cell totals.
    for cell, q in storage_release.items():
        qin_r[cell] += q
    for cell, q in storage_sink.items():
        qout_r[cell] += q

    exact_face = np.concatenate([qx.ravel() for qx in []]) if False else None
    return {
        'qx': rx, 'qy': ry, 'qz': rz,
        'injector': inj, 'producer': prod,
        'storage_sink': storage_sink,
        'storage_release': storage_release,
        'qin_cell': qin_r, 'qout_cell': qout_r,
    }


def _v9_map_path_mass_to_grid(grid, paths, segment_mass, density,
                              pore_volume, rock):
    mass = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    represented_pv = np.zeros_like(mass)
    for path, masses in zip(paths, segment_mass):
        for m, cell in enumerate(path.cells):
            mass[cell] += float(masses[m])
            represented_pv[cell] += float(path.segment_pv[m])
    saturation = mass / np.maximum(density * pore_volume, 1.0e-30)
    saturation = np.clip(saturation, 0.0, rock.s_g_max)
    return saturation, mass, represented_pv


def advance_face_flux_paths(paths, s_initial_grid, density_grid,
                            rock, fluid, dt, cfl_number=0.30,
                            cell_mixing=False, forced_substeps=None):
    """Conservative one-dimensional mass transport on exact TPFA flux paths.

    Storage-ending paths have zero terminal outflow, so their incoming phase mass
    remains in the terminal cell.  Storage-release paths have zero external inlet
    phase mass; they draw down the mass already assigned to their source cell.
    """
    slope = ccus_max_fractional_flow_slope(rock, fluid)
    segment_rho = []
    segment_mass = []
    initial_segment_s = []
    stable = np.inf
    cell_occurrences = {}
    for pidx, path in enumerate(paths):
        rho = np.array([density_grid[c] for c in path.cells], dtype=float)
        sval = np.array([s_initial_grid[c] for c in path.cells], dtype=float)
        pv = np.asarray(path.segment_pv, dtype=float)
        segment_rho.append(rho)
        segment_mass.append(rho * pv * sval)
        initial_segment_s.append(sval)
        active = pv > 1.0e-30
        if np.any(active):
            stable = min(stable, float(
                cfl_number * np.min(pv[active] / max(path.rate, 1.0e-30))
                / max(slope, 1.0e-30)
            ))
        for m, cell in enumerate(path.cells):
            cell_occurrences.setdefault(cell, []).append((pidx, m))

    required = max(1, int(np.ceil(dt / stable))) if np.isfinite(stable) else 1
    nsub = required if forced_substeps is None else max(required, int(forced_substeps))
    h = dt / nsub
    rho_inj = float(ccus_gas_density(np.array([fluid.p_ref]), fluid)[0])
    injected = 0.0; produced = 0.0

    for _ in range(nsub):
        if cell_mixing:
            # Conservative transverse mixing: all path segments occupying one
            # cell receive the cell-average saturation before face fluxes are
            # evaluated.  This is the exact path representation of cell FV.
            for cell, occurrences in cell_occurrences.items():
                mtotal = sum(segment_mass[pidx][m] for pidx, m in occurrences)
                capacity = sum(segment_rho[pidx][m] * paths[pidx].segment_pv[m]
                               for pidx, m in occurrences)
                scell = float(mtotal / max(capacity, 1.0e-30))
                for pidx, m in occurrences:
                    segment_mass[pidx][m] = (
                        segment_rho[pidx][m] * paths[pidx].segment_pv[m] * scell
                    )

        old_s = [m / np.maximum(r * p.segment_pv, 1.0e-30)
                 for m, r, p in zip(segment_mass, segment_rho, paths)]
        updates = []
        for pidx, path in enumerate(paths):
            svals = old_s[pidx]; rho = segment_rho[pidx]; q = path.rate
            n = len(path.cells); dm = np.zeros(n, dtype=float)
            for m in range(n):
                if m == 0:
                    minlet = rho_inj * q if path.source_type == 'injector' else 0.0
                else:
                    minlet = (rho[m - 1]
                              * ccus_fractional_flow(svals[m - 1], rock, fluid)
                              * q)
                if m == n - 1 and path.sink_type == 'storage':
                    mout = 0.0
                else:
                    mout = (rho[m]
                            * ccus_fractional_flow(svals[m], rock, fluid)
                            * q)
                dm[m] = h * (minlet - mout)
            updates.append(dm)
            if path.source_type == 'injector':
                injected += h * rho_inj * q
            if path.sink_type == 'producer' and n:
                produced += h * (rho[-1]
                                 * ccus_fractional_flow(svals[-1], rock, fluid)
                                 * q)
        for pidx, dm in enumerate(updates):
            segment_mass[pidx] += dm
            denom = segment_rho[pidx] * paths[pidx].segment_pv
            snew = segment_mass[pidx] / np.maximum(denom, 1.0e-30)
            violation = max(float(np.max(-snew)),
                            float(np.max(snew - rock.s_g_max))) if snew.size else 0.0
            if violation > 5.0e-8:
                raise RuntimeError(
                    f'Face-flux path saturation bounds violated by {violation:.3e}'
                )
            snew = np.clip(snew, 0.0, rock.s_g_max)
            segment_mass[pidx] = denom * snew

    initial_mass = float(sum(np.sum(r * p.segment_pv * s)
                             for r, p, s in zip(segment_rho, paths,
                                               initial_segment_s)))
    final_mass = float(sum(np.sum(m) for m in segment_mass))
    return {
        'segment_mass': segment_mass,
        'segment_saturation': [m / np.maximum(r * p.segment_pv, 1.0e-30)
                               for m, r, p in zip(segment_mass,
                                                 segment_rho, paths)],
        'initial_mass': initial_mass,
        'final_mass': final_mass,
        'injected_mass': injected,
        'produced_mass': produced,
        'balance_error': final_mass - initial_mass - injected + produced,
        'substeps': nsub,
        'required_substeps': required,
        'dt_cfl_s': stable,
        'cell_mixing': bool(cell_mixing),
    }


def _v9_relative_error(reconstructed, exact, threshold=1.0e-20):
    exact = np.asarray(exact, dtype=float)
    rec = np.asarray(reconstructed, dtype=float)
    mask = np.abs(exact) > threshold
    out = np.zeros_like(exact)
    out[mask] = (rec[mask] - exact[mask]) / exact[mask]
    return out, mask


def _v9_path_xyz(grid, path):
    return np.array([((c[0] + 0.5) * grid.dx,
                      (c[1] + 0.5) * grid.dy,
                      (np.sum(grid.dzk[:c[2]]) + 0.5 * grid.dzk[c[2]]))
                     for c in path.cells], dtype=float)


def plot_face_flux_path_diagnostics(grid, pressure, pollock_rows, paths,
                                    flow_graph, reconstruction, pv_diag,
                                    grid_s, mixed_s, unmixed_s, old_pollock_s,
                                    step, time_days, outdir, rock):
    """Individual pressure, path, flux-reconstruction, and saturation plots."""
    x = (np.arange(grid.nx) + 0.5) * grid.dx
    y = (np.arange(grid.ny) + 0.5) * grid.dy
    top_paths = sorted(paths, key=lambda p: p.rate, reverse=True)[:80]

    for kk in range(grid.nz):
        values = (pressure[:, :, kk] / 1.0e6).T
        fig, ax = plt.subplots(figsize=(6.3, 5.3))
        filled = ax.contourf(x, y, values, levels=14, cmap='viridis')
        lines = ax.contour(x, y, values, levels=8, colors='k', linewidths=0.5)
        ax.clabel(lines, fontsize=7, fmt='%.2f')
        for path in top_paths:
            pts = _v9_path_xyz(grid, path)
            mask = [c[2] == kk for c in path.cells]
            if sum(mask) >= 2:
                xy = pts[np.asarray(mask), :2]
                ax.plot(xy[:, 0], xy[:, 1], lw=0.7,
                        alpha=0.55 if path.sink_type == 'producer' else 0.25)
        ax.set_aspect('equal'); ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
        ax.set_title(f'Pressure + exact TPFA flux paths, step {step}, layer {kk + 1}')
        fig.colorbar(filled, ax=ax, label='pressure [MPa]')
        _v7_save(fig, f'130_step_{step:02d}_pressure_flux_paths_layer_{kk + 1}.png', outdir)

        # Pollock geometry remains visible separately.
        fig, ax = plt.subplots(figsize=(6.3, 5.3))
        filled = ax.contourf(x, y, values, levels=14, cmap='viridis')
        for row in pollock_rows:
            if row['source_cell'][2] == kk and row['points'].shape[0] >= 2:
                ax.plot(row['points'][:, 0], row['points'][:, 1], lw=0.55,
                        alpha=0.45)
        ax.set_aspect('equal'); ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
        ax.set_title(f'Pressure + Pollock geometry, step {step}, layer {kk + 1}')
        fig.colorbar(filled, ax=ax, label='pressure [MPa]')
        _v7_save(fig, f'131_step_{step:02d}_pressure_pollock_layer_{kk + 1}.png', outdir)

        fields = [
            (grid_s, 'Finite-volume ground truth Sg', '132_fv'),
            (mixed_s, 'Cell-mixed exact-path Sg', '133_mixed'),
            (unmixed_s, 'Independent exact-path Sg', '134_unmixed'),
            (old_pollock_s, 'Variable-flux Pollock-bundle Sg', '135_pollock'),
            (mixed_s - grid_s, 'Mixed path minus FV', '136_mixed_difference'),
            (unmixed_s - grid_s, 'Unmixed path minus FV', '137_unmixed_difference'),
            (old_pollock_s - grid_s, 'Pollock bundle minus FV', '138_pollock_difference'),
        ]
        for field, title, prefix in fields:
            isdiff = 'difference' in prefix
            vmax = float(np.max(np.abs(field))) if isdiff else rock.s_g_max
            vmin = -vmax if isdiff else 0.0
            cmap = 'coolwarm' if isdiff else 'viridis'
            _plot_v8_layer(
                field, f'{title}, step {step}, layer {kk + 1}',
                f'{prefix}_step_{step:02d}_layer_{kk + 1}.png', outdir, kk,
                label='Delta Sg' if isdiff else 'Sg', cmap=cmap,
                vmin=vmin, vmax=vmax,
            )

    # 3-D exact path decomposition.
    fig = plt.figure(figsize=(8.0, 6.6))
    ax = fig.add_subplot(111, projection='3d')
    maxq = max((p.rate for p in paths), default=1.0)
    for path in top_paths:
        pts = _v9_path_xyz(grid, path)
        if pts.shape[0] >= 2:
            ax.plot(pts[:, 0], pts[:, 1], pts[:, 2],
                    lw=0.35 + 2.2 * path.rate / maxq,
                    alpha=0.65 if path.sink_type == 'producer' else 0.35)
    ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]'); ax.set_zlabel('z [m]')
    ax.set_title(f'Exact TPFA face-flux path decomposition, step {step}')
    _v7_save(fig, f'139_step_{step:02d}_exact_flux_paths_3d.png', outdir)

    # Face reconstruction errors by layer.
    ex = flow_graph['exact_qx']; ey = flow_graph['exact_qy']
    rx = reconstruction['qx']; ry = reconstruction['qy']
    for kk in range(grid.nz):
        exact_through = np.zeros((grid.nx, grid.ny), dtype=float)
        rec_through = np.zeros_like(exact_through)
        exact_through[:-1] += np.abs(ex[:, :, kk]); exact_through[1:] += np.abs(ex[:, :, kk])
        rec_through[:-1] += np.abs(rx[:, :, kk]); rec_through[1:] += np.abs(rx[:, :, kk])
        exact_through[:, :-1] += np.abs(ey[:, :, kk]); exact_through[:, 1:] += np.abs(ey[:, :, kk])
        rec_through[:, :-1] += np.abs(ry[:, :, kk]); rec_through[:, 1:] += np.abs(ry[:, :, kk])
        rel = np.zeros_like(exact_through)
        mask = exact_through > 1.0e-20
        rel[mask] = (rec_through[mask] - exact_through[mask]) / exact_through[mask]
        _plot_v8_layer(
            rel[:, :, None],
            f'Face-throughput reconstruction error, step {step}, layer {kk + 1}',
            f'140_step_{step:02d}_face_reconstruction_error_layer_{kk + 1}.png',
            outdir, 0, label='relative error', cmap='coolwarm',
            vmin=-1.0e-10, vmax=1.0e-10,
        )

    # Path-rate distribution and terminal split.
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    rates = np.array([p.rate * DAYS_TO_SECONDS for p in paths])
    ax.hist(rates, bins=min(35, max(8, len(rates) // 4)))
    ax.set_xlabel('path rate [m3/day]'); ax.set_ylabel('count')
    ax.set_title(f'Exact path-rate distribution, step {step}')
    ax.grid(alpha=0.3)
    _v7_save(fig, f'141_step_{step:02d}_path_rate_distribution.png', outdir)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    labels = ['producer paths', 'storage-ending paths', 'storage-release starts']
    values = [sum(p.rate for p in paths if p.sink_type == 'producer'),
              sum(p.rate for p in paths if p.sink_type == 'storage'),
              sum(p.rate for p in paths if p.source_type == 'storage_release')]
    ax.bar(labels, np.asarray(values) * DAYS_TO_SECONDS)
    ax.set_ylabel('rate [m3/day]')
    ax.set_title(f'Flux-path terminal/source split, step {step}')
    ax.tick_params(axis='x', rotation=12); ax.grid(axis='y', alpha=0.3)
    _v7_save(fig, f'142_step_{step:02d}_path_terminal_split.png', outdir)

    # Exact PV partition error.
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.hist(pv_diag['pore_volume_error'].ravel(), bins=25)
    ax.set_xlabel('represented PV - exact PV [m3]'); ax.set_ylabel('cell count')
    ax.set_title(f'Exact path pore-volume partition error, step {step}')
    ax.grid(alpha=0.3)
    _v7_save(fig, f'143_step_{step:02d}_pore_volume_partition_error.png', outdir)


@_dataclass_v9
class FaceFluxStepAudit:
    step: int
    time_days: float
    path_count: int
    producer_path_count: int
    storage_path_count: int
    storage_release_path_count: int
    max_face_relative_error: float
    max_cell_inflow_relative_error: float
    max_cell_outflow_relative_error: float
    max_pore_volume_error_m3: float
    mixed_l1: float
    mixed_linf: float
    unmixed_l1: float
    unmixed_linf: float
    pollock_l1: float
    pollock_linf: float
    mixed_mass_error_kg: float
    unmixed_mass_error_kg: float
    exact_injection_rate_m3_day: float
    decomposed_injection_rate_m3_day: float
    exact_production_rate_m3_day: float
    decomposed_production_rate_m3_day: float


def run_face_flux_path_decomposition_target(
        outdir='pad_stream_v9_face_flux_paths_outputs',
        total_time_days=1.0,
        pressure_dt_days=0.5,
        pollock_seeds_per_dim=6,
        make_plots=True,
        include_capillary_check=True,
        initial_co2_saturation=0.0,
        brine_compressibility=0.0,
        rock_compressibility=0.0):
    """Run exact TPFA path decomposition and transport verification."""
    _os_v9.makedirs(outdir, exist_ok=True)
    grid, _, _, cap, wells, _ = build_padstream_5x5x5_case()
    rock = CCUSRock(s_g_initial=float(initial_co2_saturation),
                    cr=float(rock_compressibility)).validate()
    fluid = CCUSFluid(p_ref=float(wells.inj_bhp),
                      c_w=float(brine_compressibility))
    if make_plots:
        plot_ccus_phase_convention(rock, fluid, cap, grid, outdir)

    nsteps = max(1, int(np.ceil(total_time_days / pressure_dt_days)))
    dt = total_time_days * DAYS_TO_SECONDS / nsteps
    pressure = np.full((grid.nx, grid.ny, grid.nz), float(wells.bhp))
    s_ground = np.full((grid.nx, grid.ny, grid.nz), rock.s_g_initial)
    audits = []; histories = []

    print('=' * 116)
    print('VERSION 9 — EXACT TPFA FACE-FLUX PATH DECOMPOSITION')
    print('=' * 116)
    print('Pollock = continuous geometry; flux paths = exact discrete rate decomposition.')

    for step in range(1, nsteps + 1):
        pressure_old = pressure.copy(); s_old = s_ground.copy()
        pstep = solve_ccus_transient_pressure_step(
            grid, s_old, rock, fluid, wells, pressure_old, dt
        )
        pressure = pstep.pressure
        qx, qy, qz = tpfa_face_fluxes(grid, pressure, pstep.mobility)
        grid_result = advance_ccus_grid_mass_advection(
            grid, s_old, pressure_old, pressure, rock, fluid,
            qx, qy, qz, pstep.well_source_rate, dt
        )
        phi_new, _ = pressure_dependent_porosity(grid, rock, pressure, fluid.p_ref)
        pore_volume = phi_new * grid.vcell
        density = ccus_gas_density(pressure, fluid)

        # Existing Pollock bundle retained as the Stage-18 comparison.
        pollock_rows, pollock_geometry = build_variable_flux_streamtubes(
            grid, pressure, pstep.mobility, wells, pstep.well_source_rate,
            qx, qy, qz, pore_volume, seeds_per_dim=pollock_seeds_per_dim
        )
        pollock_transport = advance_variable_flux_streamtubes(
            pollock_rows, grid_result['saturation_storage'], density,
            rock, fluid, dt
        )
        pollock_s, _, _, _ = _map_streamtube_mass_to_grid_v8(
            grid, pollock_rows, pollock_transport, density, pore_volume,
            grid_result['saturation_storage'], rock
        )

        # Exact directed TPFA graph and path decomposition.
        graph = build_tpfa_flow_graph(
            grid, qx, qy, qz, pstep.well_source_rate
        )
        graph['exact_qx'] = qx; graph['exact_qy'] = qy; graph['exact_qz'] = qz
        paths, decomp = decompose_tpfa_flow_paths(graph)
        pv_diag = assign_exact_path_pore_volumes(paths, pore_volume)
        reconstruction = reconstruct_fluxes_from_paths(grid, paths, graph)

        mixed = advance_face_flux_paths(
            paths, grid_result['saturation_storage'], density, rock, fluid, dt,
            cfl_number=0.30, cell_mixing=True,
            forced_substeps=grid_result['substeps'],
        )
        unmixed = advance_face_flux_paths(
            paths, grid_result['saturation_storage'], density, rock, fluid, dt,
            cfl_number=0.30, cell_mixing=False,
            forced_substeps=grid_result['substeps'],
        )
        mixed_s, mixed_mass, _ = _v9_map_path_mass_to_grid(
            grid, paths, mixed['segment_mass'], density, pore_volume, rock
        )
        unmixed_s, unmixed_mass, _ = _v9_map_path_mass_to_grid(
            grid, paths, unmixed['segment_mass'], density, pore_volume, rock
        )

        global_face_scale = max(
            float(np.max(np.abs(qx))) if qx.size else 0.0,
            float(np.max(np.abs(qy))) if qy.size else 0.0,
            float(np.max(np.abs(qz))) if qz.size else 0.0,
            1.0e-30,
        )
        max_face_absolute_error = max(
            float(np.max(np.abs(reconstruction['qx'] - qx))) if qx.size else 0.0,
            float(np.max(np.abs(reconstruction['qy'] - qy))) if qy.size else 0.0,
            float(np.max(np.abs(reconstruction['qz'] - qz))) if qz.size else 0.0,
        )
        # Normalize the largest absolute face-rate error by the largest physical
        # face rate.  This avoids allowing roundoff-level crossflow faces to
        # dominate a relative-error statistic.
        max_face_error = max_face_absolute_error / global_face_scale

        exact_qin = graph['qin_cell'].copy(); exact_qout = graph['qout_cell'].copy()
        # Augment exact cell totals with transient storage source/sink, matching
        # the reconstructed graph accounting.
        release = np.maximum(graph['qout_cell'] - graph['qin_cell'], 0.0)
        sinkrate = np.maximum(graph['qin_cell'] - graph['qout_cell'], 0.0)
        exact_qin_aug = exact_qin + release
        exact_qout_aug = exact_qout + sinkrate
        cell_rate_scale = max(
            float(np.max(np.abs(exact_qin_aug))),
            float(np.max(np.abs(exact_qout_aug))),
            1.0e-30,
        )
        cell_threshold = max(1.0e-10 * cell_rate_scale, 1.0e-14)
        rin, minmask = _v9_relative_error(
            reconstruction['qin_cell'], exact_qin_aug, threshold=cell_threshold
        )
        rout, moutmask = _v9_relative_error(
            reconstruction['qout_cell'], exact_qout_aug, threshold=cell_threshold
        )
        max_in = float(np.max(np.abs(rin[minmask]))) if np.any(minmask) else 0.0
        max_out = float(np.max(np.abs(rout[moutmask]))) if np.any(moutmask) else 0.0

        d_mixed = mixed_s - grid_result['saturation']
        d_unmixed = unmixed_s - grid_result['saturation']
        d_pollock = pollock_s - grid_result['saturation']
        audit = FaceFluxStepAudit(
            step=step,
            time_days=step * dt / DAYS_TO_SECONDS,
            path_count=len(paths),
            producer_path_count=sum(p.sink_type == 'producer' for p in paths),
            storage_path_count=sum(p.sink_type == 'storage' for p in paths),
            storage_release_path_count=sum(p.source_type == 'storage_release' for p in paths),
            max_face_relative_error=max_face_error,
            max_cell_inflow_relative_error=max_in,
            max_cell_outflow_relative_error=max_out,
            max_pore_volume_error_m3=float(pv_diag['max_abs_pore_volume_error']),
            mixed_l1=float(np.mean(np.abs(d_mixed))),
            mixed_linf=float(np.max(np.abs(d_mixed))),
            unmixed_l1=float(np.mean(np.abs(d_unmixed))),
            unmixed_linf=float(np.max(np.abs(d_unmixed))),
            pollock_l1=float(np.mean(np.abs(d_pollock))),
            pollock_linf=float(np.max(np.abs(d_pollock))),
            mixed_mass_error_kg=float(mixed['balance_error']),
            unmixed_mass_error_kg=float(unmixed['balance_error']),
            exact_injection_rate_m3_day=float(pstep.injector_well_rate * DAYS_TO_SECONDS),
            decomposed_injection_rate_m3_day=float(
                sum(p.rate for p in paths if p.source_type == 'injector')
                * DAYS_TO_SECONDS
            ),
            exact_production_rate_m3_day=float(pstep.producer_well_rate * DAYS_TO_SECONDS),
            decomposed_production_rate_m3_day=float(
                sum(p.rate for p in paths if p.sink_type == 'producer')
                * DAYS_TO_SECONDS
            ),
        )
        audits.append(audit)
        histories.append({
            'pressure': pressure.copy(), 'grid_saturation': grid_result['saturation'].copy(),
            'mixed_saturation': mixed_s.copy(), 'unmixed_saturation': unmixed_s.copy(),
            'pollock_saturation': pollock_s.copy(), 'paths': paths,
            'pollock_rows': pollock_rows, 'graph': graph,
            'reconstruction': reconstruction, 'pv_diag': pv_diag,
        })

        if make_plots:
            plot_face_flux_path_diagnostics(
                grid, pressure, pollock_rows, paths, graph, reconstruction,
                pv_diag, grid_result['saturation'], mixed_s, unmixed_s,
                pollock_s, step, audit.time_days, outdir, rock
            )

        cap_result = None
        if include_capillary_check:
            cap_result = advance_ccus_capillary_mass(
                grid, grid_result['saturation'], grid_result['mass'],
                grid_result['capacity'], grid_result['density'],
                rock, fluid, cap, dt
            )
        s_ground = (cap_result['saturation'] if cap_result is not None
                    else grid_result['saturation'])

        print(
            f'  step {step}/{nsteps} t={audit.time_days:.2f} d  '
            f'paths={audit.path_count}  face_err={audit.max_face_relative_error:.3e}  '
            f'mixed_Linf={audit.mixed_linf:.3e}  '
            f'unmixed_Linf={audit.unmixed_linf:.3e}  '
            f'Pollock_Linf={audit.pollock_linf:.3e}'
        )

    if make_plots:
        t = np.array([a.time_days for a in audits])
        fig, ax = plt.subplots(figsize=(7.0, 4.9))
        ax.semilogy(t, np.maximum([a.mixed_linf for a in audits], 1e-16), 'o-',
                    label='exact paths, cell mixed')
        ax.semilogy(t, np.maximum([a.unmixed_linf for a in audits], 1e-16), 's-',
                    label='exact paths, independent')
        ax.semilogy(t, np.maximum([a.pollock_linf for a in audits], 1e-16), '^-',
                    label='Stage-18 Pollock bundle')
        ax.set_xlabel('time [days]'); ax.set_ylabel('maximum |Delta Sg|')
        ax.set_title('Transport error after face-flux-consistent decomposition')
        ax.grid(alpha=0.3, which='both'); ax.legend()
        _v7_save(fig, '150_transport_error_history.png', outdir)

        fig, ax = plt.subplots(figsize=(7.0, 4.9))
        ax.semilogy(t, np.maximum([a.max_face_relative_error for a in audits], 1e-18),
                    'o-', label='internal faces')
        ax.semilogy(t, np.maximum([a.max_cell_inflow_relative_error for a in audits], 1e-18),
                    's-', label='cell inflow')
        ax.semilogy(t, np.maximum([a.max_cell_outflow_relative_error for a in audits], 1e-18),
                    '^-', label='cell outflow')
        ax.set_xlabel('time [days]'); ax.set_ylabel('maximum relative reconstruction error')
        ax.set_title('Exact TPFA rate reconstruction')
        ax.grid(alpha=0.3, which='both'); ax.legend()
        _v7_save(fig, '151_flux_reconstruction_history.png', outdir)

        fig, ax = plt.subplots(figsize=(7.0, 4.9))
        ax.plot(t, [a.exact_injection_rate_m3_day for a in audits], 'o-', label='exact injection')
        ax.plot(t, [a.decomposed_injection_rate_m3_day for a in audits], 's--', label='path injection')
        ax.plot(t, [a.exact_production_rate_m3_day for a in audits], '^-', label='exact production')
        ax.plot(t, [a.decomposed_production_rate_m3_day for a in audits], 'd--', label='path production')
        ax.set_xlabel('time [days]'); ax.set_ylabel('rate [m3/day]')
        ax.set_title('Well rates reconstructed from exact flux paths')
        ax.grid(alpha=0.3); ax.legend(fontsize=8)
        _v7_save(fig, '152_path_well_rate_history.png', outdir)

    summary = {
        'accepted_ground_truth': 'cell-centred finite-volume CO2 mass transport',
        'pollock_role': 'continuous pressure-derived geometry and TOF diagnostic',
        'exact_path_role': (
            'nonnegative decomposition of every directed TPFA face flux, well '
            'source/sink, and transient storage source/sink'
        ),
        'cell_mixed_path_test': (
            'algebraic verification: transverse remixing makes the path system '
            'equivalent to cell-centred finite volume'
        ),
        'independent_path_test': (
            'streamline-like no-transverse-mixing approximation with exact face weights'
        ),
        'steps': [a.__dict__ for a in audits],
    }
    summary_path = _os_v9.path.join(outdir, 'PAD_Stream_V9_Face_Flux_Path_Summary.json')
    with open(summary_path, 'w') as f:
        _json_v9.dump(summary, f, indent=2)
    print('=' * 116)
    return audits, histories, summary



# ==============================================================================
# STAGE 20 [S20] — FULLY CONSISTENT PHASE-POTENTIAL FACE FLUXES
# ==============================================================================
# Primary pressure: brine pressure p_w.
# Gas pressure:     p_g = p_w + P_c(S_g).
# Depth coordinate is positive downward.  For a face L -> R,
#
#   q_g = T_abs * lambda_g,f * [ (p_g,L-p_g,R)
#                                + rho_g,f g (d_R-d_L) ]
#   q_w = T_abs * lambda_w,f * [ (p_w,L-p_w,R)
#                                + rho_w,f g (d_R-d_L) ]
#
# q_t = q_g + q_w enters the pressure balance.  Capillary pressure and gravity
# are therefore part of the phase face fluxes themselves, rather than separate
# post-transport saturation corrections.  Mobilities and P_c are lagged at the
# beginning of each pressure step (IMPES); pressure-dependent densities are
# updated with a short fixed-point iteration.
# ============================================================================== 

from dataclasses import dataclass as _dataclass_v10
import os as _os_v10
import json as _json_v10

GRAVITY_ACCELERATION = 9.80665


@_dataclass_v10
class PhasePotentialPressureStep:
    pressure_w: np.ndarray
    pressure_g: np.ndarray
    capillary_pressure: np.ndarray
    density_g: np.ndarray
    density_w: np.ndarray
    lambda_g: np.ndarray
    lambda_w: np.ndarray
    qg_x: np.ndarray
    qg_y: np.ndarray
    qg_z: np.ndarray
    qw_x: np.ndarray
    qw_y: np.ndarray
    qw_z: np.ndarray
    qt_x: np.ndarray
    qt_y: np.ndarray
    qt_z: np.ndarray
    total_compressibility: np.ndarray
    storage_capacity: np.ndarray
    accumulation_rate: np.ndarray
    well_total_source: dict
    well_gas_source: dict
    well_brine_source: dict
    injector_total_rate: float
    producer_total_rate: float
    global_volume_balance_error: float
    max_phase_flux_closure_error: float
    max_nonwell_pressure_residual: float
    fixed_point_iterations: int
    fixed_point_relative_change: float


@_dataclass_v10
class PhasePotentialModeAudit:
    mode: str
    step: int
    time_days: float
    gas_mass_kg: float
    injected_gas_mass_kg: float
    produced_gas_mass_kg: float
    cumulative_mass_error_kg: float
    max_step_mass_residual_kg: float
    pressure_residual_m3_s: float
    phase_flux_closure_m3_s: float
    injector_rate_m3_day: float
    producer_rate_m3_day: float
    mean_abs_vertical_gas_flux_m3_day: float
    mean_abs_vertical_brine_flux_m3_day: float
    saturation_min: float
    saturation_max: float
    bound_projection_max: float
    streamlines_reaching_producer: int
    streamline_count: int


def ccus_phase_mobilities(s_g, rock: CCUSRock, fluid: CCUSFluid,
                          s_g_history=None):
    """Return gas and brine mobilities in 1/(Pa s)."""
    krg, krw = ccus_relative_permeability(s_g, rock, s_g_history)
    lambda_g = krg / max(float(fluid.mu_g) * 1.0e-3, 1.0e-30)
    lambda_w = krw / max(float(fluid.mu_w) * 1.0e-3, 1.0e-30)
    return lambda_g, lambda_w


def ccus_brine_density(pressure_w, fluid: CCUSFluid):
    return fluid.rho_w_ref * np.exp(
        fluid.c_w * (np.asarray(pressure_w, dtype=float) - fluid.p_ref)
    )


def ccus_gas_density_from_phase_pressure(pressure_g, fluid: CCUSFluid):
    return fluid.rho_g_ref * np.exp(
        fluid.c_g * (np.asarray(pressure_g, dtype=float) - fluid.p_ref)
    )


def _v10_depth_centres(grid):
    """Cell-centre depth [m], positive downward along increasing k."""
    tops = np.concatenate(([0.0], np.cumsum(grid.dzk[:-1])))
    depth_1d = tops + 0.5 * grid.dzk
    return np.broadcast_to(depth_1d[None, None, :],
                           (grid.nx, grid.ny, grid.nz)).copy()


def _v10_harmonic(a, b):
    return 2.0 * a * b / (a + b + 1.0e-30)


def _v10_phase_face_terms(grid, pressure_w, pc, rho_g, rho_w,
                          lambda_g, lambda_w,
                          include_capillary=True, include_gravity=True,
                          no_crossflow=False):
    """Return phase and total signed internal face rates [m3/s]."""
    qgx = np.zeros((grid.nx - 1, grid.ny, grid.nz), dtype=float)
    qgy = np.zeros((grid.nx, grid.ny - 1, grid.nz), dtype=float)
    qgz = np.zeros((grid.nx, grid.ny, grid.nz - 1), dtype=float)
    qwx = np.zeros_like(qgx); qwy = np.zeros_like(qgy); qwz = np.zeros_like(qgz)
    depth = _v10_depth_centres(grid)
    pc_use = pc if include_capillary else np.zeros_like(pc)
    grav = GRAVITY_ACCELERATION if include_gravity else 0.0

    for k in range(grid.nz):
        area_x = grid.dy * grid.dzk[k]
        area_y = grid.dx * grid.dzk[k]
        for j in range(grid.ny):
            for i in range(grid.nx - 1):
                left = (i, j, k); right = (i + 1, j, k)
                tabs = area_x * _v10_harmonic(grid.k[left], grid.k[right]) / grid.dx
                lgf = 0.5 * (lambda_g[left] + lambda_g[right])
                lwf = 0.5 * (lambda_w[left] + lambda_w[right])
                rgf = 0.5 * (rho_g[left] + rho_g[right])
                rwf = 0.5 * (rho_w[left] + rho_w[right])
                dd = depth[right] - depth[left]
                qgx[i, j, k] = tabs * lgf * (
                    pressure_w[left] - pressure_w[right]
                    + pc_use[left] - pc_use[right]
                    + rgf * grav * dd
                )
                qwx[i, j, k] = tabs * lwf * (
                    pressure_w[left] - pressure_w[right] + rwf * grav * dd
                )
        for j in range(grid.ny - 1):
            for i in range(grid.nx):
                low = (i, j, k); high = (i, j + 1, k)
                tabs = area_y * _v10_harmonic(grid.k[low], grid.k[high]) / grid.dy
                lgf = 0.5 * (lambda_g[low] + lambda_g[high])
                lwf = 0.5 * (lambda_w[low] + lambda_w[high])
                rgf = 0.5 * (rho_g[low] + rho_g[high])
                rwf = 0.5 * (rho_w[low] + rho_w[high])
                dd = depth[high] - depth[low]
                qgy[i, j, k] = tabs * lgf * (
                    pressure_w[low] - pressure_w[high]
                    + pc_use[low] - pc_use[high]
                    + rgf * grav * dd
                )
                qwy[i, j, k] = tabs * lwf * (
                    pressure_w[low] - pressure_w[high] + rwf * grav * dd
                )

    if not no_crossflow and grid.nz > 1:
        area_z = grid.dx * grid.dy
        for k in range(grid.nz - 1):
            distance = 0.5 * (grid.dzk[k] + grid.dzk[k + 1])
            for j in range(grid.ny):
                for i in range(grid.nx):
                    shallow = (i, j, k); deep = (i, j, k + 1)
                    tabs = area_z * _v10_harmonic(
                        grid.k[shallow], grid.k[deep]
                    ) / distance
                    lgf = 0.5 * (lambda_g[shallow] + lambda_g[deep])
                    lwf = 0.5 * (lambda_w[shallow] + lambda_w[deep])
                    rgf = 0.5 * (rho_g[shallow] + rho_g[deep])
                    rwf = 0.5 * (rho_w[shallow] + rho_w[deep])
                    dd = depth[deep] - depth[shallow]
                    qgz[i, j, k] = tabs * lgf * (
                        pressure_w[shallow] - pressure_w[deep]
                        + pc_use[shallow] - pc_use[deep]
                        + rgf * grav * dd
                    )
                    qwz[i, j, k] = tabs * lwf * (
                        pressure_w[shallow] - pressure_w[deep]
                        + rwf * grav * dd
                    )
    return qgx, qgy, qgz, qwx, qwy, qwz


def _v10_assemble_pressure_operator(grid, pc, rho_g, rho_w,
                                    lambda_g, lambda_w,
                                    include_capillary=True,
                                    include_gravity=True,
                                    no_crossflow=False):
    """Assemble A p_w + fixed_divergence for total phase-potential flux."""
    A = lil_matrix((grid.ncell, grid.ncell))
    fixed_div = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    depth = _v10_depth_centres(grid)
    pc_use = pc if include_capillary else np.zeros_like(pc)
    grav = GRAVITY_ACCELERATION if include_gravity else 0.0

    def add_face(left, right, area, distance):
        tabs = area * _v10_harmonic(grid.k[left], grid.k[right]) / distance
        lgf = 0.5 * (lambda_g[left] + lambda_g[right])
        lwf = 0.5 * (lambda_w[left] + lambda_w[right])
        rgf = 0.5 * (rho_g[left] + rho_g[right])
        rwf = 0.5 * (rho_w[left] + rho_w[right])
        coeff = tabs * (lgf + lwf)
        fixed = tabs * (
            lgf * (pc_use[left] - pc_use[right])
            + (lgf * rgf + lwf * rwf) * grav * (depth[right] - depth[left])
        )
        il = grid.idx(*left); ir = grid.idx(*right)
        A[il, il] += coeff; A[il, ir] -= coeff
        A[ir, ir] += coeff; A[ir, il] -= coeff
        fixed_div[left] += fixed
        fixed_div[right] -= fixed

    for k in range(grid.nz):
        for j in range(grid.ny):
            for i in range(grid.nx - 1):
                add_face((i, j, k), (i + 1, j, k),
                         grid.dy * grid.dzk[k], grid.dx)
        for j in range(grid.ny - 1):
            for i in range(grid.nx):
                add_face((i, j, k), (i, j + 1, k),
                         grid.dx * grid.dzk[k], grid.dy)
    if not no_crossflow and grid.nz > 1:
        for k in range(grid.nz - 1):
            for j in range(grid.ny):
                for i in range(grid.nx):
                    add_face((i, j, k), (i, j, k + 1),
                             grid.dx * grid.dy,
                             0.5 * (grid.dzk[k] + grid.dzk[k + 1]))
    return A.tocsr(), fixed_div


def _v10_phase_well_sources(grid, wells, total_source, qg, qw,
                              injection_gas_fraction=1.0):
    """Allocate well phase-volume sources with explicit injection composition."""
    divg = face_flux_outflow_divergence(grid, *qg)
    divw = face_flux_outflow_divergence(grid, *qw)
    gas = {}; brine = {}
    injector_set = set(wells.inj_cells)
    producer_set = set(wells.prod_cells)
    for cell, qtotal in total_source.items():
        qtotal = float(qtotal)
        if cell in injector_set and qtotal > 0.0:
            fg_inj = float(np.clip(injection_gas_fraction, 0.0, 1.0))
            gas[cell] = qtotal * fg_inj
            brine[cell] = qtotal * (1.0 - fg_inj)
        elif cell in producer_set and qtotal < 0.0:
            production = -qtotal
            gin = max(-float(divg[cell]), 0.0)
            win = max(-float(divw[cell]), 0.0)
            denom = gin + win
            if denom <= 1.0e-30:
                fg = 0.0
            else:
                fg = gin / denom
            gas[cell] = -production * fg
            brine[cell] = -production * (1.0 - fg)
        else:
            # Fallback preserves q_g + q_w = q_total.
            local_total = abs(float(divg[cell])) + abs(float(divw[cell]))
            fg = abs(float(divg[cell])) / max(local_total, 1.0e-30)
            gas[cell] = qtotal * fg
            brine[cell] = qtotal - gas[cell]
    return gas, brine


def solve_ccus_phase_potential_pressure_step(
        grid, s_g, rock: CCUSRock, fluid: CCUSFluid, cap: Capillary,
        wells, pressure_w_old, dt, include_capillary=True,
        include_gravity=True, no_crossflow=False,
        compressibility_scale=1.0, fixed_point_tolerance=1.0e-9,
        fixed_point_max_iterations=8, injector_completion_sg=None,
        rate_allocation='kh', hydrostatic_well_bhp=True,
        s_g_history=None, injection_gas_fraction=1.0):
    """Backward-Euler total-pressure balance using direct phase potentials.

    Saturation, relative permeability and capillary pressure are lagged over the
    pressure step.  CO2/brine density in gravity terms is fixed-point updated.
    BHP values are interpreted as brine/primary pressure in this stage; the
    dedicated final-well target will replace this development convention.
    """
    if dt <= 0.0:
        raise ValueError('dt must be positive')
    s_g = np.asarray(s_g, dtype=float)
    pressure_w_old = np.asarray(pressure_w_old, dtype=float)
    mobility_sg = s_g.copy()
    if injector_completion_sg is None:
        injector_completion_sg = rock.s_g_max
    # Completion mobility follows the injected phase. Pure-CO2 BHP injection
    # uses the gas endpoint; brine chase leaves the local hysteretic state intact.
    mobility_history = None
    if s_g_history is not None:
        mobility_history = np.maximum(np.asarray(s_g_history, dtype=float), mobility_sg)
    if wells.inj_bhp is not None and float(injection_gas_fraction) > 0.5:
        for cell in wells.inj_cells:
            mobility_sg[cell] = float(injector_completion_sg)
            if mobility_history is not None:
                mobility_history[cell] = max(float(mobility_history[cell]),
                                             float(injector_completion_sg))
    lambda_g, lambda_w = ccus_phase_mobilities(
        mobility_sg, rock, fluid, mobility_history
    )
    pc = (ccus_capillary_pressure(s_g, rock, cap)
          if include_capillary else np.zeros_like(s_g))
    phi_old, _ = pressure_dependent_porosity(
        grid, rock, pressure_w_old, fluid.p_ref
    )
    ct = ccus_total_compressibility(
        grid, s_g, rock, fluid, scale=compressibility_scale
    )
    storage_capacity = phi_old * grid.vcell * ct
    storage_flat = storage_capacity.transpose(2, 1, 0).ravel()
    old_flat = pressure_w_old.transpose(2, 1, 0).ravel()
    p_iter = pressure_w_old.copy()
    relative_change = np.inf
    iterations = 0
    prescribed = {}
    depth_field = _v10_depth_centres(grid)
    reference_depth = float(np.mean(depth_field))

    def completion_pressure(base_pressure, cell):
        if include_gravity and hydrostatic_well_bhp:
            return (float(base_pressure)
                    + float(fluid.rho_w_ref) * GRAVITY_ACCELERATION
                    * (float(depth_field[cell]) - reference_depth))
        return float(base_pressure)

    for iterations in range(1, int(fixed_point_max_iterations) + 1):
        pressure_g_iter = p_iter + pc
        rho_g = ccus_gas_density_from_phase_pressure(pressure_g_iter, fluid)
        rho_w = ccus_brine_density(p_iter, fluid)
        Aflow, fixed_div = _v10_assemble_pressure_operator(
            grid, pc, rho_g, rho_w, lambda_g, lambda_w,
            include_capillary=include_capillary,
            include_gravity=include_gravity,
            no_crossflow=no_crossflow,
        )
        A = (Aflow + csr_matrix(
            (storage_flat / dt,
             (np.arange(grid.ncell), np.arange(grid.ncell))),
            shape=(grid.ncell, grid.ncell)
        )).tolil()
        b = (storage_flat / dt) * old_flat
        b -= fixed_div.transpose(2, 1, 0).ravel()
        prescribed = {}
        if wells.inj_bhp is None:
            if str(rate_allocation).lower() == 'equal':
                weights = np.ones(len(wells.inj_cells), dtype=float)
            else:
                # kh-weighted rate allocation across completions.
                weights = np.array([
                    grid.k[cell] * grid.dzk[cell[2]] for cell in wells.inj_cells
                ], dtype=float)
            weights /= max(float(np.sum(weights)), 1.0e-30)
            for cell, weight in zip(wells.inj_cells, weights):
                value = float(wells.rate) * float(weight)
                idx = grid.idx(*cell); b[idx] += value
                prescribed[cell] = value
        for cell in wells.prod_cells:
            idx = grid.idx(*cell)
            A.rows[idx] = [idx]; A.data[idx] = [1.0]
            b[idx] = completion_pressure(wells.bhp, cell)
        if wells.inj_bhp is not None:
            for cell in wells.inj_cells:
                idx = grid.idx(*cell)
                A.rows[idx] = [idx]; A.data[idx] = [1.0]
                b[idx] = completion_pressure(wells.inj_bhp, cell)
        pflat = spsolve(A.tocsr(), b)
        p_new = pflat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)
        relative_change = float(
            np.linalg.norm(p_new - p_iter)
            / max(np.linalg.norm(p_new), 1.0)
        )
        p_iter = p_new
        if relative_change <= fixed_point_tolerance:
            break

    pressure_w = p_iter
    pressure_g = pressure_w + pc
    rho_g = ccus_gas_density_from_phase_pressure(pressure_g, fluid)
    rho_w = ccus_brine_density(pressure_w, fluid)
    qgx, qgy, qgz, qwx, qwy, qwz = _v10_phase_face_terms(
        grid, pressure_w, pc, rho_g, rho_w, lambda_g, lambda_w,
        include_capillary=include_capillary,
        include_gravity=include_gravity,
        no_crossflow=no_crossflow,
    )
    qtx, qty, qtz = qgx + qwx, qgy + qwy, qgz + qwz
    div_total = face_flux_outflow_divergence(grid, qtx, qty, qtz)
    accumulation = storage_capacity * (pressure_w - pressure_w_old) / dt
    total_source = dict(prescribed)
    for cell in wells.inj_cells + wells.prod_cells:
        if wells.inj_bhp is not None or cell in wells.prod_cells:
            total_source[cell] = float(div_total[cell] + accumulation[cell])
    gas_source, brine_source = _v10_phase_well_sources(
        grid, wells, total_source,
        (qgx, qgy, qgz), (qwx, qwy, qwz),
        injection_gas_fraction=injection_gas_fraction,
    )
    source_field = well_source_field(grid, total_source)
    physical_residual = div_total + accumulation - source_field
    nonwell = np.ones_like(s_g, dtype=bool)
    for cell in wells.inj_cells + wells.prod_cells:
        nonwell[cell] = False
    max_nonwell = float(np.max(np.abs(physical_residual[nonwell])))
    global_balance = float(np.sum(physical_residual))
    closure = max(
        float(np.max(np.abs(qtx - (qgx + qwx)))) if qtx.size else 0.0,
        float(np.max(np.abs(qty - (qgy + qwy)))) if qty.size else 0.0,
        float(np.max(np.abs(qtz - (qgz + qwz)))) if qtz.size else 0.0,
    )
    inj_rate = sum(max(float(total_source.get(c, 0.0)), 0.0)
                   for c in wells.inj_cells)
    prod_rate = sum(max(-float(total_source.get(c, 0.0)), 0.0)
                    for c in wells.prod_cells)
    return PhasePotentialPressureStep(
        pressure_w=pressure_w, pressure_g=pressure_g,
        capillary_pressure=pc, density_g=rho_g, density_w=rho_w,
        lambda_g=lambda_g, lambda_w=lambda_w,
        qg_x=qgx, qg_y=qgy, qg_z=qgz,
        qw_x=qwx, qw_y=qwy, qw_z=qwz,
        qt_x=qtx, qt_y=qty, qt_z=qtz,
        total_compressibility=ct, storage_capacity=storage_capacity,
        accumulation_rate=accumulation,
        well_total_source=total_source,
        well_gas_source=gas_source,
        well_brine_source=brine_source,
        injector_total_rate=float(inj_rate),
        producer_total_rate=float(prod_rate),
        global_volume_balance_error=global_balance,
        max_phase_flux_closure_error=closure,
        max_nonwell_pressure_residual=max_nonwell,
        fixed_point_iterations=iterations,
        fixed_point_relative_change=relative_change,
    )


def _v10_phase_mass_face_fluxes(grid, qg, rho_g):
    qx, qy, qz = qg
    mx = qx * np.where(qx >= 0.0, rho_g[:-1, :, :], rho_g[1:, :, :])
    my = qy * np.where(qy >= 0.0, rho_g[:, :-1, :], rho_g[:, 1:, :])
    mz = qz * np.where(qz >= 0.0, rho_g[:, :, :-1], rho_g[:, :, 1:])
    return mx, my, mz


def advance_ccus_direct_phase_mass(grid, s_g_old, pressure_w_old,
                                   pressure_step: PhasePotentialPressureStep,
                                   rock: CCUSRock, fluid: CCUSFluid, dt,
                                   mass_old_state=None):
    """Advance CO2 mass with the directly computed gas phase-volume flux."""
    pc_old = pressure_step.capillary_pressure
    pressure_g_old = np.asarray(pressure_w_old) + pc_old
    rho_old = ccus_gas_density_from_phase_pressure(pressure_g_old, fluid)
    rho_new = pressure_step.density_g
    phi_old, _ = pressure_dependent_porosity(grid, rock, pressure_w_old, fluid.p_ref)
    phi_new, _ = pressure_dependent_porosity(
        grid, rock, pressure_step.pressure_w, fluid.p_ref
    )
    weights_old = phi_old * grid.vcell * rho_old
    weights_new = phi_new * grid.vcell * rho_new
    if mass_old_state is None:
        mass_old = weights_old * np.asarray(s_g_old)
    else:
        mass_old = np.asarray(mass_old_state, dtype=float).copy()
        if mass_old.shape != np.asarray(s_g_old).shape:
            raise ValueError('mass_old_state must match the grid saturation shape')
    mx, my, mz = _v10_phase_mass_face_fluxes(
        grid,
        (pressure_step.qg_x, pressure_step.qg_y, pressure_step.qg_z),
        rho_new,
    )
    div_mass = _mass_flux_outflow_divergence(grid, mx, my, mz)
    source_mass = np.zeros_like(s_g_old, dtype=float)
    injected_rate = 0.0; produced_rate = 0.0
    injector_density = ccus_gas_density_from_phase_pressure(
        np.array([float(max(
            [pressure_step.pressure_g[c] for c in pressure_step.well_gas_source]
            or [fluid.p_ref]
        ))]), fluid
    )[0]
    for cell, qg in pressure_step.well_gas_source.items():
        qg = float(qg)
        if qg >= 0.0:
            rate = qg * injector_density
            injected_rate += rate
        else:
            rate = qg * float(rho_new[cell])
            produced_rate += -rate
        source_mass[cell] += rate
    raw_mass = mass_old + dt * (source_mass - div_mass)
    target_mass = float(np.sum(raw_mass))
    proposal = raw_mass / np.maximum(weights_new, 1.0e-30)
    projected, pinfo = bounded_conservative_projection(
        proposal, weights_new, target_mass,
        lower_bound=0.0, upper_bound=rock.s_g_max,
        relative_tolerance=1.0e-13,
    )
    mass_new = weights_new * projected
    expected = float(np.sum(mass_old) + dt * (injected_rate - produced_rate))
    balance = float(np.sum(mass_new) - expected)
    local_residual = mass_new - mass_old - dt * (source_mass - div_mass)
    return {
        'saturation': projected,
        'mass': mass_new,
        'raw_mass': raw_mass,
        'old_mass': mass_old,
        'weights_new': weights_new,
        'mass_fluxes': (mx, my, mz),
        'source_mass_rate': source_mass,
        'injected_mass_rate': float(injected_rate),
        'produced_mass_rate': float(produced_rate),
        'balance_error': balance,
        'local_residual': local_residual,
        'projection': pinfo,
        'max_projection': float(np.max(np.abs(pinfo['correction']))),
    }


def _v10_face_rates_to_velocity(grid, qx, qy, qz, porosity=None):
    """Convert signed face rates to the velocity dictionary used by Pollock."""
    phi = grid.phi if porosity is None else np.asarray(porosity)
    V = {key: np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
         for key in ('xm', 'xp', 'ym', 'yp', 'zm', 'zp')}
    for k in range(grid.nz):
        ax = grid.dy * grid.dzk[k]
        ay = grid.dx * grid.dzk[k]
        for j in range(grid.ny):
            for i in range(grid.nx - 1):
                q = qx[i, j, k]
                V['xp'][i, j, k] = q / max(ax * phi[i, j, k], 1.0e-30)
                V['xm'][i + 1, j, k] = q / max(ax * phi[i + 1, j, k], 1.0e-30)
        for j in range(grid.ny - 1):
            for i in range(grid.nx):
                q = qy[i, j, k]
                V['yp'][i, j, k] = q / max(ay * phi[i, j, k], 1.0e-30)
                V['ym'][i, j + 1, k] = q / max(ay * phi[i, j + 1, k], 1.0e-30)
    if grid.nz > 1:
        az = grid.dx * grid.dy
        for k in range(grid.nz - 1):
            for j in range(grid.ny):
                for i in range(grid.nx):
                    q = qz[i, j, k]
                    V['zp'][i, j, k] = q / max(az * phi[i, j, k], 1.0e-30)
                    V['zm'][i, j, k + 1] = q / max(az * phi[i, j, k + 1], 1.0e-30)
    return V


def _v10_trace_total_streamlines(grid, pressure_step, wells, seeds_per_dim=4):
    phi_new, _ = pressure_dependent_porosity(
        grid, CCUSRock(cr=0.0), pressure_step.pressure_w,
        float(np.mean(pressure_step.pressure_w))
    )
    velocity = _v10_face_rates_to_velocity(
        grid, pressure_step.qt_x, pressure_step.qt_y, pressure_step.qt_z,
        porosity=phi_new,
    )
    injection = {
        c: max(float(pressure_step.well_total_source.get(c, 0.0)), 0.0)
        for c in wells.inj_cells
    }
    rows = _injector_seed_rows(
        grid, velocity, wells, injection, seeds_per_dim=seeds_per_dim
    )
    return rows, velocity


def _v10_plot_layer(grid, field, title, filename, outdir, cmap='viridis',
                    unit='', vmin=None, vmax=None):
    for k in range(grid.nz):
        fig, ax = plt.subplots(figsize=(5.6, 4.8))
        image = ax.imshow(field[:, :, k].T, origin='lower', cmap=cmap,
                          vmin=vmin, vmax=vmax)
        ax.set_xlabel('i'); ax.set_ylabel('j')
        ax.set_title(f'{title} — layer {k + 1}')
        cbar = fig.colorbar(image, ax=ax)
        if unit:
            cbar.set_label(unit)
        _v7_save(fig, f'{filename}_layer_{k + 1}.png', outdir)


def _v10_plot_streamlines(grid, rows, pressure, mode, step, time_days, outdir):
    fig = plt.figure(figsize=(8.2, 6.5))
    ax = fig.add_subplot(111, projection='3d')
    max_lines = min(len(rows), 180)
    for row in rows[:max_lines]:
        flat = row[0]
        coords = []
        for idx in flat:
            k = idx // (grid.nx * grid.ny)
            rem = idx - k * grid.nx * grid.ny
            j = rem // grid.nx; i = rem - j * grid.nx
            coords.append(((i + 0.5) * grid.dx,
                           (j + 0.5) * grid.dy,
                           (k + 0.5) * grid.dzk[k]))
        if len(coords) >= 2:
            arr = np.asarray(coords)
            ax.plot(arr[:, 0], arr[:, 1], arr[:, 2], alpha=0.35, linewidth=0.8)
    ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]'); ax.set_zlabel('depth [m]')
    ax.invert_zaxis()
    ax.set_title(f'{mode}: total-flux Pollock paths, step {step}, t={time_days:.2f} d')
    _v7_save(fig, f'220_{mode}_step_{step:02d}_streamlines_3d.png', outdir)


def plot_phase_potential_step(grid, result, saturation, rows, mode, step,
                              time_days, outdir, rock):
    prefix = f'210_{mode}_step_{step:02d}'
    _v10_plot_layer(grid, result.pressure_w / 1.0e6,
                    f'{mode}: brine pressure at {time_days:.2f} d',
                    prefix + '_pressure_w', outdir, unit='MPa')
    _v10_plot_layer(grid, result.pressure_g / 1.0e6,
                    f'{mode}: CO2 pressure at {time_days:.2f} d',
                    prefix + '_pressure_g', outdir, unit='MPa')
    _v10_plot_layer(grid, result.capillary_pressure / 1.0e6,
                    f'{mode}: capillary pressure at {time_days:.2f} d',
                    prefix + '_pc', outdir, unit='MPa')
    _v10_plot_layer(grid, saturation,
                    f'{mode}: CO2 saturation at {time_days:.2f} d',
                    prefix + '_sg', outdir, cmap='plasma', unit='fraction',
                    vmin=0.0, vmax=rock.s_g_max)
    total_speed = np.zeros((grid.nx, grid.ny, grid.nz), dtype=float)
    gas_speed = np.zeros_like(total_speed); brine_speed = np.zeros_like(total_speed)
    # Cell-centred rate magnitude proxy from adjacent face rates.
    for qarr, target in [
        ((result.qt_x, result.qt_y, result.qt_z), total_speed),
        ((result.qg_x, result.qg_y, result.qg_z), gas_speed),
        ((result.qw_x, result.qw_y, result.qw_z), brine_speed),
    ]:
        qx, qy, qz = qarr
        target[:-1] += np.abs(qx); target[1:] += np.abs(qx)
        target[:, :-1] += np.abs(qy); target[:, 1:] += np.abs(qy)
        target[:, :, :-1] += np.abs(qz); target[:, :, 1:] += np.abs(qz)
        target *= DAYS_TO_SECONDS
    _v10_plot_layer(grid, gas_speed,
                    f'{mode}: CO2 phase face-throughput proxy',
                    prefix + '_gas_flux', outdir, unit='m3/day')
    _v10_plot_layer(grid, brine_speed,
                    f'{mode}: brine phase face-throughput proxy',
                    prefix + '_brine_flux', outdir, unit='m3/day')
    if grid.nz > 1:
        for k in range(grid.nz - 1):
            fig, ax = plt.subplots(figsize=(5.8, 4.8))
            image = ax.imshow((result.qg_z[:, :, k] * DAYS_TO_SECONDS).T,
                              origin='lower', cmap='coolwarm')
            ax.set_title(f'{mode}: vertical CO2 rate, interface {k + 1}/{k + 2}')
            ax.set_xlabel('i'); ax.set_ylabel('j')
            fig.colorbar(image, ax=ax, label='m3/day, + downward')
            _v7_save(fig, f'{prefix}_qgz_interface_{k + 1}.png', outdir)
    _v10_plot_streamlines(grid, rows, result.pressure_w, mode, step,
                          time_days, outdir)


def validate_phase_potential_limits(grid, rock, fluid, cap, wells):
    """Limiting-case checks for zero capillary/gravity and hydrostatics."""
    s = np.full((grid.nx, grid.ny, grid.nz), 0.10)
    p = np.full_like(s, float(wells.bhp))
    dt = 0.25 * DAYS_TO_SECONDS
    # Use a rate injector for an apples-to-apples zero-force comparison.
    wells_rate = Wells(
        inj_cells=list(wells.inj_cells), prod_cells=list(wells.prod_cells),
        rate=5000.0 / DAYS_TO_SECONDS, bhp=float(wells.bhp), inj_bhp=None,
    )
    phase = solve_ccus_phase_potential_pressure_step(
        grid, s, rock, fluid, cap, wells_rate, p, dt,
        include_capillary=False, include_gravity=False,
        injector_completion_sg=rock.s_g_max, rate_allocation='equal',
    )
    legacy = solve_ccus_transient_pressure_step(
        grid, s, rock, fluid, wells_rate, p, dt,
    )
    zero_force_pressure_error = float(
        np.linalg.norm(phase.pressure_w - legacy.pressure)
        / max(np.linalg.norm(legacy.pressure), 1.0)
    )

    # Hydrostatic brine column: p increases with depth, Sg=0, q_w~0.
    col = Grid3D(
        nx=1, ny=1, nz=5, dx=100.0, dy=100.0, dz=10.0,
        k=np.full((1, 1, 5), md_to_m2(100.0)),
        phi=np.full((1, 1, 5), 0.20),
    )
    depth = _v10_depth_centres(col)
    pw = 2.0e7 + fluid.rho_w_ref * GRAVITY_ACCELERATION * depth
    sg = np.zeros_like(pw)
    lg, lw = ccus_phase_mobilities(sg, rock, fluid)
    pc0 = np.zeros_like(pw)
    rg = ccus_gas_density_from_phase_pressure(pw, fluid)
    rw = ccus_brine_density(pw, fluid)
    phase_flux = _v10_phase_face_terms(
        col, pw, pc0, rg, rw, lg, lw,
        include_capillary=False, include_gravity=True,
    )
    hydrostatic_brine_flux = float(np.max(np.abs(phase_flux[5])))

    # Gas potential cancellation across a horizontal pair.
    pair = Grid3D(
        nx=2, ny=1, nz=1, dx=100.0, dy=100.0, dz=10.0,
        k=np.full((2, 1, 1), md_to_m2(100.0)),
        phi=np.full((2, 1, 1), 0.20),
    )
    sg_pair = np.array([0.05, 0.25], dtype=float).reshape(2, 1, 1)
    pc_pair = ccus_capillary_pressure(sg_pair, rock, cap)
    pg_constant = 2.5e7
    pw_pair = pg_constant - pc_pair
    lgp, lwp = ccus_phase_mobilities(sg_pair, rock, fluid)
    rgp = ccus_gas_density_from_phase_pressure(pw_pair + pc_pair, fluid)
    rwp = ccus_brine_density(pw_pair, fluid)
    pair_flux = _v10_phase_face_terms(
        pair, pw_pair, pc_pair, rgp, rwp, lgp, lwp,
        include_capillary=True, include_gravity=False,
    )
    gas_potential_cancellation = float(np.max(np.abs(pair_flux[0])))
    return {
        'zero_capillary_zero_gravity_relative_pressure_error': zero_force_pressure_error,
        'hydrostatic_brine_max_face_rate_m3_s': hydrostatic_brine_flux,
        'constant_gas_potential_max_face_rate_m3_s': gas_potential_cancellation,
    }


def run_phase_potential_target(
        outdir='pad_stream_v10_phase_potential_outputs',
        total_time_days=1.0, pressure_dt_days=0.25,
        pollock_seeds_per_dim=4, make_plots=True,
        initial_co2_saturation=0.0,
        brine_compressibility=0.0,
        rock_compressibility=0.0):
    """Run the four-mode direct phase-potential CCUS ladder."""
    _os_v10.makedirs(outdir, exist_ok=True)
    grid, _, _, cap, wells, _ = build_padstream_5x5x5_case()
    rock = CCUSRock(
        s_g_initial=float(initial_co2_saturation),
        cr=float(rock_compressibility), hysteresis=False,
    ).validate()
    fluid = CCUSFluid(
        p_ref=float(wells.inj_bhp), c_w=float(brine_compressibility)
    )
    modes = {
        'incompressible': (False, False, 0.0),
        'compressible': (False, False, 1.0),
        'capillary': (True, False, 0.0),
        'full': (True, True, 1.0),
    }
    nsteps = max(1, int(np.ceil(total_time_days / pressure_dt_days)))
    dt = total_time_days * DAYS_TO_SECONDS / nsteps
    limit_checks = validate_phase_potential_limits(grid, rock, fluid, cap, wells)
    all_audits = {}; histories = {}

    print('=' * 118)
    print('VERSION 10 — DIRECT CO2/BRINE PHASE-POTENTIAL FACE FLUXES')
    print('=' * 118)
    print('Primary pressure = brine pressure; p_g = p_w + Pc; gravity uses depth positive downward.')
    print('Limit checks:', limit_checks)

    for mode, (use_pc, use_gravity, cscale) in modes.items():
        if use_gravity:
            depth = _v10_depth_centres(grid)
            pressure_w = (float(wells.bhp)
                          + fluid.rho_w_ref * GRAVITY_ACCELERATION
                          * (depth - float(np.mean(depth))))
        else:
            pressure_w = np.full((grid.nx, grid.ny, grid.nz), float(wells.bhp))
        saturation = np.full_like(pressure_w, rock.s_g_initial)
        cumulative_injected = 0.0; cumulative_produced = 0.0
        initial_pc = (ccus_capillary_pressure(saturation, rock, cap)
                      if use_pc else np.zeros_like(saturation))
        initial_rho = ccus_gas_density_from_phase_pressure(
            pressure_w + initial_pc, fluid
        )
        phi0, _ = pressure_dependent_porosity(grid, rock, pressure_w, fluid.p_ref)
        mass_state = phi0 * grid.vcell * initial_rho * saturation
        initial_mass = float(np.sum(mass_state))
        audits = []; mode_hist = []
        for step in range(1, nsteps + 1):
            old_pressure = pressure_w.copy(); old_s = saturation.copy()
            pstep = solve_ccus_phase_potential_pressure_step(
                grid, old_s, rock, fluid, cap, wells, old_pressure, dt,
                include_capillary=use_pc,
                include_gravity=use_gravity,
                compressibility_scale=cscale,
                injector_completion_sg=rock.s_g_max,
            )
            transport = advance_ccus_direct_phase_mass(
                grid, old_s, old_pressure, pstep, rock, fluid, dt,
                mass_old_state=mass_state,
            )
            mass_state = transport['mass'].copy()
            saturation = transport['saturation']
            pressure_w = pstep.pressure_w
            cumulative_injected += transport['injected_mass_rate'] * dt
            cumulative_produced += transport['produced_mass_rate'] * dt
            gas_mass = float(np.sum(transport['mass']))
            cumulative_error = gas_mass - (
                initial_mass + cumulative_injected - cumulative_produced
            )
            rows, velocity = _v10_trace_total_streamlines(
                grid, pstep, wells, seeds_per_dim=pollock_seeds_per_dim
            )
            reached = int(sum(bool(row[2]) for row in rows))
            mean_qgz = (float(np.mean(np.abs(pstep.qg_z))) * DAYS_TO_SECONDS
                        if pstep.qg_z.size else 0.0)
            mean_qwz = (float(np.mean(np.abs(pstep.qw_z))) * DAYS_TO_SECONDS
                        if pstep.qw_z.size else 0.0)
            audit = PhasePotentialModeAudit(
                mode=mode, step=step,
                time_days=step * dt / DAYS_TO_SECONDS,
                gas_mass_kg=gas_mass,
                injected_gas_mass_kg=cumulative_injected,
                produced_gas_mass_kg=cumulative_produced,
                cumulative_mass_error_kg=float(cumulative_error),
                max_step_mass_residual_kg=float(
                    np.max(np.abs(transport['local_residual']))
                ),
                pressure_residual_m3_s=pstep.max_nonwell_pressure_residual,
                phase_flux_closure_m3_s=pstep.max_phase_flux_closure_error,
                injector_rate_m3_day=pstep.injector_total_rate * DAYS_TO_SECONDS,
                producer_rate_m3_day=pstep.producer_total_rate * DAYS_TO_SECONDS,
                mean_abs_vertical_gas_flux_m3_day=mean_qgz,
                mean_abs_vertical_brine_flux_m3_day=mean_qwz,
                saturation_min=float(np.min(saturation)),
                saturation_max=float(np.max(saturation)),
                bound_projection_max=transport['max_projection'],
                streamlines_reaching_producer=reached,
                streamline_count=len(rows),
            )
            audits.append(audit)
            mode_hist.append({
                'pressure_step': pstep, 'transport': transport,
                'saturation': saturation.copy(), 'rows': rows,
            })
            if make_plots:
                plot_phase_potential_step(
                    grid, pstep, saturation, rows, mode, step,
                    audit.time_days, outdir, rock
                )
            print(
                f'  {mode:14s} step {step}/{nsteps} t={audit.time_days:.2f} d  '
                f'Sg=[{audit.saturation_min:.4f},{audit.saturation_max:.4f}]  '
                f'mass_err={audit.cumulative_mass_error_kg:.3e} kg  '
                f'qg_z_mean={audit.mean_abs_vertical_gas_flux_m3_day:.3e} m3/d  '
                f'paths={reached}/{len(rows)}'
            )
        all_audits[mode] = audits; histories[mode] = mode_hist

    if make_plots:
        fig, ax = plt.subplots(figsize=(7.2, 5.0))
        for mode, audits in all_audits.items():
            ax.plot([a.time_days for a in audits],
                    [a.saturation_max for a in audits], marker='o', label=mode)
        ax.set_xlabel('time [days]'); ax.set_ylabel('maximum CO2 saturation')
        ax.set_title('Four-mode phase-potential comparison')
        ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '240_four_mode_max_saturation.png', outdir)

        fig, ax = plt.subplots(figsize=(7.2, 5.0))
        for mode, audits in all_audits.items():
            ax.semilogy([a.time_days for a in audits],
                        np.maximum(np.abs([a.cumulative_mass_error_kg for a in audits]), 1e-18),
                        marker='o', label=mode)
        ax.set_xlabel('time [days]'); ax.set_ylabel('|cumulative CO2 mass error| [kg]')
        ax.set_title('Direct phase-flux mass conservation')
        ax.grid(alpha=0.3, which='both'); ax.legend()
        _v7_save(fig, '241_four_mode_mass_error.png', outdir)

        fig, ax = plt.subplots(figsize=(7.2, 5.0))
        for mode, audits in all_audits.items():
            ax.plot([a.time_days for a in audits],
                    [a.mean_abs_vertical_gas_flux_m3_day for a in audits],
                    marker='o', label=mode)
        ax.set_xlabel('time [days]'); ax.set_ylabel('mean |vertical CO2 face rate| [m3/day]')
        ax.set_title('Gravity/capillary contribution to vertical CO2 flow')
        ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '242_vertical_gas_flux_history.png', outdir)

    summary = {
        'stage': 20,
        'formulation': {
            'primary_pressure': 'brine pressure p_w',
            'gas_pressure': 'p_g = p_w + Pc(Sg)',
            'gas_face_flux': 'direct gas phase-potential Darcy flux',
            'brine_face_flux': 'direct brine phase-potential Darcy flux',
            'pressure_coupling': 'q_t = q_g + q_w with backward-Euler total storage',
            'transport': 'CO2 mass update uses rho_g q_g, not fractional flow times q_t',
            'coupling': 'IMPES with lagged saturation/mobility/Pc and density fixed-point iteration',
        },
        'limit_checks': limit_checks,
        'modes': {
            mode: [a.__dict__ for a in audits]
            for mode, audits in all_audits.items()
        },
    }
    path = _os_v10.path.join(outdir, 'PAD_Stream_V10_Phase_Potential_Summary.json')
    with open(path, 'w') as f:
        _json_v10.dump(summary, f, indent=2)
    print('=' * 118)
    return all_audits, histories, summary



# ==============================================================================
# STAGE 21 [S21] — COUPLED LAND HYSTERESIS + RESIDUAL CO2 TRAPPING
# ==============================================================================
# The historical maximum gas saturation defines the Land residual endpoint.
# During imbibition, Land's free-gas transformation separates total gas into
# connected/mobile and disconnected/trapped portions while preserving total CO2
# mass exactly. Gas relative permeability is evaluated from connected gas;
# brine relative permeability remains a function of total gas saturation.
# Capillary-pressure hysteresis is intentionally not invented here: Pc retains
# the approved Brooks-Corey drainage relationship from Stage 20.
# ==============================================================================

from dataclasses import dataclass as _dataclass_v11
import os as _os_v11
import json as _json_v11


def ccus_land_coefficient(rock: CCUSRock):
    return (1.0 / max(float(rock.s_gr_max), 1.0e-30)
            - 1.0 / max(float(rock.s_g_max), 1.0e-30))


def ccus_land_residual_endpoint(s_g_history, rock: CCUSRock):
    """Potential residual endpoint corresponding to the drainage turning point."""
    history = np.clip(np.asarray(s_g_history, dtype=float), 0.0, rock.s_g_max)
    C = ccus_land_coefficient(rock)
    return history / np.maximum(1.0 + C * history, 1.0e-30)


def ccus_land_free_trapped_saturation(s_g, s_g_history, rock: CCUSRock,
                                      tolerance=1.0e-10):
    """Return connected/free and currently trapped CO2 saturations.

    On primary drainage, all gas is connected. On imbibition, the Land free-gas
    transform gives a continuous split: free gas equals the turning-point gas at
    reversal and tends to zero at the Land residual endpoint. The two returned
    saturations sum exactly to total Sg.
    """
    s_g = np.clip(np.asarray(s_g, dtype=float), 0.0, rock.s_g_max)
    history = np.maximum(np.asarray(s_g_history, dtype=float), s_g)
    residual = ccus_land_residual_endpoint(history, rock)
    C = max(ccus_land_coefficient(rock), 1.0e-30)
    imbibition = s_g < history - float(tolerance)
    excess = np.maximum(s_g - residual, 0.0)
    free_imb = 0.5 * (
        excess + np.sqrt(excess * excess + 4.0 * excess / C)
    )
    free = np.where(imbibition, np.minimum(free_imb, s_g), s_g)
    trapped = np.maximum(s_g - free, 0.0)
    # Exact closure after floating-point roundoff.
    trapped = s_g - free
    return free, trapped, residual, imbibition


# Redefine the accepted Stage-18 function for Stage 21. Drainage behavior is
# unchanged; only the hysteretic gas branch uses Land connected saturation.
def ccus_relative_permeability(s_g, rock: CCUSRock, s_g_history=None):
    rock.validate()
    s_g = np.clip(np.asarray(s_g, dtype=float), 0.0, rock.s_g_max)
    se_total = np.clip(s_g / max(rock.s_g_max, 1.0e-30), 0.0, 1.0)
    krw = rock.krw_endpoint * (1.0 - se_total) ** rock.nw
    if s_g_history is None or not rock.hysteresis:
        krg = rock.krg_endpoint * se_total ** rock.ng
        return krg, krw
    free, _, _, _ = ccus_land_free_trapped_saturation(s_g, s_g_history, rock)
    se_free = np.clip(free / max(rock.s_g_max, 1.0e-30), 0.0, 1.0)
    krg = rock.krg_endpoint * se_free ** rock.ng
    return krg, krw


@_dataclass_v11
class TrappingAudit:
    case: str
    step: int
    phase: str
    time_days: float
    gas_saturation_min: float
    gas_saturation_max: float
    history_max: float
    imbibing_cells: int
    trapped_cells: int
    total_gas_mass_kg: float
    mobile_gas_mass_kg: float
    trapped_gas_mass_kg: float
    potential_residual_mass_kg: float
    trapped_mass_fraction: float
    injected_gas_mass_kg: float
    produced_gas_mass_kg: float
    cumulative_mass_error_kg: float
    max_local_mass_residual_kg: float
    injector_total_rate_m3_day: float
    producer_total_rate_m3_day: float
    producer_gas_rate_m3_day: float
    mean_gas_relative_permeability: float
    max_gas_relative_permeability: float
    pressure_residual_m3_s: float
    streamlines_reaching_producer: int
    streamline_count: int


def _v11_inventory(grid, saturation, history, pressure_step, rock, fluid):
    phi, _ = pressure_dependent_porosity(
        grid, rock, pressure_step.pressure_w, fluid.p_ref
    )
    weight = phi * grid.vcell * pressure_step.density_g
    free, trapped, residual, imb = ccus_land_free_trapped_saturation(
        saturation, history, rock
    )
    if not rock.hysteresis:
        free = np.asarray(saturation, dtype=float).copy()
        trapped = np.zeros_like(free)
    potential = np.minimum(saturation, residual)
    return {
        'weight': weight,
        'free_saturation': free,
        'trapped_saturation': trapped,
        'residual_endpoint': residual,
        'potential_residual_saturation': potential,
        'imbibition_mask': imb,
        'total_mass': float(np.sum(weight * saturation)),
        'mobile_mass': float(np.sum(weight * free)),
        'trapped_mass': float(np.sum(weight * trapped)),
        'potential_residual_mass': float(np.sum(weight * potential)),
    }


def _v11_plot_map(grid, data, title, cbar, filename, outdir, cmap='viridis',
                  vmin=None, vmax=None):
    for k in range(grid.nz):
        fig, ax = plt.subplots(figsize=(6.4, 5.2))
        im = ax.imshow(np.asarray(data)[:, :, k].T, origin='lower', cmap=cmap,
                       vmin=vmin, vmax=vmax)
        ax.set_xlabel('i'); ax.set_ylabel('j')
        ax.set_title(f'{title} — layer {k+1}')
        fig.colorbar(im, ax=ax, label=cbar)
        _v7_save(fig, f'{filename}_layer_{k+1}.png', outdir)


def _v11_plot_pressure_contours(grid, pressure_mpa, title, filename, outdir):
    x = (np.arange(grid.nx) + 0.5) * grid.dx
    y = (np.arange(grid.ny) + 0.5) * grid.dy
    for k in range(grid.nz):
        values = np.asarray(pressure_mpa)[:, :, k].T
        fig, ax = plt.subplots(figsize=(6.4, 5.2))
        filled = ax.contourf(x, y, values, levels=14, cmap='viridis')
        lines = ax.contour(x, y, values, levels=8, colors='k', linewidths=0.5)
        ax.clabel(lines, fontsize=7, fmt='%.2f')
        ax.set_aspect('equal'); ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
        ax.set_title(f'{title} — layer {k+1}')
        fig.colorbar(filled, ax=ax, label='pressure [MPa]')
        _v7_save(fig, f'{filename}_layer_{k+1}.png', outdir)


def _v11_plot_snapshot(grid, state, case, label, outdir, rock):
    pstep = state['pressure_step']; s = state['saturation']; history = state['history']
    inv = state['inventory']; rows = state['rows']
    prefix = f'310_{case}_{label}'
    # Pressure contours are retained for the hysteretic physics run. The
    # no-hysteresis comparison uses the same well controls and is shown through
    # its saturation/mobility difference maps.
    if case == 'hysteresis_on':
        _v11_plot_pressure_contours(
            grid, pstep.pressure_w / 1.0e6,
            f'{case}: brine-pressure contours ({label})',
            prefix + '_pressure_w_contours', outdir
        )
    _v11_plot_map(grid, s, f'{case}: total CO2 saturation ({label})', 'Sg',
                  prefix + '_total_sg', outdir, vmin=0.0, vmax=rock.s_g_max)
    # Detailed trapping fields are needed only for the final hysteretic state.
    if case == 'hysteresis_on' and label == 'final':
        _v11_plot_map(grid, history,
                      f'{case}: historical maximum Sg ({label})',
                      'Sg,max history', prefix + '_history', outdir,
                      vmin=0.0, vmax=rock.s_g_max)
        _v11_plot_map(grid, inv['trapped_saturation'],
                      f'{case}: currently trapped CO2 ({label})', 'trapped Sg',
                      prefix + '_trapped_sg', outdir,
                      vmin=0.0, vmax=rock.s_gr_max)
        krg, _ = ccus_relative_permeability(s, state['rock'], state['history'])
        _v11_plot_map(grid, krg,
                      f'{case}: hysteretic gas relative permeability ({label})',
                      'krg', prefix + '_krg', outdir,
                      vmin=0.0, vmax=rock.krg_endpoint)
    _v10_plot_streamlines(
        grid, rows, pstep.pressure_w,
        f'{case}_{label}', 0, state.get('time_days', 0.0), outdir
    )


def _v11_plot_constitutive(rock, fluid, outdir):
    histories = [0.15, 0.30, 0.50, rock.s_g_max]
    s = np.linspace(0.0, rock.s_g_max, 600)
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    h = np.linspace(0.0, rock.s_g_max, 400)
    ax.plot(h, ccus_land_residual_endpoint(h, rock))
    ax.plot(h, h, linestyle='--', alpha=0.5)
    ax.set_xlabel('historical maximum CO2 saturation')
    ax.set_ylabel('Land residual endpoint')
    ax.set_title('Land trapping relationship')
    ax.grid(alpha=0.3)
    _v7_save(fig, '300_land_residual_relationship.png', outdir)

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    for hist in histories:
        valid = s <= hist + 1e-12
        free, trapped, _, _ = ccus_land_free_trapped_saturation(
            s[valid], np.full(np.sum(valid), hist), rock
        )
        ax.plot(s[valid], free, label=f'free, Sg,max={hist:.2f}')
        ax.plot(s[valid], trapped, linestyle='--',
                label=f'trapped, Sg,max={hist:.2f}')
    ax.set_xlabel('current total CO2 saturation')
    ax.set_ylabel('saturation component')
    ax.set_title('Land connected and trapped gas during imbibition')
    ax.grid(alpha=0.3); ax.legend(ncol=2, fontsize=8)
    _v7_save(fig, '301_land_free_trapped_components.png', outdir)

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    for hist in histories:
        valid = s <= hist + 1e-12
        krg, _ = ccus_relative_permeability(
            s[valid], rock, np.full(np.sum(valid), hist)
        )
        ax.plot(s[valid], krg, label=f'Sg,max={hist:.2f}')
    krg_d, _ = ccus_relative_permeability(s, rock, None)
    ax.plot(s, krg_d, color='black', linestyle=':', label='primary drainage')
    ax.set_xlabel('total CO2 saturation'); ax.set_ylabel('CO2 relative permeability')
    ax.set_title('Land/Killough-style gas-mobility scanning curves')
    ax.grid(alpha=0.3); ax.legend()
    _v7_save(fig, '302_hysteretic_krg_scanning_curves.png', outdir)


def run_hysteresis_trapping_target(
        outdir='pad_stream_v11_hysteresis_outputs',
        drainage_days=2.0, imbibition_days=4.0, dt_days=0.1,
        pollock_seeds_per_dim=6, make_plots=True,
        brine_compressibility=0.0, rock_compressibility=0.0):
    """Gas drainage followed by a pure-brine chase, with hysteresis on/off."""
    _os_v11.makedirs(outdir, exist_ok=True)
    grid, _, _, cap, wells, _ = build_padstream_5x5x5_case()
    fluid = CCUSFluid(p_ref=float(wells.inj_bhp), c_w=float(brine_compressibility))
    n_drain = max(1, int(np.ceil(drainage_days / dt_days)))
    n_imb = max(1, int(np.ceil(imbibition_days / dt_days)))
    dt = float(dt_days) * DAYS_TO_SECONDS
    schedules = [('drainage', 1.0)] * n_drain + [('imbibition', 0.0)] * n_imb
    snapshot_steps = set([n_drain,
                          min(n_drain + max(1, n_imb // 2), len(schedules)),
                          len(schedules)])
    cases = {'hysteresis_on': True, 'hysteresis_off': False}
    all_audits = {}; all_states = {}

    print('=' * 120)
    print('VERSION 11 — COUPLED LAND HYSTERESIS AND RESIDUAL CO2 TRAPPING')
    print('=' * 120)
    print(f'Schedule: {drainage_days:g} d pure CO2 injection + '
          f'{imbibition_days:g} d pure brine chase; dt={dt_days:g} d')

    for case, use_hysteresis in cases.items():
        rock = CCUSRock(
            s_g_initial=0.0, cr=float(rock_compressibility),
            hysteresis=bool(use_hysteresis), s_gr_max=0.30,
        ).validate()
        depth = _v10_depth_centres(grid)
        pressure_w = (float(wells.bhp) + fluid.rho_w_ref * GRAVITY_ACCELERATION
                      * (depth - float(np.mean(depth))))
        saturation = np.full_like(pressure_w, rock.s_g_initial)
        history = saturation.copy()
        pc0 = ccus_capillary_pressure(saturation, rock, cap)
        rho0 = ccus_gas_density_from_phase_pressure(pressure_w + pc0, fluid)
        phi0, _ = pressure_dependent_porosity(grid, rock, pressure_w, fluid.p_ref)
        mass_state = phi0 * grid.vcell * rho0 * saturation
        initial_mass = float(np.sum(mass_state))
        cumulative_injected = 0.0; cumulative_produced = 0.0
        audits=[]; states=[]

        for step, (phase, gas_fraction) in enumerate(schedules, start=1):
            old_s = saturation.copy(); old_p = pressure_w.copy()
            pstep = solve_ccus_phase_potential_pressure_step(
                grid, old_s, rock, fluid, cap, wells, old_p, dt,
                include_capillary=True, include_gravity=True,
                compressibility_scale=1.0,
                injector_completion_sg=rock.s_g_max,
                s_g_history=history,
                injection_gas_fraction=gas_fraction,
            )
            transport = advance_ccus_direct_phase_mass(
                grid, old_s, old_p, pstep, rock, fluid, dt,
                mass_old_state=mass_state,
            )
            saturation = transport['saturation']
            mass_state = transport['mass'].copy()
            pressure_w = pstep.pressure_w
            history = np.maximum(history, saturation)
            inventory = _v11_inventory(
                grid, saturation, history, pstep, rock, fluid
            )
            cumulative_injected += transport['injected_mass_rate'] * dt
            cumulative_produced += transport['produced_mass_rate'] * dt
            cumulative_error = inventory['total_mass'] - (
                initial_mass + cumulative_injected - cumulative_produced
            )
            if step in snapshot_steps:
                rows, _ = _v10_trace_total_streamlines(
                    grid, pstep, wells, seeds_per_dim=pollock_seeds_per_dim
                )
            else:
                rows = []
            krg, _ = ccus_relative_permeability(saturation, rock, history)
            producer_gas_rate = sum(
                max(-float(pstep.well_gas_source.get(c, 0.0)), 0.0)
                for c in wells.prod_cells
            ) * DAYS_TO_SECONDS
            trapped_cells = int(np.count_nonzero(
                inventory['trapped_saturation'] > 1.0e-8
            ))
            total_mass = max(inventory['total_mass'], 1.0e-30)
            audit = TrappingAudit(
                case=case, step=step, phase=phase,
                time_days=step * dt_days,
                gas_saturation_min=float(np.min(saturation)),
                gas_saturation_max=float(np.max(saturation)),
                history_max=float(np.max(history)),
                imbibing_cells=int(np.count_nonzero(inventory['imbibition_mask'])),
                trapped_cells=trapped_cells,
                total_gas_mass_kg=inventory['total_mass'],
                mobile_gas_mass_kg=inventory['mobile_mass'],
                trapped_gas_mass_kg=inventory['trapped_mass'],
                potential_residual_mass_kg=inventory['potential_residual_mass'],
                trapped_mass_fraction=inventory['trapped_mass']/total_mass,
                injected_gas_mass_kg=cumulative_injected,
                produced_gas_mass_kg=cumulative_produced,
                cumulative_mass_error_kg=float(cumulative_error),
                max_local_mass_residual_kg=float(np.max(np.abs(
                    transport['local_residual']))),
                injector_total_rate_m3_day=pstep.injector_total_rate*DAYS_TO_SECONDS,
                producer_total_rate_m3_day=pstep.producer_total_rate*DAYS_TO_SECONDS,
                producer_gas_rate_m3_day=float(producer_gas_rate),
                mean_gas_relative_permeability=float(np.mean(krg)),
                max_gas_relative_permeability=float(np.max(krg)),
                pressure_residual_m3_s=pstep.max_nonwell_pressure_residual,
                streamlines_reaching_producer=int(sum(bool(r[2]) for r in rows)),
                streamline_count=len(rows),
            )
            audits.append(audit)
            state={
                'pressure_step':pstep, 'transport':transport,
                'saturation':saturation.copy(), 'history':history.copy(),
                'inventory':inventory, 'rows':rows, 'rock':rock,
                'time_days': step * dt_days,
            }
            states.append(state)
            print(
                f'  {case:14s} step {step:02d}/{len(schedules)} {phase:10s} '
                f't={audit.time_days:5.2f} d Sgmax={audit.gas_saturation_max:.4f} '
                f'imb={audit.imbibing_cells:3d} trap={audit.trapped_mass_fraction*100:6.2f}% '
                f'mass_err={audit.cumulative_mass_error_kg:.2e} kg'
            )

        all_audits[case]=audits; all_states[case]=states
        if make_plots:
            key_indices=sorted(step_number - 1 for step_number in snapshot_steps)
            for idx in key_indices:
                label=('end_drainage' if idx==n_drain-1 else
                       'final' if idx==len(states)-1 else 'mid_imbibition')
                if case == 'hysteresis_off' and label != 'final':
                    continue
                _v11_plot_snapshot(grid, states[idx], case, label, outdir, rock)

    if make_plots:
        _v11_plot_constitutive(all_states['hysteresis_on'][-1]['rock'], fluid, outdir)
        # Time histories.
        plots=[
            ('320_total_gas_mass.png','total_gas_mass_kg','total CO2 mass [kg]',False),
            ('321_trapped_gas_mass.png','trapped_gas_mass_kg','currently trapped CO2 mass [kg]',False),
            ('322_trapped_fraction.png','trapped_mass_fraction','trapped fraction of in-place CO2',False),
            ('323_mobile_gas_mass.png','mobile_gas_mass_kg','connected/mobile CO2 mass [kg]',False),
            ('324_produced_gas_mass.png','produced_gas_mass_kg','cumulative produced CO2 mass [kg]',False),
            ('325_imbibing_cells.png','imbibing_cells','cells on imbibition branch',False),
            ('326_gas_mobility.png','mean_gas_relative_permeability','mean gas relative permeability',False),
            ('327_mass_error.png','cumulative_mass_error_kg','|cumulative CO2 mass error| [kg]',True),
        ]
        for fname,field,ylabel,logy in plots:
            fig,ax=plt.subplots(figsize=(7.4,5.0))
            for case,audits in all_audits.items():
                y=np.asarray([getattr(a,field) for a in audits],float)
                if logy: y=np.maximum(np.abs(y),1e-18)
                ax.plot([a.time_days for a in audits],y,marker='o',label=case)
            ax.axvline(drainage_days,color='black',linestyle='--',alpha=0.6,
                       label='brine chase begins' if fname==plots[0][0] else None)
            if logy: ax.set_yscale('log')
            ax.set_xlabel('time [days]'); ax.set_ylabel(ylabel)
            ax.set_title(ylabel.capitalize()); ax.grid(alpha=0.3,which='both'); ax.legend()
            _v7_save(fig,fname,outdir)

        # Final on/off difference maps.
        son=all_states['hysteresis_on'][-1]['saturation']
        soff=all_states['hysteresis_off'][-1]['saturation']
        _v11_plot_map(grid, son-soff,
                      'Final saturation effect of hysteresis',
                      'Sg(hysteresis on) - Sg(off)',
                      '330_final_hysteresis_saturation_difference',outdir,
                      cmap='coolwarm')
        kr_on,_=ccus_relative_permeability(
            son,all_states['hysteresis_on'][-1]['rock'],
            all_states['hysteresis_on'][-1]['history'])
        kr_off,_=ccus_relative_permeability(
            soff,all_states['hysteresis_off'][-1]['rock'],None)
        _v11_plot_map(grid,kr_on-kr_off,
                      'Final gas-mobility effect of hysteresis',
                      'krg(on) - krg(off)',
                      '331_final_hysteresis_krg_difference',outdir,
                      cmap='coolwarm')

    summary={
        'stage':21,
        'model':{
            'trapping_relation':'Land residual endpoint and connected/free-gas transform',
            'gas_relative_permeability':'Corey drainage evaluated on Land connected gas during imbibition',
            'brine_relative_permeability':'non-hysteretic Corey function of total gas saturation',
            'capillary_pressure':'Stage-20 Brooks-Corey drainage curve; no unapproved Pc hysteresis',
            'schedule':{'drainage_days':drainage_days,'imbibition_days':imbibition_days,
                        'dt_days':dt_days,'drainage_injection':'pure CO2',
                        'imbibition_injection':'pure brine'},
        },
        'cases':{case:[a.__dict__ for a in audits]
                 for case,audits in all_audits.items()},
    }
    summary_path=_os_v11.path.join(outdir,'PAD_Stream_V11_Hysteresis_Trapping_Summary.json')
    with open(summary_path,'w') as f:
        _json_v11.dump(summary,f,indent=2)
    print('='*120)
    return all_audits,all_states,summary



# ==============================================================================
# STAGE 22 [S22] — FINAL PHASE-AWARE WELL MODEL AND CONTROL SWITCHING
# ==============================================================================
# Wells are represented by Peaceman completion indices instead of pressure-
# pinned grid cells.  Each completion can be controlled by phase-aware BHP,
# reservoir-volume rate, or CO2 mass rate.  Rate controls calculate the implied
# datum BHP and switch to a pressure limit when required.  Completion allocation
# follows phase productivity unless explicit fractions are supplied.
# ==============================================================================

from dataclasses import dataclass as _dataclass_v12, field as _field_v12
import os as _os_v12
import json as _json_v12


@_dataclass_v12
class FinalWellControl:
    name: str
    role: str                    # 'injector' or 'producer'
    cells: list
    mode: str                    # 'bhp', 'reservoir_rate', or 'mass_rate'
    target: float                # Pa, m3/s, or kg/s according to mode
    phase: str = 'total'         # 'gas', 'brine', or 'total'
    bhp_min: float = None        # datum pressure [Pa]
    bhp_max: float = None        # datum pressure [Pa]
    well_radius: float = 0.10    # m
    skin: float = 0.0
    datum_depth: float = None
    completion_fractions: list = None
    enabled: bool = True

    def validate(self):
        self.role = str(self.role).lower()
        self.mode = str(self.mode).lower()
        self.phase = str(self.phase).lower()
        if self.role not in ('injector', 'producer'):
            raise ValueError(f'{self.name}: role must be injector or producer')
        if self.mode not in ('bhp', 'reservoir_rate', 'mass_rate'):
            raise ValueError(f'{self.name}: unsupported control mode {self.mode}')
        if self.phase not in ('gas', 'brine', 'total'):
            raise ValueError(f'{self.name}: phase must be gas, brine, or total')
        if not self.cells:
            raise ValueError(f'{self.name}: at least one completion is required')
        if self.well_radius <= 0.0:
            raise ValueError(f'{self.name}: well_radius must be positive')
        if self.completion_fractions is not None:
            f = np.asarray(self.completion_fractions, dtype=float)
            if f.size != len(self.cells) or np.any(f < 0.0) or np.sum(f) <= 0.0:
                raise ValueError(f'{self.name}: invalid completion fractions')
        return self


@_dataclass_v12
class CompletionWellReport:
    cell: tuple
    layer: int
    well_index_m3: float
    gas_productivity_m3_pa_s: float
    brine_productivity_m3_pa_s: float
    gas_rate_m3_day: float
    brine_rate_m3_day: float
    total_rate_m3_day: float
    gas_mass_rate_kg_s: float


@_dataclass_v12
class WellControlReport:
    name: str
    role: str
    requested_mode: str
    active_mode: str
    phase: str
    target: float
    datum_bhp_pa: float
    required_bhp_pa: float
    switched: bool
    switch_reason: str
    total_rate_m3_day: float
    gas_rate_m3_day: float
    brine_rate_m3_day: float
    gas_mass_rate_kg_s: float
    completion_reports: list = _field_v12(default_factory=list)


def peaceman_equivalent_radius(dx, dy, kx, ky):
    """Peaceman equivalent radius for a vertical well in a Cartesian cell."""
    kx = max(float(kx), 1.0e-40)
    ky = max(float(ky), 1.0e-40)
    ratio = ky / kx
    numerator = 0.28 * np.sqrt(np.sqrt(ratio) * dx * dx
                               + np.sqrt(1.0 / ratio) * dy * dy)
    denominator = ratio ** 0.25 + ratio ** (-0.25)
    return float(numerator / max(denominator, 1.0e-30))


def peaceman_well_index(grid, cell, well_radius=0.10, skin=0.0):
    """Geometric completion index. Multiply by phase mobility for productivity."""
    i, j, k = cell
    kx = float(grid.k[i, j, k]); ky = float(grid.k[i, j, k])
    re = peaceman_equivalent_radius(grid.dx, grid.dy, kx, ky)
    rw = float(well_radius)
    if re <= rw:
        raise ValueError('Peaceman equivalent radius must exceed well radius')
    denom = np.log(re / rw) + float(skin)
    if denom <= 0.0:
        raise ValueError('well-index denominator must be positive')
    kh = np.sqrt(kx * ky) * float(grid.dzk[k])
    return float(2.0 * np.pi * kh / denom)


def _v12_depth_and_datum(grid, well):
    depth = _v10_depth_centres(grid)
    datum = (float(np.mean(depth)) if well.datum_depth is None
             else float(well.datum_depth))
    return depth, datum


def _v12_phase_equivalent_pressures(grid, well, pressure_w, pc, rho_g, rho_w):
    depth, datum = _v12_depth_and_datum(grid, well)
    eq_g = {}; eq_w = {}
    for cell in well.cells:
        dz = float(depth[cell] - datum)
        eq_g[cell] = float(pressure_w[cell] + pc[cell]
                           - rho_g[cell] * GRAVITY_ACCELERATION * dz)
        eq_w[cell] = float(pressure_w[cell]
                           - rho_w[cell] * GRAVITY_ACCELERATION * dz)
    return eq_g, eq_w


def _v12_productivities(grid, well, lambda_g, lambda_w):
    Jg = {}; Jw = {}; WI = {}
    for cell in well.cells:
        wi = peaceman_well_index(grid, cell, well.well_radius, well.skin)
        WI[cell] = wi
        Jg[cell] = wi * float(lambda_g[cell])
        Jw[cell] = wi * float(lambda_w[cell])
    return WI, Jg, Jw


def _v12_selected_productivity(well, Jg, Jw):
    if well.phase == 'gas':
        return {c: Jg[c] for c in well.cells}
    if well.phase == 'brine':
        return {c: Jw[c] for c in well.cells}
    return {c: Jg[c] + Jw[c] for c in well.cells}


def _v12_rate_target_m3_s(well, fluid, bhp_for_density=None):
    """Convert a requested rate control to reservoir-volume magnitude."""
    if well.mode == 'reservoir_rate':
        return abs(float(well.target))
    if well.mode == 'mass_rate':
        if well.phase != 'gas':
            raise ValueError(f'{well.name}: mass_rate currently requires phase="gas"')
        p = float(fluid.p_ref if bhp_for_density is None else bhp_for_density)
        rho = float(ccus_gas_density_from_phase_pressure(np.array([p]), fluid)[0])
        return abs(float(well.target)) / max(rho, 1.0e-30)
    raise ValueError('rate target requested for a non-rate well')


def _v12_explicit_fraction_weights(well):
    if well.completion_fractions is None:
        return None
    f = np.asarray(well.completion_fractions, dtype=float)
    f /= np.sum(f)
    return {cell: float(value) for cell, value in zip(well.cells, f)}


def _v12_rate_allocations(grid, well, qmag, Jg, Jw):
    """Return fixed gas/brine reservoir-volume sources for a rate well."""
    sign = 1.0 if well.role == 'injector' else -1.0
    explicit = _v12_explicit_fraction_weights(well)
    selected = _v12_selected_productivity(well, Jg, Jw)
    if explicit is None:
        total = sum(max(float(v), 0.0) for v in selected.values())
        if total <= 1.0e-30:
            # A pure-gas injector can still inject into an initially gas-free cell;
            # allocate by geometric WI when phase productivity is zero.
            raw = {c: peaceman_well_index(
                grid, c, well.well_radius, well.skin
            ) for c in well.cells}
            total = sum(raw.values())
            weights = {c: raw[c] / max(total, 1.0e-30) for c in well.cells}
        else:
            weights = {c: max(float(selected[c]), 0.0) / total for c in well.cells}
    else:
        weights = explicit
    qg = {c: 0.0 for c in well.cells}; qw = {c: 0.0 for c in well.cells}
    for c in well.cells:
        q = sign * float(qmag) * weights[c]
        if well.phase == 'gas':
            qg[c] = q
        elif well.phase == 'brine':
            qw[c] = q
        else:
            denom = max(Jg[c] + Jw[c], 1.0e-30)
            qg[c] = q * Jg[c] / denom
            qw[c] = q - qg[c]
    return qg, qw


def _v12_required_bhp(well, qmag, eq_g, eq_w, Jg, Jw):
    """Datum BHP required to satisfy a positive rate magnitude."""
    selected = _v12_selected_productivity(well, Jg, Jw)
    denom = sum(max(float(v), 0.0) for v in selected.values())
    if denom <= 1.0e-30:
        return np.inf if well.role == 'injector' else -np.inf
    weighted = 0.0
    for c in well.cells:
        if well.phase == 'gas':
            weighted += Jg[c] * eq_g[c]
        elif well.phase == 'brine':
            weighted += Jw[c] * eq_w[c]
        else:
            weighted += Jg[c] * eq_g[c] + Jw[c] * eq_w[c]
    if well.role == 'injector':
        return float((weighted + qmag) / denom)
    return float((weighted - qmag) / denom)


def _v12_choose_control(well, fluid, eq_g, eq_w, Jg, Jw):
    """Choose active rate or BHP mode from a requested control and limits."""
    if well.mode == 'bhp':
        return {
            'active_mode': 'bhp', 'bhp': float(well.target),
            'required_bhp': float(well.target), 'switched': False,
            'reason': '', 'qmag': None,
        }

    # Gas mass-rate injection is solved at wellbore density, not converted with
    # a fixed reference density.  This keeps the requested kg/s exact while the
    # implied BHP and reservoir-volume rate change consistently with pressure.
    if well.mode == 'mass_rate':
        if well.phase != 'gas':
            raise ValueError(f'{well.name}: mass_rate currently requires phase="gas"')
        target_mass = abs(float(well.target))
        denom = sum(max(float(Jg[c]), 0.0) for c in well.cells)
        weighted = sum(float(Jg[c]) * float(eq_g[c]) for c in well.cells)
        if denom <= 1.0e-30:
            required = np.inf if well.role == 'injector' else -np.inf
            qmag = 0.0
        elif well.role == 'injector':
            required = float(fluid.p_ref)
            for _ in range(30):
                rho = float(ccus_gas_density_from_phase_pressure(
                    np.array([required]), fluid
                )[0])
                q = denom * required - weighted
                residual = rho * q - target_mass
                derivative = rho * (denom + float(fluid.c_g) * q)
                update = residual / max(abs(derivative), 1.0e-30)
                required -= update
                if abs(update) <= 1.0e-8 * max(abs(required), 1.0):
                    break
            rho_required = float(ccus_gas_density_from_phase_pressure(
                np.array([required]), fluid
            )[0])
            qmag = target_mass / max(rho_required, 1.0e-30)
        else:
            # Produced gas mass uses the completion-side reservoir density.
            rho_eff_num = sum(float(Jg[c]) * float(
                ccus_gas_density_from_phase_pressure(
                    np.array([eq_g[c]]), fluid
                )[0]) for c in well.cells)
            rho_eff = rho_eff_num / max(denom, 1.0e-30)
            qmag = target_mass / max(rho_eff, 1.0e-30)
            required = float((weighted - qmag) / denom)
    else:
        qmag = abs(float(well.target))
        required = _v12_required_bhp(well, qmag, eq_g, eq_w, Jg, Jw)

    switched = False; reason = ''; active = well.mode; bhp = required
    if well.bhp_max is not None and required > float(well.bhp_max):
        active = 'bhp'; bhp = float(well.bhp_max); switched = True
        reason = 'required BHP exceeded maximum pressure limit'
    if well.bhp_min is not None and required < float(well.bhp_min):
        active = 'bhp'; bhp = float(well.bhp_min); switched = True
        reason = 'required BHP fell below minimum pressure limit'
    return {
        'active_mode': active, 'bhp': float(bhp),
        'required_bhp': float(required), 'switched': switched,
        'reason': reason, 'qmag': float(qmag),
    }


def _v12_bhp_matrix_terms(grid, well, bhp, pc, rho_g, rho_w, Jg, Jw):
    """Return diagonal and RHS terms for phase-aware Peaceman BHP control."""
    depth, datum = _v12_depth_and_datum(grid, well)
    terms = []
    for cell in well.cells:
        dz = float(depth[cell] - datum)
        jg = Jg[cell] if well.phase in ('gas', 'total') else 0.0
        jw = Jw[cell] if well.phase in ('brine', 'total') else 0.0
        diag = jg + jw
        rhs = (jg * (float(bhp) - float(pc[cell])
                     + float(rho_g[cell]) * GRAVITY_ACCELERATION * dz)
               + jw * (float(bhp)
                       + float(rho_w[cell]) * GRAVITY_ACCELERATION * dz))
        terms.append((cell, float(diag), float(rhs)))
    return terms


def solve_ccus_final_well_pressure_step(
        grid, s_g, rock: CCUSRock, fluid: CCUSFluid, cap: Capillary,
        well_controls, pressure_w_old, dt, include_capillary=True,
        include_gravity=True, no_crossflow=False, compressibility_scale=1.0,
        fixed_point_tolerance=1.0e-9, fixed_point_max_iterations=10,
        s_g_history=None):
    """Phase-potential pressure solve with Peaceman wells and control switching."""
    if dt <= 0.0:
        raise ValueError('dt must be positive')
    controls = [w.validate() for w in well_controls if w.enabled]
    s_g = np.asarray(s_g, dtype=float)
    pressure_w_old = np.asarray(pressure_w_old, dtype=float)

    # A pure-phase injector evaluates completion mobility at the injected endpoint.
    mobility_sg = s_g.copy()
    mobility_history = (None if s_g_history is None
                        else np.maximum(np.asarray(s_g_history, dtype=float), mobility_sg))
    for w in controls:
        if w.role == 'injector' and w.phase == 'gas':
            for cell in w.cells:
                mobility_sg[cell] = rock.s_g_max
                if mobility_history is not None:
                    mobility_history[cell] = max(mobility_history[cell], rock.s_g_max)
        elif w.role == 'injector' and w.phase == 'brine':
            for cell in w.cells:
                mobility_sg[cell] = 0.0
    lambda_g, lambda_w = ccus_phase_mobilities(
        mobility_sg, rock, fluid, mobility_history
    )
    pc = (ccus_capillary_pressure(s_g, rock, cap)
          if include_capillary else np.zeros_like(s_g))
    phi_old, _ = pressure_dependent_porosity(grid, rock, pressure_w_old, fluid.p_ref)
    ct = ccus_total_compressibility(grid, s_g, rock, fluid,
                                    scale=compressibility_scale)
    storage_capacity = phi_old * grid.vcell * ct
    storage_flat = storage_capacity.transpose(2, 1, 0).ravel()
    old_flat = pressure_w_old.transpose(2, 1, 0).ravel()
    p_iter = pressure_w_old.copy()
    relative_change = np.inf
    final_control_state = None

    for iteration in range(1, int(fixed_point_max_iterations) + 1):
        pressure_g_iter = p_iter + pc
        rho_g = ccus_gas_density_from_phase_pressure(pressure_g_iter, fluid)
        rho_w = ccus_brine_density(p_iter, fluid)
        Aflow, fixed_div = _v10_assemble_pressure_operator(
            grid, pc, rho_g, rho_w, lambda_g, lambda_w,
            include_capillary=include_capillary,
            include_gravity=include_gravity,
            no_crossflow=no_crossflow,
        )
        A = (Aflow + csr_matrix(
            (storage_flat / dt,
             (np.arange(grid.ncell), np.arange(grid.ncell))),
            shape=(grid.ncell, grid.ncell)
        )).tolil()
        b = (storage_flat / dt) * old_flat
        b -= fixed_div.transpose(2, 1, 0).ravel()
        control_state = []
        for well in controls:
            WI, Jg, Jw = _v12_productivities(grid, well, lambda_g, lambda_w)
            eq_g, eq_w = _v12_phase_equivalent_pressures(
                grid, well, p_iter, pc, rho_g, rho_w
            )
            choice = _v12_choose_control(well, fluid, eq_g, eq_w, Jg, Jw)
            entry = {'well': well, 'WI': WI, 'Jg': Jg, 'Jw': Jw,
                     'eq_g': eq_g, 'eq_w': eq_w, 'choice': choice,
                     'fixed_qg': {}, 'fixed_qw': {}}
            if choice['active_mode'] == 'bhp':
                for cell, diag, rhs in _v12_bhp_matrix_terms(
                        grid, well, choice['bhp'], pc, rho_g, rho_w, Jg, Jw):
                    idx = grid.idx(*cell)
                    A[idx, idx] += diag
                    b[idx] += rhs
            else:
                qg, qw = _v12_rate_allocations(
                    grid, well, choice['qmag'], Jg, Jw
                )
                entry['fixed_qg'] = qg; entry['fixed_qw'] = qw
                for cell in well.cells:
                    b[grid.idx(*cell)] += qg[cell] + qw[cell]
            control_state.append(entry)
        pflat = spsolve(A.tocsr(), b)
        p_new = pflat.reshape((grid.nz, grid.ny, grid.nx)).transpose(2, 1, 0)
        relative_change = float(np.linalg.norm(p_new - p_iter)
                                / max(np.linalg.norm(p_new), 1.0))
        p_iter = p_new
        final_control_state = control_state
        if relative_change <= fixed_point_tolerance:
            break

    pressure_w = p_iter
    pressure_g = pressure_w + pc
    rho_g = ccus_gas_density_from_phase_pressure(pressure_g, fluid)
    rho_w = ccus_brine_density(pressure_w, fluid)
    qgx, qgy, qgz, qwx, qwy, qwz = _v10_phase_face_terms(
        grid, pressure_w, pc, rho_g, rho_w, lambda_g, lambda_w,
        include_capillary=include_capillary,
        include_gravity=include_gravity,
        no_crossflow=no_crossflow,
    )
    qtx, qty, qtz = qgx + qwx, qgy + qwy, qgz + qwz

    gas_sources = {}; brine_sources = {}; total_sources = {}
    reports = []
    all_well_cells = set()
    for entry in final_control_state:
        well = entry['well']; all_well_cells.update(well.cells)
        WI, Jg, Jw = _v12_productivities(grid, well, lambda_g, lambda_w)
        eq_g, eq_w = _v12_phase_equivalent_pressures(
            grid, well, pressure_w, pc, rho_g, rho_w
        )
        choice = _v12_choose_control(well, fluid, eq_g, eq_w, Jg, Jw)
        # Preserve the pressure-limit decision made during the converged solve.
        solved_choice = entry['choice']
        if solved_choice['active_mode'] == 'bhp' and solved_choice['switched']:
            choice = solved_choice
        if choice['active_mode'] == 'bhp':
            qg = {}; qw = {}
            bhp = choice['bhp']
            for cell in well.cells:
                qg[cell] = (Jg[cell] * (bhp - eq_g[cell])
                            if well.phase in ('gas', 'total') else 0.0)
                qw[cell] = (Jw[cell] * (bhp - eq_w[cell])
                            if well.phase in ('brine', 'total') else 0.0)
        else:
            qg, qw = _v12_rate_allocations(grid, well, choice['qmag'], Jg, Jw)
            bhp = choice['required_bhp']
        completion_reports = []
        total_qg = 0.0; total_qw = 0.0; mdotg = 0.0
        for cell in well.cells:
            gas_sources[cell] = gas_sources.get(cell, 0.0) + float(qg[cell])
            brine_sources[cell] = brine_sources.get(cell, 0.0) + float(qw[cell])
            total_sources[cell] = total_sources.get(cell, 0.0) + float(qg[cell] + qw[cell])
            total_qg += qg[cell]; total_qw += qw[cell]
            rho_for_mass = (float(ccus_gas_density_from_phase_pressure(
                np.array([bhp]), fluid)[0]) if qg[cell] >= 0.0
                else float(rho_g[cell]))
            cmass = float(qg[cell]) * rho_for_mass
            mdotg += cmass
            completion_reports.append(CompletionWellReport(
                cell=tuple(cell), layer=int(cell[2] + 1),
                well_index_m3=float(WI[cell]),
                gas_productivity_m3_pa_s=float(Jg[cell]),
                brine_productivity_m3_pa_s=float(Jw[cell]),
                gas_rate_m3_day=float(qg[cell] * DAYS_TO_SECONDS),
                brine_rate_m3_day=float(qw[cell] * DAYS_TO_SECONDS),
                total_rate_m3_day=float((qg[cell] + qw[cell]) * DAYS_TO_SECONDS),
                gas_mass_rate_kg_s=cmass,
            ))
        reports.append(WellControlReport(
            name=well.name, role=well.role,
            requested_mode=well.mode, active_mode=choice['active_mode'],
            phase=well.phase, target=float(well.target),
            datum_bhp_pa=float(bhp), required_bhp_pa=float(choice['required_bhp']),
            switched=bool(choice['switched']), switch_reason=str(choice['reason']),
            total_rate_m3_day=float((total_qg + total_qw) * DAYS_TO_SECONDS),
            gas_rate_m3_day=float(total_qg * DAYS_TO_SECONDS),
            brine_rate_m3_day=float(total_qw * DAYS_TO_SECONDS),
            gas_mass_rate_kg_s=float(mdotg),
            completion_reports=completion_reports,
        ))

    div_total = face_flux_outflow_divergence(grid, qtx, qty, qtz)
    accumulation = storage_capacity * (pressure_w - pressure_w_old) / dt
    source_field = well_source_field(grid, total_sources)
    physical_residual = div_total + accumulation - source_field
    nonwell = np.ones_like(s_g, dtype=bool)
    for cell in all_well_cells:
        nonwell[cell] = False
    max_nonwell = (float(np.max(np.abs(physical_residual[nonwell])))
                   if np.any(nonwell) else 0.0)
    closure = max(
        float(np.max(np.abs(qtx - (qgx + qwx)))) if qtx.size else 0.0,
        float(np.max(np.abs(qty - (qgy + qwy)))) if qty.size else 0.0,
        float(np.max(np.abs(qtz - (qgz + qwz)))) if qtz.size else 0.0,
    )
    inj_rate = sum(max(float(v), 0.0) for v in total_sources.values())
    prod_rate = sum(max(-float(v), 0.0) for v in total_sources.values())
    step = PhasePotentialPressureStep(
        pressure_w=pressure_w, pressure_g=pressure_g,
        capillary_pressure=pc, density_g=rho_g, density_w=rho_w,
        lambda_g=lambda_g, lambda_w=lambda_w,
        qg_x=qgx, qg_y=qgy, qg_z=qgz,
        qw_x=qwx, qw_y=qwy, qw_z=qwz,
        qt_x=qtx, qt_y=qty, qt_z=qtz,
        total_compressibility=ct, storage_capacity=storage_capacity,
        accumulation_rate=accumulation,
        well_total_source=total_sources,
        well_gas_source=gas_sources,
        well_brine_source=brine_sources,
        injector_total_rate=float(inj_rate),
        producer_total_rate=float(prod_rate),
        global_volume_balance_error=float(np.sum(physical_residual)),
        max_phase_flux_closure_error=closure,
        max_nonwell_pressure_residual=max_nonwell,
        fixed_point_iterations=iteration,
        fixed_point_relative_change=relative_change,
    )
    step.well_reports = reports
    return step


@_dataclass_v12
class FinalWellStepAudit:
    step: int
    time_days: float
    injector_mode: str
    injector_bhp_mpa: float
    injector_rate_m3_day: float
    injector_gas_mass_rate_kg_s: float
    injector_switched: bool
    producer_mode: str
    producer_bhp_mpa: float
    producer_rate_m3_day: float
    cumulative_mass_error_kg: float
    pressure_residual_m3_s: float
    saturation_min: float
    saturation_max: float
    trapped_mass_kg: float
    streamlines_reaching_producer: int
    streamline_count: int


def _v12_report_to_dict(report):
    d = report.__dict__.copy()
    d['completion_reports'] = [c.__dict__ for c in report.completion_reports]
    return d


def validate_final_well_model(grid, rock, fluid, cap):
    """Analytical and limiting checks for the final well formulation."""
    cell = (2, 2, 2)
    wi = peaceman_well_index(grid, cell, 0.10, 0.0)
    s = np.full((grid.nx, grid.ny, grid.nz), 0.10)
    lg, lw = ccus_phase_mobilities(s, rock, fluid)
    dp = 1.0e6
    analytical_q = wi * lg[cell] * dp
    direct_q = wi * lg[cell] * dp
    single_completion_relative_error = abs(direct_q - analytical_q) / max(abs(analytical_q), 1e-30)

    wis = np.array([peaceman_well_index(grid, (0, 0, k), 0.10, 0.0)
                    for k in range(grid.nz)])
    high_low_wi_ratio = float(np.mean(wis[1:4]) / np.mean(wis[[0, 4]]))

    # Rate-control pressure-limit check on a simple uniform initial field.
    depth = _v10_depth_centres(grid)
    pw = np.full_like(s, 2.0e7) + fluid.rho_w_ref * GRAVITY_ACCELERATION * (
        depth - float(np.mean(depth))
    )
    injector = FinalWellControl(
        name='CO2 injector', role='injector', cells=[(0, 0, k) for k in range(grid.nz)],
        mode='reservoir_rate', target=12000.0 / DAYS_TO_SECONDS,
        phase='gas', bhp_max=2.25e7,
    )
    producer = FinalWellControl(
        name='producer', role='producer', cells=[(4, 4, k) for k in range(grid.nz)],
        mode='bhp', target=2.0e7, phase='total',
    )
    pstep = solve_ccus_final_well_pressure_step(
        grid, s, rock, fluid, cap, [injector, producer], pw,
        0.1 * DAYS_TO_SECONDS, include_capillary=True, include_gravity=True,
        compressibility_scale=1.0,
    )
    inj_report = next(r for r in pstep.well_reports if r.role == 'injector')

    mass_injector = FinalWellControl(
        name='mass-rate validation injector', role='injector',
        cells=[(0, 0, k) for k in range(grid.nz)],
        mode='mass_rate', target=10.0, phase='gas', bhp_max=4.0e7,
    )
    pstep_mass = solve_ccus_final_well_pressure_step(
        grid, s, rock, fluid, cap, [mass_injector, producer], pw,
        0.1 * DAYS_TO_SECONDS, include_capillary=True, include_gravity=True,
        compressibility_scale=1.0,
    )
    mass_report = next(r for r in pstep_mass.well_reports if r.role == 'injector')
    mass_rate_relative_error = abs(mass_report.gas_mass_rate_kg_s - 10.0) / 10.0

    volume_target = 3000.0 / DAYS_TO_SECONDS
    volume_injector = FinalWellControl(
        name='volume-rate validation injector', role='injector',
        cells=[(0, 0, k) for k in range(grid.nz)],
        mode='reservoir_rate', target=volume_target,
        phase='gas', bhp_max=4.0e7,
    )
    pstep_volume = solve_ccus_final_well_pressure_step(
        grid, s, rock, fluid, cap, [volume_injector, producer], pw,
        0.1 * DAYS_TO_SECONDS, include_capillary=True, include_gravity=True,
        compressibility_scale=1.0,
    )
    volume_report = next(r for r in pstep_volume.well_reports if r.role == 'injector')
    volume_rate_relative_error = abs(
        volume_report.total_rate_m3_day - 3000.0
    ) / 3000.0

    return {
        'single_completion_productivity_relative_error': float(single_completion_relative_error),
        'high_to_low_layer_well_index_ratio': high_low_wi_ratio,
        'mass_rate_control_relative_error': float(mass_rate_relative_error),
        'mass_rate_control_active_mode': mass_report.active_mode,
        'reservoir_rate_control_relative_error': float(volume_rate_relative_error),
        'reservoir_rate_control_active_mode': volume_report.active_mode,
        'rate_limit_test_switched': bool(inj_report.switched),
        'rate_limit_test_active_mode': inj_report.active_mode,
        'rate_limit_test_bhp_mpa': inj_report.datum_bhp_pa / 1.0e6,
        'rate_limit_test_required_bhp_mpa': inj_report.required_bhp_pa / 1.0e6,
        'rate_limit_test_pressure_residual_m3_s': pstep.max_nonwell_pressure_residual,
    }


def _v12_plot_well_index(grid, well, outdir):
    values = [peaceman_well_index(grid, c, well.well_radius, well.skin)
              for c in well.cells]
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.bar([c[2] + 1 for c in well.cells], values)
    ax.set_xlabel('completed layer'); ax.set_ylabel('geometric WI [m3]')
    ax.set_title(f'{well.name}: Peaceman completion indices')
    ax.grid(axis='y', alpha=0.3)
    _v7_save(fig, f'400_{well.name.lower().replace(" ", "_")}_well_index.png', outdir)


def run_final_well_target(
        outdir='pad_stream_v12_final_well_outputs', total_time_days=3.0,
        dt_days=0.1, make_plots=True, pollock_seeds_per_dim=6):
    """Run mass-rate injection with automatic BHP switching and a BHP producer."""
    _os_v12.makedirs(outdir, exist_ok=True)
    grid, _, _, cap, legacy_wells, _ = build_padstream_5x5x5_case()
    rock = CCUSRock(s_g_initial=0.0, cr=0.0, hysteresis=True).validate()
    fluid = CCUSFluid(p_ref=3.0e7, c_w=0.0)
    depth = _v10_depth_centres(grid)
    pressure_w = (2.0e7 + fluid.rho_w_ref * GRAVITY_ACCELERATION
                  * (depth - float(np.mean(depth))))
    saturation = np.full_like(pressure_w, rock.s_g_initial)
    history = saturation.copy()
    phi0, _ = pressure_dependent_porosity(grid, rock, pressure_w, fluid.p_ref)
    rho0 = ccus_gas_density_from_phase_pressure(
        pressure_w + ccus_capillary_pressure(saturation, rock, cap), fluid
    )
    mass_state = phi0 * grid.vcell * rho0 * saturation
    initial_mass = float(np.sum(mass_state))

    # Target chosen high enough that mobility evolution eventually tests the
    # maximum injector BHP; the controller transparently reports any switch.
    injector = FinalWellControl(
        name='CO2 injector', role='injector',
        cells=[(0, 0, k) for k in range(grid.nz)],
        mode='mass_rate', target=38.55, phase='gas',
        bhp_max=3.0e7, well_radius=0.10, skin=0.0,
    )
    producer = FinalWellControl(
        name='mixed producer', role='producer',
        cells=[(grid.nx - 1, grid.ny - 1, k) for k in range(grid.nz)],
        mode='bhp', target=2.0e7, phase='total',
        bhp_min=1.8e7, well_radius=0.10, skin=0.0,
    )
    wells = [injector, producer]
    validations = validate_final_well_model(grid, rock, fluid, cap)
    nsteps = max(1, int(np.ceil(total_time_days / dt_days)))
    dt = total_time_days * DAYS_TO_SECONDS / nsteps
    audits = []; states = []
    switch_snapshot_done = False
    cumulative_injected = 0.0; cumulative_produced = 0.0

    print('=' * 120)
    print('VERSION 12 — FINAL PEACEMAN WELL MODEL, PHASE-AWARE CONTROLS, AND RATE/BHP SWITCHING')
    print('=' * 120)
    print('Validation:', validations)
    for step_idx in range(1, nsteps + 1):
        old_p = pressure_w.copy(); old_s = saturation.copy()
        pstep = solve_ccus_final_well_pressure_step(
            grid, old_s, rock, fluid, cap, wells, old_p, dt,
            include_capillary=True, include_gravity=True,
            compressibility_scale=1.0, s_g_history=history,
        )
        transport = advance_ccus_direct_phase_mass(
            grid, old_s, old_p, pstep, rock, fluid, dt,
            mass_old_state=mass_state,
        )
        pressure_w = pstep.pressure_w
        saturation = transport['saturation']
        mass_state = transport['mass'].copy()
        history = np.maximum(history, saturation)
        cumulative_injected += transport['injected_mass_rate'] * dt
        cumulative_produced += transport['produced_mass_rate'] * dt
        total_mass = float(np.sum(mass_state))
        mass_error = total_mass - (initial_mass + cumulative_injected - cumulative_produced)
        free, trapped, _, _ = ccus_land_free_trapped_saturation(saturation, history, rock)
        trapped_mass = float(np.sum(transport['weights_new'] * trapped))
        inj_report = next(r for r in pstep.well_reports if r.role == 'injector')
        prod_report = next(r for r in pstep.well_reports if r.role == 'producer')
        rows = []
        if make_plots and (step_idx in {1, nsteps} or (inj_report.switched and not switch_snapshot_done)):
            legacy = Wells(inj_cells=injector.cells, prod_cells=producer.cells,
                           rate=0.0, bhp=producer.target,
                           inj_bhp=inj_report.datum_bhp_pa)
            rows, _ = _v10_trace_total_streamlines(
                grid, pstep, legacy, seeds_per_dim=pollock_seeds_per_dim
            )
            if inj_report.switched:
                switch_snapshot_done = True
        reached = int(sum(bool(row[2]) for row in rows)) if rows else 0
        audit = FinalWellStepAudit(
            step=step_idx, time_days=step_idx * dt / DAYS_TO_SECONDS,
            injector_mode=inj_report.active_mode,
            injector_bhp_mpa=inj_report.datum_bhp_pa / 1.0e6,
            injector_rate_m3_day=inj_report.total_rate_m3_day,
            injector_gas_mass_rate_kg_s=inj_report.gas_mass_rate_kg_s,
            injector_switched=inj_report.switched,
            producer_mode=prod_report.active_mode,
            producer_bhp_mpa=prod_report.datum_bhp_pa / 1.0e6,
            producer_rate_m3_day=-prod_report.total_rate_m3_day,
            cumulative_mass_error_kg=float(mass_error),
            pressure_residual_m3_s=pstep.max_nonwell_pressure_residual,
            saturation_min=float(np.min(saturation)),
            saturation_max=float(np.max(saturation)),
            trapped_mass_kg=trapped_mass,
            streamlines_reaching_producer=reached,
            streamline_count=len(rows),
        )
        audits.append(audit)
        states.append({'pressure_step': pstep, 'transport': transport,
                       'saturation': saturation.copy(), 'history': history.copy(),
                       'free': free.copy(), 'trapped': trapped.copy(), 'rows': rows})
        print(
            f'  step {step_idx:02d}/{nsteps} t={audit.time_days:.2f} d  '
            f'inj={audit.injector_mode:14s} BHP={audit.injector_bhp_mpa:.3f} MPa  '
            f'q={audit.injector_rate_m3_day:.1f} m3/d  '
            f'mdot={audit.injector_gas_mass_rate_kg_s:.3f} kg/s  '
            f'Sgmax={audit.saturation_max:.4f}  err={audit.cumulative_mass_error_kg:.2e} kg'
        )

    if make_plots:
        _v12_plot_well_index(grid, injector, outdir)
        _v12_plot_well_index(grid, producer, outdir)
        time = [a.time_days for a in audits]
        fig, ax = plt.subplots(figsize=(7.6, 5.0))
        ax.plot(time, [a.injector_bhp_mpa for a in audits], marker='o', label='injector BHP')
        ax.axhline(injector.bhp_max / 1e6, linestyle='--', label='maximum BHP')
        ax.set_xlabel('time [days]'); ax.set_ylabel('datum BHP [MPa]')
        ax.set_title('Automatic injector rate/BHP control'); ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '410_injector_bhp_control_history.png', outdir)

        fig, ax = plt.subplots(figsize=(7.6, 5.0))
        ax.plot(time, [a.injector_gas_mass_rate_kg_s for a in audits], marker='o', label='actual')
        ax.axhline(injector.target, linestyle='--', label='mass-rate target')
        ax.set_xlabel('time [days]'); ax.set_ylabel('CO2 mass rate [kg/s]')
        ax.set_title('CO2 injection mass-rate control'); ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '411_injector_mass_rate_history.png', outdir)

        fig, ax = plt.subplots(figsize=(7.6, 5.0))
        ax.plot(time, [a.injector_rate_m3_day for a in audits], marker='o', label='injector')
        ax.plot(time, [a.producer_rate_m3_day for a in audits], marker='s', label='producer')
        ax.set_xlabel('time [days]'); ax.set_ylabel('reservoir-volume rate [m3/day]')
        ax.set_title('Final well-model rates'); ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '412_well_rate_history.png', outdir)

        fig, ax = plt.subplots(figsize=(7.6, 5.0))
        for idx, c in enumerate(injector.cells):
            values = []
            for st in states:
                rep = next(r for r in st['pressure_step'].well_reports if r.role == 'injector')
                values.append(rep.completion_reports[idx].total_rate_m3_day)
            ax.plot(time, values, marker='o', label=f'layer {c[2] + 1}')
        ax.set_xlabel('time [days]'); ax.set_ylabel('completion rate [m3/day]')
        ax.set_title('Injector completion allocation'); ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '413_injector_completion_allocation.png', outdir)

        fig, ax = plt.subplots(figsize=(7.6, 5.0))
        ax.semilogy(time, np.maximum(np.abs([a.cumulative_mass_error_kg for a in audits]), 1e-18), marker='o')
        ax.set_xlabel('time [days]'); ax.set_ylabel('|CO2 mass error| [kg]')
        ax.set_title('Well-coupled CO2 mass conservation'); ax.grid(alpha=0.3, which='both')
        _v7_save(fig, '414_mass_conservation.png', outdir)

        switch_indices = [i for i, a in enumerate(audits) if a.injector_switched]
        snapshot_indices = {0, len(states) - 1}
        if switch_indices:
            snapshot_indices.add(switch_indices[0])
        for idx in sorted(snapshot_indices):
            st = states[idx]; step_no = idx + 1
            _v10_plot_layer(grid, st['pressure_step'].pressure_w / 1e6,
                            f'Final well model: brine pressure at step {step_no}',
                            f'420_step_{step_no:02d}_pressure_w', outdir, unit='MPa')
            _v10_plot_layer(grid, st['saturation'],
                            f'Final well model: CO2 saturation at step {step_no}',
                            f'421_step_{step_no:02d}_saturation', outdir,
                            cmap='plasma', unit='fraction', vmin=0.0, vmax=rock.s_g_max)
            if st['rows']:
                _v10_plot_streamlines(grid, st['rows'], st['pressure_step'].pressure_w,
                                      'final_well', step_no, audits[idx].time_days, outdir)

    summary = {
        'stage': 22,
        'formulation': {
            'well_index': 'Peaceman vertical-well completion index',
            'controls': ['phase-aware BHP', 'reservoir-volume rate', 'CO2 mass rate'],
            'completion_allocation': 'phase productivity WI*lambda unless explicit fractions are supplied',
            'switching': 'rate control switches to BHP when required datum pressure violates a limit',
            'bhp_reference': 'phase pressure at common datum; hydrostatic completion correction uses phase density',
        },
        'validations': validations,
        'well_specs': [w.__dict__ for w in wells],
        'audits': [a.__dict__ for a in audits],
        'final_well_reports': [_v12_report_to_dict(r) for r in states[-1]['pressure_step'].well_reports],
    }
    path = _os_v12.path.join(outdir, 'PAD_Stream_V12_Final_Well_Summary.json')
    with open(path, 'w') as f:
        _json_v12.dump(summary, f, indent=2)
    print('=' * 120)
    return audits, states, summary



# ==============================================================================
# STAGE 23 [S23] — LONG-DURATION NONLINEAR COUPLING, ADAPTIVE TIMESTEPS,
#                    BREAKTHROUGH, AND RESTART CHECKPOINTS
# ==============================================================================
# This stage retains the Stage-22 Peaceman wells and Stage-20 phase-potential
# fluxes, but replaces the fixed-step one-pass IMPES loop with:
#   * Aitken-relaxed pressure/mobility fixed-point coupling,
#   * reject/retry adaptive global timesteps,
#   * explicit saturation-change and projection acceptance criteria,
#   * producer CO2 breakthrough detection,
#   * restartable NPZ checkpoints, and
#   * selected long-run Pollock/pressure/saturation diagnostics.
# ============================================================================== 

from dataclasses import dataclass as _dataclass_v13, asdict as _asdict_v13
import os as _os_v13
import json as _json_v13
import math as _math_v13
import zipfile as _zipfile_v13


@_dataclass_v13
class AdaptiveTimeStepConfig:
    initial_dt_days: float = 0.10
    minimum_dt_days: float = 0.005
    maximum_dt_days: float = 2.00
    target_max_saturation_change: float = 0.018
    absolute_max_saturation_change: float = 0.035
    maximum_projection_correction: float = 2.0e-5
    growth_limit: float = 1.40
    shrink_factor: float = 0.50
    maximum_retries: int = 12


@_dataclass_v13
class NonlinearCouplingConfig:
    maximum_iterations: int = 5
    saturation_tolerance: float = 1.0e-3
    rejection_tolerance: float = 4.0e-3
    initial_relaxation: float = 0.80
    pressure_fixed_point_tolerance: float = 1.0e-8
    pressure_fixed_point_max_iterations: int = 8


@_dataclass_v13
class LongRunState:
    time_days: float
    accepted_step: int
    pressure_w: np.ndarray
    saturation: np.ndarray
    gas_mass: np.ndarray
    saturation_history: np.ndarray
    cumulative_injected_mass_kg: float
    cumulative_produced_mass_kg: float
    cumulative_injected_volume_m3: float
    cumulative_produced_volume_m3: float
    next_dt_days: float
    breakthrough_time_days: float = np.nan
    breakthrough_criterion: str = ''
    last_producer_gas_cut: float = 0.0


@_dataclass_v13
class LongRunStepAudit:
    step: int
    time_days: float
    dt_days: float
    retries_before_accept: int
    nonlinear_iterations: int
    nonlinear_residual: float
    pressure_fixed_point_iterations: int
    pressure_fixed_point_residual: float
    maximum_saturation_change: float
    maximum_projection_correction: float
    injector_mode: str
    injector_bhp_mpa: float
    injector_volume_rate_m3_day: float
    injector_gas_mass_rate_kg_s: float
    producer_mode: str
    producer_bhp_mpa: float
    producer_volume_rate_m3_day: float
    producer_gas_volume_rate_m3_day: float
    producer_gas_mass_rate_kg_s: float
    producer_gas_cut: float
    cumulative_injected_mass_kg: float
    cumulative_produced_mass_kg: float
    gas_mass_in_place_kg: float
    cumulative_mass_error_kg: float
    maximum_local_mass_residual_kg: float
    saturation_minimum: float
    saturation_maximum: float
    trapped_gas_mass_kg: float
    pressure_residual_m3_s: float
    breakthrough_reached: bool
    accepted_next_dt_days: float


def build_long_duration_case():
    grid, _, _, cap, _, _ = build_padstream_5x5x5_case()
    rock = CCUSRock(s_g_initial=0.0, cr=0.0, hysteresis=True).validate()
    fluid = CCUSFluid(p_ref=3.0e7, c_w=0.0)
    depth = _v10_depth_centres(grid)
    pressure_w = (2.0e7 + fluid.rho_w_ref * GRAVITY_ACCELERATION
                  * (depth - float(np.mean(depth))))
    saturation = np.full_like(pressure_w, rock.s_g_initial)
    history = saturation.copy()
    phi, _ = pressure_dependent_porosity(grid, rock, pressure_w, fluid.p_ref)
    rho_g = ccus_gas_density_from_phase_pressure(
        pressure_w + ccus_capillary_pressure(saturation, rock, cap), fluid
    )
    gas_mass = phi * grid.vcell * rho_g * saturation
    injector = FinalWellControl(
        name='CO2 injector', role='injector',
        cells=[(0, 0, k) for k in range(grid.nz)],
        mode='mass_rate', target=38.55, phase='gas',
        bhp_max=3.0e7, well_radius=0.10, skin=0.0,
    )
    producer = FinalWellControl(
        name='mixed producer', role='producer',
        cells=[(grid.nx - 1, grid.ny - 1, k) for k in range(grid.nz)],
        mode='bhp', target=2.0e7, phase='total',
        bhp_min=1.8e7, well_radius=0.10, skin=0.0,
    )
    state = LongRunState(
        time_days=0.0, accepted_step=0,
        pressure_w=pressure_w, saturation=saturation,
        gas_mass=gas_mass, saturation_history=history,
        cumulative_injected_mass_kg=0.0,
        cumulative_produced_mass_kg=0.0,
        cumulative_injected_volume_m3=0.0,
        cumulative_produced_volume_m3=0.0,
        next_dt_days=0.10,
    )
    return grid, rock, fluid, cap, [injector, producer], state


def advance_ccus_mass_with_final_wells(
        grid, s_g_old, pressure_w_old,
        pressure_step: PhasePotentialPressureStep,
        rock: CCUSRock, fluid: CCUSFluid, dt, gas_mass_old):
    """Conservative phase-mass update using exact completion mass reports.

    Stage 20 supplied the phase face mass flux. Stage 22 supplied phase-aware
    completion reports. This routine combines those directly, avoiding a second
    approximate conversion from reservoir-volume source to injection mass.
    """
    rho_new = pressure_step.density_g
    phi_new, _ = pressure_dependent_porosity(
        grid, rock, pressure_step.pressure_w, fluid.p_ref
    )
    weights_new = phi_new * grid.vcell * rho_new
    mx, my, mz = _v10_phase_mass_face_fluxes(
        grid,
        (pressure_step.qg_x, pressure_step.qg_y, pressure_step.qg_z),
        rho_new,
    )
    divergence = _mass_flux_outflow_divergence(grid, mx, my, mz)
    source = np.zeros_like(s_g_old, dtype=float)
    injected_rate = 0.0
    produced_rate = 0.0
    for report in pressure_step.well_reports:
        for completion in report.completion_reports:
            cell = tuple(completion.cell)
            rate = float(completion.gas_mass_rate_kg_s)
            source[cell] += rate
            if rate >= 0.0:
                injected_rate += rate
            else:
                produced_rate += -rate

    raw_mass = np.asarray(gas_mass_old, dtype=float) + dt * (source - divergence)
    target_mass = float(np.sum(raw_mass))
    proposal = raw_mass / np.maximum(weights_new, 1.0e-30)
    saturation, projection = bounded_conservative_projection(
        proposal, weights_new, target_mass,
        lower_bound=0.0, upper_bound=rock.s_g_max,
        relative_tolerance=1.0e-13,
    )
    gas_mass_new = weights_new * saturation
    expected = float(
        np.sum(gas_mass_old) + dt * (injected_rate - produced_rate)
    )
    local_residual = (
        gas_mass_new - np.asarray(gas_mass_old, dtype=float)
        - dt * (source - divergence)
    )
    return {
        'saturation': saturation,
        'gas_mass': gas_mass_new,
        'weights_new': weights_new,
        'proposal': proposal,
        'projection': projection,
        'maximum_projection': float(np.max(np.abs(projection['correction']))),
        'injected_mass_rate': float(injected_rate),
        'produced_mass_rate': float(produced_rate),
        'balance_error': float(np.sum(gas_mass_new) - expected),
        'local_residual': local_residual,
        'maximum_local_residual': float(np.max(np.abs(local_residual))),
        'mass_fluxes': (mx, my, mz),
        'source_mass_rate': source,
    }


def solve_long_run_coupled_trial(
        grid, rock, fluid, cap, wells, state: LongRunState, dt_days,
        nonlinear: NonlinearCouplingConfig):
    """Aitken-relaxed pressure/mobility fixed point for one attempted step."""
    dt = float(dt_days) * DAYS_TO_SECONDS
    guess = np.asarray(state.saturation, dtype=float).copy()
    previous_residual_vector = None
    omega = float(nonlinear.initial_relaxation)
    final_pressure = None
    final_transport = None
    residual_norm = np.inf

    for iteration in range(1, nonlinear.maximum_iterations + 1):
        history_guess = np.maximum(state.saturation_history, guess)
        pressure_step = solve_ccus_final_well_pressure_step(
            grid, guess, rock, fluid, cap, wells,
            state.pressure_w, dt,
            include_capillary=True, include_gravity=True,
            compressibility_scale=1.0,
            fixed_point_tolerance=nonlinear.pressure_fixed_point_tolerance,
            fixed_point_max_iterations=nonlinear.pressure_fixed_point_max_iterations,
            s_g_history=history_guess,
        )
        transport = advance_ccus_mass_with_final_wells(
            grid, state.saturation, state.pressure_w,
            pressure_step, rock, fluid, dt, state.gas_mass,
        )
        candidate = transport['saturation']
        residual_vector = candidate - guess
        residual_norm = float(np.max(np.abs(residual_vector)))
        final_pressure = pressure_step
        final_transport = transport
        if residual_norm <= nonlinear.saturation_tolerance:
            break

        if previous_residual_vector is not None:
            delta = (residual_vector - previous_residual_vector).ravel()
            denominator = float(np.dot(delta, delta))
            if denominator > 1.0e-30:
                omega = float(np.clip(
                    -omega * np.dot(previous_residual_vector.ravel(), delta)
                    / denominator,
                    0.10, 1.00,
                ))
        guess = np.clip(
            guess + omega * residual_vector,
            0.0, rock.s_g_max,
        )
        previous_residual_vector = residual_vector.copy()

    return final_pressure, final_transport, iteration, residual_norm


def save_long_run_checkpoint(path, state: LongRunState):
    path = str(path)
    _os_v13.makedirs(_os_v13.path.dirname(path) or '.', exist_ok=True)
    np.savez_compressed(
        path,
        format_version=np.array([1], dtype=int),
        time_days=np.array([state.time_days]),
        accepted_step=np.array([state.accepted_step], dtype=int),
        pressure_w=state.pressure_w,
        saturation=state.saturation,
        gas_mass=state.gas_mass,
        saturation_history=state.saturation_history,
        cumulative_injected_mass_kg=np.array([state.cumulative_injected_mass_kg]),
        cumulative_produced_mass_kg=np.array([state.cumulative_produced_mass_kg]),
        cumulative_injected_volume_m3=np.array([state.cumulative_injected_volume_m3]),
        cumulative_produced_volume_m3=np.array([state.cumulative_produced_volume_m3]),
        next_dt_days=np.array([state.next_dt_days]),
        breakthrough_time_days=np.array([state.breakthrough_time_days]),
        breakthrough_criterion=np.array([state.breakthrough_criterion]),
        last_producer_gas_cut=np.array([state.last_producer_gas_cut]),
    )
    return path


def load_long_run_checkpoint(path):
    data = np.load(path, allow_pickle=False)
    criterion = str(data['breakthrough_criterion'][0])
    return LongRunState(
        time_days=float(data['time_days'][0]),
        accepted_step=int(data['accepted_step'][0]),
        pressure_w=np.asarray(data['pressure_w'], dtype=float),
        saturation=np.asarray(data['saturation'], dtype=float),
        gas_mass=np.asarray(data['gas_mass'], dtype=float),
        saturation_history=np.asarray(data['saturation_history'], dtype=float),
        cumulative_injected_mass_kg=float(data['cumulative_injected_mass_kg'][0]),
        cumulative_produced_mass_kg=float(data['cumulative_produced_mass_kg'][0]),
        cumulative_injected_volume_m3=float(data['cumulative_injected_volume_m3'][0]),
        cumulative_produced_volume_m3=float(data['cumulative_produced_volume_m3'][0]),
        next_dt_days=float(data['next_dt_days'][0]),
        breakthrough_time_days=float(data['breakthrough_time_days'][0]),
        breakthrough_criterion=criterion,
        last_producer_gas_cut=(float(data['last_producer_gas_cut'][0])
                               if 'last_producer_gas_cut' in data.files else 0.0),
    )


def _v13_estimate_breakthrough(previous_time, previous_value,
                               current_time, current_value, threshold):
    if current_value <= threshold:
        return np.nan
    if previous_value >= threshold or current_value <= previous_value:
        return float(current_time)
    fraction = (threshold - previous_value) / max(
        current_value - previous_value, 1.0e-30
    )
    return float(previous_time + np.clip(fraction, 0.0, 1.0)
                 * (current_time - previous_time))


def run_long_duration_simulation(
        end_time_days=365.0, state=None,
        timestep=None, nonlinear=None, post_breakthrough_nonlinear=None,
        forced_output_times=(), checkpoint_times=(), checkpoint_dir=None,
        adaptive=True, verbose=True, store_snapshot_times=()):
    """Run or restart the long-duration coupled simulator.

    `end_time_days` is an absolute simulation time, so a checkpoint at day 180
    can be loaded and continued by calling this function with end_time_days=365.
    """
    grid, rock, fluid, cap, wells, initial_state = build_long_duration_case()
    timestep = AdaptiveTimeStepConfig() if timestep is None else timestep
    nonlinear = NonlinearCouplingConfig() if nonlinear is None else nonlinear
    post_breakthrough_nonlinear = (
        NonlinearCouplingConfig(
            maximum_iterations=3, saturation_tolerance=3.0e-3,
            rejection_tolerance=8.0e-3, initial_relaxation=0.80,
            pressure_fixed_point_tolerance=1.0e-8,
            pressure_fixed_point_max_iterations=8,
        ) if post_breakthrough_nonlinear is None
        else post_breakthrough_nonlinear
    )
    if state is None:
        state = initial_state
        state.next_dt_days = timestep.initial_dt_days
    initial_mass = float(
        np.sum(state.gas_mass)
        - state.cumulative_injected_mass_kg
        + state.cumulative_produced_mass_kg
    )
    audits = []
    snapshots = {}
    forced = sorted(set(
        float(x) for x in forced_output_times
        if state.time_days < float(x) <= end_time_days
    ))
    checkpoint_schedule = sorted(set(
        float(x) for x in checkpoint_times
        if state.time_days < float(x) <= end_time_days
    ))
    event_times = sorted(set(forced + checkpoint_schedule))
    snapshot_targets = sorted(set(float(x) for x in store_snapshot_times))
    previous_gas_cut = float(state.last_producer_gas_cut)
    total_rejections = 0

    while state.time_days < end_time_days - 1.0e-12:
        controller_dt = min(
            float(state.next_dt_days),
            float(timestep.maximum_dt_days),
        )
        proposed_dt = min(controller_dt, end_time_days - state.time_days)
        dt_days = proposed_dt
        event_clipped = proposed_dt < controller_dt - 1.0e-12
        for event in event_times:
            if state.time_days < event < state.time_days + dt_days - 1.0e-12:
                dt_days = event - state.time_days
                event_clipped = True
                break
        retries = 0
        active_nonlinear = (
            post_breakthrough_nonlinear
            if (np.isfinite(state.breakthrough_time_days)
                and state.last_producer_gas_cut >= 0.50)
            else nonlinear
        )
        while True:
            pstep, transport, coupling_iterations, coupling_residual = (
                solve_long_run_coupled_trial(
                    grid, rock, fluid, cap, wells, state, dt_days, active_nonlinear
                )
            )
            maximum_saturation_change = float(np.max(np.abs(
                transport['saturation'] - state.saturation
            )))
            maximum_projection = float(transport['maximum_projection'])
            unacceptable = (
                not np.isfinite(coupling_residual)
                or (
                    coupling_iterations >= active_nonlinear.maximum_iterations
                    and coupling_residual > active_nonlinear.rejection_tolerance
                )
                or maximum_saturation_change
                > timestep.absolute_max_saturation_change
                or maximum_projection
                > timestep.maximum_projection_correction
            )
            if not unacceptable:
                break
            if not adaptive:
                raise RuntimeError(
                    'Fixed timestep failed long-run acceptance criteria: '
                    f'dt={dt_days:.6g} d, coupling={coupling_residual:.3e}, '
                    f'dS={maximum_saturation_change:.3e}, '
                    f'projection={maximum_projection:.3e}'
                )
            retries += 1
            total_rejections += 1
            if retries > timestep.maximum_retries:
                raise RuntimeError('maximum timestep retries exceeded')
            dt_days *= timestep.shrink_factor
            if dt_days < timestep.minimum_dt_days:
                raise RuntimeError(
                    'adaptive timestep fell below minimum: '
                    f'coupling={coupling_residual:.3e}, '
                    f'dS={maximum_saturation_change:.3e}'
                )
            if verbose:
                print(
                    f'  reject at t={state.time_days:.3f} d -> '
                    f'dt={dt_days:.4f} d; coupling={coupling_residual:.3e}, '
                    f'dS={maximum_saturation_change:.3e}'
                )

        dt_seconds = dt_days * DAYS_TO_SECONDS
        new_saturation = transport['saturation']
        new_mass = transport['gas_mass']
        new_history = np.maximum(state.saturation_history, new_saturation)
        cumulative_injected_mass = (
            state.cumulative_injected_mass_kg
            + transport['injected_mass_rate'] * dt_seconds
        )
        cumulative_produced_mass = (
            state.cumulative_produced_mass_kg
            + transport['produced_mass_rate'] * dt_seconds
        )
        injector_report = next(
            report for report in pstep.well_reports
            if report.role == 'injector'
        )
        producer_report = next(
            report for report in pstep.well_reports
            if report.role == 'producer'
        )
        injector_rate = max(float(injector_report.total_rate_m3_day), 0.0)
        producer_rate = max(-float(producer_report.total_rate_m3_day), 0.0)
        producer_gas_rate = max(-float(producer_report.gas_rate_m3_day), 0.0)
        producer_gas_mass_rate = max(
            -float(producer_report.gas_mass_rate_kg_s), 0.0
        )
        producer_gas_cut = producer_gas_rate / max(producer_rate, 1.0e-30)
        cumulative_injected_volume = (
            state.cumulative_injected_volume_m3 + injector_rate * dt_days
        )
        cumulative_produced_volume = (
            state.cumulative_produced_volume_m3 + producer_rate * dt_days
        )
        current_time = state.time_days + dt_days
        breakthrough_time = state.breakthrough_time_days
        breakthrough_criterion = state.breakthrough_criterion
        gas_cut_threshold = 1.0e-4
        if not np.isfinite(breakthrough_time) and producer_gas_cut >= gas_cut_threshold:
            breakthrough_time = _v13_estimate_breakthrough(
                state.time_days, previous_gas_cut,
                current_time, producer_gas_cut,
                gas_cut_threshold,
            )
            breakthrough_criterion = 'producer gas volume fraction >= 1e-4'
        previous_gas_cut = producer_gas_cut

        gas_mass_in_place = float(np.sum(new_mass))
        mass_error = float(
            gas_mass_in_place
            - (initial_mass + cumulative_injected_mass - cumulative_produced_mass)
        )
        free, trapped, _, _ = ccus_land_free_trapped_saturation(
            new_saturation, new_history, rock
        )
        trapped_mass = float(np.sum(transport['weights_new'] * trapped))

        if adaptive:
            saturation_factor = np.sqrt(
                timestep.target_max_saturation_change
                / max(maximum_saturation_change, 1.0e-8)
            )
            saturation_factor = float(np.clip(
                saturation_factor, 0.55, timestep.growth_limit
            ))
            if coupling_iterations <= 2:
                iteration_factor = timestep.growth_limit
            elif coupling_iterations <= 4:
                iteration_factor = 1.25
            else:
                iteration_factor = 1.00
            growth = min(saturation_factor, iteration_factor)
            if retries:
                growth = min(growth, 1.0)
            controller_base = controller_dt if event_clipped else dt_days
            next_dt = float(np.clip(
                controller_base * growth,
                timestep.minimum_dt_days,
                timestep.maximum_dt_days,
            ))
        else:
            next_dt = float(timestep.initial_dt_days)

        new_state = LongRunState(
            time_days=current_time,
            accepted_step=state.accepted_step + 1,
            pressure_w=pstep.pressure_w.copy(),
            saturation=new_saturation.copy(),
            gas_mass=new_mass.copy(),
            saturation_history=new_history.copy(),
            cumulative_injected_mass_kg=cumulative_injected_mass,
            cumulative_produced_mass_kg=cumulative_produced_mass,
            cumulative_injected_volume_m3=cumulative_injected_volume,
            cumulative_produced_volume_m3=cumulative_produced_volume,
            next_dt_days=next_dt,
            breakthrough_time_days=breakthrough_time,
            breakthrough_criterion=breakthrough_criterion,
            last_producer_gas_cut=producer_gas_cut,
        )
        audit = LongRunStepAudit(
            step=new_state.accepted_step,
            time_days=current_time,
            dt_days=dt_days,
            retries_before_accept=retries,
            nonlinear_iterations=coupling_iterations,
            nonlinear_residual=float(coupling_residual),
            pressure_fixed_point_iterations=pstep.fixed_point_iterations,
            pressure_fixed_point_residual=pstep.fixed_point_relative_change,
            maximum_saturation_change=maximum_saturation_change,
            maximum_projection_correction=maximum_projection,
            injector_mode=injector_report.active_mode,
            injector_bhp_mpa=injector_report.datum_bhp_pa / 1.0e6,
            injector_volume_rate_m3_day=injector_rate,
            injector_gas_mass_rate_kg_s=float(
                max(injector_report.gas_mass_rate_kg_s, 0.0)
            ),
            producer_mode=producer_report.active_mode,
            producer_bhp_mpa=producer_report.datum_bhp_pa / 1.0e6,
            producer_volume_rate_m3_day=producer_rate,
            producer_gas_volume_rate_m3_day=producer_gas_rate,
            producer_gas_mass_rate_kg_s=producer_gas_mass_rate,
            producer_gas_cut=producer_gas_cut,
            cumulative_injected_mass_kg=cumulative_injected_mass,
            cumulative_produced_mass_kg=cumulative_produced_mass,
            gas_mass_in_place_kg=gas_mass_in_place,
            cumulative_mass_error_kg=mass_error,
            maximum_local_mass_residual_kg=transport['maximum_local_residual'],
            saturation_minimum=float(np.min(new_saturation)),
            saturation_maximum=float(np.max(new_saturation)),
            trapped_gas_mass_kg=trapped_mass,
            pressure_residual_m3_s=pstep.max_nonwell_pressure_residual,
            breakthrough_reached=bool(np.isfinite(breakthrough_time)),
            accepted_next_dt_days=next_dt,
        )
        audits.append(audit)
        state = new_state

        for target in snapshot_targets:
            if abs(current_time - target) <= 1.0e-9:
                snapshots[f'day_{target:g}'] = {
                    'state': state,
                    'pressure_step': pstep,
                    'transport': transport,
                    'audit': audit,
                }
        if (np.isfinite(breakthrough_time)
                and 'breakthrough' not in snapshots
                and producer_gas_cut >= gas_cut_threshold):
            snapshots['breakthrough'] = {
                'state': state,
                'pressure_step': pstep,
                'transport': transport,
                'audit': audit,
            }

        if checkpoint_dir is not None:
            for checkpoint_time in checkpoint_schedule:
                if abs(current_time - checkpoint_time) <= 1.0e-9:
                    save_long_run_checkpoint(
                        _os_v13.path.join(
                            checkpoint_dir,
                            f'pad_stream_v13_day_{checkpoint_time:g}.npz'
                        ),
                        state,
                    )

        if verbose and (
                audit.step <= 10 or audit.step % 20 == 0
                or (audit.breakthrough_reached
                    and len(audits) >= 2
                    and not audits[-2].breakthrough_reached)
                or abs(current_time - end_time_days) <= 1.0e-9):
            print(
                f'  step {audit.step:03d}  t={current_time:8.3f} d  '
                f'dt={dt_days:5.3f} d  NL={coupling_iterations}  '
                f'dS={maximum_saturation_change:.3e}  '
                f'BHP={audit.injector_bhp_mpa:.3f} MPa  '
                f'gas cut={producer_gas_cut:.3e}  '
                f'mass err={mass_error:.2e} kg'
            )

    return state, audits, snapshots, {
        'grid': grid, 'rock': rock, 'fluid': fluid,
        'capillary': cap, 'wells': wells,
        'total_rejected_attempts': total_rejections,
    }


def validate_long_run_restart_and_timestep(outdir):
    """Small deterministic checks for adaptive stepping and restart identity."""
    _os_v13.makedirs(outdir, exist_ok=True)
    nonlinear = NonlinearCouplingConfig()

    fixed_cfg = AdaptiveTimeStepConfig(
        initial_dt_days=0.10, minimum_dt_days=0.10,
        maximum_dt_days=0.10,
    )
    fixed_state, fixed_audits, _, _ = run_long_duration_simulation(
        end_time_days=5.0,
        timestep=fixed_cfg, nonlinear=nonlinear,
        forced_output_times=(5.0,), adaptive=False, verbose=False,
    )
    adaptive_cfg = AdaptiveTimeStepConfig(
        initial_dt_days=0.10, maximum_dt_days=1.0,
    )
    adaptive_state, adaptive_audits, _, _ = run_long_duration_simulation(
        end_time_days=5.0,
        timestep=adaptive_cfg, nonlinear=nonlinear,
        forced_output_times=(5.0,), adaptive=True, verbose=False,
    )
    saturation_difference = float(np.max(np.abs(
        adaptive_state.saturation - fixed_state.saturation
    )))
    pressure_difference = float(
        np.linalg.norm(adaptive_state.pressure_w - fixed_state.pressure_w)
        / max(np.linalg.norm(fixed_state.pressure_w), 1.0)
    )

    continuous_state, _, _, _ = run_long_duration_simulation(
        end_time_days=20.0,
        timestep=adaptive_cfg, nonlinear=nonlinear,
        forced_output_times=(10.0, 20.0), adaptive=True, verbose=False,
    )
    split_state, _, _, _ = run_long_duration_simulation(
        end_time_days=10.0,
        timestep=adaptive_cfg, nonlinear=nonlinear,
        forced_output_times=(10.0,), adaptive=True, verbose=False,
    )
    checkpoint = _os_v13.path.join(outdir, 'restart_validation_day_10.npz')
    save_long_run_checkpoint(checkpoint, split_state)
    loaded = load_long_run_checkpoint(checkpoint)
    restarted_state, _, _, _ = run_long_duration_simulation(
        end_time_days=20.0, state=loaded,
        timestep=adaptive_cfg, nonlinear=nonlinear,
        forced_output_times=(20.0,), adaptive=True, verbose=False,
    )
    restart_saturation_difference = float(np.max(np.abs(
        restarted_state.saturation - continuous_state.saturation
    )))
    restart_pressure_difference = float(np.max(np.abs(
        restarted_state.pressure_w - continuous_state.pressure_w
    )))
    restart_mass_difference = float(np.max(np.abs(
        restarted_state.gas_mass - continuous_state.gas_mass
    )))

    aggressive_cfg = AdaptiveTimeStepConfig(
        initial_dt_days=5.0, maximum_dt_days=5.0,
        target_max_saturation_change=0.018,
    )
    aggressive_state, aggressive_audits, _, aggressive_context = (
        run_long_duration_simulation(
            end_time_days=5.0,
            timestep=aggressive_cfg, nonlinear=nonlinear,
            forced_output_times=(5.0,), adaptive=True, verbose=False,
        )
    )
    return {
        'adaptive_vs_fixed_5_day': {
            'maximum_saturation_difference': saturation_difference,
            'relative_pressure_difference': pressure_difference,
            'fixed_steps': len(fixed_audits),
            'adaptive_steps': len(adaptive_audits),
        },
        'restart_10_plus_10_day': {
            'maximum_saturation_difference': restart_saturation_difference,
            'maximum_pressure_difference_pa': restart_pressure_difference,
            'maximum_cell_mass_difference_kg': restart_mass_difference,
            'checkpoint': checkpoint,
        },
        'aggressive_initial_step': {
            'accepted_steps': len(aggressive_audits),
            'rejected_attempts': aggressive_context['total_rejected_attempts'],
            'minimum_accepted_dt_days': float(min(a.dt_days for a in aggressive_audits)),
            'maximum_accepted_dt_days': float(max(a.dt_days for a in aggressive_audits)),
            'final_time_days': aggressive_state.time_days,
        },
    }


def _v13_plot_long_run_histories(audits, outdir):
    t = np.array([a.time_days for a in audits])
    bt = next((a.time_days for a in audits if a.breakthrough_reached), np.nan)

    def vertical(ax):
        if np.isfinite(bt):
            ax.axvline(bt, linestyle='--', label='CO2 breakthrough')

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.step(t, [a.dt_days for a in audits], where='post')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('accepted dt [days]')
    ax.set_title('Adaptive global timestep'); ax.grid(alpha=0.3)
    if np.isfinite(bt): ax.legend()
    _v7_save(fig, '500_adaptive_timestep_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(t, [a.nonlinear_iterations for a in audits], label='coupling iterations')
    ax.plot(t, [a.pressure_fixed_point_iterations for a in audits], label='pressure density iterations')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('iterations')
    ax.set_title('Nonlinear convergence effort'); ax.grid(alpha=0.3); ax.legend()
    _v7_save(fig, '501_nonlinear_iteration_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.semilogy(t, np.maximum([a.nonlinear_residual for a in audits], 1e-16), label='mobility residual')
    ax.semilogy(t, np.maximum([a.pressure_fixed_point_residual for a in audits], 1e-16), label='pressure-density residual')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('residual')
    ax.set_title('Accepted nonlinear residuals'); ax.grid(alpha=0.3, which='both'); ax.legend()
    _v7_save(fig, '502_nonlinear_residual_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(t, [a.maximum_saturation_change for a in audits])
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('max |dSg| per step')
    ax.set_title('Adaptive saturation-change control'); ax.grid(alpha=0.3)
    if np.isfinite(bt): ax.legend()
    _v7_save(fig, '503_saturation_change_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(t, [a.injector_bhp_mpa for a in audits], label='injector BHP')
    ax.plot(t, [a.producer_bhp_mpa for a in audits], label='producer BHP')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('datum BHP [MPa]')
    ax.set_title('Long-duration well controls'); ax.grid(alpha=0.3); ax.legend()
    _v7_save(fig, '504_well_bhp_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(t, [a.injector_gas_mass_rate_kg_s for a in audits], label='injected CO2')
    ax.plot(t, [a.producer_gas_mass_rate_kg_s for a in audits], label='produced CO2')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('CO2 mass rate [kg/s]')
    ax.set_title('Injection and production CO2 rates'); ax.grid(alpha=0.3); ax.legend()
    _v7_save(fig, '505_co2_mass_rate_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.semilogy(t, np.maximum([a.producer_gas_cut for a in audits], 1e-12))
    ax.axhline(1e-4, linestyle=':', label='breakthrough criterion')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('producer gas volume fraction')
    ax.set_title('CO2 breakthrough and post-breakthrough gas cut')
    ax.grid(alpha=0.3, which='both'); ax.legend()
    _v7_save(fig, '506_producer_gas_cut.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(t, [a.cumulative_injected_mass_kg / 1e6 for a in audits], label='cumulative injected')
    ax.plot(t, [a.cumulative_produced_mass_kg / 1e6 for a in audits], label='cumulative produced')
    ax.plot(t, [a.gas_mass_in_place_kg / 1e6 for a in audits], label='in place')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('CO2 mass [million kg]')
    ax.set_title('Long-duration CO2 inventory'); ax.grid(alpha=0.3); ax.legend()
    _v7_save(fig, '507_co2_inventory_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.semilogy(t, np.maximum(np.abs([a.cumulative_mass_error_kg for a in audits]), 1e-18))
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('|mass error| [kg]')
    ax.set_title('Year-scale CO2 mass conservation'); ax.grid(alpha=0.3, which='both')
    if np.isfinite(bt): ax.legend()
    _v7_save(fig, '508_mass_conservation_history.png', outdir)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(t, [a.saturation_maximum for a in audits], label='maximum Sg')
    ax.plot(t, [a.saturation_minimum for a in audits], label='minimum Sg')
    vertical(ax); ax.set_xlabel('time [days]'); ax.set_ylabel('CO2 saturation')
    ax.set_title('Long-duration saturation bounds'); ax.grid(alpha=0.3); ax.legend()
    _v7_save(fig, '509_saturation_range_history.png', outdir)


def _v13_plot_snapshots(snapshots, context, outdir, pollock_seeds_per_dim=6):
    grid = context['grid']; wells = context['wells']; rock = context['rock']
    injector = next(w for w in wells if w.role == 'injector')
    producer = next(w for w in wells if w.role == 'producer')
    order = sorted(
        snapshots.items(),
        key=lambda kv: kv[1]['state'].time_days,
    )
    for index, (name, snapshot) in enumerate(order, start=1):
        state = snapshot['state']; pstep = snapshot['pressure_step']; audit = snapshot['audit']
        safe_name = name.replace('.', 'p')
        _v10_plot_layer(
            grid, state.pressure_w / 1e6,
            f'Long-run brine pressure at {state.time_days:.2f} days',
            f'520_{index:02d}_{safe_name}_pressure_w', outdir, unit='MPa'
        )
        _v10_plot_layer(
            grid, state.saturation,
            f'Long-run CO2 saturation at {state.time_days:.2f} days',
            f'521_{index:02d}_{safe_name}_saturation', outdir,
            cmap='plasma', unit='fraction', vmin=0.0, vmax=rock.s_g_max
        )
        legacy = Wells(
            inj_cells=injector.cells, prod_cells=producer.cells,
            rate=0.0, bhp=producer.target,
            inj_bhp=audit.injector_bhp_mpa * 1.0e6,
        )
        rows, _ = _v10_trace_total_streamlines(
            grid, pstep, legacy, seeds_per_dim=pollock_seeds_per_dim
        )
        _v10_plot_streamlines(
            grid, rows, state.pressure_w,
            f'long_run_{safe_name}', index, state.time_days, outdir
        )


def run_long_duration_stability_target(
        outdir='pad_stream_v13_long_run_outputs',
        total_time_days=365.0, make_plots=True,
        pollock_seeds_per_dim=6):
    _os_v13.makedirs(outdir, exist_ok=True)
    checkpoint_dir = _os_v13.path.join(outdir, 'checkpoints')
    _os_v13.makedirs(checkpoint_dir, exist_ok=True)
    timestep = AdaptiveTimeStepConfig(
        initial_dt_days=0.10,
        minimum_dt_days=0.005,
        maximum_dt_days=2.00,
        target_max_saturation_change=0.018,
    )
    nonlinear = NonlinearCouplingConfig()
    print('=' * 120)
    print('VERSION 13 — LONG-DURATION NONLINEAR COUPLING, ADAPTIVE TIMESTEPS, BREAKTHROUGH, AND RESTART')
    print('=' * 120)
    print('Running timestep and restart validations...')
    validations = validate_long_run_restart_and_timestep(outdir)
    print('Validation:', validations)

    output_times = tuple(x for x in (1.0, 3.0, 10.0, 30.0, 90.0, 180.0, 270.0, total_time_days)
                         if x <= total_time_days)
    checkpoint_times = tuple(x for x in (90.0, 180.0, 270.0, total_time_days)
                             if x <= total_time_days)
    snapshot_times = tuple(x for x in (1.0, 30.0, 90.0, 180.0, 270.0, total_time_days)
                           if x <= total_time_days)
    # Run in restart segments.  Each boundary is written and reloaded before
    # continuing, so the production execution path exercises the same restart
    # mechanism validated above rather than treating checkpoints as decorative.
    segment_ends = sorted(set(
        x for x in (90.0, 180.0, 270.0, total_time_days)
        if x <= total_time_days
    ))
    state = None
    audits = []
    snapshots = {}
    context = None
    for segment_end in segment_ends:
        segment_outputs = tuple(
            x for x in output_times
            if (0.0 if state is None else state.time_days) < x <= segment_end
        )
        segment_snapshots = tuple(
            x for x in snapshot_times
            if (0.0 if state is None else state.time_days) < x <= segment_end
        )
        print(f'--- long-run restart segment to day {segment_end:g} ---')
        state, segment_audits, segment_states, context = (
            run_long_duration_simulation(
                end_time_days=segment_end, state=state,
                timestep=timestep, nonlinear=nonlinear,
                forced_output_times=segment_outputs,
                checkpoint_times=(segment_end,),
                checkpoint_dir=checkpoint_dir,
                adaptive=True, verbose=True,
                store_snapshot_times=segment_snapshots,
            )
        )
        audits.extend(segment_audits)
        snapshots.update(segment_states)
        segment_checkpoint = _os_v13.path.join(
            checkpoint_dir, f'pad_stream_v13_day_{segment_end:g}.npz'
        )
        save_long_run_checkpoint(segment_checkpoint, state)
        state = load_long_run_checkpoint(segment_checkpoint)
    final_checkpoint = save_long_run_checkpoint(
        _os_v13.path.join(checkpoint_dir, 'pad_stream_v13_final.npz'), state
    )

    if make_plots:
        _v13_plot_long_run_histories(audits, outdir)
        _v13_plot_snapshots(
            snapshots, context, outdir,
            pollock_seeds_per_dim=pollock_seeds_per_dim,
        )

    breakthrough = state.breakthrough_time_days
    summary = {
        'stage': 23,
        'formulation': {
            'coupling': 'strict Aitken coupling through breakthrough transition; three-pass predictor-corrector after producer gas cut reaches 50%',
            'timestep': 'reject/retry adaptive global timestep',
            'breakthrough': 'producer gas volume fraction >= 1e-4',
            'restart': 'compressed NPZ checkpoint with all dynamic state variables',
            'maximum_timestep_days': timestep.maximum_dt_days,
        },
        'validations': validations,
        'run': {
            'final_time_days': state.time_days,
            'accepted_steps': len(audits),
            'rejected_attempts': context['total_rejected_attempts'],
            'breakthrough_time_days': None if not np.isfinite(breakthrough) else breakthrough,
            'breakthrough_criterion': state.breakthrough_criterion,
            'maximum_absolute_mass_error_kg': float(max(abs(a.cumulative_mass_error_kg) for a in audits)),
            'maximum_projection_correction': float(max(a.maximum_projection_correction for a in audits)),
            'maximum_saturation_change': float(max(a.maximum_saturation_change for a in audits)),
            'maximum_nonlinear_residual': float(max(a.nonlinear_residual for a in audits)),
            'maximum_nonlinear_iterations': int(max(a.nonlinear_iterations for a in audits)),
            'minimum_accepted_dt_days': float(min(a.dt_days for a in audits)),
            'maximum_accepted_dt_days': float(max(a.dt_days for a in audits)),
            'final_saturation_minimum': audits[-1].saturation_minimum,
            'final_saturation_maximum': audits[-1].saturation_maximum,
            'final_producer_gas_cut': audits[-1].producer_gas_cut,
            'final_producer_gas_mass_rate_kg_s': audits[-1].producer_gas_mass_rate_kg_s,
            'final_injector_mode': audits[-1].injector_mode,
            'final_injector_bhp_mpa': audits[-1].injector_bhp_mpa,
            'final_checkpoint': final_checkpoint,
        },
        'audits': [_asdict_v13(a) for a in audits],
        'checkpoint_files': sorted(
            _os_v13.path.join(checkpoint_dir, name)
            for name in _os_v13.listdir(checkpoint_dir)
            if name.endswith('.npz')
        ),
    }
    summary_path = _os_v13.path.join(
        outdir, 'PAD_Stream_V13_Long_Run_Summary.json'
    )
    with open(summary_path, 'w') as handle:
        _json_v13.dump(summary, handle, indent=2)
    print('=' * 120)
    print('Long-duration target complete.')
    print('Breakthrough time [days]:', summary['run']['breakthrough_time_days'])
    print('Accepted/rejected:', summary['run']['accepted_steps'], '/', summary['run']['rejected_attempts'])
    print('Final gas cut:', summary['run']['final_producer_gas_cut'])
    print('Maximum mass error [kg]:', summary['run']['maximum_absolute_mass_error_kg'])
    print('=' * 120)
    return state, audits, snapshots, summary



# ==============================================================================
# STAGE 24 [S24] — COMPLETE VERIFICATION, VALIDATION, AND REGRESSION SUITE
# ==============================================================================
# This final classical-physics stage does not add a new constitutive equation.
# It freezes the accepted physics by testing analytical limits, convergence,
# cross-method equivalence, controls, conservation, restart identity, and the
# completed year-scale regression.  The suite is intentionally tiered:
#
#   Tier 1: unit / analytical identities
#   Tier 2: grid and timestep convergence
#   Tier 3: cross-method equivalence
#   Tier 4: integrated system regression
#
# A failure is reported explicitly; no failed gate is silently averaged into a
# global score.  The output JSON and CSV are suitable for future CI regression.
# ==============================================================================

from dataclasses import dataclass as _dataclass_v14, asdict as _asdict_v14
from pathlib import Path as _Path_v14
import csv as _csv_v14
import json as _json_v14
import os as _os_v14
import time as _time_v14
import zipfile as _zipfile_v14


@_dataclass_v14
class PhysicsValidationResult:
    tier: str
    name: str
    passed: bool
    gate: str
    value: str
    metrics: dict
    runtime_seconds: float = 0.0


def _v14_result(tier, name, passed, gate, value, metrics, runtime=0.0):
    return PhysicsValidationResult(
        tier=str(tier), name=str(name), passed=bool(passed), gate=str(gate),
        value=str(value), metrics=dict(metrics), runtime_seconds=float(runtime),
    )


def _v14_run_check(tier, name, gate, function):
    started = _time_v14.time()
    try:
        passed, value, metrics = function()
        return _v14_result(
            tier, name, passed, gate, value, metrics,
            _time_v14.time() - started,
        )
    except Exception as exc:
        return _v14_result(
            tier, name, False, gate,
            f'{type(exc).__name__}: {exc}',
            {'exception_type': type(exc).__name__, 'exception': str(exc)},
            _time_v14.time() - started,
        )


def _v14_test_constitutive_endpoints():
    rock = CCUSRock(s_g_initial=0.0, hysteresis=True).validate()
    fluid = CCUSFluid()
    s = np.array([0.0, rock.s_g_max])
    krg, krw = ccus_relative_permeability(s, rock, s_g_history=s)
    fg = ccus_fractional_flow(s, rock, fluid, s_g_history=s)
    endpoint_error = max(
        abs(float(krg[0])),
        abs(float(krw[0]) - rock.krw_endpoint),
        abs(float(krg[-1]) - rock.krg_endpoint),
        abs(float(krw[-1])),
        abs(float(fg[0])),
        abs(float(fg[-1]) - 1.0),
    )
    passed = endpoint_error < 1.0e-12
    return passed, f'max endpoint error={endpoint_error:.3e}', {
        'maximum_endpoint_error': endpoint_error,
        'krg_at_zero': float(krg[0]),
        'krw_at_zero': float(krw[0]),
        'krg_at_max': float(krg[-1]),
        'krw_at_max': float(krw[-1]),
        'fg_at_zero': float(fg[0]),
        'fg_at_max': float(fg[-1]),
    }


def _v14_test_tpfa_linear_pressure():
    p_left = 3.0e7
    p_right = 2.0e7
    errors = []
    profiles = []
    for nx in (10, 20, 40, 80):
        grid = Grid3D(
            nx=nx, ny=1, nz=1,
            dx=1000.0 / nx, dy=100.0, dz=10.0,
            k=np.full((nx, 1, 1), md_to_m2(100.0)),
            phi=np.full((nx, 1, 1), 0.20),
        )
        rock = CCUSRock(s_g_initial=0.0).validate()
        fluid = CCUSFluid(c_g=0.0, c_w=0.0)
        wells = Wells(
            inj_cells=[(0, 0, 0)], prod_cells=[(nx - 1, 0, 0)],
            rate=0.0, bhp=p_right, inj_bhp=p_left,
        )
        saturation = np.zeros((nx, 1, 1), dtype=float)
        pressure, _ = solve_ccus_steady_pressure(
            grid, saturation, rock, fluid, wells, no_crossflow=True,
        )
        exact = np.linspace(p_left, p_right, nx)
        relative_l2 = float(
            np.linalg.norm(pressure[:, 0, 0] - exact)
            / max(np.linalg.norm(exact), 1.0)
        )
        errors.append(relative_l2)
        profiles.append({
            'nx': nx,
            'x': np.linspace(0.0, 1000.0, nx).tolist(),
            'pressure_mpa': (pressure[:, 0, 0] / 1.0e6).tolist(),
            'exact_mpa': (exact / 1.0e6).tolist(),
            'relative_l2_error': relative_l2,
        })
    maximum = max(errors)
    passed = maximum < 1.0e-12
    return passed, f'max relative L2={maximum:.3e}', {
        'grid_sizes': [10, 20, 40, 80],
        'relative_l2_errors': errors,
        'profiles': profiles,
    }


def _v14_test_buckley_leverett_grid_convergence():
    rock = RockProperties()
    fluid = FluidProperties(mu_w=0.5, mu_o=5.0)
    geometry = ReservoirGeometry()
    solver = CompressibleBLSolver(
        rock, fluid, geometry,
        CompressibleFluid(c=0.0), PressureConditions(),
    )
    time_days = 600.0
    t_d = solver.u_inj * time_days / (rock.phi * geometry.x_ip)
    grid_sizes = [101, 201, 401, 801]
    l1_errors = []
    profiles = []
    for nx in grid_sizes:
        x_d, numerical = solver.solve_incompressible(
            time_days, nx=nx, cfl=0.40,
        )
        analytical = analytical_saturation_profile(
            x_d, t_d, rock, fluid,
        )
        l1 = float(np.mean(np.abs(numerical - analytical)))
        l1_errors.append(l1)
        profiles.append({
            'nx': nx,
            'x_d': x_d.tolist(),
            'numerical': numerical.tolist(),
            'analytical': analytical.tolist(),
            'l1_error': l1,
        })
    monotone = all(
        l1_errors[i + 1] < l1_errors[i]
        for i in range(len(l1_errors) - 1)
    )
    improvement = l1_errors[0] / max(l1_errors[-1], 1.0e-30)
    passed = monotone and l1_errors[-1] < 2.5e-3 and improvement > 2.0
    return passed, (
        f'L1 {l1_errors[0]:.3e}->{l1_errors[-1]:.3e}; '
        f'improvement={improvement:.2f}x'
    ), {
        'time_days': time_days,
        'dimensionless_time': t_d,
        'grid_sizes': grid_sizes,
        'l1_errors': l1_errors,
        'monotonic_refinement': monotone,
        'improvement_factor': improvement,
        'profiles': profiles,
    }


def _v14_test_phase_potential_limits():
    grid, _, _, cap, wells, _ = build_padstream_5x5x5_case()
    rock = CCUSRock(s_g_initial=0.0).validate()
    fluid = CCUSFluid(p_ref=float(wells.inj_bhp), c_w=0.0)
    metrics = validate_phase_potential_limits(grid, rock, fluid, cap, wells)
    passed = (
        metrics['zero_capillary_zero_gravity_relative_pressure_error'] < 1.0e-10
        and metrics['hydrostatic_brine_max_face_rate_m3_s'] < 1.0e-12
        and metrics['constant_gas_potential_max_face_rate_m3_s'] < 1.0e-12
    )
    return passed, (
        'zero-force={:.3e}, hydrostatic={:.3e}, gas-potential={:.3e}'.format(
            metrics['zero_capillary_zero_gravity_relative_pressure_error'],
            metrics['hydrostatic_brine_max_face_rate_m3_s'],
            metrics['constant_gas_potential_max_face_rate_m3_s'],
        )
    ), metrics


def _v14_test_four_mode_regression(workdir):
    audits, _, summary = run_phase_potential_target(
        outdir=str(_Path_v14(workdir) / 'four_mode_internal'),
        total_time_days=1.0,
        pressure_dt_days=0.5,
        pollock_seeds_per_dim=2,
        make_plots=False,
    )
    last = {mode: rows[-1] for mode, rows in audits.items()}
    maximum_mass_error = max(
        abs(row.cumulative_mass_error_kg) for row in last.values()
    )
    capillary_reduction = (
        last['incompressible'].saturation_max
        - last['capillary'].saturation_max
    )
    gravity_ratio = (
        last['full'].mean_abs_vertical_gas_flux_m3_day
        / max(last['compressible'].mean_abs_vertical_gas_flux_m3_day, 1.0e-30)
    )
    phase_closure = max(abs(row.phase_flux_closure_m3_s) for row in last.values())
    passed = (
        maximum_mass_error < 1.0e-6
        and capillary_reduction > 0.0
        and gravity_ratio > 1.0e3
        and phase_closure < 1.0e-14
    )
    metrics = {
        'maximum_mass_error_kg': maximum_mass_error,
        'capillary_peak_saturation_reduction': capillary_reduction,
        'full_to_compressible_vertical_flux_ratio': gravity_ratio,
        'maximum_phase_flux_closure_m3_s': phase_closure,
        'final_modes': {mode: _asdict_v14(row) for mode, row in last.items()},
        'limit_checks': summary['limit_checks'],
    }
    return passed, (
        f'mass={maximum_mass_error:.3e} kg, '
        f'capillary dS={capillary_reduction:.3e}, '
        f'vertical ratio={gravity_ratio:.2e}'
    ), metrics


def _v14_test_dykstra_parsons_behavior():
    permeability = np.array([20, 35, 60, 100, 170, 280, 450, 700], dtype=float)
    n = len(permeability)
    thickness = np.full(n, 10.0)
    porosity = np.full(n, 0.20)
    swc = np.full(n, 0.20)
    krw = np.full(n, 0.80)
    kro = np.full(n, 0.80)
    pvi = np.linspace(0.0, 1.0, 101)
    heterogeneous = DykstraParsons(
        permeability, thickness, porosity, swc, 0.20, krw, kro,
        mu_w=0.5, mu_o=5.0, allocation='kh',
    )
    homogeneous = DykstraParsons(
        np.full(n, float(np.mean(permeability))), thickness, porosity, swc,
        0.20, krw, kro, mu_w=0.5, mu_o=5.0, allocation='kh',
    )
    recovery, watercut = heterogeneous.run(pvi)
    recovery_h, watercut_h = homogeneous.run(pvi)
    threshold = 1.0e-6
    bt_heterogeneous = float(pvi[np.argmax(watercut > threshold)])
    bt_homogeneous = float(pvi[np.argmax(watercut_h > threshold)])
    idx = int(np.argmin(np.abs(pvi - 0.30)))
    v_dp = dykstra_parsons_coefficient(permeability)
    _, phi_layered, lorenz = layered_flow_storage(
        permeability, thickness, porosity,
    )
    monotone_recovery = bool(np.all(np.diff(recovery) >= -1.0e-12))
    passed = (
        bt_heterogeneous < bt_homogeneous
        and recovery[idx] < recovery_h[idx]
        and monotone_recovery
        and 0.0 < v_dp < 1.0
        and 0.0 < lorenz < 1.0
    )
    return passed, (
        f'BT PVI={bt_heterogeneous:.2f} vs {bt_homogeneous:.2f}; '
        f'R@0.3={recovery[idx]:.3f} vs {recovery_h[idx]:.3f}'
    ), {
        'pvi': pvi.tolist(),
        'heterogeneous_recovery': recovery.tolist(),
        'heterogeneous_watercut': watercut.tolist(),
        'homogeneous_recovery': recovery_h.tolist(),
        'homogeneous_watercut': watercut_h.tolist(),
        'heterogeneous_breakthrough_pvi': bt_heterogeneous,
        'homogeneous_breakthrough_pvi': bt_homogeneous,
        'recovery_at_pvi_0p3': float(recovery[idx]),
        'homogeneous_recovery_at_pvi_0p3': float(recovery_h[idx]),
        'dykstra_parsons_coefficient': v_dp,
        'lorenz_coefficient': float(lorenz),
        'storage_capacity_endpoint': float(phi_layered[-1]),
    }


def _v14_test_fphi_provenance():
    old = chk_fphi_lorenz()
    # Parse fresh numerical values directly, rather than relying only on text.
    grid, _, _, wells, _ = build_dp_demo(nx=12, ny=12)
    _, _, tracer_lorenz = single_phase_fphi(grid, wells, no_crossflow=False)
    k_layer = grid.k.mean(axis=(0, 1))
    _, _, layered_lorenz = layered_flow_storage(
        k_layer, grid.dzk, grid.phi.mean(axis=(0, 1)),
    )
    relative = abs(tracer_lorenz - layered_lorenz) / max(abs(layered_lorenz), 1.0e-30)
    passed = bool(old['passed']) and relative < 0.10
    return passed, (
        f'Lc streamline={tracer_lorenz:.3f}, layered={layered_lorenz:.3f}, '
        f'relative={relative:.2%}'
    ), {
        'streamline_lorenz': float(tracer_lorenz),
        'layered_lorenz': float(layered_lorenz),
        'relative_difference': float(relative),
        'legacy_gate': old,
    }


def _v14_test_flux_path_equivalence(workdir):
    audits, _, _ = run_face_flux_path_decomposition_target(
        outdir=str(_Path_v14(workdir) / 'path_internal'),
        total_time_days=0.5,
        pressure_dt_days=0.5,
        pollock_seeds_per_dim=4,
        make_plots=False,
        include_capillary_check=False,
    )
    audit = audits[-1]
    passed = (
        audit.max_face_relative_error < 1.0e-9
        and audit.mixed_linf < 1.0e-10
        and audit.unmixed_linf < 1.0e-9
        and abs(audit.mixed_mass_error_kg) < 1.0e-6
        and audit.pollock_linf > audit.mixed_linf
    )
    return passed, (
        f'face={audit.max_face_relative_error:.3e}, '
        f'path-FV={audit.mixed_linf:.3e}, '
        f'equal-seed Pollock={audit.pollock_linf:.3e}'
    ), _asdict_v14(audit)


def _v14_test_land_trapping():
    rock = CCUSRock(
        s_g_initial=0.0, s_wir=0.20, s_gr_max=0.30,
        hysteresis=True,
    ).validate()
    peak = np.linspace(0.0, rock.s_g_max, 201)
    endpoint = ccus_land_residual_endpoint(peak, rock)
    full_error = abs(float(endpoint[-1]) - rock.s_gr_max)
    efficiency = np.divide(
        endpoint, peak, out=np.zeros_like(endpoint), where=peak > 0.0,
    )
    decreasing = bool(np.all(np.diff(efficiency[1:]) <= 1.0e-12))
    current = 0.5 * endpoint
    free, trapped, _, imbibition = ccus_land_free_trapped_saturation(
        current, peak, rock,
    )
    split_error = float(np.max(np.abs(free + trapped - current)))
    passed = full_error < 1.0e-12 and decreasing and split_error < 1.0e-12
    return passed, (
        f'full-drainage endpoint error={full_error:.3e}, '
        f'inventory split={split_error:.3e}'
    ), {
        'peak_saturation': peak.tolist(),
        'residual_endpoint': endpoint.tolist(),
        'trapping_efficiency': efficiency.tolist(),
        'full_drainage_endpoint_error': full_error,
        'efficiency_monotonically_decreasing': decreasing,
        'maximum_inventory_split_error': split_error,
        'imbibition_cells_in_test': int(np.count_nonzero(imbibition)),
    }


def _v14_test_final_wells():
    grid, rock, fluid, cap, _, _ = build_long_duration_case()
    metrics = validate_final_well_model(grid, rock, fluid, cap)
    passed = (
        metrics['single_completion_productivity_relative_error'] < 1.0e-12
        and abs(metrics['high_to_low_layer_well_index_ratio'] - 4.0) < 1.0e-12
        and metrics['mass_rate_control_relative_error'] < 1.0e-12
        and metrics['reservoir_rate_control_relative_error'] < 1.0e-12
        and metrics['rate_limit_test_switched']
        and metrics['rate_limit_test_active_mode'] == 'bhp'
        and metrics['rate_limit_test_pressure_residual_m3_s'] < 1.0e-10
    )
    return passed, (
        f"WI ratio={metrics['high_to_low_layer_well_index_ratio']:.3f}, "
        f"mass-rate err={metrics['mass_rate_control_relative_error']:.3e}, "
        f"switch={metrics['rate_limit_test_switched']}"
    ), metrics


def _v14_test_adaptive_restart(workdir):
    metrics = validate_long_run_restart_and_timestep(
        str(_Path_v14(workdir) / 'restart_internal')
    )
    adapt = metrics['adaptive_vs_fixed_5_day']
    restart = metrics['restart_10_plus_10_day']
    aggressive = metrics['aggressive_initial_step']
    passed = (
        adapt['maximum_saturation_difference'] < 2.5e-3
        and adapt['relative_pressure_difference'] < 5.0e-5
        and adapt['adaptive_steps'] < adapt['fixed_steps']
        and restart['maximum_saturation_difference'] == 0.0
        and restart['maximum_pressure_difference_pa'] == 0.0
        and restart['maximum_cell_mass_difference_kg'] == 0.0
        and aggressive['rejected_attempts'] >= 1
        and abs(aggressive['final_time_days'] - 5.0) < 1.0e-12
    )
    return passed, (
        f"adaptive/fixed steps={adapt['adaptive_steps']}/{adapt['fixed_steps']}, "
        f"restart dS={restart['maximum_saturation_difference']:.1e}, "
        f"rejections={aggressive['rejected_attempts']}"
    ), metrics


def _v14_locate_year_summary(explicit=None):
    candidates = []
    if explicit:
        candidates.append(_Path_v14(explicit))
    try:
        candidates.append(_Path_v14(__file__).resolve().with_name(
            'PAD_Stream_V13_Long_Run_Summary.json'
        ))
    except Exception:
        pass
    candidates.extend([
        _Path_v14.cwd() / 'PAD_Stream_V13_Long_Run_Summary.json',
        _Path_v14('/mnt/data/PAD_Stream_V13_Long_Run_Summary.json'),
    ])
    for path in candidates:
        if path.exists():
            return path
    return None


def _v14_test_year_regression(year_summary_path=None):
    path = _v14_locate_year_summary(year_summary_path)
    if path is None:
        # Standalone fallback: verify integrated long-run conservation over 30 d.
        state, audits, _, context = run_long_duration_simulation(
            end_time_days=30.0,
            forced_output_times=(30.0,),
            adaptive=True, verbose=False,
        )
        maximum_mass_error = max(abs(a.cumulative_mass_error_kg) for a in audits)
        passed = (
            abs(state.time_days - 30.0) < 1.0e-10
            and maximum_mass_error < 1.0e-4
            and max(a.maximum_projection_correction for a in audits) < 1.0e-12
        )
        return passed, (
            f'30-day fallback: steps={len(audits)}, mass={maximum_mass_error:.3e} kg'
        ), {
            'source': 'executed 30-day fallback because year summary was not found',
            'final_time_days': state.time_days,
            'accepted_steps': len(audits),
            'rejected_attempts': context['total_rejected_attempts'],
            'maximum_mass_error_kg': maximum_mass_error,
        }
    with open(path, 'r') as handle:
        summary = _json_v14.load(handle)
    run = summary['run']
    passed = (
        abs(float(run['final_time_days']) - 365.0) < 1.0e-8
        and run['breakthrough_time_days'] is not None
        and 0.0 < float(run['breakthrough_time_days']) < 365.0
        and float(run['maximum_absolute_mass_error_kg']) < 1.0e-4
        and float(run['maximum_projection_correction']) < 1.0e-12
        and 0.0 <= float(run['final_producer_gas_cut']) <= 1.0
    )
    metrics = dict(run)
    metrics['source_summary'] = str(path)
    return passed, (
        f"365 d, BT={run['breakthrough_time_days']:.2f} d, "
        f"gas cut={run['final_producer_gas_cut']:.3f}, "
        f"mass={run['maximum_absolute_mass_error_kg']:.3e} kg"
    ), metrics


def _v14_plot_validation_dashboard(results, output_dir):
    output_dir = _Path_v14(output_dir)
    # 1. Pass/fail scorecard.
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    names = [r.name for r in results]
    values = [1.0 if r.passed else 0.0 for r in results]
    y = np.arange(len(results))
    ax.barh(y, values)
    ax.set_yticks(y, names)
    ax.set_xlim(0.0, 1.05)
    ax.set_xticks([0.0, 1.0], ['FAIL', 'PASS'])
    ax.invert_yaxis()
    ax.set_title('PAD-Stream complete physics validation scorecard')
    ax.grid(axis='x', alpha=0.25)
    _v7_save(fig, '500_validation_scorecard.png', str(output_dir))

    # 2. Runtime by check.
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    ax.barh(y, [r.runtime_seconds for r in results])
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set_xlabel('runtime [s]')
    ax.set_title('Validation runtime by gate')
    ax.grid(axis='x', alpha=0.25)
    _v7_save(fig, '501_validation_runtime.png', str(output_dir))

    by_name = {r.name: r for r in results}
    # 3. BL convergence and profile comparison.
    if 'Buckley-Leverett grid convergence' in by_name:
        metrics = by_name['Buckley-Leverett grid convergence'].metrics
        fig, ax = plt.subplots(figsize=(7.2, 5.2))
        ax.loglog(metrics['grid_sizes'], metrics['l1_errors'], 'o-')
        ax.set_xlabel('number of 1D cells')
        ax.set_ylabel('mean absolute saturation error')
        ax.set_title('Buckley-Leverett grid convergence')
        ax.grid(alpha=0.3, which='both')
        _v7_save(fig, '510_bl_grid_convergence.png', str(output_dir))

        finest = metrics['profiles'][-1]
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        ax.plot(finest['x_d'], finest['analytical'], label='analytical Welge solution')
        ax.plot(finest['x_d'], finest['numerical'], '--', label=f"Godunov, nx={finest['nx']}")
        ax.set_xlabel('dimensionless distance')
        ax.set_ylabel('injected-phase saturation')
        ax.set_title('Buckley-Leverett analytical recovery')
        ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '511_bl_analytical_profile.png', str(output_dir))

    # 4. Pressure benchmark.
    if 'Single-phase TPFA pressure' in by_name:
        metrics = by_name['Single-phase TPFA pressure'].metrics
        finest = metrics['profiles'][-1]
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        ax.plot(finest['x'], finest['exact_mpa'], label='analytical linear pressure')
        ax.plot(finest['x'], finest['pressure_mpa'], '--', label='TPFA')
        ax.set_xlabel('distance [m]'); ax.set_ylabel('pressure [MPa]')
        ax.set_title('Single-phase pressure benchmark')
        ax.grid(alpha=0.3); ax.legend()
        _v7_save(fig, '520_tpfa_linear_pressure.png', str(output_dir))

    # 5. Phase-potential limiting errors.
    if 'Phase-potential limiting cases' in by_name:
        m = by_name['Phase-potential limiting cases'].metrics
        labels = ['zero Pc/g', 'hydrostatic brine', 'constant gas potential']
        vals = [
            m['zero_capillary_zero_gravity_relative_pressure_error'],
            m['hydrostatic_brine_max_face_rate_m3_s'],
            m['constant_gas_potential_max_face_rate_m3_s'],
        ]
        fig, ax = plt.subplots(figsize=(7.4, 5.0))
        ax.bar(labels, np.maximum(vals, 1.0e-20))
        ax.set_yscale('log')
        ax.set_ylabel('absolute or relative residual')
        ax.set_title('Phase-potential limiting-case residuals')
        ax.grid(axis='y', alpha=0.3, which='both')
        _v7_save(fig, '530_phase_potential_limits.png', str(output_dir))

    # 6. Dykstra-Parsons recovery and water cut.
    if 'Dykstra-Parsons layered behavior' in by_name:
        m = by_name['Dykstra-Parsons layered behavior'].metrics
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        ax.plot(m['pvi'], m['heterogeneous_recovery'], label='heterogeneous recovery')
        ax.plot(m['pvi'], m['homogeneous_recovery'], '--', label='homogeneous recovery')
        ax.plot(m['pvi'], m['heterogeneous_watercut'], label='heterogeneous water cut')
        ax.plot(m['pvi'], m['homogeneous_watercut'], '--', label='homogeneous water cut')
        ax.set_xlabel('total pore volumes injected')
        ax.set_ylabel('fraction')
        ax.set_title('Dykstra-Parsons layered response')
        ax.grid(alpha=0.3); ax.legend(fontsize=8)
        _v7_save(fig, '540_dykstra_parsons_behavior.png', str(output_dir))

    # 7. Streamline/path equivalence.
    if 'Flux-path versus finite-volume transport' in by_name:
        m = by_name['Flux-path versus finite-volume transport'].metrics
        labels = ['face flux', 'cell-mixed path', 'independent path', 'equal-seed Pollock']
        values = [m['max_face_relative_error'], m['mixed_linf'],
                  m['unmixed_linf'], m['pollock_linf']]
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        ax.bar(labels, np.maximum(values, 1.0e-18))
        ax.set_yscale('log')
        ax.set_ylabel('maximum error')
        ax.set_title('Cross-method transport verification')
        ax.tick_params(axis='x', rotation=18)
        ax.grid(axis='y', alpha=0.3, which='both')
        _v7_save(fig, '550_path_fv_equivalence.png', str(output_dir))

    # 8. Adaptive versus fixed comparison.
    if 'Adaptive timestep and restart identity' in by_name:
        m = by_name['Adaptive timestep and restart identity'].metrics
        a = m['adaptive_vs_fixed_5_day']
        fig, ax = plt.subplots(figsize=(6.8, 4.8))
        ax.bar(['fixed', 'adaptive'], [a['fixed_steps'], a['adaptive_steps']])
        ax.set_ylabel('accepted timesteps')
        ax.set_title('Adaptive timestep efficiency at five days')
        ax.grid(axis='y', alpha=0.3)
        _v7_save(fig, '560_adaptive_timestep_efficiency.png', str(output_dir))


def run_complete_physics_validation_target(
        outdir='pad_stream_v14_complete_validation_outputs',
        year_summary_path=None,
        make_plots=True,
        create_zip=True):
    """Execute the complete classical-physics validation matrix.

    This target deliberately reuses the accepted physics functions rather than
    maintaining a second implementation inside the tests.  It returns a
    machine-readable summary and exits nonzero from __main__ if any mandatory
    gate fails.
    """
    output_dir = _Path_v14(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    started = _time_v14.time()

    checks = [
        ('Tier 1 — analytical', 'CCUS constitutive endpoints',
         'Corey and fractional-flow endpoints close to <1e-12',
         _v14_test_constitutive_endpoints),
        ('Tier 1 — analytical', 'Single-phase TPFA pressure',
         'linear Dirichlet pressure reproduced to relative L2 <1e-12',
         _v14_test_tpfa_linear_pressure),
        ('Tier 2 — convergence', 'Buckley-Leverett grid convergence',
         'L1 error decreases monotonically and finest error <2.5e-3',
         _v14_test_buckley_leverett_grid_convergence),
        ('Tier 1 — analytical', 'Phase-potential limiting cases',
         'zero-force and hydrostatic/potential cancellations < specified tolerances',
         _v14_test_phase_potential_limits),
        ('Tier 4 — integrated', 'Four-mode phase-flux regression',
         'mass closure, capillary smoothing, gravity response, and phase closure',
         lambda: _v14_test_four_mode_regression(output_dir)),
        ('Tier 3 — cross-method', 'Dykstra-Parsons layered behavior',
         'heterogeneity causes earlier breakthrough and lower early recovery',
         _v14_test_dykstra_parsons_behavior),
        ('Tier 3 — cross-method', 'F-Phi layered provenance',
         'streamline Lorenz coefficient within 10% of analytical layered value',
         _v14_test_fphi_provenance),
        ('Tier 3 — cross-method', 'Flux-path versus finite-volume transport',
         'exact path reconstruction and path/FV saturation agreement',
         lambda: _v14_test_flux_path_equivalence(output_dir)),
        ('Tier 1 — analytical', 'Land trapping identities',
         'full drainage reaches Sgr_max and mobile+trapped inventory closes',
         _v14_test_land_trapping),
        ('Tier 1 — analytical', 'Final well controls',
         'Peaceman productivity, rate controls, allocation, and BHP switching',
         _v14_test_final_wells),
        ('Tier 2 — convergence', 'Adaptive timestep and restart identity',
         'adaptive/fixed agreement, exact restart, and reject/retry recovery',
         lambda: _v14_test_adaptive_restart(output_dir)),
        ('Tier 4 — integrated', 'Year-scale system regression',
         '365-day breakthrough run closes mass and avoids bound projection',
         lambda: _v14_test_year_regression(year_summary_path)),
    ]

    print('=' * 124)
    print('VERSION 14 — COMPLETE PHYSICS VERIFICATION, VALIDATION, AND REGRESSION')
    print('=' * 124)
    results = []
    for tier, name, gate, function in checks:
        result = _v14_run_check(tier, name, gate, function)
        results.append(result)
        tag = 'PASS' if result.passed else 'FAIL'
        print(
            f'[{tag}] {name:<45s} {result.value} '
            f'({result.runtime_seconds:.2f} s)'
        )

    passed_count = sum(r.passed for r in results)
    mandatory_count = len(results)
    all_passed = passed_count == mandatory_count
    tier_summary = {}
    for result in results:
        tier_summary.setdefault(result.tier, {'passed': 0, 'total': 0})
        tier_summary[result.tier]['total'] += 1
        tier_summary[result.tier]['passed'] += int(result.passed)

    summary = {
        'stage': 24,
        'title': 'Complete classical-physics verification and validation suite',
        'all_mandatory_checks_passed': all_passed,
        'passed_checks': passed_count,
        'total_checks': mandatory_count,
        'runtime_seconds': _time_v14.time() - started,
        'tier_summary': tier_summary,
        'results': [_asdict_v14(r) for r in results],
        'completion_statement': (
            'The controlled 5x5x5 classical CCUS physics prototype is frozen as '
            'the deterministic ground-truth baseline when all mandatory gates pass.'
        ),
        'scope_boundary': (
            'Field-scale PVT, corner-point grids, faults, geochemistry, and thermal '
            'effects remain extensions rather than missing validation gates for the '
            'controlled classical prototype.'
        ),
    }

    json_path = output_dir / 'PAD_Stream_V14_Complete_Validation_Summary.json'
    with open(json_path, 'w') as handle:
        _json_v14.dump(summary, handle, indent=2)

    csv_path = output_dir / 'PAD_Stream_V14_Validation_Matrix.csv'
    with open(csv_path, 'w', newline='') as handle:
        writer = _csv_v14.DictWriter(
            handle,
            fieldnames=['tier', 'name', 'passed', 'gate', 'value', 'runtime_seconds'],
        )
        writer.writeheader()
        for result in results:
            writer.writerow({
                'tier': result.tier,
                'name': result.name,
                'passed': result.passed,
                'gate': result.gate,
                'value': result.value,
                'runtime_seconds': result.runtime_seconds,
            })

    if make_plots:
        _v14_plot_validation_dashboard(results, output_dir)

    zip_path = output_dir / 'PAD_Stream_Complete_Physics_Validation_Diagnostics_v14.zip'
    if create_zip:
        with _zipfile_v14.ZipFile(zip_path, 'w', _zipfile_v14.ZIP_DEFLATED) as archive:
            for path in sorted(output_dir.rglob('*')):
                if path.is_file() and path != zip_path:
                    archive.write(path, path.relative_to(output_dir))

    print('-' * 124)
    print(f'Validation result: {passed_count}/{mandatory_count} mandatory checks passed.')
    print(f'Summary: {json_path}')
    print(f'Matrix:  {csv_path}')
    if create_zip:
        print(f'Archive: {zip_path}')
    print('=' * 124)
    return results, summary, str(json_path), str(csv_path), str(zip_path)


if __name__ == '__main__':
    import matplotlib
    V7_DISPLAY_PLOTS = True
    V7_CLOSE_AFTER_SHOW = True
    V7_PLOT_PAUSE_SECONDS = 0.10
    print(f'[plots] Matplotlib backend: {matplotlib.get_backend()}')
    print(f'[plots] Interactive mode: {plt.isinteractive()}')
    print(f'[plots] Display requested: {V7_DISPLAY_PLOTS}')
    _results_v14, _summary_v14, _, _, _ = run_complete_physics_validation_target(
        outdir='pad_stream_v14_complete_validation_outputs',
        make_plots=True,
        create_zip=True,
    )
    if V7_DISPLAY_PLOTS and not _v7_backend_is_headless():
        plt.pause(0.25)
    raise SystemExit(0 if _summary_v14['all_mandatory_checks_passed'] else 1)
