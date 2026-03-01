import random

from some_sim.core.agent import Agent
from some_sim.core.environment import Environment
from some_sim.core.stimulus import StimulusType
from some_sim.systems.drives import Drive, DriveSystem, DriveType
from some_sim.systems.memory import MemorySystem
from some_sim.systems.motor import Direction, MotorSystem
from some_sim.systems.sensors import Perception, SensorSystem

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
    ) -> None:
        drive_system = DriveSystem(
            drives=[
                Drive(DriveType.HUNGER, rate=hunger_rate),
                Drive(DriveType.THIRST, rate=thirst_rate),
                Drive(DriveType.TEMPERATURE, rate=temperature_rate),
            ]
        )
        super().__init__(
            position=position,
            orientation=Direction.NORTH,
            drive_system=drive_system,
            sensor_system=SensorSystem(perception_radius=perception_radius),
            memory_system=MemorySystem(
                learning_rate=learning_rate, decay_rate=decay_rate
            ),
            motor_system=MotorSystem(),
        )

    def _drive_to_stimulus(self, drive_type: DriveType) -> StimulusType:
        return DRIVE_STIMULUS_MAP[drive_type]

    def _direction_toward(self, target: tuple[int, int]) -> Direction:
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        if abs(dx) >= abs(dy):
            return Direction.EAST if dx > 0 else Direction.WEST
        else:
            return Direction.SOUTH if dy > 0 else Direction.NORTH

    def _get_light_perceptions(self) -> list[Perception]:
        return [
            p
            for p in self.current_perceptions
            if p.stimulus.stimulus_type == StimulusType.LIGHT
        ]

    def _apply_aversion(self, preferred: Direction) -> Direction:
        light_perceptions = self._get_light_perceptions()
        if not light_perceptions:
            return preferred

        strongest = max(light_perceptions, key=lambda p: p.perceived_intensity)
        light_dir = (
            1 if strongest.direction[0] > 0 else (-1 if strongest.direction[0] < 0 else 0),
            1 if strongest.direction[1] > 0 else (-1 if strongest.direction[1] < 0 else 0),
        )

        preferred_delta = preferred.value
        moves_toward_light = (
            (preferred_delta[0] != 0 and preferred_delta[0] == light_dir[0])
            or (preferred_delta[1] != 0 and preferred_delta[1] == light_dir[1])
        )

        if moves_toward_light:
            alternatives = [d for d in MOVE_DIRECTIONS if d != preferred]
            for alt in alternatives:
                alt_delta = alt.value
                toward = (
                    (alt_delta[0] != 0 and alt_delta[0] == light_dir[0])
                    or (alt_delta[1] != 0 and alt_delta[1] == light_dir[1])
                )
                if not toward:
                    return alt
            return Direction.STAY

        return preferred

    def _explore(self) -> Direction:
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

        return random.choice(MOVE_DIRECTIONS)

    def decide(self) -> Direction:
        urgent = self.drive_system.get_most_urgent()
        if urgent is None:
            direction = random.choice(MOVE_DIRECTIONS)
            return self._apply_aversion(direction)

        target_stimulus = self._drive_to_stimulus(urgent.drive_type)

        remembered_pos = self.memory_system.get_best_location_for(target_stimulus)
        if remembered_pos is not None and remembered_pos != self.position:
            direction = self._navigate_toward(remembered_pos)
        else:
            direction = self._explore()

        return self._apply_aversion(direction)

    def _navigate_toward(self, target: tuple[int, int]) -> Direction:
        path = self.memory_system.find_path(self.position, target)
        if path is not None and len(path) >= 2:
            next_pos = path[1]
            dx = next_pos[0] - self.position[0]
            dy = next_pos[1] - self.position[1]
            if abs(dx) >= abs(dy):
                return Direction.EAST if dx > 0 else Direction.WEST
            else:
                return Direction.SOUTH if dy > 0 else Direction.NORTH
        return self._direction_toward(target)

    def post_act(self, environment: Environment) -> None:
        """Called after acting — updates drives, memory, and expectations."""
        self.drive_system.update()

        stimuli_here = environment.get_stimuli_at(self.position)
        for stimulus in stimuli_here:
            reward = 0.0
            if (
                stimulus.stimulus_type == StimulusType.FOOD
                and self.drive_system.get_level(DriveType.HUNGER) > 0.1
            ):
                self.drive_system.satisfy(DriveType.HUNGER, 0.3)
                reward = 1.0
                stimulus._consumed = True
            elif (
                stimulus.stimulus_type == StimulusType.WATER
                and self.drive_system.get_level(DriveType.THIRST) > 0.1
            ):
                self.drive_system.satisfy(DriveType.THIRST, 0.3)
                reward = 1.0
                stimulus._consumed = True

            self.memory_system.record_experience(
                self.position,
                stimulus.stimulus_type,
                stimulus.intensity,
                reward,
            )

        for pos, entries in list(self.memory_system.cognitive_map.items()):
            if pos == self.position:
                for entry in entries:
                    actual_stim = [
                        s
                        for s in stimuli_here
                        if s.stimulus_type == entry.stimulus_type
                    ]
                    if actual_stim:
                        self.memory_system.update_expectation(
                            pos,
                            entry.stimulus_type,
                            actual_stim[0].intensity,
                            entry.reward_value,
                        )
                    else:
                        self.memory_system.update_expectation(
                            pos, entry.stimulus_type, 0.0, 0.0
                        )

        self.memory_system.decay()
        self.memory_system.record_visit(self.position)
