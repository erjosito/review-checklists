"""Versioned recommendation contract shared by authoring tools and the local app."""

from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
import json
import math
from pathlib import Path
from uuid import UUID

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 1
SCHEMA_PATH = ROOT / "v2" / "schema" / "recommendation.schema.json"


class CorpusError(ValueError):
    """Invalid corpus data or an unsafe migration."""


class StrictLoader(getattr(yaml, "CSafeLoader", yaml.SafeLoader)):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise CorpusError(f"YAML mapping keys must be strings (line {key_node.start_mark.line + 1})")
            if key in result:
                raise CorpusError(f"Duplicate YAML key {key!r} (line {key_node.start_mark.line + 1})")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CorpusError("JSON object keys must be strings")
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise CorpusError("Non-finite numbers are not valid corpus values")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise CorpusError(f"Unsupported corpus value type: {type(value).__name__}")


def load_yaml_document(path: Path) -> dict:
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=StrictLoader)
        if not isinstance(document, dict):
            raise CorpusError("Expected an object")
        return json_value(document)
    except (OSError, UnicodeError, yaml.YAMLError, CorpusError) as exc:
        raise CorpusError(f"{path}: {exc}") from exc


def canonical_id(reco: dict) -> str:
    labels = reco.get("labels", {})
    if not isinstance(labels, dict):
        raise CorpusError("labels must be an object")
    values = [reco.get("id"), reco.get("guid"), labels.get("guid")]
    values = [value for value in values if value is not None]
    if not values:
        raise CorpusError("Recommendation needs an id or legacy GUID")
    try:
        ids = {str(UUID(value)) for value in values}
    except (ValueError, TypeError, AttributeError) as exc:
        raise CorpusError("Invalid recommendation GUID") from exc
    if len(ids) != 1:
        raise CorpusError("id, guid and labels.guid must identify the same recommendation")
    return ids.pop()


def enrich_recommendation(reco: dict) -> dict:
    """Fill only mechanically known metadata; do not infer a compliance meaning."""
    reco = json_value(deepcopy(reco))
    if "schemaVersion" in reco and (
        type(reco["schemaVersion"]) is not int or reco["schemaVersion"] != SCHEMA_VERSION
    ):
        raise CorpusError(f"Unsupported recommendation schemaVersion: {reco['schemaVersion']}")
    reco.pop("filepath", None)
    reco.pop("corpus_file", None)
    reco["schemaVersion"] = SCHEMA_VERSION
    reco["id"] = canonical_id(reco)
    reco.setdefault("services", [])
    reco.setdefault("resourceTypes", [])
    queries = reco.get("queries", {})
    if not isinstance(queries, dict) or not isinstance(queries.get("arg", ""), str):
        raise CorpusError("queries.arg must be a string")
    has_query = bool(queries.get("arg", "").strip())
    automation = reco.setdefault("automation", {})
    if not isinstance(automation, dict):
        raise CorpusError("automation must be an object")
    if has_query:
        inferred_status = "query_available"
    elif reco.get("automatable") is True:
        inferred_status = "candidate"
    elif reco.get("automatable") is False:
        inferred_status = "manual"
    else:
        inferred_status = "unknown"
    automation.setdefault("status", inferred_status)
    automation.setdefault("validatedAt", None)
    if automation["status"] == "query_available":
        automation.setdefault("resultSemantics", "unknown")
    provenance = reco.setdefault("provenance", {})
    if not isinstance(provenance, dict):
        raise CorpusError("provenance must be an object")
    provenance.setdefault("upstreamRevision", None)
    provenance.setdefault("lastReviewed", reco.get("reviewedDate"))
    provenance.setdefault("sources", [])
    return reco


@lru_cache(maxsize=1)
def recommendation_validator():
    from jsonschema import Draft202012Validator, FormatChecker
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CorpusError(f"Cannot read recommendation schema: {exc}") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_recommendation(reco: dict) -> None:
    reco = json_value(reco)
    errors = sorted(
        recommendation_validator().iter_errors(reco),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise CorpusError(f"{reco.get('name', '<unnamed>')}: {location}: {error.message}")
    if reco["id"] != canonical_id(reco):
        raise CorpusError("id must be a canonical lowercase UUID")
    if reco["automation"].get("validatedAt") and reco["automation"]["status"] != "query_available":
        raise CorpusError("validatedAt requires an available query")
    upstream_ids = set()
    for reference in reco["provenance"].get("upstreamRecommendations", []):
        identity = (reference["sourceId"], reference["recommendationId"])
        if identity in upstream_ids:
            raise CorpusError(f"Duplicate upstream recommendation mapping: {identity}")
        upstream_ids.add(identity)
    for alias in reco.get("aliases", []):
        if str(UUID(alias["id"])) != alias["id"]:
            raise CorpusError("Alias id must be a canonical lowercase UUID")
        if alias["id"] == reco["id"]:
            raise CorpusError("An alias cannot use its canonical recommendation's id")


def validate_corpus(recos: list[dict]) -> None:
    if not recos:
        raise CorpusError("Corpus must contain at least one recommendation")
    identities = {}
    names = {}
    for reco in recos:
        validate_recommendation(reco)
        entries = [{"id": reco["id"], "name": reco["name"]}, *reco.get("aliases", [])]
        for entry in entries:
            if entry["id"] in identities:
                raise CorpusError(f"Duplicate recommendation or alias GUID: {entry['id']}")
            identities[entry["id"]] = reco["id"]
            name = entry["name"].casefold()
            if name in names:
                raise CorpusError(f"Duplicate recommendation or alias name: {entry['name']}")
            names[name] = reco["id"]


class CorpusDumper(yaml.SafeDumper):
    pass


def _text_presenter(dumper, value):
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str", value, style="|" if "\n" in value else None,
    )


CorpusDumper.add_representer(str, _text_presenter)


def dump_recommendation(reco: dict) -> str:
    validate_recommendation(reco)
    return yaml.dump(reco, Dumper=CorpusDumper, sort_keys=False, allow_unicode=True, width=100)
