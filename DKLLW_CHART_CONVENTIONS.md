# DKLLW chart conventions implemented by HFPSS Studio

This document records the display contract used by the Studio. It is a
presentation contract, not a replacement for the proposition graph or for a
proof of a differential.

## Published class glyphs

The published version of [DKLLW24], Table 11 uses:

| Glyph | Meaning |
| --- | --- |
| dot | \(k\) |
| fat dot | \(k[[j]]\) |
| circle | \(k[[j]]\{j\}\) |
| square | \(\mathbb W(k)\) |

Here \(k=\mathbb F_2\) for the \(SD_{16}\) and \(G_{48}\) charts, and
\(k=\mathbb F_4\) for the \(Q_8\) and \(G_{24}\) charts. The symbol \(j\)
depends on the chart: \(j=v_1^{12}D^{-3}\) for \(G_{24}\) and \(G_{48}\), and
\(j=v_1^4D^{-1}\) otherwise.

The arXiv source also contains an older blue/red-dot palette. The Studio may
retain those colors for compatible imports, but color is treated as a module
pattern. It must not be inferred from whether a class supports or receives a
differential.

## Published multiplication lines

The published version of [DKLLW24], Table 10 uses:

| Line | Meaning |
| --- | --- |
| vertical | multiplication by \(2\) |
| slope \(1\) | multiplication by \(h_1\) |
| slope \(1/3\) | multiplication by \(h_2\) |
| dashed (2BSS only) | hidden extension |

A vertical line may join two marks in the same spectral-sequence bidegree.
The small visual offset separates the marks; it is not a second filtration
coordinate. In particular, the upper mark is twice the lower generator.

Multiplication edges and differentials are separate record types. A slope
alone may provide a suggested display style, but the Studio stores the
multiplier explicitly and does not promote an arbitrary line to a theorem.

## Page and differential semantics

A class record stores its first page of appearance. A differential \(d_r\)
belongs to page \(E_r\). A chart can therefore show the \(E_2\) input together
with \(d_3\)-arrows whose homology is the \(E_3\) result. UI text must state
these roles separately instead of using one ambiguous page label.

Class glyph/module-pattern metadata is independent of class fate. Fate records
whether a class is live, supports a differential, receives a differential, or
survives; it controls page visibility and annotations but not the Table 11
glyph.

## Period cycles

A user may select a class live on \(E_r\) and record it as a period cycle on
that page. The display expands its translates virtually within the visible
viewport. It does not persist one class record per translated dot.

The same cycle is available as a period on earlier pages \(E_s\), \(s<r\).
It may continue to \(E_{r+1}\) only when it neither supports nor receives a
nonzero \(d_r\). This is a page-eligibility rule; it does not independently
prove that multiplication is an isomorphism or certify a claimed differential.

## Source locators

- [DKLLW24], published PDF, Tables 10 and 11 and Remarks 6.1--6.2.
- [DKLLW24], Figure 5 and Section 6.1.2 for the integer-graded \(Q_8\)-HFPSS
  and its stated \(D\)-periodicity.
- Local source archive: `arXiv-2209.01830v3/main.tex`.

