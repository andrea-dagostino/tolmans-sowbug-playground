import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from some_sim.systems.drives import DriveType


def _extract_agent_data(records: list[dict], agent_index: int = 0):
    """Extract per-tick data for a single agent."""
    ticks = []
    positions = []
    drive_data = {DriveType.HUNGER: [], DriveType.THIRST: [], DriveType.TEMPERATURE: []}

    for record in records:
        agents = record.get("agents", [])
        if agent_index >= len(agents):
            continue
        agent = agents[agent_index]
        ticks.append(record["tick"])
        positions.append(agent["position"])
        for dt in drive_data:
            drive_data[dt].append(agent.get("drive_levels", {}).get(dt, 0.0))

    return ticks, positions, drive_data


def plot_drive_levels(records: list[dict], agent_index: int = 0) -> Figure:
    ticks, _, drive_data = _extract_agent_data(records, agent_index)

    fig, ax = plt.subplots(figsize=(10, 4))
    colors = {
        DriveType.HUNGER: "#4CAF50",
        DriveType.THIRST: "#2196F3",
        DriveType.TEMPERATURE: "#F44336",
    }

    for dt, values in drive_data.items():
        ax.plot(ticks, values, label=dt.value.capitalize(), color=colors.get(dt, "#999"))

    ax.set_xlabel("Tick")
    ax.set_ylabel("Drive Level")
    ax.set_title("Drive Levels Over Time")
    ax.legend()
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    return fig


def plot_exploration_heatmap(
    records: list[dict], grid_size: tuple[int, int], agent_index: int = 0
) -> Figure:
    _, positions, _ = _extract_agent_data(records, agent_index)

    heatmap = np.zeros(grid_size)
    for pos in positions:
        x, y = pos[0], pos[1]
        if 0 <= x < grid_size[0] and 0 <= y < grid_size[1]:
            heatmap[y][x] += 1

    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(heatmap, cmap="YlOrRd", interpolation="nearest")
    ax.set_title("Exploration Heatmap (Visit Frequency)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    fig.colorbar(im, ax=ax, label="Visit Count")
    plt.tight_layout()
    return fig


def plot_learning_curve(
    records: list[dict], window: int = 20, agent_index: int = 0
) -> Figure:
    _, _, drive_data = _extract_agent_data(records, agent_index)
    hunger = drive_data[DriveType.HUNGER]

    # Compute rolling average of satisfaction events (hunger decreases)
    satisfactions = []
    for i in range(1, len(hunger)):
        satisfactions.append(1.0 if hunger[i] < hunger[i - 1] else 0.0)

    if len(satisfactions) < window:
        window = max(1, len(satisfactions))

    rolling = []
    for i in range(len(satisfactions)):
        start = max(0, i - window + 1)
        rolling.append(sum(satisfactions[start : i + 1]) / (i - start + 1))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(range(1, len(rolling) + 1), rolling, color="#4CAF50")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Satisfaction Rate (rolling avg)")
    ax.set_title("Learning Curve — Drive Satisfaction Over Time")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    return fig


def plot_path_efficiency(
    records: list[dict], optimal_distance: float, agent_index: int = 0
) -> Figure:
    _, positions, _ = _extract_agent_data(records, agent_index)

    cumulative_dist = [0.0]
    for i in range(1, len(positions)):
        dx = positions[i][0] - positions[i - 1][0]
        dy = positions[i][1] - positions[i - 1][1]
        cumulative_dist.append(cumulative_dist[-1] + math.sqrt(dx * dx + dy * dy))

    # Efficiency = optimal / actual (capped at 1.0)
    efficiency = []
    for d in cumulative_dist:
        if d == 0:
            efficiency.append(1.0)
        else:
            efficiency.append(min(1.0, optimal_distance / d))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(range(len(efficiency)), efficiency, color="#FF9800")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Path Efficiency")
    ax.set_title("Path Efficiency Over Time (optimal / actual distance)")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    return fig


def save_plot(fig: Figure, path: str) -> None:
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
