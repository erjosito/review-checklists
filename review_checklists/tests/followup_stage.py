"""Reconstruct the normalized checkpoint through exact, hash-verified later stages."""

from functools import lru_cache
from contextlib import contextmanager
import json
from pathlib import Path
from unittest.mock import patch

import yaml

from review_checklists.catalog import make_bundle
from review_checklists.corpus_history import read_stage, rewind_files
from scripts.modules.cl_corpus import StrictLoader, json_value
from scripts.modules import cl_services


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "review_checklists" / "docs" / "corpus-refresh"
FOLLOWUP_STAGES = ("followup-2026-09-13-application.json",)


def corpus_documents(files):
    return [
        json_value(yaml.load(raw.decode("utf-8"), Loader=StrictLoader))
        for path, raw in sorted(files.items()) if path.startswith("v2/recos/")
    ]


def verify_corpus_state(files, state):
    documents = corpus_documents(files)
    bundle = make_bundle(documents, "historical-stage-verification")
    assert bundle["contentHash"] == state["contentHash"], "Corpus history content hash mismatch"
    assert len(documents) == state["canonical"], "Corpus history canonical count mismatch"
    assert sum(len(doc.get("aliases", [])) for doc in documents) == state["aliases"], "Corpus history alias count mismatch"


@lru_cache(maxsize=1)
def pre_followup_files():
    files = {
        path.relative_to(ROOT).as_posix(): path.read_bytes()
        for path in (ROOT / "v2" / "recos").rglob("*.yaml")
    }
    files["scripts/service_dictionary.json"] = (ROOT / "scripts" / "service_dictionary.json").read_bytes()
    for filename in reversed(FOLLOWUP_STAGES):
        path = REPORTS / filename
        if not path.exists():
            continue
        stage = read_stage(path)
        verify_corpus_state(files, stage["afterCorpus"])
        files = rewind_files(files, stage)
        verify_corpus_state(files, stage["beforeCorpus"])
    return files


def pre_followup_bytes(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / "v2" / "recos") and path != ROOT / "scripts" / "service_dictionary.json":
        return path.read_bytes()
    return pre_followup_files()[path.relative_to(ROOT).as_posix()]


def pre_followup_document(path):
    return json_value(yaml.load(pre_followup_bytes(path).decode("utf-8"), Loader=StrictLoader))


def pre_followup_paths():
    return [ROOT / path for path in sorted(pre_followup_files()) if path.startswith("v2/recos/")]


@contextmanager
def pre_followup_catalogue():
    catalogue = json.loads(pre_followup_files()["scripts/service_dictionary.json"])
    cl_services._catalogue.cache_clear()
    try:
        with patch.object(cl_services, "service_dictionary", return_value=catalogue):
            yield
    finally:
        cl_services._catalogue.cache_clear()
