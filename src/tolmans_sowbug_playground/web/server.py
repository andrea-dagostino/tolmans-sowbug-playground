import asyncio
import copy
import json
from pathlib import Path
import uuid

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from tolmans_sowbug_playground.analysis.recorder import _make_json_safe
from tolmans_sowbug_playground.core.config import SimulationConfig, StimulusConfig, build_simulation
from tolmans_sowbug_playground.core.simulation import Simulation

STATIC_DIR = Path(__file__).parent / "static"

# Divider wall: full-width horizontal wall at y=15
_DIVIDER_WALL: list[tuple[int, int]] = [(x, 15) for x in range(20) if x not in (3, 4)]

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
    "Divided Foraging": {
        "grid_width": 20,
        "grid_height": 20,
        "agent_position": (11, 10),
        "stimuli": [
            # Light source above wall (right side)
            {"type": "light", "position": (18, 13), "intensity": 1.0, "radius": 5.0},
            # Food cluster (bottom-left)
            {"type": "food", "position": (0, 17), "quantity": 5.0},
            {"type": "food", "position": (0, 18), "quantity": 5.0},
            {"type": "food", "position": (2, 18), "quantity": 5.0},
            {"type": "food", "position": (0, 19), "quantity": 5.0},
            {"type": "food", "position": (2, 19), "quantity": 5.0},
            # Water sources (scattered below wall)
            {"type": "water", "position": (2, 16), "quantity": 5.0},
            {"type": "water", "position": (3, 18), "quantity": 5.0},
            {"type": "water", "position": (1, 19), "quantity": 5.0},
            {"type": "water", "position": (7, 19), "quantity": 5.0},
            # Heat sources (bottom-middle)
            {"type": "heat", "position": (10, 18), "intensity": 0.7, "radius": 5.0},
            {"type": "heat", "position": (15, 18), "intensity": 0.7, "radius": 5.0},
            {"type": "heat", "position": (11, 19), "intensity": 0.7, "radius": 5.0},
            # Light source (bottom-right)
            {"type": "light", "position": (19, 19), "intensity": 1.0, "radius": 5.0},
        ] + [
            {"type": "obstacle", "position": p, "intensity": 1.0, "radius": 0.0}
            for p in _DIVIDER_WALL
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

# Base configuration used to seed each websocket session.
_base_config: SimulationConfig | None = None
MODEL_DIR = Path("results") / "models"


def _clone_config(config: SimulationConfig | None) -> SimulationConfig | None:
    if config is None:
        return None
    return copy.deepcopy(config)


def _init_simulation(config: SimulationConfig | None) -> Simulation | None:
    if config is None:
        return None
    return build_simulation(config)


def _stimulus_configs_from_sim(simulation: Simulation) -> list[StimulusConfig]:
    return [
        StimulusConfig(
            stimulus_type=s.stimulus_type.value,
            position=tuple(s.position),
            intensity=s.intensity,
            radius=s.radius,
            quantity=s.quantity,
        )
        for s in simulation.environment.stimuli
    ]


async def _send_event(
    ws: WebSocket,
    event_type: str,
    action: str | None = None,
    request_id: str | None = None,
    message: str | None = None,
    payload: dict | None = None,
) -> None:
    envelope: dict = {"type": event_type}
    if action is not None:
        envelope["action"] = action
    if request_id is not None:
        envelope["request_id"] = request_id
    if message is not None:
        envelope["message"] = message
    if payload is not None:
        envelope["payload"] = payload
    await ws.send_text(json.dumps(_make_json_safe(envelope)))


async def _send_state(
    ws: WebSocket,
    simulation: Simulation | None,
    running: bool,
    speed: int,
    session_id: str,
) -> None:
    if simulation is None:
        return
    await ws.send_text(
        json.dumps(
            _make_json_safe(
                {
                    "type": "state",
                    "session_id": session_id,
                    "running": running,
                    "speed": speed,
                    "state": simulation.get_state(),
                }
            )
        )
    )


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(index_path.read_text())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = uuid.uuid4().hex[:8]
    running = False
    speed = 5
    config = _clone_config(_base_config)
    simulation = _init_simulation(config)

    await _send_event(
        ws,
        "status",
        action="connect",
        message=f"Session {session_id} connected.",
        payload={"session_id": session_id},
    )
    await _send_state(ws, simulation, running, speed, session_id)

    try:
        while True:
            action = None
            request_id = None
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                data = json.loads(msg)
                action = data.get("action")
                request_id = data.get("request_id")
                if action == "play":
                    running = True
                    await _send_event(
                        ws,
                        "ack",
                        action=action,
                        request_id=request_id,
                        message="Simulation running.",
                    )
                elif action == "pause":
                    running = False
                    await _send_event(
                        ws,
                        "ack",
                        action=action,
                        request_id=request_id,
                        message="Simulation paused.",
                    )
                elif action == "step":
                    if running:
                        await _send_event(
                            ws,
                            "error",
                            action=action,
                            request_id=request_id,
                            message="Cannot step while running. Pause first.",
                        )
                    elif simulation:
                        simulation.step()
                        await _send_event(
                            ws,
                            "ack",
                            action=action,
                            request_id=request_id,
                            message="Step completed.",
                        )
                        await _send_state(ws, simulation, running, speed, session_id)
                elif action == "speed":
                    speed = max(1, min(60, data.get("value", 5)))
                    await _send_event(
                        ws,
                        "ack",
                        action=action,
                        request_id=request_id,
                        message=f"Speed set to {speed} tps.",
                    )
                elif action == "reset":
                    running = False
                    simulation = _init_simulation(config)
                    await _send_event(
                        ws,
                        "ack",
                        action=action,
                        request_id=request_id,
                        message="Simulation reset and paused.",
                    )
                    await _send_state(ws, simulation, running, speed, session_id)
                elif action == "add_stimulus":
                    if simulation:
                        from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType

                        stim_type = StimulusType(data["stimulus_type"])
                        simulation.environment.add_stimulus(
                            Stimulus(
                                stimulus_type=stim_type,
                                position=tuple(data["position"]),
                                intensity=data.get("intensity", 1.0),
                                radius=data.get("radius", 5.0),
                                quantity=data.get("quantity"),
                            )
                        )
                        if config is not None:
                            config.stimuli = _stimulus_configs_from_sim(simulation)
                        await _send_event(
                            ws,
                            "ack",
                            action=action,
                            request_id=request_id,
                            message="Stimulus added.",
                        )
                        if not running:
                            await _send_state(ws, simulation, running, speed, session_id)
                elif action == "remove_stimulus":
                    if simulation:
                        pos = tuple(data["position"])
                        matches = simulation.environment.get_stimuli_at(pos)
                        for s in matches:
                            simulation.environment.remove_stimulus(s)
                        if config is not None:
                            config.stimuli = _stimulus_configs_from_sim(simulation)
                        await _send_event(
                            ws,
                            "ack",
                            action=action,
                            request_id=request_id,
                            message=f"Removed {len(matches)} stimuli.",
                        )
                        if matches and not running:
                            await _send_state(ws, simulation, running, speed, session_id)
                elif action == "resize":
                    width = max(5, min(100, data.get("width", 20)))
                    height = max(5, min(100, data.get("height", 20)))
                    if config is not None:
                        config.grid_width = width
                        config.grid_height = height
                        ax = min(config.agent.position[0], width - 1)
                        ay = min(config.agent.position[1], height - 1)
                        config.agent.position = (ax, ay)
                    running = False
                    simulation = _init_simulation(config)
                    await _send_event(
                        ws,
                        "ack",
                        action=action,
                        request_id=request_id,
                        message=f"Resized map to {width}x{height}; paused.",
                    )
                    await _send_state(ws, simulation, running, speed, session_id)
                elif action == "load_preset":
                    preset_name = data.get("preset", "")
                    preset = PRESETS.get(preset_name)
                    if preset and config is not None:
                        config.grid_width = preset["grid_width"]
                        config.grid_height = preset["grid_height"]
                        config.agent.position = preset["agent_position"]
                        config.stimuli = [
                            StimulusConfig(
                                stimulus_type=s["type"],
                                position=tuple(s["position"]),
                                intensity=s.get("intensity", 1.0),
                                radius=s.get("radius", 5.0),
                                quantity=s.get("quantity"),
                            )
                            for s in preset["stimuli"]
                        ]
                        running = False
                        simulation = _init_simulation(config)
                        await _send_event(
                            ws,
                            "ack",
                            action=action,
                            request_id=request_id,
                            message=f'Preset "{preset_name}" loaded; paused.',
                        )
                        await _send_state(ws, simulation, running, speed, session_id)
                    else:
                        await _send_event(
                            ws,
                            "error",
                            action=action,
                            request_id=request_id,
                            message=f'Unknown preset "{preset_name}".',
                        )
                elif action == "update_params":
                    if simulation and simulation.agents:
                        agent = simulation.agents[0]
                        param = data.get("param")
                        value = float(data.get("value", 0))
                        drives = agent.drive_system.drives
                        from tolmans_sowbug_playground.systems.drives import DriveType
                        if param == "hunger_rate":
                            drives[DriveType.HUNGER].rate = value
                        elif param == "thirst_rate":
                            drives[DriveType.THIRST].rate = value
                        elif param == "temperature_rate":
                            drives[DriveType.TEMPERATURE].rate = value
                        elif param == "satiety_decay_rate":
                            for d in drives.values():
                                d.satiety_decay_rate = value
                        elif param == "bite_size":
                            agent.bite_size = value
                        if config is not None:
                            config.agent.params[param] = value
                        await _send_event(
                            ws,
                            "ack",
                            action=action,
                            request_id=request_id,
                            message=f"Parameter {param} set to {value}.",
                        )
                elif action == "save_preset":
                    preset_name = data.get("name", "").strip()
                    if preset_name and simulation and config:
                        stimuli_list = []
                        for s in simulation.environment.stimuli:
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
                            "grid_width": config.grid_width,
                            "grid_height": config.grid_height,
                            "agent_position": config.agent.position,
                            "stimuli": stimuli_list,
                        }
                        await _send_event(
                            ws,
                            "ack",
                            action=action,
                            request_id=request_id,
                            message=f'Preset "{preset_name}" saved.',
                            payload={
                                "preset_saved": preset_name,
                                "presets": list(PRESETS.keys()),
                            },
                        )
                    else:
                        await _send_event(
                            ws,
                            "error",
                            action=action,
                            request_id=request_id,
                            message="Preset name is required.",
                        )
                elif action == "save_model":
                    if simulation and simulation.agents:
                        agent = simulation.agents[0]
                        if not hasattr(agent, "save_model"):
                            await _send_event(
                                ws,
                                "error",
                                action=action,
                                request_id=request_id,
                                message="Current agent does not support model checkpoints.",
                            )
                        else:
                            tick = simulation.tick_count
                            requested_name = str(data.get("name", "")).strip()
                            safe_name = requested_name.replace("/", "_").replace("\\", "_")
                            filename = (
                                f"{safe_name}.pt"
                                if safe_name
                                else f"sowbug_tick{tick}.pt"
                            )
                            session_dir = MODEL_DIR / session_id
                            session_dir.mkdir(parents=True, exist_ok=True)
                            model_path = session_dir / filename
                            agent.save_model(model_path)
                            await _send_event(
                                ws,
                                "ack",
                                action=action,
                                request_id=request_id,
                                message=f"Model checkpoint saved at tick {tick}.",
                                payload={
                                    "model_saved": str(model_path),
                                    "model_saved_tick": tick,
                                    "model_session": session_id,
                                },
                            )
                else:
                    await _send_event(
                        ws,
                        "error",
                        action=action,
                        request_id=request_id,
                        message=f"Unknown action: {action}",
                    )
            except asyncio.TimeoutError:
                pass
            except Exception as exc:
                await _send_event(
                    ws,
                    "error",
                    action=action if "action" in locals() else None,
                    request_id=request_id if "request_id" in locals() else None,
                    message=str(exc),
                )

            if running and simulation:
                simulation.step()
                await _send_state(ws, simulation, running, speed, session_id)
                await asyncio.sleep(1.0 / speed)
            else:
                await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        pass


# Mount static files AFTER routes so / isn't overridden
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def start_server(config: SimulationConfig | None = None, port: int = 8000):
    global _base_config
    _base_config = config
    uvicorn.run(app, host="0.0.0.0", port=port)
