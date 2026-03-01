from dataclasses import dataclass

from some_sim.core.stimulus import StimulusType


@dataclass
class MemoryEntry:
    stimulus_type: StimulusType
    expected_intensity: float
    reward_value: float
    strength: float = 1.0


class MemorySystem:
    def __init__(
        self, learning_rate: float = 0.1, decay_rate: float = 0.01
    ) -> None:
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.cognitive_map: dict[tuple[int, int], list[MemoryEntry]] = {}
        self.edges: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}

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

    def get_best_location_for(
        self, stimulus_type: StimulusType
    ) -> tuple[int, int] | None:
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
