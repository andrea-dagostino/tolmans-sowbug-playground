from dataclasses import dataclass, field

from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType


@dataclass
class Environment:
    width: int
    height: int
    stimuli: list[Stimulus] = field(default_factory=list)

    def add_stimulus(self, stimulus: Stimulus) -> None:
        self.stimuli.append(stimulus)

    def remove_stimulus(self, stimulus: Stimulus) -> None:
        self.stimuli.remove(stimulus)

    def get_stimuli_at(self, position: tuple[int, int]) -> list[Stimulus]:
        return [s for s in self.stimuli if s.position == position]

    def get_stimuli_in_radius(
        self, position: tuple[int, int], radius: float
    ) -> list[tuple[Stimulus, float]]:
        results = []
        for s in self.stimuli:
            dist = s.distance_to(position)
            if dist <= radius:
                results.append((s, dist))
        return results

    def is_within_bounds(self, position: tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def is_passable(self, position: tuple[int, int]) -> bool:
        for s in self.stimuli:
            if s.position == position and s.stimulus_type == StimulusType.OBSTACLE:
                return False
        return True

    def update(self) -> None:
        to_remove = []
        for s in self.stimuli:
            if s.depletes and getattr(s, "_consumed", False):
                s.intensity -= s.depletion_rate
                s._consumed = False
                if s.intensity <= 0.0:
                    to_remove.append(s)
        for s in to_remove:
            self.stimuli.remove(s)
