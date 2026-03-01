import random
from collections import deque

from tolmans_sowbug_playground.core.agent import Agent
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import StimulusType
from tolmans_sowbug_playground.systems.drives import Drive, DriveSystem, DriveType
from tolmans_sowbug_playground.systems.memory import MemorySystem
from tolmans_sowbug_playground.systems.motor import Direction, MotorSystem
from tolmans_sowbug_playground.systems.sensors import Perception, SensorSystem

DRIVE_STIMULUS_MAP = {
    DriveType.HUNGER: StimulusType.FOOD,
    DriveType.THIRST: StimulusType.WATER,
    DriveType.TEMPERATURE: StimulusType.HEAT,
}

MOVE_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]


class Sowbug(Agent):
    def __init__(
        self,
        position: tuple[int, int],
        hunger_rate: float = 0.01,
        thirst_rate: float = 0.008,
        temperature_rate: float = 0.005,
        perception_radius: float = 5.0,
        learning_rate: float = 0.1,
        decay_rate: float = 0.01,
        kernel_bandwidth: float = 2.0,
        vte_horizon: int = 5,
        vte_threshold: float = 0.8,
        bite_size: float = 0.3,
        satiety_decay_rate: float = 0.05,
    ) -> None:
        drive_system = DriveSystem(
            drives=[
                Drive(DriveType.HUNGER, rate=hunger_rate, satiety_decay_rate=satiety_decay_rate),
                Drive(DriveType.THIRST, rate=thirst_rate, satiety_decay_rate=satiety_decay_rate),
                Drive(DriveType.TEMPERATURE, rate=temperature_rate, satiety_decay_rate=satiety_decay_rate),
            ]
        )
        super().__init__(
            position=position,
            orientation=Direction.NORTH,
            drive_system=drive_system,
            sensor_system=SensorSystem(perception_radius=perception_radius),
            memory_system=MemorySystem(
                learning_rate=learning_rate,
                decay_rate=decay_rate,
                kernel_bandwidth=kernel_bandwidth,
            ),
            motor_system=MotorSystem(),
        )
        self._grid_size: tuple[int, int] = (20, 20)
        self._vte_horizon = vte_horizon
        self._vte_threshold = vte_threshold
        self._vte_automaticity = 0.7
        self._vte_hesitation_rate = 0.3
        self.bite_size = bite_size

        # VTE state — reset each tick, exported for visualization
        self._vte_candidates: list[dict] = []
        self._is_deliberating: bool = False
        self._vte_chosen: str = ""
        self._vte_hesitated: bool = False

        # Resource gathering counter — cumulative across the simulation
        self._resource_consumptions: int = 0

        # Stuck detection — when the bug oscillates in a small area,
        # it suppresses stimulus attraction and explores freely
        self._stuck_window: int = 8
        self._recent_positions: deque[tuple[int, int]] = deque(maxlen=self._stuck_window)
        self._is_stuck: bool = False

    def perceive(self, environment: Environment) -> None:
        self._grid_size = (environment.width, environment.height)
        super().perceive(environment)

        # Precompute which adjacent moves are passable for obstacle-aware decisions
        self._passable_moves: dict[Direction, tuple[int, int]] = {}
        for d in MOVE_DIRECTIONS:
            dx, dy = d.value
            nx, ny = self.position[0] + dx, self.position[1] + dy
            if environment.is_within_bounds((nx, ny)) and environment.is_passable(
                (nx, ny)
            ):
                self._passable_moves[d] = (nx, ny)

    def _drive_to_stimulus(self, drive_type: DriveType) -> StimulusType:
        return DRIVE_STIMULUS_MAP[drive_type]

    def _direction_toward(self, target: tuple[int, int]) -> Direction:
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]

        # Build preference: primary toward target, then perpendicular directions
        if abs(dx) >= abs(dy):
            primary = Direction.EAST if dx > 0 else Direction.WEST
            perp_a = Direction.SOUTH if dy > 0 else Direction.NORTH
            perp_b = Direction.NORTH if dy > 0 else Direction.SOUTH
        else:
            primary = Direction.SOUTH if dy > 0 else Direction.NORTH
            perp_a = Direction.EAST if dx > 0 else Direction.WEST
            perp_b = Direction.WEST if dx > 0 else Direction.EAST

        # Use current orientation as momentum to break ties between
        # perpendicular directions — creates natural wall-following
        perps = [perp_a, perp_b]
        if self.orientation in perps:
            perps.remove(self.orientation)
            perps.insert(0, self.orientation)

        for d in [primary] + perps:
            if d in self._passable_moves:
                return d

        # All toward-target directions blocked — pick any passable direction
        if self._passable_moves:
            return random.choice(list(self._passable_moves.keys()))

        return Direction.STAY

    def _get_light_perceptions(self) -> list[Perception]:
        return [
            p
            for p in self.current_perceptions
            if p.stimulus.stimulus_type == StimulusType.LIGHT
        ]

    def _apply_phototaxis(self, preferred: Direction) -> Direction:
        """Positive phototaxis: bias movement toward the strongest light source.

        The phototactic pull is inversely proportional to drive urgency —
        when drives are high, the agent follows its drive-based decision;
        when drives are low, phototaxis dominates.
        """
        light_perceptions = self._get_light_perceptions()
        if not light_perceptions:
            return preferred

        # High drives suppress phototaxis — a hungry agent ignores the light
        urgent = self.drive_system.get_most_urgent()
        if urgent is not None and urgent.level > 0.3:
            suppress = min(1.0, (urgent.level - 0.3) * 1.43)  # 0.0 at 0.3, 1.0 at 1.0
            if random.random() < suppress:
                return preferred

        # Redirect toward strongest light
        strongest = max(light_perceptions, key=lambda p: p.perceived_intensity)
        return self._direction_toward(strongest.stimulus.position)

    def _explore_freely(self) -> Direction:
        """Pure familiarity-based exploration — no stimulus attraction."""
        candidates = []
        for direction, (nx, ny) in self._passable_moves.items():
            familiarity = self.memory_system.visited.get((nx, ny), 0.0)
            candidates.append((direction, familiarity))

        if not candidates:
            return Direction.STAY

        min_familiarity = min(f for _, f in candidates)
        least_familiar = [d for d, f in candidates if f == min_familiarity]
        return random.choice(least_familiar)

    def _explore(self) -> Direction:
        if self._is_stuck:
            return self._explore_freely()

        urgent = self.drive_system.get_most_urgent()
        if urgent is not None:
            target_type = self._drive_to_stimulus(urgent.drive_type)
            relevant = [
                p
                for p in self.current_perceptions
                if p.stimulus.stimulus_type == target_type
            ]
            if relevant:
                strongest = max(relevant, key=lambda p: p.perceived_intensity)
                return self._direction_toward(strongest.stimulus.position)

        return self._explore_freely()

    def _get_avg_memory_strength(self, stimulus_type: StimulusType) -> float:
        strengths = []
        for entries in self.memory_system.cognitive_map.values():
            for entry in entries:
                if entry.stimulus_type == stimulus_type:
                    strengths.append(entry.strength)
        return sum(strengths) / len(strengths) if strengths else 0.0

    def _deliberate(self, target_stimulus: StimulusType) -> Direction:
        """Vicarious trial and error: mentally simulate each direction."""
        candidates = []
        for direction in MOVE_DIRECTIONS:
            if direction not in self._passable_moves:
                continue
            next_pos = self._passable_moves[direction]
            value = self.memory_system.estimate_value(
                next_pos, target_stimulus, horizon=self._vte_horizon
            )
            candidates.append({
                "direction": direction.name,
                "value": round(value, 4),
                "position": list(next_pos),
            })

        if not candidates:
            self._is_deliberating = False
            self._vte_hesitated = False
            return Direction.STAY

        candidates.sort(key=lambda c: c["value"], reverse=True)
        self._vte_candidates = candidates

        best_val = candidates[0]["value"]
        second_val = candidates[1]["value"] if len(candidates) > 1 else 0.0

        if best_val == 0.0:
            # No information in any direction — can't deliberate
            self._is_deliberating = False
            self._vte_hesitated = False
            return self._explore()

        # Check if top two options are close enough to trigger deliberation
        if best_val > 0 and second_val / best_val >= self._vte_threshold:
            self._is_deliberating = True
            # Hesitation: sometimes pause instead of committing
            if random.random() < self._vte_hesitation_rate:
                self._vte_hesitated = True
                self._vte_chosen = "STAY"
                return Direction.STAY
        else:
            self._is_deliberating = False

        self._vte_hesitated = False
        chosen_name = candidates[0]["direction"]
        self._vte_chosen = chosen_name
        return Direction[chosen_name]

    def _update_stuck_detection(self) -> None:
        self._recent_positions.append(self.position)
        if len(self._recent_positions) >= self._stuck_window:
            unique = len(set(self._recent_positions))
            self._is_stuck = unique <= 3
        else:
            self._is_stuck = False

    def decide(self) -> Direction:
        # Reset VTE state each tick
        self._vte_candidates = []
        self._is_deliberating = False
        self._vte_chosen = ""
        self._vte_hesitated = False

        self._update_stuck_detection()

        # When stuck, bypass all stimulus-directed navigation
        if self._is_stuck:
            return self._explore_freely()

        urgent = self.drive_system.get_most_urgent()
        if urgent is None:
            # No drives active — default behavior is positive phototaxis
            light_perceptions = self._get_light_perceptions()
            if light_perceptions:
                strongest = max(
                    light_perceptions, key=lambda p: p.perceived_intensity
                )
                return self._direction_toward(strongest.stimulus.position)
            if self._passable_moves:
                return random.choice(list(self._passable_moves.keys()))
            return Direction.STAY

        target_stimulus = self._drive_to_stimulus(urgent.drive_type)
        avg_strength = self._get_avg_memory_strength(target_stimulus)

        if avg_strength >= self._vte_automaticity:
            # Well-learned: skip deliberation, navigate directly
            remembered_pos = self.memory_system.get_best_location_for(
                target_stimulus, self._grid_size[0], self._grid_size[1]
            )
            if remembered_pos is not None and remembered_pos != self.position:
                direction = self._navigate_toward(remembered_pos)
            else:
                direction = self._explore()
        elif avg_strength > 0:
            # Weak/moderate memories: deliberate (VTE)
            direction = self._deliberate(target_stimulus)
        else:
            # No memories at all: pure exploration
            direction = self._explore()

        return self._apply_phototaxis(direction)

    def _navigate_toward(self, target: tuple[int, int]) -> Direction:
        path = self.memory_system.find_path(self.position, target)
        if path is not None and len(path) >= 2:
            next_pos = path[1]
            dx = next_pos[0] - self.position[0]
            dy = next_pos[1] - self.position[1]
            if abs(dx) >= abs(dy):
                d = Direction.EAST if dx > 0 else Direction.WEST
            else:
                d = Direction.SOUTH if dy > 0 else Direction.NORTH
            # Path cell should be passable, but verify
            if d in self._passable_moves:
                return d
        return self._direction_toward(target)

    def get_state(self) -> dict:
        state = super().get_state()
        state["vte"] = {
            "is_deliberating": self._is_deliberating,
            "candidates": self._vte_candidates,
            "chosen": self._vte_chosen,
            "hesitated": self._vte_hesitated,
        }
        state["resource_consumptions"] = self._resource_consumptions
        state["is_stuck"] = self._is_stuck
        return state

    def post_act(self, environment: Environment) -> None:
        """Called after acting — updates drives, memory, and expectations."""
        self.drive_system.update()

        stimuli_here = environment.get_stimuli_at(self.position)

        # Evaluate predictions BEFORE recording new experiences, so we
        # compare against what the bug expected from prior visits.
        CONSUMABLE = {
            StimulusType.FOOD: DriveType.HUNGER,
            StimulusType.WATER: DriveType.THIRST,
            StimulusType.HEAT: DriveType.TEMPERATURE,
        }

        for pos, entries in list(self.memory_system.cognitive_map.items()):
            if pos == self.position:
                for entry in entries:
                    actual_stim = [
                        s
                        for s in stimuli_here
                        if s.stimulus_type == entry.stimulus_type
                    ]
                    if actual_stim:
                        # Compute actual reward from current drive state
                        drive_type = CONSUMABLE.get(entry.stimulus_type)
                        if drive_type is not None and self.drive_system.get_level(drive_type) > 0.1:
                            actual_reward = 1.0
                        else:
                            actual_reward = 0.0
                        self.memory_system.update_expectation(
                            pos,
                            entry.stimulus_type,
                            actual_stim[0].intensity,
                            actual_reward,
                        )
                    else:
                        self.memory_system.update_expectation(
                            pos, entry.stimulus_type, 0.0, 0.0
                        )

        for stimulus in stimuli_here:
            drive_type = CONSUMABLE.get(stimulus.stimulus_type)
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
            if actual > 0:
                self._resource_consumptions += 1
            self.memory_system.record_experience(
                self.position, stimulus.stimulus_type, stimulus.intensity, 1.0
            )

        self.memory_system.decay()
        self.memory_system.record_visit(self.position)
