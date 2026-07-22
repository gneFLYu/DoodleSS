"""Cross-workspace products with explicit sector normalization evidence."""
from __future__ import annotations

from dataclasses import asdict

from .fate import class_is_live_on_page
from .grading import normalize_to_q8_sector
from .models import CrossGradedProduct, Project, Proposition, new_id


def _sector(project: Project, sector_id: str):
    sector = next((item for item in project.grading_sectors if item.id == sector_id), None)
    if not sector:
        raise ValueError(f"Unknown grading sector: {sector_id}")
    return sector


def _workspace(project: Project, workspace_id: str):
    return next(item for item in project.workspaces if item.id == workspace_id)


def preview_cross_graded_product(
    project: Project,
    left_sector_id: str,
    left_class_id: str,
    right_sector_id: str,
    right_class_id: str,
    page: int,
) -> dict:
    left_sector = _sector(project, left_sector_id)
    right_sector = _sector(project, right_sector_id)
    left_workspace = _workspace(project, left_sector.workspace_id)
    right_workspace = _workspace(project, right_sector.workspace_id)
    left = next((item for item in left_workspace.classes if item.id == left_class_id and not item.archived), None)
    right = next((item for item in right_workspace.classes if item.id == right_class_id and not item.archived), None)
    if not left or not right:
        raise ValueError("Both product inputs must be unarchived classes in their named sectors.")
    if page < max(left.page, right.page):
        raise ValueError("Both inputs must exist on the requested E_r page.")
    if not class_is_live_on_page(left_workspace, left.id, page) or not class_is_live_on_page(right_workspace, right.id, page):
        raise ValueError("Both product inputs must be live on the same E_r page.")
    if left.coefficient_context_id != right.coefficient_context_id:
        raise ValueError("Cross-graded products require a declared coefficient-context coercion.")

    raw_grade = left.grade.shifted(right.grade)
    normalized = normalize_to_q8_sector(project, raw_grade.representation)
    return {
        "left_workspace_id": left_workspace.id,
        "left_class_id": left.id,
        "right_workspace_id": right_workspace.id,
        "right_class_id": right.id,
        "page": page,
        "left_sector_id": left_sector_id,
        "right_sector_id": right_sector_id,
        "raw_representation_sum": raw_grade.representation,
        "result_sector_id": normalized.sector_id,
        "result_stem": raw_grade.stem,
        "result_filtration": raw_grade.filtration,
        "normalization_path": normalized.normalization_path,
        "normalization_status": normalized.status,
        "obligations": normalized.obligations,
        "resulting_expression": f"({left.expression})*({right.expression})",
        "coefficient_context_id": left.coefficient_context_id,
        "leibniz_sign_convention_id": left.convention_id,
    }


def create_cross_graded_product(project: Project, **arguments) -> CrossGradedProduct:
    preview = preview_cross_graded_product(project, **arguments)
    if preview["result_sector_id"] is None:
        raise ValueError("The raw representation sum cannot yet be normalized into the stored atlas.")
    proposition_id = new_id("prop")
    product = CrossGradedProduct(
        id=new_id("product"),
        left_workspace_id=preview["left_workspace_id"],
        left_class_id=preview["left_class_id"],
        right_workspace_id=preview["right_workspace_id"],
        right_class_id=preview["right_class_id"],
        page=preview["page"],
        left_sector_id=preview["left_sector_id"],
        right_sector_id=preview["right_sector_id"],
        raw_representation_sum=preview["raw_representation_sum"],
        result_sector_id=preview["result_sector_id"],
        result_stem=preview["result_stem"],
        result_filtration=preview["result_filtration"],
        normalization_path=preview["normalization_path"],
        resulting_expression=preview["resulting_expression"],
        coefficient_context_id=preview["coefficient_context_id"],
        leibniz_sign_convention_id=preview["leibniz_sign_convention_id"],
        proposition_id=proposition_id,
        status="candidate" if preview["normalization_status"] == "exact" else "unknown",
    )
    result_sector = _sector(project, product.result_sector_id)
    result_workspace = _workspace(project, result_sector.workspace_id)
    result_workspace.propositions.append(
        Proposition(
            id=proposition_id,
            kind="cross-graded-product",
            statement=(
                f"Product candidate on E_{product.page}: {product.resulting_expression} "
                f"lands in {result_sector.display_label}."
            ),
            status=product.status,
            conclusion={"product_id": product.id, "result_sector_id": product.result_sector_id},
            rule="CrossGradedProduct",
            confidence=0.6 if product.status == "candidate" else 0.2,
            hypotheses=list(preview["obligations"]),
            verification_checks=["same-page-liveness", "coefficient-context", "normalization", "LeibnizRule"],
            notes="Expressions, not rendered labels, are multiplied.",
        )
    )
    project.cross_graded_products.append(product)
    left_sector = _sector(project, product.left_sector_id)
    right_sector = _sector(project, product.right_sector_id)
    left_sector.products_out = list(dict.fromkeys(left_sector.products_out + [product.id]))
    right_sector.products_out = list(dict.fromkeys(right_sector.products_out + [product.id]))
    result_sector.products_in = list(dict.fromkeys(result_sector.products_in + [product.id]))
    return product


def product_to_dict(product: CrossGradedProduct) -> dict:
    return asdict(product)
