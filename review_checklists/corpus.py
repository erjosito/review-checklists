"""Read-only adapter for the existing v2 recommendation corpus."""

from pathlib import Path

from scripts.modules.cl_analyze_v2 import reco_matches_criteria
from scripts.modules.cl_corpus import (
    CorpusError, enrich_recommendation, load_yaml_document, validate_corpus,
)


class ReviewError(Exception):
    """An actionable input or review-operation error."""


SELECTORS = {
    "nameSelector": "names",
    "guidSelector": "guids",
    "labelSelector": "labels",
    "serviceSelector": "services",
    "resourceTypeSelector": "resource_types",
    "wafSelector": "waf_pillars",
    "sourceSelector": "sources",
}


def has_arg_query(recommendation: dict) -> bool:
    return bool(recommendation.get("queries", {}).get("arg", "").strip())


def read_document(path: Path) -> dict:
    try:
        return load_yaml_document(path)
    except CorpusError as exc:
        raise ReviewError(f"Cannot read {path}: {exc}") from exc


def load_corpus(root: Path, *, require_current: bool = False) -> list[dict]:
    if not root.is_dir():
        raise ReviewError(f"Corpus directory does not exist: {root}")
    recommendations = []
    paths = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        reco = read_document(path)
        try:
            if "schemaVersion" not in reco:
                if require_current:
                    raise CorpusError("Missing schemaVersion; run 'corpus migrate' first")
                reco = enrich_recommendation(reco)
        except CorpusError as exc:
            raise ReviewError(f"{path}: {exc}") from exc
        paths.append(path.relative_to(root).as_posix())
        recommendations.append(reco)
    if not recommendations:
        raise ReviewError(f"No recommendations found in {root}")
    try:
        validate_corpus(recommendations)
    except CorpusError as exc:
        raise ReviewError(str(exc)) from exc
    for reco, path in zip(recommendations, paths, strict=True):
        reco["corpus_file"] = path
    return recommendations


def selector_arguments(block: dict) -> dict:
    if not isinstance(block, dict) or not block:
        raise ReviewError("A selector block must be a nonempty object")
    if unknown := block.keys() - SELECTORS.keys():
        raise ReviewError(f"Unsupported selectors: {', '.join(sorted(unknown))}")
    arguments = {}
    for key, value in block.items():
        if key == "labelSelector":
            if not isinstance(value, dict) or not value:
                raise ReviewError("labelSelector must be a nonempty object")
        elif not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ReviewError(f"{key} must be a nonempty list of strings")
        if key == "wafSelector":
            value = [item.lower() for item in value]
        arguments[SELECTORS[key]] = value
    return arguments


def select_checklist(recos: list[dict], checklist: dict, *, allow_empty: bool = False) -> list[dict]:
    """Union root/area/subarea selections using v2's selector matching semantics."""
    selected = {}

    def visit(node: dict, area: str = "", subarea: str = "") -> None:
        if not isinstance(node, dict):
            raise ReviewError("Checklist sections must be objects")
        include = selector_arguments(node["include"]) if "include" in node else None
        exclude = selector_arguments(node["exclude"]) if "exclude" in node else None
        if include is not None or exclude is not None:
            for reco in recos:
                if (include is None or reco_matches_criteria(reco, **include)) and (
                    exclude is None or not reco_matches_criteria(reco, **exclude)
                ):
                    selected[reco["id"]] = dict(reco, area=area, subarea=subarea)
        for key in ("areas", "subareas"):
            children = node.get(key, [])
            if not isinstance(children, list):
                raise ReviewError(f"{key} must be a list")
            for child in children:
                if not isinstance(child, dict) or not isinstance(child.get("name"), str):
                    raise ReviewError(f"Each {key} entry needs a name")
                visit(
                    child,
                    child["name"] if key == "areas" else area,
                    child["name"] if key == "subareas" else "",
                )

    visit(checklist)
    if not selected and not allow_empty:
        raise ReviewError("Checklist selection matched no recommendations")
    return list(selected.values())
