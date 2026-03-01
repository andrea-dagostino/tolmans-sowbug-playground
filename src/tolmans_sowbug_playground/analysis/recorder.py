import csv
import json
import os
from enum import Enum

from tolmans_sowbug_playground.core.agent import Agent
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.systems.drives import DriveType


def _make_json_safe(obj):
    """Recursively convert dicts with Enum keys and tuple values for JSON."""
    if isinstance(obj, dict):
        return {
            (k.value if isinstance(k, Enum) else k): _make_json_safe(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_make_json_safe(i) for i in obj]
    if isinstance(obj, tuple):
        return list(obj)
    return obj


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
        dirn = os.path.dirname(path)
        if dirn:
            os.makedirs(dirn, exist_ok=True)
        data = {
            "run_id": self.run_id,
            "records": self.records,
        }
        with open(path, "w") as f:
            json.dump(_make_json_safe(data), f, indent=2, default=str)

    def save_csv(self, path: str) -> None:
        if not self.records:
            return
        dirn = os.path.dirname(path)
        if dirn:
            os.makedirs(dirn, exist_ok=True)
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
