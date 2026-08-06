# 01 Intake and Index

1. Run `init`.
2. Edit `config.json` before indexing. Confirm `file_pools`, `excluded_globs`, bilingual `glossary`, OCR policy, retrieval weights, and journal constraints.
3. Run `index` and inspect `project_inventory.json`.
4. Resolve unreadable study files and references intended for citation.
5. Review `duplicate_groups.json`; use the canonical published item and keep supplements as separate sources when they contain unique evidence.
6. Re-run `index` after any source change. Unchanged files are reused.

External evidence searches must use `external-evidence`. Empty external results are reported as evidence gaps.
