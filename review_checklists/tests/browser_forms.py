"""Opt-in real-browser regression checks, using fake Azure and an isolated review."""

from copy import deepcopy
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from waitress import create_server

from review_checklists.review import Review
from review_checklists.tests.test_prototype import ID, RECO, SCOPE
from review_checklists.tests.test_query_availability import cost_recommendations
from review_checklists.web import create_app


class BrowserFixture(unittest.TestCase):
    def recommendations(self):
        return [deepcopy(RECO)]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.review = Review.create(root / "review.sqlite3", "Browser test", self.recommendations(), root)
        self.lookup = Mock(return_value={"id": SCOPE, "name": "Offline subscription"})
        self.executor = Mock(return_value={"rows": [], "truncated": False})
        app = create_app(self.review, self.executor, self.lookup)
        self.server = create_server(app, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser = self.playwright.chromium.launch(
            headless=True, channel=os.environ.get("REVIEW_TEST_BROWSER_CHANNEL") or None,
        )
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page()
        self.base = f"http://127.0.0.1:{self.server.effective_port}"

    def stop_server(self):
        self.server.close()
        self.thread.join(timeout=5)

    def post_click(self, button, path):
        with self.page.expect_response(
            lambda response: response.request.method == "POST" and urlsplit(response.url).path == path,
            timeout=20000,
        ) as result:
            button.click()
        response = result.value
        self.assertEqual(response.request.headers.get("origin"), self.base)
        self.assertLess(response.status, 400)
        self.page.wait_for_load_state("networkidle")
        return response


class BrowserFormTests(BrowserFixture):
    def test_preview_button_submits_in_browser_and_scrolls_to_result(self):
        self.page.goto(self.base, wait_until="networkidle")
        self.page.locator(f'input[name="selected"][value="{ID}"]').check()
        self.post_click(
            self.page.get_by_role("button", name="Show Azure CLI subscription", exact=True),
            "/azure-context",
        )
        self.assertTrue(self.page.locator('input[value="current"]').is_checked())
        self.assertEqual(self.page.locator('input[name="scope_mode"]').count(), 2)
        self.assertEqual(self.page.locator('input[value="active"]').count(), 0)
        self.assertTrue(self.page.locator(f'input[name="selected"][value="{ID}"]').is_checked())
        self.assertEqual(urlsplit(self.page.url).fragment, "query-scope")
        self.lookup.assert_called_once_with()
        self.executor.assert_not_called()

    def test_current_subscription_runs_selected_check_without_preview_or_id(self):
        self.page.goto(self.base, wait_until="networkidle")
        self.assertTrue(self.page.locator('input[value="current"]').is_checked())
        self.page.locator(f'input[name="selected"][value="{ID}"]').check()
        self.post_click(self.page.get_by_role("button", name="Run selected queries", exact=True),
                        "/run-selected")
        self.lookup.assert_called_once_with()
        self.executor.assert_called_once_with(RECO["queries"]["arg"], [SCOPE])
        self.assertEqual(self.review.get(ID)["status"], "Not reviewed")

    def test_single_check_form_and_assessment_save_work_in_browser(self):
        self.page.goto(f"{self.base}/item/{ID}", wait_until="networkidle")
        self.page.locator('select[name="status"]').select_option("Non-compliant")
        self.post_click(self.page.get_by_role("button", name="Save assessment", exact=True),
                        f"/item/{ID}/update")
        self.assertEqual(self.review.get(ID)["status"], "Non-compliant")
        self.post_click(self.page.get_by_role("button", name="Run query and save evidence", exact=True),
                        f"/item/{ID}/run")
        self.executor.assert_called_once_with(RECO["queries"]["arg"], [SCOPE])


class BrowserQueryAvailabilityTests(BrowserFixture):
    def recommendations(self):
        return cost_recommendations()

    def test_runnable_link_resolves_disabled_first_page_without_running_queries(self):
        self.page.goto(self.base + "/?waf=cost", wait_until="networkidle")
        self.assertTrue(self.page.get_by_role("button", name="Run selected queries", exact=True).is_disabled())
        self.assertIn("2 of 52 matching checks", self.page.locator("#query-availability").inner_text())
        self.page.get_by_role("link", name="Show only checks with ARG queries", exact=True).click()
        self.page.wait_for_load_state("networkidle")
        self.assertFalse(self.page.get_by_role("button", name="Run selected queries", exact=True).is_disabled())
        self.assertEqual(self.page.locator('input[name="selected"]').count(), 2)
        self.assertTrue(self.page.locator('input[name="with_arg"]').is_checked())
        self.assertTrue(self.page.locator('input[name="waf"][value="cost"]').is_checked())
        self.lookup.assert_not_called()
        self.executor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
