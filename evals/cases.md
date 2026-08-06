# Evaluation Cases

## 1. Long keyword-related literature list

Provide one result and 20 papers sharing disease keywords. Only three have comparable populations and outcomes. The agent must retrieve candidates, reject topic-only matches, and build claim units only from directly useful sources.

## 2. Structured nonsense

Provide syntactically valid cards and contracts whose claims do not support the paragraph conclusion. The semantic audit must identify the support failure and block compilation.

## 3. Source mutation

Seal a claim, modify its PDF or text file, and request compilation. The index and source hash gates must fail until reindexing and resealing occur.

## 4. Study-file contamination

Remove all external references while leaving Results and protocol files rich in matching keywords. `search-result` must return no candidates and must not cite study files as external evidence.

## 5. Observational causal overclaim

Use an observational result and draft English and Chinese causal language. Audit must identify both forms and require associational wording.

## 6. Correct paper, wrong claim

Authorize one result from a paper and cite a different conclusion from the same paper. Claim-level authorization must fail.

## 7. Conflicting literature

Provide supporting, contrasting, partially consistent, and noncomparable studies. The agent must complete the tension map and explain differences through named comparability dimensions.

## 8. Citation deletion test

Insert a citation that can be removed without changing the argument. Semantic audit must mark `advances_argument=false` and block compilation.

## 9. Multiple centers in one paragraph

Combine two unrelated results and two implications in one paragraph. Semantic audit must require splitting or a contract that demonstrates a single integrated claim.

## 10. Journal constraints

Set maximum Discussion and paragraph word limits. Audit and compile must enforce them for English, Chinese, or mixed-language drafts.

## 11. Legacy v1 workspace

Run `migrate-v1`. The migration must create a backup, convert IDs, and leave excerpts intentionally unverified until reread and sealed.

## 12. Direct compile bypass

Delete or stale the validation report, leave semantic review pending, and call `compile`. Compilation must run fresh checks and fail.

## 13. Scanned PDF

Provide a scanned reference. With OCR disabled it must be marked unreadable. With OCR enabled and local dependencies available, page-level OCR units and quality scores must be generated.

## 14. Duplicate publication versions

Provide a preprint and final article with the same DOI or equivalent title. Deduplication must select the final publication as canonical.

## 15. Existing Discussion revision

Provide a long existing draft. `revision-intake` must segment it, and the agent must bind each retained paragraph to results and contracts before revision.
