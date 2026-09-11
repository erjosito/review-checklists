"""Read-only adapter for the existing v2 recommendation corpus."""

import json
from pathlib import Path
from uuid import UUID

import yaml

from scripts.modules.cl_analyze_v2 import reco_matches_criteria


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
        document = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader),
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ReviewError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ReviewError(f"{path}: expected an object")
    return document


def load_corpus(root: Path) -> list[dict]:
    if not root.is_dir():
        raise ReviewError(f"Corpus directory does not exist: {root}")
    recommendations = []
    seen_ids = set()
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        reco = read_document(path)
        for field in ("name", "title"):
            if not isinstance(reco.get(field), str) or not reco[field].strip():
                raise ReviewError(f"{path}: missing or invalid {field}")
        if type(reco.get("severity")) is not int or reco["severity"] not in (0, 1, 2):
            raise ReviewError(f"{path}: severity must be 0 (high), 1 (medium), or 2 (low)")
        if "waf" in reco and not isinstance(reco["waf"], str):
            raise ReviewError(f"{path}: waf must be a string")
        if "description" in reco and not isinstance(reco["description"], str):
            raise ReviewError(f"{path}: description must be a string")
        for field in ("labels", "source", "queries"):
            if field in reco and not isinstance(reco[field], dict):
                raise ReviewError(f"{path}: {field} must be an object")
        if "type" in reco.get("source", {}) and not isinstance(reco["source"]["type"], str):
            raise ReviewError(f"{path}: source.type must be a string")
        if "links" in reco and (
            not isinstance(reco["links"], list)
            or not all(
                isinstance(link, dict) and isinstance(link.get("url"), str)
                for link in reco["links"]
            )
        ):
            raise ReviewError(f"{path}: links must contain objects with string URLs")
        for field in ("services", "resourceTypes"):
            if field in reco and (
                not isinstance(reco[field], list)
                or not all(isinstance(value, str) for value in reco[field])
            ):
                raise ReviewError(f"{path}: {field} must be a list of strings")
        query = reco.get("queries", {}).get("arg", "")
        if not isinstance(query, str):
            raise ReviewError(f"{path}: queries.arg must be a string")
        try:
            reco["id"] = str(UUID(reco.get("guid") or reco.get("labels", {}).get("guid", "")))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ReviewError(f"{path}: missing or invalid recommendation GUID") from exc
        if reco["id"] in seen_ids:
            raise ReviewError(f"{path}: duplicate recommendation GUID {reco['id']}")
        seen_ids.add(reco["id"])
        reco["corpus_file"] = path.relative_to(root).as_posix()
        recommendations.append(json.loads(json.dumps(reco, default=str)))
    if not recommendations:
        raise ReviewError(f"No recommendations found in {root}")
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


def select_checklist(recos: list[dict], checklist: dict) -> list[dict]:
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
    if not selected:
        raise ReviewError("Checklist selection matched no recommendations")
    return list(selected.values())
