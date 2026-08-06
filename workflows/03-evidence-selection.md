# 03 Evidence Selection

Search one result at a time. Candidate ranking is not evidence verification.

For each selected source:

1. Read the full local text and the relevant table, figure, or result section.
2. Create a card and one or more claim units.
3. Give every claim a unique ID such as `REF-004-C2`.
4. Record its linked result, argumentative role, precise locator, exact supporting excerpt, effect size, analysis level, directness, certainty, and forbidden inferences.
5. Assess population, design, intervention or exposure, outcome, follow-up, setting, and overall comparability.
6. Run `seal-card` to calculate source and excerpt hashes and verify the excerpt at the locator.

A source may support several claims. Each claim needs independent verification and authorization.
