"""Compare equations with a transcription of tables, independently of glyphs."""
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from backend.domain.migrations import migrate_project
from backend.domain.published_differentials import JOURNAL_PROOFS, PUBLISHED_ARROWS
from backend.domain.published_products import derived_published_arrows
from backend.domain.seed import demo_project


FIXTURE = Path(__file__).parent / "fixtures" / "dkllw24_tables_8_9.tsv"


def test_printed_proof_preserves_the_journal_method_annotations():
    assert len(JOURNAL_PROOFS[8]) == 24 and len(JOURNAL_PROOFS[9]) == 22
    assert sum("(" in proof for proofs in JOURNAL_PROOFS.values() for proof in proofs) == 20
    assert JOURNAL_PROOFS[8][1] == "Corollary 4.15 (vanishing line) or Proposition 4.41 (restriction)"
    assert JOURNAL_PROOFS[8][2] == "Proposition 4.17 (8ν = η³)"
    assert JOURNAL_PROOFS[8][18] == "Proposition 4.18 (transfer)"
    assert JOURNAL_PROOFS[9][18] == "Proposition 5.20 (vanishing line or norm differential)"


def _printed_rows():
    result = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        table, row, stem, filtration, source, page, target = line.split("\t")
        result.append((int(table), int(row), int(stem), int(filtration), source, int(page), target))
    return result


def _normalise_display(value):
    value = re.sub(r"\s+", "", value)
    value = value.replace(r"\{", "(").replace(r"\}", ")")
    return re.sub(r"\^\{(-?\d+)\}", r"^\1", value)


def _expand_euler_alias(value):
    euler = r"a_{\sigma_i}"
    if value.startswith(euler):
        return "(x+y)" + value[len(euler):] + r"u_{\sigma_i}"
    return value


@pytest.mark.parametrize("printed", _printed_rows(), ids=lambda row: f"table{row[0]}-row{row[1]}")
def test_each_imported_row_matches_the_printed_equation(printed):
    table, ordinal, stem, filtration, source, page, target = printed
    workspace = "ws_integer" if table == 8 else "ws_sigma_i"
    rows = [row for row in PUBLISHED_ARROWS if row.workspace_id == workspace]
    actual = rows[ordinal - 1]
    assert (actual.source_stem, actual.source_filtration, actual.page) == (stem, filtration, page)
    assert _normalise_display(_expand_euler_alias(actual.source_label)) == _normalise_display(source)
    # The printed sigma d23 target omits u_sigma_i once. Restoring its
    # ambient representation grade is the only substantive transcription fix.
    if (table, ordinal) == (9, 21):
        target += r"u_{\sigma_i}"
    assert _normalise_display(actual.target_label) == _normalise_display(target)
    assert (actual.target_stem, actual.target_filtration) == (stem - 1, filtration + page)


def test_transcription_matches_actual_local_tex_when_available():
    tex_path = Path(__file__).resolve().parents[3] / "arXiv-2209.01830v3" / "main.tex"
    if not tex_path.exists():
        pytest.skip("The external arXiv source is optional; the checked-in table transcription remains tested.")
    tex = tex_path.read_text(encoding="utf-8")
    extracted = []
    for table, label in ((8, "integer"), (9, "sigmai")):
        start = tex.index(r"\label{table:HPFSS_" + label + "_diff}")
        body = tex[start:tex.index(r"\end{longtable}", start)]
        pattern = r"\$\((-?\d+),\s*(\d+)\)\$\s*&\s*\$([^$]+)\$\s*&\s*(\d+)\s*&\s*\$([^$]+)\$"
        rows = re.findall(pattern, body, re.S)
        assert len(rows) == (24 if table == 8 else 22)
        for ordinal, (stem, filtration, source, page, target) in enumerate(rows, 1):
            extracted.append((table, ordinal, int(stem), int(filtration), _normalise_display(source), int(page), _normalise_display(target)))
    fixture = [(t, r, s, f, _normalise_display(a), p, _normalise_display(b)) for t, r, s, f, a, p, b in _printed_rows()]
    assert extracted == fixture


def test_every_materialized_row_preserves_its_own_period_including_d7_d4_exception():
    project = migrate_project(demo_project())
    expected_periods = {
        8: [8, 16, 32, 32, 64] + [64] * 19,
        9: [8, 8, 16, 16] + [64] * 18,
    }
    seen = set()
    for workspace in project.workspaces:
        if workspace.id not in {"ws_integer", "ws_sigma_i"}:
            continue
        propositions = {item.id: item for item in workspace.propositions}
        for differential in workspace.differentials:
            if not differential.id.startswith("published_diff_"):
                continue
            metadata = propositions[differential.proposition_id].conclusion
            table, row = metadata["table_number"], metadata["table_row"]
            expected = expected_periods[table][row - 1]
            assert differential.period_stem == expected
            assert metadata["period_stem"] == expected
            assert metadata["period_is_invertible"] == (expected == 64)
            seen.add((table, row))
    assert seen == {(table, row) for table, rows in expected_periods.items() for row in range(1, len(rows) + 1)}
    # Shifting the D^4 d7 row by 32 would falsely kill D^8 and the unit.
    assert expected_periods[8][4] == 64
    assert (32 - 64) % 64 != 0 and (32 + 64) % 64 != 0


def test_secondary_d7_family_is_an_explicit_derivation_not_an_extra_printed_row():
    derived = next(item for item in derived_published_arrows() if item.key == "integer_d7_4D3")
    assert not any(row.source_label == derived.arrow.source_label and row.page == 7 for row in PUBLISHED_ARROWS)
    assert (derived.origin_table, derived.origin_row) == (8, 3)
    assert "hidden-2-extension" in derived.derivation
    assert "d5(D^3)=3g h2" in derived.derivation
    assert derived.source_two_valuation == 2
    assert derived.period_stem == 32


def _formal_pdf_page(page):
    """Read the user's journal PDF when installed; never require it in CI."""
    pdf = Path(__file__).resolve().parents[3] / "[Formal DKLLW] s42543-024-00087-7.pdf"
    if not pdf.exists():
        pytest.skip("The external formal DKLLW journal PDF is not installed.")
    command = shutil.which("pdftotext")
    if command is None:
        texlive = Path("C:/texlive/2025/bin/windows/pdftotext.exe")
        if texlive.is_file():
            command = str(texlive)
    if command is None:
        pytest.skip("pdftotext is not available; the independent TeX transcription is still checked.")
    completed = subprocess.run(
        [command, "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
        capture_output=True, text=True, encoding="utf-8", errors="strict", check=True,
        timeout=20,
    )
    return completed.stdout


@pytest.mark.parametrize("table,page", [(8, 39), (9, 49)])
def test_formal_journal_tables_preserve_every_row_grade_page_and_proof_locator(table, page):
    text = _formal_pdf_page(page)
    assert f"Table {table} HPFSS differentials" in text
    header = next(line for line in text.splitlines() if "(s, f )" in line)
    assert re.search(r"\(s, f \)\s+x\s+r\s+dr \(x\)\s+Proof", header)
    assert "period" not in header.lower()
    if table == 8:
        assert "integer page" in text
    else:
        assert "σi" in text

    # Superscripts and subscripts are reordered by PDF extraction. Compare
    # numerical bidegrees/pages and actual printed proof labels here; the
    # preceding TeX tests independently check complete symbolic equations.
    pattern = (
        r"^\s*\(([−-]?\d+),\s*(\d+)\)\s+(.+?)\s{2,}"
        r"(3|5|7|9|11|13|17|23)\s{2,}(.+?)\s{2,}"
        r"((?:Proposition|Corollary) .+?)\s*$"
    )
    extracted = re.findall(pattern, text, re.M)
    expected = [row for row in _printed_rows() if row[0] == table]
    assert len(extracted) == len(expected) == (24 if table == 8 else 22)
    actual_degrees = [(int(s.replace("−", "-")), int(f), int(r)) for s, f, _, r, _, _ in extracted]
    assert actual_degrees == [(s, f, r) for _, _, s, f, _, r, _ in expected]

    proofs = {
        8: [
            "Proposition 4.10", "Corollary 4.15", "Proposition 4.17", "Proposition 4.17",
            "Proposition 4.28", "Corollary 4.32", "Corollary 4.32", "Corollary 4.16",
            "Proposition 4.18", "Proposition 4.38", "Proposition 4.38", "Corollary 4.34",
            "Corollary 4.34", "Proposition 4.30", "Proposition 4.30", "Corollary 4.35",
            "Corollary 4.35", "Proposition 4.14", "Proposition 4.18", "Proposition 4.25",
            "Proposition 4.25", "Proposition 4.14", "Corollary 4.22", "Corollary 4.22",
        ],
        9: [
            "Proposition 5.8", "Proposition 5.1", "Corollary 5.3", "Corollary 5.5",
            "Proposition 5.11", "Proposition 5.11", "Proposition 5.12", "Proposition 5.12",
            "Corollary 5.13", "Corollary 5.13", "Proposition 5.15", "Proposition 5.15",
            "Proposition 5.19", "Proposition 5.19", "Proposition 5.19", "Proposition 5.19",
            "Corollary 5.10", "Corollary 5.10", "Proposition 5.20", "Proposition 5.14",
            "Proposition 5.17", "Proposition 5.17",
        ],
    }
    assert [re.match(r"(?:Proposition|Corollary) \d+\.\d+", proof).group(0) for *_, proof in extracted] == proofs[table]
    def normalise_proof(proof):
        return re.sub(r"\s+", "", proof).replace("³", "3")
    assert [normalise_proof(proof) for *_, proof in extracted] == [
        normalise_proof(proof) for proof in JOURNAL_PROOFS[table]
    ]
    if table == 8:
        # The journal proof column literally prints 8nu=eta^3 here. This
        # differs from the usual 2-primary 4nu=eta^3 convention; preserve it
        # as source evidence, never use that parenthesis as a rewrite rule.
        assert re.search(r"8ν\s*=\s*η3", extracted[2][-1])


def test_formal_journal_legend_distinguishes_series_and_witt_coefficients():
    text = _formal_pdf_page(50)
    assert "Table 10 Keys for" in text and "Table 11 Keys for classes" in text
    assert re.search(r"Vertical\s+2 multiplication", text)
    assert re.search(r"Slope 1\s+h\s*1 multiplication", text)
    assert re.search(r"Slope 1/3\s+h\s*2 multiplication", text)
    assert re.search(r"Dot\s+k\s*\n", text)
    assert re.search(r"Fat dot\s+k\[\[\s*j\]\]", text)
    assert re.search(r"Circle\s+k\[\[\s*j\]\]\{\s*j\}", text)
    assert re.search(r"Square\s+W\(k\)", text)
