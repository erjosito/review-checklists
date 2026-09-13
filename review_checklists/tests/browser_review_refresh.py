"""Real-browser refresh checks using temporary schema-1 reviews and fake Azure."""

import json
from unittest.mock import patch
from urllib.parse import urlsplit

from playwright.sync_api import expect

from review_checklists.catalog import make_bundle
from review_checklists.tests.browser_forms import BrowserFixture
from review_checklists.tests.test_review_refresh import ID, SECOND, THIRD, recommendation
from review_checklists.web import create_app


NEW = "44444444-4444-4444-4444-444444444444"


class BrowserReviewRefreshTests(BrowserFixture):
    def recommendations(self):
        return [recommendation(), recommendation(SECOND), recommendation(THIRD)]

    def setUp(self):
        def capture_app(*args, **kwargs):
            self.app = create_app(*args, **kwargs)
            return self.app

        with patch("review_checklists.tests.browser_forms.create_app", side_effect=capture_app):
            super().setUp()
        self.review.update(ID, "Compliant", "Preserved browser notes", 0)
        self.review.add_evidence(ID, {
            "outcome": "success", "rows": [{"id": "offline evidence"}],
            "completed_at": "2026-09-11T12:00:00+00:00", "subscriptions": [],
            "query": "resources",
        })
        with self.review.connection() as connection:
            connection.execute("DROP TABLE refresh_item_state")
            connection.execute("DROP TABLE refresh_history")
            connection.execute("DELETE FROM metadata WHERE key = 'review_scope'")
            connection.execute("PRAGMA user_version = 1")
        self.target = make_bundle([
            dict(recommendation(), title="Refreshed browser guidance",
                 aliases=[{"id": SECOND, "name": recommendation(SECOND)["name"]}]),
            recommendation(NEW),
        ], "browser-new-source")

    def submit(self, name, path, status=200):
        with self.page.expect_response(
            lambda response: response.request.method == "POST" and urlsplit(response.url).path == path,
        ) as pending:
            self.page.get_by_role("button", name=name, exact=True).click()
        response = pending.value
        self.assertEqual(response.status, status)
        self.assertEqual(response.request.headers.get("origin"), self.base)
        self.page.wait_for_load_state("networkidle")
        return response

    def upload(self):
        self.page.goto(self.base + "/review-refresh", wait_until="networkidle")
        self.page.get_by_label("Versioned JSON bundle", exact=True).set_input_files({
            "name": "bundle.json", "mimeType": "application/json",
            "buffer": json.dumps(self.target).encode("utf-8"),
        })

    def test_preview_apply_history_preserves_schema1_data_and_deliberate_acknowledgment(self):
        before = self.review.path.read_bytes()
        evidence = self.review.evidence(ID)
        self.upload()
        expect(self.page.get_by_label("Add new checks within the selected scope", exact=True)).not_to_be_checked()
        self.submit("Preview review refresh", "/review-refresh/preview")
        self.assertEqual(self.review.path.read_bytes(), before)
        expect(self.page.get_by_role("heading", name="Consolidation groups")).to_be_visible()
        expect(self.page.locator(".refresh-change")).to_have_count(3)
        self.submit("Apply this review refresh", "/review-refresh/apply", 303)
        expect(self.page.get_by_role("heading", name="Review refresh history", exact=True)).to_be_visible()
        self.assertEqual({item["id"] for item in self.review.items()}, {ID, SECOND, THIRD})
        self.assertEqual(self.review.evidence(ID), evidence)
        self.assertEqual(self.review.get(ID)["comments"], "Preserved browser notes")
        self.assertEqual(self.review.get(ID)["status"], "Compliant")
        self.assertEqual(len(self.review.refresh_history()), 1)
        self.page.get_by_role("link", name="Return to assessments", exact=True).click()
        expect(self.page.locator("#guidance-assessment-warning")).to_contain_text("Historical saved assessments")
        expect(self.page.locator("#guidance-assessment-warning")).to_contain_text("1 matching checks need reassessment")
        self.page.get_by_role("link", name="Refreshed browser guidance", exact=True).click()
        self.page.wait_for_url(f"{self.base}/item/{ID}")
        self.page.locator('textarea[name="comments"]').fill("New comment, same decision")
        self.submit("Save assessment", f"/item/{ID}/update", 303)
        self.assertTrue(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        self.page.get_by_label("I reviewed the refreshed guidance and confirm the current assessment", exact=True).check()
        self.submit("Save assessment", f"/item/{ID}/update", 303)
        self.assertFalse(self.review.get(ID)["refresh_state"]["needs_reassessment"])
        report = self.page.request.get(self.base + "/export/html")
        self.assertEqual(report.status, 200)
        self.assertIn("Superseded", report.text())
        self.assertIn("No longer current", report.text())
        self.assertIn("offline evidence", report.text())
        self.executor.assert_not_called()
        self.lookup.assert_not_called()

    def test_unknown_scope_rejected_then_explicit_all_adds_unreviewed_check(self):
        self.upload()
        self.page.get_by_label("Add new checks within the selected scope", exact=True).check()
        self.submit("Preview review refresh", "/review-refresh/preview", 400)
        self.assertEqual(len(self.review.items()), 3)
        self.upload()
        self.page.get_by_label("Add new checks within the selected scope", exact=True).check()
        self.page.get_by_label("Explicitly use all-corpus scope", exact=True).check()
        self.submit("Preview review refresh", "/review-refresh/preview")
        self.submit("Apply this review refresh", "/review-refresh/apply", 303)
        self.assertEqual(self.review.get(NEW)["status"], "Not reviewed")
        self.assertEqual(json.loads(self.review.metadata["review_scope"]), {"kind": "all"})

    def test_expired_oversized_wrong_csrf_and_stale_previews_do_not_apply(self):
        before = self.review.path.read_bytes()
        self.app.config["REVIEW_REFRESH_PREVIEW_TTL"] = 0
        self.upload()
        self.submit("Preview review refresh", "/review-refresh/preview")
        self.submit("Apply this review refresh", "/review-refresh/apply", 410)
        self.app.config["REVIEW_REFRESH_PREVIEW_TTL"] = 900
        self.app.config["REVIEW_REFRESH_MAX_BUNDLE_BYTES"] = 100
        self.upload()
        self.submit("Preview review refresh", "/review-refresh/preview", 413)
        self.app.config["REVIEW_REFRESH_MAX_BUNDLE_BYTES"] = 12 * 1024 * 1024
        self.upload()
        self.page.locator('input[name="csrf"]').evaluate("(input) => { input.value = 'wrong'; }")
        self.submit("Preview review refresh", "/review-refresh/preview", 403)
        self.assertEqual(self.review.path.read_bytes(), before)
        self.upload()
        self.submit("Preview review refresh", "/review-refresh/preview")
        self.review.update_metadata(description="Concurrent browser-independent edit")
        changed = self.review.path.read_bytes()
        self.submit("Apply this review refresh", "/review-refresh/apply", 409)
        self.assertEqual(self.review.path.read_bytes(), changed)
        self.assertEqual(self.review.refresh_history(), [])
        self.assertEqual(list(self.review.path.parent.glob("*before-refresh*")), [])

    def test_browser_session_binding_and_duplicate_apply_cannot_replay(self):
        self.upload()
        self.submit("Preview review refresh", "/review-refresh/preview")
        handle = self.page.locator('input[name="handle"]').input_value()
        csrf = self.page.locator('input[name="csrf"]').input_value()
        other = self.browser.new_context()
        try:
            second = other.new_page()
            second.goto(self.base + "/review-refresh")
            other_csrf = second.locator('input[name="csrf"]').input_value()
            response = other.request.post(self.base + "/review-refresh/apply",
                                          form={"csrf": other_csrf, "handle": handle})
            self.assertEqual(response.status, 403)
        finally:
            other.close()
        self.submit("Apply this review refresh", "/review-refresh/apply", 303)
        response = self.page.request.post(self.base + "/review-refresh/apply",
                                         form={"csrf": csrf, "handle": handle})
        self.assertEqual(response.status, 410)
        self.assertEqual(len(self.review.refresh_history()), 1)
        self.assertEqual(len(list(self.review.path.parent.glob("*before-refresh*"))), 1)

    def test_unsaved_inline_draft_blocks_refresh_and_history_navigation(self):
        self.page.route("**/item/*/assessment", lambda route: route.fulfill(
            status=500, content_type="application/json",
            body=json.dumps({"error": {"kind": "storage", "message": "Synthetic failed save"}}),
        ))
        self.page.goto(self.base, wait_until="networkidle")
        expect(self.page.locator("#autosave-mode")).to_contain_text("Autosave enabled")
        form = self.page.locator(f'[data-assessment="assessment-{ID}"]')
        form.locator("summary").click()
        form.locator('textarea[name="comments"]').fill("Unsaved draft must survive")
        expect(form.locator(".save-state")).to_contain_text("Error")
        for link in ("Refresh saved review guidance", "Review refresh history"):
            self.page.once("dialog", lambda dialog: dialog.accept())
            self.page.get_by_role("link", name=link, exact=True).click()
            self.assertEqual(urlsplit(self.page.url).path, "/")
            expect(form.locator('textarea[name="comments"]')).to_have_value("Unsaved draft must survive")
        self.assertEqual(self.review.get(ID)["comments"], "Preserved browser notes")
        self.executor.assert_not_called()
        self.lookup.assert_not_called()


if __name__ == "__main__":
    import unittest
    unittest.main()
