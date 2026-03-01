from some_sim.core.stimulus import StimulusType
from some_sim.systems.memory import MemoryEntry, MemorySystem


class TestMemoryEntry:
    def test_creation(self):
        entry = MemoryEntry(
            stimulus_type=StimulusType.FOOD,
            expected_intensity=0.8,
            reward_value=1.0,
        )
        assert entry.stimulus_type == StimulusType.FOOD
        assert entry.expected_intensity == 0.8
        assert entry.reward_value == 1.0
        assert entry.strength == 1.0


class TestMemorySystem:
    def test_record_and_retrieve_experience(self):
        mem = MemorySystem()
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry is not None
        assert entry.expected_intensity == 0.8
        assert entry.reward_value == 1.0

    def test_get_expected_returns_none_for_unknown(self):
        mem = MemorySystem()
        assert mem.get_expected((5, 5), StimulusType.FOOD) is None

    def test_record_traversal(self):
        mem = MemorySystem()
        mem.record_traversal((0, 0), (1, 0))
        mem.record_traversal((0, 0), (1, 0))
        assert mem.edges[((0, 0), (1, 0))] == 2

    def test_get_best_location_for_stimulus(self):
        mem = MemorySystem()
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.record_experience((3, 3), StimulusType.FOOD, intensity=0.5, reward=0.5)
        best = mem.get_best_location_for(StimulusType.FOOD)
        assert best == (5, 5)

    def test_get_best_location_returns_none_when_empty(self):
        mem = MemorySystem()
        assert mem.get_best_location_for(StimulusType.FOOD) is None

    def test_update_expectation_strengthens_on_match(self):
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        initial_strength = mem.get_expected((5, 5), StimulusType.FOOD).strength
        mem.update_expectation((5, 5), StimulusType.FOOD, actual_intensity=0.8, actual_reward=1.0)
        updated = mem.get_expected((5, 5), StimulusType.FOOD)
        assert updated.strength >= initial_strength

    def test_update_expectation_weakens_on_mismatch(self):
        mem = MemorySystem(learning_rate=0.5)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, actual_intensity=0.0, actual_reward=0.0)
        updated = mem.get_expected((5, 5), StimulusType.FOOD)
        assert updated.strength < 1.0

    def test_decay_reduces_strength(self):
        mem = MemorySystem(decay_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.decay()
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry is not None
        assert entry.strength == 0.9

    def test_decay_removes_weak_entries(self):
        mem = MemorySystem(decay_rate=0.5)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.cognitive_map[(5, 5)][0].strength = 0.005
        mem.decay()
        assert mem.get_expected((5, 5), StimulusType.FOOD) is None

    def test_update_expectation_adjusts_values(self):
        mem = MemorySystem(learning_rate=0.5)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, actual_intensity=0.4, actual_reward=0.6)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert abs(entry.expected_intensity - 0.6) < 1e-9  # 0.8 + 0.5*(0.4-0.8) = 0.6
        assert abs(entry.reward_value - 0.8) < 1e-9  # 1.0 + 0.5*(0.6-1.0) = 0.8
