"""PAD-Stream reactive transport (padstream_rt).

A package (not a load-by-path milestone script) that adds multi-component
aqueous transport, a priori Damkohler routing, ML chemistry with a
mass-balance fallback, and porosity/permeability feedback to the PAD-Stream
3D streamline simulator.  See docs/REACTIVE_TRANSPORT_DESIGN.md.
"""

from .state import GridGeometry, Mineral, ChemicalSystem, ReactiveState
from .transfer import StreamlineBundle, TransferOperator, advect_along_streamlines
from .damkohler import Regime, RoutingConfig, damkohler, route
from .kinetics import rate_constant, saturation_ratio, mineral_rate
from .chemistry import ChemInput, ReferenceBackend, SurrogateBackend
from .petrophysics import (LearnedPermeability, kozeny_carman, verma_pruess,
                           update_permeability, transmissibilities_field_units)
from .coupling import reactive_step, StepReport
from .pvt import Fluid, flash, load_sun2020_fwu
from .partition import HydrocarbonState, equilibrate_co2
from .mineralogy import unit_mineralogy, load_freiburg_table1, load_freiburg_table3, c_eq_scales

try:  # optional: needs `pip install phreeqc`
    from .phreeqc_backend import PhreeqcBackend
except ImportError:  # pragma: no cover
    PhreeqcBackend = None

__version__ = "0.3.2"
