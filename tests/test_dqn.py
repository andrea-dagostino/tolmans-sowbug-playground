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
