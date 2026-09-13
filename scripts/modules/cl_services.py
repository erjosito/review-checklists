"""Shared service catalogue without a false service-to-ARM-type bijection."""

from functools import lru_cache
import json
from pathlib import Path
import re


CATALOG_PATH = Path(__file__).resolve().parents[1] / "service_dictionary.json"
ARM_TYPE = re.compile(r"^[a-z][a-z0-9.]*\/[a-z0-9]+(?:\/[a-z0-9]+)*$", re.I)


def is_resource_type(value: str) -> bool:
    return bool(ARM_TYPE.fullmatch(value.strip()))


def normalize_resource_types(values: list[str]) -> list[str]:
    """Case/outer whitespace/order/duplicates only; never repair or infer a type."""
    return sorted({value.strip().casefold() for value in values})


@lru_cache(maxsize=1)
def service_dictionary() -> list[dict]:
    entries = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Service dictionary must be a list")
    aliases = {}
    for entry in entries:
        if not isinstance(entry, dict) or not all(
            isinstance(entry.get(key), str) and entry[key].strip()
            for key in ("service", "displayName")
        ) or not isinstance(entry.get("names"), list) or not entry["names"]:
            raise ValueError("Invalid service dictionary entry")
        names = entry["names"] + [entry["service"], entry["displayName"]]
        if not all(isinstance(name, str) and name.strip() for name in names):
            raise ValueError("Invalid service dictionary alias")
        types = entry.get("resourceTypes")
        if types is not None:
            if not isinstance(types, list) or not all(
                isinstance(t, str) and is_resource_type(t) and t == t.strip().casefold()
                for t in types
            ) or len(types) != len(set(types)):
                raise ValueError("Invalid service catalogue resourceTypes")
        inferred_types = entry.get("inferredResourceTypes")
        if inferred_types is not None:
            if (not isinstance(inferred_types, list) or types is None
                    or not all(isinstance(t, str) and t in types for t in inferred_types)
                    or len(inferred_types) != len(set(inferred_types))):
                raise ValueError("Inferred resource types must be a unique subset of resourceTypes")
        for name in names:
            if is_resource_type(name):
                continue
            key = name.strip().casefold()
            if key in aliases and aliases[key] != entry["displayName"]:
                raise ValueError(f"Ambiguous service alias: {name}")
            aliases[key] = entry["displayName"]
    return entries


@lru_cache(maxsize=1)
def _catalogue() -> tuple[dict, dict, dict, frozenset]:
    aliases, by_service, by_type, cross_cutting = {}, {}, {}, set()
    for entry in service_dictionary():
        display = entry["displayName"]
        for name in entry["names"] + [entry["service"], display]:
            if not is_resource_type(name):
                aliases[name.strip().casefold()] = display
        types = entry.get("resourceTypes")
        if types is None:
            types = [name for name in entry["names"] if is_resource_type(name)]
            if entry.get("arm"):
                types.append(entry["arm"])
        by_service.setdefault(display, set()).update(normalize_resource_types(types))
        for resource_type in entry.get("inferredResourceTypes", normalize_resource_types(types)):
            by_type.setdefault(resource_type, set()).add(display)
        if entry.get("applicability") == "cross-cutting":
            cross_cutting.add(display)
    return aliases, by_service, by_type, frozenset(cross_cutting)


def normalize_service_name(value: str) -> str:
    """Preserve unknown names visibly; technical values never imply curation."""
    value = value.strip()
    if is_resource_type(value):
        return value.casefold()
    return _catalogue()[0].get(value.casefold(), value)


def normalize_services(values: list[str]) -> list[str]:
    return sorted({normalize_service_name(value) for value in values}, key=str.casefold)


def resource_types_for_service(service: str) -> list[str]:
    return sorted(_catalogue()[1].get(normalize_service_name(service), ()))


def services_for_resource_type(resource_type: str) -> list[str]:
    """Type-based candidates, excluding capabilities that need extra configuration evidence."""
    return sorted(_catalogue()[2].get(resource_type.strip().casefold(), ()), key=str.casefold)


def service_catalogue() -> dict[str, list[str]]:
    """Aggregate duplicate legacy entries and all known many-to-many mappings."""
    return {name: sorted(types) for name, types in sorted(_catalogue()[1].items())}


def semantic_classification(recommendation: dict) -> dict:
    """Canonical sets for comparison, preserving missing versus explicitly empty."""
    return {
        field: normalizer(recommendation[field]) if field in recommendation else None
        for field, normalizer in (
            ("services", normalize_services), ("resourceTypes", normalize_resource_types)
        )
    }


def classifications_equivalent(before: dict, after: dict) -> bool:
    return semantic_classification(before) == semantic_classification(after)


def classify_applicability(recommendation: dict) -> dict:
    """Report gaps and possible contradictions; never rewrite service or type scope."""
    services = normalize_services(recommendation.get("services", []))
    types = normalize_resource_types(recommendation.get("resourceTypes", []))
    known = _catalogue()[1]
    candidates = {t: services_for_resource_type(t) for t in types}
    unknown = [s for s in services if s not in known]
    contradictions = []
    # An unmatched auxiliary type is not a contradiction: services can span resources.
    # Flag only services disjoint from the entire known declared resource scope.
    if types and all(candidates.values()):
        for service in services:
            applicable = set(resource_types_for_service(service))
            if applicable and not applicable.intersection(types) and service not in _catalogue()[3]:
                contradictions.append(service)
    return {
        "classification": "explicit" if services else "uncurated",
        "missingFields": [f for f in ("services", "resourceTypes") if f not in recommendation],
        "unknownServices": unknown,
        "unknownResourceTypes": [t for t, names in candidates.items() if not names],
        "ambiguousResourceTypes": {t: names for t, names in candidates.items() if len(names) > 1},
        "possibleContradictions": contradictions,
    }
