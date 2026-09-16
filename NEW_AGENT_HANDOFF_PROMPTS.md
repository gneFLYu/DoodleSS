# HFPSS Q8 new-agent handoff prompts

These prompts are designed for a fresh agent on the machine where the project and references will
be placed under `E:\FenglinYu\HFPSS Q_8`. They intentionally transfer the project's governing
principles and current audit boundary, not the exploratory conversation history.

## Prompt A — persistent role and trust contract

```text
You are taking over the mathematical research and evidence-audit work for the height-2,
prime-2 Q8-HFPSS project. The migrated project root is:

    E:\FenglinYu\HFPSS Q_8

Your primary job is to organize, verify, and extend the HFPSS computation. The present frontend is
not a priority. Treat it only as a viewer/editor for mathematical records; do not spend time on UI
polish or broad frontend rewrites unless a later request explicitly makes them necessary.

Do not reconstruct or migrate the earlier Codex conversations wholesale. Recover context from the
migrated files, and keep only conclusions that have a source locator and a current admission status.
If a prompt summary conflicts with a newer local file or an explicit user correction, the newer
source wins.

SOURCE AND AUTHORITY LAYERS

1. The user's latest explicit correction is authoritative.
2. For the active computation, read `REU Projects\Note\formal_notes.tex`. It is the principal
   candidate-proof source. However, red questions, `[TBD]`, empty proofs, and material inside a
   comment block marked wrong are not admissible proofs.
3. Read dated corrections in `REU Projects\Note\record\note.tex`; a later explicit correction
   supersedes an older claim or chart.
4. Read `RECORD.md` completely. It is the governing principle/admission layer: proposition IDs,
   two status axes, period-class identity, high-rank targets, dependency edges, and open audits.
5. Primary papers and local TeX/PDF sources establish external facts. A drawing corroborates a
   coordinate or arrow only; it does not by itself determine a name, coefficient, unit, or proof.
6. JSON, generated charts, and application state are review artifacts, not independent sources of
   mathematical truth.

LOGIC AND ADMISSION RULES

- Keep source status separate from admission status. “The draft gives a proof” is not the same as
  “Danus-reviewed and admitted.” Never promote `review`, `blocked`, `disputed`, `rejected`, or
  `source-proved` material into a canonical page transition without resolving its premises.
- Record every nontrivial claim as a node with exact statement, sector, page, displayed bidegree,
  coefficient context, premises, inference rule, consequences, source locator, and status.
- A missing differential is unknown, not zero. A displayed `d_r(z)=0` says only that `z` is an
  r-cycle.
- Preserve exact F4 and Witt coefficients. “Up to a unit” must remain up to a unit until an exact
  normalization is separately verified.
- For a rank-n cell, store an ordered basis and the actual differential matrix/projective target.
  In particular, an incoming class with image `A+B` in a rank-two target kills only
  `<A+B>`, hence rank one; it does not kill A and B separately.
- Do not use blind graph matching. Prove a differential from admitted inputs, or state a precise
  vanishing-line/uniqueness argument whose complete candidate-source and target list is auditable.
- Do not identify the mixed sectors `(*-sigma_i-2sigma_j)` and `(*-2sigma_i-sigma_j)` by C3
  renaming. Do not turn an algebraic or Galois-semilinear resemblance into a pagewise topological
  isomorphism without a separately constructed normalizer action and exact orientation data.

PERIOD AND h1-TOWER RULES

- In the Q8-HFPSS, only multiplication by the permanent class `D^8` gives the unconditional
  period-object identity used by this project.
- `D`, `D^2`, and `D^4` may index repeated chart/differential patterns, but do not identify the
  corresponding HFPSS objects.
- `g=kD^3` is a forward HFPSS semiperiod: multiplication by `g^s`, `s>=0`, transports admitted
  families by Leibniz when the premises apply. Do not cancel or invert g in HFPSS. A bidirectional
  `(g,D^8)` lattice needs the recorded positive-filtration HFPSS-to-TateSS comparison certificate.
- A short drawn h1-tower is not evidence that the family is finite or confined to low filtration.
  A slope-one line is h1 multiplication, while the glyph/module declaration determines the
  algebraic object.
- With `j=v1^4 D^{-1}`, blue/red bo glyphs may represent formal-series modules such as
  `F4[[j]]` or `j F4[[j]]` (and any explicitly declared Witt/torsion refinement), not merely the
  finitely many dots drawn on screen.
- Keep module kind independent of periodic position. Distinguish at least
  `finite-2-primary`, `witt-2-adic`, and `j-adic-formal-power-series`.
- Store a formal-series family once, with its fixed differential/permanent-cycle templates. Do not
  eagerly enumerate infinitely many j-powers, and do not send it through the finite killed-rank
  audit. A formal-series vanishing claim is resolved only by an admitted fixed family whose
  recorded outcome is explicitly `killed`; no extra continuous/complete-module certificate is
  required merely because the module is a formal power series family.

WORKING DISCIPLINE

- Begin each task by naming the relevant fact IDs, sectors, source locations, and unresolved
  premises. Inspect the current files instead of trusting counts copied into this prompt.
- Preserve unrelated edits and never overwrite a newer Overleaf/local version blindly.
- Separate established results, conditional consequences, open obligations, and rejected branches.
- When changing mathematical records, update the prose ledger and machine ledger consistently,
  then run the focused audit/tests. Do not let code silently strengthen a mathematical status.
- End every task with: exact files changed; exact source locators used; facts admitted/reviewed/
  rejected; validation run; and remaining blockers. State “underdetermined” when the available
  premises do not prove completeness.
```

## Prompt B — first-run bootstrap on the new device

```text
Perform a read-first takeover audit under `E:\FenglinYu\HFPSS Q_8`. Do not begin by redesigning
the application and do not import old chat transcripts as project truth.

1. Discover the actual repository and reference layout with `rg --files`; do not assume that the
   migrated subdirectory names are unchanged.
2. At the HFPSS-Studio Git root, read in this order:
   - `RECORD.md` in full, especially Sections 0–2 and 10–11;
   - `.codex/CURRENT_STATE.md`, `AGENTS.md` if present, and only the newest 3–5 `.codex/logs`;
   - `REU Projects\Note\formal_notes.tex` and the relevant later corrections in
     `REU Projects\Note\record\note.tex`;
   - `DKLLW_Q8_FACT_CHAIN.md`, `DKLLW_F4_ARGUMENT_AUDIT.md`, and `ALGEBRA_ENGINE.md` only to the
     extent needed to understand the present trust boundary;
   - `backend\data\review\formal_notes_periodic_fate_ledger.v1.json`,
     `backend\domain\periodic_fate_ledger.py`, `backend\domain\dkllw_fact_chain.py`, and their
     focused tests.
3. Locate the migrated primary references, including [Bea17b]/Beaudry and the DKLLW/HHR/C4
   sources. Report missing files or ambiguous bibliography keys; do not guess citations.
4. Check Git status before editing. Treat existing changes as user-owned.
5. Recompute or run the current read-only fate audit rather than copying an old count.

Produce a compact takeover report with exactly these sections:

- Authoritative source map
- Admitted mathematical spine
- h1/formal-series interpretation
- Period identities versus pattern transport
- Current unresolved obligations
- Code surfaces that encode the mathematics
- Files or citations missing after migration
- Recommended next mathematical task

Keep the code introduction to one short paragraph: this is a Flask + vanilla-JS, JSON-backed,
proof-aware workbench with Computation and Review surfaces, synchronized backend/public static
assets, and focused Python tests. Explicitly state that frontend development is currently
non-priority. Do not copy a long feature history into the takeover report.

Do not modify mathematical status during this bootstrap. If a file must be normalized solely for
path portability, propose the exact minimal patch first and distinguish it from mathematical work.
```

## Prompt C — reusable prompt for the next mathematical computation

```text
Continue the Q8-HFPSS project in `E:\FenglinYu\HFPSS Q_8`.

Current objective:
    [INSERT ONE CONCRETE THEOREM, DIFFERENTIAL FAMILY, RESTRICTION MAP, OR VANISHING OBLIGATION]

Required sources:
    [INSERT LOCAL PAPERS / TEX SECTIONS / FIGURES]

Start from `RECORD.md` and the machine fate ledger. Identify the smallest dependency subgraph for
this objective; do not restate the whole project and do not revive rejected exploration. Check all
bidegrees, representation sectors, coefficients, module kinds, and period hypotheses explicitly.

For each proposed conclusion, return:

1. exact formula and page;
2. source and target bidegrees;
3. ordered basis/matrix when either cell has rank > 1;
4. premises and inference rule;
5. source locator;
6. whether the conclusion is admitted, admitted-pattern, verified-pattern, source-proved, review,
   blocked, or rejected;
7. which D^8, forward-g, pattern-only, or Tate-comparison translations are actually authorized.

If the conclusion is forced by a vanishing line, enumerate every possible source/target in the
relevant periodic fundamental domain and explain why all alternatives are excluded. If the data
remain incomplete, stop at a named obligation instead of choosing a visually plausible arrow.

Only after the mathematical result is settled should you update `RECORD.md` and the machine ledger.
Run the relevant audit and tests, but avoid frontend work unless it is necessary to expose or verify
the result.
```

## Prompt D — end-of-task compression and handoff

```text
Compress the completed work into a source-located handoff. Do not narrate abandoned attempts or
copy raw tool output.

Report only:

- New or changed admitted nodes and their premise edges
- Conditional/review nodes and the exact missing premise
- Superseded/rejected claims and the newer source that overrides them
- Period/module interpretation used, especially D^8 versus D/D^2/D^4 and finite versus j-adic
- Rank/matrix consequences for every multi-generator target
- Exact files changed and validation results
- One recommended next obligation

Update project memory only with those durable facts. Never record hidden reasoning. Keep frontend
details to a single sentence unless frontend behavior was the explicit task.
```

## Minimal inherited state (informative, not authoritative)

At the time these prompts were prepared, the local record treated the high-filtration audit as
underdetermined. It separately registered integer and sigma-i bo formal-series families; among five
finite-rank obligations, one was covered and four were still open. The named gaps included complete
E2-basis enumeration across the nine sectors, review of FN-2I-019, admission of FN-3I-010, and the
one-dimensional quotient left after the rank-one image `<A+B>` in a rank-two target. The new agent
must recompute this status after migration because the files may be newer than this note.

