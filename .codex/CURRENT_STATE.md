# Codex Project Memory: Current State

Last updated: 2026-09-22 18:00:00 +0800

## Current Project Goal

- Verify Q8-HFPSS high-filtration vanishing from period-class-indexed facts while preserving finite, Witt, and separately stored j-adic formal-series structure.

## Active Branch

- main at `05ba805` (`Further proofread`; local commit awaiting GitHub authentication for push).

## Repository checkout

- Canonical clone: `E:\FenglinYu\HFPSS Q_8\DoodleSS-github`.
- Remote: `https://github.com/gneFLYu/DoodleSS.git`.
- The clone was clean at checkout; current changes include the synchronized low-zoom dot-sizing implementation, its focused test, and a read-only unresolved-differential audit.

## Page coverage snapshot

- `ws_3sigma_i`: 249 classes, 16 differential records, 432 propositions. The source chart includes the (d_3), (d_5), (d_9), (d_{11}), (d_{19}), and (d_{23}) families, while the governing record still distinguishes review/source-proved claims from admitted mathematical status.
- `ws_sigma_i_2sigma_j`: 230 classes, 11 differential records, 407 propositions. FN-MIX-001, FN-MIX-004, and FN-MIX-006 have verified source records; FN-MIX-002, FN-MIX-003, and FN-MIX-005 remain review/blocked in `RECORD.md`.
- `backend/data/review/mixed_pq_d21_source.v1.json` and `mixed_phi_a_coefficient.v1.json` are conditional source audits with `runtime_admission: false`; they fix (c=\zeta^2) in the stated convention, prove only (b\ne0), and retain the canonical rank-one (P/Q\to Y) map with unresolved (b^{-1}).

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
- `backend/audit_undecided_differentials.py` reports five unresolved differential facts with source locators, bidegree checks, and explicit premise blockers; it does not promote any status.

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
