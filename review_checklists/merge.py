"""Apply reviewed duplicate-merge manifests without losing retired identities."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

import yaml

from scripts.modules.cl_corpus import (
    CorpusError, StrictLoader, dump_recommendation, json_value, validate_corpus,
)

from review_checklists.catalog import canonical_json, content_hash, reject_constant, unique_object


def _groups(groups):
    if not isinstance(groups, list) or not groups:
        raise CorpusError("Merge groups must be a nonempty array")
    for group in groups:
        if not isinstance(group, dict):
            raise CorpusError("Each merge group must be an object")
        unknown = group.keys() - {
            "canonicalId", "retiredIds", "reason", "description", "beforeContentHash",
        }
        if unknown:
            raise CorpusError(f"Unsupported merge group fields: {', '.join(sorted(unknown))}")
        if not isinstance(group.get("canonicalId"), str) or not group["canonicalId"].strip():
            raise CorpusError("Each merge group needs a canonicalId")
        retired = group.get("retiredIds")
        if not isinstance(retired, list) or not retired or not all(
            isinstance(value, str) and value.strip() for value in retired
        ):
            raise CorpusError("Each merge group needs a nonempty retiredIds list")
        if not isinstance(group.get("reason"), str) or not group["reason"].strip():
            raise CorpusError("Each merge group needs its confirmation rationale")
        if "description" in group and not isinstance(group["description"], str):
            raise CorpusError("Merged description must be text")
        if "beforeContentHash" in group and (
            not isinstance(group["beforeContentHash"], str)
            or len(group["beforeContentHash"]) != 71
            or not group["beforeContentHash"].startswith("sha256:")
            or any(c not in "0123456789abcdef" for c in group["beforeContentHash"][7:])
        ):
            raise CorpusError("beforeContentHash must be a lowercase sha256 content hash")
    return groups


def read_merge_manifest(path: Path) -> list[dict]:
    """Read a strict JSON approval manifest, rejecting ambiguous or misspelled fields."""
    try:
        manifest = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise CorpusError(f"Cannot read merge manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict) or set(manifest) != {"groups"}:
        raise CorpusError("Merge manifest must contain only a groups array")
    return _groups(manifest["groups"])


def _paths(root):
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in {".yaml", ".yml", ".json"})


def _safe_path(root, path):
    return path.resolve().is_relative_to(root) and not any(
        parent.is_symlink() for parent in [path, *path.parents] if parent.is_relative_to(root)
    )


def _snapshot(root):
    if not root.is_dir():
        raise CorpusError(f"Corpus directory does not exist: {root}")
    records, originals = [], {}
    try:
        for path in _paths(root):
            if not _safe_path(root, path):
                raise CorpusError(f"Symlinked or external corpus path is not supported: {path}")
            original = path.read_bytes()
            reco = json_value(yaml.load(original.decode("utf-8"), Loader=StrictLoader))
            if not isinstance(reco, dict) or "schemaVersion" not in reco:
                raise CorpusError(f"{path}: expected a versioned recommendation object")
            records.append(reco)
            originals[path] = original
        validate_corpus(records)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CorpusError(f"Cannot snapshot corpus {root}: {exc}") from exc
    for reco, path in zip(records, originals, strict=True):
        reco["corpus_file"] = path.relative_to(root).as_posix()
    return records, originals


def _scope(reco: dict):
    return (
        reco.get("waf"), reco["severity"],
        frozenset(value.casefold() for value in reco.get("resourceTypes", [])),
        frozenset(value.casefold() for value in reco.get("services", [])),
        canonical_json(reco.get("constraints", [])),
        canonical_json({key: value for key, value in reco.get("labels", {}).items() if key != "guid"}),
        reco["source"]["type"],
    )


def _preflight(root, originals):
    if set(_paths(root)) != set(originals):
        raise CorpusError("Corpus files changed during merge preflight")
    for path, original in originals.items():
        if not _safe_path(root, path) or path.read_bytes() != original:
            raise CorpusError(f"File changed during merge preflight: {path}")


def _stage(path, content, mode):
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)


def _commit(root, originals, updates):
    """Stage all bytes first; roll back handled failures without overwriting concurrent edits."""
    directory = Path(tempfile.mkdtemp(prefix=".corpus-merge-", dir=root.parent))
    backups, staged, applied = {}, {}, []
    preserve_backups = False
    try:
        for index, (path, updated) in enumerate(updates.items()):
            mode = stat.S_IMODE(path.stat().st_mode)
            backups[path] = directory / f"{index}.original"
            _stage(backups[path], originals[path], mode)
            if updated is not None:
                staged[path] = directory / f"{index}.updated"
                _stage(staged[path], updated, mode)
        _preflight(root, originals)
        for path, updated in updates.items():
            if path.is_symlink() or path.read_bytes() != originals[path]:
                raise CorpusError(f"File changed during merge: {path}")
            if updated is None:
                os.replace(path, backups[path])
            else:
                os.replace(staged[path], path)
            applied.append(path)
        for path, updated in updates.items():
            if (updated is None and path.exists()) or (
                updated is not None and path.read_bytes() != updated
            ):
                raise CorpusError(f"File changed after merge write: {path}")
        _snapshot(root)
    except (OSError, CorpusError) as exc:
        failures = []
        for path in reversed(applied):
            try:
                expected = updates[path]
                if path.is_symlink() or (
                    path.exists() if expected is None else not path.exists() or path.read_bytes() != expected
                ):
                    raise CorpusError(f"Concurrent edit prevents safe rollback: {path}")
                os.replace(backups[path], path)
            except (OSError, CorpusError) as rollback_exc:
                failures.append(str(rollback_exc))
        preserve_backups = bool(failures)
        detail = (
            f" Rollback incomplete; original-byte backups retained at {directory}: {'; '.join(failures)}"
            if failures else " All applied changes were rolled back."
        )
        raise CorpusError(f"Merge write failed: {exc}.{detail}") from exc
    finally:
        if not preserve_backups:
            for path in directory.iterdir():
                path.unlink()
            directory.rmdir()


def merge_confirmed(root: Path, groups: list[dict], *, write: bool = False) -> dict:
    groups = _groups(groups)
    root = root.resolve()
    records, originals = _snapshot(root)
    by_id = {record["id"]: record for record in records}
    involved = set()
    replacements = {}
    removed = set()
    audit = []
    for group in groups:
        canonical_id = group.get("canonicalId")
        retired = group["retiredIds"]
        ids = [canonical_id, *retired]
        if any(not isinstance(value, str) or value not in by_id for value in ids):
            raise CorpusError("Merge groups must reference existing canonical recommendation IDs")
        if len(set(ids)) != len(ids) or involved.intersection(ids):
            raise CorpusError("A recommendation cannot participate in overlapping merge groups")
        involved.update(ids)
        members = [by_id[value] for value in ids]
        before_hash = content_hash([
            {key: value for key, value in member.items() if key != "corpus_file"}
            for member in members
        ])
        if "beforeContentHash" in group and group["beforeContentHash"] != before_hash:
            raise CorpusError(f"Merge {canonical_id} does not match its approved beforeContentHash")
        if any(_scope(member) != _scope(members[0]) for member in members[1:]):
            raise CorpusError(f"Merge {canonical_id} would change WAF, severity, resource/service applicability, constraints, labels or source type")
        for field in ("queries", "automation", "automatable", "reviewedDate", "duplicates"):
            if any(member.get(field) != members[0].get(field) for member in members[1:]):
                raise CorpusError(f"Merge {canonical_id} has conflicting {field}; defer for author review")
        for field in ("upstreamRevision", "lastReviewed"):
            if any(member["provenance"].get(field) != members[0]["provenance"].get(field) for member in members[1:]):
                raise CorpusError(f"Merge {canonical_id} has conflicting provenance.{field}; defer for author review")
        merged = deepcopy(members[0])
        descriptions = {member.get("description", "") for member in members} - {""}
        if "description" in group:
            if any(description not in group["description"] for description in descriptions):
                raise CorpusError(f"Merge {canonical_id} description would remove original evidence")
            merged["description"] = group["description"]
        elif len(descriptions) > 1:
            raise CorpusError(f"Merge {canonical_id} needs an explicitly reconciled description")
        elif descriptions:
            merged["description"] = next(iter(descriptions))
        links = {}
        sources = {}
        upstream = {}
        aliases = []
        for member in members:
            for link in member.get("links", []):
                links[canonical_json(link)] = link
            for source in member["provenance"]["sources"]:
                if source["url"] in sources and sources[source["url"]] != source:
                    raise CorpusError(f"Merge {canonical_id} has conflicting provenance for {source['url']}")
                sources[source["url"]] = source
            for reference in member["provenance"].get("upstreamRecommendations", []):
                key = (reference["sourceId"], reference["recommendationId"])
                if key in upstream and upstream[key] != reference:
                    raise CorpusError(
                        f"Merge {canonical_id} has conflicting upstream mapping {key[0]}/{key[1]}; "
                        "defer for author review"
                    )
                upstream[key] = reference
            aliases.extend(member.get("aliases", []))
            if member["id"] != canonical_id:
                aliases.append({
                    "id": member["id"], "name": member["name"],
                    "source": member["source"], "labels": member.get("labels", {}),
                    "corpusFile": member["corpus_file"],
                })
        merged["links"] = list(links.values())
        merged["aliases"] = aliases
        merged["provenance"]["sources"] = list(sources.values())
        if upstream:
            merged["provenance"]["upstreamRecommendations"] = list(upstream.values())
        merged.pop("corpus_file")
        replacements[canonical_id] = merged
        removed.update(retired)
        audit.append({
            "canonicalId": canonical_id, "retiredIds": retired, "reason": group["reason"],
            "beforeContentHash": before_hash,
            "afterContentHash": content_hash([merged]),
            "aliases": aliases,
            "originalRecommendations": [
                {key: value for key, value in member.items() if key != "corpus_file"}
                for member in members
            ],
            "originalFiles": [
                {"id": member["id"], "path": member["corpus_file"],
                 "sha256": hashlib.sha256(originals[root / member["corpus_file"]]).hexdigest()}
                for member in members
            ],
        })
    final = [
        replacements.get(record["id"], {key: value for key, value in record.items() if key != "corpus_file"})
        for record in records if record["id"] not in removed
    ]
    validate_corpus(final)
    updates = {}
    for identifier in sorted(involved, key=lambda value: (value in removed, value)):
        path = root / Path(by_id[identifier]["corpus_file"])
        updates[path] = (
            dump_recommendation(replacements[identifier]).encode("utf-8")
            if identifier in replacements else None
        )
    _preflight(root, originals)
    if write:
        _commit(root, originals, updates)
    return {
        "mode": "write" if write else "dry-run",
        "before": len(records), "after": len(final), "retired": len(removed),
        "groups": audit,
    }
