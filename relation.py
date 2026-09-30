"""Relation/schema representation with explicit set and tuple semantics."""

from dataclasses import dataclass


def value_type(value):
    return "number" if isinstance(value, (int, float)) and not isinstance(value, bool) else "string"


def tuple_equal(left, right):
    """The engine's definition of tuple equality; no built-in set owns it."""
    if len(left) != len(right):
        return False
    for left_value, right_value in zip(left, right):
        if value_type(left_value) != value_type(right_value):
            return False
        if left_value != right_value:
            return False
    return True


def tuple_hash(row):
    """A bucket hint only. Equality is always confirmed with tuple_equal."""
    result = 1469598103934665603
    for value in row:
        kind_marker = 1 if value_type(value) == "number" else 2
        result ^= hash((kind_marker, value))
        result *= 1099511628211
    return result


class TupleSet:
    """Insertion-ordered set using the engine's explicit equality routine."""

    def __init__(self, rows=()):
        self.rows = []
        self._buckets = {}
        for row in rows:
            self.add(tuple(row))

    def add(self, row):
        row = tuple(row)
        key = tuple_hash(row)
        bucket = self._buckets.get(key)
        if bucket is not None:
            for existing in bucket:
                if tuple_equal(existing, row):
                    return False
        else:
            bucket = []
            self._buckets[key] = bucket
        bucket.append(row)
        self.rows.append(row)
        return True

    def contains(self, row):
        bucket = self._buckets.get(tuple_hash(row), ())
        for existing in bucket:
            if tuple_equal(existing, row):
                return True
        return False


@dataclass(frozen=True)
class Column:
    relation: str
    name: str
    kind: str = None

    def qualified_name(self):
        return f"{self.relation}.{self.name}" if self.relation else self.name


class Relation:
    def __init__(self, columns, rows=(), force_qualified=False):
        self.columns = tuple(columns)
        self.force_qualified = force_qualified
        unique = TupleSet(rows)
        self.rows = unique.rows

    def headers(self):
        if self.force_qualified:
            return [column.qualified_name() for column in self.columns]
        return [column.name for column in self.columns]


def printable_value(value):
    if isinstance(value, str) and (
        value == "" or any(char in value for char in " ,(){}'")
    ):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def format_relation(relation):
    headers = relation.headers()
    rendered_rows = [[printable_value(value) for value in row] for row in relation.rows]
    widths = []
    for index, header in enumerate(headers):
        values = [len(row[index]) for row in rendered_rows]
        widths.append(max([len(header)] + values))

    def line(values):
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    output = [line(headers), "-+-".join("-" * width for width in widths)]
    output.extend(line(row) for row in rendered_rows)
    noun = "tuple" if len(relation.rows) == 1 else "tuples"
    output.append(f"({len(relation.rows)} {noun})")
    return "\n".join(output)

