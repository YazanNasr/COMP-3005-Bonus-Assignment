# Design Log

## 2026-09-29 — Grammar, implementation, testing, and measurement

I first translated the supplied specification into `GRAMMAR.md` and fixed the
student-selected rules before coding: contextual keywords, four algebra
precedence levels, left associativity, `not > and > or`, and an error for
repeated projection columns. I then implemented the scanner, recursive-descent
parser, tree printer, relation loader, explicit tuple set, operators, errors,
generator, and tests. The first complete run exercised all 25 required cases;
the final run also included eight focused edge cases.

Specific AI-generated problems found during this session:

1. The first version of required test 14 queried `Age` from an `Emp` fixture
   whose schema accidentally omitted `Age`. The test failed with the engine's
   `Name error: unknown attribute 'Age'`, showing that the diagnostic path was
   correct. I repaired the fixture by adding the intended column and values,
   then reran the whole suite.
2. The first assertion for required test 16 expected the words `expected ')'`
   before the word `position`. The actual error intentionally begins with its
   category and position, then names the missing parenthesis. I changed the
   test to check both required facts without imposing an irrelevant ordering.
3. An AI-written CLI smoke-test command tried to join on `Emp.DID`, but the
   example `Emp` relation has only `EID`, `Name`, and `MgrID`. The clean name
   error caught that faulty query. I corrected the demonstration to join
   `Employees.DID` with `Departments.DID`; no engine change was appropriate.
4. The first plotting attempt selected a graphical Matplotlib backend in the
   headless test environment and exited without producing the PNG. I found the
   missing file during artifact verification, selected the noninteractive
   `Agg` backend explicitly, regenerated the chart, and inspected the result.

The initial generic join also concatenated both rows before testing every
pair. That was semantically correct but needlessly slow: a 4,000-by-4,000 run
took about 4.05 seconds. I kept the required nested loops and comparison count
but resolved a simple cross-side equality's column positions once and only
concatenated rows that matched. The same 4,000-by-4,000 workload then took
about 0.35 seconds while still reporting exactly 16,000,000 comparisons.

Finally, I generated the benchmark data in memory before the timed boundary,
ran three repetitions at every required size through 64,000, and saved every
raw time. I used medians for the report, computed the log-log slopes from all
seven measurements, ran the additional match-rate study, and visually checked
the generated plot. The longest point really performed 4,096,000,000 pair
comparisons per repetition; it was not estimated.

## 2026-09-30 — Submission audit

I checked the clean Desktop submission copy against the deliverables and
grading categories, removed the workspace-only `AGENTS.md` file from that copy,
and reran all 33 tests successfully. I also reran representative parse-tree
and join commands; no code or measurement changes were needed.
