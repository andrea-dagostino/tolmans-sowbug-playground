from abc import ABC, abstractmethod

from some_sim.core.environment import Environment
from some_sim.systems.drives import DriveSystem
from some_sim.systems.memory import MemorySystem
from some_sim.systems.motor import Direction, MotorSystem
from some_sim.systems.sensors import Perception, SensorSystem


class Agent(ABC):
    def __init__(
        self,
        position: tuple[int, int],
        orientation: Direction,
        drive_system: DriveSystem,
        sensor_system: SensorSystem,
        memory_system: MemorySystem,
        motor_system: MotorSystem,
    ) -> None:
        self.position = position
        self.orientation = orientation
        self.drive_system = drive_system
        self.sensor_system = sensor_system
        self.memory_system = memory_system
        self.motor_system = motor_system
        self.current_perceptions: list[Perception] = []

    def perceive(self, environment: Environment) -> None:
        self.current_perceptions = self.sensor_system.perceive(
            self.position, environment
        )

    @abstractmethod
    def decide(self) -> Direction:
        ...

    def act(self, direction: Direction, environment: Environment) -> None:
        old_position = self.position
        self.position = self.motor_system.move(
            self.position, direction, environment
        )
        self.orientation = direction
        if self.position != old_position:
            self.memory_system.record_traversal(old_position, self.position)

    def get_state(self) -> dict:
        return {
            "position": self.position,
            "orientation": self.orientation.name,
            "drive_levels": self.drive_system.get_levels(),
            "perception_count": len(self.current_perceptions),
            "perception_radius": self.sensor_system.perception_radius,
            "perceptions": [
                {
                    "stimulus_type": p.stimulus.stimulus_type.value,
                    "stimulus_position": list(p.stimulus.position),
                    "perceived_intensity": round(p.perceived_intensity, 3),
                    "distance": round(p.distance, 3),
                    "direction": list(p.direction),
                }
                for p in self.current_perceptions
            ],
            "cognitive_map": {
                f"{pos[0]},{pos[1]}": [
                    {
                        "stimulus_type": entry.stimulus_type.value,
                        "expected_intensity": round(entry.expected_intensity, 3),
                        "reward_value": round(entry.reward_value, 3),
                        "strength": round(entry.strength, 3),
                    }
                    for entry in entries
                ]
                for pos, entries in self.memory_system.cognitive_map.items()
            },
            "cognitive_map_edges": [
                {
                    "from": list(edge_key[0]),
                    "to": list(edge_key[1]),
                    "count": count,
                }
                for edge_key, count in self.memory_system.edges.items()
            ],
            "visited_cells": {
                f"{pos[0]},{pos[1]}": round(familiarity, 3)
                for pos, familiarity in self.memory_system.visited.items()
            },
            "density_field": self._compute_density_state(),
        }

    def _compute_density_state(self) -> dict[str, float]:
        if self.memory_system.kernel_bandwidth <= 0:
            return {}
        grid_w, grid_h = getattr(self, "_grid_size", (20, 20))
        field = self.memory_system.compute_density_field(grid_w, grid_h)
        max_val = field.max()
        if max_val == 0:
            return {}
        normalized = field / max_val
        result: dict[str, float] = {}
        for y in range(grid_h):
            for x in range(grid_w):
                val = float(normalized[y, x])
                if val > 0.01:
                    result[f"{x},{y}"] = round(val, 3)
        return result
