# Disappointment-Driven Extinction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the exploration stall bug where the sowbug gets stuck revisiting depleted stimulus locations by adding a disappointment counter that accelerates memory extinction.

**Architecture:** Add a `disappointments` field to `MemoryEntry` that tracks consecutive failed visits. In `update_expectation()`, when a stimulus is completely absent (intensity=0, reward=0), increment the counter and apply exponential strength decay: `strength -= learning_rate * 2^disappointments`. Reset the counter when the stimulus is found or re-recorded. This produces a realistic extinction curve (persist 2-3 visits, then rapid drop-off).

**Tech Stack:** Python 3.12, pytest

---

### Task 1: Add disappointments field to MemoryEntry

**Files:**
- Modify: `src/tolmans_sowbug_playground/systems/memory.py:9-14`
- Test: `tests/test_memory.py`

**Step 1: Write the failing test**

Add to `TestMemoryEntry` class in `tests/test_memory.py`:

```python
def test_creation_default_disappointments(self):
    entry = MemoryEntry(
        stimulus_type=StimulusType.FOOD,
        expected_intensity=0.8,
        reward_value=1.0,
    )
    assert entry.disappointments == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_memory.py::TestMemoryEntry::test_creation_default_disappointments -v`
Expected: FAIL — `AttributeError: 'MemoryEntry' object has no attribute 'disappointments'`

**Step 3: Write minimal implementation**

In `src/tolmans_sowbug_playground/systems/memory.py`, modify the `MemoryEntry` dataclass:

```python
@dataclass
class MemoryEntry:
    stimulus_type: StimulusType
    expected_intensity: float
    reward_value: float
    strength: float = 1.0
    disappointments: int = 0
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_memory.py::TestMemoryEntry -v`
Expected: PASS (both old and new tests)

**Step 5: Commit**

```bash
git add src/tolmans_sowbug_playground/systems/memory.py tests/test_memory.py
git commit -m "feat(memory): add disappointments counter to MemoryEntry"
```

---

### Task 2: Accelerated extinction in update_expectation

**Files:**
- Modify: `src/tolmans_sowbug_playground/systems/memory.py:197-225`
- Test: `tests/test_memory.py`

**Step 1: Write the failing tests**

Add a new test class in `tests/test_memory.py`:

```python
class TestDisappointmentExtinction:
    def test_first_disappointment_increments_counter(self):
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry.disappointments == 1

    def test_disappointments_accumulate(self):
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry.disappointments == 3

    def test_strength_decays_exponentially_with_disappointments(self):
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        # Visit 1: strength -= 0.1 * 2^1 = 0.2 → 0.8
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert abs(entry.strength - 0.8) < 1e-9
        # Visit 2: strength -= 0.1 * 2^2 = 0.4 → 0.4
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        assert abs(entry.strength - 0.4) < 1e-9
        # Visit 3: strength -= 0.1 * 2^3 = 0.8 → clamped to 0.0
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        assert entry.strength == 0.0

    def test_extinction_curve_forgotten_by_visit_four(self):
        """With default learning_rate=0.1, location forgotten within 3-4 visits."""
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        for _ in range(4):
            mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry.strength == 0.0

    def test_stimulus_present_resets_disappointments(self):
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        # Two disappointments
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry.disappointments == 2
        # Stimulus returns — reset
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.8, 1.0)
        assert entry.disappointments == 0

    def test_partial_stimulus_not_treated_as_disappointment(self):
        """Reduced but non-zero stimulus should not trigger disappointment."""
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.3, 0.5)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry.disappointments == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_memory.py::TestDisappointmentExtinction -v`
Expected: FAIL — disappointments not incremented, strength decay unchanged

**Step 3: Write implementation**

Replace the strength-update section of `update_expectation()` in `memory.py` (lines 219-225):

```python
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
    pre_error = (
        abs(actual_intensity - entry.expected_intensity)
        + abs(actual_reward - entry.reward_value)
    ) / 2.0
    self.cumulative_prediction_error += pre_error
    self.prediction_count += 1
    entry.expected_intensity += self.learning_rate * (
        actual_intensity - entry.expected_intensity
    )
    entry.reward_value += self.learning_rate * (
        actual_reward - entry.reward_value
    )

    if actual_intensity == 0.0 and actual_reward == 0.0:
        # Disappointment-driven extinction: exponential strength decay
        entry.disappointments += 1
        entry.strength = max(
            0.0, entry.strength - self.learning_rate * (2 ** entry.disappointments)
        )
    else:
        # Stimulus present — reset disappointments, use normal learning
        entry.disappointments = 0
        intensity_error = abs(actual_intensity - entry.expected_intensity)
        reward_error = abs(actual_reward - entry.reward_value)
        avg_error = (intensity_error + reward_error) / 2.0
        if avg_error < 0.2:
            entry.strength = min(1.0, entry.strength + self.learning_rate * 0.5)
        else:
            entry.strength = max(0.0, entry.strength - avg_error * self.learning_rate)
```

**Step 4: Run all memory tests**

Run: `uv run python -m pytest tests/test_memory.py -v`
Expected: ALL PASS (new tests + existing tests unchanged)

**Step 5: Commit**

```bash
git add src/tolmans_sowbug_playground/systems/memory.py tests/test_memory.py
git commit -m "feat(memory): disappointment-driven extinction in update_expectation"
```

---

### Task 3: Reset disappointments on rediscovery in record_experience

**Files:**
- Modify: `src/tolmans_sowbug_playground/systems/memory.py:33-55`
- Test: `tests/test_memory.py`

**Step 1: Write the failing test**

Add to `TestDisappointmentExtinction` class:

```python
    def test_record_experience_resets_disappointments(self):
        mem = MemorySystem(learning_rate=0.1)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        # Accumulate disappointments
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        mem.update_expectation((5, 5), StimulusType.FOOD, 0.0, 0.0)
        entry = mem.get_expected((5, 5), StimulusType.FOOD)
        assert entry.disappointments == 2
        # Re-record experience (stimulus respawned)
        mem.record_experience((5, 5), StimulusType.FOOD, intensity=0.8, reward=1.0)
        assert entry.disappointments == 0
        assert entry.strength == 1.0
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_memory.py::TestDisappointmentExtinction::test_record_experience_resets_disappointments -v`
Expected: FAIL — disappointments not reset by record_experience

**Step 3: Write minimal implementation**

In `record_experience()`, add `entry.disappointments = 0` alongside the existing `entry.strength = 1.0`:

```python
def record_experience(
    self,
    position: tuple[int, int],
    stimulus_type: StimulusType,
    intensity: float,
    reward: float,
) -> None:
    if position not in self.cognitive_map:
        self.cognitive_map[position] = []
    for entry in self.cognitive_map[position]:
        if entry.stimulus_type == stimulus_type:
            entry.strength = 1.0
            entry.disappointments = 0
            return
    self.cognitive_map[position].append(
        MemoryEntry(
            stimulus_type=stimulus_type,
            expected_intensity=intensity,
            reward_value=reward,
            strength=1.0,
        )
    )
```

**Step 4: Run all memory tests**

Run: `uv run python -m pytest tests/test_memory.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/tolmans_sowbug_playground/systems/memory.py tests/test_memory.py
git commit -m "feat(memory): reset disappointments on stimulus rediscovery"
```

---

### Task 4: Full test suite verification

**Files:**
- All test files

**Step 1: Run full test suite**

Run: `uv run python -m pytest -v`
Expected: ALL PASS — no regressions in sowbug, environment, or other tests

**Step 2: Commit (if any adjustments were needed)**

Only if test fixes were required. Otherwise skip.

---
