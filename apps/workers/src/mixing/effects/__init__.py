"""
Audio effects module for DJ transitions.

Contains:
- Delay (echo) effects with BPM sync
- Reverb for space and atmosphere
- Filters (HPF/LPF) with sweep automation
- Advanced effects (flanger, phaser, beat repeat, etc.)
"""

from .delay import apply_delay, apply_delay_bpm_sync, create_delay_tail
from .reverb import apply_reverb, apply_convolution_reverb, create_reverb_tail
from .filters import (
    apply_filter,
    apply_hpf,
    apply_lpf,
    create_filter_sweep,
    apply_bandpass,
)
from .advanced import (
    apply_flanger,
    apply_phaser,
    apply_beat_repeat,
    apply_gater,
    apply_bitcrusher,
    apply_spiral,
)

__all__ = [
    # Delay
    "apply_delay",
    "apply_delay_bpm_sync",
    "create_delay_tail",
    # Reverb
    "apply_reverb",
    "apply_convolution_reverb",
    "create_reverb_tail",
    # Filters
    "apply_filter",
    "apply_hpf",
    "apply_lpf",
    "create_filter_sweep",
    "apply_bandpass",
    # Advanced
    "apply_flanger",
    "apply_phaser",
    "apply_beat_repeat",
    "apply_gater",
    "apply_bitcrusher",
    "apply_spiral",
]
