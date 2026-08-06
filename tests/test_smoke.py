import tempfile
import unittest
from pathlib import Path

from scripts.indexing.bm25 import scores, tokenize
from scripts.workspace import file_role, init_workspace, load_json


class SmokeTests(unittest.TestCase):
    def test_core_imports(self):
        from scripts.cli import build_parser
        from scripts.compiler import compile_draft
        from scripts.ingest import extract_file
        self.assertTrue(callable(build_parser))
        self.assertTrue(callable(compile_draft))
        self.assertTrue(callable(extract_file))

    def test_bm25_ranking(self):
        result = scores(["structured counselling treatment uptake", "unrelated laboratory method"], "counselling uptake")
        self.assertGreater(result[0], result[1])

    def test_workspace_file_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = init_workspace(root)
            config = load_json(ws / "config.json", {})
            self.assertEqual(file_role("results/results.md", config), "study-evidence")
            self.assertEqual(file_role("references/paper.pdf", config), "external-evidence")


if __name__ == "__main__":
    unittest.main()
