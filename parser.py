"""Hand-written recursive-descent parser for relational algebra queries."""

from ra_errors import SyntaxErrorRA
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
from tokenizer import tokenize


class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source)
        self.current = 0

    def parse(self):
        expression = self._union_expression()
        self._expect("EOF", "unexpected text after the complete query")
        return expression

    def _union_expression(self):
        expression = self._intersect_expression()
        while self._word("union") or self._word("minus"):
            operator = self._advance().value
            right = self._intersect_expression()
            expression = BinaryNode(operator, expression, right)
        return expression

    def _intersect_expression(self):
        expression = self._product_expression()
        while self._word("intersect"):
            self._advance()
            expression = BinaryNode("intersect", expression, self._product_expression())
        return expression

    def _product_expression(self):
        expression = self._unary_expression()
        while self._word("times") or self._word("join"):
            operator = self._advance().value
            condition = None
            if operator == "join":
                self._expect("[", "expected '[' after 'join'")
                condition = self._condition()
                self._expect("]", "expected ']' after the join condition")
            right = self._unary_expression()
            expression = BinaryNode(operator, expression, right, condition)
        return expression

    def _unary_expression(self):
        if self._unary_start("select"):
            self._advance()
            self._expect("[", "expected '[' after 'select'")
            condition = self._condition()
            self._expect("]", "expected ']' after the selection condition")
            child = self._parenthesized_input("select")
            return SelectNode(condition, child)
        if self._unary_start("project"):
            self._advance()
            self._expect("[", "expected '[' after 'project'")
            if self._check("]"):
                raise self._syntax("projection attribute list cannot be empty")
            attributes = [self._attribute_reference()]
            while self._match(","):
                attributes.append(self._attribute_reference())
            self._expect("]", "expected ']' after projection attributes")
            child = self._parenthesized_input("project")
            return ProjectNode(tuple(attributes), child)
        if self._unary_start("rename"):
            self._advance()
            self._expect("[", "expected '[' after 'rename'")
            name = self._expect("IDENT", "expected a new relation name").value
            self._expect("]", "expected ']' after the new relation name")
            child = self._parenthesized_input("rename")
            return RenameNode(name, child)
        return self._primary()

    def _parenthesized_input(self, operator):
        self._expect("(", f"expected '(' before the input to '{operator}'")
        expression = self._union_expression()
        self._expect(")", f"expected ')' after the input to '{operator}'")
        return expression

    def _primary(self):
        if self._match("("):
            expression = self._union_expression()
            self._expect(")", "expected ')' to close the grouped expression")
            return expression
        if self._check("IDENT"):
            return RelationNode(self._advance().value)
        raise self._syntax("expected a relation name, unary operator, or '('")

    def _condition(self):
        return self._or_condition()

    def _or_condition(self):
        condition = self._and_condition()
        while self._word("or"):
            self._advance()
            condition = BoolBinary("or", condition, self._and_condition())
        return condition

    def _and_condition(self):
        condition = self._not_condition()
        while self._word("and"):
            self._advance()
            condition = BoolBinary("and", condition, self._not_condition())
        return condition

    def _not_condition(self):
        if self._word("not") and self._peek(1).kind not in (
            ".",
            "=",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
        ):
            self._advance()
            return NotCondition(self._not_condition())
        if self._match("("):
            condition = self._condition()
            self._expect(")", "expected ')' to close the condition")
            return condition
        return self._comparison()

    def _comparison(self):
        left = self._operand()
        token = self._peek()
        if token.kind not in ("=", "!=", "<", "<=", ">", ">="):
            raise self._syntax("expected a comparison operator")
        operator = self._advance().kind
        right = self._operand()
        return Comparison(operator, left, right)

    def _operand(self):
        if self._check("NUMBER") or self._check("STRING"):
            return Literal(self._advance().value)
        if self._check("IDENT"):
            return self._attribute_reference()
        raise self._syntax("expected a number, quoted string, or attribute name")

    def _attribute_reference(self):
        first = self._expect("IDENT", "expected an attribute name")
        if self._match("."):
            second = self._expect("IDENT", "expected an attribute name after '.'")
            return AttrRef(second.value, first.value)
        return AttrRef(first.value)

    def _unary_start(self, word):
        return self._word(word) and self._peek(1).kind == "["

    def _word(self, word):
        return self._peek().is_word(word)

    def _check(self, kind):
        return self._peek().kind == kind

    def _match(self, kind):
        if not self._check(kind):
            return False
        self._advance()
        return True

    def _expect(self, kind, message):
        if self._check(kind):
            return self._advance()
        raise self._syntax(message)

    def _advance(self):
        token = self._peek()
        if token.kind != "EOF":
            self.current += 1
        return token

    def _peek(self, distance=0):
        index = min(self.current + distance, len(self.tokens) - 1)
        return self.tokens[index]

    def _syntax(self, message):
        token = self._peek()
        return SyntaxErrorRA(message, token.position, token.line, token.column)


def parse(source):
    return Parser(source).parse()
