"""Verify and reverse recorded public corpus file changes without writing files."""

from datetime import date
import hashlib
import json
from pathlib import Path, PurePosixPath

from review_checklists.catalog import reject_constant, unique_object
from scripts.modules.cl_corpus import CorpusError


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_stage(stage: dict) -> None:
    if (not isinstance(stage, dict) or type(stage.get("schemaVersion")) is not int
            or stage["schemaVersion"] != 1 or stage.get("status") != "applied"):
        raise CorpusError("Corpus history requires an applied schemaVersion 1 stage")
    if not isinstance(stage.get("stage"), str) or not stage["stage"].strip():
        raise CorpusError("Corpus history stage identity is missing")
    try:
        if date.fromisoformat(stage["assessedAt"]).isoformat() != stage["assessedAt"]:
            raise ValueError("Date must use YYYY-MM-DD")
    except (KeyError, TypeError, ValueError) as exc:
        raise CorpusError("Corpus history assessment date is invalid") from exc
    if not isinstance(stage.get("files"), list):
        raise CorpusError("Corpus history file changes are missing")
    paths = set()
    for change in stage["files"]:
        if not isinstance(change, dict) or not isinstance(change.get("path"), str):
            raise CorpusError("Corpus history contains an invalid file change")
        name = change["path"]
        path = PurePosixPath(name)
        if (path.as_posix() != name or "\\" in name or path.is_absolute()
                or ".." in path.parts or ":" in name
                or not (name == "scripts/service_dictionary.json"
                        or (path.parts[:2] == ("v2", "recos") and path.suffix == ".yaml"))):
            raise CorpusError(f"Corpus history path is outside the authoring scope: {name}")
        if name in paths:
            raise CorpusError(f"Corpus history repeats a path: {name}")
        paths.add(name)
        for side in ("before", "after"):
            if side not in change or side + "Sha256" not in change:
                raise CorpusError(f"Corpus history {side} evidence is missing: {name}")
            text, digest = change[side], change[side + "Sha256"]
            if text is None:
                if digest is not None:
                    raise CorpusError(f"Absent corpus history file has a hash: {name}")
            elif not isinstance(text, str) or digest != text_hash(text):
                raise CorpusError(f"Corpus history {side} hash mismatch: {name}")
        if change["before"] == change["after"]:
            raise CorpusError(f"Corpus history contains a no-change entry: {name}")


def read_stage(path: Path) -> dict:
    try:
        stage = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
    except (OSError, ValueError) as exc:
        raise CorpusError(f"Cannot read corpus history stage {path}: {exc}") from exc
    validate_stage(stage)
    return stage


def rewind_files(files: dict[str, bytes], stage: dict) -> dict[str, bytes]:
    """Require the exact recorded after-state, then restore only declared changes."""
    validate_stage(stage)
    restored = files.copy()
    for change in stage["files"]:
        name = change["path"]
        expected = change["after"].encode("utf-8") if change["after"] is not None else None
        if files.get(name) != expected:
            raise CorpusError(f"Corpus history after-state disagrees with current files: {name}")
        if change["before"] is None:
            del restored[name]
        else:
            restored[name] = change["before"].encode("utf-8")
    return restored
