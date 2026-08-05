# Result-Centered Discussion Skill Design

## Goal

Create a Codex Skill that drafts scientific Discussion sections from project-local study results and literature while preventing topic-based information accumulation and functionless citations.

## Architecture

The Skill uses progressive disclosure. `SKILL.md` defines gates and routing. Workflow and reference files contain detailed judgment rules. A standard-library Python toolkit performs local extraction, BM25 retrieval, schema-oriented validation, trace auditing, and final compilation.

## Data flow

Project files → local text index → result ledger → result-specific searches → verified evidence cards → argument map → approved paragraph contracts → traceable draft → audit → clean Discussion.

## Reliability controls

- Full-text verification and source locators;
- explicit evidence roles;
- result-reference-contract traceability;
- reference allowlists per paragraph;
- causal ceiling fields;
- validation and audit exit codes;
- no external file upload by the bundled scripts;
- automated regression tests and behavioral evaluation cases.
