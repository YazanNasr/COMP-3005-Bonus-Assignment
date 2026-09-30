"""Parser for the assignment's in-memory relation-definition format."""

from ra_errors import DataError, SchemaError, SyntaxErrorRA
from relation import Column, Relation, value_type
from tokenizer import tokenize


class RelationFileParser:
    def __init__(self, source):
        self.tokens = tokenize(source, preserve_newlines=True, relation_mode=True)
        self.current = 0

    def parse(self):
        relations = {}
        self._newlines()
        if self._check("EOF"):
            raise self._syntax("relation file contains no relation definitions")
        while not self._check("EOF"):
            name, relation = self._definition()
            if name in relations:
                raise SchemaError(f"relation {name!r} is defined more than once")
            relations[name] = relation
            self._newlines()
        return relations

    def _definition(self):
        name = self._expect("IDENT", "expected a relation name").value
        self._expect("(", "expected '(' after the relation name")
        if self._check(")"):
            raise self._syntax("a relation must have at least one attribute")
        attributes = [self._expect("IDENT", "expected an attribute name").value]
        while self._match(","):
            attributes.append(self._expect("IDENT", "expected an attribute name").value)
        self._expect(")", "expected ')' after relation attributes")
        self._expect("=", "expected '=' before the relation body")
        self._expect("{", "expected '{' before the relation body")
        self._expect("NEWLINE", "expected a newline after '{'")

        if len(attributes) != len(set(attributes)):
            raise SchemaError(f"relation {name!r} has duplicate attribute names")

        rows = []
        while True:
            self._newlines()
            if self._match("}"):
                break
            if self._check("EOF"):
                raise self._syntax(f"expected '}}' to close relation {name!r}")
            rows.append(self._tuple_row(name, len(attributes)))

        kinds = [None] * len(attributes)
        for row in rows:
            for index, value in enumerate(row):
                kind = value_type(value)
                if kinds[index] is None:
                    kinds[index] = kind
                elif kinds[index] != kind:
                    raise DataError(
                        f"attribute {name}.{attributes[index]} mixes "
                        f"{kinds[index]} and {kind} values"
                    )
        columns = [
            Column(name, attribute, kinds[index])
            for index, attribute in enumerate(attributes)
        ]
        return name, Relation(columns, rows)

    def _tuple_row(self, relation_name, arity):
        values = [self._literal()]
        while self._match(","):
            values.append(self._literal())
        if not self._check("NEWLINE"):
            raise self._syntax("expected a comma or newline in tuple row")
        self._advance()
        if len(values) != arity:
            raise DataError(
                f"relation {relation_name!r} has {arity} attributes but a tuple has "
                f"{len(values)} values"
            )
        return tuple(values)

    def _literal(self):
        token = self._peek()
        if token.kind in ("NUMBER", "STRING", "IDENT", "BARE"):
            self._advance()
            return token.value
        raise self._syntax("expected a number or string value")

    def _newlines(self):
        while self._match("NEWLINE"):
            pass

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

    def _peek(self):
        return self.tokens[self.current]

    def _syntax(self, message):
        token = self._peek()
        return SyntaxErrorRA(message, token.position, token.line, token.column)


def parse_relation_file(source):
    return RelationFileParser(source).parse()


def load_relation_files(paths):
    relations = {}
    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = parse_relation_file(handle.read())
        for name, relation in loaded.items():
            if name in relations:
                raise SchemaError(f"relation {name!r} is defined in more than one file")
            relations[name] = relation
    return relations
