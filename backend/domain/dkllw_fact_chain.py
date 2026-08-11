"""Source-backed dependency records for the DKLLW24 Q8 HFPSS computation."""

from __future__ import annotations

from .models import Project, Proposition


REVIEWED_AT = "2026-08-11"
COEFFICIENTS = ["coefficient-context:q8-witt-f4"]


def _conclusion(datum_type: str, spectral_sequence: str, **metadata) -> dict:
    return {"datum_type": datum_type, "spectral_sequence": spectral_sequence, **metadata}


def ensure_dkllw_fact_chain(project: Project) -> Project:
    """Install the principal source dependencies, not a formal proof transcript."""
    if project.id != "hfpss_studio":
        return project
    workspaces = {item.id: item for item in project.workspaces}
    if "ws_integer" not in workspaces or "ws_sigma_i" not in workspaces:
        return project
    known = {
        proposition.id
        for workspace in project.workspaces
        for proposition in workspace.propositions
    }

    def add(workspace_id: str, proposition: Proposition) -> None:
        if proposition.id not in known:
            workspaces[workspace_id].propositions.append(proposition)
            known.add(proposition.id)

    def fact(
        ident: str,
        kind: str,
        statement: str,
        conclusion: dict,
        premises: list[str],
        rule: str,
        source: str,
        notes: str,
        workspace_id: str = "ws_integer",
    ) -> None:
        add(workspace_id, Proposition(
            id=ident,
            kind=kind,
            statement=statement,
            status="established",
            conclusion=conclusion,
            premise_ids=premises,
            rule=rule,
            notes=notes,
            source_ref=source,
            source_refs=[source],
            hypotheses=COEFFICIENTS,
            verification_checks=[
                "Check the displayed source formula and page scope.",
                "Treat D^8-translates as one Q8 period family; do not merge D^4-separated anchors.",
            ],
            reviewer="Codex source-chain audit",
            reviewed_at=REVIEWED_AT,
        ))

    # 2-Bockstein input and output.  A 2-BSS survivor is only an HFPSS E2 input.
    fact(
        "prop_chain_2bss_int_d1", "differential",
        r"Integer 2-BSS: d1(v1^(2m+1))=2v1^(2m)h1, d1(Dx)=2h2^2, d1(x)=2y^2, d1(y)=2x^2.",
        _conclusion("differential", "2-BSS", page=1, scope="integer", formulas=[
            "d1(v1^(2m+1))=2v1^(2m)h1", "d1(Dx)=2h2^2", "d1(x)=2y^2", "d1(y)=2x^2",
        ]),
        ["prop_dkllw_bss_f4_to_witt"], "2-Bockstein",
        "DKLLW24 main.tex lines 965-1004, Table 1",
        "These differentials recover the first 2-adic extensions from the F4 E1-page.",
    )
    fact(
        "prop_chain_2bss_int_d2", "differential",
        r"Integer 2-BSS: d2(v1^2)=4h2.",
        _conclusion("differential", "2-BSS", page=2, scope="integer", formulas=["d2(v1^2)=4h2"]),
        ["prop_chain_2bss_int_d1"], "2-Bockstein",
        "DKLLW24 main.tex lines 999-1004, Table 1",
        "This is the source of the order-four h2 class in integral group cohomology.",
    )
    fact(
        "prop_chain_2bss_int_d3", "differential",
        r"Integer 2-BSS: d3(y h2^2)=8kD.",
        _conclusion("differential", "2-BSS", page=3, scope="integer", formulas=["d3(y h2^2)=8kD"]),
        ["prop_chain_2bss_int_d1", "prop_chain_2bss_int_d2"], "2-Bockstein",
        "DKLLW24 main.tex lines 999-1004, Table 1",
        "This records the order-eight k-family rather than reducing it modulo two.",
    )
    fact(
        "prop_chain_2bss_int_survivors", "permanent-cycle",
        r"The integer 2-BSS E-infinity generators are k, x^2, y^2, xh1, h1, h2, v1^2h1, D and v1^4 with the listed 8/2/2/2/2/4/2/infinite/infinite orders.",
        _conclusion("permanent-cycle", "2-BSS", scope="integer", role="HFPSS-E2-input", cycles=[
            "k:Z/8", "x^2:Z/2", "y^2:Z/2", "xh1:Z/2", "h1:Z/2",
            "h2:Z/4", "v1^2h1:Z/2", "D:torsion-free", "v1^4:torsion-free",
        ], period_identity="D-translates are the same 2-BSS/E2 chart family only; D is not an HFPSS permanent cycle."),
        ["prop_chain_2bss_int_d1", "prop_chain_2bss_int_d2", "prop_chain_2bss_int_d3"],
        "2-BSS E-infinity",
        "DKLLW24 main.tex lines 1007-1040, Tables 2-3",
        "Permanent here means surviving the auxiliary 2-BSS, not surviving the Q8 HFPSS.",
    )
    fact(
        "prop_chain_2bss_sigma_d1", "differential",
        r"(*-sigma_i) 2-BSS: d1(u_sigma_i)=2(x+y)u_sigma_i, with the remaining d1-pattern forced by Leibniz.",
        _conclusion("differential", "2-BSS", page=1, scope="*-sigma_i", formulas=[
            "d1(u_sigma_i)=2(x+y)u_sigma_i", "d1(xu_sigma_i)=2(x^2+y^2)u_sigma_i",
            "d1(v1u_sigma_i)=2(h1+xv1)u_sigma_i", "d1(h2u_sigma_i)=2(x+y)h2u_sigma_i",
        ]),
        ["prop_dkllw_bss_f4_to_witt"], "2-Bockstein+Leibniz",
        "DKLLW24 main.tex lines 1067-1168, Table 4",
        "Modulo two u_sigma_i orients the twist, but the integral d1 records the failure of integral orientation.",
        "ws_sigma_i",
    )
    fact(
        "prop_chain_2bss_sigma_d2", "differential",
        r"(*-sigma_i) 2-BSS: d2(xh1^2 u_sigma_i)=4kv1^2u_sigma_i.",
        _conclusion("differential", "2-BSS", page=2, scope="*-sigma_i", formulas=["d2(xh1^2u_sigma_i)=4kv1^2u_sigma_i"]),
        ["prop_chain_2bss_sigma_d1"], "2-Bockstein",
        "DKLLW24 main.tex lines 1119-1168, Table 4",
        "Forced by H^4(Q8,pi4(E2) tensor sigma_i)=W/4.",
        "ws_sigma_i",
    )
    fact(
        "prop_chain_2bss_sigma_survivors", "permanent-cycle",
        r"The (*-sigma_i) 2-BSS E-infinity module generators are (x^2+y^2)u_sigma_i, (x+y)u_sigma_i, (h1+xv1)u_sigma_i and v1^2u_sigma_i.",
        _conclusion("permanent-cycle", "2-BSS", scope="*-sigma_i", role="HFPSS-E2-input", cycles=[
            "(x^2+y^2)u_sigma_i:Z/2", "(x+y)u_sigma_i:Z/2",
            "(h1+xv1)u_sigma_i:Z/2", "v1^2u_sigma_i:torsion-free",
        ], period_identity="D-translates are the same E2 chart family; HFPSS fates are decided later."),
        ["prop_chain_2bss_sigma_d1", "prop_chain_2bss_sigma_d2"], "2-BSS E-infinity",
        "DKLLW24 main.tex lines 1171-1215, Tables 5-6",
        "These four names are the object identities used on the later (*-sigma_i) HFPSS pages.",
        "ws_sigma_i",
    )

    # Lower-subgroup HFPSS input.
    fact(
        "prop_chain_c2_hurewicz_pc", "permanent-cycle",
        r"The C2-HFPSS Hurewicz images detecting eta, nu and bar-kappa are permanent cycles.",
        _conclusion("permanent-cycle", "C2-HFPSS", cycles=["h1 detects eta", "h2 detects nu", "g detects bar-kappa"]),
        ["prop_dkllw_coeff_witt"], "C2-Hurewicz detection",
        "DKLLW24 main.tex lines 1327-1342; LSWX19 Theorem 1.8",
        "Nonzero C2 restrictions imply the corresponding Q8 Hurewicz images cannot vanish.",
    )
    fact(
        "prop_chain_c4_periodic_pc", "permanent-cycle",
        r"C4-HFPSS: Delta1^4, u8lambda, u4sigma and u4lambda*u2sigma give the stated permanent periodicity classes.",
        _conclusion("permanent-cycle", "C4-HFPSS", cycles=["Delta1^4:(32,0)", "u8lambda", "u4sigma", "u4lambda*u2sigma"]),
        ["prop_dkllw_coeff_witt"], "C4 periodicity",
        "DKLLW24 main.tex lines 821-831 and 1529-1533",
        "Their norms supply genuine RO(Q8) periodicity; the 32-period C4 class does not make D^4 a Q8 period.",
    )
    fact(
        "prop_chain_c4_d3", "differential",
        r"C4-HFPSS: d3(T2)=nonzero and d3(T2^3)=T2^2 eta^3.",
        _conclusion("differential", "C4-HFPSS", page=3, formulas=["d3(T2) != 0", "d3(T2^3)=T2^2 eta^3"]),
        ["prop_chain_c4_periodic_pc"], "Restriction+naturality",
        "DKLLW24 main.tex lines 1358-1369 and 1941-1955; BBHS20 Proposition 5.21",
        "The T2 formula restricts to the sigma_i d3; the T2^3 formula restricts to the integer d3.",
    )
    fact(
        "prop_chain_c4_d5_delta", "differential",
        r"C4-HFPSS: Delta1 supports a nonzero d5.",
        _conclusion("differential", "C4-HFPSS", page=5, formulas=["d5(Delta1) != 0"]),
        ["prop_chain_c4_periodic_pc"], "C4 computation",
        "DKLLW24 main.tex lines 1810-1821; BBHS20 Proposition 5.24",
        "Since Res(D)=Delta1 up to a Witt unit, this bounds and then determines the Q8 d5 on D.",
    )
    fact(
        "prop_chain_c4_d5_norm", "differential",
        r"C4-HFPSS: d5(u2lambda)=delta1*u_lambda*a_2lambda*a_sigma.",
        _conclusion("differential", "C4-HFPSS", page=5, formulas=["d5(u2lambda)=delta1*u_lambda*a_2lambda*a_sigma"]),
        ["prop_chain_c4_periodic_pc"], "Slice differential theorem",
        "DKLLW24 main.tex lines 2281-2295; HHR17 Theorem 11.13",
        "The norm theorem predicts the independent Q8 (*-sigma_i) d9 family.",
    )
    fact(
        "prop_chain_c4_d7_norm", "differential",
        r"C4-HFPSS: d7(u4lambda)=delta1*eta'*u2lambda*a_3lambda.",
        _conclusion("differential", "C4-HFPSS", page=7, formulas=["d7(u4lambda)=delta1*eta'*u2lambda*a_3lambda"]),
        ["prop_chain_c4_periodic_pc"], "Slice differential theorem",
        "DKLLW24 main.tex lines 2380-2395; HHR17 Theorem 11.13",
        "The norm theorem predicts the Q8 (*-sigma_i) d13 family.",
    )
    fact(
        "prop_chain_c4_hidden_2", "extension",
        r"C4-HFPSS has the stem-22 exotic restriction/transfer hidden 2-extension used in Q8.",
        _conclusion("auxiliary", "C4-HFPSS", relation="hidden-2-extension"),
        ["prop_chain_c4_periodic_pc"], "Exotic restriction+transfer",
        "DKLLW24 main.tex lines 755-809, Lemma 2.11",
        "This is an auxiliary implication edge, not itself an HFPSS differential or permanent-cycle claim.",
    )

    # Structural Q8 permanent-cycle facts.
    fact(
        "prop_chain_q8_D8_pc", "permanent-cycle",
        r"D^8 is an invertible Q8-HFPSS permanent cycle giving 64-periodicity.",
        _conclusion("permanent-cycle", "Q8-HFPSS", cycle="D^8", period_family_id="period_integer_D8", period_identity="x and D^(8n)x are one Q8 period object"),
        ["prop_chain_c4_periodic_pc", "prop_dkllw_unit_ambiguity"], "Norm periodicity",
        "DKLLW24 main.tex lines 1236-1253, Proposition 4.1",
        "Only the unit multiple is unspecified. D^4 is not identified with 1 in this period family.",
    )
    fact(
        "prop_chain_q8_hurewicz_pc", "permanent-cycle",
        r"h1, h2 and g=kD^3 are Q8-HFPSS permanent cycles.",
        _conclusion("permanent-cycle", "Q8-HFPSS", cycles=["h1", "h2", "g=kD^3"], period_family_id="period_integer_D8"),
        ["prop_chain_c2_hurewicz_pc", "prop_chain_2bss_int_survivors"], "Restriction to C2",
        "DKLLW24 main.tex lines 1327-1342, Lemma 4.7",
        "These permanent cycles transport differentials by Leibniz; g also gives the chart's (20,4) repetition away from low v1-local classes.",
    )
    fact(
        "prop_chain_q8_usigma_pc", "permanent-cycle",
        r"(x+y)u_sigma_i=a_sigma_i is a Q8-HFPSS permanent cycle.",
        _conclusion("permanent-cycle", "Q8-HFPSS", cycle="(x+y)u_sigma_i=a_sigma_i", period_family_id="period_sigma_D8"),
        ["prop_chain_2bss_sigma_survivors"], "Euler-class permanence",
        "DKLLW24 main.tex lines 1972-1977, Lemma 5.2",
        "This exact object identity is by bidegree; its D^(8n)-translates are the same 64-period family.",
        "ws_sigma_i",
    )
    fact(
        "prop_chain_q8_x2y2D_pc", "permanent-cycle",
        r"(x^2+y^2)D u_sigma_i is a Q8-HFPSS permanent cycle.",
        _conclusion("permanent-cycle", "Q8-HFPSS", cycle="(x^2+y^2)D u_sigma_i", period_family_id="period_sigma_D8"),
        ["prop_chain_q8_usigma_pc", "prop_chain_q8_hurewicz_pc", "prop_chain_q8_d9_D2h1"], "Tate target exclusion",
        "DKLLW24 main.tex lines 1993-2007, Lemma 5.4",
        "The proof identifies its D^8-translates, not the D^4-shifted class, as the same period object.",
        "ws_sigma_i",
    )

    # Integer Q8 HFPSS generator facts.  Each statement includes every source-level sibling anchor.
    integer_facts = [
        ("prop_chain_q8_d3", "differential", r"d3(D^(8n)v1^6)=D^(8n)v1^4h1^3.", ["prop_chain_c4_d3", "prop_chain_2bss_int_survivors", "prop_chain_q8_D8_pc"], "Restriction", "DKLLW24 main.tex lines 1358-1369, Proposition 4.8", ["d3(D^(8n)v1^6)=D^(8n)v1^4h1^3"]),
        ("prop_chain_q8_bo_pc", "permanent-cycle", r"The integer bo-pattern D^m v1^(4l), its h1/h1^2 multiples, and 2D^m v1^(4l+2) survive the Q8 HFPSS.", ["prop_chain_q8_d3", "prop_chain_q8_hurewicz_pc"], "Tate method+norm", "DKLLW24 main.tex lines 1390-1432, Proposition 4.9", ["D^m v1^(4l)", "D^m v1^(4l)h1", "D^m v1^(4l)h1^2", "2D^m v1^(4l+2)"]),
        ("prop_chain_q8_d5_D", "differential", r"d5(D^(8n+1))=D^(8n-2)gh2.", ["prop_chain_c4_d5_delta", "prop_chain_q8_hurewicz_pc", "prop_chain_q8_D8_pc"], "Restriction", "DKLLW24 main.tex lines 1459-1494 and 1810-1821, Proposition 4.11", ["d5(D^(8n+1))=D^(8n-2)gh2"]),
        ("prop_chain_q8_d7", "differential", r"d7(4D^(8n+1))=D^(8n-2)gh1^3; d7(2D^(8n+2))=D^(8n-1)gh1^3; d7(D^(8n+4))=D^(8n+1)gh1^3.", ["prop_chain_q8_d5_D", "prop_chain_q8_hurewicz_pc", "prop_chain_q8_pc_Dh13", "prop_chain_q8_D8_pc"], "Hidden 2+vanishing line", "DKLLW24 main.tex lines 1512-1527 and 1617-1637, Propositions 4.13 and 4.23", ["d7(4D^(8n+1))", "d7(2D^(8n+2))", "d7(D^(8n+4))"]),
        ("prop_chain_q8_d9_Dh1", "differential", r"d9(D^(8n+1)h1)=D^(8n-5)g^2c and d9(D^(8n+5)h1)=D^(8n-1)g^2c.", ["prop_chain_q8_pc_D3dh1", "prop_chain_q8_d11", "prop_chain_q8_D8_pc"], "Contradiction+Leibniz", "DKLLW24 main.tex lines 1674-1692, Corollary 4.27", ["d9(D^(8n+1)h1)", "d9(D^(8n+5)h1)"]),
        ("prop_chain_q8_d9_c", "differential", r"The Dc/D^5c and D^2c/D^6c families support the four d9 differentials in Table 8.", ["prop_chain_q8_d13", "prop_chain_q8_D8_pc"], "Hidden h1+degree exclusion", "DKLLW24 main.tex lines 1499-1510, 1536-1571 and 1694-1713", ["d9(Dc)", "d9(D^5c)", "d9(D^2c)", "d9(D^6c)"]),
        ("prop_chain_q8_d11", "differential", r"D^2d, D^6d, Ddh1 and D^5dh1 support the four d11 differentials in Table 8.", ["prop_chain_c4_periodic_pc", "prop_chain_q8_pc_D3dh1", "prop_chain_q8_D8_pc"], "Restriction+Leibniz", "DKLLW24 main.tex lines 1644-1672 and 1717-1727", ["d11(D^2d)", "d11(D^6d)", "d11(Ddh1)", "d11(D^5dh1)"]),
        ("prop_chain_q8_d13", "differential", r"Dch1, D^5ch1, 2Dh2 and 2D^5h2 support the four d13 differentials in Table 8.", ["prop_chain_c4_hidden_2", "prop_chain_q8_d5_D", "prop_chain_q8_hurewicz_pc", "prop_chain_q8_D8_pc"], "Vanishing/transfer+hidden 2", "DKLLW24 main.tex lines 1438-1457, 1536-1571 and 1580-1607", ["d13(Dch1)", "d13(D^5ch1)", "d13(2Dh2)", "d13(2D^5h2)"]),
        ("prop_chain_q8_d23", "differential", r"D^(-1)h1, D^2h1^2 and D^5h1^3 support the three d23 differentials in Table 8.", ["prop_chain_q8_pc_D3h1", "prop_chain_q8_D8_pc"], "Vanishing line+Leibniz", "DKLLW24 main.tex lines 1438-1457 and 1544-1555", ["d23(D^(-1)h1)", "d23(D^2h1^2)", "d23(D^5h1^3)"]),
        ("prop_chain_q8_pc_D3h1", "permanent-cycle", r"D^3h1 is a Q8-HFPSS permanent cycle.", ["prop_chain_q8_d9_c", "prop_chain_q8_hurewicz_pc"], "Target exclusion", "DKLLW24 main.tex lines 1574-1588, Lemma 4.19", ["D^3h1"]),
        ("prop_chain_q8_pc_Dh13", "permanent-cycle", r"Dh1^3 is a Q8-HFPSS permanent cycle.", ["prop_chain_q8_d13", "prop_chain_q8_d23"], "Target exclusion", "DKLLW24 main.tex lines 1609-1617, Lemma 4.22", ["Dh1^3"]),
        ("prop_chain_q8_pc_D3dh1", "permanent-cycle", r"D^3dh1 is a Q8-HFPSS permanent cycle.", ["prop_chain_q8_d9_c"], "Tate method", "DKLLW24 main.tex lines 1639-1642, Lemma 4.24", ["D^3dh1"]),
        ("prop_chain_q8_pc_d", "permanent-cycle", r"d=D^2x^2 is a Q8-HFPSS permanent cycle.", ["prop_chain_q8_d13", "prop_chain_q8_hurewicz_pc"], "Tate method/Hurewicz", "DKLLW24 main.tex lines 1734-1743, Lemma 4.31", ["d=D^2x^2"]),
        ("prop_chain_q8_d9_D2h1", "differential", r"d9(D^(8n+2)h1)=D^(8n-4)g^2c and d9(D^(8n+6)h1)=D^(8n)g^2c.", ["prop_chain_q8_pc_d", "prop_chain_q8_d9_Dh1", "prop_chain_q8_D8_pc"], "Contradiction", "DKLLW24 main.tex lines 1744-1754, Proposition 4.32", ["d9(D^(8n+2)h1)", "d9(D^(8n+6)h1)"]),
    ]
    for ident, kind, statement, premises, rule, source, formulas in integer_facts:
        datum_type = "differential" if kind == "differential" else "permanent-cycle"
        fact(
            ident, kind, statement,
            _conclusion(datum_type, "Q8-HFPSS", formulas=formulas, period_family_id="period_integer_D8", period_identity="D^8-translates are one object; D^4-separated anchors remain distinct"),
            premises, rule, source,
            "The listed formulas are generator facts; all other displayed copies require permanent multipliers and Leibniz.",
        )

    # (*-sigma_i) Q8 HFPSS generator facts.
    sigma_facts = [
        ("prop_chain_sigma_d3", r"v1^2u_sigma_i and (h1+xv1)u_sigma_i support the two d3 generator families.", ["prop_chain_c4_d3", "prop_chain_2bss_sigma_survivors"], "Restriction/2-BSS extensions", "DKLLW24 main.tex lines 1941-1955 and 2045-2078", ["d3(v1^2u_sigma_i)", "d3((h1+xv1)u_sigma_i)"]),
        ("prop_chain_sigma_d5", r"(x+y)Du_sigma_i and (x^2+y^2)D^2u_sigma_i support the two d5 generator families.", ["prop_chain_q8_d5_D", "prop_chain_q8_usigma_pc", "prop_chain_q8_x2y2D_pc"], "Module structure", "DKLLW24 main.tex lines 1980-2014", ["d5((x+y)Du_sigma_i)", "d5((x^2+y^2)D^2u_sigma_i)"]),
        ("prop_chain_sigma_d9", r"The eight d9 rows of Table 9 follow from Tate forcing, integer module structure, hidden 2-extensions, and one independent C4 norm differential.", ["prop_chain_c4_d5_norm", "prop_chain_q8_d9_Dh1", "prop_chain_q8_d9_D2h1", "prop_chain_q8_usigma_pc", "prop_chain_q8_x2y2D_pc"], "Tate/module/norm", "DKLLW24 main.tex lines 2110-2300, Propositions 5.10-5.17", ["Table 9 d9 rows"]),
        ("prop_chain_sigma_pc_hcombo", r"(h1^2+xh1v1)D^r u_sigma_i is permanent for r=2,3,6,7.", ["prop_chain_sigma_d9", "prop_chain_q8_d23", "prop_chain_q8_d11"], "Target exclusion", "DKLLW24 main.tex lines 2324-2329, Lemma 5.19", ["r=2", "r=3", "r=6", "r=7"]),
        ("prop_chain_sigma_d11", r"The six d11 rows of Table 9 follow from vanishing-line forcing and module structure.", ["prop_chain_sigma_pc_hcombo", "prop_chain_sigma_d9", "prop_chain_q8_D8_pc"], "Vanishing line+module", "DKLLW24 main.tex lines 2088-2106 and 2331-2362", ["Table 9 d11 rows"]),
        ("prop_chain_sigma_d13", r"d13((x+y)D^4u_sigma_i)=k^3(h1^2+xh1v1)D^5u_sigma_i.", ["prop_chain_c4_d7_norm", "prop_chain_sigma_pc_hcombo", "prop_chain_sigma_d9"], "Vanishing line/norm", "DKLLW24 main.tex lines 2365-2397, Proposition 5.21", ["d13((x+y)D^4u_sigma_i)"]),
        ("prop_chain_sigma_d17", r"d17((h1^2+xh1v1)u_sigma_i)=k^4(x+y)h1^2D^2u_sigma_i.", ["prop_chain_q8_d23", "prop_chain_q8_usigma_pc", "prop_chain_q8_D8_pc"], "Vanishing line", "DKLLW24 main.tex lines 2164-2221, Proposition 5.14", ["d17((h1^2+xh1v1)u_sigma_i)"]),
        ("prop_chain_sigma_d23", r"The two d23 rows of Table 9 are integer d23 differentials multiplied by the permanent a_sigma_i class.", ["prop_chain_q8_d23", "prop_chain_q8_usigma_pc"], "Module structure", "DKLLW24 main.tex lines 2304-2321, Proposition 5.18", ["Table 9 d23 rows"]),
    ]
    for ident, statement, premises, rule, source, formulas in sigma_facts:
        fact(
            ident, "differential" if "_pc_" not in ident else "permanent-cycle", statement,
            _conclusion("permanent-cycle" if "_pc_" in ident else "differential", "Q8-HFPSS", formulas=formulas, period_family_id="period_sigma_D8", period_identity="D^8-translates are one object; D^4-separated anchors remain distinct"),
            premises, rule, source,
            "This is a generator datum in the single-sigma_i tower; it asserts no transport to arbitrary mixed RO(Q8) gradings.",
            "ws_sigma_i",
        )
    return project
