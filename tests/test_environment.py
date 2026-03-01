from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus, StimulusType


class TestEnvironmentCreation:
    def test_create_environment(self):
        env = Environment(width=20, height=15)
        assert env.width == 20
        assert env.height == 15
        assert env.stimuli == []


class TestBounds:
    def test_within_bounds(self):
        env = Environment(width=10, height=10)
        assert env.is_within_bounds((0, 0)) is True
        assert env.is_within_bounds((9, 9)) is True
        assert env.is_within_bounds((5, 5)) is True

    def test_outside_bounds(self):
        env = Environment(width=10, height=10)
        assert env.is_within_bounds((-1, 0)) is False
        assert env.is_within_bounds((0, -1)) is False
        assert env.is_within_bounds((10, 0)) is False
        assert env.is_within_bounds((0, 10)) is False


class TestStimuli:
    def test_add_stimulus(self):
        env = Environment(width=10, height=10)
        s = Stimulus(StimulusType.FOOD, (5, 5), intensity=0.8, radius=3.0)
        env.add_stimulus(s)
        assert len(env.stimuli) == 1
        assert env.stimuli[0] is s

    def test_remove_stimulus(self):
        env = Environment(width=10, height=10)
        s = Stimulus(StimulusType.FOOD, (5, 5), intensity=0.8, radius=3.0)
        env.add_stimulus(s)
        env.remove_stimulus(s)
        assert len(env.stimuli) == 0

    def test_get_stimuli_at_exact_position(self):
        env = Environment(width=10, height=10)
        s1 = Stimulus(StimulusType.FOOD, (5, 5), intensity=0.8, radius=3.0)
        s2 = Stimulus(StimulusType.WATER, (5, 5), intensity=0.6, radius=2.0)
        s3 = Stimulus(StimulusType.LIGHT, (3, 3), intensity=1.0, radius=5.0)
        env.add_stimulus(s1)
        env.add_stimulus(s2)
        env.add_stimulus(s3)
        at_5_5 = env.get_stimuli_at((5, 5))
        assert len(at_5_5) == 2
        assert s1 in at_5_5
        assert s2 in at_5_5

    def test_get_stimuli_in_radius(self):
        env = Environment(width=20, height=20)
        s1 = Stimulus(StimulusType.FOOD, (5, 5), intensity=0.8, radius=3.0)
        s2 = Stimulus(StimulusType.WATER, (15, 15), intensity=0.6, radius=2.0)
        env.add_stimulus(s1)
        env.add_stimulus(s2)
        nearby = env.get_stimuli_in_radius((6, 5), radius=5.0)
        assert len(nearby) == 1
        stim, dist = nearby[0]
        assert stim is s1
        assert dist == 1.0


class TestPassability:
    def test_passable_empty_cell(self):
        env = Environment(width=10, height=10)
        assert env.is_passable((5, 5)) is True

    def test_impassable_obstacle(self):
        env = Environment(width=10, height=10)
        wall = Stimulus(StimulusType.OBSTACLE, (5, 5), intensity=1.0, radius=0.0)
        env.add_stimulus(wall)
        assert env.is_passable((5, 5)) is False

    def test_passable_non_obstacle(self):
        env = Environment(width=10, height=10)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=0.8, radius=3.0)
        env.add_stimulus(food)
        assert env.is_passable((5, 5)) is True


class TestEnvironmentUpdate:
    def test_update_depletes_consumed_stimuli(self):
        env = Environment(width=10, height=10)
        s = Stimulus(
            StimulusType.FOOD, (5, 5), intensity=1.0, radius=3.0,
            depletes=True, depletion_rate=0.2,
        )
        env.add_stimulus(s)
        s._consumed = True
        env.update()
        assert s.intensity == 0.8

    def test_update_removes_fully_depleted(self):
        env = Environment(width=10, height=10)
        s = Stimulus(
            StimulusType.FOOD, (5, 5), intensity=0.05, radius=3.0,
            depletes=True, depletion_rate=0.1,
        )
        env.add_stimulus(s)
        s._consumed = True
        env.update()
        assert s not in env.stimuli
