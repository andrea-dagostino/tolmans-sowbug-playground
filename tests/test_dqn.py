import random

import torch

from tolmans_sowbug_playground.systems.dqn import DQN, DQNAgent, ReplayMemory


class TestReplayMemory:
    def test_push_and_len(self):
        mem = ReplayMemory(capacity=100)
        assert len(mem) == 0
        state = torch.zeros(10)
        mem.push(state, 0, 1.0, state, False)
        assert len(mem) == 1

    def test_capacity_limit(self):
        mem = ReplayMemory(capacity=5)
        state = torch.zeros(10)
        for i in range(10):
            mem.push(state, 0, float(i), state, False)
        assert len(mem) == 5

    def test_sample(self):
        mem = ReplayMemory(capacity=100)
        state = torch.zeros(10)
        for i in range(20):
            mem.push(state, i % 5, float(i), state, False)
        batch = mem.sample(8)
        assert len(batch) == 8
        # Each element is a Transition namedtuple
        assert hasattr(batch[0], "state")
        assert hasattr(batch[0], "action")
        assert hasattr(batch[0], "reward")


class TestDQNNetwork:
    def test_output_shape(self):
        net = DQN(state_dim=56, n_actions=5, hidden_size=128)
        x = torch.randn(1, 56)
        out = net(x)
        assert out.shape == (1, 5)

    def test_batch_forward(self):
        net = DQN(state_dim=56, n_actions=5, hidden_size=64)
        x = torch.randn(32, 56)
        out = net(x)
        assert out.shape == (32, 5)

    def test_different_dims(self):
        net = DQN(state_dim=10, n_actions=3, hidden_size=32)
        x = torch.randn(4, 10)
        out = net(x)
        assert out.shape == (4, 3)


class TestDQNAgent:
    def test_select_action_returns_valid(self):
        agent = DQNAgent(state_dim=56, n_actions=5)
        state = torch.randn(56)
        action = agent.select_action(state)
        assert 0 <= action < 5

    def test_select_action_respects_valid_action_mask_when_exploring(self):
        agent = DQNAgent(
            state_dim=10, n_actions=5, eps_start=1.0, eps_end=1.0, eps_decay=1.0
        )
        state = torch.randn(10)
        valid_actions = [1, 3]
        for _ in range(50):
            action = agent.select_action(state, valid_actions=valid_actions)
            assert action in valid_actions

    def test_select_action_respects_valid_action_mask_when_exploiting(self):
        agent = DQNAgent(
            state_dim=10, n_actions=5, eps_start=0.0, eps_end=0.0, eps_decay=1.0
        )
        with torch.no_grad():
            # Make action 4 globally best, action 1 second best.
            for p in agent.policy_net.parameters():
                p.zero_()
            final_layer = agent.policy_net.net[-1]
            final_layer.bias.copy_(torch.tensor([0.0, 2.0, 0.5, 1.0, 5.0]))
        state = torch.randn(10)
        action = agent.select_action(state, valid_actions=[0, 1, 3])
        assert action == 1

    def test_epsilon_decays(self):
        agent = DQNAgent(state_dim=10, n_actions=5, eps_start=0.9, eps_end=0.05)
        eps_initial = agent.epsilon
        state = torch.randn(10)
        for _ in range(100):
            agent.select_action(state)
        assert agent.epsilon < eps_initial

    def test_get_q_values(self):
        agent = DQNAgent(state_dim=10, n_actions=5)
        state = torch.randn(10)
        q = agent.get_q_values(state)
        assert q.shape == (5,)

    def test_optimize_returns_zero_when_insufficient_data(self):
        agent = DQNAgent(state_dim=10, n_actions=5, batch_size=64)
        # Only push 10 transitions, batch_size is 64
        state = torch.randn(10)
        for i in range(10):
            agent.memory.push(state, 0, 1.0, state, False)
        loss = agent.optimize()
        assert loss == 0.0

    def test_optimize_runs_with_sufficient_data(self):
        agent = DQNAgent(
            state_dim=10, n_actions=5, batch_size=8, replay_capacity=100
        )
        state = torch.randn(10)
        for i in range(20):
            next_state = torch.randn(10)
            agent.memory.push(state, i % 5, 1.0, next_state, False)
            state = next_state
        loss = agent.optimize()
        assert loss > 0.0
        assert agent.last_loss == loss

    def test_compute_next_q_values_masks_invalid_actions(self):
        agent = DQNAgent(state_dim=4, n_actions=3, eps_start=0.0, eps_end=0.0)
        with torch.no_grad():
            for p in agent.target_net.parameters():
                p.zero_()
            final_layer = agent.target_net.net[-1]
            # Global max is action 2, but we'll mask it out.
            final_layer.bias.copy_(torch.tensor([1.0, 2.0, 10.0]))
        next_states = torch.randn(2, 4)
        next_valid_mask = torch.tensor(
            [
                [True, False, False],   # only action 0 valid -> value 1.0
                [False, True, False],   # only action 1 valid -> value 2.0
            ],
            dtype=torch.bool,
        )
        vals = agent._compute_next_q_values(next_states, next_valid_mask)
        assert torch.allclose(vals, torch.tensor([1.0, 2.0]))

    def test_soft_update_target(self):
        agent = DQNAgent(state_dim=10, n_actions=5, tau=0.5)
        # Modify policy net weights
        with torch.no_grad():
            for p in agent.policy_net.parameters():
                p.fill_(1.0)
        # Target should still have original weights
        target_before = [p.clone() for p in agent.target_net.parameters()]
        agent.soft_update_target()
        # After soft update, target should have moved toward policy
        for tp, tb in zip(agent.target_net.parameters(), target_before):
            assert not torch.equal(tp, tb)

    def test_save_and_load(self, tmp_path):
        agent = DQNAgent(state_dim=10, n_actions=5)
        state = torch.randn(10)
        agent.select_action(state)  # increment steps_done

        path = tmp_path / "model.pt"
        agent.save(path)

        agent2 = DQNAgent(state_dim=10, n_actions=5)
        agent2.load(path)
        assert agent2.steps_done == agent.steps_done

        # Weights should match
        for p1, p2 in zip(
            agent.policy_net.parameters(), agent2.policy_net.parameters()
        ):
            assert torch.equal(p1, p2)
