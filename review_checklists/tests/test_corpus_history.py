from copy import deepcopy
import unittest

from review_checklists.corpus_history import rewind_files, text_hash, validate_stage
from scripts.modules.cl_corpus import CorpusError


def entry(path, before, after):
    return {
        "path": path, "before": before, "after": after,
        "beforeSha256": text_hash(before) if before is not None else None,
        "afterSha256": text_hash(after) if after is not None else None,
    }


class CorpusHistoryTests(unittest.TestCase):
    def setUp(self):
        self.stage = {
            "schemaVersion": 1, "stage": "fixture", "status": "applied", "assessedAt": "2026-09-13",
            "files": [
                entry("v2/recos/update.yaml", "old\r\n", "new\r\n"),
                entry("v2/recos/retired.yaml", "retired\n", None),
                entry("v2/recos/added.yaml", None, "added\n"),
                entry("scripts/service_dictionary.json", "[]\n", "[{}]\n"),
            ],
        }
        self.files = {
            "v2/recos/update.yaml": b"new\r\n", "v2/recos/added.yaml": b"added\n",
            "v2/recos/untouched.yaml": b"unchanged\n",
            "scripts/service_dictionary.json": b"[{}]\n",
        }

    def test_rewind_preserves_exact_bytes_and_unrelated_files_without_mutation(self):
        original = deepcopy(self.files)
        restored = rewind_files(self.files, self.stage)
        self.assertEqual(restored, {
            "v2/recos/update.yaml": b"old\r\n", "v2/recos/retired.yaml": b"retired\n",
            "v2/recos/untouched.yaml": b"unchanged\n", "scripts/service_dictionary.json": b"[]\n",
        })
        self.assertEqual(self.files, original)

    def test_unrecorded_edit_missing_file_and_reappearing_retirement_fail(self):
        for path, value in (
            ("v2/recos/update.yaml", b"new\n"),
            ("v2/recos/retired.yaml", b"retired\n"),
            ("v2/recos/added.yaml", None),
        ):
            with self.subTest(path=path):
                files = deepcopy(self.files)
                if value is None:
                    files.pop(path)
                else:
                    files[path] = value
                with self.assertRaises(CorpusError):
                    rewind_files(files, self.stage)

    def test_tampered_incomplete_and_duplicate_evidence_fails(self):
        for field, value in (("before", "invented"), ("afterSha256", "0" * 64),
                             ("beforeSha256", None), ("after", None)):
            with self.subTest(field=field):
                stage = deepcopy(self.stage)
                stage["files"][0][field] = value
                with self.assertRaises(CorpusError):
                    validate_stage(stage)
        stage = deepcopy(self.stage)
        stage["files"].append(stage["files"][0])
        with self.assertRaises(CorpusError):
            validate_stage(stage)
        stage = deepcopy(self.stage)
        del stage["files"][0]["after"]
        with self.assertRaises(CorpusError):
            validate_stage(stage)
        stage["files"] = [entry("v2/recos/a.yaml", None, None)]
        with self.assertRaises(CorpusError):
            validate_stage(stage)

    def test_unapproved_paths_are_rejected(self):
        for path in ("../secret.yaml", "/v2/recos/a.yaml", "C:/v2/recos/a.yaml",
                     "v2/recos/../../secret.yaml", "v2\\recos\\a.yaml", "v2//recos/a.yaml",
                     ".reviews/review.sqlite3", "scripts/other.json", "v2/recos/a.txt"):
            with self.subTest(path=path):
                stage = dict(self.stage, files=[entry(path, "old", "new")])
                with self.assertRaises(CorpusError):
                    validate_stage(stage)

    def test_stage_identity_version_status_and_date_are_required(self):
        for field, value in (("schemaVersion", True), ("schemaVersion", 2),
                             ("stage", ""), ("status", "proposed"), ("assessedAt", "20260913")):
            with self.subTest(field=field):
                with self.assertRaises(CorpusError):
                    validate_stage(dict(self.stage, **{field: value}))
