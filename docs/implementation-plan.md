# Result-Centered Discussion Skill Implementation Plan

**Goal:** Package an installable Codex Skill with local evidence retrieval, structured argument planning, validation, auditing, and compilation.

**Architecture:** Keep the main Skill concise and route detailed tasks to workflow references. Use a dependency-light Python CLI for deterministic operations. Preserve every intermediate artifact inside the manuscript project.

**Tech Stack:** Markdown, JSON Schema, Python 3 standard library, optional pypdf or pdftotext.

## Implemented tasks

1. Define tests for indexing, validation, auditing, and compilation.
2. Implement local extraction and BM25 retrieval.
3. Implement result ledger, evidence card, and paragraph contract validation.
4. Implement trace-aware draft audit and citation compilation.
5. Write Skill workflow and reference documentation.
6. Add install scripts, examples, schemas, and behavioral evaluations.
7. Run automated tests, CLI smoke tests, package checks, and ZIP integrity checks.
