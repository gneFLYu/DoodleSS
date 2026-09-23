"""Build a directed, typed evidence multigraph from canonical project records."""
from __future__ import annotations

from .models import Project
from .fate import _cycle_premises_accepted, resolve_raw_coefficient_parameter


ADMITTED_PROPOSITION_STATUSES = frozenset({"established", "verified", "source-verified"})
NON_FACT_PROPOSITION_KINDS = frozenset({"tombstone"})
COEFFICIENT_HYPOTHESIS_PREFIX = "coefficient-context:"


def _proposition_state(project: Project) -> dict[str, dict]:
    propositions = {
        proposition.id: proposition
        for workspace in project.workspaces
        for proposition in workspace.propositions
    }
    depths: dict[str, int | None] = {}
    admitted: dict[str, bool] = {}

    def premises_for(proposition):
        values = proposition.premise_ids
        if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
            return None
        data = proposition.conclusion
        if "required_admitted_premises" in data and (
            data["required_admitted_premises"] is not True or not values
        ):
            return None
        return values

    def depth(ident: str, trail: frozenset[str] = frozenset()) -> int | None:
        if ident in depths:
            return depths[ident]
        if ident in trail:
            return None
        proposition = propositions[ident]
        premises = premises_for(proposition)
        if premises is None:
            depths[ident] = None
            return None
        premise_depths = [
            depth(premise, trail | {ident})
            for premise in premises
            if premise in propositions
        ]
        value = None if any(item is None for item in premise_depths) else 1 + max(premise_depths, default=-1)
        depths[ident] = value
        return value

    def is_admitted(ident: str, trail: frozenset[str] = frozenset()) -> bool:
        if ident in admitted:
            return admitted[ident]
        if ident in trail:
            return False
        proposition = propositions[ident]
        premises = premises_for(proposition)
        value = (
            proposition.status in ADMITTED_PROPOSITION_STATUSES
            and proposition.kind not in NON_FACT_PROPOSITION_KINDS
            and premises is not None
            and all(premise in propositions for premise in premises)
            and all(is_admitted(premise, trail | {ident}) for premise in premises)
        )
        data = proposition.conclusion
        parameter = data.get("coefficient_parameter")
        if value and (proposition.kind == "coefficient-proof"
                      or data.get("coefficient_proof_registration")
                      or isinstance(parameter, dict) and "proof_binding" in parameter):
            owners = [w for w in project.workspaces if any(p is proposition for p in w.propositions)]
            value = len(owners) == 1 and _cycle_premises_accepted(owners[0], proposition, project, strict=True)
            if value and proposition.kind != "coefficient-proof":
                registration = data.get("coefficient_proof_registration", {})
                value = (isinstance(parameter, dict) and "proof_binding" in parameter
                         and parameter.get("id") == registration.get("parameter_id", parameter.get("id"))
                         and resolve_raw_coefficient_parameter(owners[0], parameter["id"], project=project)["resolved"])
        admitted[ident] = value
        return value

    state: dict[str, dict] = {}
    for ident, proposition in propositions.items():
        premises = premises_for(proposition)
        missing = [premise for premise in premises or [] if premise not in propositions]
        blocked = [
            premise
            for premise in premises or []
            if premise in propositions and not is_admitted(premise)
        ]
        explicitly_verified = (
            proposition.status in ADMITTED_PROPOSITION_STATUSES
            and proposition.kind not in NON_FACT_PROPOSITION_KINDS
        )
        if proposition.status not in ADMITTED_PROPOSITION_STATUSES:
            blocked.insert(0, f"status:{proposition.status}")
        elif proposition.kind in NON_FACT_PROPOSITION_KINDS:
            blocked.insert(0, f"kind:{proposition.kind}")
        if premises is None:
            blocked.insert(0, "premises:invalid-or-required")
        state[ident] = {
            "admitted": is_admitted(ident),
            "explicitly_verified": explicitly_verified,
            "dependency_depth": depth(ident),
            "blocked_by": [*missing, *blocked],
        }
    return state


def admitted_proposition_ids(project: Project) -> set[str]:
    """Return the premise-complete Danus admission set."""
    return {ident for ident, state in _proposition_state(project).items() if state["admitted"]}


def build_logic_graph(project: Project) -> dict:
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

    for context in project.coefficient_contexts:
        add_node(
            f"coefficient-context:{context.id}",
            "coefficient-context",
            f"{context.coefficient_ring} (residue {context.residue_field})",
            record_id=context.id,
            status=context.scalar_mode,
            coefficient_ring=context.coefficient_ring,
            residue_field=context.residue_field,
            bockstein_stage=context.bockstein_stage,
        )

    proposition_state = _proposition_state(project)
    proposition_implications: dict[str, list[str]] = {}
    for workspace in project.workspaces:
        for proposition in workspace.propositions:
            for premise_id in proposition.premise_ids if isinstance(proposition.premise_ids, list) else []:
                if not isinstance(premise_id, str):
                    continue
                proposition_implications.setdefault(premise_id, []).append(proposition.id)
    proposition_locations: dict[str, str] = {}
    for workspace in project.workspaces:
        for proposition in workspace.propositions:
            prop_id = f"proposition:{proposition.id}"
            proposition_locations[proposition.id] = prop_id
            coefficient_context_ids = [
                item.removeprefix(COEFFICIENT_HYPOTHESIS_PREFIX)
                for item in proposition.hypotheses
                if item.startswith(COEFFICIENT_HYPOTHESIS_PREFIX)
            ]
            add_node(
                prop_id,
                "proposition",
                proposition.statement,
                record_id=proposition.id,
                workspace_id=workspace.id,
                status=proposition.status,
                rule=proposition.rule,
                conclusion=proposition.conclusion,
                notes=proposition.notes,
                hypotheses=proposition.hypotheses,
                verification_checks=proposition.verification_checks,
                reviewer=proposition.reviewer,
                reviewed_at=proposition.reviewed_at,
                coefficient_context_ids=coefficient_context_ids,
                implies_ids=proposition_implications.get(proposition.id, []),
                **proposition_state[proposition.id],
            )
            for source_ref in proposition.source_refs or ([proposition.source_ref] if proposition.source_ref else []):
                source_id = f"source:{source_ref}"
                add_node(source_id, "source-reference", source_ref, status="source-scoped")

    for workspace in project.workspaces:
        for proposition in workspace.propositions:
            prop_id = proposition_locations[proposition.id]
            for premise in proposition.premise_ids if isinstance(proposition.premise_ids, list) else []:
                if not isinstance(premise, str):
                    continue
                premise_id = proposition_locations.get(premise)
                if premise_id:
                    add_edge(premise_id, prop_id, "uses")
            for source_ref in proposition.source_refs or ([proposition.source_ref] if proposition.source_ref else []):
                add_edge(f"source:{source_ref}", prop_id, "supports")
            for hypothesis in proposition.hypotheses:
                if not hypothesis.startswith(COEFFICIENT_HYPOTHESIS_PREFIX):
                    continue
                context_id = hypothesis.removeprefix(COEFFICIENT_HYPOTHESIS_PREFIX)
                add_edge(f"coefficient-context:{context_id}", prop_id, "requires-coefficients")
            if proposition.supersedes_id:
                superseded = proposition_locations.get(proposition.supersedes_id)
                if superseded:
                    add_edge(prop_id, superseded, "supersedes")

        for cell in workspace.cells:
            cell_node_id = f"cell:{workspace.id}:{cell.id}"
            add_node(
                cell_node_id,
                "cell-vector-space",
                f"rank {len(cell.basis)} cell at ({cell.grade.stem},{cell.grade.filtration})",
                record_id=cell.id,
                workspace_id=workspace.id,
                status=cell.status,
                coefficient_context_id=cell.coefficient_context_id,
                computational_basis=[item.label for item in cell.basis],
                display_basis=[{"label": item.label, "coordinates": item.coordinates} for item in cell.display_basis],
                named_vectors=[{"label": item.label, "coordinates": item.coordinates} for item in cell.named_vectors],
                source_refs=cell.source_refs or ([cell.source_ref] if cell.source_ref else []),
            )
            add_edge(f"coefficient-context:{cell.coefficient_context_id}", cell_node_id, "defines-scalars")

        for linear_map in workspace.differential_maps:
            map_node_id = f"differential-map:{workspace.id}:{linear_map.id}"
            add_node(
                map_node_id,
                "differential-map",
                f"d_{linear_map.page} matrix {linear_map.source_cell_id or '0'} -> {linear_map.target_cell_id or '0'}",
                record_id=linear_map.id,
                workspace_id=workspace.id,
                status=linear_map.status,
                coverage=linear_map.coverage,
                matrix=linear_map.matrix,
                source_cell_id=linear_map.source_cell_id,
                target_cell_id=linear_map.target_cell_id,
                proposition_id=linear_map.proposition_id,
                source_refs=linear_map.source_refs or ([linear_map.source_ref] if linear_map.source_ref else []),
            )
            if linear_map.source_cell_id:
                add_edge(f"cell:{workspace.id}:{linear_map.source_cell_id}", map_node_id, "domain")
            if linear_map.target_cell_id:
                add_edge(map_node_id, f"cell:{workspace.id}:{linear_map.target_cell_id}", "codomain")
            proposition_id = proposition_locations.get(linear_map.proposition_id)
            if proposition_id:
                add_edge(proposition_id, map_node_id, "asserts-matrix")

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
        for workspace_item in project.workspaces:
            for proposition in workspace_item.propositions:
                if proposition.conclusion.get("period_family_id") == family.id:
                    add_edge(f"proposition:{proposition.id}", family_id, "belongs-to-period")
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

    admitted_count = sum(
        item["kind"] == "proposition" and item.get("admitted", False)
        for item in nodes
    )
    proposition_count = sum(item["kind"] == "proposition" for item in nodes)
    return {
        "nodes": nodes,
        "edges": edges,
        "admission": {
            "admitted": admitted_count,
            "review_queue": proposition_count - admitted_count,
            "policy": "Only established or verifier-marked propositions whose premises are admitted enter the fact DAG.",
        },
    }


def validate_logic_graph(graph: dict) -> list[str]:
    node_ids = [item["id"] for item in graph.get("nodes", [])]
    errors: list[str] = []
    if len(node_ids) != len(set(node_ids)):
        errors.append("Logic graph contains duplicate node IDs.")
    known = set(node_ids)
    for edge in graph.get("edges", []):
        if edge.get("source") not in known or edge.get("target") not in known:
            errors.append(f"Dangling {edge.get('kind', 'unknown')} edge.")
    node_lookup = {item["id"]: item for item in graph.get("nodes", [])}
    dependency_edges = [
        edge for edge in graph.get("edges", [])
        if edge.get("kind") == "uses"
        and str(edge.get("source", "")).startswith("proposition:")
        and str(edge.get("target", "")).startswith("proposition:")
    ]
    adjacency: dict[str, list[str]] = {}
    for edge in dependency_edges:
        adjacency.setdefault(edge["source"], []).append(edge["target"])
        source = node_lookup.get(edge["source"], {})
        target = node_lookup.get(edge["target"], {})
        if target.get("admitted") and not source.get("admitted"):
            errors.append("Admitted proposition depends on a proposition outside the admitted fact DAG.")

    visiting: set[str] = set()
    visited: set[str] = set()

    def has_cycle(ident: str) -> bool:
        if ident in visiting:
            return True
        if ident in visited:
            return False
        visiting.add(ident)
        cyclic = any(has_cycle(target) for target in adjacency.get(ident, []))
        visiting.remove(ident)
        visited.add(ident)
        return cyclic

    if any(has_cycle(ident) for ident in adjacency if ident not in visited):
        errors.append("Proposition dependencies must form a directed acyclic graph.")
    return errors
