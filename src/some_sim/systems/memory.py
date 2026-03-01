from collections import deque
from dataclasses import dataclass

import numpy as np

from some_sim.core.stimulus import StimulusType


@dataclass
class MemoryEntry:
    stimulus_type: StimulusType
    expected_intensity: float
    reward_value: float
    strength: float = 1.0


class MemorySystem:
    def __init__(
        self,
        learning_rate: float = 0.1,
        decay_rate: float = 0.01,
        kernel_bandwidth: float = 2.0,
    ) -> None:
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.kernel_bandwidth = kernel_bandwidth
        self.cognitive_map: dict[tuple[int, int], list[MemoryEntry]] = {}
        self.edges: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}
        self.visited: dict[tuple[int, int], float] = {}

    def record_experience(
        self,
        position: tuple[int, int],
        stimulus_type: StimulusType,
        intensity: float,
        reward: float,
    ) -> None:
        if position not in self.cognitive_map:
            self.cognitive_map[position] = []
        for entry in self.cognitive_map[position]:
            if entry.stimulus_type == stimulus_type:
                entry.expected_intensity = intensity
                entry.reward_value = reward
                entry.strength = 1.0
                return
        self.cognitive_map[position].append(
            MemoryEntry(
                stimulus_type=stimulus_type,
                expected_intensity=intensity,
                reward_value=reward,
                strength=1.0,
            )
        )

    def record_traversal(
        self, from_pos: tuple[int, int], to_pos: tuple[int, int]
    ) -> None:
        key = (from_pos, to_pos)
        self.edges[key] = self.edges.get(key, 0) + 1

    def get_expected(
        self, position: tuple[int, int], stimulus_type: StimulusType
    ) -> MemoryEntry | None:
        entries = self.cognitive_map.get(position, [])
        for entry in entries:
            if entry.stimulus_type == stimulus_type:
                return entry
        return None

    def compute_density_field(
        self,
        grid_width: int,
        grid_height: int,
        stimulus_type: StimulusType | None = None,
    ) -> np.ndarray:
        field = np.zeros((grid_height, grid_width))
        points: list[tuple[int, int, float]] = []
        for pos, entries in self.cognitive_map.items():
            for entry in entries:
                if stimulus_type is not None and entry.stimulus_type != stimulus_type:
                    continue
                weight = entry.reward_value * entry.strength
                if weight > 0:
                    points.append((pos[0], pos[1], weight))
        if not points:
            return field
        sigma = self.kernel_bandwidth
        if sigma <= 0:
            for px, py, w in points:
                if 0 <= px < grid_width and 0 <= py < grid_height:
                    field[py, px] += w
            return field
        xs = np.arange(grid_width)
        ys = np.arange(grid_height)
        gx, gy = np.meshgrid(xs, ys)
        for px, py, w in points:
            dist_sq = (gx - px) ** 2 + (gy - py) ** 2
            field += w * np.exp(-dist_sq / (2 * sigma**2))
        return field

    def get_best_location_for(
        self,
        stimulus_type: StimulusType,
        grid_width: int = 20,
        grid_height: int = 20,
    ) -> tuple[int, int] | None:
        if self.kernel_bandwidth <= 0:
            best_pos = None
            best_score = -1.0
            for pos, entries in self.cognitive_map.items():
                for entry in entries:
                    if entry.stimulus_type == stimulus_type:
                        score = entry.reward_value * entry.strength
                        if score > best_score:
                            best_score = score
                            best_pos = pos
            return best_pos
        field = self.compute_density_field(grid_width, grid_height, stimulus_type)
        max_val = field.max()
        if max_val == 0:
            return None
        flat_idx = int(np.argmax(field))
        row, col = np.unravel_index(flat_idx, field.shape)
        return (int(col), int(row))

    def record_visit(self, position: tuple[int, int]) -> None:
        self.visited[position] = 1.0

    def find_path(
        self, start: tuple[int, int], goal: tuple[int, int]
    ) -> list[tuple[int, int]] | None:
        if start not in self.visited or goal not in self.visited:
            return None
        if start == goal:
            return [start]
        queue = deque([(start, [start])])
        seen = {start}
        while queue:
            current, path = queue.popleft()
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor in self.visited and neighbor not in seen:
                    new_path = path + [neighbor]
                    if neighbor == goal:
                        return new_path
                    seen.add(neighbor)
                    queue.append((neighbor, new_path))
        return None

    def update_expectation(
        self,
        position: tuple[int, int],
        stimulus_type: StimulusType,
        actual_intensity: float,
        actual_reward: float,
    ) -> None:
        entry = self.get_expected(position, stimulus_type)
        if entry is None:
            return
        entry.expected_intensity += self.learning_rate * (
            actual_intensity - entry.expected_intensity
        )
        entry.reward_value += self.learning_rate * (
            actual_reward - entry.reward_value
        )
        intensity_error = abs(actual_intensity - entry.expected_intensity)
        reward_error = abs(actual_reward - entry.reward_value)
        avg_error = (intensity_error + reward_error) / 2.0
        if avg_error < 0.2:
            entry.strength = min(1.0, entry.strength + self.learning_rate * 0.5)
        else:
            entry.strength = max(0.0, entry.strength - avg_error * self.learning_rate)

    def decay(self) -> None:
        positions_to_clean = []
        for pos, entries in self.cognitive_map.items():
            to_remove = []
            for entry in entries:
                entry.strength -= self.decay_rate
                if entry.strength < 0.01:
                    to_remove.append(entry)
            for entry in to_remove:
                entries.remove(entry)
            if not entries:
                positions_to_clean.append(pos)
        for pos in positions_to_clean:
            del self.cognitive_map[pos]

        visited_to_remove = []
        for pos in self.visited:
            self.visited[pos] -= self.decay_rate
            if self.visited[pos] < 0.01:
                visited_to_remove.append(pos)
        for pos in visited_to_remove:
            del self.visited[pos]
