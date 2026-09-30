"""User-facing errors for the relational algebra engine."""


class RAError(Exception):
    """Base class for every error that may be shown to a user."""

    category = "Error"

    def __init__(self, message, position=None, line=None, column=None):
        super().__init__(message)
        self.message = message
        self.position = position
        self.line = line
        self.column = column

    def __str__(self):
        if self.position is None:
            return f"{self.category}: {self.message}"
        location = f"position {self.position}"
        if self.line is not None and self.column is not None:
            location += f" (line {self.line}, column {self.column})"
        return f"{self.category} at {location}: {self.message}"


class LexicalError(RAError):
    category = "Lexical error"


class SyntaxErrorRA(RAError):
    category = "Syntax error"


class NameErrorRA(RAError):
    category = "Name error"


class SchemaError(RAError):
    category = "Schema error"


class TypeErrorRA(RAError):
    category = "Type error"


class DataError(RAError):
    category = "Data error"

