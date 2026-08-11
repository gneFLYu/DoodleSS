# Codex Project Memory: Current State

Last updated: 2026-08-11 12:28:23 +0800

## Current Project Goal

- Maintain a source-backed, coefficient-aware Q8 HFPSS Studio with auditable proposition dependencies, corrected period identities, and separate computation/review surfaces.

## Active Branch

- main

## Recent Decisions

- The REU/Overleaf audit is encoded in `REU_LATEST_FACT_CHAIN.md` and in the runtime proposition graph through `backend/domain/reu_fact_chain.py`.
- Admit `a_{2sigma_i}=(x^2+y^2)u_{2sigma_i}=a_{sigma_i}^2`; keep the exact coefficient in `d3(u_{2sigma_i})=c x^2 h1 u` under review until a filtered topological psi-action and exact Thom normalization are independently sourced.
- Treat the topological Galois/normalizer action as real spectrum-level structure, but do not infer exact mixed-RO transport or orientation normalization from the coefficient-field action alone.
- Use D^8, not D^4, as the Q8-HFPSS same-object period. Interpret 16- and 32-patterns as repeated differential families.
- The period lattice has Smith normal form `(1,2,4,4,64)` and quotient `Z/64 + Z/4 + Z/4 + Z/2`; reject the older `64,8,8,4` exercise answer.
- `/` is computation mode and `/review` is the dedicated logic-graph/proposition-ledger mode.

## Verification

- New REU fact-chain tests: 2 passed.
- New page-mode tests: 2 passed.
- Focused interaction tests: 24 passed.
- Full suite: 151 tests, 150 passed; one pre-existing failure remains because `backend/domain/tex_renderer.py` points to an unavailable external `2Sigma_corrected_E11above.tex` fixture.
- Both page modes were checked in the live in-app browser; no console warnings/errors remain. JavaScript syntax, static-copy hashes, and `git diff --check` pass.

## Known Issues

- Restriction-based formulas may identify a target only up to a W(F4)-unit, and the chain does not construct arbitrary mixed-RO(Q8) transport.
- The exact Thom-orientation normalization required to promote the nonzero d3 pattern to coefficient 1 is not yet independently certified.
- The deterministic TeX-export test needs its external template source path made portable or the fixture restored.

## Open Tasks

- Attach future source-reviewed differentials and permanent cycles to the same D8 period-family metadata.
- Independently source the filtered topological psi-action and exact Thom normalization before admitting the exact d3 coefficient.

## Latest Log References

- .codex/logs/20260811T122823+0800.md
- .codex/logs/20260811T111736+0800.md
- .codex/logs/20260811T111300+0800.md
- .codex/logs/20260811T111212+0800.md
- .codex/logs/20260811T111024+0800.md

## Collaboration Notes

- Read this file before starting Codex-assisted work.
- Read `AGENTS.md` if present.
- Read only the most recent 3 to 10 logs from `.codex/logs/`.
- Do not store chain-of-thought, hidden reasoning, JSON memory, or external database state.
