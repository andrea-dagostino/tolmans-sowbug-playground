from dataclasses import dataclass

from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import Stimulus


@dataclass
class Perception:
    stimulus: Stimulus
    perceived_intensity: float
    distance: float
    direction: tuple[int, int]


class SensorSystem:
    def __init__(self, perception_radius: float = 5.0) -> None:
        self.perception_radius = perception_radius

    def perceive(
        self, position: tuple[int, int], environment: Environment
    ) -> list[Perception]:
        stimuli_in_range = environment.get_stimuli_in_radius(
            position, self.perception_radius
        )
        perceptions = []
        for stimulus, distance in stimuli_in_range:
            perceived_intensity = stimulus.perceived_intensity_at(position)
            direction = (
                stimulus.position[0] - position[0],
                stimulus.position[1] - position[1],
            )
            perceptions.append(
                Perception(
                    stimulus=stimulus,
                    perceived_intensity=perceived_intensity,
                    distance=distance,
                    direction=direction,
                )
            )
        return perceptions
