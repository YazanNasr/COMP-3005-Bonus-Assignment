#!/usr/bin/env python3
"""Generate R(a,b) and S(b,c) relation files with a controlled match rate."""

import argparse


def generate_text(n, m, match_rate):
    if n < 0 or m < 0:
        raise ValueError("n and m must be nonnegative")
    if match_rate < 0:
        raise ValueError("match rate must be nonnegative")

    if match_rate == 0:
        r_keys = list(range(n))
        s_keys = [n + index for index in range(m)]
    else:
        key_count = max(1, (m + match_rate - 1) // match_rate)
        r_keys = [index % key_count for index in range(n)]
        s_keys = [index // match_rate for index in range(m)]

    lines = ["// generated relation R", "R(a, b) = {"]
    lines.extend(f"  {index}, {r_keys[index]}" for index in range(n))
    lines.extend(["}", "", "// generated relation S", "S(b, c) = {"])
    lines.extend(f"  {s_keys[index]}, {index}" for index in range(m))
    lines.extend(["}", ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate join benchmark relations")
    parser.add_argument("--n", type=int, required=True, help="number of R tuples")
    parser.add_argument("--m", type=int, required=True, help="number of S tuples")
    parser.add_argument(
        "--match-rate",
        type=int,
        required=True,
        help="approximately how many S tuples match each R tuple",
    )
    parser.add_argument("--output", required=True, help="output relation file")
    arguments = parser.parse_args(argv)
    try:
        text = generate_text(arguments.n, arguments.m, arguments.match_rate)
        with open(arguments.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

