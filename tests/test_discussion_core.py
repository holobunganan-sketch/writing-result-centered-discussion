import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.discussion_core import (
    audit_draft,
    build_index,
    compile_draft,
    extract_file,
    init_workspace,
    search_for_result,
    search_index,
    validate_workspace,
)


FIXTURE = Path(__file__).parent / "fixtures" / "project"


class DiscussionSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="discussion-skill-"))
        self.project = self.tmp / "project"
        shutil.copytree(FIXTURE, self.project)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


    def test_office_extractors_read_minimal_docx_pptx_and_xlsx(self):
        docx = self.project / "sample.docx"
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>Discussion evidence</w:t></w:r></w:p></w:body></w:document>')
        pptx = self.project / "sample.pptx"
        with zipfile.ZipFile(pptx, "w") as archive:
            archive.writestr("ppt/slides/slide1.xml", '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><p:cSld><a:t>Slide evidence</a:t></p:cSld></p:sld>')
        xlsx = self.project / "sample.xlsx"
        with zipfile.ZipFile(xlsx, "w") as archive:
            archive.writestr("xl/sharedStrings.xml", '<sst xmlns="urn:x"><si><t>Sheet evidence</t></si></sst>')
            archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="urn:x"><sheetData><row><c t="s"><v>0</v></c></row></sheetData></worksheet>')

        docx_units, docx_error = extract_file(docx)
        pptx_units, pptx_error = extract_file(pptx)
        xlsx_units, xlsx_error = extract_file(xlsx)
        self.assertIsNone(docx_error)
        self.assertIsNone(pptx_error)
        self.assertIsNone(xlsx_error)
        self.assertIn("Discussion evidence", docx_units[0].text)
        self.assertIn("Slide evidence", pptx_units[0].text)
        self.assertIn("Sheet evidence", xlsx_units[0].text)

    def test_index_and_search_prioritize_directly_relevant_sources(self):
        init_workspace(self.project)
        report = build_index(self.project)
        self.assertGreaterEqual(report["indexed_files"], 4)
        hits = search_index(
            self.project,
            "structured counselling treatment uptake early protection gap",
            top_k=3,
        )
        self.assertTrue(hits)
        self.assertTrue(hits[0]["path"].endswith("supporting.txt"))
        paths = [hit["path"] for hit in hits]
        self.assertNotEqual(paths[0], "references/irrelevant.txt")


    def test_result_search_prefers_reference_roots_over_study_files(self):
        workspace = init_workspace(self.project)
        ledger = json.loads((Path(__file__).parent.parent / "templates" / "result_ledger.example.json").read_text(encoding="utf-8"))
        (workspace / "result_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        build_index(self.project)
        hits = search_for_result(self.project, "R1", top_k=10)
        self.assertTrue(hits)
        self.assertTrue(all(hit["path"].startswith("references/") for hit in hits))

    def test_validation_rejects_unlinked_and_unlocated_evidence(self):
        workspace = init_workspace(self.project)
        ledger = {
            "study_title": "Example",
            "study_design": "Cross-sectional",
            "results": [{
                "id": "R1",
                "priority": "primary",
                "finding": "Counselling increased uptake.",
                "source": {"file": "results.md", "locator": "R1"},
                "effect_direction": "increase",
                "effect_size": "54.7% vs 31.2%",
                "uncertainty": "not reported",
                "analysis_status": "prespecified",
                "causal_ceiling": "associational",
                "discussion_questions": ["How does this compare with prior studies?"],
                "importance": "high"
            }]
        }
        (workspace / "result_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        bad_card = {
            "id": "REF-001",
            "citation_key": "Support2024",
            "source_file": "references/supporting.txt",
            "locator": "",
            "population": "Adults",
            "design": "Prospective",
            "sample_size": "842",
            "exposure_or_intervention": "Counselling",
            "outcome": "Uptake",
            "main_finding": "Improved uptake",
            "effect_size": "",
            "limitations": ["Non-random allocation"],
            "linked_results": [],
            "evidence_roles": ["support"],
            "relevance_reason": "",
            "usable_claims": [],
            "forbidden_inferences": [],
            "verified_full_text": False
        }
        cards = workspace / "evidence_cards"
        (cards / "REF-001.json").write_text(json.dumps(bad_card), encoding="utf-8")
        result = validate_workspace(self.project)
        joined = "\n".join(result["errors"])
        self.assertIn("locator", joined)
        self.assertIn("linked_results", joined)
        self.assertIn("verified_full_text", joined)

    def test_validation_accepts_traceable_contract(self):
        workspace = init_workspace(self.project)
        ledger = json.loads((Path(__file__).parent.parent / "templates" / "result_ledger.example.json").read_text(encoding="utf-8"))
        (workspace / "result_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        card = json.loads((Path(__file__).parent.parent / "templates" / "evidence_card.example.json").read_text(encoding="utf-8"))
        (workspace / "evidence_cards" / "REF-001.json").write_text(json.dumps(card), encoding="utf-8")
        contract = json.loads((Path(__file__).parent.parent / "templates" / "paragraph_contract.example.json").read_text(encoding="utf-8"))
        (workspace / "paragraph_contracts" / "D1.json").write_text(json.dumps(contract), encoding="utf-8")
        argument_map = {"paragraph_order": ["D1"], "global_main_line": "R1 comparison and meaning"}
        (workspace / "argument_map.json").write_text(json.dumps(argument_map), encoding="utf-8")
        result = validate_workspace(self.project)
        self.assertEqual(result["errors"], [])

    def test_audit_flags_reference_outside_contract(self):
        workspace = init_workspace(self.project)
        ledger = json.loads((Path(__file__).parent.parent / "templates" / "result_ledger.example.json").read_text(encoding="utf-8"))
        (workspace / "result_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        card = json.loads((Path(__file__).parent.parent / "templates" / "evidence_card.example.json").read_text(encoding="utf-8"))
        (workspace / "evidence_cards" / "REF-001.json").write_text(json.dumps(card), encoding="utf-8")
        other = dict(card)
        other["id"] = "REF-002"
        other["citation_key"] = "Other2024"
        (workspace / "evidence_cards" / "REF-002.json").write_text(json.dumps(other), encoding="utf-8")
        contract = json.loads((Path(__file__).parent.parent / "templates" / "paragraph_contract.example.json").read_text(encoding="utf-8"))
        (workspace / "paragraph_contracts" / "D1.json").write_text(json.dumps(contract), encoding="utf-8")
        draft = "<!-- D:D1 R:R1 -->\nOur study found higher uptake. A prior study supports this [REF-001]. Another unrelated citation was added [REF-002].\n"
        (workspace / "discussion_trace.md").write_text(draft, encoding="utf-8")
        report = audit_draft(self.project)
        self.assertTrue(any("REF-002" in issue for issue in report["errors"]))

    def test_compile_strips_trace_comments_and_renders_keys(self):
        workspace = init_workspace(self.project)
        card = json.loads((Path(__file__).parent.parent / "templates" / "evidence_card.example.json").read_text(encoding="utf-8"))
        (workspace / "evidence_cards" / "REF-001.json").write_text(json.dumps(card), encoding="utf-8")
        (workspace / "discussion_trace.md").write_text(
            "<!-- D:D1 R:R1 -->\nOur finding aligned with prior evidence [REF-001].\n",
            encoding="utf-8",
        )
        output = compile_draft(self.project, citation_mode="key")
        text = output.read_text(encoding="utf-8")
        self.assertNotIn("<!--", text)
        self.assertIn("[@Support2024]", text)


if __name__ == "__main__":
    unittest.main()
