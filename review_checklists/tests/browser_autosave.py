"""Opt-in autosave checks against real Chrome, fake Azure and temporary SQLite."""

from datetime import datetime
import threading
from time import perf_counter
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect

from review_checklists.tests.browser_forms import BrowserFixture
from review_checklists.tests.test_prototype import ID, RECO


MANUAL = "ffffffff-ffff-ffff-ffff-ffffffffffff"


class BrowserAutosaveTests(BrowserFixture):
    def recommendations(self):
        return [dict(RECO), dict(RECO, id=MANUAL, title="Offline manual check", queries={})]

    def open_list(self, query=""):
        self.page.goto(self.base + "/" + query)
        expect(self.page.locator("#autosave-mode")).to_contain_text("Autosave enabled")

    def cell(self, item_id=ID):
        return self.page.locator(f'[data-assessment="assessment-{item_id}"]')

    def status(self, item_id=ID):
        return self.cell(item_id).locator('select[name="status"]')

    def comments(self, item_id=ID):
        cell = self.cell(item_id)
        details = cell.locator(".comments-editor")
        if not details.evaluate("(element) => element.open"):
            details.locator("summary").click()
        return cell.locator('textarea[name="comments"]')

    def saved(self, item_id=ID):
        expect(self.cell(item_id).locator(".save-state")).to_have_text("Saved")

    def test_quick_status_and_offline_comments_autosave_without_metadata_or_azure(self):
        self.open_list()
        expect(self.cell().locator(".save-state")).to_have_text("No unsaved changes", use_inner_text=True)
        expect(self.cell().locator(".save-assessment")).to_be_hidden()
        self.status().select_option("Compliant")
        self.saved()
        notes = self.comments(MANUAL)
        notes.fill("Offline interview: exception approved.")
        self.saved(MANUAL)
        self.assertEqual(self.review.get(ID)["status"], "Compliant")
        self.assertEqual(self.review.get(MANUAL)["comments"], "Offline interview: exception approved.")
        self.assertEqual(self.review.metadata["description"], "")
        self.assertEqual(self.review.evidence(MANUAL), [])
        self.executor.assert_not_called()
        self.lookup.assert_not_called()
        self.page.reload()
        self.assertEqual(self.comments(MANUAL).input_value(), "Offline interview: exception approved.")

    def test_comments_debounce_and_blur_save(self):
        self.open_list()
        self.page.clock.install(time=datetime(2026, 1, 1))
        self.page.clock.pause_at(datetime(2026, 1, 1, 0, 0, 1))
        notes = self.comments()
        posts = []
        self.page.on("request", lambda request: posts.append(request)
                     if request.method == "POST" else None)
        notes.fill("First")
        self.page.clock.run_for(250)
        notes.fill("Second")
        self.page.clock.run_for(699)
        self.assertEqual(posts, [])
        expect(self.cell().locator(".save-state")).to_have_text("Unsaved")
        self.page.clock.run_for(1)
        self.saved()
        self.assertEqual(len(posts), 1)
        self.assertEqual(self.review.get(ID)["revision"], 1)
        notes.fill("Blur saves promptly")
        with self.page.expect_response("**/assessment", timeout=1500):
            notes.blur()
        self.saved()
        self.assertEqual(len(posts), 2)
        self.assertEqual(self.review.get(ID)["comments"], "Blur saves promptly")

    def test_typing_and_status_changes_during_delayed_request_are_serialized(self):
        self.open_list()
        notes = self.comments()
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        update = self.review.update
        calls = []

        def delayed_update(*args):
            calls.append(args)
            if len(calls) == 1:
                started.set()
                if not release.wait(10):
                    raise RuntimeError("Test failed to release delayed save")
            update(*args)

        with patch.object(self.review, "update", side_effect=delayed_update):
            notes.fill("First draft")
            notes.blur()
            expect(self.cell().locator(".save-state")).to_contain_text("Saving")
            self.assertTrue(started.wait(3))
            notes.fill("New text while saving")
            self.status().select_option("Not applicable")
            notes.fill("Newest text is never dropped")
            self.page.wait_for_timeout(850)
            self.assertEqual(len(calls), 1)
            release.set()
            self.saved()
        self.assertEqual(len(calls), 2)
        self.assertEqual([call[3] for call in calls], [0, 1])
        self.assertEqual(calls[0][2], "First draft")
        self.assertEqual(calls[1][1:3], ("Not applicable", "Newest text is never dropped"))
        self.assertEqual(self.review.get(ID)["revision"], 2)
        self.assertEqual(notes.input_value(), "Newest text is never dropped")

    def test_stale_editor_conflict_retains_draft_and_stops_automatic_retries(self):
        self.open_list()
        other = self.browser.new_page()
        self.addCleanup(other.close)
        other.goto(self.base)
        other.locator(f'[data-assessment="assessment-{ID}"] select').select_option("Compliant")
        expect(other.locator(f'[data-assessment="assessment-{ID}"] .save-state')).to_have_text("Saved")
        notes = self.comments()
        notes.fill("My conflicting draft")
        expect(self.cell().locator(".save-state")).to_contain_text("Error (conflict)")
        self.assertEqual(notes.input_value(), "My conflicting draft")
        expect(self.cell().locator(".save-assessment")).to_be_disabled()
        expect(self.cell().locator(".conflict-help")).to_be_visible()
        notes.fill("Keep editing conflict draft")
        notes.blur()
        self.page.wait_for_timeout(900)
        self.assertEqual(self.review.get(ID)["revision"], 1)
        self.assertEqual(self.review.get(ID)["status"], "Compliant")
        self.assertEqual(self.review.get(ID)["comments"], "")
        self.assertEqual(notes.input_value(), "Keep editing conflict draft")

    def test_network_failure_retains_draft_until_explicit_retry(self):
        self.open_list()
        attempts = []

        def offline(route):
            attempts.append(route.request)
            route.abort("internetdisconnected")

        self.page.route("**/assessment", offline)
        notes = self.comments()
        notes.fill("Retain this offline draft")
        expect(self.cell().locator(".save-state")).to_contain_text("Error (network)")
        notes.fill("Even newer offline draft")
        notes.blur()
        self.page.wait_for_timeout(900)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(self.review.get(ID)["revision"], 0)
        self.page.unroute("**/assessment", offline)
        self.cell().get_by_role("button", name="Retry save").click()
        self.saved()
        self.assertEqual(self.review.get(ID)["comments"], "Even newer offline draft")
        self.assertEqual(self.review.get(ID)["revision"], 1)

    def test_timeout_retains_draft_and_does_not_retry_automatically(self):
        self.open_list()
        self.page.clock.install(time=datetime(2026, 1, 1))
        self.page.clock.pause_at(datetime(2026, 1, 1, 0, 0, 1))
        pending = []
        self.page.route("**/assessment", lambda route: pending.append(route))
        self.status().select_option("Non-compliant")
        expect(self.cell().locator(".save-state")).to_contain_text("Saving")
        self.page.clock.run_for(15000)
        expect(self.cell().locator(".save-state")).to_contain_text("timed out")
        self.assertEqual(self.status().input_value(), "Non-compliant")
        self.page.clock.run_for(30000)
        self.assertEqual(len(pending), 1)
        self.assertEqual(self.review.get(ID)["revision"], 0)
        pending[0].abort("failed")
        self.page.unroute("**/assessment")
        self.cell().get_by_role("button", name="Retry save").click()
        self.saved()

    def test_edits_while_script_loads_are_not_mistaken_for_saved_values(self):
        scripts = []
        self.page.route("**/autosave.js", lambda route: scripts.append(route))
        self.page.goto(self.base, wait_until="commit")
        expect(self.page.locator("#autosave-mode")).to_contain_text("Autosave is not enabled")
        self.status().select_option("Not applicable")
        self.comments().fill("Typed before script initialization")
        self.assertEqual(self.review.get(ID)["revision"], 0)
        scripts[0].continue_()
        expect(self.page.locator("#autosave-mode")).to_contain_text("Autosave enabled")
        self.saved()
        self.assertEqual(self.review.get(ID)["status"], "Not applicable")
        self.assertEqual(self.review.get(ID)["comments"], "Typed before script initialization")

    def test_lost_acknowledgement_does_not_skip_revision_or_claim_saved(self):
        self.open_list()

        def lose_response(route):
            response = route.fetch()
            self.assertEqual(response.status, 200)
            route.abort("failed")

        self.page.route("**/assessment", lose_response)
        self.status().select_option("Compliant")
        expect(self.cell().locator(".save-state")).to_contain_text("Error (network)")
        self.assertEqual(self.review.get(ID)["revision"], 1)
        # Even a draft reverted to the page-load values has an uncertain outstanding write.
        self.status().select_option("Not reviewed")
        self.page.unroute("**/assessment", lose_response)
        self.cell().get_by_role("button", name="Retry save").click()
        expect(self.cell().locator(".save-state")).to_contain_text("Error (conflict)")
        self.assertEqual(self.review.get(ID)["status"], "Compliant")
        self.assertEqual(self.status().input_value(), "Not reviewed")
        self.assertEqual(self.review.get(ID)["revision"], 1)

    def test_server_errors_are_visible_and_retain_input(self):
        self.open_list()
        for kind, code in (("validation", 400), ("auth", 403), ("storage", 500)):
            with self.subTest(kind=kind):
                def fail(route):
                    route.fulfill(status=code, json={
                        "error": {"kind": kind, "message": f"Test {kind} failure"},
                    })
                self.page.route("**/assessment", fail)
                self.status().select_option("Non-compliant")
                if kind != "validation":
                    self.cell().get_by_role("button", name="Retry save").click()
                expect(self.cell().locator(".save-state")).to_contain_text(f"Error ({kind})")
                self.assertEqual(self.status().input_value(), "Non-compliant")
                self.page.unroute("**/assessment")
        self.cell().get_by_role("button", name="Retry save").click()
        self.saved()
        self.assertEqual(self.review.get(ID)["revision"], 1)

    def test_external_form_ownership_and_arg_post_excludes_assessment_fields(self):
        self.open_list("?waf=security&paginate=1")
        form = self.page.locator("#run-selection")
        names = form.evaluate("(form) => Array.from(new FormData(form).keys())")
        self.assertNotIn("status", names)
        self.assertNotIn("comments", names)
        self.assertNotIn("revision", names)
        self.assertEqual(names.count("csrf"), 1)
        self.status().focus()
        for name in ("status", "comments"):
            self.assertEqual(self.cell().locator(f'[name="{name}"]').evaluate(
                "(control) => control.form.id"), f"assessment-{ID}")
        self.assertEqual(self.page.locator(f'input[name="selected"][value="{ID}"]').evaluate(
            "(control) => control.form.id"), "run-selection")
        self.assertEqual(self.page.locator("form form").count(), 0)
        self.status().select_option("Non-compliant")
        self.saved()
        self.page.locator(f'input[name="selected"][value="{ID}"]').check()
        response = self.post_click(
            self.page.get_by_role("button", name="Run selected queries", exact=True), "/run-selected",
        )
        posted = parse_qs(response.request.post_data)
        self.assertEqual(posted["selected"], [ID])
        self.assertNotIn("status", posted)
        self.assertNotIn("comments", posted)
        self.assertNotIn("revision", posted)
        self.executor.assert_called_once()
        self.assertEqual(self.review.get(ID)["status"], "Non-compliant")

    def test_overview_explicitly_stale_and_refresh_retains_filters_and_pagination(self):
        query = "?status=Not+reviewed&waf=security&severity=medium&paginate=1&page=1"
        self.open_list(query)
        self.status().select_option("Compliant")
        self.saved()
        expect(self.page.locator("#overview-stale")).to_be_visible()
        expect(self.page.locator("#overview-title")).to_have_text("Assessment overview (needs refresh)")
        self.assertEqual(self.page.locator("tbody tr").count(), 2)
        self.page.get_by_role("link", name="Refresh overview and list").click()
        self.page.wait_for_load_state("networkidle")
        expect(self.page.locator("#overview-stale")).to_be_hidden()
        self.assertEqual(self.page.locator("tbody tr").count(), 1)
        self.assertEqual(parse_qs(urlsplit(self.page.url).query), parse_qs(query[1:]))
        self.assertEqual(self.cell().count(), 0)

    def test_pending_edits_block_all_other_forms_and_links_and_warn_beforeunload(self):
        self.open_list()
        self.page.locator("#review-details summary").click()
        self.page.locator(f'input[name="selected"][value="{ID}"]').check()
        self.page.route("**/assessment", lambda route: route.abort("failed"))
        notes = self.comments()
        notes.fill("Draft must survive navigation")
        expect(self.cell().locator(".save-state")).to_contain_text("Error (network)")
        dialogs = []

        def dismiss(dialog):
            dialogs.append((dialog.type, dialog.message))
            dialog.dismiss()

        self.page.on("dialog", dismiss)
        for button in ("Filter", "Save review details", "Run selected queries",
                       "Show Azure CLI subscription"):
            self.page.get_by_role("button", name=button, exact=True).click()
            self.assertEqual(dialogs[-1][0], "alert")
            self.assertIn("Unsaved or in-flight", dialogs[-1][1])
            self.assertEqual(notes.input_value(), "Draft must survive navigation")
        self.page.get_by_role("link", name=RECO["title"], exact=True).click()
        self.assertEqual(len(dialogs), 5)
        # Browser reload triggers the native beforeunload prompt; dismiss keeps the draft.
        self.page.evaluate("() => { location.reload(); }")
        expect(notes).to_have_value("Draft must survive navigation")
        self.page.wait_for_timeout(100)
        self.assertEqual(dialogs[-1][0], "beforeunload")
        self.executor.assert_not_called()
        self.lookup.assert_not_called()
        self.assertEqual(self.review.get(ID)["revision"], 0)

    def test_inflight_navigation_is_guarded_and_independent_rows_can_save(self):
        self.open_list()
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        update = self.review.update

        def delayed_update(item_id, *args):
            if item_id == ID:
                started.set()
                if not release.wait(10):
                    raise RuntimeError("Test failed to release delayed save")
            update(item_id, *args)

        with patch.object(self.review, "update", side_effect=delayed_update):
            self.status().select_option("Compliant")
            expect(self.cell().locator(".save-state")).to_contain_text("Saving")
            self.assertTrue(started.wait(3))
            self.status(MANUAL).select_option("Not applicable")
            self.saved(MANUAL)
            dialogs = []

            def dismiss(dialog):
                dialogs.append(dialog.message)
                dialog.dismiss()

            self.page.on("dialog", dismiss)
            self.page.get_by_role("button", name="Filter", exact=True).click()
            self.assertEqual(len(dialogs), 1)
            self.assertIn("Unsaved or in-flight", dialogs[0])
            self.assertEqual(self.review.get(ID)["revision"], 0)
            release.set()
            self.saved()

    def test_no_javascript_and_missing_script_use_explicit_form_save(self):
        for javascript, blocked in ((False, None), (True, "**/autosave.js"), (True, "**/static/*.js")):
            with self.subTest(javascript=javascript, blocked=blocked):
                context = self.browser.new_context(java_script_enabled=javascript)
                try:
                    page = context.new_page()
                    if blocked:
                        page.route(blocked, lambda route: route.abort("failed"))
                    page.goto(self.base + "/?waf=security&paginate=1")
                    expect(page.locator("#autosave-mode")).to_contain_text("Autosave is not enabled")
                    cell = page.locator(f'[data-assessment="assessment-{MANUAL}"]')
                    cell.locator("select").select_option("Not applicable")
                    cell.locator("summary").click()
                    cell.locator("textarea").fill(f"Manual save with JS={javascript}")
                    cell.get_by_role("button", name="Save assessment", exact=True).click()
                    page.wait_for_load_state("networkidle")
                    self.assertEqual(self.review.get(MANUAL)["comments"], f"Manual save with JS={javascript}")
                    self.assertEqual(self.review.get(MANUAL)["status"], "Not applicable")
                    self.assertEqual(parse_qs(urlsplit(page.url).query),
                                     {"waf": ["security"], "paginate": ["1"]})
                    self.assertEqual(self.review.get(ID)["revision"], 0)
                finally:
                    context.close()
        self.executor.assert_not_called()
        self.lookup.assert_not_called()

    def test_missing_bootstrap_keeps_native_forms_and_autosave_working(self):
        self.page.route("**/assessment-forms.js", lambda route: route.abort("failed"))
        self.open_list()
        self.assertEqual(self.page.locator("form.assessment-form").count(), 2)
        self.status().select_option("Compliant")
        self.saved()
        self.assertEqual(self.review.get(ID)["status"], "Compliant")


class BrowserLargeListAutosaveTests(BrowserFixture):
    def recommendations(self):
        return [dict(RECO, id=f"{index:04}", title=f"Recommendation {index}", queries={})
                for index in range(2000)]

    def test_all_two_thousand_rows_have_compact_editors_and_last_row_saves(self):
        self.page.add_init_script("""
            window.formDataBuilds = 0;
            window.formElementsReads = 0;
            window.FormData = new Proxy(window.FormData, {
                construct(target, args) {
                    window.formDataBuilds++;
                    return Reflect.construct(target, args);
                }
            });
            const elements = Object.getOwnPropertyDescriptor(HTMLFormElement.prototype, "elements");
            Object.defineProperty(HTMLFormElement.prototype, "elements", {
                get() {
                    window.formElementsReads++;
                    return elements.get.call(this);
                }
            });
        """)
        start = perf_counter()
        self.page.goto(self.base, timeout=10000)
        expect(self.page.locator("#autosave-mode")).to_contain_text("Autosave enabled", timeout=10000)
        usable = perf_counter() - start
        self.assertEqual(self.page.locator("tbody tr").count(), 2000)
        self.assertEqual(self.page.locator(".comments-editor[open]").count(), 0)
        self.assertEqual(self.page.locator("[data-assessment]").count(), 2000)
        self.assertEqual(self.page.locator("form.assessment-form").count(), 0)
        self.assertEqual(self.page.locator("[data-save-state]").count(), 0)
        self.assertEqual(self.page.evaluate("window.formDataBuilds"), 0)
        self.assertEqual(self.page.evaluate("window.formElementsReads"), 0)
        last = self.page.locator('[data-assessment="assessment-1999"]')
        last.locator("select").select_option("Compliant")
        expect(last.locator(".save-state")).to_have_text("Saved")
        saved = perf_counter() - start
        self.assertEqual(self.review.get("1999")["status"], "Compliant")
        self.assertEqual(self.page.locator("form.assessment-form").count(), 1)
        self.assertEqual(self.page.locator("[data-save-state]").count(), 1)
        self.assertEqual(self.page.evaluate("window.formDataBuilds"), 1)
        print(f"\n{type(self).__name__}: usable {usable:.2f}s; last-row save {saved:.2f}s", flush=True)
        self.assertLess(saved, 10, "2,000-row load plus an acknowledged edit must take under 10 seconds")
        last.locator("summary").click()
        last.locator("textarea").fill("Last-row notes still work with lazy native form ownership")
        last.locator("textarea").blur()
        expect(last.locator(".save-state")).to_have_text("Saved")
        self.assertEqual(self.review.get("1999")["comments"],
                         "Last-row notes still work with lazy native form ownership")
        expect(last.locator("textarea")).to_be_in_viewport()
        self.assertEqual(last.evaluate("element => getComputedStyle(element).contentVisibility"), "auto")
        self.page.emulate_media(media="print")
        self.assertEqual(last.evaluate("element => getComputedStyle(element).contentVisibility"), "visible")
        self.page.emulate_media(media="screen")
        self.assertEqual(self.review.get("0000")["revision"], 0)
        self.executor.assert_not_called()
        self.lookup.assert_not_called()


class BrowserLargeQueryListAutosaveTests(BrowserLargeListAutosaveTests):
    def recommendations(self):
        return [dict(reco, queries=RECO["queries"] if index % 2 else {})
                for index, reco in enumerate(super().recommendations())]


if __name__ == "__main__":
    unittest.main()
