#!/usr/bin/env python3
"""Run and record the required performance study on this engine."""

import argparse
import gc
import json
import math
import platform
import statistics
from time import perf_counter

from evaluator import evaluate
from generate_data import generate_text
from parser import parse
from relation_loader import parse_relation_file


DEFAULT_SIZES = (1000, 2000, 4000, 8000, 16000, 32000, 64000)


def measure(tree, relations, repetitions):
    times = []
    final_result = None
    final_counts = None
    for _ in range(repetitions):
        gc.collect()
        start = perf_counter()
        final_result, final_counts = evaluate(tree, relations)
        times.append(perf_counter() - start)
    return {
        "times_s": times,
        "median_s": statistics.median(times),
        "output_tuples": len(final_result.rows),
        "counters": {count.label: count.count for count in final_counts},
    }


def run_study(sizes, repetitions, match_rate, rate_size, rates):
    trees = {
        "join": parse("R join[R.b=S.b] S"),
        "select": parse("select[a>=0](R)"),
        "project": parse("project[a](R)"),
    }
    results = []
    for size in sizes:
        relations = parse_relation_file(generate_text(size, size, match_rate))
        row = {"n": size, "m": size, "match_rate": match_rate}
        for operator, tree in trees.items():
            row[operator] = measure(tree, relations, repetitions)
        results.append(row)
        print(
            f"n={size}: join={row['join']['median_s']:.6f}s, "
            f"select={row['select']['median_s']:.6f}s, "
            f"project={row['project']['median_s']:.6f}s",
            flush=True,
        )

    rate_results = []
    join_tree = trees["join"]
    for rate in rates:
        relations = parse_relation_file(generate_text(rate_size, rate_size, rate))
        measurement = measure(join_tree, relations, repetitions)
        rate_results.append(
            {"n": rate_size, "m": rate_size, "match_rate": rate, **measurement}
        )
        print(
            f"rate={rate}: join={measurement['median_s']:.6f}s, "
            f"output={measurement['output_tuples']}",
            flush=True,
        )

    return {
        "machine": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "processor_note": "Apple M2, 8 CPU cores, 16 GB memory",
        },
        "method": {
            "repetitions": repetitions,
            "reported_statistic": "median",
            "main_match_rate": match_rate,
            "rate_study_size": rate_size,
            "rate_study_rates": list(rates),
            "timing_excludes": "data generation, relation parsing, and query parsing",
        },
        "sizes": results,
        "match_rates": rate_results,
    }


def log_log_slope(points, operator):
    xs = [math.log(row["n"]) for row in points]
    ys = [math.log(row[operator]["median_s"]) for row in points]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    return numerator / denominator


def add_slopes(results):
    results["slopes"] = {
        operator: log_log_slope(results["sizes"], operator)
        for operator in ("join", "select", "project")
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the COMP 3005 performance study")
    parser.add_argument("--output", default="performance_results.json")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--match-rate", type=int, default=1)
    parser.add_argument("--rate-size", type=int, default=8000)
    parser.add_argument("--rates", type=int, nargs="+", default=[0, 1, 4, 16])
    parser.add_argument("--sizes", type=int, nargs="+", default=list(DEFAULT_SIZES))
    arguments = parser.parse_args(argv)
    if arguments.repetitions < 1:
        parser.error("repetitions must be at least 1")

    results = run_study(
        arguments.sizes,
        arguments.repetitions,
        arguments.match_rate,
        arguments.rate_size,
        arguments.rates,
    )
    add_slopes(results)
    with open(arguments.output, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
        handle.write("\n")
    print(f"wrote {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

