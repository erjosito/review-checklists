from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import yaml

from scripts.modules.cl_corpus import (
    CorpusError, enrich_recommendation, load_yaml_document, validate_corpus, validate_recommendation,
)
from review_checklists.__main__ import main
from review_checklists.arg import run_selected
from review_checklists.catalog import make_bundle, migrate_corpus, read_bundle, build_bundle
from review_checklists.corpus import ReviewError, load_corpus
from review_checklists.review import Review
from review_checklists.tests.test_prototype import RECO, ID, SCOPE


ALIAS = "66666666-6666-6666-6666-666666666666"


class ContractTests(unittest.TestCase):
    def test_enrichment_preserves_identity_and_does_not_invent_technical_claims(self):
        legacy = deepcopy(RECO)
        legacy["source"]["timestamp"] = "July 24, 2024"
        result = enrich_recommendation(legacy)
        validate_recommendation(result)
        self.assertEqual(result["id"], ID)
        self.assertEqual(result["labels"]["guid"], ID)
        self.assertEqual(result["queries"], legacy["queries"])
        self.assertEqual(result["automation"], {
            "status": "query_available", "resultSemantics": "unknown", "validatedAt": None,
        })
        self.assertEqual(result["services"], [])
        self.assertIsNone(result["provenance"]["lastReviewed"])
        self.assertIsNone(result["provenance"]["upstreamRevision"])
        self.assertNotIn("schemaVersion", legacy)

    def test_manual_candidate_and_unknown_are_distinct(self):
        for flag, expected in ((None, "unknown"), (False, "manual"), (True, "candidate")):
            reco = dict(deepcopy(RECO), queries={})
            if flag is not None:
                reco["automatable"] = flag
            enriched = enrich_recommendation(reco)
            self.assertEqual(enriched["automation"]["status"], expected)
            validate_recommendation(enriched)

    def test_query_contract_and_recorded_dates_are_validated(self):
        reco = enrich_recommendation(RECO)
        reco["automation"]["resultSemantics"] = "compliance"
        with self.assertRaisesRegex(CorpusError, "complianceColumn"):
            validate_recommendation(reco)
        reco["automation"]["complianceColumn"] = "compliant"
        validate_recommendation(reco)
        reco["automation"]["validatedAt"] = "yesterday"
        with self.assertRaises(CorpusError):
            validate_recommendation(reco)
        reco["automation"]["validatedAt"] = None
        reco["automation"]["status"] = "manual"
        with self.assertRaises(CorpusError):
            validate_recommendation(reco)

    def test_id_collisions_alias_collisions_and_conflicts_are_rejected(self):
        reco = enrich_recommendation(RECO)
        reco["aliases"] = [{"id": ALIAS, "name": "retired-Recommendation"}]
        validate_corpus([reco])
        with self.assertRaisesRegex(CorpusError, "Duplicate"):
            validate_corpus([reco, deepcopy(reco)])
        conflict = deepcopy(reco)
        conflict["labels"]["guid"] = ALIAS
        with self.assertRaisesRegex(CorpusError, "same recommendation"):
            validate_recommendation(conflict)
        alias_reco = enrich_recommendation(dict(
            RECO, id=ALIAS, labels={"guid": ALIAS}, name="another-Recommendation",
        ))
        with self.assertRaisesRegex(CorpusError, "Duplicate"):
            validate_corpus([reco, alias_reco])


class CatalogFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.file = self.corpus / "recommendation.yaml"
        legacy = deepcopy(RECO)
        legacy.pop("id")
        self.original = "# Preserve this comment\n" + yaml.safe_dump(legacy, sort_keys=False)
        self.file.write_text(self.original, encoding="utf-8", newline="\n")

    def test_migration_is_preflighted_minimal_and_idempotent(self):
        result = migrate_corpus(self.corpus)
        self.assertEqual(result["files_to_change"], 1)
        self.assertEqual(self.file.read_text(encoding="utf-8"), self.original)
        with self.assertRaisesRegex(ReviewError, "schemaVersion"):
            load_corpus(self.corpus, require_current=True)
        self.assertEqual(migrate_corpus(self.corpus, write=True)["files_changed"], 1)
        self.assertTrue(self.file.read_text(encoding="utf-8").startswith(self.original))
        self.assertEqual(migrate_corpus(self.corpus, write=True)["files_changed"], 0)
        self.assertEqual(load_corpus(self.corpus, require_current=True)[0]["id"], ID)

    def test_invalid_file_prevents_writes_to_all_files(self):
        (self.corpus / "bad.yaml").write_text("name: bad\n", encoding="utf-8")
        with self.assertRaises(CorpusError):
            migrate_corpus(self.corpus, write=True)
        self.assertEqual(self.file.read_text(encoding="utf-8"), self.original)

    def test_document_end_marker_and_keep_chomping_preserve_exact_query_text(self):
        legacy = deepcopy(RECO)
        legacy.pop("queries")
        self.file.write_text(
            yaml.safe_dump(legacy, sort_keys=False)
            + "queries:\n  arg: |+\n    resources\n    | project id\n\n...\n",
            encoding="utf-8",
        )
        before = load_yaml_document(self.file)
        migrate_corpus(self.corpus, write=True)
        after = load_yaml_document(self.file)
        self.assertEqual(after["queries"], before["queries"])
        self.assertTrue(self.file.read_text(encoding="utf-8").endswith("...\n"))
        self.assertEqual(migrate_corpus(self.corpus)["files_to_change"], 0)

    def test_duplicate_yaml_keys_are_not_silently_accepted(self):
        self.file.write_text(self.original + "\nseverity: 0\n", encoding="utf-8")
        with self.assertRaisesRegex(CorpusError, "Duplicate YAML key"):
            load_yaml_document(self.file)

    def test_bundle_is_deterministic_and_checks_content_integrity(self):
        migrate_corpus(self.corpus, write=True)
        first = build_bundle(self.corpus, "test.1", self.root / "one.json")
        second = build_bundle(self.corpus, "test.1", self.root / "two.json")
        self.assertEqual(first, second)
        self.assertEqual((self.root / "one.json").read_bytes(), (self.root / "two.json").read_bytes())
        self.assertEqual(read_bundle(self.root / "one.json"), first)
        reordered = [{key: value for key, value in reversed(list(first["recommendations"][0].items()))}]
        self.assertEqual(make_bundle(reordered, "test.1"), first)
        first["recommendations"][0]["title"] = "Tampered recommendation title"
        (self.root / "tampered.json").write_text(json.dumps(first), encoding="utf-8")
        with self.assertRaisesRegex(CorpusError, "contentHash"):
            read_bundle(self.root / "tampered.json")
        with self.assertRaises(CorpusError):
            build_bundle(self.corpus, "test.1", self.corpus / "bundle.json")

    def test_bundle_init_pins_version_and_does_not_touch_an_existing_review(self):
        old = Review.create(self.root / "old.sqlite3", "Old", [deepcopy(RECO)], self.corpus)
        old.update(ID, "Non-compliant", "Keep my assessment", 0)
        old_bytes = old.path.read_bytes()
        migrate_corpus(self.corpus, write=True)
        bundle_path = self.root / "bundle.json"
        bundle = build_bundle(self.corpus, "test.2", bundle_path)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = main(["--review", str(self.root / "new.sqlite3"), "init", "--bundle", str(bundle_path)])
        self.assertEqual(code, 0)
        new = Review(self.root / "new.sqlite3")
        self.assertEqual(new.metadata["corpus_version"], "test.2")
        self.assertEqual(new.metadata["corpus_content_hash"], bundle["contentHash"])
        self.assertEqual(new.get(ID)["status"], "Not reviewed")
        self.assertEqual(old.path.read_bytes(), old_bytes)

    def test_alias_access_updates_only_the_canonical_item(self):
        reco = enrich_recommendation(RECO)
        reco["aliases"] = [{"id": ALIAS, "name": "retired-Recommendation"}]
        review = Review.create(self.root / "aliases.sqlite3", "Aliases", [reco], self.corpus)
        self.assertEqual(review.get(ALIAS)["id"], ID)
        review.update(ALIAS, "Compliant", "Alias edit", 0)
        self.assertEqual(review.get(ID)["comments"], "Alias edit")
        executor = Mock(return_value={"rows": [], "truncated": False})
        result = run_selected(review, [ALIAS, ID], SCOPE, executor)
        self.assertEqual(result["succeeded"], 1)
        executor.assert_called_once()
        self.assertEqual(review.evidence(ALIAS), review.evidence(ID))
