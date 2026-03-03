import random

import torch

from tolmans_sowbug_playground.agents.dqn_sowbug import (
    ACTION_DIRECTIONS,
    DQNSowbug,
    compute_state_dim,
)
from tolmans_sowbug_playground.core.environment import Environment
from tolmans_sowbug_playground.core.stimulus import Stimulus, StimulusType
from tolmans_sowbug_playground.systems.drives import DriveType
from tolmans_sowbug_playground.systems.motor import Direction


class TestDQNSowbugCreation:
    def test_default_drives(self):
        bug = DQNSowbug(position=(5, 5))
        levels = bug.drive_system.get_levels()
        assert DriveType.HUNGER in levels
        assert DriveType.THIRST in levels
        assert DriveType.TEMPERATURE in levels

    def test_custom_position(self):
        bug = DQNSowbug(position=(3, 7))
        assert bug.position == (3, 7)

    def test_state_dim(self):
        # 3 drives + 3 satiety + 5 passable + 5*3*3 perceptions = 56
        assert compute_state_dim(3) == 56

    def test_action_directions_count(self):
        assert len(ACTION_DIRECTIONS) == 5


class TestStateEncoding:
    def test_encode_state_shape(self):
        bug = DQNSowbug(position=(5, 5), dqn_perception_k=3)
        env = Environment(width=20, height=20)
        bug.perceive(env)
        state = bug._encode_state()
        assert state.shape == (56,)
        assert state.dtype == torch.float32

    def test_drive_levels_in_state(self):
        bug = DQNSowbug(position=(5, 5), dqn_perception_k=3)
        bug.drive_system.drives[DriveType.HUNGER].level = 0.7
        bug.drive_system.drives[DriveType.THIRST].level = 0.3
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.1
        env = Environment(width=20, height=20)
        bug.perceive(env)
        state = bug._encode_state()
        assert abs(state[0].item() - 0.7) < 1e-5
        assert abs(state[1].item() - 0.3) < 1e-5
        assert abs(state[2].item() - 0.1) < 1e-5

    def test_passable_directions_encoded(self):
        bug = DQNSowbug(position=(0, 0), dqn_perception_k=3)
        env = Environment(width=20, height=20)
        bug.perceive(env)
        state = bug._encode_state()
        # At (0,0): NORTH blocked (y=-1), WEST blocked (x=-1)
        # Passable indices: 6=N, 7=S, 8=E, 9=W, 10=STAY
        assert state[6].item() == 0.0   # NORTH blocked
        assert state[7].item() == 1.0   # SOUTH passable
        assert state[8].item() == 1.0   # EAST passable
        assert state[9].item() == 0.0   # WEST blocked
        assert state[10].item() == 1.0  # STAY always passable

    def test_perceptions_encoded(self):
        bug = DQNSowbug(position=(5, 5), dqn_perception_k=3)
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 3), intensity=1.0, radius=6.0)
        env.add_stimulus(food)
        bug.perceive(env)
        state = bug._encode_state()
        # First perception slot after drives(3) + satiety(3) + passable(5) = 11
        # FOOD is first stimulus type, first perception: intensity at index 11
        assert state[11].item() > 0.0  # perceived intensity > 0

    def test_zero_perceptions_padded(self):
        bug = DQNSowbug(position=(5, 5), dqn_perception_k=3)
        env = Environment(width=20, height=20)
        bug.perceive(env)
        state = bug._encode_state()
        # All perception slots should be zero (no stimuli)
        assert state[11:].sum().item() == 0.0


class TestDecideAndAct:
    def test_decide_returns_direction(self):
        random.seed(42)
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        direction = bug.decide()
        assert isinstance(direction, Direction)

    def test_decide_stores_prev_state(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()
        assert bug._prev_state is not None
        assert bug._prev_action is not None

    def test_full_step_cycle(self):
        """perceive → decide → act → post_act should not crash."""
        random.seed(42)
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 3), intensity=1.0, radius=6.0)
        env.add_stimulus(food)

        for _ in range(10):
            bug.perceive(env)
            direction = bug.decide()
            bug.act(direction, env)
            bug.post_act(env)


class TestRewardComputation:
    def test_reward_from_drive_reduction(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        food = Stimulus(
            StimulusType.FOOD, (5, 5), intensity=1.0, radius=1.0, quantity=10.0
        )
        env.add_stimulus(food)

        # Set high hunger so agent will consume
        bug.drive_system.drives[DriveType.HUNGER].level = 0.8

        bug.perceive(env)
        bug.decide()  # saves prev_drive_levels
        bug.act(Direction.STAY, env)
        bug.post_act(env)  # consumes food, pushes transition

        # Should have a transition in replay memory
        assert len(bug._dqn.memory) == 1
        transition = bug._dqn.memory.buffer[0]
        # Reward should be positive (drive was reduced)
        assert transition.reward > 0.0

    def test_urgency_penalty(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)

        # High drives, no food → no drive reduction, just penalty
        bug.drive_system.drives[DriveType.HUNGER].level = 0.5

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.STAY, env)
        bug.post_act(env)

        assert len(bug._dqn.memory) == 1
        transition = bug._dqn.memory.buffer[0]
        # Should be negative (urgency penalty, no drive reduction)
        assert transition.reward < 0.0


class TestGetState:
    def test_state_has_q_values(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()
        state = bug.get_state()
        assert "q_values" in state
        assert len(state["q_values"]) == 5

    def test_state_has_epsilon(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()
        state = bug.get_state()
        assert "epsilon" in state
        assert 0.0 <= state["epsilon"] <= 1.0

    def test_state_has_vte_compat(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()
        state = bug.get_state()
        assert "vte" in state
        assert "candidates" in state["vte"]
        assert "chosen" in state["vte"]

    def test_state_has_replay_and_loss(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()
        state = bug.get_state()
        assert "replay_size" in state
        assert "training_loss" in state


class TestTraining:
    def test_replay_fills_over_steps(self):
        random.seed(42)
        bug = DQNSowbug(position=(5, 5), dqn_batch_size=8)
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (6, 5), intensity=1.0, radius=3.0)
        env.add_stimulus(food)

        for _ in range(20):
            bug.perceive(env)
            d = bug.decide()
            bug.act(d, env)
            bug.post_act(env)

        assert len(bug._dqn.memory) == 20

    def test_optimization_runs_after_enough_data(self):
        random.seed(42)
        bug = DQNSowbug(position=(5, 5), dqn_batch_size=8, dqn_replay_capacity=100)
        env = Environment(width=20, height=20)
        food = Stimulus(
            StimulusType.FOOD, (6, 5), intensity=1.0, radius=3.0, quantity=50.0
        )
        env.add_stimulus(food)

        for _ in range(20):
            bug.perceive(env)
            d = bug.decide()
            bug.act(d, env)
            bug.post_act(env)

        # With 20 transitions and batch_size 8, optimization should have run
        assert bug._dqn.last_loss > 0.0


class TestConfigIntegration:
    def test_load_dqn_config(self):
        from tolmans_sowbug_playground.core.config import load_config

        config = load_config("configs/dqn_basic.yaml")
        assert config.agent.agent_type == "dqn_sowbug"
        assert "dqn_hidden_size" in config.agent.params

    def test_build_dqn_simulation(self):
        from tolmans_sowbug_playground.core.config import build_simulation, load_config

        config = load_config("configs/dqn_basic.yaml")
        sim = build_simulation(config)
        agent = sim.agents[0]
        assert isinstance(agent, DQNSowbug)

    def test_dqn_simulation_step(self):
        from tolmans_sowbug_playground.core.config import build_simulation, load_config

        config = load_config("configs/dqn_basic.yaml")
        sim = build_simulation(config)
        sim.step()
        state = sim.get_state()
        agent_state = state["agents"][0]
        assert "q_values" in agent_state
