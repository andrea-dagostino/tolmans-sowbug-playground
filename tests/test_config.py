import tempfile

import yaml

from tolmans_sowbug_playground.core.config import SimulationConfig, load_config, build_simulation


VALID_CONFIG = {
    "grid": {"width": 20, "height": 20},
    "simulation": {"max_ticks": 1000, "random_seed": 42},
    "stimuli": [
        {"type": "food", "position": [10, 10], "intensity": 1.0, "radius": 5.0},
        {"type": "water", "position": [15, 5], "intensity": 0.8, "radius": 3.0},
        {"type": "light", "position": [3, 3], "intensity": 1.0, "radius": 8.0},
        {"type": "obstacle", "position": [7, 7], "intensity": 1.0, "radius": 0.0},
    ],
    "agent": {
        "type": "sowbug",
        "position": [5, 5],
        "hunger_rate": 0.01,
        "thirst_rate": 0.008,
        "temperature_rate": 0.005,
        "perception_radius": 5.0,
        "learning_rate": 0.1,
        "decay_rate": 0.01,
    },
}


class TestLoadConfig:
    def test_load_valid_config(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(VALID_CONFIG, f)
            path = f.name
        config = load_config(path)
        assert config.grid_width == 20
        assert config.grid_height == 20
        assert config.max_ticks == 1000
        assert config.random_seed == 42
        assert len(config.stimuli) == 4

    def test_missing_grid_raises(self):
        bad = {"simulation": {"max_ticks": 100}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(bad, f)
            path = f.name
        try:
            load_config(path)
            assert False, "Should have raised"
        except (KeyError, ValueError):
            pass


class TestBuildSimulation:
    def test_build_creates_simulation(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(VALID_CONFIG, f)
            path = f.name
        config = load_config(path)
        sim = build_simulation(config)
        assert sim.environment.width == 20
        assert sim.environment.height == 20
        assert len(sim.agents) == 1
        assert sim.max_ticks == 1000
        assert len(sim.environment.stimuli) == 4
