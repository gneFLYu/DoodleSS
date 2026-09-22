# HFPSS Studio user guide

HFPSS Studio is a local-first, proof-aware workbench for the Q8 HFPSS. The chart is a
viewer/editor for source-backed records; a drawn line is never admitted as a theorem by
itself. Keep the source locator, proposition status, and premise chain with every change.

## Run and verify

From the repository root, start the Flask app with `python backend/app.py`, then open
`http://127.0.0.1:5078/`. Check `/api/health` before reviewing a chart. The Researching
surface edits chart records; Reviewing is read-only and exposes admissions, premises,
coefficients, cells, and matrix maps.

## Chart conventions

The E2 catalogue has exactly two presentation families: the oriented integer pattern and
the non-oriented `sigma_i` pattern. Internal `I..` and `S..` identifiers are module/basis
slots within those two families, not additional E2 patterns. The integer and even Thom
sectors use the oriented pattern; odd Thom sectors use the non-oriented pattern.

Glyphs encode module kind independently of fate: a dot is a finite class, rings denote
the declared `j`-adic families, and a double square denotes a `W(F4)[[j]]` 2-adic tower.
The unit anchor is periodic virtually by forward `g = kD^3` and by the permanent `D^8`
object period. Finite two-tower levels use the same rendered dot radius as ordinary dots.

Multiplication lines use the displayed bidegree shifts: `h_1` has shift `(1,1)`, `h_2`
has shift `(3,1)`, and a same-cell vertical line is multiplication by `2`. Because SVG
screen coordinates grow downward, a positive-filtration multiplication appears with a
negative visual slope.

## Evidence and editing rules

Use `RECORD.md`, the formal notes, the dated corrections, and the machine fate ledger in
that order. Keep `admitted`, `admitted-pattern`, `verified-pattern`, `source-proved`,
`review`, `blocked`, and `rejected` distinct. A review row may remain in the ledger as
provenance while a separately certified map is the only rendered arrow. D8 translations
and forward-`g` copies are not interchangeable with D, D2, or D4 pattern repetition, and
Tate comparison does not by itself authorize an HFPSS translation.

Before importing JSON, use the Preview step and inspect the source/status report. Run the
focused Python tests after changing a mathematical or rendering surface; update both
`backend/static` and `public/static` copies when a browser asset changes.

The safe import workflow is **Import JSON → Preview → Apply**. Legacy data can be
**Import into current page**, but imported connections and period rules remain
`candidate/manual-unverified` until a source-backed review admits them.
