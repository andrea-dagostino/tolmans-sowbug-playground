"""DQN-based sowbug agent — learns Q(state, action) through experience replay."""

from collections import deque
import math
from pathlib import Path

import torch

from tolmans_sowbug_playground.core.agent import Agent
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import StimulusType
from tolmans_sowbug_playground.systems.dqn import DQNAgent
from tolmans_sowbug_playground.systems.drives import Drive, DriveSystem, DriveType
from tolmans_sowbug_playground.systems.memory import MemorySystem
from tolmans_sowbug_playground.systems.motor import Direction, MotorSystem
from tolmans_sowbug_playground.systems.organs import (
    OrganConfig,
    OrgansObservation,
    compute_organ_state_dim,
    encode_organs,
)
from tolmans_sowbug_playground.systems.sensors import Perception, SensorSystem

DRIVE_STIMULUS_MAP = {
    DriveType.HUNGER: StimulusType.FOOD,
    DriveType.THIRST: StimulusType.WATER,
    DriveType.TEMPERATURE: StimulusType.HEAT,
}

# Ordered list mapping action index → Direction
ACTION_DIRECTIONS = [
    Direction.NORTH,
    Direction.SOUTH,
    Direction.EAST,
    Direction.WEST,
    Direction.STAY,
]

N_ACTIONS = len(ACTION_DIRECTIONS)
CRITICAL_URGENCY_LEVEL = 0.85
CRITICAL_OFF_TARGET_PENALTY = 0.12
URGENT_EXPLORE_LEVEL = 0.7
URGENT_EXPLORE_NOVELTY_BONUS = 0.02
URGENT_EXPLORE_STAY_PENALTY = 0.02
URGENT_EXPLORE_LOOP_PENALTY = 0.01
HIGH_URGENCY_STASIS_LEVEL = 0.6
HIGH_URGENCY_STAY_PENALTY = 0.01
HIGH_URGENCY_LOOP_PENALTY = 0.005


DRIVE_TYPES = [DriveType.HUNGER, DriveType.THIRST, DriveType.TEMPERATURE]


class DQNSowbug(Agent):
    """A sowbug that uses a Deep Q-Network for decision-making.

    Keeps the same drive/sensor/motor/memory subsystems as the symbolic
    Sowbug, but replaces the handcrafted decide() logic with an
    epsilon-greedy DQN policy trained via experience replay.
    """

    def __init__(
        self,
        position: tuple[int, int],
        # Drive params
        hunger_rate: float = 0.01,
        thirst_rate: float = 0.008,
        temperature_rate: float = 0.005,
        perception_radius: float = 5.0,
        satiety_decay_rate: float = 0.05,
        bite_size: float = 0.3,
        # DQN params
        dqn_hidden_size: int = 128,
        dqn_learning_rate: float = 3e-4,
        dqn_gamma: float = 0.99,
        dqn_eps_start: float = 0.9,
        dqn_eps_end: float = 0.05,
        dqn_eps_decay: float = 5000.0,
        dqn_tau: float = 0.005,
        dqn_batch_size: int = 128,
        dqn_replay_capacity: int = 50000,
        dqn_optimize_every: int = 1,
        dqn_urgent_explore_level: float = URGENT_EXPLORE_LEVEL,
        dqn_urgent_explore_novelty_bonus: float = URGENT_EXPLORE_NOVELTY_BONUS,
        dqn_urgent_explore_stay_penalty: float = URGENT_EXPLORE_STAY_PENALTY,
        dqn_urgent_explore_loop_penalty: float = URGENT_EXPLORE_LOOP_PENALTY,
        dqn_high_urgency_stasis_level: float = HIGH_URGENCY_STASIS_LEVEL,
        dqn_high_urgency_stay_penalty: float = HIGH_URGENCY_STAY_PENALTY,
        dqn_high_urgency_loop_penalty: float = HIGH_URGENCY_LOOP_PENALTY,
        dqn_use_memory_target_known: bool = False,
        dqn_use_memory_shaping: bool = False,
        # Organ params
        organ_sight_k: int = 3,
        organ_sight_radius: float | None = None,
        organ_sight_fov_degrees: float = 180.0,
        organ_smell_radius: float | None = None,
        organ_touch_radius: int = 1,
        organ_rhythm_period: float = 100.0,
    ) -> None:
        sight_radius = (
            float(perception_radius)
            if organ_sight_radius is None
            else float(organ_sight_radius)
        )
        smell_radius = (
            float(perception_radius) * 1.5
            if organ_smell_radius is None
            else float(organ_smell_radius)
        )

        drive_system = DriveSystem(
            drives=[
                Drive(
                    DriveType.HUNGER,
                    rate=hunger_rate,
                    satiety_decay_rate=satiety_decay_rate,
                ),
                Drive(
                    DriveType.THIRST,
                    rate=thirst_rate,
                    satiety_decay_rate=satiety_decay_rate,
                ),
                Drive(
                    DriveType.TEMPERATURE,
                    rate=temperature_rate,
                    satiety_decay_rate=satiety_decay_rate,
                ),
            ]
        )
        super().__init__(
            position=position,
            orientation=Direction.NORTH,
            drive_system=drive_system,
            sensor_system=SensorSystem(perception_radius=sight_radius),
            memory_system=MemorySystem(
                learning_rate=0.1, decay_rate=0.01, kernel_bandwidth=0.0
            ),
            motor_system=MotorSystem(),
        )
        self._grid_size: tuple[int, int] = (20, 20)
        self.bite_size = bite_size
        self._optimize_every = dqn_optimize_every
        self._tick_count = 0
        self._urgent_explore_level = dqn_urgent_explore_level
        self._urgent_explore_novelty_bonus = dqn_urgent_explore_novelty_bonus
        self._urgent_explore_stay_penalty = dqn_urgent_explore_stay_penalty
        self._urgent_explore_loop_penalty = dqn_urgent_explore_loop_penalty
        self._high_urgency_stasis_level = dqn_high_urgency_stasis_level
        self._high_urgency_stay_penalty = dqn_high_urgency_stay_penalty
        self._high_urgency_loop_penalty = dqn_high_urgency_loop_penalty
        self._use_memory_target_known = dqn_use_memory_target_known
        self._use_memory_shaping = dqn_use_memory_shaping

        # Organ encoder
        self._organ_config = OrganConfig(
            sight_k=organ_sight_k,
            sight_radius=sight_radius,
            sight_fov_degrees=organ_sight_fov_degrees,
            smell_radius=smell_radius,
            touch_radius=organ_touch_radius,
            rhythm_period=organ_rhythm_period,
        )
        state_dim = compute_organ_state_dim(self._organ_config)
        self._dqn = DQNAgent(
            state_dim=state_dim,
            n_actions=N_ACTIONS,
            hidden_size=dqn_hidden_size,
            learning_rate=dqn_learning_rate,
            gamma=dqn_gamma,
            eps_start=dqn_eps_start,
            eps_end=dqn_eps_end,
            eps_decay=dqn_eps_decay,
            tau=dqn_tau,
            batch_size=dqn_batch_size,
            replay_capacity=dqn_replay_capacity,
        )

        # Transition bookkeeping — filled in decide(), used in post_act()
        self._prev_state: torch.Tensor | None = None
        self._prev_action: int | None = None
        self._prev_position: tuple[int, int] = position
        self._prev_drive_levels: dict[DriveType, float] = {}
        self._prev_urgent_drive: DriveType | None = None
        self._prev_urgent_level: float = 0.0
        self._prev_urgent_target_known: bool = False
        self._recent_positions: deque[tuple[int, int]] = deque(maxlen=8)
        self._last_consumption_ticks: dict[DriveType, int] = {}

        # Visualization / diagnostic state
        self._last_q_values: dict[str, float] = {}
        self._chosen_direction: str = ""
        self._resource_consumptions: int = 0
        self._last_reward_total: float = 0.0
        self._last_reward_components: dict[str, float] = {
            "drive_reduction": 0.0,
            "shaping": 0.0,
            "urgency_penalty": 0.0,
            "off_target_penalty": 0.0,
            "urgent_explore_bonus": 0.0,
            "urgent_explore_penalty": 0.0,
            "stasis_penalty": 0.0,
        }
        self._last_organ_obs: OrgansObservation | None = None

        # Passable moves cache (filled in perceive)
        self._passable_moves: dict[Direction, tuple[int, int]] = {}
        self._environment: Environment | None = None

    def perceive(self, environment: Environment) -> None:
        self._grid_size = (environment.width, environment.height)
        self._environment = environment
        super().perceive(environment)

        # Cache passable moves for state encoding and action masking
        self._passable_moves = {}
        for d in ACTION_DIRECTIONS:
            if d == Direction.STAY:
                self._passable_moves[d] = self.position
                continue
            dx, dy = d.value
            nx, ny = self.position[0] + dx, self.position[1] + dy
            if environment.is_within_bounds((nx, ny)) and environment.is_passable(
                (nx, ny)
            ):
                self._passable_moves[d] = (nx, ny)

    def _shortest_path_distance(
        self, start: tuple[int, int], goal: tuple[int, int], environment: Environment
    ) -> int | None:
        """Manhattan-step shortest path length over passable cells."""
        if start == goal:
            return 0
        if (
            not environment.is_within_bounds(start)
            or not environment.is_within_bounds(goal)
            or not environment.is_passable(goal)
        ):
            return None
        queue: deque[tuple[tuple[int, int], int]] = deque([(start, 0)])
        seen = {start}
        while queue:
            (x, y), dist = queue.popleft()
            for dx, dy in [Direction.NORTH.value, Direction.SOUTH.value, Direction.EAST.value, Direction.WEST.value]:
                nx, ny = x + dx, y + dy
                nxt = (nx, ny)
                if nxt in seen:
                    continue
                if not environment.is_within_bounds(nxt) or not environment.is_passable(nxt):
                    continue
                if nxt == goal:
                    return dist + 1
                seen.add(nxt)
                queue.append((nxt, dist + 1))
        return None

    def _encode_state(self) -> torch.Tensor:
        """Encode current perceptions + internal state via the organ encoder."""
        assert self._environment is not None
        obs = encode_organs(
            perceptions=self.current_perceptions,
            environment=self._environment,
            position=self.position,
            orientation=self.orientation,
            drive_system=self.drive_system,
            passable_moves=self._passable_moves,
            prev_position=self._prev_position,
            tick=self._tick_count,
            last_consumption_ticks=self._last_consumption_ticks,
            config=self._organ_config,
        )
        self._last_organ_obs = obs
        return obs.to_tensor()

    def _is_in_sight_fov(self, direction: tuple[int, int]) -> bool:
        """Return True when vector lies within current forward sight cone."""
        fx, fy = self.orientation.value
        # If stationary orientation is unknown, keep omnidirectional fallback.
        if fx == 0 and fy == 0:
            return True
        dx, dy = float(direction[0]), float(direction[1])
        dist = math.hypot(dx, dy)
        if dist <= 1e-9:
            return True
        fov = max(1.0, min(360.0, float(self._organ_config.sight_fov_degrees)))
        half_fov_rad = math.radians(fov / 2.0)
        cos_threshold = math.cos(half_fov_rad)
        cos_angle = (dx * float(fx) + dy * float(fy)) / dist
        return cos_angle >= cos_threshold

    def _current_sight_perceptions(
        self, stimulus_type: StimulusType | None = None
    ) -> list[Perception]:
        filtered = [p for p in self.current_perceptions if self._is_in_sight_fov(p.direction)]
        if stimulus_type is None:
            return filtered
        return [p for p in filtered if p.stimulus.stimulus_type == stimulus_type]

    def decide(self) -> Direction:
        """Epsilon-greedy action selection from DQN."""
        state = self._encode_state()

        # Save for transition in post_act
        self._prev_state = state
        self._prev_position = self.position
        self._prev_drive_levels = dict(self.drive_system.get_levels())
        urgent = self.drive_system.get_most_urgent()
        if urgent is not None and urgent.level >= 0.1:
            self._prev_urgent_drive = urgent.drive_type
            self._prev_urgent_level = urgent.level
            urgent_stimulus = DRIVE_STIMULUS_MAP[urgent.drive_type]
            has_visible_target = bool(
                self._current_sight_perceptions(stimulus_type=urgent_stimulus)
            )
            has_memory_target = False
            if self._use_memory_target_known:
                gw, gh = self._grid_size
                has_memory_target = (
                    self.memory_system.get_best_location_for(urgent_stimulus, gw, gh)
                    is not None
                )
            self._prev_urgent_target_known = has_visible_target or has_memory_target
        else:
            self._prev_urgent_drive = None
            self._prev_urgent_level = 0.0
            self._prev_urgent_target_known = False

        valid_action_indices = [
            i for i, direction in enumerate(ACTION_DIRECTIONS) if direction in self._passable_moves
        ]
        action_idx = self._dqn.select_action(state, valid_actions=valid_action_indices)
        self._prev_action = action_idx

        direction = ACTION_DIRECTIONS[action_idx]

        # Store Q-values for visualization
        q_vals = self._dqn.get_q_values(state)
        self._last_q_values = {
            d.name: round(q_vals[i].item(), 4) for i, d in enumerate(ACTION_DIRECTIONS)
        }
        self._chosen_direction = direction.name

        return direction

    def post_act(self, environment: Environment) -> None:
        """Update drives, consume resources, compute reward, train DQN."""
        # Re-perceive after movement so transition next_state matches
        # the post-action world snapshot.
        self.perceive(environment)
        self._tick_count += 1

        # Update drives (same as symbolic sowbug)
        self.drive_system.update()

        # Consume resources at current position
        stimuli_here = environment.get_stimuli_at(self.position)
        consumable = {
            StimulusType.FOOD: DriveType.HUNGER,
            StimulusType.WATER: DriveType.THIRST,
            StimulusType.HEAT: DriveType.TEMPERATURE,
        }

        # Evaluate prior expectations at current position BEFORE recording
        # new experience, to model disappointment-driven extinction.
        for entry in list(self.memory_system.cognitive_map.get(self.position, [])):
            actual_stim = [
                s for s in stimuli_here if s.stimulus_type == entry.stimulus_type
            ]
            if actual_stim:
                drive_type = consumable.get(entry.stimulus_type)
                actual_reward = 0.0
                if (
                    drive_type is not None
                    and self.drive_system.get_level(drive_type) > 0.1
                ):
                    actual_reward = 1.0
                self.memory_system.update_expectation(
                    self.position,
                    entry.stimulus_type,
                    actual_stim[0].intensity,
                    actual_reward,
                )
            else:
                self.memory_system.update_expectation(
                    self.position, entry.stimulus_type, 0.0, 0.0
                )

        for stimulus in stimuli_here:
            drive_type = consumable.get(stimulus.stimulus_type)
            if drive_type is None:
                self.memory_system.record_experience(
                    self.position, stimulus.stimulus_type, stimulus.intensity, 0.0
                )
                continue
            drive_level = self.drive_system.get_level(drive_type)
            if drive_level <= 0.1:
                self.memory_system.record_experience(
                    self.position, stimulus.stimulus_type, stimulus.intensity, 0.0
                )
                continue
            wanted = self.bite_size * drive_level
            actual = stimulus.consume(wanted)
            self.drive_system.satisfy(drive_type, actual)
            reward_value = 1.0 if actual > 0 else 0.0
            if reward_value > 0:
                self._resource_consumptions += 1
                self._last_consumption_ticks[drive_type] = self._tick_count
            self.memory_system.record_experience(
                self.position, stimulus.stimulus_type, stimulus.intensity, reward_value
            )

        # Compute reward: drive reduction + approach shaping + urgency penalty
        current_levels = self.drive_system.get_levels()
        reward_drive_reduction = 0.0
        reward_shaping = 0.0
        reward_off_target_penalty = 0.0
        reward_urgent_explore_bonus = 0.0
        reward_urgent_explore_penalty = 0.0
        reward_stasis_penalty = 0.0
        critical_focus = (
            self._prev_urgent_drive is not None
            and self._prev_urgent_level >= CRITICAL_URGENCY_LEVEL
        )

        # Primary: reward for drive reduction, scaled by (1 - satiety).
        # Diminishing returns: first bite when starving is highly rewarding,
        # continued consumption while sated gives almost nothing.
        satiety_levels = self.drive_system.get_satiety_levels()
        for dt in DriveType:
            prev = self._prev_drive_levels.get(dt, 0.0)
            curr = current_levels.get(dt, 0.0)
            reduction = prev - curr
            if reduction > 0:
                satiety = satiety_levels.get(dt, 0.0)
                scaled_reduction = reduction * (1.0 - satiety)
                if critical_focus and dt != self._prev_urgent_drive:
                    # During critical urgency, downweight off-target consumption.
                    # This prevents camping at a convenient but irrelevant resource.
                    scaled_reduction *= 0.0
                    reward_off_target_penalty += (
                        reduction * CRITICAL_OFF_TARGET_PENALTY
                    )
                reward_drive_reduction += scaled_reduction

        # Shaping: reward for moving closer to the MOST URGENT drive's stimulus.
        # Only the highest drive gets approach shaping — forces the agent to
        # prioritize sequentially (eat → drink → seek warmth) rather than
        # chasing whichever resource is closest.
        radius = self.sensor_system.perception_radius
        prev_pos = getattr(self, "_prev_position", self.position)
        if self._prev_urgent_drive is not None and self._prev_urgent_level >= 0.1:
            stim_type = DRIVE_STIMULUS_MAP[self._prev_urgent_drive]
            drive_level = self._prev_urgent_level
            relevant = self._current_sight_perceptions(stimulus_type=stim_type)
            if relevant:
                target = max(relevant, key=lambda p: p.perceived_intensity)
                prev_dist = self._shortest_path_distance(
                    prev_pos, target.stimulus.position, environment
                )
                curr_dist = self._shortest_path_distance(
                    self.position, target.stimulus.position, environment
                )
                if prev_dist is not None and curr_dist is not None:
                    approach = (prev_dist - curr_dist) / max(radius, 1.0)
                    reward_shaping += 0.1 * approach * drive_level
            elif self._use_memory_shaping:
                # Fallback: follow memory when the target resource isn't visible.
                # Creates a gradient toward remembered locations even outside
                # perception range — prevents getting stuck in perception deserts.
                gw, gh = self._grid_size
                best_mem = self.memory_system.get_best_location_for(
                    stim_type, gw, gh
                )
                if best_mem is not None and best_mem != self.position:
                    prev_dist = self._shortest_path_distance(prev_pos, best_mem, environment)
                    curr_dist = self._shortest_path_distance(self.position, best_mem, environment)
                    if prev_dist is not None and curr_dist is not None:
                        approach = (prev_dist - curr_dist) / max(radius, 1.0)
                        reward_shaping += 0.05 * approach * drive_level

        # When urgent target is unknown (not perceived, no memory), incentivize
        # directed exploration and discourage camping/short loops.
        urgent_search = (
            self._prev_urgent_drive is not None
            and self._prev_urgent_level >= self._urgent_explore_level
            and not self._prev_urgent_target_known
        )
        if urgent_search:
            familiarity = self.memory_system.visited.get(self.position, 0.0)
            novelty = max(0.0, 1.0 - min(1.0, familiarity))
            reward_urgent_explore_bonus = self._urgent_explore_novelty_bonus * novelty
            if self.position == prev_pos:
                reward_urgent_explore_penalty += self._urgent_explore_stay_penalty
            if self.position in self._recent_positions:
                reward_urgent_explore_penalty += self._urgent_explore_loop_penalty

        # Generic anti-stasis pressure under high urgency, regardless of whether
        # the target is "known". This helps break STAY/short-loop attractors.
        max_drive = max(current_levels.values()) if current_levels else 0.0
        if max_drive >= self._high_urgency_stasis_level:
            if self.position == prev_pos:
                reward_stasis_penalty += self._high_urgency_stay_penalty * max_drive
            if self.position in self._recent_positions:
                reward_stasis_penalty += self._high_urgency_loop_penalty * max_drive

        # Urgency penalty — quadratic so extreme drives create strong pressure
        # to move while barely affecting behavior when drives are low.
        # At (1.0, 1.0, 0.1): ~0.01/tick.  At (0.3, 0.2, 0.1): ~0.0007/tick.
        total_urgency = sum(v * v for v in current_levels.values())
        reward_urgency_penalty = 0.005 * total_urgency
        reward = (
            reward_drive_reduction
            + reward_shaping
            - reward_urgency_penalty
            - reward_off_target_penalty
            + reward_urgent_explore_bonus
            - reward_urgent_explore_penalty
            - reward_stasis_penalty
        )
        self._last_reward_total = reward
        self._last_reward_components = {
            "drive_reduction": reward_drive_reduction,
            "shaping": reward_shaping,
            "urgency_penalty": reward_urgency_penalty,
            "off_target_penalty": reward_off_target_penalty,
            "urgent_explore_bonus": reward_urgent_explore_bonus,
            "urgent_explore_penalty": reward_urgent_explore_penalty,
            "stasis_penalty": reward_stasis_penalty,
        }

        # Encode next state and push transition
        next_state = self._encode_state()
        next_valid_mask = torch.tensor(
            [direction in self._passable_moves for direction in ACTION_DIRECTIONS],
            dtype=torch.bool,
        )
        if self._prev_state is not None and self._prev_action is not None:
            self._dqn.memory.push(
                self._prev_state,
                self._prev_action,
                reward,
                next_state,
                False,
                next_valid_mask,
            )

        # Optimize and update target network
        if self._tick_count % self._optimize_every == 0:
            self._dqn.optimize()
            self._dqn.soft_update_target()

        # Maintain memory system for UI
        self.memory_system.decay()
        self.memory_system.record_visit(self.position)
        self._recent_positions.append(self.position)

    def get_state(self) -> dict:
        state = super().get_state()
        state["q_values"] = self._last_q_values
        state["epsilon"] = round(self._dqn.epsilon, 4)
        state["replay_size"] = len(self._dqn.memory)
        state["training_loss"] = round(self._dqn.last_loss, 6)
        state["resource_consumptions"] = self._resource_consumptions
        state["reward_total"] = round(self._last_reward_total, 6)
        state["reward_components"] = {
            k: round(v, 6) for k, v in self._last_reward_components.items()
        }
        state["decision_reason"] = "dqn"
        state["sight_perceptions"] = [
            {
                "stimulus_type": p.stimulus.stimulus_type.value,
                "stimulus_position": list(p.stimulus.position),
                "perceived_intensity": round(p.perceived_intensity, 3),
                "distance": round(p.distance, 3),
                "direction": list(p.direction),
            }
            for p in self._current_sight_perceptions()
        ]
        state["organ_radii"] = {
            "sight": round(float(self._organ_config.sight_radius), 3),
            "smell": round(float(self._organ_config.smell_radius), 3),
            "touch": int(self._organ_config.touch_radius),
            "sight_fov_degrees": round(float(self._organ_config.sight_fov_degrees), 3),
        }
        if self._last_organ_obs is not None:
            state["organ_metrics"] = self._last_organ_obs.to_dict()
        # Map to existing VTE format for UI compatibility
        state["vte"] = {
            "is_deliberating": False,
            "candidates": [
                {"direction": d, "value": v}
                for d, v in self._last_q_values.items()
            ],
            "chosen": self._chosen_direction,
            "hesitated": False,
        }
        return state

    def save_model(self, path: str | Path) -> None:
        """Persist DQN checkpoint for this sowbug."""
        self._dqn.save(path)

    def load_model(self, path: str | Path) -> None:
        """Load DQN checkpoint for this sowbug."""
        self._dqn.load(path)
