from some_sim.core.agent import Agent
from some_sim.core.environment import Environment
from some_sim.core.stimulus import Stimulus, StimulusType
from some_sim.systems.drives import Drive, DriveSystem, DriveType
from some_sim.systems.memory import MemorySystem
from some_sim.systems.motor import Direction, MotorSystem
from some_sim.systems.sensors import SensorSystem


class ConcreteAgent(Agent):
    """Minimal agent for testing — always moves north."""

    def decide(self) -> Direction:
        return Direction.NORTH


class TestAgent:
    def _make_agent(self, position=(5, 5)):
        return ConcreteAgent(
            position=position,
            orientation=Direction.NORTH,
            drive_system=DriveSystem(drives=[Drive(DriveType.HUNGER)]),
            sensor_system=SensorSystem(perception_radius=5.0),
            memory_system=MemorySystem(),
            motor_system=MotorSystem(),
        )

    def test_creation(self):
        agent = self._make_agent()
        assert agent.position == (5, 5)
        assert agent.orientation == Direction.NORTH

    def test_perceive_stores_perceptions(self):
        agent = self._make_agent()
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 4), intensity=1.0, radius=3.0)
        env.add_stimulus(food)
        agent.perceive(env)
        assert len(agent.current_perceptions) == 1
        assert agent.current_perceptions[0].stimulus is food

    def test_act_updates_position(self):
        agent = self._make_agent(position=(5, 5))
        env = Environment(width=20, height=20)
        direction = agent.decide()
        agent.act(direction, env)
        assert agent.position == (5, 4)

    def test_act_blocked_by_wall(self):
        agent = self._make_agent(position=(5, 0))
        env = Environment(width=20, height=20)
        direction = agent.decide()  # NORTH
        agent.act(direction, env)
        assert agent.position == (5, 0)

    def test_get_state(self):
        agent = self._make_agent()
        state = agent.get_state()
        assert state["position"] == (5, 5)
        assert state["orientation"] == "NORTH"
        assert "drive_levels" in state
        assert DriveType.HUNGER in state["drive_levels"]
