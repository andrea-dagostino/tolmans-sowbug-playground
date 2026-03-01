import argparse
import sys

from some_sim.core.config import build_simulation, load_config


def cmd_run(args):
    config = load_config(args.config)
    if args.ticks:
        config.max_ticks = args.ticks
    sim = build_simulation(config)
    print(f"Running simulation: {config.max_ticks} ticks, seed {config.random_seed}")
    sim.run()
    print(f"Simulation complete. {sim.tick_count} ticks executed.")

    output = args.output or f"output_{sim.recorder.run_id}"
    sim.recorder.save_json(f"{output}.json")
    sim.recorder.save_csv(f"{output}.csv")
    print(f"Data saved to {output}.json and {output}.csv")


def cmd_serve(args):
    print("Starting web server...")
    from some_sim.web.server import start_server

    config = load_config(args.config) if args.config else None
    start_server(config=config, port=args.port)


def cmd_analyze(args):
    import json

    from some_sim.analysis.plots import (
        plot_drive_levels,
        plot_exploration_heatmap,
        plot_learning_curve,
        save_plot,
    )

    with open(args.input) as f:
        data = json.load(f)

    records = data["records"]
    plot_type = args.plot or "drives"
    prefix = args.input.rsplit(".", 1)[0]

    if plot_type == "drives":
        fig = plot_drive_levels(records)
        save_plot(fig, f"{prefix}_drives.png")
        print(f"Saved: {prefix}_drives.png")
    elif plot_type == "heatmap":
        fig = plot_exploration_heatmap(records, grid_size=(20, 20))
        save_plot(fig, f"{prefix}_heatmap.png")
        print(f"Saved: {prefix}_heatmap.png")
    elif plot_type == "learning":
        fig = plot_learning_curve(records)
        save_plot(fig, f"{prefix}_learning.png")
        print(f"Saved: {prefix}_learning.png")
    else:
        print(f"Unknown plot type: {plot_type}")
        print("Available: drives, heatmap, learning")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="some-sim",
        description="Schematic Sowbug simulation platform",
    )
    subparsers = parser.add_subparsers(dest="command")

    # run
    run_parser = subparsers.add_parser("run", help="Run a headless simulation")
    run_parser.add_argument("--config", required=True, help="Path to YAML config")
    run_parser.add_argument("--ticks", type=int, help="Override max ticks")
    run_parser.add_argument("--output", help="Output file prefix")
    run_parser.set_defaults(func=cmd_run)

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start web visualization")
    serve_parser.add_argument("--config", help="Path to YAML config")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port number")
    serve_parser.set_defaults(func=cmd_serve)

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze simulation data")
    analyze_parser.add_argument("--input", required=True, help="Path to JSON data file")
    analyze_parser.add_argument("--plot", help="Plot type to generate")
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
