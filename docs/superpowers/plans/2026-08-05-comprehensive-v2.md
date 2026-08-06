# Result-Centered Discussion Skill v2.0.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Skill into a hard-gated, claim-level, source-verifiable Discussion workflow with hybrid local retrieval, semantic auditing, accurate document locators, and comprehensive regression tests.

**Architecture:** Replace the single core module with focused ingestion, indexing, evidence, argument, audit, workspace, and compiler modules. Persist immutable source hashes and structured intermediate artifacts so every claim, citation, paragraph, validation run, and final compilation is reproducible and invalidated when source files change.

**Tech Stack:** Python 3.10+, standard library, jsonschema, optional python-docx/openpyxl/python-pptx/pypdf/scikit-learn/sentence-transformers/pytesseract/pdf2image.

## Global Constraints

- Version is `2.0.0`.
- Project content remains local; no network API is required by any workflow.
- External evidence and study evidence are separate pools; external searches never fall back to study files.
- Final compilation always executes fresh validation and audit and refuses output on any error.
- Evidence authorization is claim-level, with immutable source hash, locator, verified excerpt, and excerpt hash.
- Existing v1 commands remain available where their behavior is safe; legacy cards receive explicit migration errors.
- All automated tests must pass from an extracted release ZIP.

---

### Task 1: Workspace, file roles, ingestion, freshness, and deduplication

**Files:**
- Create: `scripts/workspace.py`
- Create: `scripts/ingest/*.py`
- Create: `scripts/indexing/dedup.py`
- Test: `tests/test_workspace_ingest_v2.py`

- [ ] Write failing tests for excluded globs, file pool isolation, precise Office locators, source hashes, duplicate grouping, and stale indexes.
- [ ] Run the tests and confirm failures are caused by missing v2 behavior.
- [ ] Implement configuration normalization, role assignment, precise extraction, quality scores, optional OCR, hashing, and deduplication.
- [ ] Run the tests and confirm they pass.

### Task 2: Hybrid retrieval and query expansion

**Files:**
- Create: `scripts/indexing/bm25.py`
- Create: `scripts/indexing/semantic.py`
- Create: `scripts/indexing/query_expansion.py`
- Create: `scripts/indexing/search.py`
- Test: `tests/test_retrieval_v2.py`

- [ ] Write failing tests for bilingual expansion, no-pool-fallback, hybrid reranking, comparability metadata, and duplicate suppression.
- [ ] Run the tests and confirm failures.
- [ ] Implement deterministic BM25, local TF-IDF semantic retrieval, optional sentence-transformer backend, glossary expansion, metadata filtering, and comparability reranking.
- [ ] Run the tests and confirm they pass.

### Task 3: Claim-level evidence and argument contracts

**Files:**
- Create: `scripts/evidence/*.py`
- Create: `scripts/argument/*.py`
- Replace: `schemas/*.schema.json`
- Test: `tests/test_evidence_argument_v2.py`

- [ ] Write failing tests for formal JSON Schema validation, exact excerpt verification, source mutation invalidation, claim authorization, comparability matrices, and evidence tension maps.
- [ ] Run the tests and confirm failures.
- [ ] Implement claim-level evidence cards, excerpt hashes, source verification, comparability matrices, tension maps, contract validation, and legacy migration diagnostics.
- [ ] Run the tests and confirm they pass.

### Task 4: Structural, causal, semantic, and citation auditing

**Files:**
- Create: `scripts/audit/*.py`
- Test: `tests/test_audit_v2.py`

- [ ] Write failing tests for Chinese and English causal overclaiming, citation drift, two-center paragraphs, absent return-to-study closure, reference-list behavior, sentence functions, and structured semantic review.
- [ ] Run the tests and confirm failures.
- [ ] Implement deterministic structural/causal/citation auditing and a schema-validated Codex semantic-audit artifact with paragraph summaries, sentence functions, support mappings, deletion tests, drift findings, closure findings, and revision instructions.
- [ ] Run the tests and confirm they pass.

### Task 5: Hard compile gate and CLI

**Files:**
- Create: `scripts/compiler.py`
- Create: `scripts/cli.py`
- Modify: `scripts/discussion.py`
- Keep compatibility: `scripts/discussion_core.py`
- Test: `tests/test_compile_cli_v2.py`

- [ ] Write failing tests for direct compile bypass, empty drafts, stale validation, stale sources, unknown citations, missing contracts, incomplete semantic audit, and nonzero CLI exit codes.
- [ ] Run the tests and confirm failures.
- [ ] Implement the fresh release gate, atomic final output, structured run metadata, migration command, new CLI commands, and compatibility exports.
- [ ] Run the tests and confirm they pass.

### Task 6: Skill instructions, examples, evaluations, packaging, and release

**Files:**
- Modify: `SKILL.md`, `README.md`, `CHANGELOG.md`, `VERSION`
- Modify: `workflows/*`, `references/*`, `templates/*`, `evals/*`
- Create: `.github/workflows/ci.yml`
- Test: all test files and extracted ZIP verification

- [ ] Update all user-facing guidance to the v2 workflow and remove outdated v1 assumptions.
- [ ] Add evaluation cases for structured nonsense, incomparable evidence, source mutation, causal overclaiming, conflicting literature, and compile-gate bypass.
- [ ] Run unit tests, package checks, Python compilation, sample end-to-end workflow, and extracted-ZIP tests.
- [ ] Commit the v2 branch, publish it to GitHub, open and review a pull request, merge to `main`, and verify the remote version and files.
