"""
Energy management module for DJ sets.

Contains:
- Set phase management (warmup, build, peak, cooldown)
- Serpentine flow for energy progression
- Teasing techniques for tension building
"""

from .set_manager import (
    SetPhase,
    determine_set_phase,
    get_transition_recommendations,
    calculate_energy_trajectory,
)

from .serpentine import (
    apply_serpentine_flow,
    suggest_energy_ordering,
    create_tease,
    validate_energy_flow,
)

__all__ = [
    # Set Manager
    "SetPhase",
    "determine_set_phase",
    "get_transition_recommendations",
    "calculate_energy_trajectory",
    # Serpentine
    "apply_serpentine_flow",
    "suggest_energy_ordering",
    "create_tease",
    "validate_energy_flow",
]
