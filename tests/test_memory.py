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


class TestSpatialLearning:
    def test_record_visit_creates_entry(self):
        mem = MemorySystem()
        mem.record_visit((3, 4))
        assert (3, 4) in mem.visited
        assert mem.visited[(3, 4)] == 1.0

    def test_record_visit_refreshes_familiarity(self):
        mem = MemorySystem(decay_rate=0.1)
        mem.record_visit((3, 4))
        mem.decay()
        assert mem.visited[(3, 4)] < 1.0
        mem.record_visit((3, 4))
        assert mem.visited[(3, 4)] == 1.0

    def test_decay_removes_forgotten_cells(self):
        mem = MemorySystem(decay_rate=0.5)
        mem.record_visit((3, 4))
        mem.visited[(3, 4)] = 0.005
        mem.decay()
        assert (3, 4) not in mem.visited

    def test_decay_reduces_familiarity(self):
        mem = MemorySystem(decay_rate=0.1)
        mem.record_visit((3, 4))
        mem.decay()
        assert mem.visited[(3, 4)] == 0.9

    def test_visited_independent_of_cognitive_map(self):
        mem = MemorySystem()
        mem.record_visit((3, 4))
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        assert (3, 4) in mem.visited
        assert (3, 4) not in mem.cognitive_map
        assert (5, 5) in mem.cognitive_map
        assert (5, 5) not in mem.visited


class TestPathfinding:
    def test_find_path_simple_line(self):
        mem = MemorySystem()
        for x in range(5):
            mem.record_visit((x, 0))
        path = mem.find_path((0, 0), (4, 0))
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (4, 0)
        assert len(path) == 5

    def test_find_path_returns_none_for_disconnected(self):
        mem = MemorySystem()
        mem.record_visit((0, 0))
        mem.record_visit((5, 5))
        assert mem.find_path((0, 0), (5, 5)) is None

    def test_find_path_returns_none_when_start_not_visited(self):
        mem = MemorySystem()
        mem.record_visit((1, 0))
        assert mem.find_path((0, 0), (1, 0)) is None

    def test_find_path_returns_none_when_goal_not_visited(self):
        mem = MemorySystem()
        mem.record_visit((0, 0))
        assert mem.find_path((0, 0), (1, 0)) is None

    def test_find_path_same_start_and_goal(self):
        mem = MemorySystem()
        mem.record_visit((3, 3))
        path = mem.find_path((3, 3), (3, 3))
        assert path == [(3, 3)]

    def test_find_path_uses_bidirectional_edges(self):
        mem = MemorySystem()
        mem.record_visit((0, 0))
        mem.record_visit((1, 0))
        # Can go from (0,0) to (1,0) and back
        assert mem.find_path((0, 0), (1, 0)) is not None
        assert mem.find_path((1, 0), (0, 0)) is not None

    def test_find_path_chooses_shortest(self):
        mem = MemorySystem()
        # L-shaped path: (0,0)->(1,0)->(2,0)->(2,1)->(2,2)
        for x in range(3):
            mem.record_visit((x, 0))
        for y in range(3):
            mem.record_visit((2, y))
        # Also add direct path: (0,0)->(0,1)->(0,2)->(1,2)->(2,2)
        for y in range(3):
            mem.record_visit((0, y))
        mem.record_visit((1, 2))
        path = mem.find_path((0, 0), (2, 2))
        assert path is not None
        assert len(path) == 5  # BFS finds shortest: 5 steps either way

    def test_find_path_excludes_forgotten_cells(self):
        mem = MemorySystem(decay_rate=0.5)
        for x in range(5):
            mem.record_visit((x, 0))
        # Forget the middle cell
        mem.visited[(2, 0)] = 0.005
        mem.decay()
        assert (2, 0) not in mem.visited
        assert mem.find_path((0, 0), (4, 0)) is None
