import numpy as np

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


class TestEstimateValue:
    def test_returns_zero_for_unvisited_position(self):
        mem = MemorySystem()
        assert mem.estimate_value((5, 5), StimulusType.FOOD) == 0.0

    def test_returns_reward_at_visited_position_with_memory(self):
        mem = MemorySystem()
        mem.record_visit((5, 5))
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        val = mem.estimate_value((5, 5), StimulusType.FOOD)
        assert val == 1.0  # reward * strength = 1.0 * 1.0, discount^0 = 1.0

    def test_discounts_distant_memories(self):
        mem = MemorySystem()
        for x in range(4):
            mem.record_visit((x, 0))
        mem.record_experience((3, 0), StimulusType.FOOD, intensity=0.8, reward=1.0)
        val = mem.estimate_value((0, 0), StimulusType.FOOD, discount=0.9)
        expected = 0.9 ** 3 * 1.0  # 3 steps away
        assert abs(val - expected) < 1e-9

    def test_accumulates_multiple_memories(self):
        mem = MemorySystem()
        for x in range(3):
            mem.record_visit((x, 0))
            mem.record_experience((x, 0), StimulusType.FOOD, intensity=0.8, reward=0.5)
        val = mem.estimate_value((0, 0), StimulusType.FOOD, discount=0.9)
        expected = 0.5 + 0.9 * 0.5 + 0.81 * 0.5
        assert abs(val - expected) < 1e-9

    def test_respects_horizon(self):
        mem = MemorySystem()
        for x in range(10):
            mem.record_visit((x, 0))
        mem.record_experience((8, 0), StimulusType.FOOD, intensity=0.8, reward=1.0)
        val_short = mem.estimate_value((0, 0), StimulusType.FOOD, horizon=3)
        val_long = mem.estimate_value((0, 0), StimulusType.FOOD, horizon=10)
        assert val_short == 0.0  # food at distance 8, horizon 3 can't reach
        assert val_long > 0.0

    def test_filters_by_stimulus_type(self):
        mem = MemorySystem()
        mem.record_visit((5, 5))
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.record_experience((5, 5), StimulusType.WATER, intensity=0.9, reward=0.8)
        food_val = mem.estimate_value((5, 5), StimulusType.FOOD)
        water_val = mem.estimate_value((5, 5), StimulusType.WATER)
        assert food_val == 1.0
        assert abs(water_val - 0.8) < 1e-9

    def test_weights_by_strength(self):
        mem = MemorySystem()
        mem.record_visit((5, 5))
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.cognitive_map[(5, 5)][0].strength = 0.5
        val = mem.estimate_value((5, 5), StimulusType.FOOD)
        assert abs(val - 0.5) < 1e-9  # reward * strength = 1.0 * 0.5

    def test_higher_value_toward_food(self):
        """Direction with food should have higher estimated value."""
        mem = MemorySystem()
        # Path east: (5,5) -> (6,5) -> (7,5) with food at (7,5)
        for x in range(5, 8):
            mem.record_visit((x, 0))
        mem.record_experience((7, 0), StimulusType.FOOD, intensity=1.0, reward=1.0)
        # Path west: (5,5) -> (4,5) -> (3,5), no food
        for x in range(3, 6):
            mem.record_visit((x, 0))
        val_east = mem.estimate_value((6, 0), StimulusType.FOOD)
        val_west = mem.estimate_value((4, 0), StimulusType.FOOD)
        assert val_east > val_west


class TestDensityField:
    def test_density_field_empty_map_returns_zeros(self):
        mem = MemorySystem()
        field = mem.compute_density_field(10, 10)
        assert field.shape == (10, 10)
        assert np.all(field == 0)

    def test_density_field_single_point_peak_at_source(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field = mem.compute_density_field(10, 10)
        peak_idx = np.unravel_index(np.argmax(field), field.shape)
        assert peak_idx == (5, 5)  # (row, col) = (y, x)

    def test_density_field_single_point_decays_with_distance(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field = mem.compute_density_field(10, 10)
        assert field[5, 5] > field[5, 6]
        assert field[5, 6] > field[5, 8]

    def test_density_field_bandwidth_affects_spread(self):
        mem_narrow = MemorySystem(kernel_bandwidth=1.0)
        mem_narrow.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field_narrow = mem_narrow.compute_density_field(10, 10)

        mem_wide = MemorySystem(kernel_bandwidth=3.0)
        mem_wide.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field_wide = mem_wide.compute_density_field(10, 10)

        # Both peak at same value (exp(0)=1), but narrow drops off faster
        ratio_narrow = field_narrow[5, 8] / field_narrow[5, 5]
        ratio_wide = field_wide[5, 8] / field_wide[5, 5]
        assert ratio_wide > ratio_narrow
        # At a distant point, wide bandwidth has higher absolute value
        assert field_wide[5, 8] > field_narrow[5, 8]

    def test_density_field_combined_all_types(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((3, 3), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.record_experience((7, 7), StimulusType.WATER, intensity=0.9, reward=0.8)
        field = mem.compute_density_field(10, 10, stimulus_type=None)
        assert field[3, 3] > 0
        assert field[7, 7] > 0

    def test_density_field_filtered_by_type(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((3, 3), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.record_experience((7, 7), StimulusType.WATER, intensity=0.9, reward=0.8)
        food_field = mem.compute_density_field(10, 10, stimulus_type=StimulusType.FOOD)
        water_field = mem.compute_density_field(10, 10, stimulus_type=StimulusType.WATER)
        assert food_field[3, 3] > 0
        assert food_field[7, 7] < food_field[3, 3]
        assert water_field[7, 7] > 0
        assert water_field[3, 3] < water_field[7, 7]

    def test_density_field_weight_is_reward_times_strength(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=0.5)
        field1 = mem.compute_density_field(10, 10)
        peak1 = field1[5, 5]

        mem2 = MemorySystem(kernel_bandwidth=2.0)
        mem2.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field2 = mem2.compute_density_field(10, 10)
        peak2 = field2[5, 5]

        assert abs(peak2 - 2 * peak1) < 1e-9

    def test_density_field_zero_bandwidth_discrete(self):
        mem = MemorySystem(kernel_bandwidth=0)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field = mem.compute_density_field(10, 10)
        assert field[5, 5] == 1.0
        assert field[5, 6] == 0.0
        assert field[4, 5] == 0.0

    def test_density_field_zero_weight_excluded(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=0.0)
        field = mem.compute_density_field(10, 10)
        assert np.all(field == 0)

    def test_density_field_respects_grid_bounds(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((0, 0), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field = mem.compute_density_field(10, 10)
        assert field.shape == (10, 10)
        assert field[0, 0] > 0

    def test_density_field_after_decay(self):
        mem = MemorySystem(kernel_bandwidth=2.0, decay_rate=0.5)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        field_before = mem.compute_density_field(10, 10)
        mem.decay()
        field_after = mem.compute_density_field(10, 10)
        assert field_after[5, 5] < field_before[5, 5]

    def test_get_best_location_kde_returns_valid_cell(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        best = mem.get_best_location_for(StimulusType.FOOD, 10, 10)
        assert best == (5, 5)

    def test_get_best_location_kde_returns_none_when_empty(self):
        mem = MemorySystem(kernel_bandwidth=2.0)
        assert mem.get_best_location_for(StimulusType.FOOD, 10, 10) is None

    def test_get_best_location_kde_cluster_wins(self):
        """3 clustered moderate memories should outweigh 1 isolated high memory."""
        mem = MemorySystem(kernel_bandwidth=2.0)
        # Isolated high-reward point
        mem.record_experience((15, 15), StimulusType.FOOD, intensity=1.0, reward=1.0)
        # Cluster of moderate-reward points
        mem.record_experience((3, 3), StimulusType.FOOD, intensity=0.8, reward=0.5)
        mem.record_experience((4, 3), StimulusType.FOOD, intensity=0.8, reward=0.5)
        mem.record_experience((3, 4), StimulusType.FOOD, intensity=0.8, reward=0.5)
        best = mem.get_best_location_for(StimulusType.FOOD, 20, 20)
        # The cluster region should win over the isolated point
        assert best is not None
        assert abs(best[0] - 3.5) < 2 and abs(best[1] - 3.5) < 2

    def test_get_best_location_backward_compat_bandwidth_zero(self):
        """bandwidth=0 should recover exact discrete-max behavior."""
        mem = MemorySystem(kernel_bandwidth=0)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.record_experience((3, 3), StimulusType.FOOD, intensity=0.5, reward=0.5)
        best = mem.get_best_location_for(StimulusType.FOOD)
        assert best == (5, 5)
