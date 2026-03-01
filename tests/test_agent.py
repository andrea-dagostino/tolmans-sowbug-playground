from tolmans_sowbug_playground.core.agent import Agent
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType
from tolmans_sowbug_playground.systems.drives import Drive, DriveSystem, DriveType
from tolmans_sowbug_playground.systems.memory import MemorySystem
from tolmans_sowbug_playground.systems.motor import Direction, MotorSystem
from tolmans_sowbug_playground.systems.sensors import SensorSystem


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

    def test_get_state_includes_visualization_keys(self):
        agent = self._make_agent()
        state = agent.get_state()
        assert "perceptions" in state
        assert "cognitive_map" in state
        assert "cognitive_map_edges" in state
        assert "perception_radius" in state
        assert isinstance(state["perceptions"], list)
        assert isinstance(state["cognitive_map"], dict)
        assert isinstance(state["cognitive_map_edges"], list)

    def test_get_state_cognitive_map_format(self):
        agent = self._make_agent()
        agent.memory_system.record_experience(
            (3, 4), StimulusType.FOOD, 0.8, 1.0
        )
        agent.memory_system.record_traversal((5, 5), (5, 4))
        state = agent.get_state()
        assert "3,4" in state["cognitive_map"]
        entries = state["cognitive_map"]["3,4"]
        assert len(entries) == 1
        assert entries[0]["stimulus_type"] == "food"
        assert entries[0]["expected_intensity"] == 0.8
        assert entries[0]["reward_value"] == 1.0
        assert entries[0]["strength"] == 1.0
        assert len(state["cognitive_map_edges"]) == 1
        edge = state["cognitive_map_edges"][0]
        assert edge["from"] == [5, 5]
        assert edge["to"] == [5, 4]
        assert edge["count"] == 1

    def test_get_state_includes_visited_cells(self):
        agent = self._make_agent()
        agent.memory_system.record_visit((3, 4))
        agent.memory_system.record_visit((5, 5))
        state = agent.get_state()
        assert "visited_cells" in state
        assert "3,4" in state["visited_cells"]
        assert state["visited_cells"]["3,4"] == 1.0
        assert "5,5" in state["visited_cells"]

    def test_get_state_perception_format(self):
        agent = self._make_agent()
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 3), intensity=1.0, radius=5.0)
        env.add_stimulus(food)
        agent.perceive(env)
        state = agent.get_state()
        assert len(state["perceptions"]) == 1
        p = state["perceptions"][0]
        assert p["stimulus_type"] == "food"
        assert p["stimulus_position"] == [5, 3]
        assert isinstance(p["perceived_intensity"], float)
        assert isinstance(p["distance"], float)
        assert p["direction"] == [0, -2]

    def test_get_state_includes_density_field(self):
        agent = self._make_agent()
        agent.memory_system.record_experience(
            (3, 4), StimulusType.FOOD, 0.8, 1.0
        )
        state = agent.get_state()
        assert "density_field" in state
        assert isinstance(state["density_field"], dict)
        assert "3,4" in state["density_field"]
        assert state["density_field"]["3,4"] == 1.0  # peak is normalized to 1.0

    def test_get_state_density_field_empty_when_no_memories(self):
        agent = self._make_agent()
        state = agent.get_state()
        assert "density_field" in state
        assert state["density_field"] == {}
