import copy, importlib.util, json, pathlib, shutil, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("validate_skills", ROOT / "scripts/validate_skills.py"); vs = importlib.util.module_from_spec(spec); spec.loader.exec_module(vs)
GRAPH = json.loads((ROOT / "knowledge/skill-graph.json").read_text())

class SkillGraph(unittest.TestCase):
    def check(self, graph, skills=None): return vs.check_graph(graph, skills or ROOT / ".claude/skills")

    def test_current_graph_is_clean(self): self.assertEqual(self.check(GRAPH), [])

    def test_a_validator_the_gate_cannot_see_is_reported(self):
        g = copy.deepcopy(GRAPH); g["edges"] = [e for e in g["edges"] if not (e["from"] == "head-shape-audit" and e["to"] == "character-gate")]
        self.assertTrue(any("head-shape-audit" in p and "cannot see" in p for p in self.check(g)))

    def test_a_claimed_dependency_that_is_not_in_the_code_is_reported(self):
        g = copy.deepcopy(GRAPH); g["edges"][5]["via"] = "--no-such-flag"
        self.assertTrue(any("--no-such-flag" in p for p in self.check(g)))

    def test_a_skill_with_no_edge_is_reported(self):
        g = copy.deepcopy(GRAPH); g["edges"] = [e for e in g["edges"] if "creator-bridge" not in (e["from"], e["to"])]
        self.assertTrue(any("creator-bridge" in p and "no edge" in p for p in self.check(g)))

    def test_unknown_skill_and_missing_file_are_reported(self):
        g = copy.deepcopy(GRAPH); g["edges"].append({"from": "ghost", "to": "character-gate", "artifact": "x", "kind": "doc", "consumer_file": "character-gate/SKILL.md", "via": "x"})
        g["edges"].append({"from": "render-validator", "to": "character-gate", "artifact": "x", "kind": "code", "consumer_file": "character-gate/scripts/nope.py", "via": "x"})
        p = self.check(g); self.assertTrue(any("'ghost'" in x for x in p)); self.assertTrue(any("nope.py" in x for x in p))

    def test_a_consumer_that_does_not_name_its_producer_is_reported(self):
        with tempfile.TemporaryDirectory() as t:
            skills = pathlib.Path(t) / "skills"; shutil.copytree(ROOT / ".claude/skills", skills, ignore=shutil.ignore_patterns("__pycache__"))
            p = skills / "render-validator/SKILL.md"; p.write_text(p.read_text().replace("`character-gate`", "the gate"))
            self.assertTrue(any("render-validator/SKILL.md does not name the `character-gate`" in x for x in self.check(GRAPH, skills)))

if __name__ == "__main__":
    unittest.main()
