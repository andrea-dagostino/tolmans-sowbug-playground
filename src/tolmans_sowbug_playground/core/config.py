import random as rng
from dataclasses import dataclass, field

import yaml

from tolmans_sowbug_playground.agents.dqn_sowbug import DQNSowbug
from tolmans_sowbug_playground.agents.sowbug import Sowbug
from tolmans_sowbug_playground.analysis.recorder import Recorder
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.simulation import Simulation
from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType

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
    quantity: float | None = None


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
                quantity=s.get("quantity"),
            )
        )

    agent_params = {
        k: v for k, v in agent_raw.items() if k not in ("type", "position")
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
    rng.seed(config.random_seed)

    env = Environment(width=config.grid_width, height=config.grid_height)
    for sc in config.stimuli:
        env.add_stimulus(
            Stimulus(
                stimulus_type=STIMULUS_TYPE_MAP[sc.stimulus_type],
                position=sc.position,
                intensity=sc.intensity,
                radius=sc.radius,
                quantity=sc.quantity,
            )
        )

    if config.agent.agent_type == "sowbug":
        agent = Sowbug(position=config.agent.position, **config.agent.params)
    elif config.agent.agent_type == "dqn_sowbug":
        agent = DQNSowbug(position=config.agent.position, **config.agent.params)
    else:
        raise ValueError(f"Unknown agent type: {config.agent.agent_type}")

    recorder = Recorder(run_id=f"run_seed{config.random_seed}")

    return Simulation(
        environment=env,
        agents=[agent],
        recorder=recorder,
        max_ticks=config.max_ticks,
    )
