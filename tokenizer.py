"""Character-by-character tokenizer. Deliberately uses no regular expressions."""

from dataclasses import dataclass

from ra_errors import LexicalError


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    text: str
    position: int
    line: int
    column: int

    def is_word(self, word):
        return self.kind == "IDENT" and self.value == word


class Tokenizer:
    TWO_CHARACTER = (">=", "<=", "!=")
    ONE_CHARACTER = set("()[]{},.=<>\n")

    def __init__(self, source, preserve_newlines=False, relation_mode=False):
        self.source = source
        self.preserve_newlines = preserve_newlines
        self.relation_mode = relation_mode
        self.index = 0
        self.line = 1
        self.column = 1
        self.only_space_on_line = True

    def tokenize(self):
        tokens = []
        while not self._at_end():
            char = self._peek()
            if char in " \t\f\v":
                self._advance()
            elif char == "\r" or char == "\n":
                token = self._newline()
                if self.preserve_newlines:
                    tokens.append(token)
            elif char == "/" and self._peek(1) == "/" and self.only_space_on_line:
                self._comment()
            elif char == "'":
                tokens.append(self._string())
            elif self.relation_mode and char not in self.ONE_CHARACTER:
                tokens.append(self._relation_atom())
            elif self._is_letter(char):
                tokens.append(self._identifier())
            elif self._is_digit(char) or (
                char == "-" and self._is_digit(self._peek(1))
            ):
                tokens.append(self._number())
            else:
                tokens.append(self._punctuation())
        tokens.append(Token("EOF", None, "", self.index + 1, self.line, self.column))
        return tokens

    def _at_end(self):
        return self.index >= len(self.source)

    def _peek(self, distance=0):
        position = self.index + distance
        return "\0" if position >= len(self.source) else self.source[position]

    def _advance(self):
        char = self.source[self.index]
        self.index += 1
        self.column += 1
        if char not in " \t\f\v":
            self.only_space_on_line = False
        return char

    def _start(self):
        return self.index, self.line, self.column

    def _make(self, kind, value, start, text=None):
        index, line, column = start
        if text is None:
            text = self.source[index : self.index]
        return Token(kind, value, text, index + 1, line, column)

    def _newline(self):
        start = self._start()
        if self._peek() == "\r":
            self.index += 1
            if self._peek() == "\n":
                self.index += 1
        else:
            self.index += 1
        self.line += 1
        self.column = 1
        self.only_space_on_line = True
        return self._make("NEWLINE", "\n", start, "\n")

    def _comment(self):
        while not self._at_end() and self._peek() not in "\r\n":
            self._advance()

    @staticmethod
    def _is_letter(char):
        return ("a" <= char <= "z") or ("A" <= char <= "Z") or char == "_"

    @staticmethod
    def _is_digit(char):
        return "0" <= char <= "9"

    def _identifier(self):
        start = self._start()
        self._advance()
        while self._is_letter(self._peek()) or self._is_digit(self._peek()):
            self._advance()
        text = self.source[start[0] : self.index]
        return self._make("IDENT", text, start, text)

    def _number(self):
        start = self._start()
        if self._peek() == "-":
            self._advance()
        while self._is_digit(self._peek()):
            self._advance()
        if self._peek() == "." and self._is_digit(self._peek(1)):
            self._advance()
            while self._is_digit(self._peek()):
                self._advance()
        text = self.source[start[0] : self.index]
        value = float(text) if "." in text else int(text)
        return self._make("NUMBER", value, start, text)

    def _relation_atom(self):
        """Scan an unquoted relation value; classify names and numbers afterward."""
        start = self._start()
        delimiters = set(" \t\f\v\r\n()[]{},=<>!'")
        while not self._at_end() and self._peek() not in delimiters:
            self._advance()
        text = self.source[start[0] : self.index]
        if not text:
            raise self._error(f"unexpected character {self._peek()!r}", start)
        numeric = self._relation_number(text)
        if numeric is not None:
            return self._make("NUMBER", numeric, start, text)
        if self._identifier_text(text):
            return self._make("IDENT", text, start, text)
        return self._make("BARE", text, start, text)

    @classmethod
    def _identifier_text(cls, text):
        if not text or not cls._is_letter(text[0]):
            return False
        return all(cls._is_letter(char) or cls._is_digit(char) for char in text[1:])

    @classmethod
    def _relation_number(cls, text):
        index = 0
        if text.startswith("-"):
            index = 1
        digit_start = index
        while index < len(text) and cls._is_digit(text[index]):
            index += 1
        if index == digit_start:
            return None
        if index < len(text) and text[index] == ".":
            index += 1
            fraction_start = index
            while index < len(text) and cls._is_digit(text[index]):
                index += 1
            if index == fraction_start:
                return None
        if index != len(text):
            return None
        return float(text) if "." in text else int(text)

    def _string(self):
        start = self._start()
        self._advance()
        characters = []
        while not self._at_end():
            char = self._peek()
            if char in "\r\n":
                raise self._error("unterminated quoted string", start)
            if char == "'":
                self._advance()
                if self._peek() == "'":
                    self._advance()
                    characters.append("'")
                    continue
                return self._make("STRING", "".join(characters), start)
            characters.append(self._advance())
        raise self._error("unterminated quoted string", start)

    def _punctuation(self):
        start = self._start()
        pair = self._peek() + self._peek(1)
        if pair in self.TWO_CHARACTER:
            self._advance()
            self._advance()
            return self._make(pair, pair, start)
        char = self._peek()
        if char in self.ONE_CHARACTER and char != "\n":
            self._advance()
            return self._make(char, char, start)
        if char == "!":
            raise self._error("'!' is not an operator; use '!='", start)
        if char == "-":
            raise self._error("'-' must be followed by digits to form a number", start)
        raise self._error(f"unexpected character {char!r}", start)

    @staticmethod
    def _error(message, start):
        index, line, column = start
        return LexicalError(message, index + 1, line, column)


def tokenize(source, preserve_newlines=False, relation_mode=False):
    return Tokenizer(source, preserve_newlines, relation_mode).tokenize()
