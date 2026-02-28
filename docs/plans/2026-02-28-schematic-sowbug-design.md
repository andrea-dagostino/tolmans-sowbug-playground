# Schematic Sowbug Simulation Platform — Design Document

**Date:** 2026-02-28
**Status:** Approved

## Purpose

A research platform and exploration sandbox for studying psychological phenomena.
Starting with a faithful recreation of Tolman's Schematic Sowbug, then generalizing
to support cognitive maps, reinforcement/conditioning, and decision-making under
uncertainty.

**Interaction modes:**
- Headless core for batch experiments (CLI, scriptable)
- Browser-based visualization for real-time observation and debugging

## Architecture: Clean OOP with Modular Subsystems

### Tick Loop

```
for each tick:
    1. agent.perceive(environment)   -> sensors detect nearby stimuli
    2. agent.decide()                -> internal state + memory -> choose action
    3. agent.act(environment)        -> move, eat, flee, etc.
    4. environment.update()          -> stimuli change, time passes
    5. simulation.record()           -> log state for analysis
```

### Core Classes

- **`Environment`** — 2D grid world containing `Stimulus` objects (food, light, heat,
  obstacles). Each cell can hold multiple stimuli with varying intensities. Environment
  can change over time (food depletes, temperatures shift).

- **`Stimulus`** — Something in the environment: type (food, light, heat, odor),
  position, intensity, radius of effect. Can be static or dynamic.

- **`Agent`** — Base class. Has position, orientation, and four internal subsystems:
  - **`DriveSystem`** — Manages internal drives (hunger, thirst, temperature comfort).
    Drives increase over time and decrease when satisfied.
  - **`SensorSystem`** — Detects stimuli within a perception radius. Returns what the
    agent can perceive from its current position.
  - **`MemorySystem`** — Stores past experiences. Cognitive maps live here —
    associations between locations, stimuli, and outcomes.
  - **`MotorSystem`** — Translates decisions into grid movement.

- **`Simulation`** — Orchestrates the loop. Holds environment, agent(s), tick counter,
  configuration, and data recorder.

## Tolman's Schematic Sowbug

### Drives

| Drive | Behavior |
|-------|----------|
| Hunger | Increases over time, decreases when food consumed |
| Thirst | Increases over time, decreases when water found |
| Temperature discomfort | Increases outside comfort range, decreases at comfortable temps |

Each drive has a `level` (0.0-1.0) and a `rate` of increase. The most urgent drive
influences behavior selection.

### Stimuli

- **Food odor** — Gradient (stronger = closer to source)
- **Water** — Detectable at short range
- **Light** — Sowbug is negatively phototactic (avoids bright light)
- **Temperature** — Gradient; sowbug seeks comfortable range
- **Obstacles** — Impassable cells

### Behavioral Rules (Means-End Readiness)

The sowbug has *expectations*: "if I go toward that smell, I expect food."
- Confirmed expectations strengthen the association
- Violated expectations weaken it
- This is how the cognitive map forms

### Decision-Making

1. Rank active drives by urgency
2. For top drive, consult memory: "where did I last satisfy this?"
3. If memory has answer -> navigate toward that location (exploit)
4. If no memory -> explore (biased random walk, weighted by stimulus gradients)
5. Modulated by aversion: avoid light, avoid extreme temps even if drive pulls that way

### Cognitive Map

- Graph: nodes = grid locations/regions, edges = traversal experiences
- Each node stores: `{location -> {stimulus_type: expected_intensity, outcome: reward}}`
- Updated after each experience via associative learning (strengthen/weaken)

## Web Visualization

### Tech Stack

- **Backend:** FastAPI + WebSocket (pushes state each tick at configurable frame rate)
- **Frontend:** HTML5 Canvas + vanilla JS

### Views

- **Grid view** — 2D grid with color-coded stimuli (food=green, water=blue,
  light=yellow, heat=red). Sowbug rendered with position and orientation.
- **Agent dashboard (sidebar):**
  - Drive levels (bar charts)
  - Current action and decision rationale
  - Memory strength heatmap overlay
- **Controls:**
  - Play / Pause / Step
  - Speed slider
  - Toggle overlays (cognitive map, stimulus gradients)
  - Interactive stimulus placement (click to add food, drag to create walls)

### Headless Mode

```
python -m some_sim run --ticks 10000 --config experiment.yaml
```

Outputs structured JSON/CSV logs.

## Data & Analysis

### Data Recording

Each tick logs:
```json
{
  "tick": 42,
  "agent_position": [5, 3],
  "agent_orientation": "north",
  "drive_levels": {"hunger": 0.7, "thirst": 0.3, "temperature": 0.1},
  "perceived_stimuli": [...],
  "action_taken": "move_north",
  "reward": 0.0,
  "memory_updates": [...]
}
```

Environment snapshots at configurable intervals. All data as structured JSON (one file
per run) with summary CSV.

### Experiment Configuration (YAML)

Defines: environment layout (grid size, stimulus placement), agent parameters (drive
rates, sensor range, learning rate), run parameters (tick count, random seed).

### Built-in Analysis

- **Learning curves** — Drive satisfaction rate over time
- **Exploration heatmap** — Cell visit frequency
- **Cognitive map visualization** — Agent's internal model at any point
- **Path efficiency** — Agent paths vs optimal paths over time
- **Comparative runs** — Overlay results across configs (e.g., memory vs memoryless)

Output as matplotlib plots (PNG/SVG). Accessible from CLI and web UI.

## Project Structure

```
some_sim/
├── pyproject.toml
├── src/
│   └── some_sim/
│       ├── __init__.py
│       ├── __main__.py              # CLI entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── simulation.py        # Simulation orchestrator
│       │   ├── environment.py       # Grid world, stimuli
│       │   ├── stimulus.py          # Stimulus types and behaviors
│       │   └── agent.py             # Base Agent class
│       ├── agents/
│       │   ├── __init__.py
│       │   └── sowbug.py            # Tolman's Schematic Sowbug
│       ├── systems/
│       │   ├── __init__.py
│       │   ├── drives.py            # DriveSystem
│       │   ├── sensors.py           # SensorSystem
│       │   ├── memory.py            # MemorySystem + cognitive map
│       │   └── motor.py             # MotorSystem
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── recorder.py          # Data logging
│       │   └── plots.py             # Built-in analysis/plotting
│       └── web/
│           ├── __init__.py
│           ├── server.py            # FastAPI + WebSocket
│           └── static/
│               ├── index.html
│               ├── main.js          # Canvas rendering + controls
│               └── style.css
├── configs/
│   └── sowbug_basic.yaml            # Default experiment config
├── tests/
│   ├── test_environment.py
│   ├── test_agent.py
│   ├── test_drives.py
│   ├── test_memory.py
│   └── test_simulation.py
└── docs/
    └── plans/
```

## Dependencies

- `fastapi` + `uvicorn` — web server
- `websockets` — real-time communication
- `pyyaml` — config files
- `matplotlib` — analysis plots
- `numpy` — numerical operations for grids/gradients

## Future Extensions

- Reinforcement/conditioning experiments (classical, operant)
- Decision-making under uncertainty (exploration vs exploitation)
- Additional agent types beyond the sowbug
- Preset experiment configs for classic psychology experiments
