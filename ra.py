#!/usr/bin/env python3
"""Command-line interface for the relational algebra engine."""

import argparse
import sys

from evaluator import evaluate
from parser import parse
from ra_errors import RAError
from relation import format_relation
from relation_loader import load_relation_files
from syntax_tree import format_tree


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Evaluate relational algebra queries")
    parser.add_argument("query", nargs="?", help="query to parse or execute")
    parser.add_argument(
        "--tree",
        metavar="QUERY",
        help="print a query's parse tree without executing it",
    )
    parser.add_argument(
        "--data",
        action="append",
        default=[],
        metavar="FILE",
        help="relation-definition file (repeatable)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="print each select/join counter after execution",
    )
    return parser


def main(argv=None):
    arguments = build_argument_parser().parse_args(argv)
    try:
        if arguments.tree is not None:
            print(format_tree(parse(arguments.tree)))
            return 0
        if arguments.query is None:
            build_argument_parser().error("an execution query or --tree QUERY is required")
        if not arguments.data:
            build_argument_parser().error("executing a query requires at least one --data FILE")
        relations = load_relation_files(arguments.data)
        result, counts = evaluate(parse(arguments.query), relations)
        print(format_relation(result))
        if arguments.stats:
            print("\nOperator counters:")
            if not counts:
                print("(no select or join operators)")
            for count in counts:
                unit = "tuples examined" if count.operator == "select" else "pairs compared"
                print(f"{count.label}: {count.count} {unit}")
        return 0
    except RAError as error:
        print(error, file=sys.stderr)
        return 2
    except OSError as error:
        print(f"File error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
