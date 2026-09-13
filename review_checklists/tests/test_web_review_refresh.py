from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import Mock, patch

from review_checklists.catalog import make_bundle
from review_checklists.review import Review
from review_checklists.tests.test_review_refresh import ID, SECOND, THIRD, recommendation
from review_checklists.web import create_app


NEW = "44444444-4444-4444-4444-444444444444"


class WebRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "review.sqlite3"
        self.original = recommendation()
        self.second, self.third = recommendation(SECOND), recommendation(THIRD)
        self.review = Review.create(self.path, "Private review", [self.original, self.second, self.third], self.root)
        self.review.update(ID, "Compliant", "Keep review notes", 0)
        self.review.update(SECOND, "Non-compliant", "Keep retired assessment", 0)
        self.review.add_evidence(ID, {
            "outcome": "success", "completed_at": "2026-09-11T12:00:00+00:00",
            "query": "resources", "subscriptions": [], "rows": [{"id": "retained evidence"}],
        })
        with self.review.connection() as connection:
            connection.execute("DROP TABLE refresh_item_state")
            connection.execute("DROP TABLE refresh_history")
            connection.execute("DELETE FROM metadata WHERE key = 'review_scope'")
            connection.execute("PRAGMA user_version = 1")
        self.target = make_bundle([
            dict(self.original, title="Changed guidance requiring reassessment",
                 aliases=[{"id": SECOND, "name": self.second["name"]}]),
            recommendation(NEW),
        ], "next-bundle")
        self.executor, self.lookup = Mock(), Mock()
        self.app = create_app(self.review, self.executor, self.lookup)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.client.get("/review-refresh")
        with self.client.session_transaction() as session:
            self.csrf = session["csrf"]

    def preview(self, *, bundle=None, **fields):
        data = {
            "csrf": self.csrf, "refresh_scope": "saved",
            "bundle": (io.BytesIO(json.dumps(bundle or self.target).encode("utf-8")), "bundle.json"),
            **fields,
        }
        return self.client.post("/review-refresh/preview", data=data)

    def handle(self, response):
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:1500])
        match = re.search(r'name="handle" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def apply(self, handle, **fields):
        return self.client.post("/review-refresh/apply", data={"csrf": self.csrf, "handle": handle, **fields})

    def test_schema1_upload_preview_is_readonly_and_only_opaque_handle_is_submitted(self):
        before = self.path.read_bytes()
        page = self.client.get("/review-refresh")
        self.assertIn(b"unknown scope", page.data)
        response = self.preview()
        handle = self.handle(response)
        self.assertEqual(len(handle), 43)
        self.assertIn(b"No review changes have been saved", response.data)
        for word in (b"Consolidation groups", b"superseded", b"removed", b"Needs reassessment", b"backup"):
            self.assertIn(word, response.data)
        self.assertNotIn(b'name="token"', response.data)
        self.assertNotIn(b'name="bundle"', response.data)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])
        self.assertEqual(self.review.report()["schema_version"], 1)
        self.executor.assert_not_called()
        self.lookup.assert_not_called()

    def test_apply_preserves_assessments_evidence_legacy_items_and_exports_history(self):
        evidence = self.review.evidence(ID)
        result = self.apply(self.handle(self.preview()))
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.location, "/review-refresh/history")
        self.assertEqual({item["id"] for item in self.review.items()}, {ID, SECOND, THIRD})
        item = self.review.get(ID)
        self.assertEqual((item["status"], item["comments"]), ("Compliant", "Keep review notes"))
        self.assertEqual(self.review.evidence(ID), evidence)
        self.assertTrue(item["refresh_state"]["needs_reassessment"])
        self.assertEqual(self.review.get(SECOND)["recommendation"], self.second)
        self.assertEqual(self.review.get(THIRD)["recommendation"], self.third)
        self.assertEqual(self.review.get(SECOND)["refresh_state"]["currency"], "superseded")
        history = self.client.get(result.location)
        self.assertIn(b"next-bundle", history.data)
        self.assertIn(b"before-refresh-", history.data)
        detail = self.client.get(f"/item/{ID}")
        self.assertIn(b"Needs reassessment", detail.data)
        self.assertIn(b"not every item", detail.data)
        self.assertIn(b"confirm_current_assessment", detail.data)
        exported = self.client.get("/export/html")
        self.assertEqual(exported.status_code, 200)
        self.assertIn(b"Historical saved assessments", exported.data)
        self.assertIn(b"No longer current", exported.data)
        self.assertIn(b"Superseded", exported.data)
        self.assertIn(b"Keep review notes", exported.data)
        self.assertIn(b"retained evidence", exported.data)
        self.assertIn(b"Previous recommendation snapshot", exported.data)
        exported_json = self.client.get("/export/json").json
        self.assertEqual(len(exported_json["refresh_history"]), 1)
        self.assertEqual(exported_json["items"][0]["id"], min(ID, SECOND, THIRD))
        self.assertEqual(Review(next(self.root.glob("*before-refresh*"))).report()["schema_version"], 1)
        self.executor.assert_not_called()
        self.lookup.assert_not_called()

    def test_unknown_scope_additions_require_explicit_choice_and_checklist_is_respected(self):
        self.assertEqual(self.preview(add_new="1").status_code, 400)
        definition = {"areas": [{"name": "Chosen area", "include": {"guidSelector": [NEW]}}]}
        preview = self.preview(
            add_new="1", refresh_scope="checklist",
            checklist=(io.BytesIO(json.dumps(definition).encode()), "checklist.json"),
        )
        self.assertEqual(self.apply(self.handle(preview)).status_code, 303)
        item = self.review.get(NEW)
        self.assertEqual(item["status"], "Not reviewed")
        self.assertEqual(item["recommendation"]["area"], "Chosen area")
        self.assertTrue(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        self.assertEqual(json.loads(self.review.metadata["review_scope"])["definition"], definition)

    def test_all_scope_is_explicit_and_can_be_reused(self):
        first = self.preview(add_new="1", refresh_scope="all")
        self.assertEqual(self.apply(self.handle(first)).status_code, 303)
        self.assertEqual(self.review.get(NEW)["status"], "Not reviewed")
        self.assertEqual(json.loads(self.review.metadata["review_scope"]), {"kind": "all"})
        second = self.preview(add_new="1")
        self.assertEqual(second.status_code, 200)

    def test_csrf_origin_session_handle_and_replay_do_not_write(self):
        handle = self.handle(self.preview())
        before = self.path.read_bytes()
        self.assertEqual(self.apply(handle, csrf="wrong").status_code, 403)
        response = self.client.post("/review-refresh/apply", data={"csrf": self.csrf, "handle": handle},
                                    headers={"Origin": "https://attacker.example"})
        self.assertEqual(response.status_code, 403)
        other = self.app.test_client()
        other.get("/review-refresh")
        with other.session_transaction() as session:
            other_csrf = session["csrf"]
        self.assertEqual(other.post("/review-refresh/apply", data={"csrf": other_csrf, "handle": handle}).status_code, 403)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.apply(handle).status_code, 303)
        after = self.path.read_bytes()
        self.assertEqual(self.apply(handle).status_code, 410)
        self.assertEqual(self.path.read_bytes(), after)
        self.assertEqual(len(self.review.refresh_history()), 1)
        self.assertEqual(self.apply("missing").status_code, 410)

    def test_preview_expiry_and_bounded_cache_are_explicit(self):
        self.app.config["REVIEW_REFRESH_PREVIEW_TTL"] = 60
        with patch("review_checklists.web.time.monotonic", return_value=1000):
            handle = self.handle(self.preview())
            self.assertEqual(self.preview().status_code, 200)
            self.assertEqual(self.preview().status_code, 429)
        with patch("review_checklists.web.time.monotonic", return_value=1061):
            self.assertEqual(self.apply(handle).status_code, 410)
            self.assertEqual(len(self.app.extensions["review_refresh_previews"]), 0)
        self.app.config["REVIEW_REFRESH_CACHE_BYTES"] = 1
        self.assertEqual(self.preview().status_code, 503)
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])

    def test_bundle_upload_has_own_limits_without_loosening_ordinary_forms(self):
        self.assertEqual(self.app.config["MAX_CONTENT_LENGTH"], 256 * 1024)
        self.app.config["REVIEW_REFRESH_MAX_BUNDLE_BYTES"] = 20
        self.assertEqual(self.preview().status_code, 413)

    def test_route_request_cap_and_large_valid_upload(self):
        raw = b" " * (300 * 1024) + json.dumps(self.target).encode()
        response = self.client.post("/review-refresh/preview", data={
            "csrf": self.csrf, "bundle": (io.BytesIO(raw), "large.json"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post("/metadata", data={
            "csrf": self.csrf, "description": "x" * (300 * 1024),
        }).status_code, 413)
        self.app.config["REVIEW_REFRESH_MAX_REQUEST_BYTES"] = 1024
        self.assertEqual(self.preview().status_code, 413)

    def test_invalid_uploads_hashes_and_options_are_not_saved(self):
        before = self.path.read_bytes()
        tampered = deepcopy(self.target)
        tampered["recommendations"][0]["title"] = "Tampered guidance"
        self.assertEqual(self.preview(bundle=tampered).status_code, 400)
        for payload in (b'{"schemaVersion":1,"schemaVersion":1}', b"{bad", b"\xff"):
            response = self.client.post("/review-refresh/preview", data={
                "csrf": self.csrf, "bundle": (io.BytesIO(payload), "bad.json"),
            })
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.preview(add_new="yes").status_code, 400)
        self.assertEqual(self.preview(refresh_scope="unknown-option").status_code, 400)
        self.assertEqual(self.preview(
            refresh_scope="checklist", checklist=(io.BytesIO(b"include: &x {guidSelector: [x]}\nother: *x"), "bad.yaml"),
        ).status_code, 400)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.app.extensions["review_refresh_previews"], {})

    def test_stale_review_and_client_edited_options_require_new_preview(self):
        handle = self.handle(self.preview())
        self.assertEqual(self.apply(handle, add_new="1").status_code, 400)
        self.review.add_evidence(ID, {"rows": ["intervening evidence"]})
        before = self.path.read_bytes()
        self.assertEqual(self.apply(handle).status_code, 409)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.apply(handle).status_code, 410)
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])

    def test_backup_failure_is_visible_and_consumes_preview_without_partial_changes(self):
        handle = self.handle(self.preview())
        before = self.path.read_bytes()
        with patch("review_checklists.refresh._backup", side_effect=OSError("disk full")):
            response = self.apply(handle)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"no changes were committed", response.data)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.apply(handle).status_code, 410)

    def test_comment_autosave_preserves_flag_and_detail_confirmation_checks_revision(self):
        self.apply(self.handle(self.preview()))
        item = self.review.get(ID)
        self.assertEqual(self.client.post(f"/item/{ID}/assessment", data={
            "csrf": self.csrf, "revision": item["revision"], "status": item["status"],
            "comments": "Comment-only autosave",
        }, headers={"Accept": "application/json"}).status_code, 200)
        self.assertTrue(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        self.assertEqual(self.client.post(f"/item/{ID}/update", data={
            "csrf": self.csrf, "revision": item["revision"], "status": item["status"],
            "comments": "Stale detail", "confirm_current_assessment": "1",
        }).status_code, 400)
        self.assertTrue(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        current = self.review.get(ID)
        self.assertEqual(self.client.post(f"/item/{ID}/update", data={
            "csrf": self.csrf, "revision": current["revision"], "status": current["status"],
            "comments": current["comments"], "confirm_current_assessment": "1",
        }).status_code, 303)
        self.assertFalse(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        self.assertEqual(self.review.get(ID)["revision"], current["revision"] + 1)

    def test_preview_and_history_escape_recommendation_text_and_keep_dashboard_route(self):
        target = make_bundle([dict(self.original, title="<script>alert('not executable')</script>")], "safe-html")
        preview = self.preview(bundle=target)
        self.assertNotIn(b"<script>alert", preview.data)
        self.assertIn(b"&lt;script&gt;", preview.data)
        self.apply(self.handle(preview))
        history = self.client.get("/review-refresh/history")
        self.assertNotIn(b"<script>alert", history.data)
        response = self.client.get("/refresh?paginate=1&page=99")
        self.assertEqual(response.status_code, 303)
        self.assertIn("page=1", response.location)
        self.assertNotIn("review-refresh", response.location)

    def test_concurrent_apply_double_click_commits_exactly_once(self):
        handle = self.handle(self.preview())
        cookie = self.client.get_cookie("session").value

        def submit():
            client = self.app.test_client()
            client.set_cookie("session", cookie)
            return client.post("/review-refresh/apply", data={"csrf": self.csrf, "handle": handle}).status_code

        with ThreadPoolExecutor(max_workers=2) as workers:
            statuses = list(workers.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(statuses), [303, 410])
        self.assertEqual(len(self.review.refresh_history()), 1)
        self.assertEqual(len(list(self.root.glob("*before-refresh*"))), 1)

    def test_same_target_no_change_apply_has_no_extra_backup_or_history(self):
        self.assertEqual(self.apply(self.handle(self.preview())).status_code, 303)
        before = self.path.read_bytes()
        preview = self.preview()
        self.assertIn(b"No changes are needed", preview.data)
        self.assertEqual(self.apply(self.handle(preview)).status_code, 303)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.review.refresh_history()), 1)
        self.assertEqual(len(list(self.root.glob("*before-refresh*"))), 1)

    def test_server_cached_target_tampering_is_revalidated(self):
        handle = self.handle(self.preview())
        record = self.app.extensions["review_refresh_previews"][handle]
        record["bundle"]["recommendations"][0]["title"] = "Altered server-held target"
        before = self.path.read_bytes()
        response = self.apply(handle)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"contentHash", response.data)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("*before-refresh*")), [])

    def test_provenance_only_references_are_visible_safe_and_do_not_flag_reassessment(self):
        current = deepcopy(self.original)
        current["provenance"]["upstreamRecommendations"] = [{
            "sourceId": "example-source", "recommendationId": "TEST:01",
            "url": "https://learn.microsoft.com/azure/", "coverage": "supporting",
            "assessedAt": "2026-09-11", "notes": "<script>escaped reference notes</script>",
        }]
        bundle = make_bundle([current, self.second, self.third], "references-only")
        self.assertEqual(self.apply(self.handle(self.preview(bundle=bundle))).status_code, 303)
        self.assertFalse(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        page = self.client.get(f"/item/{ID}")
        self.assertIn(b"example-source / TEST:01", page.data)
        self.assertIn(b"&lt;script&gt;escaped reference notes&lt;/script&gt;", page.data)
        self.assertNotIn(b"<script>escaped", page.data)
        self.assertIn(b'href="https://learn.microsoft.com/azure/"', page.data)
        current["provenance"]["upstreamRecommendations"][0]["url"] = "javascript:alert(1)"
        with self.review.connection() as connection:
            connection.execute("UPDATE items SET recommendation = ? WHERE id = ?", (json.dumps(current), ID))
        self.assertNotIn(b'href="javascript:', self.client.get(f"/item/{ID}").data)


if __name__ == "__main__":
    unittest.main()
