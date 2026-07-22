"""Build a directed, typed evidence multigraph from canonical project records."""
from __future__ import annotations

from .models import Project


def build_logic_graph(project: Project) -> dict[str, list[dict]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()
    edge_keys: set[tuple[str, str, str]] = set()

    def add_node(ident: str, kind: str, label: str, **metadata) -> None:
        if ident in node_ids:
            return
        node_ids.add(ident)
        nodes.append({"id": ident, "kind": kind, "label": label, **metadata})

    def add_edge(source: str, target: str, kind: str, **metadata) -> None:
        key = (source, target, kind)
        if source not in node_ids or target not in node_ids or key in edge_keys:
            return
        edge_keys.add(key)
        edges.append({"source": source, "target": target, "kind": kind, **metadata})

    proposition_locations: dict[str, str] = {}
    for workspace in project.workspaces:
        for proposition in workspace.propositions:
            prop_id = f"proposition:{proposition.id}"
            proposition_locations[proposition.id] = prop_id
            add_node(
                prop_id,
                "proposition",
                proposition.statement,
                record_id=proposition.id,
                workspace_id=workspace.id,
                status=proposition.status,
                rule=proposition.rule,
            )
            for source_ref in proposition.source_refs or ([proposition.source_ref] if proposition.source_ref else []):
                source_id = f"source:{source_ref}"
                add_node(source_id, "source-reference", source_ref, status="source-scoped")

    for workspace in project.workspaces:
        for proposition in workspace.propositions:
            prop_id = proposition_locations[proposition.id]
            for premise in proposition.premise_ids:
                premise_id = proposition_locations.get(premise)
                if premise_id:
                    add_edge(premise_id, prop_id, "uses")
            for source_ref in proposition.source_refs or ([proposition.source_ref] if proposition.source_ref else []):
                add_edge(f"source:{source_ref}", prop_id, "supports")
            if proposition.supersedes_id:
                superseded = proposition_locations.get(proposition.supersedes_id)
                if superseded:
                    add_edge(prop_id, superseded, "supersedes")

        for differential in workspace.differentials:
            claim_id = f"differential:{differential.id}"
            add_node(
                claim_id,
                "differential-claim",
                f"d_{differential.page}: {differential.source_id} -> {differential.target_id}",
                record_id=differential.id,
                workspace_id=workspace.id,
                status=differential.status,
            )
            proposition_id = proposition_locations.get(differential.proposition_id)
            if proposition_id:
                add_edge(proposition_id, claim_id, "asserts")

        for fate in workspace.fates:
            fate_id = f"fate:{workspace.id}:{fate.class_id}"
            add_node(
                fate_id,
                "class-fate",
                f"{fate.class_id}: {fate.conclusion}",
                record_id=fate.class_id,
                workspace_id=workspace.id,
                status=fate.conclusion,
            )
        for event in workspace.differential_events:
            event_id = f"event:{workspace.id}:{event.id}"
            add_node(
                event_id,
                "differential-event",
                f"{event.spectral_sequence} {event.role} d_{event.page}",
                record_id=event.id,
                workspace_id=workspace.id,
                status=event.status,
                comparison_status=event.comparison_status,
            )
            add_edge(event_id, f"fate:{workspace.id}:{event.class_id}", "updates")
            claim_id = f"differential:{event.differential_claim_id}"
            if claim_id in node_ids:
                add_edge(claim_id, event_id, "records")

    for family in project.period_families:
        family_id = f"period-family:{family.id}"
        add_node(
            family_id,
            "period-family",
            family.name,
            record_id=family.id,
            workspace_id=family.workspace_id,
            status=family.status,
        )
        certificate = proposition_locations.get(family.certificate_proposition_id)
        if certificate:
            add_edge(certificate, family_id, "certifies")
        workspace = next((item for item in project.workspaces if item.id == family.workspace_id), None)
        if workspace:
            for differential in workspace.differentials:
                if differential.period_family_id != family.id:
                    continue
                claim_id = f"differential:{differential.id}"
                add_edge(claim_id, family_id, "belongs-to")
                if differential.anchor_differential_id and differential.anchor_differential_id != differential.id:
                    add_edge(f"differential:{differential.anchor_differential_id}", claim_id, "transports")

    for sector in project.grading_sectors:
        add_node(
            f"sector:{sector.id}",
            "grading-sector",
            sector.display_label,
            record_id=sector.id,
            workspace_id=sector.workspace_id,
            status=sector.status,
        )
    for product in project.cross_graded_products:
        product_id = f"product:{product.id}"
        add_node(
            product_id,
            "cross-graded-product",
            product.resulting_expression,
            record_id=product.id,
            workspace_id=next(
                (item.workspace_id for item in project.grading_sectors if item.id == product.result_sector_id),
                None,
            ),
            status=product.status,
        )
        add_edge(product_id, f"sector:{product.result_sector_id}", "lands-in")
        proposition = proposition_locations.get(product.proposition_id)
        if proposition:
            add_edge(proposition, product_id, "asserts")

    for action in project.c3_actions:
        action_id = f"action:{action.id}"
        add_node(action_id, "c3-action", action.name, record_id=action.id, status=action.status)
        for sector in project.grading_sectors:
            add_edge(action_id, f"sector:{sector.id}", "tracks-orbit", orbit_id=sector.c3_orbit_id)

    return {"nodes": nodes, "edges": edges}


def validate_logic_graph(graph: dict[str, list[dict]]) -> list[str]:
    node_ids = [item["id"] for item in graph.get("nodes", [])]
    errors: list[str] = []
    if len(node_ids) != len(set(node_ids)):
        errors.append("Logic graph contains duplicate node IDs.")
    known = set(node_ids)
    for edge in graph.get("edges", []):
        if edge.get("source") not in known or edge.get("target") not in known:
            errors.append(f"Dangling {edge.get('kind', 'unknown')} edge.")
    return errors
