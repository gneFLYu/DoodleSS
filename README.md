# HFPSS Studio

A local-first, proof-aware workbench for RO(G)-graded spectral sequences, beginning with the Q8 HFPSS for height-2 Morava E-theory at characteristic 2.

中文快速入门、完整交互工作流、来源导入与能力边界见 [HFPSS Studio 中文操作手册](USER_GUIDE.zh-CN.md)。

## What is usable now

- An interactive upper-half-plane chart: add classes, draw differentials, choose pages E2--E25 by default, add later pages from the page menu, and inspect class gradings.
- Wheel-zooming and middle-button panning with a buffered renderer. The x-axis cannot be moved into the upper half of the viewport, while stem and positive-filtration exploration are otherwise unbounded.
- Research-backed seed data distilled from the local `REU_Projects (1).zip` archive: integer, `(* - sigma_i)`, `(* - 2 sigma_i)`, `(* - 3 sigma_i)`, mixed, C4 reference, TateSS, and `(* - H)` workspaces.
- Provenance-aware propositions: each imported statement records its source file, rule, dependencies, confidence, and a research status (`established`, `derived`, `under-review`, or `superseded`).
- A proposition/dependency tree that can show either the active workspace or the full cross-workspace project graph.
- Explicit comparison records for orientation/Euler multiplication, C4 restriction, C4 transfer, and TateSS-to-H-periodicity.
- Conservative suggestion rules: `LeibnizRule`, a strong `VanishingLine` obligation, plus comparison transport for translation/restriction/transfer/norm/Tate records.
- A JSON-backed local project revision counter. This deliberately has no authentication or shared server yet.
- An explicit finite E2-presentation workflow: source-cited, typed integral generators and monic relations can be previewed, exactly rewritten, and materialized without inventing monomial dots or differentials. F4/Witt coefficients are deliberately rejected until their scalar algebra is implemented.
- A read-only structured algebra preview for registered generators: exact formal-integer and F4 polynomial arithmetic, bounded SymPy-backed integral expansion/collection, full RO(Q8) term grades, explicit rewrite provenance, and strict Witt/2-adic rejection.

The research seed is a structured index of the Overleaf archive, not a machine-checked transcription of every chart. In particular, the working log records corrected periodicities and draft sections that need review. The interface deliberately preserves these facts rather than presenting a draft differential as settled mathematics.

## Why these first rules

The project's sources use the integer-graded HFPSS as input and derive RO(Q8) shifts through orientability, the 2-Bockstein viewpoint, Leibniz rule, C4 restriction/transfer, and a strong vanishing line. The data model therefore keeps the RO(Q8) representation component separate from displayed stem/filtration, and stores every inference with provenance rather than treating a graphical arrow as proof.

## Run it

### Canonical latest application

There is one application to run and inspect:

```text
E:\课程\PACE2025_fly\HFPSS Q_8\DoodleSS\HFPSS-Studio
```

Run `run-latest.ps1` from that directory (or use the command below), then open **http://127.0.0.1:5078/**. The chart itself identifies the selected workspace and page in its header; that is the current live page, not a static export.

For a quick identity check, open **http://127.0.0.1:5078/api/health**. It reports `HFPSS Studio` and the current application version.

Do not use these as the latest application:

- `frontEnd_lty/sseq ver15.3.html` — interaction and visual reference only.
- `DoodleSS/app.py` — an earlier separate prototype.
- `tests/test_smoke.py` — automated checks only.

If the server was already open before an update, reload the browser with `Ctrl+F5` after restarting it.

From this directory:

```powershell
python -m pip install -r requirements.txt
python backend/app.py
```

Open `http://127.0.0.1:5078`.

To run the smoke checks:

```powershell
python -m unittest discover -s tests -v
```

### Vercel deployment

The repository now exposes `api/index.py` as Vercel's Flask/WSGI entry point.
`vercel.json` includes the `backend/` application bundle and the browser assets
are available under `public/static/`, so the deployed site uses the same routes
as the local launcher.

Install the Vercel CLI and run the following from this repository root:

```powershell
npm install --global vercel
vercel
vercel --prod
```

Use `vercel dev` to exercise the production entry point locally. Confirm a
deployment with `/api/health`.

The checked-in `backend/data/project.json` is the deployment seed. Vercel
Functions have no durable local disk, so deployed edits are stored only in the
warm function instance's temporary directory and can disappear after a restart
or be different across instances. Set `HFPSS_DATA_PATH` only when running
against a writable persistent volume outside Vercel; a shared production
workspace needs an external database or object store before edits can be
durable.

## Guides

- [Chinese operational user guide](USER_GUIDE.zh-CN.md): launch, chart controls, explicit E2-presentation dialog, read-only candidate enumeration, and capability limits.
- [Explicit E2-presentation JSON/API contract](E2_PRESENTATION_INPUT.md).
- [Safe structured algebra preview API](ALGEBRA_ENGINE.md): exact integer/F4 polynomial arithmetic, RO(Q8) grading, bounded SymPy expansion, and rewrite limits.
- [Full project and legacy ver15.3 JSON contract](PROJECT_JSON_IO.md): complete Studio projects, current-page lossy legacy import/export, staged Preview/Apply, validation, and history semantics.
- [DKLLW chart conventions](DKLLW_CHART_CONVENTIONS.md): class glyphs, multiplication lines, page roles, and period-cycle eligibility.
- Page-aware periods are compact `PagePeriodCycle` records. Viewport copies are virtual, and legacy materialized copies can be retired only through an ownership-checked preview/apply operation.
- [Safe workspace canvas clear API](CANVAS_CLEAR.md): archive active dots without deleting mathematics, with one-step undo.
- [Manual drawing periodicity contract](MANUAL_PERIODICITY.md): named vectors, batched chart copies, conflict handling, JSON provenance, and limits.

## Deliberate next increments

1. Import each verified TikZ/PDF chart coordinate system into the corresponding workspace, retaining a chart-specific grading convention.
2. Add typed map hypotheses for restriction, transfer, norm, and the C3 action; do not infer transport merely from a matching bidegree.
3. Add a review workflow so collaborators can attach a proof, accept a derived candidate, or supersede an outdated assertion.
4. Replace the JSON file with a collaborative service that has user identity, roles, review states, and revision conflict handling.

## Project layout

```text
backend/
  domain/models.py        # grades, charts, propositions, comparisons
  domain/proof_engine.py  # transparent rule suggestions
  domain/seed.py          # explicitly illustrative starting workspace
  app.py                  # Flask HTTP API and local persistence
  templates/ + static/    # no-build browser UI
run-latest.ps1            # canonical local launcher
tests/test_smoke.py
```

The experimental JSON/algebra CLI remains in the neighbouring
`DoodleSS/QuickDemo` folder. Its documented Windows entry point is
`quickdemo.ps1`; see `QuickDemo/README.md` for validation, bridge, Table 3,
and logic-tree commands.
