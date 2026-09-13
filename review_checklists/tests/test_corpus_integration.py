from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from review_checklists.corpus_admin import (
    APRL_EVENT, COST_EVENT, DUPLICATE_PROPOSALS, FOLLOWUP_EVENT, KEY_VAULT_PROPOSALS,
    NORMALIZATION_EVENT, PERFORMANCE_EVENT, CorpusAdminError, create_corpus_blueprint,
    followup_application_event, followup_proposal_snapshot, frozen_refresh_event,
    maintenance_history, normalization_event,
)
from review_checklists.review import Review
from review_checklists.tests import test_corpus_admin
from review_checklists.web import create_app


class CorpusIntegrationTests(unittest.TestCase):
    setUp = test_corpus_admin.CorpusAdminTests.setUp
    write_corpus = test_corpus_admin.CorpusAdminTests.write_corpus

    def test_review_navigation_and_public_routes_never_read_review_state(self):
        review = Review.create(self.root / "review.sqlite3", "Private engagement", self.recos, self.root)
        with patch("review_checklists.web.create_corpus_blueprint",
                   side_effect=lambda: create_corpus_blueprint(self.corpus, self.reports)):
            app = create_app(review)
        client = app.test_client()
        self.assertIn(b'href="/corpus/"', client.get("/").data)
        with patch.object(review, "items", side_effect=AssertionError("Customer state read")), \
             patch.object(review, "refresh_history", side_effect=AssertionError("Customer history read")):
            for route in ("/corpus/", "/corpus/recommendations", "/corpus/sources", "/corpus/history"):
                response = client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b"Private engagement", response.data)
                self.assertIn(b"Return to review", response.data)
        self.assertEqual(client.post("/corpus/").status_code, 403)

    def test_new_history_adapters_reject_inconsistent_accounting(self):
        record = {"id": self.recos[0]["id"], "status": "updated"}
        manifest = {
            "schemaVersion": 1, "status": "applied", "asOf": "2026-09-11",
            "scope": "Frozen fixture source",
            "counts": {"baseline": 1, "byStatus": {
                "updated": 1, "supported_unchanged": 0, "needs_manual_review": 0,
            }},
            "records": [record],
        }
        self.assertEqual(frozen_refresh_event(manifest, APRL_EVENT)["summary"]["updated"], 1)
        invalid = deepcopy(manifest)
        invalid["counts"]["byStatus"]["updated"] = 2
        with self.assertRaises(CorpusAdminError):
            frozen_refresh_event(invalid, APRL_EVENT)
        invalid = deepcopy(manifest)
        invalid["records"].append(record)
        with self.assertRaises(CorpusAdminError):
            frozen_refresh_event(invalid, APRL_EVENT)

    def test_source_pages_explain_excluded_inventory_entries(self):
        source = test_corpus_admin.coverage_report(test_corpus_admin.inventory(), [])
        source.update(
            coverageSelection={"scope": "Active entries"},
            inventoryScope="All lifecycle states", inventoryCount=6, excludedCount=1,
            excludedItems=[{"id": "DISABLED-1", "title": "Retired <requirement>", "state": "full"}],
            comparison=None,
        )
        with patch("review_checklists.corpus_admin.source_coverage", return_value={
            "sources": [source], "errors": [], "unknownSources": {},
        }):
            for route in ("/corpus/sources", "/corpus/sources/" + source["sourceId"]):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertIn("6 total inventoried", response.text)
                self.assertIn("1 excluded from this coverage scope", response.text)
            self.assertIn("DISABLED-1", response.text)
            self.assertIn("Retired &lt;requirement&gt;", response.text)
            self.assertIn("All lifecycle states", response.text)

    def test_persisted_all_pillar_history_has_one_event_per_stage(self):
        from review_checklists.corpus_admin import DEFAULT_REPORTS
        history = maintenance_history(DEFAULT_REPORTS)
        self.assertEqual(history["errors"], [])
        names = [event["filename"] for event in history["events"]]
        self.assertEqual(len(names), len(set(names)))
        for name in (APRL_EVENT, COST_EVENT, PERFORMANCE_EVENT, NORMALIZATION_EVENT, FOLLOWUP_EVENT):
            self.assertEqual(names.count(name), 1)
        self.assertIn("report-redactions.json", [entry["filename"] for entry in history["snapshots"]])
        self.assertEqual(len(history["deferrals"]), 14)
        self.assertNotIn("confirmed-012", {row["groupId"] for row in history["deferrals"]})

    def test_normalization_history_reconciles_recorded_counts(self):
        data = {
            "schemaVersion": 1, "stage": "service-normalization", "status": "applied",
            "assessedAt": "2026-09-12", "records": [{"id": "a"}], "corpusBefore": [{"id": "a"}, {"id": "b"}],
            "summary": {"canonical": 2, "changed": 1, "unchanged": 1},
        }
        self.assertEqual(normalization_event(data, NORMALIZATION_EVENT)["summary"]["changed"], 1)
        for field in ("canonical", "changed", "unchanged"):
            invalid = deepcopy(data)
            invalid["summary"][field] += 1
            with self.assertRaises(CorpusAdminError):
                normalization_event(invalid, NORMALIZATION_EVENT)
        invalid = deepcopy(data)
        invalid["records"][0]["id"] = "outside"
        with self.assertRaises(CorpusAdminError):
            normalization_event(invalid, NORMALIZATION_EVENT)

    def test_followup_history_rejects_inconsistent_application_and_proposal_evidence(self):
        from review_checklists.corpus_admin import DEFAULT_REPORTS
        applied = json.loads((DEFAULT_REPORTS / FOLLOWUP_EVENT).read_text(encoding="utf-8"))
        self.assertEqual(followup_application_event(applied, FOLLOWUP_EVENT)["summary"]["retiredRecommendationFiles"], 3)
        for section, field, value in (
            ("summary", "sourceAmendments", 20), ("afterCorpus", "aliases", 59),
            ("mergeResult", "mode", "dry-run"),
        ):
            invalid = deepcopy(applied)
            invalid[section][field] = value
            with self.assertRaises(CorpusAdminError):
                followup_application_event(invalid, FOLLOWUP_EVENT)
        invalid = deepcopy(applied)
        invalid["files"][0]["afterSha256"] = "0" * 64
        with self.assertRaises(CorpusAdminError):
            followup_application_event(invalid, FOLLOWUP_EVENT)
        proposals = json.loads((DEFAULT_REPORTS / KEY_VAULT_PROPOSALS).read_text(encoding="utf-8"))
        proposals["counts"]["updated"] += 1
        with self.assertRaises(CorpusAdminError):
            followup_proposal_snapshot(proposals, KEY_VAULT_PROPOSALS)

    def test_mergeable_proposals_stay_pending_without_a_separate_application(self):
        from review_checklists.corpus_admin import DEFAULT_REPORTS
        (self.reports / DUPLICATE_PROPOSALS).write_bytes((DEFAULT_REPORTS / DUPLICATE_PROPOSALS).read_bytes())
        history = maintenance_history(self.reports)
        self.assertEqual(history["errors"], [])
        self.assertEqual(len(history["deferrals"]), 16)
        self.assertEqual(history["events"], [])
