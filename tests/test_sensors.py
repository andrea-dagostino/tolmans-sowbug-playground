from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus, StimulusType
from some_sim.systems.sensors import Perception, SensorSystem


class TestPerception:
    def test_creation(self):
        s = Stimulus(StimulusType.FOOD, (5, 5), intensity=0.8, radius=3.0)
        p = Perception(stimulus=s, perceived_intensity=0.4, distance=2.0, direction=(2, 2))
        assert p.stimulus is s
        assert p.perceived_intensity == 0.4
        assert p.distance == 2.0
        assert p.direction == (2, 2)


class TestSensorSystem:
    def _make_env_with_food(self):
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=6.0)
        env.add_stimulus(food)
        return env, food

    def test_perceive_nearby_stimulus(self):
        env, food = self._make_env_with_food()
        sensors = SensorSystem(perception_radius=10.0)
        perceptions = sensors.perceive((4, 5), env)
        assert len(perceptions) == 1
        assert perceptions[0].stimulus is food
        assert perceptions[0].distance == 1.0
        assert perceptions[0].direction == (1, 0)

    def test_perceive_ignores_distant_stimulus(self):
        env, _ = self._make_env_with_food()
        sensors = SensorSystem(perception_radius=2.0)
        perceptions = sensors.perceive((15, 15), env)
        assert len(perceptions) == 0

    def test_perceived_intensity_decreases_with_distance(self):
        env, _ = self._make_env_with_food()
        sensors = SensorSystem(perception_radius=10.0)
        close = sensors.perceive((5, 5), env)
        far = sensors.perceive((3, 5), env)
        assert close[0].perceived_intensity > far[0].perceived_intensity

    def test_perceive_multiple_stimuli(self):
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=6.0)
        water = Stimulus(StimulusType.WATER, (6, 5), intensity=0.8, radius=4.0)
        env.add_stimulus(food)
        env.add_stimulus(water)
        sensors = SensorSystem(perception_radius=10.0)
        perceptions = sensors.perceive((5, 5), env)
        assert len(perceptions) == 2

    def test_direction_calculation(self):
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (8, 3), intensity=1.0, radius=10.0)
        env.add_stimulus(food)
        sensors = SensorSystem(perception_radius=10.0)
        perceptions = sensors.perceive((5, 5), env)
        assert perceptions[0].direction == (3, -2)
