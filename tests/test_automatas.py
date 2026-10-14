import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automatas import (  # noqa: E402
    accepts_dfa,
    accepts_nfa,
    render_regex,
    solve_regular_expression,
    subset_construction,
    verify_equivalence,
)


ROOT = Path(__file__).resolve().parents[1]


def load_case(name):
    import json
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class AutomataTests(unittest.TestCase):
    def test_annex_case_1_subset_construction_and_sink(self):
        nfa = load_case("caso1_afnd.json")
        dfa, _steps = subset_construction(nfa)
        transitions = {(e["from"], e["symbol"]): e["to"] for e in dfa["transitions"]}
        self.assertEqual(dfa["initial"], "{q0}")
        self.assertEqual(transitions[("{q0}", "a")], "{q0,q1}")
        self.assertEqual(transitions[("{q0}", "b")], "∅")
        self.assertEqual(transitions[("{q0,q1}", "b")], "{q2}")
        self.assertEqual(transitions[("∅", "a")], "∅")
        self.assertEqual(transitions[("∅", "b")], "∅")
        self.assertIn("{q2}", dfa["finals"])

    def test_annex_case_2_regular_expression_is_equivalent(self):
        automaton = load_case("caso2_af.json")
        dfa, _ = subset_construction(automaton)
        result = solve_regular_expression(dfa)
        self.assertTrue(result["regular_expression"])
        check = verify_equivalence(automaton, dfa, result["expression"], 6)
        self.assertEqual(check["mismatches"], [])

    def test_epsilon_closure_is_used_in_subset_construction(self):
        nfa = {
            "states": ["s", "f"], "alphabet": ["a"], "initial": "s", "finals": ["f"],
            "transitions": [{"from": "s", "symbol": "ε", "to": "f"}],
        }
        dfa, _ = subset_construction(nfa)
        self.assertEqual(dfa["initial"], "{f,s}")
        self.assertTrue(accepts_nfa(nfa, ""))
        self.assertTrue(accepts_dfa(dfa, ""))


if __name__ == "__main__":
    unittest.main()
