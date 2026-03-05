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
        # 3 drives + 3 satiety + 5 passable + 6 memory dir + 5*3*3 perceptions = 62
        assert compute_state_dim(3) == 62

    def test_action_directions_count(self):
        assert len(ACTION_DIRECTIONS) == 5


class TestStateEncoding:
    def test_encode_state_shape(self):
        bug = DQNSowbug(position=(5, 5), dqn_perception_k=3)
        env = Environment(width=20, height=20)
        bug.perceive(env)
        state = bug._encode_state()
        assert state.shape == (62,)
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
        # Passable indices: 6=N, 7=S, 8=E, 9=W, 10=STAY (after 3 drives + 3 satiety)
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
        # First perception slot after drives(3) + satiety(3) + passable(5) + memory_dir(6) = 17
        # FOOD is first stimulus type, first perception: intensity at index 17
        assert state[17].item() > 0.0  # perceived intensity > 0

    def test_memory_direction_encoded(self):
        bug = DQNSowbug(position=(5, 5), dqn_perception_k=3)
        env = Environment(width=20, height=20)
        bug.perceive(env)

        # No memories yet — direction features should be zero
        state = bug._encode_state()
        # Memory direction starts at index 11 (after 3+3+5), 6 dims
        assert state[11:17].sum().item() == 0.0

        # Record a food memory at (15, 10)
        bug.memory_system.record_experience(
            (15, 10), StimulusType.FOOD, 1.0, 1.0
        )
        state = bug._encode_state()
        # HUNGER direction (indices 11, 12) should now point toward (15, 10)
        dx = state[11].item()
        dy = state[12].item()
        assert dx > 0  # food is to the east (x=15 > x=5)
        assert dy > 0  # food is to the south (y=10 > y=5)

    def test_zero_perceptions_padded(self):
        bug = DQNSowbug(position=(5, 5), dqn_perception_k=3)
        env = Environment(width=20, height=20)
        bug.perceive(env)
        state = bug._encode_state()
        # All perception slots should be zero (no stimuli)
        assert state[17:].sum().item() == 0.0


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

    def test_decide_never_returns_blocked_direction(self):
        random.seed(42)
        bug = DQNSowbug(
            position=(0, 0), dqn_eps_start=1.0, dqn_eps_end=1.0, dqn_eps_decay=1.0
        )
        env = Environment(width=20, height=20)
        for _ in range(50):
            bug.perceive(env)
            direction = bug.decide()
            assert direction in [Direction.SOUTH, Direction.EAST, Direction.STAY]

    def test_transition_next_state_is_post_action_snapshot(self):
        bug = DQNSowbug(position=(5, 5), dqn_eps_start=0.0, dqn_eps_end=0.0)
        env = Environment(width=20, height=20)
        # Put food at (6,5): moving EAST lands on the stimulus position.
        food = Stimulus(StimulusType.FOOD, (6, 5), intensity=1.0, radius=6.0)
        env.add_stimulus(food)

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.EAST, env)
        bug.post_act(env)

        transition = bug._dqn.memory.buffer[0]
        # FOOD first slot starts at 17: [intensity, dir_x, dir_y]
        # At the stimulus location, encoded direction should be exactly (0, 0).
        assert abs(transition.next_state[18].item()) < 1e-6
        assert abs(transition.next_state[19].item()) < 1e-6


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

    def test_approach_shaping_reward(self):
        """Moving toward perceived food when hungry gives positive shaping reward."""
        bug = DQNSowbug(position=(5, 5), perception_radius=6.0)
        env = Environment(width=20, height=20)
        # Food at (5, 2) — 3 cells north, within perception radius
        food = Stimulus(StimulusType.FOOD, (5, 2), intensity=1.0, radius=8.0)
        env.add_stimulus(food)

        bug.drive_system.drives[DriveType.HUNGER].level = 0.8
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()  # saves prev_position=(5,5)
        bug.act(Direction.NORTH, env)  # moves to (5,4), closer to food
        bug.post_act(env)

        transition = bug._dqn.memory.buffer[0]
        # Should get positive approach shaping (moved closer to food)
        assert transition.reward > 0.0

    def test_memory_approach_shaping(self):
        """When food is out of perception range, memory guides the agent."""
        bug = DQNSowbug(position=(0, 5), perception_radius=3.0)
        env = Environment(width=20, height=20)
        # No food in environment — but agent remembers food at (10, 5)
        bug.memory_system.record_experience(
            (10, 5), StimulusType.FOOD, 1.0, 1.0
        )

        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()  # saves prev_position=(0,5)
        bug.act(Direction.EAST, env)  # moves to (1,5), closer to memory
        bug.post_act(env)

        transition = bug._dqn.memory.buffer[0]
        # Should get positive reward from memory-based approach shaping
        assert transition.reward > 0.0

    def test_no_false_positive_shaping_through_blocking_wall(self):
        """Path-based shaping should not reward straight-line moves through walls."""
        bug = DQNSowbug(
            position=(8, 10),
            perception_radius=8.0,
            dqn_urgent_explore_novelty_bonus=0.0,
            dqn_urgent_explore_stay_penalty=0.0,
            dqn_urgent_explore_loop_penalty=0.0,
        )
        env = Environment(width=20, height=20)
        # Full vertical wall at x=9 blocks access to food on the right.
        for y in range(20):
            env.add_stimulus(
                Stimulus(StimulusType.OBSTACLE, (9, y), intensity=1.0, radius=0.0)
            )
        env.add_stimulus(Stimulus(StimulusType.FOOD, (12, 10), intensity=1.0, radius=8.0))

        bug.drive_system.drives[DriveType.HUNGER].level = 0.8
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()
        # Move north: Euclidean distance to food decreases, but path is still blocked.
        bug.act(Direction.NORTH, env)
        bug.post_act(env)

        transition = bug._dqn.memory.buffer[0]
        # Should not receive positive shaping from impossible straight-line progress.
        assert transition.reward < 0.0

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

    def test_shaping_uses_decision_time_urgent_drive(self):
        # Hunger starts slightly above thirst, but thirst grows faster and becomes
        # most urgent after update(). Reward shaping should still target hunger.
        bug = DQNSowbug(
            position=(5, 5),
            perception_radius=10.0,
            hunger_rate=0.0,
            thirst_rate=0.2,
            temperature_rate=0.0,
        )
        env = Environment(width=20, height=20)
        food = Stimulus(StimulusType.FOOD, (5, 2), intensity=1.0, radius=10.0)
        water = Stimulus(StimulusType.WATER, (5, 8), intensity=1.0, radius=10.0)
        env.add_stimulus(food)
        env.add_stimulus(water)

        bug.drive_system.drives[DriveType.HUNGER].level = 0.51
        bug.drive_system.drives[DriveType.THIRST].level = 0.50
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.NORTH, env)
        bug.post_act(env)

        transition = bug._dqn.memory.buffer[0]
        # If shaping follows decision-time hunger target, this move is favorable.
        # If shaping incorrectly retargets thirst after update(), reward goes negative.
        assert transition.reward > 0.0

    def test_disappointment_extinction_updates_in_dqn_agent(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.memory_system.record_experience((5, 5), StimulusType.FOOD, 1.0, 1.0)

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.STAY, env)
        bug.post_act(env)

        entry = bug.memory_system.get_expected((5, 5), StimulusType.FOOD)
        assert entry is not None
        assert entry.disappointments >= 1
        assert entry.strength < 1.0

    def test_critical_hunger_penalizes_off_target_water_consumption(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        water = Stimulus(
            StimulusType.WATER, (5, 5), intensity=1.0, radius=2.0, quantity=10.0
        )
        env.add_stimulus(water)

        bug.drive_system.drives[DriveType.HUNGER].level = 0.95
        bug.drive_system.drives[DriveType.THIRST].level = 0.5
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.STAY, env)
        bug.post_act(env)
        transition = bug._dqn.memory.buffer[0]
        assert transition.reward < 0.0

    def test_reward_components_sum_to_total(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.drive_system.drives[DriveType.HUNGER].level = 0.6
        food = Stimulus(StimulusType.FOOD, (5, 5), intensity=1.0, radius=2.0, quantity=10.0)
        env.add_stimulus(food)

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.STAY, env)
        bug.post_act(env)
        state = bug.get_state()
        comps = state["reward_components"]
        reconstructed = (
            comps["drive_reduction"]
            + comps["shaping"]
            - comps["urgency_penalty"]
            - comps["off_target_penalty"]
            + comps["urgent_explore_bonus"]
            - comps["urgent_explore_penalty"]
            - comps["stasis_penalty"]
        )
        assert abs(reconstructed - state["reward_total"]) < 1e-5

    def test_unknown_urgent_target_gets_novelty_bonus(self):
        bug = DQNSowbug(position=(5, 5), dqn_urgent_explore_level=0.7)
        env = Environment(width=20, height=20)
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.EAST, env)
        bug.post_act(env)

        comps = bug.get_state()["reward_components"]
        assert comps["urgent_explore_bonus"] > 0.0

    def test_unknown_urgent_target_stay_gets_search_penalty(self):
        bug = DQNSowbug(position=(5, 5), dqn_urgent_explore_level=0.7)
        env = Environment(width=20, height=20)
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.STAY, env)
        bug.post_act(env)

        comps = bug.get_state()["reward_components"]
        assert comps["urgent_explore_penalty"] > 0.0

    def test_high_urgency_stay_incur_stasis_penalty_even_with_known_target(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        # Seed memory so target is known (urgent-search path is off)
        bug.memory_system.record_experience((10, 5), StimulusType.FOOD, 1.0, 1.0)
        bug.drive_system.drives[DriveType.HUNGER].level = 0.9
        bug.drive_system.drives[DriveType.THIRST].level = 0.0
        bug.drive_system.drives[DriveType.TEMPERATURE].level = 0.0

        bug.perceive(env)
        bug.decide()
        bug.act(Direction.STAY, env)
        bug.post_act(env)

        comps = bug.get_state()["reward_components"]
        assert comps["urgent_explore_penalty"] == 0.0
        assert comps["stasis_penalty"] > 0.0


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

    def test_state_has_reward_decomposition(self):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()
        bug.act(Direction.STAY, env)
        bug.post_act(env)
        state = bug.get_state()
        assert "reward_total" in state
        assert "reward_components" in state
        assert "drive_reduction" in state["reward_components"]
        assert "shaping" in state["reward_components"]
        assert "urgency_penalty" in state["reward_components"]
        assert "off_target_penalty" in state["reward_components"]
        assert "urgent_explore_bonus" in state["reward_components"]
        assert "urgent_explore_penalty" in state["reward_components"]
        assert "stasis_penalty" in state["reward_components"]


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

    def test_save_and_load_model_checkpoint(self, tmp_path):
        bug = DQNSowbug(position=(5, 5))
        env = Environment(width=20, height=20)
        bug.perceive(env)
        bug.decide()  # increments steps_done

        path = tmp_path / "sowbug_model.pt"
        bug.save_model(path)

        bug2 = DQNSowbug(position=(5, 5))
        bug2.load_model(path)
        assert bug2._dqn.steps_done == bug._dqn.steps_done


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
