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
        }
