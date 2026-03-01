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
            "grid_width": self.environment.width,
            "grid_height": self.environment.height,
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
