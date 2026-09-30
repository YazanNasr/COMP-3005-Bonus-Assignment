"""Bottom-up evaluator for relational algebra parse trees."""

from dataclasses import dataclass
import operator

from ra_errors import NameErrorRA, SchemaError, TypeErrorRA
from relation import Column, Relation, TupleSet, value_type
from syntax_tree import (
    AttrRef,
    BinaryNode,
    BoolBinary,
    Comparison,
    Literal,
    NotCondition,
    ProjectNode,
    RelationNode,
    RenameNode,
    SelectNode,
)


COMPARATORS = {
    "=": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


@dataclass
class OperatorCount:
    operator: str
    number: int
    count: int = 0

    @property
    def label(self):
        return f"{self.operator}_{self.number}"


class Evaluator:
    def __init__(self, relations):
        self.relations = relations
        self.counts = []
        self._numbers = {"select": 0, "join": 0}

    def evaluate(self, node):
        if isinstance(node, RelationNode):
            relation = self.relations.get(node.name)
            if relation is None:
                raise NameErrorRA(f"unknown relation {node.name!r}")
            return relation
        if isinstance(node, SelectNode):
            return self._select(node)
        if isinstance(node, ProjectNode):
            return self._project(node)
        if isinstance(node, RenameNode):
            return self._rename(node)
        if isinstance(node, BinaryNode):
            if node.operator == "times":
                return self._times(self.evaluate(node.left), self.evaluate(node.right))
            if node.operator == "join":
                return self._join(node)
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            return self._set_operation(node.operator, left, right)
        raise AssertionError(f"unknown tree node {type(node).__name__}")

    def _new_count(self, name):
        self._numbers[name] += 1
        count = OperatorCount(name, self._numbers[name])
        self.counts.append(count)
        return count

    def _select(self, node):
        source = self.evaluate(node.child)
        condition = compile_condition(node.condition, source.columns)
        counter = self._new_count("select")
        output = []
        for row in source.rows:
            counter.count += 1
            if condition(row):
                output.append(row)
        return Relation(source.columns, output, source.force_qualified)

    def _project(self, node):
        source = self.evaluate(node.child)
        indices = [resolve_attribute(attribute, source.columns) for attribute in node.attributes]
        if len(indices) != len(set(indices)):
            raise SchemaError("projection lists the same resolved attribute more than once")
        columns = [source.columns[index] for index in indices]
        output = TupleSet()
        for row in source.rows:
            output.add(tuple(row[index] for index in indices))
        return Relation(columns, output.rows, source.force_qualified)

    def _rename(self, node):
        source = self.evaluate(node.child)
        names = [column.name for column in source.columns]
        if len(names) != len(set(names)):
            raise SchemaError(
                f"rename[{node.name}] would create duplicate qualified attribute names"
            )
        columns = [Column(node.name, column.name, column.kind) for column in source.columns]
        return Relation(columns, source.rows, source.force_qualified)

    def _times(self, left, right):
        columns = combined_columns(left, right)
        output = TupleSet()
        for left_row in left.rows:
            for right_row in right.rows:
                output.add(left_row + right_row)
        return Relation(columns, output.rows, True)

    def _join(self, node):
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        columns = combined_columns(left, right)
        counter = self._new_count("join")
        output = TupleSet()

        # Equality between one column from each side is the benchmark's common
        # case. It is still a genuine nested loop and still compares every
        # pair; resolving column names once avoids constructing a temporary
        # concatenated tuple for billions of nonmatching pairs.
        fast_indices = simple_cross_equality(
            node.condition, columns, len(left.columns)
        )
        if fast_indices is not None:
            left_index, right_index = fast_indices
            comparisons = 0
            for left_row in left.rows:
                left_value = left_row[left_index]
                for right_row in right.rows:
                    comparisons += 1
                    if left_value == right_row[right_index]:
                        output.add(left_row + right_row)
            counter.count = comparisons
            return Relation(columns, output.rows, True)

        condition = compile_condition(node.condition, columns)
        for left_row in left.rows:
            for right_row in right.rows:
                counter.count += 1
                combined = left_row + right_row
                if condition(combined):
                    output.add(combined)
        return Relation(columns, output.rows, True)

    def _set_operation(self, operation, left, right):
        ensure_union_compatible(left, right)
        left_set = TupleSet(left.rows)
        right_set = TupleSet(right.rows)
        output = TupleSet()
        if operation == "union":
            for row in left.rows:
                output.add(row)
            for row in right.rows:
                output.add(row)
        elif operation == "intersect":
            for row in left.rows:
                if right_set.contains(row):
                    output.add(row)
        elif operation == "minus":
            for row in left.rows:
                if not right_set.contains(row):
                    output.add(row)
        else:
            raise AssertionError(f"unknown set operation {operation}")
        return Relation(left.columns, output.rows, left.force_qualified)


def combined_columns(left, right):
    columns = list(left.columns) + list(right.columns)
    qualified = [column.qualified_name() for column in columns]
    if len(qualified) != len(set(qualified)):
        duplicates = sorted(name for name in set(qualified) if qualified.count(name) > 1)
        raise SchemaError(
            "qualified attribute names collide: " + ", ".join(duplicates)
        )
    return columns


def simple_cross_equality(condition, columns, left_width):
    """Return local column indices for a simple cross-side equality, if any."""
    if not isinstance(condition, Comparison) or condition.operator != "=":
        return None
    if not isinstance(condition.left, AttrRef) or not isinstance(condition.right, AttrRef):
        return None
    first = resolve_attribute(condition.left, columns)
    second = resolve_attribute(condition.right, columns)
    first_kind = columns[first].kind
    second_kind = columns[second].kind
    if first_kind is not None and second_kind is not None and first_kind != second_kind:
        raise TypeErrorRA(f"cannot compare {first_kind} to {second_kind} with '='")
    if first < left_width <= second:
        return first, second - left_width
    if second < left_width <= first:
        return second, first - left_width
    return None


def ensure_union_compatible(left, right):
    if len(left.columns) != len(right.columns):
        raise SchemaError("set-operation inputs have different numbers of attributes")
    for index, (left_column, right_column) in enumerate(zip(left.columns, right.columns), 1):
        if left_column.name != right_column.name:
            raise SchemaError(
                f"attribute {index} is {left_column.name!r} on the left but "
                f"{right_column.name!r} on the right"
            )
        if (
            left_column.kind is not None
            and right_column.kind is not None
            and left_column.kind != right_column.kind
        ):
            raise SchemaError(
                f"attribute {left_column.name!r} has incompatible types "
                f"{left_column.kind} and {right_column.kind}"
            )


def resolve_attribute(reference, columns):
    matches = []
    for index, column in enumerate(columns):
        if column.name != reference.name:
            continue
        if reference.relation is None or column.relation == reference.relation:
            matches.append(index)
    if not matches:
        raise NameErrorRA(f"unknown attribute {str(reference)!r}")
    if len(matches) > 1:
        raise NameErrorRA(f"ambiguous attribute {str(reference)!r}; qualify it")
    return matches[0]


def compile_condition(condition, columns):
    if isinstance(condition, Comparison):
        left_getter, left_kind = compile_operand(condition.left, columns)
        right_getter, right_kind = compile_operand(condition.right, columns)
        if left_kind is not None and right_kind is not None and left_kind != right_kind:
            raise TypeErrorRA(
                f"cannot compare {left_kind} to {right_kind} with {condition.operator!r}"
            )
        compare = COMPARATORS[condition.operator]

        def comparison(row):
            left_value = left_getter(row)
            right_value = right_getter(row)
            if value_type(left_value) != value_type(right_value):
                raise TypeErrorRA(
                    f"cannot compare {value_type(left_value)} to "
                    f"{value_type(right_value)} with {condition.operator!r}"
                )
            return compare(left_value, right_value)

        return comparison
    if isinstance(condition, NotCondition):
        child = compile_condition(condition.child, columns)
        return lambda row: not child(row)
    left = compile_condition(condition.left, columns)
    right = compile_condition(condition.right, columns)
    if condition.operator == "and":
        return lambda row: left(row) and right(row)
    return lambda row: left(row) or right(row)


def compile_operand(operand, columns):
    if isinstance(operand, Literal):
        value = operand.value
        return (lambda row, value=value: value), value_type(value)
    if not isinstance(operand, AttrRef):
        raise AssertionError(f"unknown operand {type(operand).__name__}")
    index = resolve_attribute(operand, columns)
    return (lambda row, index=index: row[index]), columns[index].kind


def evaluate(tree, relations):
    evaluator = Evaluator(relations)
    result = evaluator.evaluate(tree)
    return result, evaluator.counts
