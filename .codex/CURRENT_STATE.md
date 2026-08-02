# Codex Project Memory: Current State

Last updated: 2026-08-02 15:56:46 +0800

## Current Project Goal

- Maintain a source-backed, coefficient-aware Q8 HFPSS Studio with auditable proposition dependencies.

## Active Branch

- main

## Recent Decisions

- Treat DKLLW24 differential patterns as F4/W(F4)-aware but preserve W(F4)-unit ambiguity.
- Admit only reviewed mathematical propositions whose premises are admitted; exclude tombstones and cycles.

## Known Issues

- The fact DAG records explicit human/source review; it is not an automated formal verifier.

## Open Tasks

- Attach coefficient-context hypotheses to future reviewed propositions and separately construct any genuine mixed-RO normalizer action.

## Latest Log References

- .codex/logs/20260802T155636+0800.md

## Collaboration Notes

- Read this file before starting Codex-assisted work.
- Read `AGENTS.md` if present.
- Read only the most recent 3 to 10 logs from `.codex/logs/`.
- Do not store chain-of-thought, hidden reasoning, JSON memory, or external database state.
