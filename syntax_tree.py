"""Parse-tree node definitions and readable tree rendering."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AttrRef:
    name: str
    relation: str = None

    def __str__(self):
        return f"{self.relation}.{self.name}" if self.relation else self.name


@dataclass(frozen=True)
class Literal:
    value: object


@dataclass(frozen=True)
class Comparison:
    operator: str
    left: object
    right: object


@dataclass(frozen=True)
class BoolBinary:
    operator: str
    left: object
    right: object


@dataclass(frozen=True)
class NotCondition:
    child: object


@dataclass(frozen=True)
class RelationNode:
    name: str


@dataclass(frozen=True)
class SelectNode:
    condition: object
    child: object


@dataclass(frozen=True)
class ProjectNode:
    attributes: tuple
    child: object


@dataclass(frozen=True)
class RenameNode:
    name: str
    child: object


@dataclass(frozen=True)
class BinaryNode:
    operator: str
    left: object
    right: object
    condition: object = None


COMPARISON_NAMES = {
    "=": "Eq",
    "!=": "Ne",
    "<": "Lt",
    "<=": "Le",
    ">": "Gt",
    ">=": "Ge",
}


def format_operand(operand):
    if isinstance(operand, AttrRef):
        return f"Attr({operand})"
    value = operand.value
    if isinstance(value, str):
        return f"Str({value!r})"
    return f"Num({value})"


def format_condition(condition):
    if isinstance(condition, Comparison):
        name = COMPARISON_NAMES[condition.operator]
        return f"{name}({format_operand(condition.left)}, {format_operand(condition.right)})"
    if isinstance(condition, NotCondition):
        return f"Not({format_condition(condition.child)})"
    name = "And" if condition.operator == "and" else "Or"
    return f"{name}({format_condition(condition.left)}, {format_condition(condition.right)})"


def _label(node):
    if isinstance(node, RelationNode):
        return f"Relation({node.name})"
    if isinstance(node, SelectNode):
        return f"Select(cond={format_condition(node.condition)})"
    if isinstance(node, ProjectNode):
        return "Project(attrs=[" + ", ".join(map(str, node.attributes)) + "])"
    if isinstance(node, RenameNode):
        return f"Rename(name={node.name})"
    if node.operator == "join":
        return f"Join(cond={format_condition(node.condition)})"
    return node.operator.capitalize()


def _children(node):
    if isinstance(node, (SelectNode, ProjectNode, RenameNode)):
        return (node.child,)
    if isinstance(node, BinaryNode):
        return (node.left, node.right)
    return ()


def format_tree(root):
    lines = [_label(root)]

    def add_children(node, prefix):
        children = _children(node)
        for index, child in enumerate(children):
            last = index == len(children) - 1
            lines.append(prefix + ("└── " if last else "├── ") + _label(child))
            add_children(child, prefix + ("    " if last else "│   "))

    add_children(root, "")
    return "\n".join(lines)

