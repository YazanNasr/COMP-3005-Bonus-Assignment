"""The 25 required cases from Section 7, in the same numbering."""

import unittest

from evaluator import evaluate
from parser import parse
from ra_errors import LexicalError, NameErrorRA, SchemaError, SyntaxErrorRA, TypeErrorRA
from relation import format_relation
from relation_loader import parse_relation_file
from syntax_tree import BinaryNode, SelectNode, format_tree
from tokenizer import tokenize


DATA = """
R(x, a, b, c, Name, Age) = {
  1, 1, 1, 0, Bob, 31
  2, 1, 2, 3, Alice, 20
  3, 0, 2, 0, Cara, 40
}
S(x, a, b, c, Name, Age) = {
  2, 1, 2, 3, Alice, 20
  4, 0, 0, 0, Dan, 50
}
A(x) = {
  1
  2
}
B(x) = {
  1
}
C(x) = {
  2
}
D(x) = {
  3
}
Emp(EID, Name, Age, MgrID, DID) = {
  E1, John, 32, E3, D1
  E2, Alice, 28, E3, D2
  E3, Bob, 29, E3, D1
}
Dept(DID, Department) = {
  D1, Engineering
  D2, Finance
}
Bad(y) = {
  1
}
"""


class RequiredCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.relations = parse_relation_file(DATA)

    def run_query(self, query):
        return evaluate(parse(query), self.relations)[0]

    def test_01_no_whitespace(self):
        self.assertIsInstance(parse("select[x1=3](R)"), SelectNode)

    def test_02_whitespace_same_tree(self):
        compact = format_tree(parse("select[x=3](R)"))
        spaced = format_tree(parse("select[ x = 3 ](R)"))
        self.assertEqual(compact, spaced)

    def test_03_maximal_munch_greater_equal(self):
        kinds = [token.kind for token in tokenize("select[Age>=30](R)")]
        self.assertIn(">=", kinds)
        self.assertNotIn(">", kinds)

    def test_04_greater_then_negative_number(self):
        tokens = tokenize("select[Age>-30](R)")
        self.assertIn(">", [token.kind for token in tokens])
        self.assertIn(-30, [token.value for token in tokens])

    def test_05_parenthesis_inside_string(self):
        tree = parse("select[Name='Bob)'](R)")
        self.assertIsInstance(tree, SelectNode)

    def test_06_comma_inside_string(self):
        tree = parse("select[Name='a,b'](R)")
        self.assertIsInstance(tree, SelectNode)

    def test_07_doubled_quote(self):
        tokens = tokenize("select[Name='O''Brien'](R)")
        strings = [token.value for token in tokens if token.kind == "STRING"]
        self.assertEqual(strings, ["O'Brien"])

    def test_08_keyword_as_attribute(self):
        tree = parse("select[union=3](R)")
        self.assertIsInstance(tree, SelectNode)

    def test_09_unterminated_string(self):
        with self.assertRaisesRegex(LexicalError, "position"):
            parse("select[Name='Bob](R)")

    def test_10_documented_precedence(self):
        tree = parse("A union B minus C")
        self.assertIsInstance(tree, BinaryNode)
        self.assertEqual(tree.operator, "minus")
        self.assertEqual(tree.left.operator, "union")

    def test_11_minus_is_left_associative_and_differs(self):
        chosen = self.run_query("A minus B minus C")
        other = self.run_query("A minus (B minus C)")
        self.assertEqual(chosen.rows, [])
        self.assertEqual(other.rows, [(2,)])

    def test_12_condition_precedence(self):
        result = self.run_query("select[not (a=1 and b=2) or c>3](R)")
        self.assertEqual([row[0] for row in result.rows], [1, 3])

    def test_13_and_before_or(self):
        result = self.run_query("select[a=1 and b=2 or c=0](R)")
        self.assertEqual([row[0] for row in result.rows], [1, 2, 3])

    def test_14_three_unary_levels(self):
        result = self.run_query(
            "project[Name](select[Age>30](select[DID='D1'](Emp)))"
        )
        self.assertEqual(result.rows, [("John",)])

    def test_15_parentheses_override_precedence(self):
        tree = parse("(A union B) minus (C intersect D)")
        self.assertEqual(tree.operator, "minus")
        self.assertEqual(tree.right.operator, "intersect")

    def test_16_missing_parenthesis(self):
        with self.assertRaises(SyntaxErrorRA) as raised:
            parse("select[Age>30](R")
        self.assertIn("expected ')'", str(raised.exception))
        self.assertIn("position", str(raised.exception))

    def test_17_empty_projection(self):
        with self.assertRaises(SyntaxErrorRA):
            parse("project[](R)")

    def test_18_attribute_against_attribute(self):
        result = self.run_query("select[a=b](R)")
        self.assertEqual([row[0] for row in result.rows], [1])

    def test_19_qualified_join_and_distinct_dids(self):
        result = self.run_query("Emp join[Emp.DID=Dept.DID] Dept")
        self.assertIn("Emp.DID", result.headers())
        self.assertIn("Dept.DID", result.headers())
        self.assertEqual(len(result.rows), 3)

    def test_20_rename_enables_self_join(self):
        result = self.run_query("rename[E2](Emp) join[Emp.MgrID=E2.EID] Emp")
        self.assertEqual(len(result.rows), 3)
        self.assertIn("E2.EID", result.headers())
        self.assertIn("Emp.EID", result.headers())

    def test_21_incompatible_union(self):
        with self.assertRaises(SchemaError):
            self.run_query("R union Bad")

    def test_22_number_string_type_error(self):
        with self.assertRaises(TypeErrorRA):
            self.run_query("select[Age>'30'](R)")

    def test_23_projection_removes_duplicates(self):
        result = self.run_query("project[DID](Emp)")
        self.assertEqual(result.rows, [("D1",), ("D2",)])

    def test_24_repeated_projection_is_clear_error(self):
        with self.assertRaisesRegex(SchemaError, "same resolved attribute"):
            self.run_query("project[Name, Name](R)")

    def test_25_empty_result_keeps_schema(self):
        result = self.run_query("select[Age>100](R)")
        output = format_relation(result)
        self.assertEqual(result.headers(), ["x", "a", "b", "c", "Name", "Age"])
        self.assertIn("(0 tuples)", output)
        self.assertNotIn("<empty>", output)


class AdditionalCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.relations = parse_relation_file(DATA)

    def test_unknown_relation(self):
        with self.assertRaises(NameErrorRA):
            evaluate(parse("Missing"), self.relations)

    def test_unknown_attribute(self):
        with self.assertRaises(NameErrorRA):
            evaluate(parse("select[Missing=1](R)"), self.relations)

    def test_cross_product_self_collision(self):
        with self.assertRaises(SchemaError):
            evaluate(parse("Emp times Emp"), self.relations)

    def test_duplicate_input_rows_collapse(self):
        relations = parse_relation_file("T(x) = {\n1\n1\n}\n")
        self.assertEqual(relations["T"].rows, [(1,)])

    def test_join_counter_counts_every_pair(self):
        result, counts = evaluate(parse("A join[A.x=B.x] B"), self.relations)
        self.assertEqual(result.rows, [(1, 1)])
        self.assertEqual(counts[0].count, 2)

    def test_select_counter_counts_every_input(self):
        _, counts = evaluate(parse("select[x>1](R)"), self.relations)
        self.assertEqual(counts[0].count, 3)

    def test_not_can_be_an_attribute_name(self):
        relations = parse_relation_file("T(not) = {\n3\n}\n")
        result, _ = evaluate(parse("select[not=3](T)"), relations)
        self.assertEqual(result.rows, [(3,)])

    def test_bare_strings_can_contain_hyphen_and_period(self):
        relations = parse_relation_file("T(x) = {\nD-1\na.b\n}\n")
        self.assertEqual(relations["T"].rows, [("D-1",), ("a.b",)])


if __name__ == "__main__":
    unittest.main()
