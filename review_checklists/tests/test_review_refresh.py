from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from review_checklists.__main__ import main
from review_checklists.catalog import make_bundle
from review_checklists.corpus import ReviewError
from review_checklists.refresh import RefreshConflict, apply_refresh, plan_refresh
from review_checklists.review import Review, RevisionConflict
from review_checklists.tests.test_prototype import ID, RECO
from scripts.modules.cl_corpus import enrich_recommendation


SECOND = "22222222-2222-2222-2222-222222222222"
THIRD = "33333333-3333-3333-3333-333333333333"


def recommendation(item_id=ID, **changes):
    reco = enrich_recommendation(deepcopy(RECO))
    reco.update(id=item_id, name="check-" + item_id, labels={"guid": item_id}, **changes)
    return reco


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "review.sqlite3"
        self.original = recommendation()
        self.bundle = make_bundle([self.original], "original-not-semver")
        self.review = Review.create(
            self.path, "My review", [self.original], self.root,
            description="Preserve description", corpus_version=self.bundle["corpusVersion"],
            corpus_content_hash=self.bundle["contentHash"],
        )

    def apply(self, bundle, **options):
        plan = plan_refresh(self.review, bundle, **options)
        return apply_refresh(self.review, bundle, token=plan["token"], **options)

    def target(self, **changes):
        return make_bundle([dict(deepcopy(self.original), **changes)], "new-label")

    def legacy(self):
        with self.review.connection() as connection:
            connection.execute("DROP TABLE IF EXISTS refresh_item_state")
            connection.execute("DROP TABLE IF EXISTS refresh_history")
            connection.execute("PRAGMA user_version = 1")
            connection.execute("DELETE FROM metadata WHERE key = 'review_scope'")
        self.review = Review(self.path)

    def test_schema1_open_preview_and_report_are_byte_readonly(self):
        self.legacy()
        before = self.path.read_bytes()
        review = Review(self.path)
        plan = plan_refresh(review, self.target(title="New relevant recommendation"))
        self.assertEqual(plan["counts"]["updated"], 1)
        self.assertEqual(review.get(ID)["refresh_state"]["needs_reassessment"], False)
        self.assertEqual(review.refresh_history(), [])
        self.assertEqual(review.report()["schema_version"], 1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])
        with review.connection() as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'refresh_item_state'"
            ).fetchone())

    def test_guidance_update_preserves_assessment_evidence_identity_and_unknown_metadata(self):
        self.review.update(ID, "Compliant", "Keep this decision", 0)
        self.review.add_evidence(ID, {"query": "old query", "rows": [{"id": "sample"}]})
        with self.review.connection() as connection:
            connection.execute("INSERT INTO metadata VALUES ('custom', 'keep')")
        metadata = self.review.metadata
        evidence = self.review.evidence(ID)
        result = self.apply(self.target(title="Updated recommendation text"))
        item = self.review.get(ID)
        self.assertTrue(result["applied"])
        self.assertEqual((item["status"], item["comments"], item["revision"]), ("Compliant", "Keep this decision", 2))
        self.assertTrue(item["refresh_state"]["needs_reassessment"])
        self.assertEqual(self.review.evidence(ID), evidence)
        for key, value in metadata.items():
            self.assertEqual(self.review.metadata[key], value, key)
        backup = Review(Path(result["backup_path"]))
        self.assertEqual(backup.get(ID)["recommendation"], self.original)
        self.assertEqual(backup.evidence(ID), evidence)
        report = json.loads(self.review.export())
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["refresh_history"][0]["plan"]["changes"][0]["before"], self.original)
        self.assertEqual(report["metadata"]["corpus_content_hash"], self.bundle["contentHash"])
        self.assertNotEqual(report["metadata"]["reviewed_snapshot_hash"], report["metadata"]["corpus_content_hash"])

    def test_provenance_only_changes_do_not_require_reassessment(self):
        self.review.update(ID, "Non-compliant", "Existing comment", 0)
        updated = deepcopy(self.original)
        updated["provenance"]["sources"] = [{"url": "https://learn.microsoft.com/azure/", "accessedAt": "2026-09-11"}]
        updated["automation"]["validatedAt"] = "2026-09-11"
        result = self.apply(make_bundle([updated], "new"))
        self.assertFalse(result["plan"]["changes"][0]["assessment_relevant"])
        self.assertFalse(self.review.get(ID)["refresh_state"]["needs_reassessment"])

    def test_schema1_upgrade_preserves_legacy_assessment_and_backup_schema(self):
        self.legacy()
        legacy = deepcopy(RECO)
        with self.review.connection() as connection:
            connection.execute(
                "UPDATE items SET recommendation = ?, status = 'Compliant', comments = 'Legacy decision'",
                (json.dumps(legacy),),
            )
        target = make_bundle([enrich_recommendation(legacy)], "explicit-metadata")
        result = self.apply(target)
        item = self.review.get(ID)
        self.assertFalse(item["refresh_state"]["needs_reassessment"])
        self.assertEqual((item["status"], item["comments"]), ("Compliant", "Legacy decision"))
        self.assertEqual(Review(self.path).report()["schema_version"], 2)
        backup = Review(Path(result["backup_path"]))
        self.assertEqual(backup.report()["schema_version"], 1)
        self.assertEqual(backup.get(ID)["recommendation"], legacy)

    def test_schema1_failed_apply_rolls_back_extension_tables_and_schema(self):
        self.legacy()
        with self.review.connection() as connection:
            connection.execute("CREATE TRIGGER reject_refresh BEFORE UPDATE OF recommendation ON items BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        before = self.review.report()
        with self.assertRaises(ReviewError):
            self.apply(self.target(title="New recommendation"))
        self.assertEqual(self.review.report(), before)
        with self.review.connection() as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'refresh_history'"
            ).fetchone())

    def test_semantic_fields_each_require_reassessment_but_unreviewed_does_not(self):
        changes = {
            "title": "New scope title", "description": "Changed guidance",
            "resourceTypes": ["Microsoft.Storage/storageAccounts"], "services": ["Storage"],
            "queries": {"arg": "resources | project id"},
            "automation": dict(self.original["automation"], resultSemantics="inventory"),
            "constraints": [{"field": "region", "operator": "equals", "value": "west"}],
        }
        self.review.update(ID, "Not applicable", "Not applicable is a decision", 0)
        for key, value in changes.items():
            with self.subTest(field=key):
                plan = plan_refresh(self.review, self.target(**{key: value}))
                self.assertTrue(plan["changes"][0]["assessment_relevant"])
                self.assertTrue(plan["changes"][0]["needs_reassessment"])
        self.review.update(ID, "Not reviewed", "Pending", 1)
        self.apply(self.target(title="New guidance"))
        self.assertFalse(self.review.get(ID)["refresh_state"]["needs_reassessment"])

    def test_comment_only_save_does_not_acknowledge_but_status_and_confirmation_do(self):
        self.review.update(ID, "Compliant", "Initial", 0)
        self.apply(self.target(title="New assessment guidance"))
        self.review.update(ID, "Compliant", "Comment-only autosave", 2)
        self.assertTrue(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        self.review.update(ID, "Compliant", "Confirmed", 3, confirm_current_assessment=True)
        self.assertFalse(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        self.apply(self.target(title="Another assessment change"))
        self.review.update(ID, "Non-compliant", "Deliberate decision", 5)
        self.assertFalse(self.review.get(ID)["refresh_state"]["needs_reassessment"])

    def test_service_alias_and_resource_type_normalization_preserve_assessment(self):
        original = recommendation(
            services=["Azure Kubernetes Service", "Azure Storage", "Storage"],
            resourceTypes=[
                "Microsoft.Storage/storageAccounts",
                "Microsoft.ContainerService/managedClusters",
                "microsoft.storage/storageaccounts",
            ],
        )
        with self.review.connection() as connection:
            connection.execute("UPDATE items SET recommendation = ?", (json.dumps(original),))
        self.review.update(ID, "Compliant", "Scope already assessed", 0)
        self.review.add_evidence(ID, {"rows": ["Original evidence"]})
        target = make_bundle([dict(
            original, services=["Storage", "AKS"],
            resourceTypes=[
                "microsoft.containerservice/managedclusters",
                "microsoft.storage/storageaccounts",
            ],
        )], "normalized")
        result = self.apply(target)
        change = result["plan"]["changes"][0]
        self.assertEqual(change["changed_fields"], ["resourceTypes", "services"])
        self.assertFalse(change["assessment_relevant"])
        item = self.review.get(ID)
        self.assertFalse(item["refresh_state"]["needs_reassessment"])
        self.assertEqual((item["status"], item["comments"], item["revision"]),
                         ("Compliant", "Scope already assessed", 2))
        self.assertEqual(self.review.evidence(ID)[0]["rows"], ["Original evidence"])
        self.assertEqual(item["recommendation"]["services"], ["Storage", "AKS"])
        self.assertFalse(self.review.refresh_history()[0]["plan"]["changes"][0]["assessment_relevant"])

    def test_actual_service_and_resource_scope_changes_still_require_reassessment(self):
        original = recommendation(
            services=["Azure Storage"],
            resourceTypes=["Microsoft.Storage/storageAccounts"],
        )
        with self.review.connection() as connection:
            connection.execute("UPDATE items SET recommendation = ?", (json.dumps(original),))
        self.review.update(ID, "Compliant", "Original scope", 0)
        for changes in (
            {"services": ["Blob Storage"]},
            {"services": ["Storage", "AKS"]},
            {"services": []},
            {"resourceTypes": ["Microsoft.Storage/storageAccounts/blobServices"]},
            {"resourceTypes": ["Microsoft.Storage/storageAccounts", "Microsoft.Compute/virtualMachines"]},
            {"resourceTypes": []},
        ):
            with self.subTest(changes=changes):
                plan = plan_refresh(self.review, make_bundle([dict(original, **changes)], "scope-change"))
                self.assertTrue(plan["changes"][0]["assessment_relevant"])
                self.assertTrue(plan["changes"][0]["needs_reassessment"])

    def test_removed_aliased_and_many_to_one_preserve_separate_records(self):
        second, third = recommendation(SECOND), recommendation(THIRD)
        with self.review.connection() as connection:
            connection.executemany(
                "INSERT INTO items (id, recommendation, status, comments) VALUES (?, ?, ?, ?)",
                [(SECOND, json.dumps(second), "Compliant", "Second assessment"),
                 (THIRD, json.dumps(third), "Non-compliant", "Third assessment")],
            )
        self.review.add_evidence(SECOND, {"rows": ["second evidence"]})
        canonical = dict(self.original, aliases=[
            {"id": SECOND, "name": second["name"]}, {"id": THIRD, "name": third["name"]},
        ])
        result = self.apply(make_bundle([canonical], "consolidated"))
        self.assertEqual(result["plan"]["consolidations"], [{"canonical_id": ID, "item_ids": sorted([ID, SECOND, THIRD])}])
        self.assertEqual(len(self.review.items()), 3)
        for old, status, comment in ((second, "Compliant", "Second assessment"), (third, "Non-compliant", "Third assessment")):
            item = self.review.get(old["id"])
            self.assertEqual(item["recommendation"], old)
            self.assertEqual((item["status"], item["comments"]), (status, comment))
            self.assertEqual(item["refresh_state"]["currency"], "superseded")
            self.assertEqual(item["refresh_state"]["canonical_id"], ID)
        self.assertEqual(self.review.evidence(SECOND)[0]["rows"], ["second evidence"])
        self.apply(make_bundle([self.original], "removed"))
        self.assertEqual(self.review.get(SECOND)["refresh_state"]["currency"], "no-longer-current")
        self.assertEqual(self.review.get(SECOND)["recommendation"], second)

    def test_unknown_scope_requires_explicit_addition_opt_in_and_known_scope_is_saved(self):
        target = make_bundle([self.original, recommendation(SECOND)], "new")
        self.assertEqual(plan_refresh(self.review, target)["counts"]["added"], 0)
        with self.assertRaisesRegex(ReviewError, "unknown"):
            plan_refresh(self.review, target, add_new=True)
        result = self.apply(target, add_new=True, scope={"kind": "all"})
        self.assertEqual(result["plan"]["counts"]["added"], 1)
        self.assertEqual(self.review.get(SECOND)["status"], "Not reviewed")
        self.assertEqual(json.loads(self.review.metadata["review_scope"]), {"kind": "all"})
        target = make_bundle([self.original, recommendation(SECOND), recommendation(THIRD)], "later")
        self.assertEqual(plan_refresh(self.review, target, add_new=True)["counts"]["added"], 1)

    def test_checklist_scope_updates_existing_outside_scope_and_preserves_placements(self):
        with self.review.connection() as connection:
            connection.execute("UPDATE items SET recommendation = ?", (json.dumps(dict(self.original, area="Original", subarea="Keep")),))
        second = recommendation(SECOND)
        scope = {"kind": "checklist", "definition": {"areas": [
            {"name": "New area", "include": {"guidSelector": [SECOND]}}
        ]}}
        target = make_bundle([dict(self.original, title="Update outside scope"), second, recommendation(THIRD)], "new")
        self.apply(target, add_new=True, scope=scope)
        self.assertEqual({item["id"] for item in self.review.items()}, {ID, SECOND})
        self.assertEqual(self.review.get(ID)["recommendation"]["title"], "Update outside scope")
        self.assertEqual(self.review.get(ID)["recommendation"]["area"], "Original")
        self.assertEqual(self.review.get(ID)["recommendation"]["subarea"], "Keep")
        self.assertEqual(self.review.get(SECOND)["recommendation"]["area"], "New area")
        empty_scope = {"kind": "checklist", "definition": {"include": {"guidSelector": ["44444444-4444-4444-4444-444444444444"]}}}
        self.assertEqual(plan_refresh(self.review, target, add_new=True, scope=empty_scope)["counts"]["added"], 0)

    def test_stale_plan_rejects_assessment_evidence_metadata_and_option_changes(self):
        target = self.target(title="New guidance")
        for mutate in (
            lambda: self.review.update(ID, "Compliant", "Changed", self.review.get(ID)["revision"]),
            lambda: self.review.add_evidence(ID, {"rows": []}),
            lambda: self.review.update_metadata(description="Changed metadata"),
        ):
            plan = plan_refresh(self.review, target)
            mutate()
            before = self.path.read_bytes()
            with self.assertRaises(RefreshConflict):
                apply_refresh(self.review, target, token=plan["token"])
            self.assertEqual(self.path.read_bytes(), before)
        plan = plan_refresh(self.review, target)
        with self.assertRaises(RefreshConflict):
            apply_refresh(self.review, target, token=plan["token"], scope={"kind": "all"})
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])

    def test_stale_form_cannot_overwrite_after_refresh(self):
        revision = self.review.get(ID)["revision"]
        self.apply(self.target(title="Changed recommendation"))
        with self.assertRaises(RevisionConflict):
            self.review.update(ID, "Compliant", "Old form", revision)

    def test_same_version_different_hash_is_not_treated_as_unchanged(self):
        target = make_bundle([dict(self.original, title="Changed same-label guidance")], self.bundle["corpusVersion"])
        result = self.apply(target)
        self.assertTrue(result["applied"])
        self.assertEqual(result["plan"]["source"]["version"], result["plan"]["target"]["version"])
        self.assertNotEqual(result["plan"]["source"]["content_hash"], result["plan"]["target"]["content_hash"])

    def test_unchanged_records_remain_byte_identical_in_mixed_refresh(self):
        second = recommendation(SECOND)
        with self.review.connection() as connection:
            connection.execute("INSERT INTO items (id, recommendation) VALUES (?, ?)", (SECOND, json.dumps(second, indent=3)))
            before = tuple(connection.execute("SELECT * FROM items WHERE id = ?", (SECOND,)).fetchone())
        self.apply(make_bundle([dict(self.original, title="Changed first recommendation"), second], "new"))
        with self.review.connection() as connection:
            after = tuple(connection.execute("SELECT * FROM items WHERE id = ?", (SECOND,)).fetchone())
        self.assertEqual(before, after)

    def test_wal_backup_includes_committed_evidence_and_writer_lock_protects_apply(self):
        keeper = sqlite3.connect(self.path)
        self.addCleanup(keeper.close)
        keeper.execute("PRAGMA journal_mode = WAL")
        self.review.add_evidence(ID, {"rows": ["committed WAL evidence"]})
        from review_checklists.refresh import _backup

        def check_lock(review, backup_path):
            competing = sqlite3.connect(review.path, timeout=0)
            try:
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    competing.execute("UPDATE items SET comments = 'racing writer'")
            finally:
                competing.close()
            _backup(review, backup_path)

        with patch("review_checklists.refresh._backup", side_effect=check_lock):
            result = self.apply(self.target(title="New WAL guidance"))
        backup = Review(Path(result["backup_path"]))
        self.assertEqual(backup.evidence(ID)[0]["rows"], ["committed WAL evidence"])
        self.assertEqual(backup.get(ID)["recommendation"], self.original)
        self.assertEqual(self.review.get(ID)["comments"], "")

    def test_invalid_tampered_bundle_and_token_are_rejected_before_backup(self):
        target = self.target(title="New guidance")
        plan = plan_refresh(self.review, target)
        invalid = deepcopy(target)
        invalid["recommendations"][0]["title"] = "Tampered"
        with self.assertRaisesRegex(ReviewError, "contentHash"):
            apply_refresh(self.review, invalid, token=plan["token"])
        invalid = deepcopy(target)
        invalid["recommendations"].append(deepcopy(invalid["recommendations"][0]))
        with self.assertRaises(ReviewError):
            plan_refresh(self.review, invalid)
        with self.assertRaises(RefreshConflict):
            apply_refresh(self.review, self.target(title="Different valid guidance"), token=plan["token"])
        with self.assertRaises(RefreshConflict):
            apply_refresh(self.review, target, token="edited-token")
        with self.assertRaises(RefreshConflict):
            apply_refresh(self.review, target, token="\u00e9")
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])

    def test_backup_and_transaction_failures_leave_original_review_intact(self):
        target = self.target(title="New guidance")
        before = self.path.read_bytes()
        with patch("review_checklists.refresh._backup", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(ReviewError, "no changes were committed"):
                self.apply(target)
        self.assertEqual(self.path.read_bytes(), before)
        with self.review.connection() as connection:
            connection.execute("CREATE TRIGGER reject_refresh BEFORE UPDATE OF recommendation ON items BEGIN SELECT RAISE(ABORT, 'test storage failure'); END")
        before_report = self.review.report()
        with self.assertRaisesRegex(ReviewError, "no changes were committed"):
            self.apply(target)
        self.assertEqual(self.review.report(), before_report)
        backup = next(self.root.glob("*before-refresh*"))
        self.assertEqual(Review(backup).report(), before_report)

    def test_idempotence_preserves_bytes_history_backups_and_revisions(self):
        before = self.path.read_bytes()
        self.assertFalse(self.apply(self.bundle)["applied"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.review.refresh_history(), [])
        target = self.target(title="New guidance")
        self.apply(target)
        before = self.path.read_bytes()
        backups = list(self.root.glob("*before-refresh*"))
        self.assertFalse(self.apply(target)["applied"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("*before-refresh*")), backups)
        self.assertEqual(len(self.review.refresh_history()), 1)
        self.assertEqual(self.review.get(ID)["revision"], 1)

    def test_cli_preview_apply_token_and_init_scope(self):
        bundle_path = self.root / "target.json"
        bundle_path.write_text(json.dumps(self.target(title="New guidance")), encoding="utf-8")
        prefix = ["--review", str(self.path), "refresh", "--bundle", str(bundle_path)]
        before = self.path.read_bytes()
        output = io.StringIO()
        with redirect_stdout(output), patch("review_checklists.arg.run_query") as query:
            self.assertEqual(main(prefix), 0)
            query.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)
        token = json.loads(output.getvalue())["token"]
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(prefix + ["--apply"]), 1)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(prefix + ["--apply", "--token", token]), 0)
        new_path = self.root / "new.sqlite3"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--review", str(new_path), "init", "--bundle", str(bundle_path)]), 0)
        self.assertEqual(json.loads(Review(new_path).metadata["review_scope"]), {"kind": "all"})

    def test_cli_init_captures_checklist_definition_not_mutable_filename(self):
        bundle_path = self.root / "bundle.json"
        target = make_bundle([self.original, recommendation(SECOND, waf="Cost")], "first")
        bundle_path.write_text(json.dumps(target), encoding="utf-8")
        checklist = self.root / "checklist.json"
        definition = {"include": {"wafSelector": ["Security"]}}
        checklist.write_text(json.dumps(definition), encoding="utf-8")
        review_path = self.root / "scoped.sqlite3"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([
                "--review", str(review_path), "init", "--bundle", str(bundle_path),
                "--checklist", str(checklist),
            ]), 0)
        review = Review(review_path)
        self.assertEqual(json.loads(review.metadata["review_scope"]), {"kind": "checklist", "definition": definition})
        checklist.write_text('{"include": {"wafSelector": ["Cost"]}}', encoding="utf-8")
        target = make_bundle([self.original, recommendation(SECOND, waf="Cost"), recommendation(THIRD)], "next")
        plan = plan_refresh(review, target, add_new=True)
        self.assertEqual(plan["scope"]["candidate_ids"], [THIRD])

    def test_invalid_scope_and_alias_collision_do_not_mutate_review(self):
        before = self.path.read_bytes()
        for scope in ({"kind": "all", "unexpected": True}, {"kind": "checklist", "definition": {"include": {"bogus": ["x"]}}}):
            with self.assertRaises(ReviewError):
                plan_refresh(self.review, self.bundle, scope=scope)
        invalid = deepcopy(self.bundle)
        invalid["recommendations"][0]["aliases"] = [{"id": ID, "name": "duplicate-Alias"}]
        with self.assertRaises(ReviewError):
            plan_refresh(self.review, invalid)
        self.assertEqual(self.path.read_bytes(), before)

    def test_schema_change_after_handle_open_is_not_silently_downgraded(self):
        target = self.target(title="New guidance")
        plan = plan_refresh(self.review, target)
        with self.review.connection() as connection:
            connection.execute("PRAGMA user_version = 999")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ReviewError, "Unsupported review schema"):
            apply_refresh(self.review, target, token=plan["token"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])


if __name__ == "__main__":
    unittest.main()
