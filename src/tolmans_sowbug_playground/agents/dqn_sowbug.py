"""DQN-based sowbug agent — learns Q(state, action) through experience replay."""

import torch

from tolmans_sowbug_playground.core.agent import Agent
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import StimulusType
from tolmans_sowbug_playground.systems.dqn import DQNAgent
from tolmans_sowbug_playground.systems.drives import Drive, DriveSystem, DriveType
from tolmans_sowbug_playground.systems.memory import MemorySystem
from tolmans_sowbug_playground.systems.motor import Direction, MotorSystem
from tolmans_sowbug_playground.systems.sensors import SensorSystem

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

# Ordered list of stimulus types for perception encoding
STIMULUS_TYPES = [
    StimulusType.FOOD,
    StimulusType.WATER,
    StimulusType.LIGHT,
    StimulusType.HEAT,
    StimulusType.OBSTACLE,
]

N_ACTIONS = len(ACTION_DIRECTIONS)


def compute_state_dim(perception_k: int = 3) -> int:
    """Total dimensionality of the state vector.

    3 drives + 3 satiety + 5 passable + 5*k*3 perceptions
    """
    return 3 + 3 + 5 + len(STIMULUS_TYPES) * perception_k * 3


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
        dqn_perception_k: int = 3,
    ) -> None:
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
            sensor_system=SensorSystem(perception_radius=perception_radius),
            memory_system=MemorySystem(
                learning_rate=0.1, decay_rate=0.01, kernel_bandwidth=0.0
            ),
            motor_system=MotorSystem(),
        )
        self._grid_size: tuple[int, int] = (20, 20)
        self.bite_size = bite_size
        self._perception_k = dqn_perception_k
        self._optimize_every = dqn_optimize_every
        self._tick_count = 0

        state_dim = compute_state_dim(dqn_perception_k)
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
        self._prev_drive_levels: dict[DriveType, float] = {}

        # Visualization state
        self._last_q_values: dict[str, float] = {}
        self._chosen_direction: str = ""
        self._resource_consumptions: int = 0

        # Passable moves cache (filled in perceive)
        self._passable_moves: dict[Direction, tuple[int, int]] = {}

    def perceive(self, environment: Environment) -> None:
        self._grid_size = (environment.width, environment.height)
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

    def _encode_state(self) -> torch.Tensor:
        """Encode current perceptions + drives into a fixed-size tensor."""
        features: list[float] = []

        # Drive levels (3 dims)
        levels = self.drive_system.get_levels()
        for dt in [DriveType.HUNGER, DriveType.THIRST, DriveType.TEMPERATURE]:
            features.append(levels.get(dt, 0.0))

        # Satiety levels (3 dims)
        satiety = self.drive_system.get_satiety_levels()
        for dt in [DriveType.HUNGER, DriveType.THIRST, DriveType.TEMPERATURE]:
            features.append(satiety.get(dt, 0.0))

        # Passable directions (5 dims: N, S, E, W, STAY)
        for d in ACTION_DIRECTIONS:
            features.append(1.0 if d in self._passable_moves else 0.0)

        # Top-k perceptions per stimulus type (5 types × k × 3 dims each)
        radius = self.sensor_system.perception_radius
        for stype in STIMULUS_TYPES:
            typed_perceptions = [
                p
                for p in self.current_perceptions
                if p.stimulus.stimulus_type == stype
            ]
            # Sort by intensity descending, take top-k
            typed_perceptions.sort(
                key=lambda p: p.perceived_intensity, reverse=True
            )
            for i in range(self._perception_k):
                if i < len(typed_perceptions):
                    p = typed_perceptions[i]
                    features.append(p.perceived_intensity)
                    # Normalize direction by perception radius
                    features.append(p.direction[0] / max(radius, 1.0))
                    features.append(p.direction[1] / max(radius, 1.0))
                else:
                    features.extend([0.0, 0.0, 0.0])

        return torch.tensor(features, dtype=torch.float32)

    def decide(self) -> Direction:
        """Epsilon-greedy action selection from DQN."""
        state = self._encode_state()

        # Save for transition in post_act
        self._prev_state = state
        self._prev_drive_levels = dict(self.drive_system.get_levels())

        action_idx = self._dqn.select_action(state)
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

        for stimulus in stimuli_here:
            drive_type = consumable.get(stimulus.stimulus_type)
            if drive_type is None:
                continue
            drive_level = self.drive_system.get_level(drive_type)
            if drive_level <= 0.1:
                continue
            wanted = self.bite_size * drive_level
            actual = stimulus.consume(wanted)
            self.drive_system.satisfy(drive_type, actual)
            if actual > 0:
                self._resource_consumptions += 1
                # Record in memory for UI cognitive map display
                self.memory_system.record_experience(
                    self.position, stimulus.stimulus_type, stimulus.intensity, 1.0
                )

        # Compute reward: drive reduction + urgency penalty
        current_levels = self.drive_system.get_levels()
        reward = 0.0
        for dt in DriveType:
            prev = self._prev_drive_levels.get(dt, 0.0)
            curr = current_levels.get(dt, 0.0)
            reduction = prev - curr
            if reduction > 0:
                reward += reduction
        max_drive = max(current_levels.values()) if current_levels else 0.0
        reward -= 0.01 * max_drive

        # Encode next state and push transition
        next_state = self._encode_state()
        if self._prev_state is not None and self._prev_action is not None:
            self._dqn.memory.push(
                self._prev_state, self._prev_action, reward, next_state, False
            )

        # Optimize and update target network
        if self._tick_count % self._optimize_every == 0:
            self._dqn.optimize()
            self._dqn.soft_update_target()

        # Maintain memory system for UI
        self.memory_system.decay()
        self.memory_system.record_visit(self.position)

    def get_state(self) -> dict:
        state = super().get_state()
        state["q_values"] = self._last_q_values
        state["epsilon"] = round(self._dqn.epsilon, 4)
        state["replay_size"] = len(self._dqn.memory)
        state["training_loss"] = round(self._dqn.last_loss, 6)
        state["resource_consumptions"] = self._resource_consumptions
        state["decision_reason"] = "dqn"
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
