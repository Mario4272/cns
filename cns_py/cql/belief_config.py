"""
Configuration for Belief Revision Logic (Slice 12.1).
"""

from dataclasses import dataclass


@dataclass
class BeliefConfig:
    # Time Decay
    decay_enabled: bool = True
    decay_halflife_days: float = 365.0  # 1 year halflife by default

    # Contradiction Logic
    contradiction_penalty: float = 0.5  # Multiplier penalty if contradiction exists

    # Provenance
    base_provenance_weight: float = 0.1  # Weight per citation
    max_provenance_weight: float = 0.9  # Max cap contribution from provenance

    # Defaults
    default_confidence: float = 1.0  # Starting confidence before modifiers
