# Tolman's Sowbug Playground

A research simulation platform for studying cognitive mapping and goal-directed behavior, based on [Tolman's schematic sowbug](https://en.wikipedia.org/wiki/Edward_C._Tolman) model. A virtual agent navigates a 2D grid, develops internal drives, builds spatial memories, and makes decisions — all observable in real time through a browser UI.

Built for researchers and devs interested in computational psychology, agent-based modeling, or just watching a bug figure out where food is.

![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

**Agent with internal state** — Three drives (hunger, thirst, temperature) that rise over time and get satisfied by reaching the right stimulus. The agent perceives stimuli within a radius, remembers where it found things (cognitive map), and navigates or explores accordingly.

**Decision-making model** — When the agent knows where to go, it navigates directly. When uncertain, it engages in Vicarious Trial and Error (VTE) — mentally evaluating each direction before committing. Sometimes it hesitates. Sometimes it explores randomly. Drives compete for attention.

**Interactive web UI** — Real-time canvas rendering with overlays for perception radius, cognitive map edges, KDE density heatmaps, and VTE deliberation arrows. Place/remove stimuli by clicking the grid. Adjust speed, grid size, toggle overlays, load environment presets.

**Headless mode + analysis** — Run batch experiments from CLI, export to JSON/CSV, generate plots (drive levels, exploration heatmaps, learning curves).

**YAML config** — Define grid size, stimulus placement, agent parameters, random seeds. Ship with presets (empty, basic foraging, choice point, light + drives).

## Quickstart

```bash
# clone and install
git clone https://github.com/andrea-dagostino/tolmans-sowbug-playground.git
cd tolmans-sowbug-playground
python -m venv .venv && source .venv/bin/activate
pip install -e .

# launch the web UI
some-sim serve --config configs/sowbug_basic.yaml --port 8000
# open http://localhost:8000
```

## CLI

```bash
# run a headless simulation
some-sim run --config configs/sowbug_basic.yaml --ticks 2000 --output results/run1

# generate analysis plots
some-sim analyze --input results/run1.json --plot drives
some-sim analyze --input results/run1.json --plot heatmap
some-sim analyze --input results/run1.json --plot learning

# run tests
pytest
```

## Project Structure

```
src/some_sim/
├── core/           # simulation engine, grid world, stimulus model, config
├── agents/         # sowbug implementation (decision logic)
├── systems/        # drives, sensors, memory (cognitive map + KDE), motor
├── analysis/       # JSON/CSV recorder, matplotlib plots
└── web/            # FastAPI + WebSocket server, canvas UI
configs/            # YAML experiment configs
tests/              # pytest suite
```

## Tech Stack

Python 3.12, FastAPI, NumPy, Matplotlib, vanilla JS + HTML5 Canvas. No frontend framework. WebSocket for real-time state sync.

## Background

Edward Tolman proposed in the 1930s-40s that even simple organisms build internal "cognitive maps" of their environment rather than just reacting to stimuli. His thought experiment of a "schematic sowbug" described a minimal agent with drives, perception, and memory — enough to exhibit purposive behavior.

This project makes that thought experiment runnable.

## License

MIT
