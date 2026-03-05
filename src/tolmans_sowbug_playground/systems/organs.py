"""Organ-based state encoder for biologically-plausible DQN input.

Each organ produces a normalized sub-vector; the full state tensor is their
concatenation.  This replaces the legacy hand-crafted _encode_state().

Organs and their feature dimensions (default config, sight_k=3):

  Sight (45)        — LOS-gated top-k intensity/direction per stimulus family
  Smell  (9)        — non-LOS weighted gradient per consumable family
  Touch (10)        — adjacent obstacle flags + at-cell consumable presence/intensity
  Proprioception (18) — drives, satiety, orientation, displacement, action validity
  Rhythm  (5)       — cyclical tick phase + inter-consumption intervals

Total default: 87 dims.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch

from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import StimulusType
from tolmans_sowbug_playground.systems.drives import DriveSystem, DriveType
from tolmans_sowbug_playground.systems.motor import Direction
from tolmans_sowbug_playground.systems.sensors import Perception

SIGHT_FAMILIES = [
    StimulusType.FOOD,
    StimulusType.WATER,
    StimulusType.LIGHT,
    StimulusType.HEAT,
    StimulusType.OBSTACLE,
]

SMELL_FAMILIES = [
    StimulusType.FOOD,
    StimulusType.WATER,
    StimulusType.HEAT,
]

CARDINAL_DIRS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
ALL_DIRS = [
    Direction.NORTH,
    Direction.SOUTH,
    Direction.EAST,
    Direction.WEST,
    Direction.STAY,
]
DRIVE_TYPES = [DriveType.HUNGER, DriveType.THIRST, DriveType.TEMPERATURE]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp11(value: float) -> float:
    return max(-1.0, min(1.0, value))


@dataclass
class OrganConfig:
    """Hyperparameters governing organ channel shapes and ranges."""

    sight_k: int = 3
    sight_radius: float = 5.0
    sight_fov_degrees: float = 180.0
    smell_radius: float = 7.5
    touch_radius: int = 1
    rhythm_period: float = 100.0
    # Backward-compatibility knobs; if set, they override modern fields.
    smell_radius_scale: float | None = None
    touch_range: int | None = None

    def __post_init__(self) -> None:
        if self.smell_radius_scale is not None:
            self.smell_radius = max(0.0, self.sight_radius * self.smell_radius_scale)
        if self.touch_range is not None:
            self.touch_radius = self.touch_range


@dataclass
class OrgansObservation:
    """Named channels for each organ's output tensor."""

    sight: torch.Tensor
    smell: torch.Tensor
    touch: torch.Tensor
    proprioception: torch.Tensor
    rhythm: torch.Tensor

    def to_tensor(self) -> torch.Tensor:
        return torch.cat(
            [self.sight, self.smell, self.touch, self.proprioception, self.rhythm]
        )

    def to_dict(self) -> dict[str, float]:
        """Per-organ mean absolute activation for recorder/UI diagnostics."""
        return {
            "sight_mag": round(float(self.sight.abs().mean()), 4),
            "smell_mag": round(float(self.smell.abs().mean()), 4),
            "touch_mag": round(float(self.touch.abs().mean()), 4),
            "proprio_mag": round(float(self.proprioception.abs().mean()), 4),
            "rhythm_mag": round(float(self.rhythm.abs().mean()), 4),
        }


def compute_organ_state_dim(config: OrganConfig) -> int:
    """Total dimensionality of the organs-only state vector."""
    sight_dim = len(SIGHT_FAMILIES) * config.sight_k * 3
    smell_dim = len(SMELL_FAMILIES) * 3
    touch_dim = len(CARDINAL_DIRS) + len(SMELL_FAMILIES) * 2
    proprio_dim = len(DRIVE_TYPES) * 2 + len(ALL_DIRS) + 2 + len(ALL_DIRS)
    rhythm_dim = 2 + len(DRIVE_TYPES)
    return sight_dim + smell_dim + touch_dim + proprio_dim + rhythm_dim


# ── Individual organ encoders ──────────────────────────────────────────


def _encode_sight(
    perceptions: list[Perception],
    orientation: Direction,
    config: OrganConfig,
) -> torch.Tensor:
    """Top-k intensity/direction vectors per stimulus family (LOS-gated)."""
    features: list[float] = []
    radius = max(config.sight_radius, 1.0)
    fov = max(1.0, min(360.0, float(config.sight_fov_degrees)))
    half_fov_rad = math.radians(fov / 2.0)
    cos_threshold = math.cos(half_fov_rad)

    def in_view(direction: tuple[int, int]) -> bool:
        # If orientation is STAY, keep vision omnidirectional.
        fx, fy = orientation.value
        if fx == 0 and fy == 0:
            return True
        dx, dy = float(direction[0]), float(direction[1])
        dist = math.hypot(dx, dy)
        if dist <= 1e-9:
            return True
        dot = dx * float(fx) + dy * float(fy)
        cos_angle = dot / dist
        return cos_angle >= cos_threshold

    for family in SIGHT_FAMILIES:
        typed = [
            p
            for p in perceptions
            if p.stimulus.stimulus_type == family and in_view(p.direction)
        ]
        typed.sort(key=lambda p: p.perceived_intensity, reverse=True)
        for i in range(config.sight_k):
            if i < len(typed):
                p = typed[i]
                intensity = float(p.perceived_intensity)
                if family == StimulusType.OBSTACLE and intensity <= 0.0:
                    # Obstacles are often configured with radius=0 (point blockers),
                    # which would otherwise zero out perceived_intensity and flatten
                    # obstacle salience in sight. Use distance-based proximity instead.
                    intensity = max(0.0, 1.0 - float(p.distance) / radius)
                features.append(_clamp01(intensity))
                features.append(_clamp11(float(p.direction[0]) / radius))
                features.append(_clamp11(float(p.direction[1]) / radius))
            else:
                features.extend([0.0, 0.0, 0.0])

    return torch.tensor(features, dtype=torch.float32)


def _encode_smell(
    position: tuple[int, int],
    environment: Environment,
    config: OrganConfig,
) -> torch.Tensor:
    """Non-LOS gradient vectors for consumable families via radius-weighted
    field accumulation.  Uses a dedicated smell_radius (wider, weaker than
    sight) with linear falloff independent of the stimulus's own radius."""
    smell_radius = float(config.smell_radius)
    if smell_radius <= 0:
        return torch.zeros(len(SMELL_FAMILIES) * 3, dtype=torch.float32)
    features: list[float] = []

    all_in_range = environment.get_stimuli_in_radius(position, smell_radius)

    for family in SMELL_FAMILIES:
        agg_dx = 0.0
        agg_dy = 0.0
        total_strength = 0.0
        for stimulus, dist in all_in_range:
            if stimulus.stimulus_type != family:
                continue
            if dist < 1e-6:
                intensity = float(stimulus.intensity)
            else:
                intensity = float(stimulus.intensity) * max(
                    0.0, 1.0 - dist / smell_radius
                )

            if intensity > 0:
                dx = stimulus.position[0] - position[0]
                dy = stimulus.position[1] - position[1]
                agg_dx += dx * intensity
                agg_dy += dy * intensity
                total_strength += intensity

        if total_strength > 0:
            mean_dx = agg_dx / total_strength
            mean_dy = agg_dy / total_strength
            features.append(_clamp01(total_strength))
            features.append(_clamp11(mean_dx / max(smell_radius, 1.0)))
            features.append(_clamp11(mean_dy / max(smell_radius, 1.0)))
        else:
            features.extend([0.0, 0.0, 0.0])

    return torch.tensor(features, dtype=torch.float32)


def _encode_touch(
    position: tuple[int, int],
    environment: Environment,
    config: OrganConfig,
) -> torch.Tensor:
    """Near-contact map with tunable touch range.

    Features:
      - 4 directional blockage flags (any obstacle/boundary within touch_radius)
      - 3x local consumable presence/proximity pairs inside touch_radius
    """
    features: list[float] = []
    touch_radius = max(1, int(config.touch_radius))

    for d in CARDINAL_DIRS:
        dx, dy = d.value
        blocked = False
        for step in range(1, touch_radius + 1):
            adj = (position[0] + dx * step, position[1] + dy * step)
            if (not environment.is_within_bounds(adj)) or (
                not environment.is_passable(adj)
            ):
                blocked = True
                break
        features.append(1.0 if blocked else 0.0)

    nearby = environment.get_stimuli_in_radius(position, touch_radius)
    for family in SMELL_FAMILIES:
        best_signal = 0.0
        for stimulus, dist in nearby:
            if stimulus.stimulus_type != family:
                continue
            # Touch is a short-range proximity channel; encode strongest local
            # signal so nearby heat/consumables can be felt before contact.
            if dist < 1e-6:
                signal = float(stimulus.intensity)
            else:
                signal = float(stimulus.intensity) * max(
                    0.0, 1.0 - dist / max(touch_radius, 1.0)
                )
            best_signal = max(best_signal, signal)
        features.append(1.0 if best_signal > 0 else 0.0)
        features.append(_clamp01(best_signal))

    return torch.tensor(features, dtype=torch.float32)


def _encode_proprioception(
    orientation: Direction,
    drive_system: DriveSystem,
    passable_moves: dict[Direction, tuple[int, int]],
    position: tuple[int, int],
    prev_position: tuple[int, int],
) -> torch.Tensor:
    """Drives + satiety (interoception), orientation one-hot, last displacement,
    and action-validity mask."""
    features: list[float] = []

    levels = drive_system.get_levels()
    for dt in DRIVE_TYPES:
        features.append(_clamp01(float(levels.get(dt, 0.0))))

    satiety = drive_system.get_satiety_levels()
    for dt in DRIVE_TYPES:
        features.append(_clamp01(float(satiety.get(dt, 0.0))))

    for d in ALL_DIRS:
        features.append(1.0 if d == orientation else 0.0)

    dx = position[0] - prev_position[0]
    dy = position[1] - prev_position[1]
    features.append(_clamp11(float(dx)))
    features.append(_clamp11(float(dy)))

    for d in ALL_DIRS:
        features.append(1.0 if d in passable_moves else 0.0)

    return torch.tensor(features, dtype=torch.float32)


def _encode_rhythm(
    tick: int,
    last_consumption_ticks: dict[DriveType, int],
    config: OrganConfig,
) -> torch.Tensor:
    """sin/cos tick phase + normalised interval since last consumption per drive."""
    features: list[float] = []

    phase = 2.0 * math.pi * tick / max(config.rhythm_period, 1.0)
    features.append(math.sin(phase))
    features.append(math.cos(phase))

    for dt in DRIVE_TYPES:
        last_tick = last_consumption_ticks.get(dt, -1)
        if last_tick < 0:
            interval = 1.0
        else:
            elapsed = tick - last_tick
            interval = min(1.0, elapsed / max(config.rhythm_period, 1.0))
        features.append(_clamp01(interval))

    return torch.tensor(features, dtype=torch.float32)


# ── Public API ─────────────────────────────────────────────────────────


def encode_organs(
    perceptions: list[Perception],
    environment: Environment,
    position: tuple[int, int],
    orientation: Direction,
    drive_system: DriveSystem,
    passable_moves: dict[Direction, tuple[int, int]],
    prev_position: tuple[int, int],
    tick: int,
    last_consumption_ticks: dict[DriveType, int],
    config: OrganConfig,
    perception_radius: float | None = None,
) -> OrgansObservation:
    """Build a complete organ observation from the current agent/environment state."""
    return OrgansObservation(
        sight=_encode_sight(perceptions, orientation, config),
        smell=_encode_smell(position, environment, config),
        touch=_encode_touch(position, environment, config),
        proprioception=_encode_proprioception(
            orientation,
            drive_system,
            passable_moves,
            position,
            prev_position,
        ),
        rhythm=_encode_rhythm(tick, last_consumption_ticks, config),
    )
