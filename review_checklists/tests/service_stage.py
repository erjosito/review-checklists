"""Verify the normalization stage, then replay historical pillar inputs exactly."""

from functools import lru_cache
import json
from pathlib import Path

import yaml

from scripts.modules.cl_corpus import StrictLoader, json_value
from review_checklists.service_normalization import (
    document_hash, protected_hash, replay_normalization, sha256,
)
from review_checklists.tests.followup_stage import pre_followup_bytes


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "review_checklists" / "docs" / "corpus-refresh" / "service-normalization.json"


@lru_cache(maxsize=1)
def normalization_report():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "applied"
    return report


@lru_cache(maxsize=1)
def _rows():
    return {(ROOT / row["path"]).resolve(): row for row in normalization_report()["records"]}


def stage_file_bytes(path):
    path = Path(path)
    raw = pre_followup_bytes(path)
    row = _rows().get(path.resolve())
    if row is None:
        return raw
    assert sha256(raw) == row["afterFileSha256"], path
    actual = json_value(yaml.load(raw.decode("utf-8"), Loader=StrictLoader))
    assert document_hash(actual) == row["afterDocumentSha256"], path
    assert protected_hash(actual) == row["protectedFieldsSha256"], path
    before = replay_normalization(actual, normalization_report(), reverse=True)
    text, shift, positions = raw.decode("utf-8"), 0, []
    for edit in row["edits"]:
        positions.append((edit["start"] + shift, edit))
        shift += len(edit["after"]) - len(edit["before"])
    for start, edit in reversed(positions):
        assert text[start:start + len(edit["after"])] == edit["after"], path
        text = text[:start] + edit["before"] + text[start + len(edit["after"]):]
    original = text.encode("utf-8")
    assert sha256(original) == row["beforeFileSha256"], path
    assert json_value(yaml.load(text, Loader=StrictLoader)) == before, path
    assert document_hash(before) == row["beforeDocumentSha256"], path
    return original


def stage_file_text(path):
    return stage_file_bytes(path).decode("utf-8").replace("\r\n", "\n")


def load_stage_document(path):
    return json_value(yaml.load(stage_file_text(path), Loader=StrictLoader))
