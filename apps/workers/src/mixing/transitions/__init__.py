"""
Transition techniques module for professional DJ mixing.

Contains all transition types:
- Blend / Crossfade: Standard house/techno technique
- Bass Swap: CRITICAL - never two basses > 2 beats
- Hard Cut: Instant transitions
- Filter Sweep: Creative filter-based transitions
- Echo Out: Delay/reverb tail exits
- Loop Mixing: Extend sections for longer mixes
- Double Drop: Advanced simultaneous drops
- Acapella: Vocal over instrumental mashups
"""

from .bass_swap import (
    execute_bass_swap,
    calculate_bass_swap_time,
    validate_bass_swap,
)

from .blend import (
    create_blend_transition,
    create_stem_blend,
    apply_stem_automation,
)

from .cut import (
    create_cut_transition,
    create_cut_with_effect,
)

from .filter_transition import (
    create_filter_transition,
    create_hpf_exit,
    create_lpf_entry,
)

from .echo_out import (
    create_echo_out_transition,
    create_reverb_out_transition,
    create_delay_out_transition,
)

from .loop_mixing import (
    create_loop,
    extend_section,
    create_seamless_loop,
)

from .double_drop import (
    create_double_drop,
    validate_double_drop_compatibility,
)

from .acapella import (
    create_acapella_mix,
    prepare_vocal_for_mix,
)

def create_transition(
    audio_a,
    audio_b,
    transition_type: str = "BLEND",
    **kwargs
):
    """
    Create a transition between two audio segments.

    This is the main dispatcher that routes to the appropriate
    transition function based on type.

    Args:
        audio_a: Outgoing audio
        audio_b: Incoming audio
        transition_type: Type of transition (BLEND, CUT, FILTER, ECHO_OUT)
        **kwargs: Additional parameters for the specific transition type

    Returns:
        Transition audio
    """
    transition_type = transition_type.upper()

    if transition_type in ("BLEND", "CROSSFADE", "STEM_BLEND"):
        return create_blend_transition(audio_a, audio_b, **kwargs)
    elif transition_type in ("CUT", "HARD_CUT"):
        return create_cut_transition(audio_a, audio_b, **kwargs)
    elif transition_type in ("FILTER", "FILTER_SWEEP"):
        return create_filter_transition(audio_a, audio_b, **kwargs)
    elif transition_type in ("ECHO", "ECHO_OUT"):
        return create_echo_out_transition(audio_a, audio_b, **kwargs)
    else:
        # Default to blend
        return create_blend_transition(audio_a, audio_b, **kwargs)


__all__ = [
    # Main dispatcher
    "create_transition",
    # Bass Swap
    "execute_bass_swap",
    "calculate_bass_swap_time",
    "validate_bass_swap",
    # Blend
    "create_blend_transition",
    "create_stem_blend",
    "apply_stem_automation",
    # Cut
    "create_cut_transition",
    "create_cut_with_effect",
    # Filter
    "create_filter_transition",
    "create_hpf_exit",
    "create_lpf_entry",
    # Echo Out
    "create_echo_out_transition",
    "create_reverb_out_transition",
    "create_delay_out_transition",
    # Loop
    "create_loop",
    "extend_section",
    "create_seamless_loop",
    # Double Drop
    "create_double_drop",
    "validate_double_drop_compatibility",
    # Acapella
    "create_acapella_mix",
    "prepare_vocal_for_mix",
]
