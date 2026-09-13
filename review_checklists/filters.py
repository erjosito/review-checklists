"""Review filters derived from pinned recommendation metadata."""

from collections.abc import Callable, Sequence
from functools import lru_cache
from scripts.modules import cl_services

from review_checklists.corpus import ReviewError, has_arg_query


SEVERITIES = {"high": 0, "medium": 1, "low": 2}
WAF_PILLARS = {
    "security": "Security",
    "performance": "Performance",
    "reliability": "Reliability",
    "cost": "Cost",
    "operations": "Operations",
    "none": "Not specified",
}
MULTI_FILTERS = ("status", "severity", "waf", "service")
FilterValue = str | Sequence[str]


def filter_values(
    value: FilterValue, normalize: Callable[[str], str] = str.strip,
) -> tuple[str, ...]:
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, Sequence) or not all(isinstance(item, str) for item in values):
        raise ReviewError("Filter values must be text or a list of text values")
    return tuple(dict.fromkeys(normalize(item.strip()) for item in values if item.strip()))


@lru_cache(maxsize=1)
def service_dictionary() -> list[dict]:
    try:
        return cl_services.service_dictionary()
    except (OSError, ValueError) as exc:
        raise ReviewError(f"Cannot read service dictionary: {exc}") from exc


@lru_cache(maxsize=2048)
def service_name(value: str) -> str:
    service_dictionary()
    return cl_services.normalize_service_name(value)


def services_for(recommendation: dict) -> list[str]:
    if recommendation.get("services"):
        return cl_services.normalize_services(recommendation["services"])
    names = []
    for resource_type in recommendation.get("resourceTypes", []):
        candidates = cl_services.services_for_resource_type(resource_type)
        names.append(candidates[0] if len(candidates) == 1 else resource_type.strip().casefold())
    return sorted(set(names), key=str.casefold)


def _service_keys(recommendation: dict) -> set[str]:
    keys = {name.casefold() for name in services_for(recommendation)}
    types = cl_services.normalize_resource_types(recommendation.get("resourceTypes", []))
    # Raw ARM filters always test the actual type, even with explicit classifications.
    keys.update(types)
    if not recommendation.get("services"):
        for resource_type in types:
            keys.update(name.casefold() for name in cl_services.services_for_resource_type(resource_type))
    return keys or {"none"}


def filter_options(items: list[dict]) -> dict:
    services = {
        name.casefold(): name
        for item in items for name in services_for(item["recommendation"])
    }
    services["none"] = "Not service-specific"
    return {
        "severities": {key: key.title() for key in SEVERITIES},
        "waf_pillars": WAF_PILLARS,
        "services": dict(sorted(services.items(), key=lambda entry: entry[1].casefold())),
    }


def filter_items(
    items: list[dict], *, severity: FilterValue = "", waf: FilterValue = "",
    service: FilterValue = "",
    with_arg: bool = False,
) -> list[dict]:
    severities = filter_values(severity, str.casefold)
    pillars = filter_values(waf, str.casefold)
    services = set(filter_values(service, lambda value: service_name(value).casefold()))
    if unknown := set(severities) - SEVERITIES.keys():
        raise ReviewError(f"Unknown severity: {', '.join(sorted(unknown))}. Use high, medium, or low.")
    if unknown := set(pillars) - WAF_PILLARS.keys():
        raise ReviewError(
            f"Unknown WAF pillar: {', '.join(sorted(unknown))}. Use {', '.join(WAF_PILLARS)}."
        )
    if type(with_arg) is not bool:
        raise ReviewError("The ARG-only filter must be a boolean")
    if services:
        available = filter_options(items)["services"]
        accepted = {"none"}.union(*(_service_keys(item["recommendation"]) for item in items))
        if unknown := services - accepted:
            raise ReviewError(
                f"Unknown Azure service: {', '.join(sorted(unknown))}. Available in this review: "
                + ", ".join(available.values())
            )
    severity_codes = {SEVERITIES[value] for value in severities}
    return [
        item for item in items
        if (not severity_codes or item["recommendation"].get("severity") in severity_codes)
        and (not with_arg or has_arg_query(item["recommendation"]))
        and (not pillars or (item["recommendation"].get("waf") or "none").casefold() in pillars)
        and (not services or services.intersection(_service_keys(item["recommendation"])))
    ]
