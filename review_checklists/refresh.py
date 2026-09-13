"""Preview-first, transactional refresh of a review's recommendation snapshots."""

from copy import deepcopy
from contextlib import closing
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from jsonschema import Draft202012Validator

from review_checklists.catalog import BUNDLE_SCHEMA, canonical_json, content_hash
from review_checklists.corpus import ReviewError, select_checklist
from review_checklists.review import utc_now
from scripts.modules.cl_corpus import CorpusError, validate_corpus
from scripts.modules.cl_services import normalize_resource_types, normalize_services


REFRESH_SCHEMA_VERSION = 2
SEMANTIC_FIELDS = (
    "title", "description", "severity", "waf", "resourceTypes", "services",
    "constraints", "queries",
)


class RefreshConflict(ReviewError):
    """The review, target bundle, or refresh options changed after preview."""


def validate_bundle(bundle: dict) -> dict:
    """Copy and revalidate even previously validated, mutable caller input."""
    try:
        bundle = deepcopy(bundle)
        schema = json.loads(BUNDLE_SCHEMA.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(bundle))
        if errors:
            raise CorpusError(f"Invalid corpus bundle: {errors[0].message}")
        validate_corpus(bundle["recommendations"])
        if content_hash(bundle["recommendations"]) != bundle["contentHash"]:
            raise CorpusError("Corpus bundle contentHash does not match its recommendation content")
        return bundle
    except (CorpusError, ValueError, TypeError) as exc:
        raise ReviewError(f"Cannot refresh: {exc}") from exc


def validate_scope(scope: dict | None) -> dict:
    if scope is None:
        return {"kind": "unknown"}
    if not isinstance(scope, dict):
        raise ReviewError("Refresh scope must be an object")
    kind = scope.get("kind")
    if kind in ("all", "unknown") and set(scope) == {"kind"}:
        return deepcopy(scope)
    if kind == "checklist" and set(scope) == {"kind", "definition"}:
        if isinstance(scope["definition"], dict):
            # Validate selector structure even when no recommendation matches.
            select_checklist([], scope["definition"], allow_empty=True)
            return deepcopy(scope)
    raise ReviewError("Scope must be {kind: all}, {kind: unknown}, or a checklist definition")


def ensure_schema(connection) -> None:
    """Called only inside explicit create/refresh transactions, never on open."""
    connection.execute(
        "CREATE TABLE IF NOT EXISTS refresh_item_state "
        "(item_id TEXT PRIMARY KEY, state TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS refresh_history "
        "(refresh_id TEXT PRIMARY KEY, applied_at TEXT NOT NULL, record TEXT NOT NULL)"
    )
    connection.execute(f"PRAGMA user_version = {REFRESH_SCHEMA_VERSION}")


def _has_table(connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,),
    ).fetchone() is not None


def _baseline(metadata: dict) -> dict:
    return {
        "version": metadata.get("corpus_version"),
        "content_hash": metadata.get("corpus_content_hash"),
        "snapshot_hash": metadata.get("baseline_snapshot_hash", metadata.get("corpus_sha256")),
    }


def default_item_state(item_id: str, metadata: dict) -> dict:
    return {
        "currency": "current", "canonical_id": item_id,
        "needs_reassessment": False, "source": _baseline(metadata),
    }


def item_states(connection, metadata: dict | None = None) -> dict:
    metadata = metadata if metadata is not None else dict(
        connection.execute("SELECT key, value FROM metadata")
    )
    states = {
        row[0]: default_item_state(row[0], metadata)
        for row in connection.execute("SELECT id FROM items")
    }
    if _has_table(connection, "refresh_item_state"):
        states.update({
            row["item_id"]: json.loads(row["state"])
            for row in connection.execute("SELECT item_id, state FROM refresh_item_state")
        })
    return states


def item_state(connection, item_id: str) -> dict:
    if _has_table(connection, "refresh_item_state"):
        row = connection.execute(
            "SELECT state FROM refresh_item_state WHERE item_id = ?", (item_id,),
        ).fetchone()
        if row is not None:
            return json.loads(row[0])
    return default_item_state(item_id, dict(connection.execute("SELECT key, value FROM metadata")))


def acknowledge_assessment(connection, item_id: str) -> None:
    """Use inside the same optimistic assessment-update transaction."""
    if not _has_table(connection, "refresh_item_state"):
        return
    state = item_state(connection, item_id)
    if state["needs_reassessment"]:
        state["needs_reassessment"] = False
        state["assessment_confirmed_at"] = utc_now()
        connection.execute(
            "UPDATE refresh_item_state SET state = ? WHERE item_id = ?",
            (canonical_json(state), item_id),
        )


def refresh_history(connection) -> list[dict]:
    if not _has_table(connection, "refresh_history"):
        return []
    return [
        json.loads(row[0]) for row in connection.execute(
            "SELECT record FROM refresh_history ORDER BY applied_at, refresh_id"
        )
    ]


def _snapshot(connection) -> dict:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version not in (1, REFRESH_SCHEMA_VERSION):
        raise ReviewError(f"Unsupported review schema {version}; reopen with a compatible application.")
    tables = {}
    for name, order in (
        ("metadata", "key"), ("items", "id"), ("evidence", "run_id"),
        ("refresh_item_state", "item_id"), ("refresh_history", "refresh_id"),
    ):
        tables[name] = (
            [dict(row) for row in connection.execute(f"SELECT * FROM {name} ORDER BY {order}")]
            if _has_table(connection, name) else None
        )
    return {"schema_version": version, **tables}


def _hash(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _semantics(reco: dict) -> dict:
    result = {key: reco.get(key) for key in SEMANTIC_FIELDS}
    result["services"] = sorted({value.casefold() for value in normalize_services(reco.get("services", []))})
    result["resourceTypes"] = normalize_resource_types(reco.get("resourceTypes", []))
    result["constraints"] = reco.get("constraints", [])
    result["description"] = reco.get("description", "")
    result["queries"] = reco.get("queries", {})
    automation = reco.get("automation", {})
    result["resultSemantics"] = automation.get("resultSemantics", "unknown")
    result["complianceColumn"] = automation.get("complianceColumn")
    result["automationNotes"] = automation.get("notes")
    return result


def _metadata_json(metadata: dict, key: str):
    try:
        return json.loads(metadata[key])
    except (TypeError, ValueError) as exc:
        raise ReviewError(f"Invalid saved {key} metadata; inspect the review before refreshing.") from exc


def _plan(connection, bundle: dict, *, add_new: bool, scope: dict | None) -> dict:
    snapshot = _snapshot(connection)
    metadata = {row["key"]: row["value"] for row in snapshot["metadata"]}
    saved_scope = validate_scope(_metadata_json(metadata, "review_scope") if "review_scope" in metadata else None)
    effective_scope = validate_scope(scope) if scope is not None else saved_scope
    if add_new and effective_scope["kind"] == "unknown":
        raise ReviewError("Review scope is unknown. Use --checklist or --all-corpus with --add-new.")
    if not isinstance(add_new, bool):
        raise ReviewError("add_new must be a boolean")
    source = _metadata_json(metadata, "last_applied_source") if "last_applied_source" in metadata else _baseline(metadata)
    if not isinstance(source, dict):
        raise ReviewError("Invalid saved last_applied_source metadata; inspect the review before refreshing.")
    target = {"version": bundle["corpusVersion"], "content_hash": bundle["contentHash"]}
    records = {reco["id"]: reco for reco in bundle["recommendations"]}
    aliases = {
        alias["id"]: reco["id"]
        for reco in bundle["recommendations"] for alias in reco.get("aliases", [])
    }
    selected = {}
    if effective_scope["kind"] == "all":
        selected = records
    elif effective_scope["kind"] == "checklist":
        selected = {reco["id"]: reco for reco in select_checklist(
            bundle["recommendations"], effective_scope["definition"], allow_empty=True,
        )}
    old_states = item_states(connection, metadata)
    changes = []
    counts = {key: 0 for key in ("unchanged", "updated", "removed", "superseded", "added", "needs_reassessment")}
    existing_ids = {row["id"] for row in snapshot["items"]}
    groups = {}
    for row in snapshot["items"]:
        item_id = row["id"]
        before = json.loads(row["recommendation"])
        old_state = old_states[item_id]
        state = deepcopy(old_state)
        if item_id in records:
            after = deepcopy(records[item_id])
            for key in ("area", "subarea", "corpus_file"):
                if key in before:
                    after[key] = before[key]
            state.update(currency="current", canonical_id=item_id)
            action = "updated"
            if after != before:
                state["source"] = target
        else:
            after = before
            canonical = aliases.get(item_id)
            state.update(
                currency="superseded" if canonical else "no-longer-current",
                canonical_id=canonical,
            )
            action = "superseded" if canonical else "removed"
        canonical = state["canonical_id"]
        if canonical is not None:
            groups.setdefault(canonical, []).append(item_id)
        relevant = _semantics(before) != _semantics(after)
        if relevant and row["status"] != "Not reviewed":
            state["needs_reassessment"] = True
        if state["needs_reassessment"]:
            counts["needs_reassessment"] += 1
        if before == after and state == old_state:
            counts["unchanged"] += 1
            continue
        counts[action] += 1
        changes.append({
            "id": item_id, "action": action, "canonical_id": canonical,
            "assessment_relevant": relevant, "needs_reassessment": state["needs_reassessment"],
            "changed_fields": sorted(
                key for key in before.keys() | after.keys() if before.get(key) != after.get(key)
            ),
            "before": before, "after": after, "previous_state": old_state, "state": state,
        })
    candidates = sorted(set(selected) - existing_ids)
    if add_new:
        for item_id in candidates:
            state = default_item_state(item_id, {})
            state["source"] = target
            changes.append({
                "id": item_id, "action": "added", "canonical_id": item_id,
                "assessment_relevant": False, "needs_reassessment": False,
                "changed_fields": [], "before": None, "after": selected[item_id],
                "previous_state": None, "state": state,
            })
            counts["added"] += 1
            groups.setdefault(item_id, []).append(item_id)
    consolidations = [
        {"canonical_id": canonical, "item_ids": sorted(ids)}
        for canonical, ids in sorted(groups.items()) if len(ids) > 1
    ]
    source_changed = any(source.get(key) != target[key] for key in target)
    plan = {
        "plan_version": 1, "review_id": metadata.get("review_id"),
        "review_fingerprint": _hash(snapshot), "source": source, "target": target,
        "counts": counts, "changes": changes, "consolidations": consolidations,
        "scope": {
            "saved": saved_scope, "effective": effective_scope, "explicit": scope is not None,
            "add_new": add_new, "candidate_ids": candidates,
            "skipped_new": 0 if add_new else len(candidates),
        },
        "has_changes": bool(changes or source_changed or effective_scope != saved_scope),
    }
    plan["token"] = _hash(plan)
    return plan


def plan_refresh(review, bundle: dict, *, add_new: bool = False, scope: dict | None = None) -> dict:
    bundle = validate_bundle(bundle)
    with review.connection() as connection:
        connection.execute("PRAGMA query_only = ON")
        connection.execute("BEGIN")
        return _plan(connection, bundle, add_new=add_new, scope=scope)


def _backup(review, backup_path: Path) -> None:
    """Back up committed SQLite pages while the apply connection holds the writer lock."""
    with backup_path.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(
            review.path.as_uri() + "?mode=ro", uri=True, timeout=10,
        )) as source, closing(sqlite3.connect(backup_path)) as destination:
            source.backup(destination)
    except (OSError, sqlite3.Error):
        backup_path.unlink(missing_ok=True)
        raise


def apply_refresh(
    review, bundle: dict, *, token: str, add_new: bool = False, scope: dict | None = None,
) -> dict:
    bundle = validate_bundle(bundle)
    backup_path = None
    try:
        with review.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            plan = _plan(connection, bundle, add_new=add_new, scope=scope)
            if (
                not isinstance(token, str) or not token.isascii()
                or not hmac.compare_digest(plan["token"], token)
            ):
                raise RefreshConflict("Refresh preview is stale or options changed. Preview again before applying.")
            if not plan["has_changes"]:
                return {"applied": False, "plan": plan, "backup_path": None, "refresh_id": None}
            refresh_id = str(uuid4())
            backup_path = review.path.with_name(f"{review.path.name}.before-refresh-{refresh_id}.sqlite3")
            _backup(review, backup_path)
            ensure_schema(connection)
            for change in plan["changes"]:
                item_id = change["id"]
                if change["action"] == "added":
                    connection.execute(
                        "INSERT INTO items (id, recommendation) VALUES (?, ?)",
                        (item_id, canonical_json(change["after"])),
                    )
                else:
                    connection.execute(
                        "UPDATE items SET recommendation = ?, revision = revision + 1 WHERE id = ?",
                        (canonical_json(change["after"]), item_id),
                    )
                connection.execute(
                    "INSERT INTO refresh_item_state VALUES (?, ?) ON CONFLICT(item_id) "
                    "DO UPDATE SET state = excluded.state",
                    (item_id, canonical_json(change["state"])),
                )
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            recommendations = [
                json.loads(row[0]) for row in connection.execute("SELECT recommendation FROM items ORDER BY id")
            ]
            updates = {
                "baseline_snapshot_hash": metadata.get("baseline_snapshot_hash", metadata.get("corpus_sha256", "")),
                "reviewed_snapshot_hash": content_hash(recommendations),
                "last_applied_source": canonical_json(plan["target"]),
                "guidance_origin": "per-item; last_applied_source is not every item's origin",
            }
            if "review_scope" not in metadata or plan["scope"]["effective"] != plan["scope"]["saved"]:
                updates["review_scope"] = canonical_json(plan["scope"]["effective"])
            connection.executemany(
                "INSERT INTO metadata VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                updates.items(),
            )
            record = {
                "refresh_id": refresh_id, "applied_at": utc_now(), "backup_path": str(backup_path),
                "plan": plan, "reviewed_snapshot_hash": updates["reviewed_snapshot_hash"],
            }
            connection.execute(
                "INSERT INTO refresh_history VALUES (?, ?, ?)",
                (refresh_id, record["applied_at"], canonical_json(record)),
            )
        return {"applied": True, "plan": plan, "backup_path": str(backup_path), "refresh_id": refresh_id}
    except (OSError, sqlite3.Error) as exc:
        backup = f" Consistent pre-refresh backup: {backup_path}." if backup_path and backup_path.exists() else ""
        raise ReviewError(f"Refresh failed; no changes were committed. Check storage/permissions and retry.{backup} {exc}") from exc
