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

__version__ = "0.1.0"
