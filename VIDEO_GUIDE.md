# Five-Minute Video Guide

This is a speaking outline, not a prerecorded submission. Record the terminal
and code editor while following it.

## 0:00–0:45 — Introduce and run the tests

State that the project is a hand-written Python relational algebra engine with
no regex tokenizer or parser generator. Run:

```sh
python3 -m unittest discover -v
```

Point out that tests 1–25 correspond directly to Section 7.

## 0:45–1:35 — Show precedence through the parse tree

Run:

```sh
python3 ra.py --tree "A union B minus C"
```

Explain that the root is `Minus`, its left child is `Union`, and therefore the
tree means `(A union B) minus C`. Both operators share one loop in
`_union_expression`, so they associate left as documented in `GRAMMAR.md`.

## 1:35–2:20 — Execute a join and show the counter

Run:

```sh
python3 ra.py --data examples/employees.ra --stats \
  "Employees join[Employees.DID=Departments.DID] Departments"
```

Show that both qualified `DID` columns remain in the schema. Explain that three
employee tuples times two department tuples gives exactly six evaluated pairs,
regardless of how many match.

## 2:20–3:05 — Explain one report number

Open `REPORT.md` and select the 64,000 row. Say: “The
4,096,000,000 comparison count is not estimated; it is the join operator's
counter, and it equals 64,000 times 64,000. The 96.665575 seconds is the median
of three recorded wall times in `performance_results.json`. The near-2 slope
shows quadratic scaling.”

## 3:05–4:35 — Walk through the code structure

Show, in order:

1. `tokenizer.py`: character dispatch, maximal munch, doubled quotes, token
   positions.
2. `parser.py`: one function per precedence rule and loops that remove left
   recursion.
3. `syntax_tree.py`: node classes and the visible tree printer.
4. `relation.py`: `tuple_equal` and `TupleSet`, emphasizing that tuple
   deduplication is owned by this project.
5. `evaluator.py`: bottom-up dispatch, select counter, and nested-loop join
   counter.
6. `generate_data.py` and `benchmark.py`: controlled input and actual timing.

## 4:35–5:00 — Close with errors and limitations

Run one malformed query, for example:

```sh
python3 ra.py --tree "select[Age>30](R"
```

Point out the error category, exact position, missing parenthesis, and absence
of a stack trace. Close by noting the deliberate in-memory, no-index,
nested-loop limitations listed in `README.md`.
