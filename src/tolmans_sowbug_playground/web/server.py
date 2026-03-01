import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from tolmans_sowbug_playground.analysis.recorder import _make_json_safe
from tolmans_sowbug_playground.core.config import SimulationConfig, StimulusConfig, build_simulation
from tolmans_sowbug_playground.core.simulation import Simulation

STATIC_DIR = Path(__file__).parent / "static"

# Maze wall positions (x, y) for the multi-corridor preset
_MAZE_WALLS: list[tuple[int, int]] = (
    [(x, 2) for x in (2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17)]
    + [(x, 3) for x in (2, 7, 12, 17)]
    + [(x, 4) for x in (2, 7, 12, 17)]
    + [(x, 5) for x in (2, 17)]
    + [(x, 6) for x in (2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17)]
    + [(x, 8) for x in (2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17)]
    + [(x, 9) for x in (2, 17)]
    + [(x, 10) for x in (2, 7, 12, 17)]
    + [(x, 11) for x in (2, 7, 12, 17)]
    + [(x, 12) for x in (2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17)]
    + [(x, 14) for x in (2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17)]
    + [(x, 15) for x in (2, 8, 11, 17)]
    + [(x, 16) for x in (2, 17)]
    + [(x, 17) for x in (2, 8, 11, 17)]
    + [(x, 18) for x in (2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17)]
)

# Environment presets
PRESETS: dict[str, dict] = {
    "Empty": {
        "grid_width": 20,
        "grid_height": 20,
        "agent_position": (10, 10),
        "stimuli": [],
    },
    "Basic Foraging": {
        "grid_width": 25,
        "grid_height": 25,
        "agent_position": (12, 12),
        "stimuli": [
            {"type": "food", "position": (5, 5), "quantity": 5.0},
            {"type": "food", "position": (20, 8), "quantity": 5.0},
            {"type": "food", "position": (10, 20), "quantity": 5.0},
            {"type": "water", "position": (18, 18), "quantity": 5.0},
            {"type": "water", "position": (3, 15), "quantity": 5.0},
        ],
    },
    "Choice Point": {
        "grid_width": 20,
        "grid_height": 20,
        "agent_position": (10, 10),
        "stimuli": [
            {"type": "food", "position": (3, 10), "quantity": 5.0},
            {"type": "food", "position": (17, 10), "quantity": 5.0},
        ],
    },
    "Light + Drives": {
        "grid_width": 20,
        "grid_height": 20,
        "agent_position": (10, 10),
        "stimuli": [
            {"type": "light", "position": (3, 3)},
            {"type": "food", "position": (17, 17), "quantity": 5.0},
            {"type": "water", "position": (17, 3), "quantity": 5.0},
        ],
    },
    "Maze": {
        "grid_width": 20,
        "grid_height": 20,
        "agent_position": (9, 9),
        "stimuli": [
            {"type": "food", "position": (14, 4), "quantity": 5.0},
            {"type": "food", "position": (5, 11), "quantity": 5.0},
            {"type": "food", "position": (15, 16), "quantity": 5.0},
            {"type": "water", "position": (4, 4), "quantity": 5.0},
            {"type": "water", "position": (14, 11), "quantity": 5.0},
            {"type": "water", "position": (4, 16), "quantity": 5.0},
        ] + [
            {"type": "obstacle", "position": p, "intensity": 1.0, "radius": 0.0}
            for p in _MAZE_WALLS
        ],
    },
}

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
                            json.dumps(_make_json_safe(_simulation.get_state()))
                        )
                elif action == "speed":
                    _speed = max(1, min(60, data.get("value", 5)))
                elif action == "reset":
                    _init_simulation()
                    if _simulation:
                        await ws.send_text(
                            json.dumps(_make_json_safe(_simulation.get_state()))
                        )
                elif action == "add_stimulus":
                    if _simulation:
                        from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType

                        stim_type = StimulusType(data["stimulus_type"])
                        _simulation.environment.add_stimulus(
                            Stimulus(
                                stimulus_type=stim_type,
                                position=tuple(data["position"]),
                                intensity=data.get("intensity", 1.0),
                                radius=data.get("radius", 5.0),
                                quantity=data.get("quantity"),
                            )
                        )
                        if not _running:
                            await ws.send_text(
                                json.dumps(
                                    _make_json_safe(_simulation.get_state())
                                )
                            )
                elif action == "remove_stimulus":
                    if _simulation:
                        pos = tuple(data["position"])
                        matches = _simulation.environment.get_stimuli_at(pos)
                        for s in matches:
                            _simulation.environment.remove_stimulus(s)
                        if matches and not _running:
                            await ws.send_text(
                                json.dumps(
                                    _make_json_safe(_simulation.get_state())
                                )
                            )
                elif action == "resize":
                    width = max(5, min(100, data.get("width", 20)))
                    height = max(5, min(100, data.get("height", 20)))
                    if _config is not None:
                        _config.grid_width = width
                        _config.grid_height = height
                        ax = min(_config.agent.position[0], width - 1)
                        ay = min(_config.agent.position[1], height - 1)
                        _config.agent.position = (ax, ay)
                    _running = False
                    _init_simulation()
                    if _simulation:
                        await ws.send_text(
                            json.dumps(
                                _make_json_safe(_simulation.get_state())
                            )
                        )
                elif action == "load_preset":
                    preset_name = data.get("preset", "")
                    preset = PRESETS.get(preset_name)
                    if preset and _config is not None:
                        _config.grid_width = preset["grid_width"]
                        _config.grid_height = preset["grid_height"]
                        _config.agent.position = preset["agent_position"]
                        _config.stimuli = [
                            StimulusConfig(
                                stimulus_type=s["type"],
                                position=tuple(s["position"]),
                                intensity=s.get("intensity", 1.0),
                                radius=s.get("radius", 5.0),
                                quantity=s.get("quantity"),
                            )
                            for s in preset["stimuli"]
                        ]
                        _running = False
                        _init_simulation()
                        if _simulation:
                            await ws.send_text(
                                json.dumps(
                                    _make_json_safe(_simulation.get_state())
                                )
                            )
                elif action == "save_preset":
                    preset_name = data.get("name", "").strip()
                    if preset_name and _simulation and _config:
                        stimuli_list = []
                        for s in _simulation.environment.stimuli:
                            entry = {
                                "type": s.stimulus_type.value,
                                "position": s.position,
                                "intensity": s.intensity,
                                "radius": s.radius,
                            }
                            if s.quantity is not None:
                                entry["quantity"] = s.quantity
                            stimuli_list.append(entry)
                        PRESETS[preset_name] = {
                            "grid_width": _config.grid_width,
                            "grid_height": _config.grid_height,
                            "agent_position": _config.agent.position,
                            "stimuli": stimuli_list,
                        }
                        await ws.send_text(
                            json.dumps({
                                "preset_saved": preset_name,
                                "presets": list(PRESETS.keys()),
                            })
                        )
            except asyncio.TimeoutError:
                pass

            # Run simulation if playing
            if _running and _simulation:
                _simulation.step()
                state = _simulation.get_state()
                await ws.send_text(json.dumps(_make_json_safe(state)))
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
