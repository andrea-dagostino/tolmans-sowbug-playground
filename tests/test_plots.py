import matplotlib
matplotlib.use("Agg")

from matplotlib.figure import Figure

from tolmans_sowbug_playground.analysis.plots import (
    plot_drive_levels,
    plot_exploration_heatmap,
    plot_learning_curve,
    plot_path_efficiency,
)
from tolmans_sowbug_playground.systems.drives import DriveType


def _make_records(n=50):
    records = []
    for i in range(n):
        records.append({
            "tick": i,
            "agents": [
                {
                    "position": (i % 10, i // 10),
                    "orientation": "NORTH",
                    "drive_levels": {
                        DriveType.HUNGER: max(0, 0.8 - i * 0.01),
                        DriveType.THIRST: max(0, 0.5 - i * 0.005),
                        DriveType.TEMPERATURE: 0.1,
                    },
                    "perception_count": 2,
                }
            ],
            "stimuli": [],
        })
    return records


class TestPlots:
    def test_plot_drive_levels_returns_figure(self):
        records = _make_records()
        fig = plot_drive_levels(records)
        assert isinstance(fig, Figure)

    def test_plot_exploration_heatmap_returns_figure(self):
        records = _make_records()
        fig = plot_exploration_heatmap(records, grid_size=(10, 10))
        assert isinstance(fig, Figure)

    def test_plot_learning_curve_returns_figure(self):
        records = _make_records()
        fig = plot_learning_curve(records)
        assert isinstance(fig, Figure)

    def test_plot_path_efficiency_returns_figure(self):
        records = _make_records()
        fig = plot_path_efficiency(records, optimal_distance=5.0)
        assert isinstance(fig, Figure)
