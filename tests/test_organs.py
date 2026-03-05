"""Tests for the organ-based state encoder."""

import math

import torch

from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType
from tolmans_sowbug_playground.systems.drives import Drive, DriveSystem, DriveType
from tolmans_sowbug_playground.systems.motor import Direction
from tolmans_sowbug_playground.systems.organs import (
    ALL_DIRS,
    CARDINAL_DIRS,
    DRIVE_TYPES,
    SIGHT_FAMILIES,
    SMELL_FAMILIES,
    OrganConfig,
    OrgansObservation,
    compute_organ_state_dim,
    encode_organs,
)
from tolmans_sowbug_playground.systems.sensors import SensorSystem


def _make_drive_system() -> DriveSystem:
    return DriveSystem(
        drives=[
            Drive(DriveType.HUNGER, level=0.5),
            Drive(DriveType.THIRST, level=0.3),
            Drive(DriveType.TEMPERATURE, level=0.1),
        ]
    )


class TestComputeOrganStateDim:
    def test_default_config(self):
        config = OrganConfig()
        dim = compute_organ_state_dim(config)
        sight = len(SIGHT_FAMILIES) * config.sight_k * 3  # 5*3*3 = 45
        smell = len(SMELL_FAMILIES) * 3  # 3*3 = 9
        touch = len(CARDINAL_DIRS) + len(SMELL_FAMILIES) * 2  # 4+6 = 10
        proprio = len(DRIVE_TYPES) * 2 + len(ALL_DIRS) + 2 + len(ALL_DIRS)  # 18
        rhythm = 2 + len(DRIVE_TYPES)  # 5
        assert dim == sight + smell + touch + proprio + rhythm
        assert dim == 87

    def test_different_sight_k(self):
        config = OrganConfig(sight_k=5)
        dim = compute_organ_state_dim(config)
        expected_sight = len(SIGHT_FAMILIES) * 5 * 3  # 75
        assert dim == expected_sight + 9 + 10 + 18 + 5


class TestEncodeOrgans:
    def _encode(
        self,
        position=(5, 5),
        env=None,
        perceptions=None,
        orientation=Direction.NORTH,
        drives=None,
        passable=None,
        prev_position=None,
        tick=0,
        consumption_ticks=None,
        config=None,
        perception_radius=5.0,
    ):
        if env is None:
            env = Environment(width=20, height=20)
        if perceptions is None:
            sensors = SensorSystem(perception_radius=perception_radius)
            perceptions = sensors.perceive(position, env)
        if drives is None:
            drives = _make_drive_system()
        if passable is None:
            passable = {Direction.NORTH: (5, 4), Direction.SOUTH: (5, 6),
                        Direction.EAST: (6, 5), Direction.WEST: (4, 5),
                        Direction.STAY: position}
        if prev_position is None:
            prev_position = position
        if consumption_ticks is None:
            consumption_ticks = {}
        if config is None:
            config = OrganConfig()
        return encode_organs(
            perceptions=perceptions,
            environment=env,
            position=position,
            orientation=orientation,
            drive_system=drives,
            passable_moves=passable,
            prev_position=prev_position,
            tick=tick,
            last_consumption_ticks=consumption_ticks,
            config=config,
            perception_radius=perception_radius,
        )

    def test_returns_observation(self):
        obs = self._encode()
        assert isinstance(obs, OrgansObservation)

    def test_tensor_shape(self):
        obs = self._encode()
        t = obs.to_tensor()
        assert t.shape == (87,)
        assert t.dtype == torch.float32

    def test_to_dict_keys(self):
        obs = self._encode()
        d = obs.to_dict()
        assert set(d.keys()) == {"sight_mag", "smell_mag", "touch_mag", "proprio_mag", "rhythm_mag"}

    def test_deterministic(self):
        t1 = self._encode().to_tensor()
        t2 = self._encode().to_tensor()
        assert torch.equal(t1, t2)

    def test_features_are_bounded(self):
        env = Environment(width=20, height=20)
        # Intentionally high intensity to ensure clamping is applied.
        env.add_stimulus(Stimulus(StimulusType.FOOD, (5, 5), intensity=3.0, radius=6.0))
        obs = self._encode(env=env)
        t = obs.to_tensor()
        assert float(t.min()) >= -1.0
        assert float(t.max()) <= 1.0


class TestSightOrgan:
    def test_no_stimuli_gives_zeros(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        assert obs.sight.sum().item() == 0.0

    def test_visible_food_appears_in_sight(self):
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 3), intensity=1.0, radius=6.0)
        env.add_stimulus(food)
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # FOOD is the first sight family, first slot: intensity > 0
        assert obs.sight[0].item() > 0.0
        # Direction to (5,3) from (5,5) is (0, -2) → normalized by radius 5
        assert abs(obs.sight[1].item() - 0.0) < 1e-5  # dx=0
        assert obs.sight[2].item() < 0.0  # dy=-2/5 = -0.4

    def test_obstacle_blocked_not_in_sight(self):
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0))
        env.add_stimulus(Stimulus(StimulusType.FOOD, (5, 3), intensity=1.0, radius=6.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # FOOD slot intensity should be 0 (blocked by obstacle LOS)
        assert obs.sight[0].item() == 0.0

    def test_obstacle_with_zero_radius_still_has_sight_salience(self):
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # OBSTACLE is sight family index 4, first slot starts at 4*3*3 = 36
        assert obs.sight[36].item() > 0.0

    def test_food_behind_agent_not_in_sight(self):
        env = Environment(width=20, height=20)
        # Agent at (5,5), facing NORTH; south target should be outside FOV.
        env.add_stimulus(Stimulus(StimulusType.FOOD, (5, 7), intensity=1.0, radius=6.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # FOOD first slot should be empty due to rear-hemisphere exclusion.
        assert obs.sight[0].item() == 0.0

    def test_food_behind_agent_visible_when_turning_around(self):
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.FOOD, (5, 7), intensity=1.0, radius=6.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.SOUTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        assert obs.sight[0].item() > 0.0


class TestSmellOrgan:
    def test_no_consumables_gives_zeros(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        assert obs.smell.sum().item() == 0.0

    def test_food_behind_wall_still_smelled(self):
        """Smell is non-LOS: food behind an obstacle is still detected."""
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0))
        env.add_stimulus(Stimulus(StimulusType.FOOD, (5, 3), intensity=1.0, radius=6.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # FOOD is SMELL_FAMILIES[0], smell channels: [magnitude, dir_x, dir_y]
        assert obs.smell[0].item() > 0.0  # food detected via smell

    def test_smell_direction_points_toward_food(self):
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.FOOD, (10, 5), intensity=1.0, radius=6.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # Direction X should be positive (food is east)
        assert obs.smell[1].item() > 0.0

    def test_non_positive_smell_scale_is_safe_and_zero(self):
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.FOOD, (7, 5), intensity=1.0, radius=6.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(smell_radius_scale=0.0),
            perception_radius=5.0,
        )
        assert obs.smell.sum().item() == 0.0


class TestTouchOrgan:
    def test_open_space_no_obstacles(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # First 4 dims of touch are obstacle flags, all should be 0
        assert obs.touch[:4].sum().item() == 0.0

    def test_wall_north_detected(self):
        env = Environment(width=20, height=20)
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # CARDINAL_DIRS: N=0, S=1, E=2, W=3; North is blocked
        assert obs.touch[0].item() == 1.0
        assert obs.touch[1].item() == 0.0  # south open

    def test_boundary_detected_as_blocked(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((0, 0), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(0, 0),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={Direction.SOUTH: (0, 1), Direction.EAST: (1, 0), Direction.STAY: (0, 0)},
            prev_position=(0, 0), tick=0, last_consumption_ticks={},
            config=OrganConfig(), perception_radius=5.0,
        )
        assert obs.touch[0].item() == 1.0  # North out of bounds
        assert obs.touch[3].item() == 1.0  # West out of bounds

    def test_food_at_cell_detected(self):
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=0.8, radius=3.0, quantity=10.0)
        env.add_stimulus(food)
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)
        obs = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # Touch dims: 4 obstacle flags + [food_present, food_intensity, water_present, ...]
        assert obs.touch[4].item() == 1.0  # food present
        assert abs(obs.touch[5].item() - 0.8) < 1e-5  # food intensity

    def test_touch_range_changes_directional_contact(self):
        env = Environment(width=20, height=20)
        # Obstacle two cells north; only detectable when touch_range >= 2.
        env.add_stimulus(Stimulus(StimulusType.OBSTACLE, (5, 3), intensity=1.0, radius=0.0))
        sensors = SensorSystem(perception_radius=5.0)
        perceptions = sensors.perceive((5, 5), env)

        obs_r1 = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(touch_range=1),
            perception_radius=5.0,
        )
        obs_r2 = encode_organs(
            perceptions=perceptions, environment=env, position=(5, 5),
            orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(touch_range=2),
            perception_radius=5.0,
        )
        assert obs_r1.touch[0].item() == 0.0
        assert obs_r2.touch[0].item() == 1.0


class TestProprioceptionOrgan:
    def test_drive_levels_encoded(self):
        ds = _make_drive_system()
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        obs = encode_organs(
            perceptions=sensors.perceive((5, 5), env), environment=env,
            position=(5, 5), orientation=Direction.NORTH, drive_system=ds,
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # First 3 dims of proprioception: hunger=0.5, thirst=0.3, temperature=0.1
        assert abs(obs.proprioception[0].item() - 0.5) < 1e-5
        assert abs(obs.proprioception[1].item() - 0.3) < 1e-5
        assert abs(obs.proprioception[2].item() - 0.1) < 1e-5

    def test_orientation_one_hot(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        obs = encode_organs(
            perceptions=sensors.perceive((5, 5), env), environment=env,
            position=(5, 5), orientation=Direction.EAST, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # Proprioception layout: 3 drives + 3 satiety + 5 orientation one-hot
        # Orientation: N=0, S=1, E=2, W=3, STAY=4 (offset +6)
        assert obs.proprioception[6].item() == 0.0  # N
        assert obs.proprioception[7].item() == 0.0  # S
        assert obs.proprioception[8].item() == 1.0  # E (active)
        assert obs.proprioception[9].item() == 0.0  # W
        assert obs.proprioception[10].item() == 0.0  # STAY

    def test_displacement_vector(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        obs = encode_organs(
            perceptions=sensors.perceive((6, 5), env), environment=env,
            position=(6, 5), orientation=Direction.EAST, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # Displacement: (6-5, 5-5) = (1, 0)
        assert obs.proprioception[11].item() == 1.0  # dx
        assert obs.proprioception[12].item() == 0.0  # dy

    def test_action_validity(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        passable = {Direction.SOUTH: (0, 1), Direction.EAST: (1, 0), Direction.STAY: (0, 0)}
        obs = encode_organs(
            perceptions=sensors.perceive((0, 0), env), environment=env,
            position=(0, 0), orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves=passable, prev_position=(0, 0),
            tick=0, last_consumption_ticks={}, config=OrganConfig(),
            perception_radius=5.0,
        )
        # Validity mask: offset = 3+3+5+2 = 13 within proprioception
        assert obs.proprioception[13].item() == 0.0  # N blocked
        assert obs.proprioception[14].item() == 1.0  # S passable
        assert obs.proprioception[15].item() == 1.0  # E passable
        assert obs.proprioception[16].item() == 0.0  # W blocked
        assert obs.proprioception[17].item() == 1.0  # STAY always


class TestRhythmOrgan:
    def test_cyclical_encoding(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        config = OrganConfig(rhythm_period=100.0)
        obs = encode_organs(
            perceptions=sensors.perceive((5, 5), env), environment=env,
            position=(5, 5), orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=25, last_consumption_ticks={}, config=config,
            perception_radius=5.0,
        )
        phase = 2.0 * math.pi * 25 / 100.0
        assert abs(obs.rhythm[0].item() - math.sin(phase)) < 1e-5
        assert abs(obs.rhythm[1].item() - math.cos(phase)) < 1e-5

    def test_never_consumed_max_interval(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        obs = encode_organs(
            perceptions=sensors.perceive((5, 5), env), environment=env,
            position=(5, 5), orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=50, last_consumption_ticks={}, config=OrganConfig(rhythm_period=100.0),
            perception_radius=5.0,
        )
        # All intervals should be 1.0 (never consumed)
        assert obs.rhythm[2].item() == 1.0
        assert obs.rhythm[3].item() == 1.0
        assert obs.rhythm[4].item() == 1.0

    def test_recent_consumption_low_interval(self):
        env = Environment(width=20, height=20)
        sensors = SensorSystem(perception_radius=5.0)
        consumption_ticks = {DriveType.HUNGER: 45}
        obs = encode_organs(
            perceptions=sensors.perceive((5, 5), env), environment=env,
            position=(5, 5), orientation=Direction.NORTH, drive_system=_make_drive_system(),
            passable_moves={d: (5, 5) for d in ALL_DIRS}, prev_position=(5, 5),
            tick=50, last_consumption_ticks=consumption_ticks,
            config=OrganConfig(rhythm_period=100.0), perception_radius=5.0,
        )
        # Hunger interval: (50-45)/100 = 0.05
        assert abs(obs.rhythm[2].item() - 0.05) < 1e-5
        # Others still 1.0
        assert obs.rhythm[3].item() == 1.0
        assert obs.rhythm[4].item() == 1.0
