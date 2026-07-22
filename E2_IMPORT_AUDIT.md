# Conservative Q8-HFPSS E2 import

## Source-backed scope

`backend/domain/e2_import.py` contains a deliberately finite, source-verified catalogue.

- Integer representatives: DKLLW24, Theorem 3.3 and Table 2, PDF p. 16.
- `(*-sigma_i)` representatives: DKLLW24, Theorem 3.10 and Table 5, PDF p. 18.
- The link from those 2-Bockstein `E_infinity` presentations to the Q8-HFPSS `E2` page is the final paragraph of DKLLW24 §3.2, PDF p. 19, invoking Lemma 2.12.
- A small raw-relation subset is retained from Table 3 (PDF p. 16) and Table 6 (PDF p. 19). It is stored as cited propositions, not applied as automatic rewrite rules.

All of these records are **D-localized representatives**. Importing them does not claim an unlocalized presentation, does not create periodic translates, and does not assert that any class survives past `E2`.

## Legacy DoodleSS audit

The JSON files in `frontEnd_lty` contain only `generators`, `connections`, and (sometimes) `periodicityRules`. They do not identify their Q8 workspace, RO-grading convention, source document, or calculation stage. Their expanded points and periodicity rules are therefore never automatically imported.

Run a read-only audit:

```powershell
python backend/audit_e2_import.py --workspace sigma_i `
  --legacy-json ..\frontEnd_lty\spectral_sequence_project_newd9d11.json
```

Review statuses mean:

- `source-match`: an explicitly `E2` legacy point has an exact label-and-coordinate match to the cited finite catalogue. It is still not a request to create periodic copies.
- `needs-stage-attestation`: the legacy point has no explicit page, so it cannot be accepted as `E2`.
- `needs-manual-review`: no exact source match; it has no source-grading metadata.
- `out-of-scope`: its legacy page is not `E2`.

## Opt-in source import

To add only the cited catalogue to an existing project JSON, use:

```powershell
python backend/audit_e2_import.py --workspace integer --apply-verified `
  --project backend\data\project.json
```

The command is idempotent. It adds source propositions with PDF locators and leaves legacy chart dots, UI layout, Select behavior, connections, and periodicity expansion untouched.

## Deliberately unsupported

- Treating a legacy filename as evidence of the chart's RO(Q8)-grading or page.
- Importing `frontEnd_lty` connections as HFPSS differentials or relations.
- Importing any periodicity-generated dot from legacy data.
- Automatically reducing or transporting the catalogue through representation-period relations.
- Parsing all Table 3/Table 6 relations into executable algebra rules. The current backend has no source-audited presentation-to-AST map; raw cited propositions are retained instead.
