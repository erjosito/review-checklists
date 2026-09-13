"""Read-only administration of the public source corpus, independent of reviews."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from threading import RLock
from urllib.parse import urlsplit
from uuid import UUID

from flask import Blueprint, Flask, Response, abort, current_app, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException, SecurityError

from review_checklists.catalog import canonical_json, content_hash, reject_constant, unique_object
from review_checklists.corpus import ReviewError, has_arg_query, load_corpus
from review_checklists.corpus_history import validate_stage
from review_checklists.filters import WAF_PILLARS, service_name, services_for
from scripts.modules.cl_corpus import CorpusError


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "v2" / "recos"
DEFAULT_REPORTS = Path(__file__).resolve().parent / "docs" / "corpus-refresh"
PAGE_SIZE = 50
MAX_REPORT_BYTES = 16 * 1024 * 1024
PILLARS = tuple(WAF_PILLARS.values())
QUALITY_LABELS = {
    "missing_review_date": "No recorded human review date",
    "missing_sources": "No supporting provenance references",
    "missing_source_dates": "Supporting references without access dates",
    "missing_upstream_revision": "No recorded upstream revision",
    "unknown_query_semantics": "Available ARG with unknown result semantics",
    "unvalidated_query": "Available ARG without a validation date",
    "missing_service": "No explicit or inferred service",
    "inferred_service": "Service inferred from resource type only",
    "aliases": "Has retired identity aliases",
}
REFRESH_MANIFESTS = tuple(
    f"{pillar}-refresh-manifest.json"
    for pillar in ("cost", "security", "reliability", "performance", "operations")
)
OPERATIONS_EVENT = "full-refresh-2026-09-11-operations-manifest.json"
SECURITY_EVENT = "full-refresh-2026-09-11-security-manifest.json"
RELIABILITY_EVENT = "full-refresh-2026-09-11-reliability-manifest.json"
COST_EVENT = "full-refresh-2026-09-11-cost-refresh-manifest.json"
PERFORMANCE_EVENT = "full-refresh-2026-09-11-performance-manifest.json"
APRL_EVENT = "full-refresh-2026-09-11-aprl-review.json"
NORMALIZATION_EVENT = "service-normalization.json"
FOLLOWUP_EVENT = "followup-2026-09-13-application.json"
CLASSIFICATION_PROPOSALS = "classification-followup-2026-09-13.json"
KEY_VAULT_PROPOSALS = "key-vault-followup-2026-09-13.json"
DUPLICATE_PROPOSALS = "deferred-duplicate-followup-2026-09-13.json"
FOLLOWUP_PROPOSALS = (CLASSIFICATION_PROPOSALS, KEY_VAULT_PROPOSALS, DUPLICATE_PROPOSALS)
NESTED_EVENTS = {
    OPERATIONS_EVENT: Path("full-refresh-2026-09-11") / "operations-manifest.json",
    SECURITY_EVENT: Path("full-refresh-2026-09-11") / "security-manifest.json",
    RELIABILITY_EVENT: Path("full-refresh-2026-09-11") / "reliability-manifest.json",
    COST_EVENT: Path("full-refresh-2026-09-11") / "cost-refresh-manifest.json",
    PERFORMANCE_EVENT: Path("full-refresh-2026-09-11") / "performance-manifest.json",
    APRL_EVENT: Path("full-refresh-2026-09-11") / "aprl-review.json",
}
NESTED_DOCUMENTS = {
    f"full-refresh-2026-09-11-{name}": Path("full-refresh-2026-09-11") / name
    for name in ("README.md", "cost-report.md", "cost-sources.md", "security-report.md",
                 "reliability-report.md", "performance-report.md", "operations-report.md",
                 "operations-sources.md", "aprl-summary.md")
}
NESTED_REPORTS = {**NESTED_EVENTS, **NESTED_DOCUMENTS}
KNOWN_REPORTS = (
    *REFRESH_MANIFESTS,
    "alias-migration.json", "cost-alias-migration.json", "duplicate-audit.json",
    "post-cost-duplicate-review.json", "url-normalization.json",
    "non-cost-merge-manifest.json", "post-cost-safe-merge-manifest.json", "cost-research.json",
    NORMALIZATION_EVENT, "report-redactions.json",
    *FOLLOWUP_PROPOSALS, FOLLOWUP_EVENT, "followup-safe-merge-manifest-2026-09-13.json",
    "followup-merge-result-2026-09-13.json",
    *NESTED_EVENTS,
)
PUBLIC_DOCUMENTS = (
    "README.md",
    *(f"{pillar}-{suffix}.md" for pillar in
      ("cost", "security", "reliability", "performance", "operations")
      for suffix in ("sources", "refresh-report")),
    *NESTED_DOCUMENTS,
    *(name.removesuffix(".json") + ".md" for name in FOLLOWUP_PROPOSALS),
    "followup-2026-09-13.md",
)


class CorpusAdminError(Exception):
    """A public-corpus or maintenance-report problem requiring attention."""


class CorpusFilterError(CorpusAdminError):
    """A malformed read-only drilldown request."""


def safe_external_url(value: str | None) -> str | None:
    """Only explicit HTTP(S) links may become clickable report/source URLs."""
    if not isinstance(value, str) or any(ord(char) < 32 for char in value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() in {"http", "https"} and parsed.hostname and not (
            parsed.username or parsed.password
        ):
            return value
    except ValueError:
        return None
    return None


def quality_flags(reco: dict, services: list[str]) -> set[str]:
    provenance = reco["provenance"]
    sources = provenance["sources"]
    flags = set()
    if not provenance["lastReviewed"]:
        flags.add("missing_review_date")
    if not sources:
        flags.add("missing_sources")
    if any(not source.get("accessedAt") for source in sources):
        flags.add("missing_source_dates")
    if not provenance["upstreamRevision"]:
        flags.add("missing_upstream_revision")
    if has_arg_query(reco):
        if reco["automation"].get("resultSemantics", "unknown") == "unknown":
            flags.add("unknown_query_semantics")
        if not reco["automation"]["validatedAt"]:
            flags.add("unvalidated_query")
    if not services:
        flags.add("missing_service")
    elif not reco["services"]:
        flags.add("inferred_service")
    if reco.get("aliases"):
        flags.add("aliases")
    return flags


def summarize_corpus(recommendations: list[dict]) -> dict:
    """Count canonical records only; aliases and reference relationships are separate."""
    rows = []
    matrix = defaultdict(Counter)
    origins = Counter()
    alias_origins = Counter()
    service_modes = Counter()
    semantics = Counter()
    automation = Counter()
    quality = Counter()
    supporting = {}
    reviewed_dates = []
    validated = 0
    for reco in recommendations:
        services = services_for(reco)
        mode = "explicit" if reco["services"] else "inferred" if services else "missing"
        pillar = reco.get("waf") or "Not specified"
        flags = quality_flags(reco, services)
        arg = has_arg_query(reco)
        is_validated = arg and bool(reco["automation"]["validatedAt"])
        rows.append({
            "id": reco["id"], "recommendation": reco, "services": services,
            "service_mode": mode, "pillar": pillar, "quality": flags,
            "arg_available": arg, "arg_validated": is_validated,
        })
        service_modes[mode] += 1
        origins[reco["source"]["type"]] += 1
        alias_origins.update(alias.get("source", {}).get("type", "Not recorded")
                             for alias in reco.get("aliases", []))
        automation[reco["automation"]["status"]] += 1
        quality.update(flags)
        if provenance_date := reco["provenance"]["lastReviewed"]:
            reviewed_dates.append(provenance_date)
        if arg:
            semantics[reco["automation"].get("resultSemantics", "unknown")] += 1
            validated += is_validated
        for service in services or ["Not service-specific"]:
            matrix[service][pillar] += 1
        for source in reco["provenance"]["sources"]:
            entry = supporting.setdefault(source["url"], {
                "url": source["url"], "titles": set(), "ids": set(), "dates": set(),
                "undated": False,
            })
            entry["ids"].add(reco["id"])
            if source.get("title"):
                entry["titles"].add(source["title"])
            if source.get("accessedAt"):
                entry["dates"].add(source["accessedAt"])
            else:
                entry["undated"] = True
    records = sorted(
        ({key: value for key, value in reco.items() if key != "corpus_file"}
         for reco in recommendations),
        key=lambda reco: reco["id"],
    )
    return {
        "rows": rows, "total": len(rows), "aliases": sum(alias_origins.values()),
        "hash": content_hash(records),
        "schema_versions": sorted({reco["schemaVersion"] for reco in recommendations}),
        "arg_available": sum(semantics.values()), "arg_validated": validated,
        "semantics": dict(sorted(semantics.items())),
        "automation": dict(sorted(automation.items())),
        "service_modes": {mode: service_modes[mode] for mode in ("explicit", "inferred", "missing")},
        "origins": dict(sorted(origins.items())),
        "alias_origins": dict(sorted(alias_origins.items())),
        "quality": {key: quality[key] for key in QUALITY_LABELS},
        "matrix": dict(sorted(matrix.items(), key=lambda pair: pair[0].casefold())),
        "references": sorted(supporting.values(), key=lambda item: item["url"]),
        "oldest_review": min(reviewed_dates) if reviewed_dates else None,
        "latest_review": max(reviewed_dates) if reviewed_dates else None,
    }


@dataclass
class CorpusSnapshot:
    recommendations: list[dict]
    summary: dict


class CorpusStore:
    """One validated snapshot, invalidated by every source-file metadata change."""

    def __init__(self, root: Path):
        self.root = root.absolute()
        self._signature = None
        self._snapshot = None
        self._lock = RLock()

    def signature(self) -> tuple:
        if not self.root.is_dir():
            raise CorpusAdminError("Source corpus directory is missing or unavailable.")
        resolved_root = self.root.resolve()
        result = []
        for path in sorted(self.root.rglob("*")):
            if path.is_symlink() or not path.resolve().is_relative_to(resolved_root):
                raise CorpusAdminError("Source corpus contains a link outside its boundary; use ordinary source files.")
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            stat = path.stat()
            if not path.is_file() or stat.st_size > 2 * 1024 * 1024:
                raise CorpusAdminError("A corpus entry is not a regular file or exceeds the 2 MiB limit.")
            result.append((path.relative_to(self.root).as_posix(), stat.st_mtime_ns,
                           stat.st_ctime_ns, stat.st_size, stat.st_ino))
            if len(result) > 50000:
                raise CorpusAdminError("Source corpus exceeds the 50,000-file administration limit.")
        return tuple(result)

    def get(self) -> CorpusSnapshot:
        with self._lock:
            try:
                signature = self.signature()
                if self._snapshot is not None and signature == self._signature:
                    return self._snapshot
                self._snapshot = None
                recommendations = load_corpus(self.root, require_current=True)
                summary = summarize_corpus(recommendations)
                if signature != self.signature():
                    raise CorpusAdminError("Source corpus changed while loading. Reload after the edit completes.")
                self._snapshot = CorpusSnapshot(recommendations, summary)
                self._signature = signature
                return self._snapshot
            except (ReviewError, CorpusError, OSError) as exc:
                self._snapshot = None
                message = str(exc).replace(str(self.root), "<corpus>")
                raise CorpusAdminError(f"Cannot validate the source corpus: {message}") from exc


def public_report_path(root: Path, name: str) -> Path:
    if name not in (*KNOWN_REPORTS, *PUBLIC_DOCUMENTS):
        raise CorpusAdminError("This file is not an allowlisted public maintenance report.")
    path = root / NESTED_REPORTS.get(name, Path(name))
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise CorpusAdminError("Public report links must stay inside the configured reports directory.")
    if not path.is_file():
        raise CorpusAdminError(f"Public report is missing: {name}")
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise CorpusAdminError(f"Public report exceeds the 16 MiB limit: {name}")
    return path


def read_report(root: Path, name: str) -> dict:
    try:
        path = public_report_path(root, name)
        text = path.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) > MAX_REPORT_BYTES:
            raise CorpusAdminError(f"Public report exceeds the 16 MiB limit: {name}")
        data = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise CorpusAdminError(f"{name}: expected a structured JSON object.")
        return data
    except (OSError, UnicodeError, ValueError, CorpusError) as exc:
        raise CorpusAdminError(f"Cannot read structured report {name}: {exc}") from exc


def _object(data: dict, key: str, name: str) -> dict:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise CorpusAdminError(f"{name}: {key} must be an object.")
    return value


def _records(data: dict, key: str, name: str) -> list[dict]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CorpusAdminError(f"{name}: {key} must be an array of objects.")
    return value


def _outcome_entries(data: dict, name: str) -> tuple[list[dict], list[dict], Counter]:
    records = _records(data, "records", name)
    additions = _records(data, "additions", name)
    if "records" not in data or "additions" not in data:
        raise CorpusAdminError(f"{name}: incomplete outcome manifest.")
    observed = Counter()
    identities = set()
    for record in [*records, *additions]:
        try:
            identity = record["id"]
            if str(UUID(identity)) != identity or identity in identities:
                raise ValueError("Noncanonical or duplicate ID")
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise CorpusAdminError(f"{name}: invalid or repeated outcome record ID.") from exc
        identities.add(identity)
        if not isinstance(record.get("reason"), str) or not record["reason"].strip():
            raise CorpusAdminError(f"{name}: every outcome record requires its recorded reason.")
    for record in records:
        if not isinstance(record.get("outcome"), str) or record["outcome"] not in {
            "updated", "supportedunchanged", "needsmanualreview",
        }:
            raise CorpusAdminError(f"{name}: unknown assessment outcome.")
        observed[record["outcome"]] += 1
    return records, additions, observed


def _event_date(data: dict, key: str, name: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise CorpusAdminError(f"{name}: assessment date is missing.")
    try:
        if datetime.strptime(value, "%Y-%m-%d").date().isoformat() != value:
            raise ValueError("Noncanonical date")
    except ValueError as exc:
        raise CorpusAdminError(f"{name}: invalid assessment date.") from exc
    return value


def operations_event(data: dict, name: str) -> dict:
    """The finalized bounded Operations manifest predates the generic event schema."""
    records, additions, observed = _outcome_entries(data, name)
    outcomes = _object(data, "outcomes", name)
    if set(outcomes) != {"updated", "supportedunchanged", "needsmanualreview"}:
        raise CorpusAdminError(f"{name}: incomplete Operations outcome counts.")
    for key, value in outcomes.items():
        if type(value) is not int or value < 0 or value != observed[key]:
            raise CorpusAdminError(f"{name}: {key} disagrees with its Operations records.")
    for key, value in (("baselineCount", len(records)), ("additionsCount", len(additions))):
        if type(data.get(key)) is not int or data[key] != value:
            raise CorpusAdminError(f"{name}: {key} disagrees with its Operations records.")
    return {
        "filename": name, "status": "Applied bounded Operations event (recorded manifest)",
        "date": _event_date(data, "assessedAt", name),
        "scope": (
            "Frozen non-APRL Operations baseline. Only updated records and additions are "
            "application changes; supported-unchanged and needs-manual-review records are "
            "separate assessment outcomes. Supporting inventories/mappings are not extra events."
        ),
        "summary": {
            "baselineRecordsAssessed": len(records),
            "appliedUpdates": observed["updated"], "appliedAdditions": len(additions),
            "supportedUnchanged": observed["supportedunchanged"],
            "needsManualReview": observed["needsmanualreview"],
        },
    }


def security_event(data: dict, name: str) -> dict:
    """Security distinguishes guidance edits from provenance-only verified-unchanged rows."""
    if data.get("artifactSchema") != "security-refresh-manifest/1":
        raise CorpusAdminError(f"{name}: unsupported Security manifest schema.")
    records, additions, observed = _outcome_entries(data, name)
    counts = _object(data, "counts", name)
    guidance = 0
    provenance_only = 0
    for record in records:
        fields = record.get("changedFields")
        if type(record.get("guidanceChanged")) is not bool or not isinstance(fields, list) or not all(
            isinstance(field, str) for field in fields
        ):
            raise CorpusAdminError(f"{name}: invalid Security guidance/field-change evidence.")
        if record["guidanceChanged"] != (record["outcome"] == "updated"):
            raise CorpusAdminError(f"{name}: Security guidance-change and outcome evidence disagree.")
        guidance += record["guidanceChanged"]
        provenance_only += not record["guidanceChanged"] and set(fields) == {"provenance"}
    expected = {
        "baseline": len(records), "after": len(records) + len(additions),
        "updated": observed["updated"], "supportedunchanged": observed["supportedunchanged"],
        "needsmanualreview": observed["needsmanualreview"], "additions": len(additions),
        "guidanceChanged": guidance, "provenanceOnly": provenance_only,
        "sourceVerified": observed["updated"] + observed["supportedunchanged"],
        "unverified": observed["needsmanualreview"],
    }
    for key, count in expected.items():
        if type(counts.get(key)) is not int or counts[key] != count:
            raise CorpusAdminError(f"{name}: {key} disagrees with its Security outcome evidence.")
    if not isinstance(data.get("scope"), str) or not data["scope"].strip():
        raise CorpusAdminError(f"{name}: Security scope must be recorded.")
    return {
        "filename": name, "status": "Implemented bounded Security draft; not full source refresh",
        "date": _event_date(data, "date", name),
        "scope": data["scope"] + ". Guidance edits and provenance-only changes are separate. "
                 "Unverified records remain visible; no human approval or live validation is implied.",
        "summary": {
            "baselineRecordsAccountedFor": len(records), "guidanceUpdates": guidance,
            "provenanceOnlyUpdates": provenance_only, "appliedAdditions": len(additions),
            "supportedUnchanged": observed["supportedunchanged"],
            "unverifiedNeedsManualReview": observed["needsmanualreview"],
        },
    }


def reliability_event(data: dict, name: str) -> dict:
    """Reconcile the frozen Reliability entry inventory, without counting triage as refresh."""
    entries = _records(data, "entries", name)
    if "entries" not in data or "additions" not in data:
        raise CorpusAdminError(f"{name}: Reliability entries/additions must be recorded.")
    records, additions, observed = _outcome_entries({
        "records": [dict(entry, reason=entry.get("evidence")) for entry in entries],
        "additions": data["additions"],
    }, name)
    baseline = data.get("baselineIds")
    if not isinstance(baseline, list) or not all(isinstance(identity, str) for identity in baseline):
        raise CorpusAdminError(f"{name}: Reliability baseline IDs must be an explicit list.")
    if len(baseline) != len(set(baseline)) or set(baseline) != {record["id"] for record in records}:
        raise CorpusAdminError(f"{name}: Reliability entries do not reconcile with the frozen baseline IDs.")
    for key, count in (("baselineCount", len(records)), ("additionCount", len(additions))):
        if type(data.get(key)) is not int or data[key] != count:
            raise CorpusAdminError(f"{name}: {key} disagrees with its Reliability records.")
    summary = _object(data, "summary", name)
    if set(summary) != {"updated", "supportedunchanged", "needsmanualreview"} or any(
        type(count) is not int or count != observed[key] for key, count in summary.items()
    ):
        raise CorpusAdminError(f"{name}: Reliability outcome counts disagree with the entry evidence.")
    if not isinstance(data.get("scope"), str) or not data["scope"].strip():
        raise CorpusAdminError(f"{name}: Reliability scope must be recorded.")
    return {
        "filename": name, "status": "Implemented bounded Reliability event; not full baseline verification",
        "date": _event_date(data, "date", name),
        "scope": data["scope"] + ". Only updated entries and additions are refresh changes. "
                 "Baseline and source-coverage artifacts are supporting evidence, not extra events.",
        "summary": {
            "baselineRecordsAccountedFor": len(records), "appliedUpdates": observed["updated"],
            "appliedAdditions": len(additions), "supportedUnchanged": observed["supportedunchanged"],
            "needsManualReview": observed["needsmanualreview"],
        },
    }


def frozen_refresh_event(data: dict, name: str) -> dict:
    """Adapt the remaining frozen-slice ledgers without equating triage with verification."""
    records = _records(data, "records", name)
    if "records" not in data:
        raise CorpusAdminError(f"{name}: frozen outcome records are missing.")
    if name == COST_EVENT:
        if data.get("artifactSchema") != "full-refresh-cost-manifest/1":
            raise CorpusAdminError(f"{name}: unsupported Cost manifest schema.")
        summary = _object(data, "summary", name)
        counts = _object(summary, "contentOutcomes", name)
        field, date_key, baseline = "contentOutcome", "asOf", summary.get("baselineCostCanonical")
        additions = _records(data, "additions", name)
        declared_additions = summary.get("addedRecommendations")
        scope = "Frozen non-APRL Cost records; subsequent APRL classifications are a separate event."
    elif name == PERFORMANCE_EVENT:
        if data.get("schemaVersion") != 1:
            raise CorpusAdminError(f"{name}: unsupported Performance manifest schema.")
        summary = _object(data, "summary", name)
        counts = {key: summary.get(key) for key in ("updated", "supported_unchanged", "needs_manual_review")}
        field, date_key, baseline = "outcome", "assessedAt", summary.get("baselineCount")
        additions = _records(data, "additions", name)
        declared_additions = summary.get("additions")
        scope = data.get("ownership")
    else:
        if data.get("schemaVersion") != 1 or data.get("status") != "applied":
            raise CorpusAdminError(f"{name}: unsupported APRL applied ledger.")
        summary = _object(data, "counts", name)
        counts = _object(summary, "byStatus", name)
        field, date_key, baseline = "status", "asOf", summary.get("baseline")
        additions, declared_additions = [], 0
        scope = data.get("scope")
    if not isinstance(scope, str) or not scope.strip():
        raise CorpusAdminError(f"{name}: scope must be explicit.")
    observed = Counter()
    identities = set()
    for record in [*records, *additions]:
        try:
            identity = record["id"]
            if str(UUID(identity)) != identity or identity in identities:
                raise ValueError("Noncanonical or repeated ID")
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise CorpusAdminError(f"{name}: invalid or repeated outcome ID.") from exc
        identities.add(identity)
    for record in records:
        outcome = record.get(field)
        if outcome not in ("updated", "supported_unchanged", "needs_manual_review"):
            raise CorpusAdminError(f"{name}: unknown outcome {outcome!r}.")
        observed[outcome] += 1
    if set(counts) != {"updated", "supported_unchanged", "needs_manual_review"} or any(
        type(value) is not int or value != observed[key] for key, value in counts.items()
    ):
        raise CorpusAdminError(f"{name}: outcome counts disagree with the frozen records.")
    if type(baseline) is not int or baseline != len(records):
        raise CorpusAdminError(f"{name}: baseline count disagrees with its records.")
    if type(declared_additions) is not int or declared_additions != len(additions):
        raise CorpusAdminError(f"{name}: addition count disagrees with its records.")
    return {
        "filename": name, "status": "Applied bounded source assessment; unresolved gaps retained",
        "date": _event_date(data, date_key, name),
        "scope": scope + " Metadata edits can occur independently of guidance outcomes. "
                 "No human approval or live ARG validation is implied.",
        "summary": {
            "baselineRecordsAccountedFor": len(records), "updated": observed["updated"],
            "supportedUnchanged": observed["supported_unchanged"],
            "needsManualReview": observed["needs_manual_review"], "appliedAdditions": len(additions),
        },
    }


def normalization_event(data: dict, name: str) -> dict:
    if data.get("schemaVersion") != 1 or data.get("stage") != "service-normalization":
        raise CorpusAdminError(f"{name}: unsupported normalization stage.")
    records = _records(data, "records", name)
    inventory = _records(data, "corpusBefore", name)
    summary = _object(data, "summary", name)
    for entries in (records, inventory):
        identifiers = [row.get("id") for row in entries]
        if not all(isinstance(identity, str) for identity in identifiers) or len(set(identifiers)) != len(entries):
            raise CorpusAdminError(f"{name}: normalization IDs must be explicit and unique.")
    if not {row["id"] for row in records} <= {row["id"] for row in inventory}:
        raise CorpusAdminError(f"{name}: changed IDs are outside the recorded normalization inventory.")
    counts = {"canonical": len(inventory), "changed": len(records), "unchanged": len(inventory) - len(records)}
    for field, count in counts.items():
        if type(summary.get(field)) is not int or summary[field] != count:
            raise CorpusAdminError(f"{name}: {field} disagrees with normalization records.")
    return {
        "filename": name, "status": data.get("status", "Not recorded"),
        "date": _event_date(data, "assessedAt", name),
        "scope": "Mechanical service/type normalization, not a source-guidance refresh or technical approval.",
        "summary": counts,
    }


def followup_proposal_snapshot(data: dict, name: str) -> dict:
    if name == DUPLICATE_PROPOSALS:
        if data.get("artifactSchema") != "deferred-duplicate-followup/1":
            raise CorpusAdminError(f"{name}: unsupported duplicate follow-up.")
        records, field, identity = _records(data, "decisions", name), "decision", "groupId"
        declared = _object(data, "decisionCounts", name)
        statuses = ("equivalent_mergeable", "related_distinct_reject_merge", "unresolved")
        date_key = "asOf"
    elif name == KEY_VAULT_PROPOSALS:
        if data.get("artifactSchema") != "key-vault-followup-proposals/1":
            raise CorpusAdminError(f"{name}: unsupported Key Vault follow-up.")
        records, field, identity = _records(data, "records", name), "decision", "id"
        declared = _object(data, "counts", name)
        statuses = ("updated", "supportedunchanged", "unresolved")
        date_key = "date"
    else:
        if data.get("schemaVersion") != 1 or data.get("stage") != "classification-followup-2026-09-13":
            raise CorpusAdminError(f"{name}: unsupported classification follow-up.")
        records, field, identity = _records(data, "records", name), "status", "id"
        summary = _object(data, "summary", name)
        statuses = ("proposed-semantic-amendment", "deferred-no-change")
        declared = dict(zip(statuses, (summary.get("proposedAmendments"), summary.get("deferredRecords"))))
        date_key = "assessedAt"
    ids = [row.get(identity) for row in records]
    if not records or not all(isinstance(value, str) and value for value in ids) or len(set(ids)) != len(ids):
        raise CorpusAdminError(f"{name}: missing or repeated follow-up identities.")
    observed = Counter()
    for row in records:
        if row.get(field) not in statuses:
            raise CorpusAdminError(f"{name}: unknown follow-up disposition.")
        observed[row[field]] += 1
        if name == DUPLICATE_PROPOSALS:
            if (not isinstance(row.get("historicalCanonicalId"), str)
                    or not isinstance(row.get("retiredIds"), list)
                    or not all(isinstance(value, str) for value in row["retiredIds"])
                    or not isinstance(row.get("blockers"), list)
                    or not all(isinstance(value, str) for value in row["blockers"])):
                raise CorpusAdminError(f"{name}: invalid duplicate identity or blocker evidence.")
            if row[field] == "equivalent_mergeable" and (
                not isinstance(row.get("canonicalId"), str) or not row["retiredIds"]
            ):
                raise CorpusAdminError(f"{name}: a mergeable proposal needs canonical and retired IDs.")
    if any(type(declared.get(key)) is not int or declared[key] != observed[key] for key in statuses):
        raise CorpusAdminError(f"{name}: proposal counts disagree with recorded decisions.")
    return {
        "filename": name, "status": "Frozen research proposals; not an application event",
        "date": _event_date(data, date_key, name),
        "scope": data.get("scope", "") + " Later application is recorded separately; no human approval is implied.",
        "summary": {"assessedGroups" if name == DUPLICATE_PROPOSALS else "assessedRecommendations": len(records),
                    **{key: observed[key] for key in statuses}},
    }


def followup_application_event(data: dict, name: str) -> dict:
    try:
        validate_stage(data)
    except CorpusError as exc:
        raise CorpusAdminError(f"{name}: {exc}") from exc
    if data["stage"] != "corpus-followup-2026-09-13":
        raise CorpusAdminError(f"{name}: unexpected follow-up stage identity.")
    before, after = _object(data, "beforeCorpus", name), _object(data, "afterCorpus", name)
    for state in (before, after):
        if any(type(state.get(key)) is not int or state[key] < 0 for key in ("canonical", "aliases")):
            raise CorpusAdminError(f"{name}: invalid before/after corpus counts.")
    corpus_files = [row for row in data["files"] if row["path"].startswith("v2/recos/")]
    updated = sum(row["before"] is not None and row["after"] is not None for row in corpus_files)
    retired = sum(row["after"] is None for row in corpus_files)
    added = sum(row["before"] is None for row in corpus_files)
    if before["canonical"] + added - retired != after["canonical"]:
        raise CorpusAdminError(f"{name}: corpus count delta disagrees with file changes.")
    amendments = _records(data, "amendments", name)
    ids = [row.get("id") for row in amendments]
    if not all(isinstance(value, str) for value in ids) or len(set(ids)) != len(ids):
        raise CorpusAdminError(f"{name}: invalid amendment identities.")
    if any(type(row.get("guidanceRelevant")) is not bool for row in amendments):
        raise CorpusAdminError(f"{name}: amendment relevance must be explicit.")
    merge = _object(data, "mergeResult", name)
    groups = _records(merge, "groups", name)
    if any(not isinstance(group.get("canonicalId"), str) or not isinstance(group.get("retiredIds"), list)
           or not all(isinstance(value, str) for value in group["retiredIds"]) for group in groups):
        raise CorpusAdminError(f"{name}: invalid applied merge identities.")
    retired_ids = [identifier for group in groups for identifier in group["retiredIds"]]
    if (len(set(retired_ids)) != retired or len(retired_ids) != retired
            or after["aliases"] != before["aliases"] + retired):
        raise CorpusAdminError(f"{name}: retired identities and alias accounting disagree.")
    if (merge.get("mode") != "write" or merge.get("before") != before["canonical"]
            or merge.get("after") != after["canonical"] or merge.get("retired") != retired):
        raise CorpusAdminError(f"{name}: merge result does not match the applied stage.")
    counts = {
        "canonicalBefore": before["canonical"], "canonicalAfter": after["canonical"],
        "aliasesBefore": before["aliases"], "aliasesAfter": after["aliases"],
        "sourceAmendments": len(amendments), "guidanceAmendments": sum(row["guidanceRelevant"] for row in amendments),
        "provenanceOnlyAmendments": sum(not row["guidanceRelevant"] for row in amendments),
        "mergeGroups": len(groups), "updatedRecommendationFiles": updated,
        "retiredRecommendationFiles": retired, "addedRecommendationFiles": added,
        "catalogueFiles": len(data["files"]) - len(corpus_files),
    }
    summary = _object(data, "summary", name)
    if set(summary) != set(counts) or any(type(summary[key]) is not int or summary[key] != value
                                          for key, value in counts.items()):
        raise CorpusAdminError(f"{name}: application summary disagrees with its evidence.")
    return {
        "filename": name, "status": "Applied bounded amendments and identity-preserving merges",
        "date": _event_date(data, "assessedAt", name),
        "scope": data.get("scope", "") + " Historical proposals remain separate. No human approval or live validation.",
        "summary": counts,
    }


def maintenance_history(root: Path) -> dict:
    """Keep application events distinct from overlapping audit/aggregate snapshots."""
    result = {"events": [], "snapshots": [], "deferrals": None, "errors": [], "documents": []}
    followup_decisions, applied_merges = None, set()
    if not root.is_dir():
        result["errors"].append("Public maintenance reports directory is missing or unavailable.")
        return result
    for name in PUBLIC_DOCUMENTS:
        if (root / NESTED_REPORTS.get(name, Path(name))).exists():
            try:
                public_report_path(root, name)
                result["documents"].append(name)
            except CorpusAdminError as exc:
                result["errors"].append(str(exc))
    for name in KNOWN_REPORTS:
        if not (root / NESTED_REPORTS.get(name, Path(name))).exists():
            continue
        try:
            data = read_report(root, name)
            if name == OPERATIONS_EVENT:
                result["events"].append(operations_event(data, name))
                continue
            if name == SECURITY_EVENT:
                result["events"].append(security_event(data, name))
                continue
            if name == RELIABILITY_EVENT:
                result["events"].append(reliability_event(data, name))
                continue
            if name in (COST_EVENT, PERFORMANCE_EVENT, APRL_EVENT):
                result["events"].append(frozen_refresh_event(data, name))
                continue
            if name == NORMALIZATION_EVENT:
                record = normalization_event(data, name)
                result["events" if data.get("status") == "applied" else "snapshots"].append(record)
                continue
            if name in FOLLOWUP_PROPOSALS:
                result["snapshots"].append(followup_proposal_snapshot(data, name))
                if name == DUPLICATE_PROPOSALS:
                    followup_decisions = data["decisions"]
                continue
            if name == FOLLOWUP_EVENT:
                result["events"].append(followup_application_event(data, name))
                applied_merges.update(
                    (group["canonicalId"], frozenset(group["retiredIds"]))
                    for group in data["mergeResult"]["groups"]
                )
                continue
            summary = _object(data, "summary", name)
            record = {
                "filename": name, "status": data.get("status", "Not recorded"),
                "date": (data.get("asOf") or data.get("createdUtc") or data.get("reviewedUtc")
                         or data.get("assessedAt") or data.get("date") or "Not recorded"),
                "scope": data.get("scope", data.get("reason", "See the source report for scope.")),
                "summary": summary,
            }
            if name in REFRESH_MANIFESTS:
                if data.get("artifactSchema") != name.removesuffix(".json") + "/1":
                    raise CorpusAdminError(f"{name}: unsupported refresh manifest schema.")
                updates = _records(data, "updates", name)
                additions = _records(data, "additions", name)
                if "updates" not in data or "additions" not in data:
                    raise CorpusAdminError(f"{name}: updates and additions must be recorded explicitly.")
                for key, count in (("appliedUpdates", len(updates)), ("appliedAdditions", len(additions))):
                    if key in summary and (type(summary[key]) is not int or summary[key] != count):
                        raise CorpusAdminError(f"{name}: {key} disagrees with its recorded entries.")
                record["summary"] = {"recordedUpdateEntries": len(updates),
                                     "recordedAdditionEntries": len(additions), **summary}
                result["events" if data.get("status") == "applied" else "snapshots"].append(record)
            elif name in {"alias-migration.json", "cost-alias-migration.json"}:
                merge = _object(data, "mergeResult", name)
                for key in ("before", "after", "retired"):
                    if key not in merge or type(merge[key]) is not int or merge[key] < 0:
                        raise CorpusAdminError(f"{name}: mergeResult.{key} must be a nonnegative integer.")
                if merge["before"] - merge["retired"] != merge["after"]:
                    raise CorpusAdminError(f"{name}: inconsistent merge transaction counts.")
                groups = _records(merge, "groups", name)
                record["summary"] = {key: merge[key] for key in ("before", "after", "retired")}
                record["summary"]["groups"] = len(groups)
                result["events" if data.get("status") == "applied" and merge.get("mode") == "write"
                       else "snapshots"].append(record)
                if "finalStageSummary" in data:
                    aggregate = _object(data, "finalStageSummary", name)
                    result["snapshots"].append(dict(record, summary=aggregate,
                                                    scope="Aggregate snapshot, not another application event."))
                if name == "alias-migration.json" and "finalTechnicalDeferrals" in data:
                    deferrals = _records(data, "finalTechnicalDeferrals", name)
                    for item in deferrals:
                        if not isinstance(item.get("groupId"), str) or not isinstance(item.get("reasons"), list):
                            raise CorpusAdminError(f"{name}: invalid technical deferral entry.")
                        if not all(isinstance(reason, str) for reason in item["reasons"]):
                            raise CorpusAdminError(f"{name}: deferral reasons must be strings.")
                        if "canonicalId" in item:
                            try:
                                if str(UUID(item["canonicalId"])) != item["canonicalId"]:
                                    raise ValueError("Noncanonical UUID")
                            except (ValueError, TypeError, AttributeError) as exc:
                                raise CorpusAdminError(f"{name}: invalid technical-deferral canonical ID.") from exc
                    result["deferrals"] = deferrals
            else:
                result["snapshots"].append(record)
        except CorpusAdminError as exc:
            result["errors"].append(str(exc))
    if followup_decisions is not None:
        pending = []
        for decision in followup_decisions:
            if decision["decision"] == "related_distinct_reject_merge":
                continue
            if decision["decision"] == "equivalent_mergeable" and (
                decision.get("canonicalId"), frozenset(decision.get("retiredIds", []))
            ) in applied_merges:
                continue
            reasons = decision.get("blockers", [])
            if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
                result["errors"].append(f"{DUPLICATE_PROPOSALS}: invalid remaining blocker evidence.")
                continue
            pending.append({
                "groupId": decision["groupId"], "canonicalId": decision.get("historicalCanonicalId"),
                "reasons": reasons or ["Equivalent proposal is awaiting a separately recorded application."],
            })
        result["deferrals"] = pending
    return result


def _paginate(items: list) -> dict:
    try:
        page = int(request.args.get("page", "1"))
    except ValueError as exc:
        raise CorpusFilterError("Page must be an integer.") from exc
    pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    if not 1 <= page <= pages:
        raise CorpusFilterError(f"Page must be between 1 and {pages}.")
    return {"items": items[(page - 1) * PAGE_SIZE:page * PAGE_SIZE],
            "total": len(items), "page": page, "pages": pages}


def filtered_rows(summary: dict) -> list[dict]:
    allowed = {"search", "service", "waf", "origin", "quality", "arg", "reference", "page"}
    if unknown := request.args.keys() - allowed:
        raise CorpusFilterError("Unknown filter: " + ", ".join(sorted(unknown)))
    if any(len(request.args.getlist(key)) > 1 for key in allowed):
        raise CorpusFilterError("Use one value per corpus filter.")
    search = request.args.get("search", "").strip().casefold()
    service = request.args.get("service", "")
    pillar = request.args.get("waf", "")
    origin = request.args.get("origin", "")
    quality = request.args.get("quality", "")
    arg = request.args.get("arg", "")
    reference = request.args.get("reference", "")
    if pillar and pillar not in PILLARS:
        raise CorpusFilterError("Unknown WAF pillar.")
    if origin and origin not in summary["origins"]:
        raise CorpusFilterError("Unknown original source family.")
    if quality and quality not in QUALITY_LABELS:
        raise CorpusFilterError("Unknown data-quality filter.")
    if arg not in {"", "available", "validated", "unvalidated", "missing"}:
        raise CorpusFilterError("Unknown ARG filter.")
    if service:
        service = "Not service-specific" if service == "none" else service_name(service)
        if service not in summary["matrix"]:
            raise CorpusFilterError("Unknown Azure service.")
    selected = []
    for row in summary["rows"]:
        reco = row["recommendation"]
        identities = [reco["id"], reco["name"], reco["title"], reco.get("description", ""),
                      *(alias["id"] + " " + alias["name"] for alias in reco.get("aliases", []))]
        if search and not any(search in value.casefold() for value in identities):
            continue
        if service and service not in (row["services"] or ["Not service-specific"]):
            continue
        if pillar and row["pillar"] != pillar:
            continue
        if origin and reco["source"]["type"] != origin:
            continue
        if quality and quality not in row["quality"]:
            continue
        if reference and not any(source["url"] == reference for source in reco["provenance"]["sources"]):
            continue
        if ((arg == "available" and not row["arg_available"])
                or (arg == "validated" and not row["arg_validated"])
                or (arg == "unvalidated" and not (row["arg_available"] and not row["arg_validated"]))
                or (arg == "missing" and row["arg_available"])):
            continue
        selected.append(row)
    return selected


def _secure_response(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'self'; img-src 'self'; "
        "frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
    )
    return response


def create_corpus_blueprint(corpus_path=DEFAULT_CORPUS, reports_path=DEFAULT_REPORTS) -> Blueprint:
    """Register with url_prefix='/corpus'; creation performs no corpus or review IO."""
    blueprint = Blueprint("corpus_admin", __name__, template_folder="templates",
                          static_folder="static", static_url_path="/assets")
    store = CorpusStore(Path(corpus_path))
    reports = Path(reports_path).absolute()
    blueprint.after_request(_secure_response)

    @blueprint.context_processor
    def corpus_context():
        def page_url(page):
            return url_for(request.endpoint, **dict(request.view_args or {}),
                           **dict(request.args.to_dict(), page=page))
        return {"safe_external_url": safe_external_url, "quality_labels": QUALITY_LABELS,
                "pillars": PILLARS, "page_url": page_url,
                "has_review_surface": "review_refresh" in current_app.view_functions}

    @blueprint.errorhandler(CorpusAdminError)
    def corpus_error(error):
        current_app.logger.warning("Corpus administration failed: %s", error)
        return render_template("corpus_error.html", error=str(error)), (
            400 if isinstance(error, CorpusFilterError) else 503
        )

    @blueprint.get("/")
    def index():
        snapshot = store.get()
        return render_template("corpus_index.html", summary=snapshot.summary)

    @blueprint.get("/recommendations")
    def recommendations():
        summary = store.get().summary
        return render_template("corpus_recommendations.html", summary=summary,
                               filters=request.args, **_paginate(filtered_rows(summary)))

    @blueprint.get("/recommendations/<identity>")
    def recommendation(identity):
        snapshot = store.get()
        for row in snapshot.summary["rows"]:
            reco = row["recommendation"]
            if identity == reco["id"] or any(alias["id"] == identity for alias in reco.get("aliases", [])):
                return render_template("corpus_recommendation.html", row=row, requested_identity=identity)
        abort(404, "Unknown corpus recommendation identity.")

    @blueprint.get("/sources")
    def sources():
        snapshot = store.get()
        return render_template("corpus_sources.html", summary=snapshot.summary,
                               coverage=source_coverage(snapshot.recommendations, reports),
                               **_paginate(snapshot.summary["references"]))

    @blueprint.get("/sources/<source_id>")
    def source(source_id):
        coverage = source_coverage(store.get().recommendations, reports)
        if source_id in coverage["unknownSources"]:
            return render_template(
                "corpus_source.html",
                source={"sourceId": source_id, "title": source_id,
                        "error": "Unknown source ID in the central registry. Normalize or register it explicitly; "
                                 "no alias, uncovered count or source percentage has been inferred."},
            )
        for item in coverage["sources"]:
            if item["sourceId"] == source_id:
                allowed = {"state", "page"}
                if request.args.keys() - allowed or any(
                    len(request.args.getlist(key)) > 1 for key in allowed
                ):
                    raise CorpusFilterError("Use only one state and page per source drilldown.")
                state = request.args.get("state", "")
                if state not in {"", "full", "partial", "stale", "supporting", "unknown"}:
                    raise CorpusFilterError("Unknown upstream reconciliation state.")
                rows = [row for row in item.get("items", []) if not state or row["state"] == state]
                return render_template("corpus_source.html", source=item, state=state, **_paginate(rows))
        abort(404, "No recorded inventory or explicit mapping for this source.")

    @blueprint.get("/history")
    def history():
        return render_template("corpus_history.html", history=maintenance_history(reports))

    @blueprint.get("/reports/<name>")
    def report(name):
        try:
            path = public_report_path(reports, name)
            data = path.read_bytes()
        except (CorpusAdminError, OSError) as exc:
            current_app.logger.warning("Public corpus report unavailable: %s", exc)
            abort(404, "Public report is unavailable or not allowlisted.")
        if len(data) > MAX_REPORT_BYTES:
            abort(413, "Public report exceeds the 16 MiB limit.")
        response = Response(data, content_type="text/plain; charset=utf-8")
        response.headers["Content-Disposition"] = f'attachment; filename="{name}"'
        return response

    return blueprint


def load_source_registry() -> dict:
    """Use the maintenance tooling's read-only local registry loader, never its fetchers."""
    from review_checklists.source_audit import load_registry
    try:
        return load_registry()
    except (ValueError, OSError, UnicodeError) as exc:
        raise CorpusAdminError(f"Cannot read the central source registry: {exc}") from exc


def source_coverage(recommendations: list[dict], reports: Path) -> dict:
    """Adapter to the pure recorded-inventory reconciliation module."""
    from review_checklists.source_coverage import (
        SourceCoverageError, coverage_report, diff_inventories, validate_inventory,
    )

    directory = reports / "source-inventories"
    result = {"sources": [], "errors": [], "directory_present": directory.is_dir(),
              "unknownSources": {}}
    try:
        registry = load_source_registry()
    except CorpusAdminError as exc:
        result["errors"].append(str(exc))
        return result
    mapped = {reference["sourceId"] for reco in recommendations
              for reference in reco["provenance"].get("upstreamRecommendations", [])}
    inventories = {}
    histories = defaultdict(list)
    invalid_sources = {}

    def read_inventory(path: Path) -> dict:
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise CorpusAdminError("Inventory links must stay within the source-inventories directory.")
        if not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
            raise CorpusAdminError(f"Inventory is not a regular file or exceeds 16 MiB: {path.name}")
        text = path.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) > MAX_REPORT_BYTES:
            raise CorpusAdminError(f"Inventory exceeds 16 MiB: {path.name}")
        data = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise CorpusAdminError(f"{path.name}: inventory must be an object.")
        return data

    if directory.is_symlink() or not directory.resolve().is_relative_to(reports.resolve()):
        result["errors"].append("Source inventory directory must not link outside the public reports directory.")
    elif directory.exists() and not directory.is_dir():
        result["errors"].append("The source-inventories path is not a directory.")
    elif directory.is_dir():
        paths = sorted(directory.glob("*.json"))
        if len(paths) > 200:
            result["errors"].append("More than 200 inventory files; narrow the configured public reports directory.")
        else:
            for path in paths:
                inventory = {}
                try:
                    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", path.stem):
                        raise CorpusAdminError(f"Invalid source inventory filename: {path.name}")
                    inventory = read_inventory(path)
                    validate_inventory(inventory)
                    histories[inventory["sourceId"]].append((path.name, inventory))
                except (CorpusAdminError, SourceCoverageError, CorpusError, OSError, UnicodeError, ValueError) as exc:
                    result["errors"].append(f"{path.name}: {exc}")
                    source_id = inventory.get("sourceId")
                    if isinstance(source_id, str) and re.fullmatch(r"[a-z0-9][a-z0-9._-]*", source_id):
                        invalid_sources[source_id] = str(exc)

    def observed_at(entry):
        data = entry[1]
        retrieved = (datetime.fromisoformat(data["retrievedAt"].replace("Z", "+00:00"))
                     if data["retrievedAt"] else datetime.min.replace(tzinfo=timezone.utc))
        return data["asOf"] or "", retrieved

    for source_id, snapshots in sorted(histories.items()):
        if source_id not in registry:
            continue
        if source_id in invalid_sources:
            continue
        try:
            # Identical copied artifacts are one observation, not a second history event.
            unique = {}
            for name, inventory in snapshots:
                unique.setdefault(canonical_json(inventory), (name, inventory))
            snapshots = sorted(unique.values(), key=observed_at)
            if len({(entry["scope"], entry["unit"], entry["fingerprintScope"])
                    for _, entry in snapshots}) != 1:
                raise CorpusAdminError("Cannot compare inventories with different scope, unit or fingerprintScope.")
            if len(snapshots) > 1 and observed_at(snapshots[-1]) == observed_at(snapshots[-2]):
                raise CorpusAdminError("Conflicting inventories have the same observation date/time; reconcile them explicitly.")
            filename, inventory = snapshots[-1]
            for field in ("scope", "unit", "fingerprintScope"):
                if registry[source_id].get(field) and registry[source_id][field] != inventory[field]:
                    raise CorpusAdminError(f"Inventory {field} differs from the registered source scope.")
            coverage = coverage_report(inventory, recommendations)
            coverage.update(fingerprintScope=inventory["fingerprintScope"], comparison=None,
                            removedItems=[], inventoryFile=filename,
                            historyFiles=[name for name, _ in snapshots])
            if len(snapshots) > 1:
                previous = snapshots[-2][1]
                coverage["comparison"] = diff_inventories(previous, inventory)
                removed = set(coverage["comparison"]["removedIds"] or [])
                coverage["removedItems"] = [row for row in previous["items"] if row["id"] in removed]
            inventories[source_id] = coverage
        except (CorpusAdminError, SourceCoverageError, ValueError) as exc:
            result["errors"].append(f"{source_id}: {exc}")
            invalid_sources[source_id] = str(exc)
    for source_id, error in invalid_sources.items():
        if source_id not in registry:
            continue
        inventories[source_id] = {
            "sourceId": source_id, "title": source_id, "error": error,
            "coveragePercent": None, "denominator": None,
        }
    for source_id in sorted((mapped | histories.keys() | invalid_sources.keys()) - registry.keys()):
        result["unknownSources"][source_id] = {
            "corpusIds": sorted({
                reco["id"] for reco in recommendations
                if any(reference["sourceId"] == source_id
                       for reference in reco["provenance"].get("upstreamRecommendations", []))
            }),
            "inventoryFiles": [name for name, _ in histories.get(source_id, [])],
        }
    for source_id in sorted(registry.keys() - inventories.keys()):
        registered = registry[source_id]
        inventories[source_id] = {
            "sourceId": source_id, "title": registered["title"], "inventoryStatus": "missing",
            "scope": registered["scope"], "unit": registered["unit"], "asOf": None, "retrievedAt": None,
            "upstreamRevision": None, "sourceUrls": [], "observedCount": None,
            "denominator": None, "coveragePercent": None, "partialPercent": None,
            "counts": None, "items": [], "comparison": None, "limitations": [],
            "reason": registered.get("unsupportedReason") or "No local inventory recorded for this registered scope.",
            "referencesOutsideInventory": [],
        }
    result["sources"] = [inventories[key] for key in sorted(inventories)]
    return result


def create_app(corpus_path=DEFAULT_CORPUS, reports_path=DEFAULT_REPORTS) -> Flask:
    app = Flask(__name__)
    app.config["TRUSTED_HOSTS"] = ["127.0.0.1", "localhost", "[::1]"]
    app.register_blueprint(create_corpus_blueprint(corpus_path, reports_path), url_prefix="/corpus")
    app.after_request(_secure_response)

    @app.get("/")
    def index():
        return redirect(url_for("corpus_admin.index"))

    @app.errorhandler(HTTPException)
    def http_error(error):
        if isinstance(error, SecurityError):
            return error
        return render_template("corpus_error.html", error=error.description), error.code

    return app


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only public corpus administration on loopback.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    from waitress import serve
    logging.basicConfig(level=logging.INFO)
    print(f"Read-only corpus administration: http://127.0.0.1:{args.port}/corpus/")
    serve(create_app(args.corpus, args.reports), host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
