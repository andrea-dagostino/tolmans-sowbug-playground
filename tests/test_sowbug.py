import random

from tolmans_sowbug_playground.agents.sowbug import Sowbug
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType
from tolmans_sowbug_playground.systems.drives import DriveType


class TestSowbugCreation:
    def test_default_drives(self):
        bug = Sowbug(position=(5, 5))
        levels = bug.drive_system.get_levels()
        assert DriveType.HUNGER in levels
        assert DriveType.THIRST in levels
        assert DriveType.TEMPERATURE in levels

    def test_custom_position(self):
        bug = Sowbug(position=(3, 7))
        assert bug.position == (3, 7)


class TestSowbugDecisionMaking:
    def test_moves_toward_food_when_hungry(self):
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 2), intensity=1.0, radius=8.0)
        env.add_stimulus(food)

        bug.perceive(env)
        random.seed(42)
        direction = bug.decide()
        bug.act(direction, env)
        # Bug should have moved closer to food (north, since food is at y=2)
        assert bug.position[1] <= 5

    def test_attracted_to_light_when_idle(self):
        """Positive phototaxis: sowbug moves toward light when no drives are urgent."""
        random.seed(0)
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.0
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        env = Environment(width=20, height=20)
        light = Stimulus(StimulusType.LIGHT, (5, 4), intensity=1.0, radius=5.0)
        env.add_stimulus(light)

        bug.perceive(env)
        direction = bug.decide()
        bug.act(direction, env)
        # Should move north (toward the light)
        assert bug.position[1] <= 5

    def test_drives_override_phototaxis(self):
        """High drives suppress phototaxis — agent follows food, not light."""
        random.seed(42)
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 1.0
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        env = Environment(width=20, height=20)
        # Light to the north
        light = Stimulus(StimulusType.LIGHT, (5, 2), intensity=1.0, radius=5.0)
        env.add_stimulus(light)
        # Food to the south
        food = Stimulus(StimulusType.FOOD, (5, 8), intensity=1.0, radius=8.0)
        env.add_stimulus(food)

        bug.perceive(env)
        direction = bug.decide()
        bug.act(direction, env)
        # Should move south toward food, not north toward light
        assert bug.position[1] >= 5

    def test_explores_when_no_memory(self):
        random.seed(42)
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9

        env = Environment(width=20, height=20)
        bug.perceive(env)
        direction = bug.decide()
        assert direction is not None

    def test_uses_memory_to_navigate(self):
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Plant a memory of food at (5, 2)
        bug.memory_system.record_experience(
            (5, 2), StimulusType.FOOD, intensity=1.0, reward=1.0
        )

        env = Environment(width=20, height=20)
        bug.perceive(env)
        direction = bug.decide()
        bug.act(direction, env)
        # Should move toward remembered food location (north)
        assert bug.position[1] <= 5

    def test_updates_memory_after_finding_food(self):
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9

        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0, quantity=5.0)
        env.add_stimulus(food)

        bug.perceive(env)
        bug.post_act(env)
        entry = bug.memory_system.get_expected((5, 5), StimulusType.FOOD)
        assert entry is not None


class TestSowbugSpatialLearning:
    def test_records_visited_cells(self):
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9

        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0)
        env.add_stimulus(food)

        bug.perceive(env)
        bug.post_act(env)
        assert (5, 5) in bug.memory_system.visited
        assert bug.memory_system.visited[(5, 5)] == 1.0

    def test_records_visit_on_empty_cell(self):
        bug = Sowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.post_act(env)
        assert (5, 5) in bug.memory_system.visited

    def test_uses_pathfinding_when_path_exists(self):
        bug = Sowbug(position=(0, 0))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Plant a memory of food at (2, 0)
        bug.memory_system.record_experience(
            (2, 0), StimulusType.FOOD, intensity=1.0, reward=1.0
        )
        # Create visited path: (0,0) -> (1,0) -> (2,0)
        bug.memory_system.record_visit((0, 0))
        bug.memory_system.record_visit((1, 0))
        bug.memory_system.record_visit((2, 0))

        env = Environment(width=20, height=20)
        bug.perceive(env)
        direction = bug.decide()
        bug.act(direction, env)
        # Should follow path to (1, 0) — the next step
        assert bug.position == (1, 0)


class TestSowbugKDE:
    def test_sowbug_accepts_kernel_bandwidth(self):
        bug = Sowbug(position=(5, 5), kernel_bandwidth=3.0)
        assert bug.memory_system.kernel_bandwidth == 3.0

    def test_sowbug_kde_navigation_toward_cluster(self):
        """Sowbug should navigate toward a cluster of moderate rewards."""
        bug = Sowbug(position=(10, 10), kernel_bandwidth=2.0)
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Cluster of food memories to the north-west
        bug.memory_system.record_experience(
            (8, 8), StimulusType.FOOD, intensity=0.8, reward=0.6
        )
        bug.memory_system.record_experience(
            (9, 8), StimulusType.FOOD, intensity=0.8, reward=0.6
        )
        bug.memory_system.record_experience(
            (8, 9), StimulusType.FOOD, intensity=0.8, reward=0.6
        )

        env = Environment(width=20, height=20)
        bug.perceive(env)
        direction = bug.decide()
        bug.act(direction, env)
        # Should move toward the cluster (north or west)
        assert bug.position[0] <= 10 or bug.position[1] <= 10

    def test_sowbug_passes_grid_size_to_get_best_location(self):
        bug = Sowbug(position=(5, 5), kernel_bandwidth=2.0)
        env = Environment(width=15, height=12)
        bug.perceive(env)
        assert bug._grid_size == (15, 12)


class TestSowbugVTE:
    def test_vte_params_accepted(self):
        bug = Sowbug(position=(5, 5), vte_horizon=3, vte_threshold=0.9)
        assert bug._vte_horizon == 3
        assert bug._vte_threshold == 0.9

    def test_vte_state_exported(self):
        bug = Sowbug(position=(5, 5))
        state = bug.get_state()
        assert "vte" in state
        assert "is_deliberating" in state["vte"]
        assert "candidates" in state["vte"]
        assert "chosen" in state["vte"]
        assert "hesitated" in state["vte"]

    def test_vte_triggers_with_weak_memories(self):
        """VTE should activate when memories exist but are weak."""
        bug = Sowbug(position=(5, 5), vte_threshold=0.8)
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Create weak food memories in two directions (similar values)
        bug.memory_system.record_visit((5, 5))
        bug.memory_system.record_visit((6, 5))
        bug.memory_system.record_visit((5, 4))
        bug.memory_system.record_experience(
            (6, 5), StimulusType.FOOD, intensity=0.5, reward=0.5
        )
        bug.memory_system.record_experience(
            (5, 4), StimulusType.FOOD, intensity=0.5, reward=0.5
        )
        # Weaken them below automaticity threshold
        for entries in bug.memory_system.cognitive_map.values():
            for entry in entries:
                entry.strength = 0.5

        env = Environment(width=20, height=20)
        bug.perceive(env)
        random.seed(99)  # avoid hesitation for this test
        bug.decide()

        # Should have populated VTE candidates
        assert len(bug._vte_candidates) == 4

    def test_vte_skipped_with_strong_memories(self):
        """VTE should not activate when memories are well-learned."""
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Strong memory of food
        bug.memory_system.record_experience(
            (5, 2), StimulusType.FOOD, intensity=1.0, reward=1.0
        )
        # strength defaults to 1.0 which is above automaticity threshold

        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()

        # Should NOT be deliberating (automatic navigation)
        assert bug._is_deliberating is False
        assert len(bug._vte_candidates) == 0

    def test_vte_skipped_with_no_memories(self):
        """VTE should not activate when there are no memories (pure exploration)."""
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9

        env = Environment(width=20, height=20)
        bug.perceive(env)
        random.seed(42)
        bug.decide()

        # No memories means avg_strength == 0, so explore, not VTE
        assert bug._is_deliberating is False
        assert len(bug._vte_candidates) == 0

    def test_vte_hesitation_produces_stay(self):
        """When deliberating with close options, agent sometimes stays in place."""
        bug = Sowbug(position=(5, 5), vte_threshold=0.5)
        bug._vte_hesitation_rate = 1.0  # force hesitation
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Create equal food memories in two directions
        bug.memory_system.record_visit((5, 5))
        bug.memory_system.record_visit((6, 5))
        bug.memory_system.record_visit((5, 4))
        bug.memory_system.record_experience(
            (6, 5), StimulusType.FOOD, intensity=0.8, reward=0.6
        )
        bug.memory_system.record_experience(
            (5, 4), StimulusType.FOOD, intensity=0.8, reward=0.6
        )
        for entries in bug.memory_system.cognitive_map.values():
            for entry in entries:
                entry.strength = 0.5

        env = Environment(width=20, height=20)
        bug.perceive(env)
        from tolmans_sowbug_playground.systems.motor import Direction
        direction = bug.decide()
        assert direction == Direction.STAY
        assert bug._vte_hesitated is True

    def test_vte_picks_higher_value_direction(self):
        """VTE should choose the direction with higher simulated reward."""
        bug = Sowbug(position=(5, 5), vte_threshold=0.99)
        bug._vte_hesitation_rate = 0.0  # never hesitate
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Strong food east, nothing elsewhere
        bug.memory_system.record_visit((5, 5))
        bug.memory_system.record_visit((6, 5))
        bug.memory_system.record_experience(
            (6, 5), StimulusType.FOOD, intensity=1.0, reward=1.0
        )
        # Weaken below automaticity
        bug.memory_system.cognitive_map[(6, 5)][0].strength = 0.5

        env = Environment(width=20, height=20)
        bug.perceive(env)
        direction = bug.decide()
        # East has food, should be chosen (after aversion check)
        from tolmans_sowbug_playground.systems.motor import Direction
        assert direction == Direction.EAST


class TestSowbugSatietyDecayRate:
    def test_sowbug_satiety_decay_rate_configurable(self):
        bug = Sowbug(position=(5, 5), satiety_decay_rate=0.1)
        for drive in bug.drive_system.drives.values():
            assert drive.satiety_decay_rate == 0.1

    def test_sowbug_satiety_decay_rate_default(self):
        bug = Sowbug(position=(5, 5))
        for drive in bug.drive_system.drives.values():
            assert drive.satiety_decay_rate == 0.05


class TestSowbugState:
    def test_prediction_accuracy_in_state(self):
        bug = Sowbug(position=(5, 5))
        state = bug.get_state()
        assert "prediction_accuracy" in state
        assert isinstance(state["prediction_accuracy"], float)

    def test_decision_reason_in_state(self):
        """After decide(), get_state() should include a non-empty decision_reason."""
        bug = Sowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()
        state = bug.get_state()
        assert "decision_reason" in state
        assert isinstance(state["decision_reason"], str)
        assert len(state["decision_reason"]) > 0


class TestSowbugDriveMapping:
    def test_hunger_maps_to_food(self):
        bug = Sowbug(position=(5, 5))
        assert bug._drive_to_stimulus(DriveType.HUNGER) == StimulusType.FOOD

    def test_thirst_maps_to_water(self):
        bug = Sowbug(position=(5, 5))
        assert bug._drive_to_stimulus(DriveType.THIRST) == StimulusType.WATER

    def test_temperature_maps_to_heat(self):
        bug = Sowbug(position=(5, 5))
        assert bug._drive_to_stimulus(DriveType.TEMPERATURE) == StimulusType.HEAT


class TestSowbugQuantityConsumption:
    def test_high_hunger_consumes_more_than_low_hunger(self):
        """Drive-proportional consumption: hungrier agent eats more per tick."""
        # High hunger bug
        bug_high = Sowbug(position=(5, 5), bite_size=0.3)
        bug_high.drive_system.drives[DriveType.HUNGER].level = 0.9

        env_high = Environment(width=20, height=20)
        food_high = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0, quantity=5.0)
        env_high.add_stimulus(food_high)

        bug_high.perceive(env_high)
        bug_high.post_act(env_high)
        consumed_high = 5.0 - food_high.quantity

        # Low hunger bug
        bug_low = Sowbug(position=(5, 5), bite_size=0.3)
        bug_low.drive_system.drives[DriveType.HUNGER].level = 0.2

        env_low = Environment(width=20, height=20)
        food_low = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0, quantity=5.0)
        env_low.add_stimulus(food_low)

        bug_low.perceive(env_low)
        bug_low.post_act(env_low)
        consumed_low = 5.0 - food_low.quantity

        assert consumed_high > consumed_low

    def test_stimulus_intensity_decreases_after_consumption(self):
        """Stimulus intensity scales down as quantity is consumed."""
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9

        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0, quantity=5.0)
        env.add_stimulus(food)

        initial_intensity = food.intensity
        bug.perceive(env)
        bug.post_act(env)
        assert food.intensity < initial_intensity

    def test_depleted_stimulus_removed_after_update(self):
        """Environment.update() removes stimuli whose quantity hits 0."""
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0, quantity=0.1)
        env.add_stimulus(food)

        bug = Sowbug(position=(5, 5), bite_size=1.0)
        bug.drive_system.drives[DriveType.HUNGER].level = 1.0

        bug.perceive(env)
        bug.post_act(env)
        env.update()
        assert food not in env.stimuli


class TestSowbugObstacleAvoidance:
    def test_does_not_get_stuck_behind_obstacle(self):
        """Bug should navigate around an obstacle between it and food."""
        from tolmans_sowbug_playground.systems.motor import Direction

        env = Environment(width=20, height=20)
        # Food is north of bug at (5, 2), obstacle blocks direct path at (5, 4)
        food = Stimulus(StimulusType.FOOD, (5, 2), intensity=1.0, radius=8.0)
        obstacle = Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0)
        env.add_stimulus(food)
        env.add_stimulus(obstacle)

        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        direction = bug.decide()
        # Direct path north is blocked — should NOT choose NORTH
        assert direction != Direction.NORTH
        # Should choose an alternative passable direction (EAST, WEST, or SOUTH)
        assert direction in (Direction.EAST, Direction.WEST, Direction.SOUTH)

    def test_moves_around_wall_over_multiple_ticks(self):
        """Bug should make progress toward food despite a wall of obstacles."""
        env = Environment(width=20, height=20)
        # Food at (5, 0)
        food = Stimulus(StimulusType.FOOD, (5, 0), intensity=1.0, radius=10.0)
        env.add_stimulus(food)
        # Wall of obstacles across row 3
        for x in range(3, 8):
            env.add_stimulus(
                Stimulus(StimulusType.OBSTACLE, (x, 3), intensity=1.0, radius=0.0)
            )

        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Run for enough ticks — the bug should not be stuck at starting position
        positions = set()
        for _ in range(50):
            bug.perceive(env)
            direction = bug.decide()
            bug.act(direction, env)
            bug.post_act(env)
            positions.add(bug.position)

        # Should have visited multiple cells, not stuck in place
        assert len(positions) > 3

    def test_explore_avoids_obstacles(self):
        """Exploration should only consider passable directions."""
        from tolmans_sowbug_playground.systems.motor import Direction

        env = Environment(width=20, height=20)
        # Surround bug on three sides with obstacles, leaving only SOUTH open
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0))  # NORTH
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (6, 5), intensity=1.0, radius=0.0))  # EAST
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (4, 5), intensity=1.0, radius=0.0))  # WEST

        bug = Sowbug(position=(5, 5))
        # No drives — pure exploration
        bug.drive_system.drives[DriveType.HUNGER].level = 0.0
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        direction = bug.decide()
        # Only SOUTH is passable
        assert direction == Direction.SOUTH

    def test_deliberate_skips_blocked_directions(self):
        """VTE deliberation should not consider impassable directions."""
        from tolmans_sowbug_playground.systems.motor import Direction

        env = Environment(width=20, height=20)
        # Block EAST with an obstacle
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (6, 5), intensity=1.0, radius=0.0))

        bug = Sowbug(position=(5, 5), vte_threshold=0.99)
        bug._vte_hesitation_rate = 0.0
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Strong food memory east (blocked) — weak food memory west (open)
        bug.memory_system.record_visit((5, 5))
        bug.memory_system.record_visit((6, 5))
        bug.memory_system.record_visit((4, 5))
        bug.memory_system.record_experience((6, 5), StimulusType.FOOD, intensity=1.0, reward=1.0)
        bug.memory_system.record_experience((4, 5), StimulusType.FOOD, intensity=0.5, reward=0.5)
        for entries in bug.memory_system.cognitive_map.values():
            for entry in entries:
                entry.strength = 0.5  # below automaticity, triggers VTE

        bug.perceive(env)
        direction = bug.decide()
        # EAST is blocked, so VTE should not pick it
        assert direction != Direction.EAST

    def test_escapes_long_wall(self):
        """Bug should break free from oscillation along a long wall."""
        env = Environment(width=20, height=20)
        # Food behind a wall that spans most of the grid
        food = Stimulus(StimulusType.FOOD, (10, 2), intensity=1.0, radius=12.0)
        env.add_stimulus(food)
        # Long wall at y=5, from x=0 to x=17 (gap at x=18,19)
        for x in range(18):
            env.add_stimulus(
                Stimulus(StimulusType.OBSTACLE, (x, 5), intensity=1.0, radius=0.0)
            )

        bug = Sowbug(position=(10, 7))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        positions = set()
        for _ in range(100):
            bug.perceive(env)
            direction = bug.decide()
            bug.act(direction, env)
            bug.post_act(env)
            positions.add(bug.position)

        # Should have explored well beyond a 3-cell oscillation
        assert len(positions) > 8

    def test_stuck_detection_activates(self):
        """Stuck flag should activate when bug oscillates in small area."""
        env = Environment(width=20, height=20)
        bug = Sowbug(position=(5, 5))

        # Manually simulate oscillation in recent_positions
        for pos in [(5, 5), (5, 6), (5, 5), (5, 6), (5, 5), (5, 6), (5, 5), (5, 6)]:
            bug._recent_positions.append(pos)

        bug.perceive(env)
        bug._update_stuck_detection()
        assert bug._is_stuck is True

    def test_stuck_state_exported(self):
        """Stuck state should be visible in get_state()."""
        bug = Sowbug(position=(5, 5))
        state = bug.get_state()
        assert "is_stuck" in state


class TestLineOfSight:
    def test_has_line_of_sight_clear_path(self):
        """LOS returns True when no obstacles block the line."""
        env = Environment(width=20, height=20)
        assert env.has_line_of_sight((2, 2), (8, 2)) is True

    def test_has_line_of_sight_blocked(self):
        """LOS returns False when an obstacle sits on the line."""
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (5, 2), intensity=1.0, radius=0.0))
        assert env.has_line_of_sight((2, 2), (8, 2)) is False

    def test_has_line_of_sight_obstacle_at_start_ignored(self):
        """Obstacle at the start cell does not block LOS (bug is standing there)."""
        env = Environment(width=20, height=20)
        # Obstacle right at start — should not block
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (2, 2), intensity=1.0, radius=0.0))
        assert env.has_line_of_sight((2, 2), (8, 2)) is True

    def test_has_line_of_sight_obstacle_at_end_ignored(self):
        """Obstacle at the end cell does not block LOS."""
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (8, 2), intensity=1.0, radius=0.0))
        assert env.has_line_of_sight((2, 2), (8, 2)) is True

    def test_has_line_of_sight_diagonal(self):
        """LOS works along diagonal paths."""
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (4, 4), intensity=1.0, radius=0.0))
        assert env.has_line_of_sight((2, 2), (6, 6)) is False

    def test_line_of_sight_blocks_perception_through_wall(self):
        """Food behind a wall should not be perceived."""
        env = Environment(width=20, height=20)
        # Wall at y=5
        for x in range(0, 20):
            env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (x, 5), intensity=1.0, radius=0.0))
        # Food behind wall
        food = Stimulus(StimulusType.FOOD, (10, 3), intensity=1.0, radius=12.0)
        env.add_stimulus(food)

        bug = Sowbug(position=(10, 7))
        bug.perceive(env)

        food_perceptions = [
            p for p in bug.current_perceptions
            if p.stimulus.stimulus_type == StimulusType.FOOD
        ]
        assert len(food_perceptions) == 0

    def test_line_of_sight_allows_perception_around_wall_end(self):
        """Food past the end of a wall should be perceived if LOS is clear."""
        env = Environment(width=20, height=20)
        # Short wall at y=5, only from x=3 to x=7
        for x in range(3, 8):
            env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (x, 5), intensity=1.0, radius=0.0))
        # Food at x=1 (past wall end), visible from x=1,y=7
        food = Stimulus(StimulusType.FOOD, (1, 3), intensity=1.0, radius=12.0)
        env.add_stimulus(food)

        bug = Sowbug(position=(1, 7))
        bug.perceive(env)

        food_perceptions = [
            p for p in bug.current_perceptions
            if p.stimulus.stimulus_type == StimulusType.FOOD
        ]
        assert len(food_perceptions) == 1


class TestFrustration:
    def test_frustration_increases_on_repeated_sticking(self):
        """Frustration level should escalate with each stuck episode."""
        env = Environment(width=20, height=20)
        bug = Sowbug(position=(5, 5))

        def trigger_stuck():
            """Force a stuck episode by injecting oscillating positions."""
            bug._is_stuck = False
            bug._recent_positions.clear()
            for pos in [(5, 5), (5, 6)] * 4:
                bug._recent_positions.append(pos)
            bug._update_stuck_detection()

        # First stuck episode
        trigger_stuck()
        assert bug._frustration_level == 1
        assert bug._frustration_cooldown == 6

        # Expire the cooldown and clear stuck so we can trigger again
        bug._frustration_cooldown = 0
        bug._is_stuck = False
        bug._recent_positions.clear()

        # Second stuck episode
        trigger_stuck()
        assert bug._frustration_level == 2
        assert bug._frustration_cooldown == 12

    def test_frustration_capped_at_five(self):
        """Frustration should not exceed 5."""
        env = Environment(width=20, height=20)
        bug = Sowbug(position=(5, 5))

        for _ in range(10):
            bug._is_stuck = False
            bug._recent_positions.clear()
            for pos in [(5, 5), (5, 6)] * 4:
                bug._recent_positions.append(pos)
            bug._update_stuck_detection()
            bug._frustration_cooldown = 0

        assert bug._frustration_level <= 5

    def test_frustration_suppresses_stimulus_targeting(self):
        """During frustration cooldown, the bug should explore instead of
        targeting food through a wall."""
        from tolmans_sowbug_playground.systems.motor import Direction

        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (10, 3), intensity=1.0, radius=12.0)
        env.add_stimulus(food)

        bug = Sowbug(position=(10, 7))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        # Set frustration cooldown directly
        bug._frustration_level = 2
        bug._frustration_cooldown = 10

        bug.perceive(env)
        direction = bug.decide()

        # During cooldown the bug explores freely — it should NOT beeline north
        # toward food. Exploration picks least-familiar passable directions.
        # We just verify the frustration cooldown path was taken (cooldown ticked down).
        assert bug._frustration_cooldown == 9  # ticked down from 10

    def test_frustration_state_exported(self):
        """Frustration level and cooldown should appear in get_state()."""
        bug = Sowbug(position=(5, 5))
        bug._frustration_level = 3
        bug._frustration_cooldown = 12
        state = bug.get_state()
        assert state["frustration_level"] == 3
        assert state["frustration_cooldown"] == 12
