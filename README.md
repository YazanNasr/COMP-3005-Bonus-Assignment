# COMP 3005 Bonus Project 1 — Relational Algebra Engine

This repository contains a hand-written relational algebra engine in Python.
It scans input character by character, parses with recursive descent, prints
the parse tree, evaluates expressions bottom up with set semantics, reports
five categories of user-facing errors, generates controlled test data, and
records operator measurements.

No regular-expression library, parser generator, `eval`, `exec`, dataframe
library, embedded SQL engine, or library cross product is used. Tuple
deduplication goes through the explicit `TupleSet`/`tuple_equal` implementation
in `relation.py`.

## Requirements

- Python 3.11 or newer for the engine and tests.
- Matplotlib only to regenerate the report plot. It is never imported by the
  engine or used by an algebra operator.

## Run it

Print a parse tree without loading data:

```sh
python3 ra.py --tree "project[Name](select[Age>30](Employees))"
```

Execute a query using the included example data:

```sh
python3 ra.py --data examples/employees.ra \
  "Employees join[Employees.DID=Departments.DID] Departments"
```

Add `--stats` to print the counter belonging to every `select` and `join`
operator in the query:

```sh
python3 ra.py --data examples/employees.ra --stats \
  "select[Age>30](Employees)"
```

More than one relation file may be supplied by repeating `--data FILE`.
Errors are printed without a Python traceback and the process exits with status
2.

## Relation-file format

```text
// employees and their departments
Employees(EID, Name, Age, DID) = {
  E1, John, 32, D1
  E2, Alice, 28, D2
  E3, Bob, 29, D1
}
```

Quoted strings use single quotes; two adjacent quotes represent one literal
quote. Tuple lines must contain exactly one value per attribute. Duplicate
tuples collapse. See `GRAMMAR.md` for the complete language and all precedence
decisions.

## Supported algebra

- Unary: `select[condition](expression)`,
  `project[attributes](expression)`, and `rename[NewName](expression)`.
- Binary: `union`, `intersect`, `minus`, `times`, and
  `join[condition]`.
- Conditions: `=`, `!=`, `<`, `<=`, `>`, `>=`, qualified or unqualified
  attributes, numbers, quoted strings, `not`, `and`, `or`, and parentheses.
- Numeric literals: signed integers and decimals.
- Set semantics and schema/type checks for every operator.

`join[c]` has theta-join semantics: it is logically `times` followed by
`select[c]`, not a natural join. The implementation uses nested loops and
compares every input pair. For the common cross-side equality condition it
resolves column positions once, but it does not build an index or skip pairs.

## Why `rename` is required for a self join

`Emp times Emp` would contain two different columns both named `Emp.EID` (and
the same problem for every other attribute), so the required fully qualified
schema would still collide. In

```text
rename[E2](Emp) join[Emp.MgrID=E2.EID] Emp
```

the renamed left input has columns such as `E2.EID`, while the right input
keeps names such as `Emp.EID`. Both copies can therefore be named and the join
condition can say which role each copy plays.

## Tests

Run the complete suite:

```sh
python3 -m unittest discover -v
```

`tests/test_required.py` follows cases 1–25 from Section 7 in order and adds
coverage for unknown names, self-product collisions, input deduplication,
contextual `not`, and exact counters.

## Data generation and performance study

Generate `R(a,b)` and `S(b,c)` with controlled sizes and match rate:

```sh
python3 generate_data.py --n 1000 --m 1000 --match-rate 4 --output data.ra
```

Regenerate every measurement (this takes several minutes because the largest
Python join genuinely makes 4.096 billion comparisons):

```sh
python3 benchmark.py
python3 plot_results.py
```

Raw repetitions are in `performance_results.json`; the analysis is in
`REPORT.md`; the chart is `performance_plot.png`.

## Code map

| File | Responsibility |
|---|---|
| `tokenizer.py` | character scanner, maximal munch, positions, strings |
| `parser.py` | recursive-descent query parser |
| `syntax_tree.py` | tree nodes and readable tree printer |
| `relation_loader.py` | relation-definition parser and type inference |
| `relation.py` | schemas, explicit tuple equality/deduplication, output |
| `evaluator.py` | all algebra operators, condition evaluation, counters |
| `ra.py` | command-line interface and clean error boundary |
| `generate_data.py` | configurable relation-file generator |
| `benchmark.py` | repeated measurements and raw results |
| `plot_results.py` | report-only log-log plot |

## Known limitations

The deliberate project exclusions remain: everything is in memory; there are
no nulls, persistence, indexes, hash joins, sort-merge joins, query rewriting,
or optimization. Names and keywords are case-sensitive. A completely empty
relation has no values from which to infer column types, so its unknown types
act as compatible until a later operation has actual values to check. The
nested-loop join is intentionally quadratic and a million-by-million join is
not feasible in this implementation.

