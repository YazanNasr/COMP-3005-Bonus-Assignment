#!/usr/bin/env python3
"""Create the report's log-log timing plot from measured JSON data."""

import argparse
import json
import os
import tempfile

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "comp3005-mpl"))
os.environ.setdefault("XDG_CACHE_HOME", os.path.join(tempfile.gettempdir(), "comp3005-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plot benchmark results")
    parser.add_argument("--input", default="performance_results.json")
    parser.add_argument("--output", default="performance_plot.png")
    arguments = parser.parse_args(argv)
    with open(arguments.input, "r", encoding="utf-8") as handle:
        results = json.load(handle)

    sizes = [row["n"] for row in results["sizes"]]
    for operator, marker in (("join", "o"), ("select", "s"), ("project", "^")):
        times = [row[operator]["median_s"] for row in results["sizes"]]
        slope = results["slopes"][operator]
        plt.loglog(sizes, times, marker=marker, label=f"{operator} (slope {slope:.3f})")
    plt.xlabel("Input tuples per relation, n (log scale)")
    plt.ylabel("Median wall time in seconds (log scale)")
    plt.title("Relational algebra operator scaling")
    plt.grid(True, which="both", linestyle=":", linewidth=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(arguments.output, dpi=180)
    print(f"wrote {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
