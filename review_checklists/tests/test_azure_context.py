import json
import subprocess
from unittest import TestCase
from unittest.mock import Mock, patch

from review_checklists.azure_context import get_cli_subscription
from review_checklists.corpus import ReviewError
from review_checklists.tests.test_prototype import ID, RECO, ReviewFixture, SCOPE
from review_checklists.web import create_app


OTHER_SCOPE = "22222222-2222-2222-2222-222222222222"
ACCOUNT = {"id": SCOPE, "name": "Development"}


class AzureContextTests(TestCase):
    def cli_result(self, stdout, returncode=0, stderr=""):
        return subprocess.CompletedProcess(["az"], returncode, stdout, stderr)

    def test_lookup_reads_only_selected_subscription_with_bounded_command(self):
        with patch("review_checklists.azure_context.shutil.which", return_value=r"C:\Azure CLI\az.cmd"), patch(
            "review_checklists.azure_context.subprocess.run",
            return_value=self.cli_result(json.dumps(ACCOUNT)),
        ) as run:
            self.assertEqual(get_cli_subscription(), ACCOUNT)
        self.assertEqual(run.call_args.args[0], [
            r"C:\Azure CLI\az.cmd", "account", "show", "--query", "{id:id,name:name}",
            "--output", "json", "--only-show-errors",
        ])
        self.assertEqual(run.call_args.kwargs["timeout"], 15)
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["env"]["PYTHONIOENCODING"], "utf-8")
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_missing_cli_and_not_logged_in_are_actionable_errors(self):
        with patch("review_checklists.azure_context.shutil.which", return_value=None), patch(
            "review_checklists.azure_context.subprocess.run",
        ) as run:
            with self.assertRaisesRegex(ReviewError, "not found"):
                get_cli_subscription()
            run.assert_not_called()
        with patch("review_checklists.azure_context.shutil.which", return_value="az"), patch(
            "review_checklists.azure_context.subprocess.run",
            return_value=self.cli_result("", returncode=1, stderr="Please run az login"),
        ):
            with self.assertRaisesRegex(ReviewError, "az login"):
                get_cli_subscription()

    def test_timeout_and_launch_failure_are_explicit(self):
        for error, message in (
            (subprocess.TimeoutExpired("az", 15), "timed out"),
            (OSError("Cannot launch"), "Cannot read"),
        ):
            with self.subTest(error=error), patch(
                "review_checklists.azure_context.shutil.which", return_value="az",
            ), patch("review_checklists.azure_context.subprocess.run", side_effect=error):
                with self.assertRaisesRegex(ReviewError, message):
                    get_cli_subscription()

    def test_malformed_output_and_missing_fields_do_not_invent_a_subscription(self):
        for output in ("not-json", "null", "[]", "{}", '{"id":"bad","name":"Test"}',
                       json.dumps({"id": SCOPE, "name": ""})):
            with self.subTest(output=output), patch(
                "review_checklists.azure_context.shutil.which", return_value="az",
            ), patch("review_checklists.azure_context.subprocess.run", return_value=self.cli_result(output)):
                with self.assertRaises(ReviewError):
                    get_cli_subscription()


class AzureContextWebTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        self.lookup = Mock(return_value=dict(ACCOUNT))
        self.executor = Mock(return_value={"rows": [], "truncated": False})
        self.app = create_app(self.review, self.executor, self.lookup)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def csrf(self):
        self.client.get("/")
        with self.client.session_transaction() as session:
            return session["csrf"]

    def show_context(self, item=False, **fields):
        path = f"/item/{ID}/azure-context" if item else "/azure-context"
        return self.client.post(path + "?with_arg=1", data={"csrf": self.csrf(), **fields})

    def test_lookup_is_opt_in_preserves_selection_and_runs_no_queries(self):
        self.client.get("/")
        self.client.get(f"/item/{ID}")
        self.lookup.assert_not_called()
        response = self.show_context(selected=[ID], subscriptions=OTHER_SCOPE)
        self.assertEqual(response.status_code, 200)
        self.lookup.assert_called_once_with()
        self.executor.assert_not_called()
        self.assertIn(b"Development", response.data)
        self.assertIn(SCOPE.encode(), response.data)
        self.assertIn(b'value="current" checked', response.data)
        self.assertNotIn(b'value="active"', response.data)
        self.assertEqual(response.data.count(b'name="scope_mode"'), 2)
        self.assertIn(f'name="selected" value="{ID}" checked'.encode(), response.data)
        self.assertIn(f'value="{OTHER_SCOPE}"'.encode(), response.data)
        self.assertIn(b'name="with_arg" value="1" checked', response.data)
        self.assertIn(b"formnovalidate", response.data)
        self.assertNotIn(b"\n      required", response.data)
        self.assertEqual(self.review.evidence(ID), [])

    def test_current_subscription_runs_without_pasting_an_id_in_both_forms(self):
        for item in (False, True):
            with self.subTest(item=item):
                self.executor.reset_mock()
                response = self.show_context(item=item)
                self.assertEqual(response.status_code, 200)
                path = f"/item/{ID}/run" if item else "/run-selected"
                response = self.client.post(path, data={
                    "csrf": self.csrf(), "scope_mode": "current",
                    "shown_subscription_id": SCOPE, "selected": [ID],
                })
                self.assertEqual(response.status_code, 303 if item else 200)
                self.executor.assert_called_once_with(RECO["queries"]["arg"], [SCOPE])
                self.assertEqual(self.review.evidence(ID)[0]["subscriptions"], [SCOPE])
                self.assertEqual(self.review.get(ID)["status"], "Not reviewed")

    def test_current_scope_is_available_without_preview_and_resolves_at_execution(self):
        response = self.client.get("/")
        self.assertIn(b'value="current" checked', response.data)
        self.lookup.assert_not_called()
        for path in ("/run-selected", f"/item/{ID}/run"):
            with self.subTest(path=path):
                self.lookup.reset_mock()
                self.executor.reset_mock()
                self.lookup.return_value = {"id": OTHER_SCOPE, "name": "Current selection"}
                response = self.client.post(path, data={
                    "csrf": self.csrf(), "scope_mode": "current", "selected": [ID],
                })
                self.assertIn(response.status_code, (200, 303))
                self.lookup.assert_called_once_with()
                self.executor.assert_called_once_with(RECO["queries"]["arg"], [OTHER_SCOPE])

    def test_current_lookup_failure_does_not_run_against_previous_subscription(self):
        self.show_context()
        self.lookup.side_effect = ReviewError("Azure CLI is signed out")
        response = self.client.post("/run-selected", data={
            "csrf": self.csrf(), "scope_mode": "current", "selected": [ID],
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"signed out", response.data)
        self.executor.assert_not_called()

    def test_browser_policy_preserves_origin_without_accepting_null_origin(self):
        response = self.client.get("/")
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        token = self.csrf()
        self.assertEqual(self.client.post("/azure-context", data={"csrf": token},
                                         headers={"Origin": "null"}).status_code, 403)
        self.assertEqual(self.client.post("/azure-context", data={"csrf": token},
                                         headers={"Origin": "http://localhost"}).status_code, 200)

    def test_manual_scope_remains_available_after_lookup(self):
        self.show_context()
        response = self.client.post("/run-selected", data={
            "csrf": self.csrf(), "scope_mode": "manual", "selected": [ID],
            "subscriptions": OTHER_SCOPE, "shown_subscription_id": SCOPE,
        })
        self.assertEqual(response.status_code, 200)
        self.executor.assert_called_once_with(RECO["queries"]["arg"], [OTHER_SCOPE])

    def test_cli_change_after_preview_requires_confirmation(self):
        self.show_context()
        self.lookup.return_value = {"id": OTHER_SCOPE, "name": "Changed CLI default"}
        response = self.client.post(f"/item/{ID}/run", data={
            "csrf": self.csrf(), "scope_mode": "current", "shown_subscription_id": SCOPE,
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"changed since it was displayed", response.data)
        self.assertEqual(self.lookup.call_count, 2)
        self.executor.assert_not_called()
        self.show_context(item=True)
        response = self.client.post(f"/item/{ID}/run", data={
            "csrf": self.csrf(), "scope_mode": "current", "shown_subscription_id": OTHER_SCOPE,
        })
        self.assertEqual(response.status_code, 303)
        self.executor.assert_called_once_with(RECO["queries"]["arg"], [OTHER_SCOPE])

    def test_refresh_in_another_tab_rejects_stale_displayed_id(self):
        self.show_context()
        self.lookup.return_value = {"id": OTHER_SCOPE, "name": "Other subscription"}
        self.show_context()
        response = self.client.post(f"/item/{ID}/run", data={
            "csrf": self.csrf(), "scope_mode": "current", "shown_subscription_id": SCOPE,
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"stale", response.data)
        self.executor.assert_not_called()

    def test_missing_tampered_or_invalid_scope_never_runs(self):
        for fields in (
            {"scope_mode": "current", "shown_subscription_id": SCOPE},
            {"scope_mode": "not-a-mode"}, {"scope_mode": "manual"},
        ):
            response = self.client.post("/run-selected", data={
                "csrf": self.csrf(), "selected": [ID], **fields,
            })
            self.assertEqual(response.status_code, 400)
        self.show_context()
        for shown_id in ("", OTHER_SCOPE):
            response = self.client.post("/run-selected", data={
                "csrf": self.csrf(), "selected": [ID], "scope_mode": "current",
                "shown_subscription_id": shown_id,
            })
            self.assertEqual(response.status_code, 400)
        self.executor.assert_not_called()

    def test_lookup_failure_clears_old_context_but_keeps_manual_form_and_selection(self):
        self.show_context()
        self.lookup.side_effect = ReviewError("Please run az login")
        response = self.show_context(selected=[ID])
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Please run az login", response.data)
        self.assertIn(b'value="manual" checked', response.data)
        self.assertIn(f'name="selected" value="{ID}" checked'.encode(), response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("active_subscription", session)
        self.executor.assert_not_called()

    def test_lookup_obeys_csrf_and_escapes_subscription_names(self):
        self.assertEqual(self.client.get("/azure-context").status_code, 405)
        self.assertEqual(self.client.post("/azure-context").status_code, 403)
        self.lookup.assert_not_called()
        self.lookup.return_value = {"id": SCOPE, "name": "<script>Subscription</script>"}
        response = self.show_context(item=True)
        self.assertIn(b"&lt;script&gt;Subscription&lt;/script&gt;", response.data)
        self.assertNotIn(b"<script>", response.data)
