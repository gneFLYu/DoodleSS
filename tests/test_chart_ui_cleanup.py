"""Rendered HTML contracts for the compact, non-destructive chart controls."""
from html.parser import HTMLParser
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import app


class HtmlInventory(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        index = len(self.nodes)
        self.nodes.append({"tag": tag, "attrs": dict(attrs), "parents": tuple(self.stack), "text": ""})
        if tag not in self.VOID_TAGS:
            self.stack.append(index)

    def handle_endtag(self, tag):
        for position in range(len(self.stack) - 1, -1, -1):
            if self.nodes[self.stack[position]]["tag"] == tag:
                del self.stack[position:]
                return

    def handle_data(self, data):
        for index in self.stack:
            self.nodes[index]["text"] += data

    def by_id(self, element_id):
        matches = [node for node in self.nodes if node["attrs"].get("id") == element_id]
        assert len(matches) == 1, (element_id, len(matches))
        return matches[0]

    def inside(self, node, ancestor):
        return self.nodes.index(ancestor) in node["parents"]

    def summary(self, details):
        matches = [node for node in self.nodes if node["tag"] == "summary"
                   and self.inside(node, details)]
        assert len(matches) == 1
        return matches[0]


@pytest.fixture(scope="module")
def chart_html():
    response = app.test_client().get("/")
    assert response.status_code == 200
    return HtmlInventory(response.get_data(as_text=True))


def test_main_toolbar_keeps_drawing_history_import_export_and_fit(chart_html):
    more = chart_html.by_id("toolbar-more")
    assert more["tag"] == "details" and "open" not in more["attrs"]
    assert chart_html.summary(more)["text"].strip() == "More"
    for element_id in ("workspace-select", "page-select", "page-previous", "page-next",
                       "undo-action", "redo-action", "import-json", "export-json",
                       "export-legacy-json", "reset-view"):
        assert not chart_html.inside(chart_html.by_id(element_id), more)
    tools = [node for node in chart_html.nodes if "data-tool" in node["attrs"]]
    assert {node["attrs"]["data-tool"] for node in tools} == {
        "inspect", "class", "differential", "relation", "delete", "rename",
    }
    assert all(not chart_html.inside(node, more) for node in tools)


def test_advanced_actions_are_preserved_once_in_native_disclosure(chart_html):
    more = chart_html.by_id("toolbar-more")
    for element_id in ("new-workspace", "open-cell-editor", "open-e2-presentation",
                       "run-rules", "export-chart", "export-article",
                       "clear-current-canvas", "reset-demo"):
        button = chart_html.by_id(element_id)
        assert button["tag"] == "button" and chart_html.inside(button, more)
    groups = [node for node in chart_html.nodes if node["attrs"].get("role") == "group"
              and chart_html.inside(node, more)]
    assert len(groups) == 1 and groups[0]["attrs"]["aria-label"] == "Advanced chart actions"
    for element_id in ("cell-dialog", "matrix-dialog", "e2-presentation-dialog", "import-project-dialog"):
        assert chart_html.by_id(element_id)["tag"] == "dialog"


def test_removed_period_and_vanishing_controls_have_no_hidden_dom_stubs(chart_html):
    ids = {node["attrs"].get("id", "") for node in chart_html.nodes}
    assert "vanishing-line" not in ids and "page-period-tool" not in ids
    assert not any(element_id.startswith(("drawing-period", "drawing-diff-period",
                                        "preview-drawing-", "apply-drawing-", "add-drawing-"))
                   for element_id in ids)
    text = chart_html.nodes[0]["text"]
    for removed in ("4 × 4", "Strong vanishing line", "Period cycle on E", "Legacy Periodicity Tool"):
        assert removed not in text
    assert chart_html.by_id("grading-atlas")
    assert chart_html.by_id("certified-periodicity-details")["tag"] == "details"


def test_all_archived_canvases_stay_reachable_from_collapsed_reference(chart_html):
    archive = chart_html.by_id("legacy-catalog-reference")
    assert archive["tag"] == "details" and "open" not in archive["attrs"]
    assert "21 source canvases" in chart_html.summary(archive)["text"]
    assert any("support-workspaces" in chart_html.nodes[index]["attrs"].get("class", "").split()
               for index in archive["parents"])
    for element_id in ("legacy-catalog-select", "open-legacy-catalog", "close-legacy-catalog", "legacy-catalog-summary"):
        assert chart_html.inside(chart_html.by_id(element_id), archive)
    assert "hidden" not in chart_html.by_id("open-legacy-catalog")["attrs"]


def test_differential_count_is_the_disclosure_summary_not_a_separate_panel(chart_html):
    ledger = chart_html.by_id("published-table-ledger")
    summary = chart_html.summary(ledger)
    count = chart_html.by_id("shown-differential-count")
    assert summary["text"].strip() == "Show Differentials: 0"
    assert chart_html.inside(count, summary) and count["attrs"]["aria-live"] == "polite"
    assert "open" not in ledger["attrs"]
    assert len([node for node in chart_html.nodes if "data-table-ledger-content" in node["attrs"]]) == 1


def test_cleanup_preserves_separate_research_and_review_navigation(chart_html):
    chart_ids = [node["attrs"]["id"] for node in chart_html.nodes if "id" in node["attrs"]]
    assert len(chart_ids) == len(set(chart_ids))
    assert "chart" in chart_ids and "logic-graph" not in chart_ids
    response = app.test_client().get("/review")
    assert response.status_code == 200
    review = HtmlInventory(response.get_data(as_text=True))
    assert review.by_id("logic-graph")
    for page, active in ((chart_html, "Researching"), (review, "Reviewing")):
        links = [node for node in page.nodes if node["tag"] == "a" and node["attrs"].get("aria-current") == "page"]
        assert len(links) == 1 and links[0]["text"].strip() == active
