import random

from some_sim.agents.sowbug import Sowbug
from some_sim.analysis.recorder import Recorder
from some_sim.core.environment import Environment
from some_sim.core.simulation import Simulation
from some_sim.core.stimulus import Stimulus, StimulusType


class TestSimulation:
    def _make_sim(self):
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (10, 10), intensity=1.0, radius=8.0)
        env.add_stimulus(food)
        bug = Sowbug(position=(5, 5))
        recorder = Recorder(run_id="test")
        return Simulation(
            environment=env, agents=[bug], recorder=recorder, max_ticks=100
        )

    def test_creation(self):
        sim = self._make_sim()
        assert sim.tick_count == 0
        assert sim.max_ticks == 100

    def test_step_advances_tick(self):
        random.seed(42)
        sim = self._make_sim()
        sim.step()
        assert sim.tick_count == 1

    def test_step_records_data(self):
        random.seed(42)
        sim = self._make_sim()
        sim.step()
        assert len(sim.recorder.records) == 1

    def test_agent_moves_during_step(self):
        random.seed(42)
        sim = self._make_sim()
        initial_pos = sim.agents[0].position
        sim.step()
        assert sim.agents[0].position is not None

    def test_run_multiple_ticks(self):
        random.seed(42)
        sim = self._make_sim()
        sim.run(10)
        assert sim.tick_count == 10
        assert len(sim.recorder.records) == 10

    def test_get_state(self):
        sim = self._make_sim()
        state = sim.get_state()
        assert "tick" in state
        assert "agents" in state
        assert "stimuli" in state
        assert state["tick"] == 0
