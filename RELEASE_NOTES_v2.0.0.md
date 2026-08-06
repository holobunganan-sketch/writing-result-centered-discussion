# Writing Result-Centered Discussion v2.0.0

V2 strengthens the Skill from a structure-guided prototype into a hard-gated, claim-level Discussion workflow.

## Main additions

- strict separation of study evidence, external evidence, context files, and excluded files;
- incremental local indexing with source hashes and freshness checks;
- DOCX, XLSX, PPTX and PDF extraction, with optional OCR for scanned PDFs;
- hybrid BM25 and multilingual semantic retrieval with comparability reranking;
- claim-level evidence cards with exact source locations, verified excerpts and hashes;
- formal JSON Schema validation;
- comparability matrices and evidence-tension maps;
- claim-level paragraph contracts;
- Chinese and English causal-language auditing;
- structured semantic paragraph review and citation-deletion tests;
- a non-bypassable final compilation gate;
- BibTeX, RIS and EndNote mapping, v1 migration and DOCX copy writeback.

The downloadable ZIP is an installable Codex Skill package. Extract it, then run `python install.py --force` from the extracted directory.
