# Codex Project Memory: Current State

Last updated: 2026-09-10 14:08:55 +0800

## Current Project Goal

- Verify Q8-HFPSS high-filtration vanishing from period-class-indexed facts while preserving finite, Witt, and separately stored j-adic formal-series structure.

## Active Branch

- main

## Recent Decisions

- Treat bo-pattern as a j=v1^4D^-1 formal-power-series module classification, never as a low-filtration or short-tower classification.
- Use D^8 for invertible HFPSS object identity; use g^N D^(8Z) as an all-family HFPSS semiperiod, including bo; use the bidirectional g,D^8 lattice only with a positive-filtration Tate comparison certificate.
- Route j-adic bo families to a separate fixed-differential/permanent-cycle registry; do not require continuous complete-module certificates or include finite killed vectors in their rank audit.
- Expose the computed high-filtration fate audit directly at /review, while retaining the read-only JSON API.

## Known Issues

- The periodic fate audit remains underdetermined: one of five finite-rank seed obligations is covered and four remain open.
- formal_notes does not enumerate a complete E2 basis in all nine RO(Q8)/P sectors.
- FN-2I-019 and FN-3I-010 are not yet fate-certifying, and the rank-two A+B target retains a one-dimensional quotient.

## Open Tasks

- Enumerate each finite/Witt sector by module generators in one g-forward/D8 fundamental family; keep formal-series families in the separate registry.
- Review the fixed integer and sigma-i bo differential/permanent templates and promote their family status only after source/admission review.
- Review FN-2I-019 and FN-3I-010 for Danus admission and supply the missing rank in the A+B target cell.

## Latest Log References

- .codex/logs/20260910T140758+0800.md
- .codex/logs/20260910T053339+0800.md
- .codex/logs/20260908T205809+0800.md
- .codex/logs/20260908T184330+0800.md
- .codex/logs/20260908T184148+0800.md
- .codex/logs/20260826T050831+0800.md
- .codex/logs/20260818T163055+0800.md
- .codex/logs/20260818T151555+0800.md
- .codex/logs/20260817T121535+0800.md
- .codex/logs/20260817T120539+0800.md

## Collaboration Notes

- Read this file before starting Codex-assisted work.
- Read `AGENTS.md` if present.
- Read only the most recent 3 to 10 logs from `.codex/logs/`.
- Do not store chain-of-thought, hidden reasoning, JSON memory, or external database state.
