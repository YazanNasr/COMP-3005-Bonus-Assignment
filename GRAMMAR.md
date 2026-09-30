# Relational Algebra Language Grammar

This document defines the language accepted by the engine. The grammar was
written before the tokenizer and parser. ASCII spellings are normative.

## 1. Lexical rules

The notation below is ISO-style EBNF: `=` defines a rule, `|` separates
alternatives, `{ ... }` means zero or more repetitions, `[ ... ]` means an
optional item, and terminal text appears in quotes.

```ebnf
letter          = "A" | ... | "Z" | "a" | ... | "z" | "_" ;
digit           = "0" | ... | "9" ;
identifier      = letter, { letter | digit } ;
number          = [ "-" ], digit, { digit }, [ ".", digit, { digit } ] ;
quoted-string   = "'", { quoted-character | "''" }, "'" ;
quoted-character = ? any character except a single quote ? ;
bare-character  = ? any character except whitespace, comma, parentheses,
                    braces, a quote, or grammar punctuation ? ;
bare-string     = bare-character, { bare-character } ;
newline         = "\n" | "\r\n" ;
comment         = "//", { ? any character except newline ? }, newline ;
```

Two adjacent single quotes inside a quoted string represent one literal
single quote. Thus `'O''Brien'` has the value `O'Brien`.

The scanner reads character by character and uses maximal munch. In
particular, `>=`, `<=`, and `!=` are single tokens, while `>-30` consists of
`>` followed by the number `-30`. Whitespace is insignificant in queries.
Newlines are significant only while reading tuple rows in a relation file.
Blank lines and lines whose first non-whitespace characters are `//` are
ignored in relation files.

Keywords are contextual rather than reserved. The scanner emits every
identifier-shaped word as an `IDENT` token. The parser treats words such as
`union` as operators only where the grammar requires an operator. This is why
`select[union=3](R)` treats `union` as an attribute name. A unary keyword is
recognized as an operator only when immediately followed (ignoring whitespace)
by `[`. In a condition, an unquoted identifier is always an attribute
reference; string constants there must be quoted.

## 2. Relation-file grammar

```ebnf
relation-file   = { separator }, relation-definition,
                  { { separator }, relation-definition }, { separator } ;
separator       = newline | comment ;

relation-definition
                = identifier, "(", attribute-list, ")", "=", "{", newline,
                  { tuple-row | separator }, "}" ;
attribute-list  = identifier, { ",", identifier } ;
tuple-row       = literal, { ",", literal }, newline ;
literal         = number | quoted-string | bare-string ;
```

A relation file contains one or more definitions. Every tuple row must have
exactly the number of values named by its relation's attribute list. Within a
relation, a column has one consistent type: number or string. Integers and
decimals are both numbers and are compatible. Bare strings cannot contain
spaces, commas, parentheses, braces, or quote characters; such values must be
quoted. Duplicate input tuples collapse according to the engine's explicit
tuple-equality routine.

## 3. Query grammar

The expression grammar is stratified from lowest precedence to highest.
Repetition implements left associativity without left recursion.

```ebnf
query           = expression, EOF ;

expression      = union-expression ;
union-expression
                = intersect-expression,
                  { ( "union" | "minus" ), intersect-expression } ;
intersect-expression
                = product-expression,
                  { "intersect", product-expression } ;
product-expression
                = unary-expression,
                  { "times", unary-expression
                  | "join", "[", condition, "]", unary-expression } ;

unary-expression
                = "select", "[", condition, "]", "(", expression, ")"
                | "project", "[", projection-list, "]", "(", expression, ")"
                | "rename", "[", identifier, "]", "(", expression, ")"
                | primary ;
primary         = identifier | "(", expression, ")" ;
projection-list = attribute-reference, { ",", attribute-reference } ;

condition       = or-condition ;
or-condition    = and-condition, { "or", and-condition } ;
and-condition   = not-condition, { "and", not-condition } ;
not-condition   = { "not" }, condition-primary ;
condition-primary
                = "(", condition, ")" | comparison ;
comparison      = operand, comparison-operator, operand ;
comparison-operator
                = "=" | "!=" | "<" | "<=" | ">" | ">=" ;
operand         = number | quoted-string | attribute-reference ;
attribute-reference
                = identifier, [ ".", identifier ] ;
```

`projection-list` is nonempty by construction. Repeating the same resolved
attribute in one projection, as in `project[Name, Name](R)`, is a schema error
rather than a request for duplicate output columns.

## 4. Precedence and associativity

| Level | Operators | Associativity |
|---:|---|---|
| 1 (lowest) | `union`, `minus` | left |
| 2 | `intersect` | left |
| 3 | `times`, `join[condition]` | left |
| 4 (highest) | `select`, `project`, `rename`, explicit parentheses | prefix / explicit |

Consequently, `A union B minus C` parses as `(A union B) minus C`, and
`A minus B minus C` parses as `(A minus B) minus C`. Parentheses override
these rules. In conditions, `not` binds tighter than `and`, which binds tighter
than `or`; repeated `and` and `or` associate left.

The rules `union-expression`, `intersect-expression`, and
`product-expression` enforce the algebra precedence levels. Each consumes one
higher-precedence expression and then loops over following operators, which
enforces left associativity.

## 5. Ambiguity demonstration

The deliberately naive grammar

```text
Expr ::= Expr "union" Expr
       | Expr "minus" Expr
       | "(" Expr ")"
       | IDENT
```

has two parse trees for `A union B minus C`:

```text
Tree 1                              Tree 2
       minus                               union
      /     \                             /     \
   union     C                           A      minus
  /     \                                      /   \
 A       B                                    B     C

Meaning: (A union B) minus C          Meaning: A union (B minus C)
```

Use these union-compatible one-column relations:

```text
A(x) = { (1) }
B(x) = { (2) }
C(x) = { (1) }
```

The first tree produces `{(2)}` because `{(1), (2)} minus {(1)} = {(2)}`.
The second produces `{(1), (2)}` because `{(2)} minus {(1)} = {(2)}`, and
then `{(1)} union {(2)} = {(1), (2)}`. The stratified query grammar selects
Tree 1: `union` and `minus` occupy the same repetition rule and therefore
associate left.

The same associativity choice matters for `A minus B minus C`. For example,
with `A={(1),(2)}`, `B={(1)}`, and `C={(2)}`, the chosen grouping
`(A minus B) minus C` is empty, while `A minus (B minus C)` is `{(2)}`.

## 6. Parsing strategy

The implementation uses a hand-written recursive-descent parser with one
method for each grammar level. This is a good fit because the grammar has a
small fixed lookahead and each method mirrors one documented production.

Direct left recursion would make recursive descent recurse again without
consuming input. For example, implementing `Expr ::= Expr "union" Expr`
literally would call the `Expr` method from the same input position until the
Python recursion limit was reached. The grammar avoids this exactly in rules
such as:

```ebnf
union-expression = intersect-expression,
                   { ( "union" | "minus" ), intersect-expression } ;
```

The parser first consumes an `intersect-expression` and then uses a loop for
each following operator. This removes left recursion and simultaneously makes
the operators left-associative.

## 7. Semantic name rules

An unqualified attribute must identify exactly one input column. No match is a
name error; more than one match is an ambiguous-name error. A qualified name
must match both its relation qualifier and attribute name. `times` and `join`
retain both inputs' columns and print them qualified; a collision even after
qualification is a schema error. `rename[X]` changes the relation qualifier of
all columns to `X`, enabling self joins.

Set operations require the same number of columns, the same attribute names in
the same order, and compatible types position by position. Their output uses
the left schema. Numeric types are compatible with one another; strings are
compatible only with strings. A comparison between a number and a string is a
type error.

## 8. Sources and AI corrections

The design was informed by Robert Nystrom's *Crafting Interpreters*, especially
the chapters [Scanning](https://craftinginterpreters.com/scanning.html) and
[Parsing Expressions](https://craftinginterpreters.com/parsing-expressions.html),
for character-at-a-time scanning, recursive descent, and grammar-based
precedence. Python's official
[`time.perf_counter`](https://docs.python.org/3.11/library/time.html#time.perf_counter)
documentation informed the benchmark clock choice. The instructor's assignment
specification supplied the language and relational semantics.

AI assistance produced several incomplete or incorrect details that tests and
manual runs exposed: an early test fixture omitted the `Age` column used by its
own query; an error test assumed the message text appeared before the position;
and a smoke-test query requested `Emp.DID` from an example `Emp` relation that
did not contain `DID`. The fixture, assertion, and query were corrected after
their failures. `DESIGN_LOG.md` records the evidence and an additional plotting
failure in context.
