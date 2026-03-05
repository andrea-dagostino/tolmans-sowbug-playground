"""Deep Q-Network components: replay memory, network, and training agent."""

import math
import random
from collections import deque
from pathlib import Path
from typing import NamedTuple

import torch
import torch.nn as nn
import torch.optim as optim


class Transition(NamedTuple):
    state: torch.Tensor
    action: int
    reward: float
    next_state: torch.Tensor
    done: bool
    next_valid_mask: torch.Tensor | None = None


class ReplayMemory:
    """Circular buffer of experience transitions."""

    def __init__(self, capacity: int) -> None:
        self.buffer: deque[Transition] = deque(maxlen=capacity)

    def push(
        self,
        state: torch.Tensor,
        action: int,
        reward: float,
        next_state: torch.Tensor,
        done: bool,
        next_valid_mask: torch.Tensor | None = None,
    ) -> None:
        self.buffer.append(
            Transition(state, action, reward, next_state, done, next_valid_mask)
        )

    def sample(self, batch_size: int) -> list[Transition]:
        return random.sample(list(self.buffer), batch_size)

    def __len__(self) -> int:
        return len(self.buffer)


class DQN(nn.Module):
    """3-layer feedforward Q-network.

    Input:  state vector (state_dim)
    Hidden: state_dim → hidden_size (ReLU) → hidden_size (ReLU)
    Output: Q-value per action (n_actions)
    """

    def __init__(self, state_dim: int, n_actions: int, hidden_size: int = 128) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, n_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DQNAgent:
    """Wraps training logic: action selection, optimization, target updates."""

    def __init__(
        self,
        state_dim: int,
        n_actions: int = 5,
        hidden_size: int = 128,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        eps_start: float = 0.9,
        eps_end: float = 0.05,
        eps_decay: float = 5000.0,
        tau: float = 0.005,
        batch_size: int = 128,
        replay_capacity: int = 50000,
    ) -> None:
        self.n_actions = n_actions
        self.gamma = gamma
        self.eps_start = eps_start
        self.eps_end = eps_end
        self.eps_decay = eps_decay
        self.tau = tau
        self.batch_size = batch_size

        self.policy_net = DQN(state_dim, n_actions, hidden_size)
        self.target_net = DQN(state_dim, n_actions, hidden_size)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=learning_rate)
        self.memory = ReplayMemory(replay_capacity)

        self.steps_done: int = 0
        self.last_loss: float = 0.0

    @property
    def epsilon(self) -> float:
        return self.eps_end + (self.eps_start - self.eps_end) * math.exp(
            -self.steps_done / self.eps_decay
        )

    def select_action(
        self, state: torch.Tensor, valid_actions: list[int] | None = None
    ) -> int:
        """Epsilon-greedy action selection."""
        candidate_actions = (
            valid_actions if valid_actions else list(range(self.n_actions))
        )
        self.steps_done += 1
        if random.random() < self.epsilon:
            return random.choice(candidate_actions)
        with torch.no_grad():
            q_values = self.policy_net(state.unsqueeze(0))
            if len(candidate_actions) != self.n_actions:
                masked = torch.full_like(q_values, float("-inf"))
                masked[:, candidate_actions] = q_values[:, candidate_actions]
                q_values = masked
            return int(q_values.argmax(dim=1).item())

    def get_q_values(self, state: torch.Tensor) -> torch.Tensor:
        """Return Q-values for all actions (no grad, for visualization)."""
        with torch.no_grad():
            return self.policy_net(state.unsqueeze(0)).squeeze(0)

    def optimize(self) -> float:
        """Sample a batch from replay and do one gradient step.

        Returns the loss value, or 0.0 if not enough samples.
        """
        if len(self.memory) < self.batch_size:
            return 0.0

        transitions = self.memory.sample(self.batch_size)

        state_batch = torch.stack([t.state for t in transitions])
        action_batch = torch.tensor([t.action for t in transitions], dtype=torch.long)
        reward_batch = torch.tensor(
            [t.reward for t in transitions], dtype=torch.float32
        )
        next_state_batch = torch.stack([t.next_state for t in transitions])
        done_batch = torch.tensor(
            [t.done for t in transitions], dtype=torch.bool
        )
        next_valid_mask_batch = torch.stack(
            [
                (
                    t.next_valid_mask.to(dtype=torch.bool)
                    if t.next_valid_mask is not None
                    else torch.ones(self.n_actions, dtype=torch.bool)
                )
                for t in transitions
            ]
        )

        # Q(s, a) for the actions actually taken
        q_values = self.policy_net(state_batch).gather(1, action_batch.unsqueeze(1))

        # V(s') = max_a Q_target(s', a)  — zero for terminal states
        with torch.no_grad():
            next_q_values = self._compute_next_q_values(
                next_state_batch, next_valid_mask_batch
            )
            next_q_values[done_batch] = 0.0

        expected_q = reward_batch + self.gamma * next_q_values

        loss = nn.functional.smooth_l1_loss(q_values.squeeze(1), expected_q)

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_value_(self.policy_net.parameters(), 100)
        self.optimizer.step()

        self.last_loss = loss.item()
        return self.last_loss

    def _compute_next_q_values(
        self, next_state_batch: torch.Tensor, next_valid_mask_batch: torch.Tensor
    ) -> torch.Tensor:
        """Max target Q over valid next actions only."""
        next_q_all = self.target_net(next_state_batch)
        masked_next_q = next_q_all.masked_fill(~next_valid_mask_batch, float("-inf"))
        next_q_values = masked_next_q.max(dim=1).values
        all_invalid = ~next_valid_mask_batch.any(dim=1)
        next_q_values[all_invalid] = 0.0
        return next_q_values

    def soft_update_target(self) -> None:
        """Polyak averaging: target ← τ·policy + (1-τ)·target."""
        for tp, pp in zip(
            self.target_net.parameters(), self.policy_net.parameters(), strict=True
        ):
            tp.data.copy_(self.tau * pp.data + (1.0 - self.tau) * tp.data)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "policy_state_dict": self.policy_net.state_dict(),
                "target_state_dict": self.target_net.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "steps_done": self.steps_done,
            },
            path,
        )

    def load(self, path: str | Path) -> None:
        checkpoint = torch.load(path, weights_only=True)
        self.policy_net.load_state_dict(checkpoint["policy_state_dict"])
        self.target_net.load_state_dict(checkpoint["target_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.steps_done = checkpoint["steps_done"]
