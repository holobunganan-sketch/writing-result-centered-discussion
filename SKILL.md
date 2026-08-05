---
name: writing-result-centered-discussion
description: Use when drafting, revising, or auditing a scientific manuscript Discussion from project-local results and reference files, especially when citations drift from the study result, paragraphs become unrelated information lists, or the argument lacks a clear main line.
---

# Writing Result-Centered Discussion

## Core Principle

Discussion follows the study results. Every paragraph makes one interpretable claim about one or more identified results. Every reference performs a declared argumentative function and advances that claim.

## Mandatory Workflow

Use the directory containing this `SKILL.md` as `SKILL_DIR`. Use the manuscript project as `PROJECT`.

1. Initialize and index before interpreting references.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" init
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" index
```

Read `.discussion-workspace/project_inventory.json`. Stop when a required source is unreadable. Report the file and extraction reason.

2. Build `.discussion-workspace/result_ledger.json` from the study's Results, tables, figures, protocol, and analysis files. Read `workflows/02-result-ledger.md`. Record the result source and locator, effect size, uncertainty, analysis status, causal ceiling, importance, and discussion questions.

3. Retrieve candidate literature separately for each important result.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" search-result --result-id R1
```

Read `workflows/03-evidence-selection.md`. Search results identify candidates only. Open and verify the full local source before creating an evidence card. Record a precise locator and one or more usable claims. Assign roles from `references/citation-roles.md`.

4. Build the global main line and paragraph contracts. Read `workflows/04-argument-design.md`. Each contract must contain one central claim, an ordered argument sequence, an explicit reference allowance, and a closing message that returns to the study result.

5. Run the structural gate.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" validate
```

Do not draft while validation has errors. Resolve every error. Review every warning and record the decision.

6. Draft only from approved contracts. Read `workflows/05-drafting.md`. Start each body paragraph with a trace header:

```markdown
<!-- D:D1 R:R1 -->
```

Use `[REF-001]` markers only for references allowed by that contract. Do not introduce a new result, reference, mechanism, or implication during drafting.

7. Audit, revise, and repeat.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" audit
```

Read `workflows/06-audit-revision.md`. Resolve all errors. Review warnings for citation density, unused evidence, contract coverage, and paragraph scope. Apply the deletion test: remove a reference when its removal does not weaken or change the argument.

8. Compile the clean manuscript text after the audit passes.

```bash
python "$SKILL_DIR/scripts/discussion.py" --project "$PROJECT" compile --citation-mode key
```

The output is `.discussion-workspace/discussion_final.md`.

## Hard Gates

- No Discussion prose before the result ledger, evidence cards, argument map, and approved paragraph contracts exist.
- No reference may enter a paragraph without a result link, role, relevance reason, precise source locator, and usable claim.
- No citation may appear outside the paragraph contract's `allowed_references`.
- No causal wording may exceed the result's `causal_ceiling` or the evidence design.
- No paragraph may end as a study list. Its final movement must state what the comparison, explanation, or limitation adds to interpretation of the current study.
- No full-text verification means no citation.
- No clean final file while validation or audit reports contain errors.

## Output Order

When the user asks for a plan, provide the result ledger summary, main line, evidence matrix, and paragraph contracts before prose. When the user asks for a draft, preserve the traceable workspace and provide the compiled Discussion after gates pass.
