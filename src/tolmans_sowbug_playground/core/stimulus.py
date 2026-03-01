import math
from dataclasses import dataclass


from enum import Enum


class StimulusType(Enum):
    FOOD = "food"
    WATER = "water"
    LIGHT = "light"
    HEAT = "heat"
    OBSTACLE = "obstacle"


@dataclass
class Stimulus:
    stimulus_type: StimulusType
    position: tuple[int, int]
    intensity: float
    radius: float
    quantity: float | None = None

    def __post_init__(self) -> None:
        self._initial_intensity: float = self.intensity
        self._initial_quantity: float | None = self.quantity

    def consume(self, amount: float) -> float:
        if self.quantity is None:
            return amount
        actual = min(amount, self.quantity)
        self.quantity -= actual
        if self._initial_quantity and self._initial_quantity > 0:
            self.intensity = self._initial_intensity * (self.quantity / self._initial_quantity)
        return actual

    @property
    def depleted(self) -> bool:
        return self.quantity is not None and self.quantity <= 0

    def distance_to(self, position: tuple[int, int]) -> float:
        dx = self.position[0] - position[0]
        dy = self.position[1] - position[1]
        return math.sqrt(dx * dx + dy * dy)

    def perceived_intensity_at(self, position: tuple[int, int]) -> float:
        dist = self.distance_to(position)
        if dist >= self.radius:
            return 0.0
        return self.intensity * (1.0 - dist / self.radius)
