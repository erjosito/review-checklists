"""Auditable, offline service/type normalization: python -m review_checklists.service_normalization."""

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path

import yaml

from scripts.modules.cl_corpus import StrictLoader, json_value, validate_corpus
from scripts.modules.cl_services import (
    CATALOG_PATH, classify_applicability, normalize_resource_types, normalize_services,
)


FIELDS = ("services", "resourceTypes")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def document_hash(document: dict) -> str:
    return sha256(json.dumps(document, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8"))


def protected_hash(document: dict) -> str:
    return document_hash({key: value for key, value in document.items() if key not in FIELDS})


def normalized_document(document: dict) -> dict:
    result = deepcopy(document)
    for field, normalizer in (("services", normalize_services),
                              ("resourceTypes", normalize_resource_types)):
        if field in result:
            result[field] = normalizer(result[field])
    return result


def rewrite_fields(raw: bytes, before: dict, after: dict) -> tuple[bytes, list[dict]]:
    """Replace only top-level classification blocks, retaining all other bytes."""
    text = raw.decode("utf-8")
    node = yaml.compose(text, Loader=StrictLoader)
    edits = []
    for index, (key, value) in enumerate(node.value):
        field = key.value
        if field not in FIELDS or before.get(field) == after.get(field):
            continue
        start = key.start_mark.index
        end = node.value[index + 1][0].start_mark.index if index + 1 < len(node.value) else value.end_mark.index
        replacement = yaml.safe_dump({field: after[field]}, sort_keys=False, allow_unicode=True)
        if "\r\n" in text:
            replacement = replacement.replace("\n", "\r\n")
        edits.append({"field": field, "start": start, "before": text[start:end], "after": replacement})
    for edit in reversed(edits):
        text = text[:edit["start"]] + edit["after"] + text[edit["start"] + len(edit["before"]):]
    parsed = json_value(yaml.load(text, Loader=StrictLoader))
    if parsed != after or protected_hash(before) != protected_hash(parsed):
        raise ValueError("Normalization changed fields outside services/resourceTypes")
    return text.encode("utf-8"), edits


def build_plan(root: Path) -> dict:
    records, inventory, diagnostics, documents = [], [], [], []
    counts = Counter()
    for path in sorted((root / "v2" / "recos").rglob("*.yaml")):
        raw = path.read_bytes()
        before = json_value(yaml.load(raw.decode("utf-8"), Loader=StrictLoader))
        after = normalized_document(before)
        documents.append(after)
        relative = path.relative_to(root).as_posix()
        inventory.append({"id": before["id"], "path": relative, "sha256": sha256(raw)})
        result = classify_applicability(after)
        counts[result["classification"]] += 1
        for key in ("missingFields", "unknownServices", "unknownResourceTypes",
                    "ambiguousResourceTypes", "possibleContradictions"):
            counts[key] += bool(result[key])
        diagnostics.append({"id": before["id"], "path": relative, **result})
        if before == after:
            continue
        new_raw, edits = rewrite_fields(raw, before, after)
        changed = [field for field in FIELDS if before.get(field) != after.get(field)]
        for field in changed:
            counts[f"{field}Changed"] += 1
        records.append({
            "id": before["id"], "path": relative, "changedFields": changed,
            "before": {field: before[field] for field in FIELDS},
            "after": {field: after[field] for field in FIELDS},
            "beforeFileSha256": sha256(raw), "afterFileSha256": sha256(new_raw),
            "beforeDocumentSha256": document_hash(before),
            "afterDocumentSha256": document_hash(after),
            "protectedFieldsSha256": protected_hash(before), "edits": edits,
        })
    validate_corpus(documents)
    return {
        "schemaVersion": 1, "stage": "service-normalization", "status": "planned",
        "assessedAt": date.today().isoformat(), "catalogueSha256": sha256(CATALOG_PATH.read_bytes()),
        "scope": "Only service aliases/display labels and ARM type whitespace/case/order/deduplication.",
        "limitations": [
            "Empty services remain uncurated. Type candidates are not curated classifications.",
            "Possible contradictions and unknown types require human review, not automatic repair.",
            "No guidance, KQL, identity, source, provenance, or aliases changed; no live validation.",
        ],
        "summary": {"canonical": len(documents), "aliases": sum(len(d.get("aliases", [])) for d in documents),
                    "changed": len(records), "unchanged": len(documents) - len(records), **dict(counts)},
        "corpusBefore": inventory, "records": records, "classifications": diagnostics,
    }


def apply_plan(root: Path, plan: dict) -> dict:
    if plan.get("status") != "planned" or plan != build_plan(root):
        raise ValueError("Plan is stale, modified, or already applied; generate and review a new dry run")
    writes = []
    for row in plan["records"]:
        path = root / Path(row["path"])
        before = json_value(yaml.load(path.read_text(encoding="utf-8"), Loader=StrictLoader))
        raw, _ = rewrite_fields(path.read_bytes(), before, normalized_document(before))
        if sha256(raw) != row["afterFileSha256"]:
            raise ValueError(f"After hash mismatch: {row['id']}")
        writes.append((path, raw, path.read_bytes()))
    written = []
    try:
        for path, raw, old in writes:
            path.write_bytes(raw)
            written.append((path, old))
    except OSError:
        for path, old in reversed(written):
            path.write_bytes(old)
        raise
    result = deepcopy(plan)
    result["status"] = "applied"
    return result


def replay_normalization(document: dict, report: dict, *, reverse: bool = False) -> dict:
    """Replay recorded fields only, with exact preconditions (also for historical tests)."""
    result = deepcopy(document)
    for row in report["records"]:
        if row["id"] != result.get("id"):
            continue
        source, target = ("after", "before") if reverse else ("before", "after")
        if any(result.get(field) != row[source][field] for field in FIELDS):
            raise ValueError(f"Classification replay precondition failed: {row['id']}")
        result.update(deepcopy(row[target]))
        break
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path, required=True, help="Fresh JSON output path (never overwritten)")
    parser.add_argument("--apply-plan", type=Path, help="Apply a previously inspected dry-run JSON")
    args = parser.parse_args(argv)
    try:
        if args.report.exists():
            raise ValueError(f"Output already exists: {args.report}")
        if not args.report.parent.is_dir():
            raise ValueError(f"Output directory does not exist: {args.report.parent}")
        plan = (json.loads(args.apply_plan.read_text(encoding="utf-8"))
                if args.apply_plan else build_plan(args.root))
        # Reserve the report before modifying the corpus, so failed saves cannot look successful.
        with args.report.open("x", encoding="utf-8") as output:
            result = apply_plan(args.root, plan) if args.apply_plan else plan
            json.dump(result, output, indent=2, ensure_ascii=False)
            output.write("\n")
        print(json.dumps({"status": result["status"], **result["summary"]}, indent=2))
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.exit(1, f"Service normalization failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
