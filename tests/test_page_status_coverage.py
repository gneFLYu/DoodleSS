"""A later verified family is not the same thing as a complete later page."""
import pytest

from test_chart_display_conventions import app_helper


def status(page=24, change="", algebra="null"):
    return app_helper(["pageStatusText"], """(() => {
      const ws = {page: PAGE, settings: {known_page_max: 12},
        differentials: [{id: 'new', proposition_id: 'proof', page: 23, status: 'verified'}],
        propositions: [{id: 'proof', status: 'verified', conclusion: {
          admission_status: 'verified', verification_certificate: {status: 'verified'}}}]};
      CHANGE
      return pageStatusText(ws, ALGEBRA);
    })()""".replace("PAGE", str(page)).replace("CHANGE", change).replace("ALGEBRA", algebra))["result"]


@pytest.mark.parametrize("page", [12, 23, 24, 25])
def test_later_verified_family_updates_range_without_claiming_completion(page):
    text = status(page)
    assert f"Showing E{page}" in text and "through d23" in text
    assert "not a complete-page or convergence claim" in text
    assert "latest documented page" not in text


@pytest.mark.parametrize("change,algebra", [
    ("ws.differentials[0].status='review';", "null"),
    ("ws.propositions[0].status='review';", "null"),
    ("ws.propositions[0].conclusion.admission_status='review';", "null"),
    ("ws.propositions[0].conclusion.verification_certificate.status='review';", "null"),
    ("delete ws.propositions[0].conclusion.verification_certificate;", "null"),
    ("ws.differentials[0].page=NaN;", "null"),
    ("", "{canApply: () => false}"),
])
def test_unadmitted_later_claims_do_not_expand_reported_verified_range(change, algebra):
    assert status(change=change, algebra=algebra).startswith("E12 is the latest documented page")


def test_earlier_page_and_published_convergence_messages_remain_distinct():
    assert status(page=9) == "Showing E9; d9 is drawn only on this page."
    change = "ws.settings.convergence={status:'published-complete',stable_from_page:24};ws.settings.vanishing_line=24;"
    assert "E24 = E∞" in status(change=change)
    assert "current d23 is drawn before taking its quotient" in status(page=23, change=change)


def test_unknown_quotient_takes_precedence_over_later_family_coverage():
    algebra = "{conflicts:[{page:23,id:'map',reason:'unresolved coefficient'}],canApply:()=>true}"
    text = status(algebra=algebra)
    assert "partial / unknown quotient" in text and "unresolved coefficient" in text
    assert "through d23" not in text
