"""Deterministic corpus distribution and conservative metadata migration."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tempfile

from jsonschema import Draft202012Validator
import yaml

from scripts.modules.cl_corpus import (
    CorpusError, StrictLoader, enrich_recommendation, json_value, load_yaml_document, validate_corpus,
)

from review_checklists.corpus import load_corpus


BUNDLE_SCHEMA = Path(__file__).resolve().parent / "schema" / "corpus-bundle.schema.json"


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(recommendations: list[dict]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(recommendations).encode("utf-8")).hexdigest()


def make_bundle(recommendations: list[dict], version: str) -> dict:
    if not version.strip() or len(version) > 200:
        raise CorpusError("A nonempty corpus version of at most 200 characters is required")
    records = [
        {key: value for key, value in reco.items() if key != "corpus_file"}
        for reco in recommendations
    ]
    validate_corpus(records)
    records.sort(key=lambda reco: reco["id"])
    return {
        "schemaVersion": 1,
        "corpusVersion": version,
        "contentHash": content_hash(records),
        "recommendations": records,
    }


def build_bundle(root: Path, version: str, output: Path) -> dict:
    if output.resolve().is_relative_to(root.resolve()):
        raise CorpusError("Generated bundles must be outside the authoring corpus directory")
    bundle = make_bundle(load_corpus(root, require_current=True), version)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return bundle


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise CorpusError(f"Invalid JSON constant: {value}")


def read_bundle(path: Path) -> dict:
    try:
        bundle = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        schema = json.loads(BUNDLE_SCHEMA.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CorpusError(f"Cannot read corpus bundle {path}: {exc}") from exc
    errors = list(Draft202012Validator(schema).iter_errors(bundle))
    if errors:
        raise CorpusError(f"Invalid corpus bundle: {errors[0].message}")
    validate_corpus(bundle["recommendations"])
    if content_hash(bundle["recommendations"]) != bundle["contentHash"]:
        raise CorpusError("Corpus bundle contentHash does not match its recommendation content")
    return bundle


def migrated_yaml(original: str, before: dict, after: dict) -> str:
    """Append metadata without rewriting titles, descriptions, KQL or comments."""
    removed = set(before) - set(after)
    if removed - {"filepath", "corpus_file"}:
        raise CorpusError("Migration would remove non-transient fields")
    for key in before.keys() & after.keys():
        if before[key] != after[key]:
            raise CorpusError(f"Partially migrated field {key!r} needs an explicit author edit")
    text = original
    for key in removed:
        lines = text.splitlines(keepends=True)
        matching = [index for index, line in enumerate(lines) if line.startswith(key + ":")]
        if len(matching) != 1:
            raise CorpusError(f"Cannot surgically remove transient field {key!r}")
        index = matching[0]
        if index + 1 < len(lines) and lines[index + 1].startswith((" ", "\t")):
            raise CorpusError(f"Multiline transient field {key!r} needs an explicit author edit")
        text = "".join(lines[:index] + lines[index + 1:])
    additions = {key: value for key, value in after.items() if key not in before}
    if additions:
        newline = "\r\n" if "\r\n" in original else "\n"
        extra = yaml.safe_dump(additions, sort_keys=False, allow_unicode=True).replace("\n", newline)
        footer = ""
        end_marker = re.search(r"(?m)^\.\.\.(?:[ \t]+#[^\r\n]*)?[ \t]*\r?$", text)
        if end_marker:
            text, footer = text[:end_marker.start()], text[end_marker.start():]
        text = text + ("" if not text or text.endswith("\n") else newline) + extra + footer
    parsed = json_value(yaml.load(text, Loader=StrictLoader))
    if parsed != after:
        raise CorpusError("Migration would change recommendation content beyond the planned metadata")
    return text


def migrate_corpus(root: Path, *, write: bool = False) -> dict:
    if not root.is_dir():
        raise CorpusError(f"Corpus directory does not exist: {root}")
    plans = []
    recos = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        original_bytes = path.read_bytes()
        original = original_bytes.decode("utf-8")
        before = load_yaml_document(path)
        after = enrich_recommendation(before)
        updated = migrated_yaml(original, before, after).encode("utf-8")
        if original_bytes != updated:
            plans.append((path, original_bytes, updated))
        recos.append(after)
    validate_corpus(recos)
    if write:
        for path, original, _ in plans:
            if path.read_bytes() != original:
                raise CorpusError(f"File changed during migration preflight: {path}")
        for path, original, updated in plans:
            if path.read_bytes() != original:
                raise CorpusError(f"File changed during migration: {path}")
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".corpus-", delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(updated)
                temporary.replace(path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    return {
        "recommendations": len(recos),
        "files_changed" if write else "files_to_change": len(plans),
        "automation": dict(sorted(Counter(reco["automation"]["status"] for reco in recos).items())),
        "mode": "write" if write else "dry-run",
    }
