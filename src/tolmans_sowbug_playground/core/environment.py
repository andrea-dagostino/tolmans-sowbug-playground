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

    def has_line_of_sight(
        self, start: tuple[int, int], end: tuple[int, int]
    ) -> bool:
        """Bresenham line check — returns False if any intermediate cell is an obstacle."""
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        err = dx - dy

        # Collect obstacle positions for fast lookup
        obstacles = {
            s.position
            for s in self.stimuli
            if s.stimulus_type == StimulusType.OBSTACLE
        }

        x, y = x0, y0
        while (x, y) != (x1, y1):
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
            # Skip the end cell — only check intermediate cells
            if (x, y) != (x1, y1) and (x, y) in obstacles:
                return False
        return True

    def update(self) -> None:
        self.stimuli = [s for s in self.stimuli if not s.depleted]
