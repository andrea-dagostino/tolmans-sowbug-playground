import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from some_sim.core.config import SimulationConfig, build_simulation
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
