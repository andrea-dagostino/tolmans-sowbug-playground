# Schematic Sowbug Simulation Platform — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a research platform for studying psychological phenomena, starting with Tolman's Schematic Sowbug.

**Architecture:** Clean OOP with modular subsystems (DriveSystem, SensorSystem, MemorySystem, MotorSystem) inside Agent classes. Headless simulation core with optional FastAPI+WebSocket browser visualization.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, numpy, matplotlib, pyyaml, pytest

---

### Task 1: Project Scaffolding

**Files:**
- Modify: `pyproject.toml`
- Create: `src/some_sim/__init__.py`
- Create: `src/some_sim/__main__.py`
- Create: `src/some_sim/core/__init__.py`
- Create: `src/some_sim/agents/__init__.py`
- Create: `src/some_sim/systems/__init__.py`
- Create: `src/some_sim/analysis/__init__.py`
- Create: `src/some_sim/web/__init__.py`
- Create: `configs/` (directory)
- Create: `tests/` (directory)

**Step 1: Update pyproject.toml**

```toml
[project]
name = "some-sim"
version = "0.1.0"
description = "A research platform for studying psychological phenomena via agent-based simulation"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "numpy>=1.26",
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "websockets>=14.0",
    "pyyaml>=6.0",
    "matplotlib>=3.9",
]

[project.scripts]
some-sim = "some_sim.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/some_sim"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**Step 2: Create all __init__.py files (empty)**

Create empty `__init__.py` in each package directory:
- `src/some_sim/__init__.py`
- `src/some_sim/core/__init__.py`
- `src/some_sim/agents/__init__.py`
- `src/some_sim/systems/__init__.py`
- `src/some_sim/analysis/__init__.py`
- `src/some_sim/web/__init__.py`

**Step 3: Create __main__.py**

```python
import sys


def main():
    print("some-sim: no command specified. Use --help for usage.")
    sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 4: Create configs/ and tests/ directories**

Create empty directories (add .gitkeep if needed).

**Step 5: Install dependencies and verify**

Run: `uv sync`
Run: `uv run python -m some_sim`
Expected: prints "some-sim: no command specified" and exits with code 1.

**Step 6: Commit**

```bash
git add pyproject.toml src/ configs/ tests/ uv.lock
git commit -m "chore: scaffold project structure and dependencies"
```

---

### Task 2: Stimulus Model

**Files:**
- Create: `src/some_sim/core/stimulus.py`
- Create: `tests/test_stimulus.py`

**Step 1: Write the failing test**

```python
# tests/test_stimulus.py
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stimulus.py -v`
Expected: FAIL — ImportError (module doesn't exist yet)

**Step 3: Write implementation**

```python
# src/some_sim/core/stimulus.py
import math
from dataclasses import dataclass
from enum import Enum


class StimulusType(Enum):
    FOOD = "food"
    WATER = "water"
    LIGHT = "light"
    HEAT = "heat"
    OBSTACLE = "obstacle"


@dataclass
class Stimulus:
    stimulus_type: StimulusType
    position: tuple[int, int]
    intensity: float
    radius: float
    depletes: bool = False
    depletion_rate: float = 0.0

    def distance_to(self, position: tuple[int, int]) -> float:
        dx = self.position[0] - position[0]
        dy = self.position[1] - position[1]
        return math.sqrt(dx * dx + dy * dy)

    def perceived_intensity_at(self, position: tuple[int, int]) -> float:
        dist = self.distance_to(position)
        if dist >= self.radius:
            return 0.0
        return self.intensity * (1.0 - dist / self.radius)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_stimulus.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/core/stimulus.py tests/test_stimulus.py
git commit -m "feat: add Stimulus model with type, intensity, and distance calculations"
```

---

### Task 3: Environment

**Files:**
- Create: `src/some_sim/core/environment.py`
- Create: `tests/test_environment.py`

**Step 1: Write the failing test**

```python
# tests/test_environment.py
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_environment.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/core/environment.py
from dataclasses import dataclass, field

from some_sim.core.stimulus import Stimulus, StimulusType


@dataclass
class Environment:
    width: int
    height: int
    stimuli: list[Stimulus] = field(default_factory=list)

    def add_stimulus(self, stimulus: Stimulus) -> None:
        self.stimuli.append(stimulus)

    def remove_stimulus(self, stimulus: Stimulus) -> None:
        self.stimuli.remove(stimulus)

    def get_stimuli_at(self, position: tuple[int, int]) -> list[Stimulus]:
        return [s for s in self.stimuli if s.position == position]

    def get_stimuli_in_radius(
        self, position: tuple[int, int], radius: float
    ) -> list[tuple[Stimulus, float]]:
        results = []
        for s in self.stimuli:
            dist = s.distance_to(position)
            if dist <= radius:
                results.append((s, dist))
        return results

    def is_within_bounds(self, position: tuple[int, int]) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def is_passable(self, position: tuple[int, int]) -> bool:
        for s in self.stimuli:
            if s.position == position and s.stimulus_type == StimulusType.OBSTACLE:
                return False
        return True

    def update(self) -> None:
        to_remove = []
        for s in self.stimuli:
            if s.depletes and getattr(s, "_consumed", False):
                s.intensity -= s.depletion_rate
                s._consumed = False
                if s.intensity <= 0.0:
                    to_remove.append(s)
        for s in to_remove:
            self.stimuli.remove(s)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_environment.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/core/environment.py tests/test_environment.py
git commit -m "feat: add Environment with grid bounds, stimuli management, and passability"
```

---

### Task 4: DriveSystem

**Files:**
- Create: `src/some_sim/systems/drives.py`
- Create: `tests/test_drives.py`

**Step 1: Write the failing test**

```python
# tests/test_drives.py
from some_sim.systems.drives import Drive, DriveSystem, DriveType


class TestDriveType:
    def test_enum_values(self):
        assert DriveType.HUNGER.value == "hunger"
        assert DriveType.THIRST.value == "thirst"
        assert DriveType.TEMPERATURE.value == "temperature"


class TestDrive:
    def test_creation_defaults(self):
        d = Drive(drive_type=DriveType.HUNGER)
        assert d.level == 0.0
        assert d.rate == 0.01

    def test_update_increases_level(self):
        d = Drive(DriveType.HUNGER, level=0.0, rate=0.05)
        d.update()
        assert d.level == 0.05

    def test_update_capped_at_one(self):
        d = Drive(DriveType.HUNGER, level=0.98, rate=0.05)
        d.update()
        assert d.level == 1.0

    def test_satisfy_decreases_level(self):
        d = Drive(DriveType.HUNGER, level=0.8, rate=0.01)
        d.satisfy(0.3)
        assert abs(d.level - 0.5) < 1e-9

    def test_satisfy_floored_at_zero(self):
        d = Drive(DriveType.HUNGER, level=0.2, rate=0.01)
        d.satisfy(0.5)
        assert d.level == 0.0


class TestDriveSystem:
    def test_creation_with_drives(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.5),
            Drive(DriveType.THIRST, level=0.3),
        ])
        assert ds.get_level(DriveType.HUNGER) == 0.5
        assert ds.get_level(DriveType.THIRST) == 0.3

    def test_update_all_drives(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.0, rate=0.1),
            Drive(DriveType.THIRST, level=0.0, rate=0.2),
        ])
        ds.update()
        assert ds.get_level(DriveType.HUNGER) == 0.1
        assert ds.get_level(DriveType.THIRST) == 0.2

    def test_get_most_urgent(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.3),
            Drive(DriveType.THIRST, level=0.7),
            Drive(DriveType.TEMPERATURE, level=0.1),
        ])
        urgent = ds.get_most_urgent()
        assert urgent is not None
        assert urgent.drive_type == DriveType.THIRST

    def test_get_most_urgent_empty(self):
        ds = DriveSystem()
        assert ds.get_most_urgent() is None

    def test_satisfy_specific_drive(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.8),
        ])
        ds.satisfy(DriveType.HUNGER, 0.3)
        assert abs(ds.get_level(DriveType.HUNGER) - 0.5) < 1e-9

    def test_get_levels(self):
        ds = DriveSystem(drives=[
            Drive(DriveType.HUNGER, level=0.5),
            Drive(DriveType.THIRST, level=0.3),
        ])
        levels = ds.get_levels()
        assert levels == {DriveType.HUNGER: 0.5, DriveType.THIRST: 0.3}

    def test_get_level_missing_drive(self):
        ds = DriveSystem()
        assert ds.get_level(DriveType.HUNGER) == 0.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_drives.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/systems/drives.py
from dataclasses import dataclass
from enum import Enum


class DriveType(Enum):
    HUNGER = "hunger"
    THIRST = "thirst"
    TEMPERATURE = "temperature"


@dataclass
class Drive:
    drive_type: DriveType
    level: float = 0.0
    rate: float = 0.01

    def update(self) -> None:
        self.level = min(1.0, self.level + self.rate)

    def satisfy(self, amount: float) -> None:
        self.level = max(0.0, self.level - amount)


class DriveSystem:
    def __init__(self, drives: list[Drive] | None = None) -> None:
        self.drives: dict[DriveType, Drive] = {}
        for d in (drives or []):
            self.drives[d.drive_type] = d

    def update(self) -> None:
        for drive in self.drives.values():
            drive.update()

    def get_most_urgent(self) -> Drive | None:
        if not self.drives:
            return None
        return max(self.drives.values(), key=lambda d: d.level)

    def satisfy(self, drive_type: DriveType, amount: float) -> None:
        if drive_type in self.drives:
            self.drives[drive_type].satisfy(amount)

    def get_level(self, drive_type: DriveType) -> float:
        if drive_type in self.drives:
            return self.drives[drive_type].level
        return 0.0

    def get_levels(self) -> dict[DriveType, float]:
        return {dt: d.level for dt, d in self.drives.items()}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_drives.py -v`
Expected: All 12 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/systems/drives.py tests/test_drives.py
git commit -m "feat: add DriveSystem with hunger, thirst, temperature drives"
```

---

### Task 5: SensorSystem

**Files:**
- Create: `src/some_sim/systems/sensors.py`
- Create: `tests/test_sensors.py`

**Step 1: Write the failing test**

```python
# tests/test_sensors.py
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sensors.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/systems/sensors.py
from dataclasses import dataclass

from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus


@dataclass
class Perception:
    stimulus: Stimulus
    perceived_intensity: float
    distance: float
    direction: tuple[int, int]


class SensorSystem:
    def __init__(self, perception_radius: float = 5.0) -> None:
        self.perception_radius = perception_radius

    def perceive(
        self, position: tuple[int, int], environment: Environment
    ) -> list[Perception]:
        stimuli_in_range = environment.get_stimuli_in_radius(
            position, self.perception_radius
        )
        perceptions = []
        for stimulus, distance in stimuli_in_range:
            perceived_intensity = stimulus.perceived_intensity_at(position)
            direction = (
                stimulus.position[0] - position[0],
                stimulus.position[1] - position[1],
            )
            perceptions.append(
                Perception(
                    stimulus=stimulus,
                    perceived_intensity=perceived_intensity,
                    distance=distance,
                    direction=direction,
                )
            )
        return perceptions
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sensors.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/systems/sensors.py tests/test_sensors.py
git commit -m "feat: add SensorSystem with perception radius and intensity falloff"
```

---

### Task 6: MotorSystem

**Files:**
- Create: `src/some_sim/systems/motor.py`
- Create: `tests/test_motor.py`

**Step 1: Write the failing test**

```python
# tests/test_motor.py
from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus, StimulusType
from some_sim.systems.motor import Direction, MotorSystem


class TestDirection:
    def test_direction_values(self):
        assert Direction.NORTH.value == (0, -1)
        assert Direction.SOUTH.value == (0, 1)
        assert Direction.EAST.value == (1, 0)
        assert Direction.WEST.value == (-1, 0)
        assert Direction.STAY.value == (0, 0)


class TestMotorSystem:
    def test_move_north(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.NORTH, env)
        assert new_pos == (5, 4)

    def test_move_south(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.SOUTH, env)
        assert new_pos == (5, 6)

    def test_move_east(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.EAST, env)
        assert new_pos == (6, 5)

    def test_move_west(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.WEST, env)
        assert new_pos == (4, 5)

    def test_stay(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.STAY, env)
        assert new_pos == (5, 5)

    def test_blocked_by_boundary_north(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((5, 0), Direction.NORTH, env)
        assert new_pos == (5, 0)

    def test_blocked_by_boundary_west(self):
        env = Environment(width=10, height=10)
        motor = MotorSystem()
        new_pos = motor.move((0, 5), Direction.WEST, env)
        assert new_pos == (0, 5)

    def test_blocked_by_obstacle(self):
        env = Environment(width=10, height=10)
        wall = Stimulus(StimulusType.OBSTACLE, (5, 4), intensity=1.0, radius=0.0)
        env.add_stimulus(wall)
        motor = MotorSystem()
        new_pos = motor.move((5, 5), Direction.NORTH, env)
        assert new_pos == (5, 5)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_motor.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/systems/motor.py
from enum import Enum

from some_sim.core.environment import Environment


class Direction(Enum):
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)
    STAY = (0, 0)


class MotorSystem:
    def move(
        self,
        position: tuple[int, int],
        direction: Direction,
        environment: Environment,
    ) -> tuple[int, int]:
        dx, dy = direction.value
        new_position = (position[0] + dx, position[1] + dy)
        if environment.is_within_bounds(new_position) and environment.is_passable(
            new_position
        ):
            return new_position
        return position
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_motor.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/systems/motor.py tests/test_motor.py
git commit -m "feat: add MotorSystem with directional movement and collision checking"
```

---

### Task 7: MemorySystem (Cognitive Map)

**Files:**
- Create: `src/some_sim/systems/memory.py`
- Create: `tests/test_memory.py`

**Step 1: Write the failing test**

```python
# tests/test_memory.py
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
        assert entry.expected_intensity == 0.6  # 0.8 + 0.5*(0.4-0.8) = 0.6
        assert entry.reward_value == 0.8  # 1.0 + 0.5*(0.6-1.0) = 0.8
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_memory.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/systems/memory.py
from dataclasses import dataclass

from some_sim.core.stimulus import StimulusType


@dataclass
class MemoryEntry:
    stimulus_type: StimulusType
    expected_intensity: float
    reward_value: float
    strength: float = 1.0


class MemorySystem:
    def __init__(
        self, learning_rate: float = 0.1, decay_rate: float = 0.01
    ) -> None:
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.cognitive_map: dict[tuple[int, int], list[MemoryEntry]] = {}
        self.edges: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}

    def record_experience(
        self,
        position: tuple[int, int],
        stimulus_type: StimulusType,
        intensity: float,
        reward: float,
    ) -> None:
        if position not in self.cognitive_map:
            self.cognitive_map[position] = []
        # Update existing entry if present
        for entry in self.cognitive_map[position]:
            if entry.stimulus_type == stimulus_type:
                entry.expected_intensity = intensity
                entry.reward_value = reward
                entry.strength = 1.0
                return
        # Otherwise create new
        self.cognitive_map[position].append(
            MemoryEntry(
                stimulus_type=stimulus_type,
                expected_intensity=intensity,
                reward_value=reward,
                strength=1.0,
            )
        )

    def record_traversal(
        self, from_pos: tuple[int, int], to_pos: tuple[int, int]
    ) -> None:
        key = (from_pos, to_pos)
        self.edges[key] = self.edges.get(key, 0) + 1

    def get_expected(
        self, position: tuple[int, int], stimulus_type: StimulusType
    ) -> MemoryEntry | None:
        entries = self.cognitive_map.get(position, [])
        for entry in entries:
            if entry.stimulus_type == stimulus_type:
                return entry
        return None

    def get_best_location_for(
        self, stimulus_type: StimulusType
    ) -> tuple[int, int] | None:
        best_pos = None
        best_score = -1.0
        for pos, entries in self.cognitive_map.items():
            for entry in entries:
                if entry.stimulus_type == stimulus_type:
                    score = entry.reward_value * entry.strength
                    if score > best_score:
                        best_score = score
                        best_pos = pos
        return best_pos

    def update_expectation(
        self,
        position: tuple[int, int],
        stimulus_type: StimulusType,
        actual_intensity: float,
        actual_reward: float,
    ) -> None:
        entry = self.get_expected(position, stimulus_type)
        if entry is None:
            return
        # Adjust expectations toward actual values
        entry.expected_intensity += self.learning_rate * (
            actual_intensity - entry.expected_intensity
        )
        entry.reward_value += self.learning_rate * (
            actual_reward - entry.reward_value
        )
        # Adjust strength based on prediction error
        intensity_error = abs(actual_intensity - entry.expected_intensity)
        reward_error = abs(actual_reward - entry.reward_value)
        avg_error = (intensity_error + reward_error) / 2.0
        if avg_error < 0.2:
            entry.strength = min(1.0, entry.strength + self.learning_rate * 0.5)
        else:
            entry.strength = max(0.0, entry.strength - avg_error * self.learning_rate)

    def decay(self) -> None:
        positions_to_clean = []
        for pos, entries in self.cognitive_map.items():
            to_remove = []
            for entry in entries:
                entry.strength -= self.decay_rate
                if entry.strength < 0.01:
                    to_remove.append(entry)
            for entry in to_remove:
                entries.remove(entry)
            if not entries:
                positions_to_clean.append(pos)
        for pos in positions_to_clean:
            del self.cognitive_map[pos]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_memory.py -v`
Expected: All 11 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/systems/memory.py tests/test_memory.py
git commit -m "feat: add MemorySystem with cognitive map, associative learning, and decay"
```

---

### Task 8: Base Agent

**Files:**
- Create: `src/some_sim/core/agent.py`
- Create: `tests/test_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_agent.py
from some_sim.core.agent import Agent
from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus, StimulusType
from some_sim.systems.drives import Drive, DriveSystem, DriveType
from some_sim.systems.memory import MemorySystem
from some_sim.systems.motor import Direction, MotorSystem
from some_sim.systems.sensors import SensorSystem


class ConcreteAgent(Agent):
    """Minimal agent for testing — always moves north."""

    def decide(self) -> Direction:
        return Direction.NORTH


class TestAgent:
    def _make_agent(self, position=(5, 5)):
        return ConcreteAgent(
            position=position,
            orientation=Direction.NORTH,
            drive_system=DriveSystem(drives=[Drive(DriveType.HUNGER)]),
            sensor_system=SensorSystem(perception_radius=5.0),
            memory_system=MemorySystem(),
            motor_system=MotorSystem(),
        )

    def test_creation(self):
        agent = self._make_agent()
        assert agent.position == (5, 5)
        assert agent.orientation == Direction.NORTH

    def test_perceive_stores_perceptions(self):
        agent = self._make_agent()
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 4), intensity=1.0, radius=3.0)
        env.add_stimulus(food)
        agent.perceive(env)
        assert len(agent.current_perceptions) == 1
        assert agent.current_perceptions[0].stimulus is food

    def test_act_updates_position(self):
        agent = self._make_agent(position=(5, 5))
        env = Environment(width=20, height=20)
        direction = agent.decide()
        agent.act(direction, env)
        assert agent.position == (5, 4)

    def test_act_blocked_by_wall(self):
        agent = self._make_agent(position=(5, 0))
        env = Environment(width=20, height=20)
        direction = agent.decide()  # NORTH
        agent.act(direction, env)
        assert agent.position == (5, 0)

    def test_get_state(self):
        agent = self._make_agent()
        state = agent.get_state()
        assert state["position"] == (5, 5)
        assert state["orientation"] == "NORTH"
        assert "drive_levels" in state
        assert DriveType.HUNGER in state["drive_levels"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/core/agent.py
from abc import ABC, abstractmethod

from some_sim.core.environment import Environment
from some_sim.systems.drives import DriveSystem
from some_sim.systems.memory import MemorySystem
from some_sim.systems.motor import Direction, MotorSystem
from some_sim.systems.sensors import Perception, SensorSystem


class Agent(ABC):
    def __init__(
        self,
        position: tuple[int, int],
        orientation: Direction,
        drive_system: DriveSystem,
        sensor_system: SensorSystem,
        memory_system: MemorySystem,
        motor_system: MotorSystem,
    ) -> None:
        self.position = position
        self.orientation = orientation
        self.drive_system = drive_system
        self.sensor_system = sensor_system
        self.memory_system = memory_system
        self.motor_system = motor_system
        self.current_perceptions: list[Perception] = []

    def perceive(self, environment: Environment) -> None:
        self.current_perceptions = self.sensor_system.perceive(
            self.position, environment
        )

    @abstractmethod
    def decide(self) -> Direction:
        ...

    def act(self, direction: Direction, environment: Environment) -> None:
        old_position = self.position
        self.position = self.motor_system.move(
            self.position, direction, environment
        )
        self.orientation = direction
        if self.position != old_position:
            self.memory_system.record_traversal(old_position, self.position)

    def get_state(self) -> dict:
        return {
            "position": self.position,
            "orientation": self.orientation.name,
            "drive_levels": self.drive_system.get_levels(),
            "perception_count": len(self.current_perceptions),
        }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agent.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/core/agent.py tests/test_agent.py
git commit -m "feat: add base Agent class with perceive/decide/act lifecycle"
```

---

### Task 9: Sowbug Agent

**Files:**
- Create: `src/some_sim/agents/sowbug.py`
- Create: `tests/test_sowbug.py`

**Step 1: Write the failing test**

```python
# tests/test_sowbug.py
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
        # Should move toward the food (north, since food is at y=2 and bug at y=5)
        bug.act(direction, env)
        # Bug should have moved closer to food
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
        # Should not move north (toward the light)
        bug.act(direction, env)
        assert bug.position[1] >= 5

    def test_explores_when_no_memory(self):
        random.seed(42)
        bug = Sowbug(position=(5, 5))
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9

        env = Environment(width=20, height=20)
        # No stimuli nearby — should still move (explore)
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sowbug.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/agents/sowbug.py
import math
import random

from some_sim.core.agent import Agent
from some_sim.core.environment import Environment
from some_sim.core.stimulus import StimulusType
from some_sim.systems.drives import Drive, DriveSystem, DriveType
from some_sim.systems.memory import MemorySystem
from some_sim.systems.motor import Direction, MotorSystem
from some_sim.systems.sensors import Perception, SensorSystem

DRIVE_STIMULUS_MAP = {
    DriveType.HUNGER: StimulusType.FOOD,
    DriveType.THIRST: StimulusType.WATER,
    DriveType.TEMPERATURE: StimulusType.HEAT,
}

# Directions excluding STAY, for exploration
MOVE_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]


class Sowbug(Agent):
    def __init__(
        self,
        position: tuple[int, int],
        hunger_rate: float = 0.01,
        thirst_rate: float = 0.008,
        temperature_rate: float = 0.005,
        perception_radius: float = 5.0,
        learning_rate: float = 0.1,
        decay_rate: float = 0.01,
    ) -> None:
        drive_system = DriveSystem(
            drives=[
                Drive(DriveType.HUNGER, rate=hunger_rate),
                Drive(DriveType.THIRST, rate=thirst_rate),
                Drive(DriveType.TEMPERATURE, rate=temperature_rate),
            ]
        )
        super().__init__(
            position=position,
            orientation=Direction.NORTH,
            drive_system=drive_system,
            sensor_system=SensorSystem(perception_radius=perception_radius),
            memory_system=MemorySystem(
                learning_rate=learning_rate, decay_rate=decay_rate
            ),
            motor_system=MotorSystem(),
        )

    def _drive_to_stimulus(self, drive_type: DriveType) -> StimulusType:
        return DRIVE_STIMULUS_MAP[drive_type]

    def _direction_toward(self, target: tuple[int, int]) -> Direction:
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        # Pick the axis with the larger difference
        if abs(dx) >= abs(dy):
            return Direction.EAST if dx > 0 else Direction.WEST
        else:
            return Direction.SOUTH if dy > 0 else Direction.NORTH

    def _get_light_perceptions(self) -> list[Perception]:
        return [
            p
            for p in self.current_perceptions
            if p.stimulus.stimulus_type == StimulusType.LIGHT
        ]

    def _apply_aversion(self, preferred: Direction) -> Direction:
        light_perceptions = self._get_light_perceptions()
        if not light_perceptions:
            return preferred

        # Find the strongest light source
        strongest = max(light_perceptions, key=lambda p: p.perceived_intensity)
        light_dir = (
            1 if strongest.direction[0] > 0 else (-1 if strongest.direction[0] < 0 else 0),
            1 if strongest.direction[1] > 0 else (-1 if strongest.direction[1] < 0 else 0),
        )

        # If preferred direction moves toward light, pick an alternative
        preferred_delta = preferred.value
        moves_toward_light = (
            (preferred_delta[0] != 0 and preferred_delta[0] == light_dir[0])
            or (preferred_delta[1] != 0 and preferred_delta[1] == light_dir[1])
        )

        if moves_toward_light:
            # Try perpendicular directions first, then opposite
            alternatives = [d for d in MOVE_DIRECTIONS if d != preferred]
            for alt in alternatives:
                alt_delta = alt.value
                toward = (
                    (alt_delta[0] != 0 and alt_delta[0] == light_dir[0])
                    or (alt_delta[1] != 0 and alt_delta[1] == light_dir[1])
                )
                if not toward:
                    return alt
            # All directions toward light — stay
            return Direction.STAY

        return preferred

    def _explore(self) -> Direction:
        # Biased random walk: if we perceive relevant stimuli, bias toward them
        urgent = self.drive_system.get_most_urgent()
        if urgent is not None:
            target_type = self._drive_to_stimulus(urgent.drive_type)
            relevant = [
                p
                for p in self.current_perceptions
                if p.stimulus.stimulus_type == target_type
            ]
            if relevant:
                strongest = max(relevant, key=lambda p: p.perceived_intensity)
                return self._direction_toward(strongest.stimulus.position)

        # Pure random exploration
        return random.choice(MOVE_DIRECTIONS)

    def decide(self) -> Direction:
        urgent = self.drive_system.get_most_urgent()
        if urgent is None:
            direction = random.choice(MOVE_DIRECTIONS)
            return self._apply_aversion(direction)

        target_stimulus = self._drive_to_stimulus(urgent.drive_type)

        # Check memory for known location
        remembered_pos = self.memory_system.get_best_location_for(target_stimulus)
        if remembered_pos is not None and remembered_pos != self.position:
            direction = self._direction_toward(remembered_pos)
        else:
            direction = self._explore()

        return self._apply_aversion(direction)

    def post_act(self, environment: Environment) -> None:
        """Called after acting — updates drives, memory, and expectations."""
        # Update drives
        self.drive_system.update()

        # Check what's at the new position and update memory
        stimuli_here = environment.get_stimuli_at(self.position)
        for stimulus in stimuli_here:
            reward = 0.0
            if (
                stimulus.stimulus_type == StimulusType.FOOD
                and self.drive_system.get_level(DriveType.HUNGER) > 0.1
            ):
                self.drive_system.satisfy(DriveType.HUNGER, 0.3)
                reward = 1.0
                stimulus._consumed = True
            elif (
                stimulus.stimulus_type == StimulusType.WATER
                and self.drive_system.get_level(DriveType.THIRST) > 0.1
            ):
                self.drive_system.satisfy(DriveType.THIRST, 0.3)
                reward = 1.0
                stimulus._consumed = True

            self.memory_system.record_experience(
                self.position,
                stimulus.stimulus_type,
                stimulus.intensity,
                reward,
            )

        # Update expectations for stimuli we expected but didn't find
        # (violation of expectations weakens memory)
        for pos, entries in list(self.memory_system.cognitive_map.items()):
            if pos == self.position:
                for entry in entries:
                    actual_stim = [
                        s
                        for s in stimuli_here
                        if s.stimulus_type == entry.stimulus_type
                    ]
                    if actual_stim:
                        self.memory_system.update_expectation(
                            pos,
                            entry.stimulus_type,
                            actual_stim[0].intensity,
                            entry.reward_value,
                        )
                    else:
                        self.memory_system.update_expectation(
                            pos, entry.stimulus_type, 0.0, 0.0
                        )

        # Decay old memories
        self.memory_system.decay()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sowbug.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/agents/sowbug.py tests/test_sowbug.py
git commit -m "feat: add Sowbug agent with Tolman's drive-based decision-making and cognitive map"
```

---

### Task 10: Data Recorder

**Files:**
- Create: `src/some_sim/analysis/recorder.py`
- Create: `tests/test_recorder.py`

**Step 1: Write the failing test**

```python
# tests/test_recorder.py
import json
import csv
import tempfile
from pathlib import Path

from some_sim.agents.sowbug import Sowbug
from some_sim.analysis.recorder import Recorder
from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus, StimulusType


class TestRecorder:
    def _make_setup(self):
        env = Environment(width=10, height=10)
        food = Stimulus(StimulusType.FOOD, (3, 3), intensity=1.0, radius=5.0)
        env.add_stimulus(food)
        agent = Sowbug(position=(5, 5))
        recorder = Recorder(run_id="test_run")
        return env, agent, recorder

    def test_record_tick(self):
        env, agent, recorder = self._make_setup()
        recorder.record_tick(tick=0, agents=[agent], environment=env)
        assert len(recorder.records) == 1
        record = recorder.records[0]
        assert record["tick"] == 0
        assert "agents" in record
        assert "stimuli" in record

    def test_save_json(self):
        env, agent, recorder = self._make_setup()
        recorder.record_tick(tick=0, agents=[agent], environment=env)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        recorder.save_json(path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["records"]) == 1
        assert data["run_id"] == "test_run"

    def test_save_csv(self):
        env, agent, recorder = self._make_setup()
        recorder.record_tick(tick=0, agents=[agent], environment=env)
        recorder.record_tick(tick=1, agents=[agent], environment=env)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        recorder.save_csv(path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert "tick" in rows[0]
        assert "position_x" in rows[0]
        assert "hunger" in rows[0]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_recorder.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/analysis/recorder.py
import csv
import json
from pathlib import Path

from some_sim.core.agent import Agent
from some_sim.core.environment import Environment
from some_sim.systems.drives import DriveType


class Recorder:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.records: list[dict] = []

    def record_tick(
        self, tick: int, agents: list[Agent], environment: Environment
    ) -> None:
        agent_states = [agent.get_state() for agent in agents]
        stimuli_data = [
            {
                "type": s.stimulus_type.value,
                "position": list(s.position),
                "intensity": s.intensity,
            }
            for s in environment.stimuli
        ]
        self.records.append(
            {
                "tick": tick,
                "agents": agent_states,
                "stimuli": stimuli_data,
            }
        )

    def save_json(self, path: str) -> None:
        data = {
            "run_id": self.run_id,
            "records": self.records,
        }
        # Convert non-serializable types
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def save_csv(self, path: str) -> None:
        if not self.records:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "tick",
                    "position_x",
                    "position_y",
                    "orientation",
                    "hunger",
                    "thirst",
                    "temperature",
                    "perception_count",
                ],
            )
            writer.writeheader()
            for record in self.records:
                for agent_state in record["agents"]:
                    drive_levels = agent_state.get("drive_levels", {})
                    pos = agent_state["position"]
                    writer.writerow(
                        {
                            "tick": record["tick"],
                            "position_x": pos[0],
                            "position_y": pos[1],
                            "orientation": agent_state.get("orientation", ""),
                            "hunger": drive_levels.get(DriveType.HUNGER, 0.0),
                            "thirst": drive_levels.get(DriveType.THIRST, 0.0),
                            "temperature": drive_levels.get(
                                DriveType.TEMPERATURE, 0.0
                            ),
                            "perception_count": agent_state.get(
                                "perception_count", 0
                            ),
                        }
                    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_recorder.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/analysis/recorder.py tests/test_recorder.py
git commit -m "feat: add Recorder for tick-level JSON and CSV data logging"
```

---

### Task 11: Simulation Orchestrator

**Files:**
- Create: `src/some_sim/core/simulation.py`
- Create: `tests/test_simulation.py`

**Step 1: Write the failing test**

```python
# tests/test_simulation.py
import random

from some_sim.agents.sowbug import Sowbug
from some_sim.analysis.recorder import Recorder
from some_sim.core.environment import Environment
from some_sim.core.simulation import Simulation
from some_sim.core.stimulus import Stimulus, StimulusType


class TestSimulation:
    def _make_sim(self):
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (10, 10), intensity=1.0, radius=8.0)
        env.add_stimulus(food)
        bug = Sowbug(position=(5, 5))
        recorder = Recorder(run_id="test")
        return Simulation(
            environment=env, agents=[bug], recorder=recorder, max_ticks=100
        )

    def test_creation(self):
        sim = self._make_sim()
        assert sim.tick_count == 0
        assert sim.max_ticks == 100

    def test_step_advances_tick(self):
        random.seed(42)
        sim = self._make_sim()
        sim.step()
        assert sim.tick_count == 1

    def test_step_records_data(self):
        random.seed(42)
        sim = self._make_sim()
        sim.step()
        assert len(sim.recorder.records) == 1

    def test_agent_moves_during_step(self):
        random.seed(42)
        sim = self._make_sim()
        initial_pos = sim.agents[0].position
        sim.step()
        # Agent should have attempted to move (might stay if blocked, but position is updated)
        assert sim.agents[0].position is not None

    def test_run_multiple_ticks(self):
        random.seed(42)
        sim = self._make_sim()
        sim.run(10)
        assert sim.tick_count == 10
        assert len(sim.recorder.records) == 10

    def test_get_state(self):
        sim = self._make_sim()
        state = sim.get_state()
        assert "tick" in state
        assert "agents" in state
        assert "stimuli" in state
        assert state["tick"] == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_simulation.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/core/simulation.py
from some_sim.analysis.recorder import Recorder
from some_sim.core.agent import Agent
from some_sim.core.environment import Environment


class Simulation:
    def __init__(
        self,
        environment: Environment,
        agents: list[Agent],
        recorder: Recorder,
        max_ticks: int = 1000,
    ) -> None:
        self.environment = environment
        self.agents = agents
        self.recorder = recorder
        self.max_ticks = max_ticks
        self.tick_count = 0

    def step(self) -> None:
        for agent in self.agents:
            agent.perceive(self.environment)
            direction = agent.decide()
            agent.act(direction, self.environment)
            # Call post_act if the agent has it (e.g., Sowbug)
            if hasattr(agent, "post_act"):
                agent.post_act(self.environment)

        self.environment.update()
        self.recorder.record_tick(
            tick=self.tick_count,
            agents=self.agents,
            environment=self.environment,
        )
        self.tick_count += 1

    def run(self, n_ticks: int | None = None) -> None:
        ticks = n_ticks if n_ticks is not None else self.max_ticks
        for _ in range(ticks):
            self.step()

    def get_state(self) -> dict:
        return {
            "tick": self.tick_count,
            "agents": [agent.get_state() for agent in self.agents],
            "stimuli": [
                {
                    "type": s.stimulus_type.value,
                    "position": list(s.position),
                    "intensity": s.intensity,
                }
                for s in self.environment.stimuli
            ],
        }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_simulation.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add src/some_sim/core/simulation.py tests/test_simulation.py
git commit -m "feat: add Simulation orchestrator with step/run lifecycle"
```

---

### Task 12: YAML Config Loading

**Files:**
- Create: `src/some_sim/core/config.py`
- Create: `tests/test_config.py`
- Create: `configs/sowbug_basic.yaml`

**Step 1: Write the failing test**

```python
# tests/test_config.py
import tempfile
from pathlib import Path

import yaml

from some_sim.core.config import SimulationConfig, load_config, build_simulation


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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/core/config.py
from dataclasses import dataclass, field

import yaml

from some_sim.agents.sowbug import Sowbug
from some_sim.analysis.recorder import Recorder
from some_sim.core.environment import Environment
from some_sim.core.simulation import Simulation
from some_sim.core.stimulus import Stimulus, StimulusType


STIMULUS_TYPE_MAP = {
    "food": StimulusType.FOOD,
    "water": StimulusType.WATER,
    "light": StimulusType.LIGHT,
    "heat": StimulusType.HEAT,
    "obstacle": StimulusType.OBSTACLE,
}


@dataclass
class StimulusConfig:
    stimulus_type: str
    position: tuple[int, int]
    intensity: float
    radius: float
    depletes: bool = False
    depletion_rate: float = 0.0


@dataclass
class AgentConfig:
    agent_type: str
    position: tuple[int, int]
    params: dict = field(default_factory=dict)


@dataclass
class SimulationConfig:
    grid_width: int
    grid_height: int
    max_ticks: int
    random_seed: int
    stimuli: list[StimulusConfig]
    agent: AgentConfig


def load_config(path: str) -> SimulationConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    grid = raw["grid"]
    sim = raw.get("simulation", {})
    stimuli_raw = raw.get("stimuli", [])
    agent_raw = raw.get("agent", {"type": "sowbug", "position": [5, 5]})

    stimuli = []
    for s in stimuli_raw:
        stimuli.append(
            StimulusConfig(
                stimulus_type=s["type"],
                position=tuple(s["position"]),
                intensity=s.get("intensity", 1.0),
                radius=s.get("radius", 5.0),
                depletes=s.get("depletes", False),
                depletion_rate=s.get("depletion_rate", 0.0),
            )
        )

    agent_params = {
        k: v
        for k, v in agent_raw.items()
        if k not in ("type", "position")
    }

    return SimulationConfig(
        grid_width=grid["width"],
        grid_height=grid["height"],
        max_ticks=sim.get("max_ticks", 1000),
        random_seed=sim.get("random_seed", 42),
        stimuli=stimuli,
        agent=AgentConfig(
            agent_type=agent_raw.get("type", "sowbug"),
            position=tuple(agent_raw["position"]),
            params=agent_params,
        ),
    )


def build_simulation(config: SimulationConfig) -> Simulation:
    import random as rng

    rng.seed(config.random_seed)

    env = Environment(width=config.grid_width, height=config.grid_height)
    for sc in config.stimuli:
        env.add_stimulus(
            Stimulus(
                stimulus_type=STIMULUS_TYPE_MAP[sc.stimulus_type],
                position=sc.position,
                intensity=sc.intensity,
                radius=sc.radius,
                depletes=sc.depletes,
                depletion_rate=sc.depletion_rate,
            )
        )

    if config.agent.agent_type == "sowbug":
        agent = Sowbug(position=config.agent.position, **config.agent.params)
    else:
        raise ValueError(f"Unknown agent type: {config.agent.agent_type}")

    recorder = Recorder(run_id=f"run_seed{config.random_seed}")

    return Simulation(
        environment=env,
        agents=[agent],
        recorder=recorder,
        max_ticks=config.max_ticks,
    )
```

**Step 4: Create the default config file**

```yaml
# configs/sowbug_basic.yaml
grid:
  width: 20
  height: 20

simulation:
  max_ticks: 1000
  random_seed: 42

stimuli:
  - type: food
    position: [15, 10]
    intensity: 1.0
    radius: 6.0
    depletes: true
    depletion_rate: 0.05

  - type: food
    position: [3, 15]
    intensity: 0.8
    radius: 5.0
    depletes: true
    depletion_rate: 0.05

  - type: water
    position: [10, 3]
    intensity: 0.9
    radius: 4.0

  - type: light
    position: [10, 10]
    intensity: 1.0
    radius: 8.0

  - type: heat
    position: [18, 18]
    intensity: 0.7
    radius: 5.0

  - type: obstacle
    position: [7, 7]
    intensity: 1.0
    radius: 0.0

  - type: obstacle
    position: [7, 8]
    intensity: 1.0
    radius: 0.0

  - type: obstacle
    position: [7, 9]
    intensity: 1.0
    radius: 0.0

agent:
  type: sowbug
  position: [5, 5]
  hunger_rate: 0.01
  thirst_rate: 0.008
  temperature_rate: 0.005
  perception_radius: 5.0
  learning_rate: 0.1
  decay_rate: 0.01
```

**Step 5: Run tests to verify**

Run: `uv run pytest tests/test_config.py -v`
Expected: All 3 tests PASS

**Step 6: Commit**

```bash
git add src/some_sim/core/config.py tests/test_config.py configs/sowbug_basic.yaml
git commit -m "feat: add YAML config loading and simulation builder"
```

---

### Task 13: CLI Entry Point

**Files:**
- Modify: `src/some_sim/__main__.py`

**Step 1: Write implementation**

```python
# src/some_sim/__main__.py
import argparse
import sys

from some_sim.core.config import build_simulation, load_config


def cmd_run(args):
    config = load_config(args.config)
    if args.ticks:
        config.max_ticks = args.ticks
    sim = build_simulation(config)
    print(f"Running simulation: {config.max_ticks} ticks, seed {config.random_seed}")
    sim.run()
    print(f"Simulation complete. {sim.tick_count} ticks executed.")

    output = args.output or f"output_{sim.recorder.run_id}"
    sim.recorder.save_json(f"{output}.json")
    sim.recorder.save_csv(f"{output}.csv")
    print(f"Data saved to {output}.json and {output}.csv")


def cmd_serve(args):
    print("Starting web server...")
    from some_sim.web.server import start_server

    config = load_config(args.config) if args.config else None
    start_server(config=config, port=args.port)


def cmd_analyze(args):
    print("Analysis tools not yet implemented.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="some-sim",
        description="Schematic Sowbug simulation platform",
    )
    subparsers = parser.add_subparsers(dest="command")

    # run
    run_parser = subparsers.add_parser("run", help="Run a headless simulation")
    run_parser.add_argument("--config", required=True, help="Path to YAML config")
    run_parser.add_argument("--ticks", type=int, help="Override max ticks")
    run_parser.add_argument("--output", help="Output file prefix")
    run_parser.set_defaults(func=cmd_run)

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start web visualization")
    serve_parser.add_argument("--config", help="Path to YAML config")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port number")
    serve_parser.set_defaults(func=cmd_serve)

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze simulation data")
    analyze_parser.add_argument("--input", required=True, help="Path to JSON data file")
    analyze_parser.add_argument("--plot", help="Plot type to generate")
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
```

**Step 2: Verify CLI works**

Run: `uv run python -m some_sim --help`
Expected: Shows help with run, serve, analyze subcommands

Run: `uv run python -m some_sim run --config configs/sowbug_basic.yaml --ticks 100`
Expected: Runs 100 ticks, saves output files

**Step 3: Commit**

```bash
git add src/some_sim/__main__.py
git commit -m "feat: add CLI with run, serve, and analyze subcommands"
```

---

### Task 14: Web Server

**Files:**
- Create: `src/some_sim/web/server.py`

**Step 1: Write implementation**

```python
# src/some_sim/web/server.py
import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from some_sim.core.config import SimulationConfig, build_simulation, load_config
from some_sim.core.simulation import Simulation

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Schematic Sowbug")

# Simulation state
_simulation: Simulation | None = None
_config: SimulationConfig | None = None
_running = False
_speed = 5  # ticks per second


def _init_simulation():
    global _simulation
    if _config is not None:
        _simulation = build_simulation(_config)


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(index_path.read_text())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global _running, _speed, _simulation
    await ws.accept()

    if _simulation is None:
        _init_simulation()

    try:
        while True:
            # Check for control messages (non-blocking)
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                data = json.loads(msg)
                action = data.get("action")
                if action == "play":
                    _running = True
                elif action == "pause":
                    _running = False
                elif action == "step":
                    if _simulation:
                        _simulation.step()
                        await ws.send_text(
                            json.dumps(_simulation.get_state(), default=str)
                        )
                elif action == "speed":
                    _speed = max(1, min(60, data.get("value", 5)))
                elif action == "reset":
                    _init_simulation()
                    if _simulation:
                        await ws.send_text(
                            json.dumps(_simulation.get_state(), default=str)
                        )
                elif action == "add_stimulus":
                    if _simulation:
                        from some_sim.core.stimulus import Stimulus, StimulusType

                        stim_type = StimulusType(data["stimulus_type"])
                        _simulation.environment.add_stimulus(
                            Stimulus(
                                stimulus_type=stim_type,
                                position=tuple(data["position"]),
                                intensity=data.get("intensity", 1.0),
                                radius=data.get("radius", 5.0),
                            )
                        )
            except asyncio.TimeoutError:
                pass

            # Run simulation if playing
            if _running and _simulation:
                _simulation.step()
                state = _simulation.get_state()
                await ws.send_text(json.dumps(state, default=str))
                await asyncio.sleep(1.0 / _speed)
            else:
                await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        pass


# Mount static files AFTER routes so / isn't overridden
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def start_server(config: SimulationConfig | None = None, port: int = 8000):
    global _config
    _config = config
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**Step 2: Verify server starts**

Run: `uv run python -m some_sim serve --config configs/sowbug_basic.yaml --port 8000`
Expected: Server starts (will fail on missing static files — that's OK, next task creates them)

**Step 3: Commit**

```bash
git add src/some_sim/web/server.py
git commit -m "feat: add FastAPI web server with WebSocket simulation streaming"
```

---

### Task 15: Web Frontend

**Files:**
- Create: `src/some_sim/web/static/index.html`
- Create: `src/some_sim/web/static/main.js`
- Create: `src/some_sim/web/static/style.css`

**Step 1: Write index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schematic Sowbug</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div id="app">
        <header>
            <h1>Schematic Sowbug Simulation</h1>
            <span id="tick-counter">Tick: 0</span>
        </header>
        <main>
            <div id="grid-container">
                <canvas id="grid-canvas" width="600" height="600"></canvas>
            </div>
            <aside id="dashboard">
                <section id="drives">
                    <h2>Drives</h2>
                    <div class="drive-bar">
                        <label>Hunger</label>
                        <div class="bar-bg"><div id="bar-hunger" class="bar-fill hunger"></div></div>
                        <span id="val-hunger">0.00</span>
                    </div>
                    <div class="drive-bar">
                        <label>Thirst</label>
                        <div class="bar-bg"><div id="bar-thirst" class="bar-fill thirst"></div></div>
                        <span id="val-thirst">0.00</span>
                    </div>
                    <div class="drive-bar">
                        <label>Temperature</label>
                        <div class="bar-bg"><div id="bar-temperature" class="bar-fill temperature"></div></div>
                        <span id="val-temperature">0.00</span>
                    </div>
                </section>
                <section id="info">
                    <h2>Agent</h2>
                    <p>Position: <span id="agent-pos">-</span></p>
                    <p>Orientation: <span id="agent-orient">-</span></p>
                </section>
                <section id="controls">
                    <h2>Controls</h2>
                    <div id="btn-group">
                        <button id="btn-play">Play</button>
                        <button id="btn-pause">Pause</button>
                        <button id="btn-step">Step</button>
                        <button id="btn-reset">Reset</button>
                    </div>
                    <div id="speed-control">
                        <label>Speed: <span id="speed-val">5</span> tps</label>
                        <input type="range" id="speed-slider" min="1" max="30" value="5">
                    </div>
                </section>
                <section id="place-stimulus">
                    <h2>Place Stimulus</h2>
                    <select id="stim-type">
                        <option value="food">Food</option>
                        <option value="water">Water</option>
                        <option value="light">Light</option>
                        <option value="heat">Heat</option>
                        <option value="obstacle">Obstacle</option>
                    </select>
                    <p><em>Click on grid to place</em></p>
                </section>
            </aside>
        </main>
    </div>
    <script src="/static/main.js"></script>
</body>
</html>
```

**Step 2: Write main.js**

```javascript
// main.js — Schematic Sowbug frontend
const canvas = document.getElementById("grid-canvas");
const ctx = canvas.getContext("2d");

const GRID_SIZE = 20;
const CELL_SIZE = canvas.width / GRID_SIZE;

const COLORS = {
    food: "#4CAF50",
    water: "#2196F3",
    light: "#FFEB3B",
    heat: "#F44336",
    obstacle: "#424242",
    agent: "#FF9800",
    background: "#FAFAFA",
    gridLine: "#E0E0E0",
};

let ws = null;
let latestState = null;

function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onmessage = (event) => {
        latestState = JSON.parse(event.data);
        render(latestState);
        updateDashboard(latestState);
    };

    ws.onclose = () => {
        setTimeout(connectWebSocket, 2000);
    };
}

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

function render(state) {
    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid lines
    ctx.strokeStyle = COLORS.gridLine;
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= GRID_SIZE; i++) {
        ctx.beginPath();
        ctx.moveTo(i * CELL_SIZE, 0);
        ctx.lineTo(i * CELL_SIZE, canvas.height);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i * CELL_SIZE);
        ctx.lineTo(canvas.width, i * CELL_SIZE);
        ctx.stroke();
    }

    // Stimuli
    if (state.stimuli) {
        for (const stim of state.stimuli) {
            const [x, y] = stim.position;
            ctx.fillStyle = COLORS[stim.type] || "#999";
            ctx.globalAlpha = Math.max(0.3, stim.intensity);
            ctx.fillRect(x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2);
            ctx.globalAlpha = 1.0;
        }
    }

    // Agents
    if (state.agents) {
        for (const agent of state.agents) {
            const [x, y] = agent.position;
            const cx = x * CELL_SIZE + CELL_SIZE / 2;
            const cy = y * CELL_SIZE + CELL_SIZE / 2;
            const r = CELL_SIZE / 2.5;

            ctx.fillStyle = COLORS.agent;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fill();

            // Orientation indicator
            const orientMap = { NORTH: [0, -1], SOUTH: [0, 1], EAST: [1, 0], WEST: [-1, 0] };
            const dir = orientMap[agent.orientation] || [0, 0];
            ctx.strokeStyle = "#BF360C";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + dir[0] * r, cy + dir[1] * r);
            ctx.stroke();
        }
    }

    // Tick counter
    document.getElementById("tick-counter").textContent = `Tick: ${state.tick}`;
}

function updateDashboard(state) {
    if (!state.agents || state.agents.length === 0) return;
    const agent = state.agents[0];
    const drives = agent.drive_levels || {};

    for (const [name, key] of [["hunger", "HUNGER"], ["thirst", "THIRST"], ["temperature", "TEMPERATURE"]]) {
        // Drive levels come as dict with DriveType keys — handle both string formats
        let val = 0;
        for (const [k, v] of Object.entries(drives)) {
            if (k.toLowerCase().includes(name)) {
                val = v;
                break;
            }
        }
        const bar = document.getElementById(`bar-${name}`);
        const valEl = document.getElementById(`val-${name}`);
        if (bar) bar.style.width = `${val * 100}%`;
        if (valEl) valEl.textContent = val.toFixed(2);
    }

    document.getElementById("agent-pos").textContent =
        `(${agent.position[0]}, ${agent.position[1]})`;
    document.getElementById("agent-orient").textContent = agent.orientation;
}

// Controls
document.getElementById("btn-play").onclick = () => send({ action: "play" });
document.getElementById("btn-pause").onclick = () => send({ action: "pause" });
document.getElementById("btn-step").onclick = () => send({ action: "step" });
document.getElementById("btn-reset").onclick = () => send({ action: "reset" });

const speedSlider = document.getElementById("speed-slider");
const speedVal = document.getElementById("speed-val");
speedSlider.oninput = () => {
    speedVal.textContent = speedSlider.value;
    send({ action: "speed", value: parseInt(speedSlider.value) });
};

// Click to place stimulus
canvas.onclick = (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / CELL_SIZE);
    const y = Math.floor((e.clientY - rect.top) / CELL_SIZE);
    const stimType = document.getElementById("stim-type").value;
    send({
        action: "add_stimulus",
        stimulus_type: stimType,
        position: [x, y],
        intensity: 1.0,
        radius: 5.0,
    });
};

// Start
connectWebSocket();
```

**Step 3: Write style.css**

```css
/* style.css — Schematic Sowbug */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
}

#app { max-width: 1100px; margin: 0 auto; padding: 1rem; }

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #ddd;
}

header h1 { font-size: 1.3rem; }
#tick-counter { font-family: monospace; font-size: 1.1rem; }

main { display: flex; gap: 1.5rem; }

#grid-container {
    flex-shrink: 0;
    background: white;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px;
}

#grid-canvas { display: block; cursor: crosshair; }

aside#dashboard { flex: 1; min-width: 240px; }

aside section {
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
}

aside h2 { font-size: 0.9rem; margin-bottom: 0.5rem; color: #666; text-transform: uppercase; }

.drive-bar { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
.drive-bar label { width: 80px; font-size: 0.85rem; }
.bar-bg { flex: 1; height: 14px; background: #eee; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.2s; }
.bar-fill.hunger { background: #4CAF50; }
.bar-fill.thirst { background: #2196F3; }
.bar-fill.temperature { background: #F44336; }
.drive-bar span { width: 35px; font-size: 0.8rem; font-family: monospace; text-align: right; }

#info p { font-size: 0.85rem; margin-bottom: 0.2rem; }
#info span { font-family: monospace; }

#btn-group { display: flex; gap: 0.4rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
#btn-group button {
    padding: 0.4rem 0.8rem;
    border: 1px solid #ccc;
    border-radius: 3px;
    background: white;
    cursor: pointer;
    font-size: 0.85rem;
}
#btn-group button:hover { background: #f0f0f0; }

#speed-control { font-size: 0.85rem; }
#speed-slider { width: 100%; margin-top: 0.3rem; }

#place-stimulus select {
    width: 100%;
    padding: 0.3rem;
    margin-bottom: 0.3rem;
    border: 1px solid #ccc;
    border-radius: 3px;
}
#place-stimulus em { font-size: 0.8rem; color: #999; }
```

**Step 4: Verify end-to-end**

Run: `uv run python -m some_sim serve --config configs/sowbug_basic.yaml`
Open browser to `http://localhost:8000`
Expected: Grid renders, controls work, WebSocket streams state on Play

**Step 5: Commit**

```bash
git add src/some_sim/web/static/
git commit -m "feat: add browser frontend with canvas grid, dashboard, and controls"
```

---

### Task 16: Analysis Tools

**Files:**
- Create: `src/some_sim/analysis/plots.py`
- Create: `tests/test_plots.py`

**Step 1: Write the failing test**

```python
# tests/test_plots.py
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for testing

from matplotlib.figure import Figure

from some_sim.analysis.plots import (
    plot_drive_levels,
    plot_exploration_heatmap,
    plot_learning_curve,
    plot_path_efficiency,
)
from some_sim.systems.drives import DriveType


def _make_records(n=50):
    records = []
    for i in range(n):
        records.append({
            "tick": i,
            "agents": [
                {
                    "position": (i % 10, i // 10),
                    "orientation": "NORTH",
                    "drive_levels": {
                        DriveType.HUNGER: max(0, 0.8 - i * 0.01),
                        DriveType.THIRST: max(0, 0.5 - i * 0.005),
                        DriveType.TEMPERATURE: 0.1,
                    },
                    "perception_count": 2,
                }
            ],
            "stimuli": [],
        })
    return records


class TestPlots:
    def test_plot_drive_levels_returns_figure(self):
        records = _make_records()
        fig = plot_drive_levels(records)
        assert isinstance(fig, Figure)

    def test_plot_exploration_heatmap_returns_figure(self):
        records = _make_records()
        fig = plot_exploration_heatmap(records, grid_size=(10, 10))
        assert isinstance(fig, Figure)

    def test_plot_learning_curve_returns_figure(self):
        records = _make_records()
        fig = plot_learning_curve(records)
        assert isinstance(fig, Figure)

    def test_plot_path_efficiency_returns_figure(self):
        records = _make_records()
        fig = plot_path_efficiency(records, optimal_distance=5.0)
        assert isinstance(fig, Figure)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_plots.py -v`
Expected: FAIL — ImportError

**Step 3: Write implementation**

```python
# src/some_sim/analysis/plots.py
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from some_sim.systems.drives import DriveType


def _extract_agent_data(records: list[dict], agent_index: int = 0):
    """Extract per-tick data for a single agent."""
    ticks = []
    positions = []
    drive_data = {DriveType.HUNGER: [], DriveType.THIRST: [], DriveType.TEMPERATURE: []}

    for record in records:
        agents = record.get("agents", [])
        if agent_index >= len(agents):
            continue
        agent = agents[agent_index]
        ticks.append(record["tick"])
        positions.append(agent["position"])
        for dt in drive_data:
            drive_data[dt].append(agent.get("drive_levels", {}).get(dt, 0.0))

    return ticks, positions, drive_data


def plot_drive_levels(records: list[dict], agent_index: int = 0) -> Figure:
    ticks, _, drive_data = _extract_agent_data(records, agent_index)

    fig, ax = plt.subplots(figsize=(10, 4))
    colors = {DriveType.HUNGER: "#4CAF50", DriveType.THIRST: "#2196F3", DriveType.TEMPERATURE: "#F44336"}

    for dt, values in drive_data.items():
        ax.plot(ticks, values, label=dt.value.capitalize(), color=colors.get(dt, "#999"))

    ax.set_xlabel("Tick")
    ax.set_ylabel("Drive Level")
    ax.set_title("Drive Levels Over Time")
    ax.legend()
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    return fig


def plot_exploration_heatmap(
    records: list[dict], grid_size: tuple[int, int], agent_index: int = 0
) -> Figure:
    _, positions, _ = _extract_agent_data(records, agent_index)

    heatmap = np.zeros(grid_size)
    for pos in positions:
        x, y = pos[0], pos[1]
        if 0 <= x < grid_size[0] and 0 <= y < grid_size[1]:
            heatmap[y][x] += 1

    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(heatmap, cmap="YlOrRd", interpolation="nearest")
    ax.set_title("Exploration Heatmap (Visit Frequency)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    fig.colorbar(im, ax=ax, label="Visit Count")
    plt.tight_layout()
    return fig


def plot_learning_curve(
    records: list[dict], window: int = 20, agent_index: int = 0
) -> Figure:
    _, _, drive_data = _extract_agent_data(records, agent_index)
    hunger = drive_data[DriveType.HUNGER]

    # Compute rolling average of satisfaction events (hunger decreases)
    satisfactions = []
    for i in range(1, len(hunger)):
        satisfactions.append(1.0 if hunger[i] < hunger[i - 1] else 0.0)

    if len(satisfactions) < window:
        window = max(1, len(satisfactions))

    rolling = []
    for i in range(len(satisfactions)):
        start = max(0, i - window + 1)
        rolling.append(sum(satisfactions[start : i + 1]) / (i - start + 1))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(range(1, len(rolling) + 1), rolling, color="#4CAF50")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Satisfaction Rate (rolling avg)")
    ax.set_title("Learning Curve — Drive Satisfaction Over Time")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    return fig


def plot_path_efficiency(
    records: list[dict], optimal_distance: float, agent_index: int = 0
) -> Figure:
    _, positions, _ = _extract_agent_data(records, agent_index)

    cumulative_dist = [0.0]
    for i in range(1, len(positions)):
        dx = positions[i][0] - positions[i - 1][0]
        dy = positions[i][1] - positions[i - 1][1]
        cumulative_dist.append(cumulative_dist[-1] + math.sqrt(dx * dx + dy * dy))

    # Efficiency = optimal / actual (capped at 1.0)
    efficiency = []
    for d in cumulative_dist:
        if d == 0:
            efficiency.append(1.0)
        else:
            efficiency.append(min(1.0, optimal_distance / d))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(range(len(efficiency)), efficiency, color="#FF9800")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Path Efficiency")
    ax.set_title("Path Efficiency Over Time (optimal / actual distance)")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    return fig


def save_plot(fig: Figure, path: str) -> None:
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_plots.py -v`
Expected: All 4 tests PASS

**Step 5: Update CLI analyze command**

Update `cmd_analyze` in `src/some_sim/__main__.py`:

```python
def cmd_analyze(args):
    import json
    from some_sim.analysis.plots import (
        plot_drive_levels,
        plot_exploration_heatmap,
        plot_learning_curve,
        save_plot,
    )

    with open(args.input) as f:
        data = json.load(f)

    records = data["records"]
    plot_type = args.plot or "drives"
    prefix = args.input.rsplit(".", 1)[0]

    if plot_type == "drives":
        fig = plot_drive_levels(records)
        save_plot(fig, f"{prefix}_drives.png")
        print(f"Saved: {prefix}_drives.png")
    elif plot_type == "heatmap":
        fig = plot_exploration_heatmap(records, grid_size=(20, 20))
        save_plot(fig, f"{prefix}_heatmap.png")
        print(f"Saved: {prefix}_heatmap.png")
    elif plot_type == "learning":
        fig = plot_learning_curve(records)
        save_plot(fig, f"{prefix}_learning.png")
        print(f"Saved: {prefix}_learning.png")
    else:
        print(f"Unknown plot type: {plot_type}")
        print("Available: drives, heatmap, learning")
```

**Step 6: Run all tests**

Run: `uv run pytest -v`
Expected: All tests across all files PASS

**Step 7: Commit**

```bash
git add src/some_sim/analysis/plots.py tests/test_plots.py src/some_sim/__main__.py
git commit -m "feat: add analysis tools with drive, heatmap, learning curve, and path efficiency plots"
```

---

## Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | Project scaffolding | - |
| 2 | Stimulus model | 8 |
| 3 | Environment | 10 |
| 4 | DriveSystem | 12 |
| 5 | SensorSystem | 6 |
| 6 | MotorSystem | 9 |
| 7 | MemorySystem (cognitive map) | 11 |
| 8 | Base Agent | 5 |
| 9 | Sowbug agent | 9 |
| 10 | Data Recorder | 3 |
| 11 | Simulation orchestrator | 6 |
| 12 | YAML config loading | 3 |
| 13 | CLI entry point | - |
| 14 | Web server (FastAPI) | - |
| 15 | Web frontend (Canvas + JS) | - |
| 16 | Analysis tools | 4 |
| **Total** | | **86** |
