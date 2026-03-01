import random

from some_sim.agents.sowbug import Sowbug
from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus, StimulusType
from some_sim.systems.drives import DriveType


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

    def test_avoids_light(self):
        random.seed(0)
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.1
        bug.drive_system.drives[DriveType.THIRST].level = 0.1
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.1

        env = Environment(width=20, height=20)
        light = Stimulus(StimulusType.LIGHT, (5, 4), intensity=1.0, radius=5.0)
        env.add_stimulus(light)

        bug.perceive(env)
        direction = bug.decide()
        bug.act(direction, env)
        # Should not move north (toward the light)
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
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0)
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
