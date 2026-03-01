import math

from some_sim.core.stimulus import Stimulus, StimulusType


class TestStimulusType:
    def test_enum_values(self):
        assert StimulusType.FOOD.value == "food"
        assert StimulusType.WATER.value == "water"
        assert StimulusType.LIGHT.value == "light"
        assert StimulusType.HEAT.value == "heat"
        assert StimulusType.OBSTACLE.value == "obstacle"


class TestStimulus:
    def test_creation(self):
        s = Stimulus(
            stimulus_type=StimulusType.FOOD,
            position=(5, 3),
            intensity=0.8,
            radius=4.0,
        )
        assert s.stimulus_type == StimulusType.FOOD
        assert s.position == (5, 3)
        assert s.intensity == 0.8
        assert s.radius == 4.0
        assert s.depletes is False
        assert s.depletion_rate == 0.0

    def test_distance_to_same_position(self):
        s = Stimulus(StimulusType.FOOD, position=(3, 4), intensity=1.0, radius=5.0)
        assert s.distance_to((3, 4)) == 0.0

    def test_distance_to_different_position(self):
        s = Stimulus(StimulusType.FOOD, position=(0, 0), intensity=1.0, radius=10.0)
        assert s.distance_to((3, 4)) == 5.0

    def test_perceived_intensity_at_origin(self):
        s = Stimulus(StimulusType.FOOD, position=(5, 5), intensity=0.8, radius=4.0)
        assert s.perceived_intensity_at((5, 5)) == 0.8

    def test_perceived_intensity_within_radius(self):
        s = Stimulus(StimulusType.FOOD, position=(0, 0), intensity=1.0, radius=10.0)
        intensity = s.perceived_intensity_at((5, 0))
        assert intensity == 0.5  # 1.0 * (1 - 5/10)

    def test_perceived_intensity_at_edge(self):
        s = Stimulus(StimulusType.FOOD, position=(0, 0), intensity=1.0, radius=5.0)
        intensity = s.perceived_intensity_at((5, 0))
        assert intensity == 0.0

    def test_perceived_intensity_outside_radius(self):
        s = Stimulus(StimulusType.FOOD, position=(0, 0), intensity=1.0, radius=3.0)
        intensity = s.perceived_intensity_at((5, 0))
        assert intensity == 0.0

    def test_depletable_stimulus(self):
        s = Stimulus(
            StimulusType.FOOD,
            position=(0, 0),
            intensity=1.0,
            radius=5.0,
            depletes=True,
            depletion_rate=0.1,
        )
        assert s.depletes is True
        assert s.depletion_rate == 0.1
