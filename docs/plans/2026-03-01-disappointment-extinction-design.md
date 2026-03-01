# Disappointment-Driven Extinction Design

**Date:** 2026-03-01
**Problem:** Sowbug gets stuck revisiting depleted stimulus locations because memory entries persist long after stimuli are consumed.

## Root Cause

When a stimulus is consumed, the `MemoryEntry` retains its original `reward_value` and high `strength`. The `update_expectation()` method only reduces strength by ~0.1 per failed visit (via `learning_rate`), so it takes 9-10 ticks of back-and-forth before the memory fades. Meanwhile, `get_best_location_for()` keeps scoring the depleted location highest, and automatic navigation (triggered when `avg_strength >= 0.7`) locks out exploration.

## Solution: Disappointment Multiplier

Track consecutive disappointments per memory entry. Accelerate strength decay exponentially with each failed visit, producing a realistic extinction curve.

### Changes

#### 1. `MemoryEntry` — add `disappointments: int = 0`

Tracks consecutive visits where the expected stimulus was absent.

#### 2. `update_expectation()` — accelerated decay on disappointment

When `actual_intensity == 0.0` and `actual_reward == 0.0`:
- Increment `entry.disappointments`
- Decay strength by `learning_rate * (2 ** disappointments)` instead of the small error-based decay

When stimulus is present (`actual_reward > 0`):
- Reset `entry.disappointments = 0`
- Existing reinforcement logic unchanged

#### 3. `record_experience()` — reset on rediscovery

When refreshing an existing entry, reset `disappointments = 0` alongside `strength = 1.0`.

### Extinction Curve

```
Visit 1: strength 1.0 → ~0.9    (persists)
Visit 2: strength 0.9 → ~0.68   (uncertain)
Visit 3: strength 0.68 → ~0.28  (exploring)
Visit 4: strength 0.28 → ~0.0   (forgotten)
```

### Files Changed

- `src/tolmans_sowbug_playground/systems/memory.py`
- `tests/test_memory.py`
