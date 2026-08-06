---
name: writing-result-centered-discussion
description: Use when drafting, revising, or auditing a scientific manuscript Discussion from project-local results and literature, especially when references drift from the study findings, paragraphs become unrelated information lists, evidence is weakly traceable, or the argument lacks a clear main line.
---

# Writing Result-Centered Discussion

## Core rule

Discussion starts from the study results. Each paragraph advances one declared interpretation of identified results. Each external claim has a precise source location, verified excerpt, explicit argumentative role, comparability assessment, and claim-level citation ID.

Set `SKILL_DIR` to this Skill directory and `PROJECT` to the manuscript project.

## Mandatory sequence

1. Initialize and index.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" init
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" index
```

Inspect `project_inventory.json`. Classify files as `study-evidence`, `external-evidence`, `context-only`, or excluded. Resolve unreadable sources. External searches may use only `external-evidence`.

2. Build `result_ledger.json` from Results, tables, figures, protocol, and analysis outputs. Record a verified study-file locator, effect size, uncertainty, analysis status, discussion questions, importance, and causal ceiling. Complete `study_profile` for comparability reranking.

3. Retrieve literature separately for each result.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" search-result --result-id R1
```

Candidates require full-text review. Create evidence cards with claim IDs such as `REF-001-C1`. Each claim must include its linked result, role, statement, exact locator, verbatim supporting excerpt, forbidden inferences, evidence strength, and comparability assessment. Run `seal-card` after entering the excerpt.

4. Complete `comparability_matrix.json` and `evidence_tension_map.json`. State which claims support, contrast with, partially align with, or cannot be compared with each study result. Record unresolved questions.

5. Build `argument_map.json` and approved paragraph contracts. A contract contains one central claim, one discussion question, ordered argument steps, a claim-level allowance list, and a closing message that returns to the study result.

6. Run structural validation.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" validate
```

Drafting is blocked while errors remain.

7. Draft from approved contracts. Start each paragraph with:

```markdown
<!-- D:D1 R:R1 -->
```

Cite claim IDs, for example `[REF-001-C1]`. Do not introduce claims outside the contract.

8. Generate the semantic-audit task.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" semantic-audit-init
```

Read `semantic_audit/tasks.json`. Review every paragraph and complete `semantic_audit_report.json`. Confirm one central claim, result focus, sentence functions, claim support, citation deletion consequences, topic stability, evidence-strength limits, and return to the study.

9. Audit and compile.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" audit
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" compile --citation-mode key
```

`compile` reruns index freshness, Schema validation, source verification, causal audit, citation authorization, semantic audit, and journal constraints. It refuses output on any error. The final text is `discussion_final.md`.

## Non-negotiable gates

- A source mutation invalidates its evidence claims until reindexed and resealed.
- An external search never falls back to Results, protocol, manuscript, or notes.
- A reference is authorized at claim level. A correct paper cannot support an undeclared claim.
- Citation count is not a quality target. Delete a citation when its removal causes no loss in the argument.
- Observational or descriptive results cannot use causal language.
- A paragraph that cannot be summarized in one clear sentence requires revision.
- Final compilation cannot use old validation or audit reports.

Read the matching file in `workflows/` before each stage. Use `migrate-v1` for old workspaces and `revision-intake` for an existing Discussion draft.
