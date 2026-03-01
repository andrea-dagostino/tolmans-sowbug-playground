import math

import pytest

from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType


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
        assert s.quantity is None

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


class TestQuantity:
    def test_default_quantity_is_none(self):
        s = Stimulus(StimulusType.FOOD, (0, 0), intensity=1.0, radius=5.0)
        assert s.quantity is None
        assert s.depleted is False

    def test_consume_infinite_returns_full_amount(self):
        s = Stimulus(StimulusType.HEAT, (0, 0), intensity=1.0, radius=5.0)
        actual = s.consume(0.5)
        assert actual == 0.5
        assert s.intensity == 1.0  # unchanged

    def test_consume_finite_reduces_quantity_and_scales_intensity(self):
        s = Stimulus(StimulusType.FOOD, (0, 0), intensity=1.0, radius=5.0, quantity=10.0)
        actual = s.consume(2.0)
        assert actual == 2.0
        assert s.quantity == 8.0
        assert s.intensity == pytest.approx(0.8)  # 1.0 * (8/10)

    def test_consume_cannot_take_more_than_remaining(self):
        s = Stimulus(StimulusType.FOOD, (0, 0), intensity=1.0, radius=5.0, quantity=1.0)
        actual = s.consume(5.0)
        assert actual == 1.0
        assert s.quantity == 0.0

    def test_depleted_when_quantity_zero(self):
        s = Stimulus(StimulusType.FOOD, (0, 0), intensity=1.0, radius=5.0, quantity=1.0)
        s.consume(1.0)
        assert s.depleted is True

    def test_half_quantity_half_intensity(self):
        s = Stimulus(StimulusType.WATER, (0, 0), intensity=0.8, radius=3.0, quantity=4.0)
        s.consume(2.0)
        assert s.quantity == 2.0
        assert s.intensity == pytest.approx(0.4)  # 0.8 * (2/4)
