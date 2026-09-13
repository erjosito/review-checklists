from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from azure.core.exceptions import AzureError
from azure.mgmt.resourcegraph.models import ResultTruncated
import yaml

from review_checklists.__main__ import main
from review_checklists.arg import collect_pages, query_azure, run_query, subscription_ids
from review_checklists.corpus import ReviewError, load_corpus, read_document, select_checklist
from review_checklists.filters import filter_items
from review_checklists.review import Review
from review_checklists.web import create_app


ID = "5de32c19-9248-4160-9d5d-1e4e614658d3"
SCOPE = "11111111-1111-1111-1111-111111111111"
RECO = {
    "id": ID, "name": "test-Recommendation", "title": "Check resource tags",
    "severity": 1, "waf": "Security", "labels": {"guid": ID},
    "source": {"type": "revcl", "file": "test-fixture.yaml"}, "resourceTypes": ["Microsoft.Test/resources"],
    "queries": {"arg": "resources | project id, name"},
}
ROOT = Path(__file__).resolve().parents[2]


class ReviewFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "review.sqlite3"
        self.recos = [deepcopy(RECO)]
        self.review = Review.create(self.path, "Test review", self.recos, self.root)


class CorpusTests(unittest.TestCase):
    def test_real_corpus_and_nested_checklists(self):
        recos = load_corpus(ROOT / "v2" / "recos")
        # Six full-pillar additions, followed by three audited storage duplicate retirements.
        self.assertEqual(len(recos), 2008)
        self.assertEqual(sum(len(reco.get("aliases", [])) for reco in recos), 58)
        self.assertEqual(len({r["id"] for r in recos}), len(recos))
        all_recos = read_document(ROOT / "v2" / "checklists" / "all_recos.yaml")
        self.assertEqual(len(select_checklist(recos, all_recos)), len(recos))
        alz = select_checklist(recos, read_document(ROOT / "v2" / "checklists" / "alz.yaml"))
        self.assertEqual(len(alz), 236)
        self.assertTrue(all(reco["area"] and reco["subarea"] for reco in alz))
        delivery = select_checklist(
            recos, read_document(ROOT / "v2" / "checklists" / "app_delivery.yaml")
        )
        self.assertEqual(len(delivery), 42)
        self.assertIn("64f9a19a-f29c-495d-94c6-c7919ca0f6c5", {reco["id"] for reco in delivery})
        items = [{"id": reco["id"], "recommendation": reco} for reco in recos]
        expected_aks = {
            reco["id"] for reco in recos
            if any(resource.casefold() == "microsoft.containerservice/managedclusters"
                   for resource in reco.get("resourceTypes", []))
        }
        self.assertTrue(expected_aks)
        self.assertEqual({item["id"] for item in filter_items(items, service="AKS")}, expected_aks)
        query_items = filter_items(items, with_arg=True)
        self.assertTrue(query_items)
        self.assertTrue(all(item["recommendation"]["queries"]["arg"].strip() for item in query_items))

    def test_selectors_and_exclusion_use_existing_semantics(self):
        definition = {"include": {"wafSelector": ["Security"]}}
        self.assertEqual(len(select_checklist([RECO], definition)), 1)
        definition["exclude"] = {"nameSelector": [RECO["name"]]}
        with self.assertRaisesRegex(ReviewError, "matched no"):
            select_checklist([RECO], definition)
        with self.assertRaisesRegex(ReviewError, "Unsupported"):
            select_checklist([RECO], {"include": {"typoSelector": ["anything"]}})
        with self.assertRaisesRegex(ReviewError, "nonempty"):
            select_checklist([RECO], {"include": {}})

    def test_invalid_corpus_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ReviewError, "No recommendations"):
                load_corpus(root)
            file = root / "reco.yaml"
            file.write_text("name: [bad", encoding="utf-8")
            with self.assertRaisesRegex(ReviewError, "Cannot read"):
                load_corpus(root)
            file.write_text(yaml.safe_dump(RECO), encoding="utf-8")
            self.assertEqual(load_corpus(root)[0]["id"], ID)
            (root / "duplicate.yaml").write_text(yaml.safe_dump(RECO), encoding="utf-8")
            with self.assertRaisesRegex(ReviewError, "[Dd]uplicate"):
                load_corpus(root)


class StorageTests(ReviewFixture):
    def test_persistence_and_revision_conflicts(self):
        self.review.update(ID, "Non-compliant", "Needs work", 0)
        reopened = Review(self.path)
        item = reopened.get(ID)
        self.assertEqual((item["status"], item["comments"], item["revision"]),
                         ("Non-compliant", "Needs work", 1))
        with self.assertRaisesRegex(ReviewError, "Reload"):
            reopened.update(ID, "Compliant", "Stale edit", 0)
        self.assertEqual(reopened.get(ID), item)

    def test_unknown_ids_invalid_status_and_no_overwrite(self):
        with self.assertRaises(ReviewError):
            self.review.get("unknown")
        with self.assertRaises(ReviewError):
            self.review.update(ID, "Invalid", "", 0)
        with self.assertRaises(ReviewError):
            Review.create(self.path, "Overwrite", [RECO], self.root)
        self.assertEqual(Review(self.path).metadata["name"], "Test review")

    def test_snapshot_is_independent_and_report_shape_is_stable(self):
        self.recos[0]["title"] = "Changed upstream"
        report = json.loads(self.review.export())
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["summary"]["Not reviewed"], 1)
        self.assertEqual(report["items"][0]["recommendation"]["title"], RECO["title"])
        self.assertEqual(len(report["metadata"]["corpus_sha256"]), 64)
        self.assertEqual(report["items"][0]["evidence"], [])

    def test_missing_or_unknown_schema_does_not_create_a_review(self):
        missing = self.root / "missing.sqlite3"
        with self.assertRaises(ReviewError):
            Review(missing)
        self.assertFalse(missing.exists())
        with self.review.connection() as connection:
            connection.execute("PRAGMA user_version=999")
        with self.assertRaisesRegex(ReviewError, "Unsupported"):
            Review(self.path)

    def test_failed_initialization_removes_only_its_new_database(self):
        target = self.root / "invalid.sqlite3"
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            Review.create(target, "Duplicate IDs", [RECO, RECO], self.root)
        self.assertFalse(target.exists())
        self.assertTrue(self.path.exists())


class ArgTests(ReviewFixture):
    def test_success_and_zero_rows_never_assign_compliance(self):
        executor = Mock(return_value={"rows": [], "truncated": False})
        result = run_query(self.review, ID, SCOPE, executor)
        executor.assert_called_once_with(RECO["queries"]["arg"], [SCOPE])
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(self.review.get(ID)["status"], "Not reviewed")
        self.assertEqual(self.review.evidence(ID)[0]["rows"], [])

    def test_failure_recorded_without_destroying_prior_evidence(self):
        run_query(self.review, ID, SCOPE, Mock(return_value={"rows": [], "truncated": False}))
        with self.assertRaisesRegex(ReviewError, "failure saved"):
            run_query(self.review, ID, SCOPE, Mock(side_effect=AzureError("Access denied")))
        evidence = self.review.evidence(ID)
        self.assertEqual([run["outcome"] for run in evidence], ["error", "success"])
        self.assertIn("Access denied", evidence[0]["error"])
        self.assertEqual(self.review.get(ID)["status"], "Not reviewed")

    def test_explicit_valid_scope_required(self):
        executor = Mock()
        for invalid in ("", "all", SCOPE + ",", "not-a-guid"):
            with self.assertRaises(ReviewError):
                run_query(self.review, ID, invalid, executor)
        executor.assert_not_called()
        self.assertEqual(subscription_ids(f"{SCOPE}, {SCOPE}"), [SCOPE])

    def test_manual_recommendation_cannot_trigger_azure(self):
        reco = dict(RECO, queries={})
        review = Review.create(self.root / "manual.sqlite3", "Manual", [reco], self.root)
        executor = Mock()
        with self.assertRaisesRegex(ReviewError, "no ARG query"):
            run_query(review, ID, SCOPE, executor)
        executor.assert_not_called()

    def test_azure_credential_is_cli_only_and_client_is_closed(self):
        with patch("review_checklists.arg.DefaultAzureCredential") as credential, patch(
            "review_checklists.arg.ResourceGraphClient"
        ) as client, patch("review_checklists.arg.collect_pages", return_value={}) as collect:
            query_azure("resources", [SCOPE])
        kwargs = credential.call_args.kwargs
        self.assertTrue(kwargs["exclude_environment_credential"])
        self.assertTrue(kwargs["exclude_managed_identity_credential"])
        self.assertTrue(kwargs["exclude_interactive_browser_credential"])
        self.assertNotIn("exclude_cli_credential", kwargs)
        collect.assert_called_once()
        client.return_value.__exit__.assert_called_once()

    def test_pagination_including_sdk_enum(self):
        client = Mock()
        client.resources.side_effect = [
            SimpleNamespace(data=[{"id": "one"}], skip_token="next", result_truncated=ResultTruncated.true),
            SimpleNamespace(data=[{"id": "two"}], skip_token=None, result_truncated=ResultTruncated.false),
        ]
        result = collect_pages(client, "resources", [SCOPE])
        self.assertEqual(result, {"rows": [{"id": "one"}, {"id": "two"}], "truncated": False})
        requests = [call.args[0] for call in client.resources.call_args_list]
        self.assertEqual(requests[1].options.skip_token, "next")
        self.assertEqual(requests[0].subscriptions, [SCOPE])
        self.assertFalse(requests[0].options.allow_partial_scopes)

    def test_unpageable_results_and_row_cap_are_marked_truncated(self):
        client = Mock()
        client.resources.return_value = SimpleNamespace(
            data=[{"id": "one"}, {"id": "two"}], skip_token=None,
            result_truncated=ResultTruncated.true,
        )
        self.assertTrue(collect_pages(client, "resources", [SCOPE])["truncated"])
        with patch("review_checklists.arg.MAX_ROWS", 1):
            result = collect_pages(client, "resources", [SCOPE])
        self.assertEqual(len(result["rows"]), 1)
        self.assertTrue(result["truncated"])

    def test_repeated_token_and_invalid_response_fail_explicitly(self):
        client = Mock()
        client.resources.return_value = SimpleNamespace(
            data=[], skip_token="repeat", result_truncated=True,
        )
        with self.assertRaisesRegex(ReviewError, "repeated"):
            collect_pages(client, "resources", [SCOPE])
        client.resources.return_value.data = {"bad": "shape"}
        with self.assertRaisesRegex(ReviewError, "shape"):
            collect_pages(client, "resources", [SCOPE])

    def test_page_limit_is_explicitly_truncated(self):
        client = Mock()
        client.resources.return_value = SimpleNamespace(
            data=[{"id": "one"}], skip_token="next", result_truncated=True,
        )
        with patch("review_checklists.arg.MAX_PAGES", 1):
            result = collect_pages(client, "resources", [SCOPE])
        self.assertEqual(result, {"rows": [{"id": "one"}], "truncated": True})


class WebTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        self.executor = Mock(return_value={"rows": [{"id": "<script>bad</script>"}], "truncated": False})
        self.app = create_app(self.review, self.executor)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def csrf(self):
        self.client.get("/")
        with self.client.session_transaction() as session:
            return session["csrf"]

    def test_browse_edit_run_and_export(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        detail = self.client.get(f"/item/{ID}")
        self.assertIn(b"Check resource tags", detail.data)
        response = self.client.post(f"/item/{ID}/update", data={
            "csrf": self.csrf(), "revision": "0", "status": "Non-compliant",
            "comments": "<script>alert(1)</script>",
        })
        self.assertEqual(response.status_code, 303)
        self.assertIn(b"&lt;script&gt;", self.client.get(f"/item/{ID}").data)
        response = self.client.post(f"/item/{ID}/run", data={
            "csrf": self.csrf(), "subscriptions": SCOPE,
        })
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.review.get(ID)["status"], "Non-compliant")
        self.assertEqual(self.client.get("/export/json").json["items"][0]["evidence"][0]["outcome"],
                         "success")
        report = self.client.get("/export/html")
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"&lt;script&gt;", report.data)
        self.assertNotIn(b"<script>", report.data)
        self.assertIn("attachment", report.headers["Content-Disposition"])

    def test_csrf_origin_host_and_get_mutations_blocked(self):
        self.assertEqual(self.client.post(f"/item/{ID}/run").status_code, 403)
        self.assertEqual(self.client.get(f"/item/{ID}/run").status_code, 405)
        self.assertEqual(self.client.get("/", headers={"Host": "attacker.example"}).status_code, 400)
        self.assertEqual(self.client.post(f"/item/{ID}/run", data={
            "csrf": self.csrf(), "subscriptions": SCOPE,
        }, headers={"Origin": "https://attacker.example"}).status_code, 403)
        self.assertEqual(self.client.post(f"/item/{ID}/run", data={
            "csrf": "\u00e9", "subscriptions": SCOPE,
        }).status_code, 403)
        self.executor.assert_not_called()

    def test_stale_edit_and_invalid_filter_are_visible_errors(self):
        token = self.csrf()
        self.review.update(ID, "Compliant", "Another tab", 0)
        response = self.client.post(f"/item/{ID}/update", data={
            "csrf": token, "revision": "0", "status": "Non-compliant", "comments": "Stale",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Reload", response.data)
        self.assertEqual(self.review.get(ID)["comments"], "Another tab")
        self.assertEqual(self.client.get("/?status=garbage").status_code, 400)
        self.assertEqual(self.client.get("/?page=garbage").status_code, 400)

    def test_pagination_search_and_local_headers(self):
        response = self.client.get("/?search=tags")
        self.assertIn(b"1 matching recommendations", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertIn(b"0 matching recommendations", self.client.get("/?search=nonexistent").data)

    def test_multiple_pages_are_bounded(self):
        recos = [dict(RECO, id=str(index), title=f"Recommendation {index}") for index in range(51)]
        review = Review.create(self.root / "pages.sqlite3", "Pages", recos, self.root)
        client = create_app(review).test_client()
        first, second = client.get("/?paginate=1"), client.get("/?page=2")
        self.assertEqual(first.data.count(b"<td><a "), 50)
        self.assertEqual(second.data.count(b"<td><a "), 1)
        self.assertIn(b"Page 2 of 2", second.data)

    def test_azure_failure_is_visible_in_page_and_evidence(self):
        self.executor.side_effect = AzureError("Not authorized")
        response = self.client.post(f"/item/{ID}/run", data={
            "csrf": self.csrf(), "subscriptions": SCOPE,
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Not authorized", response.data)
        self.assertIn(b"Not authorized", self.client.get(f"/item/{ID}").data)


class CliTests(ReviewFixture):
    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = main(["--review", str(self.path), *args])
        return code, output.getvalue(), error.getvalue()

    def test_cli_lifecycle_and_exports(self):
        self.assertEqual(self.invoke("update", ID, "--comments", "CLI comment")[0], 0)
        self.assertEqual(self.invoke("update", ID, "--status", "Compliant")[0], 0)
        code, output, _ = self.invoke("show", ID)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["comments"], "CLI comment")
        self.assertEqual(len(json.loads(self.invoke("list", "--status", "Compliant")[1])), 1)
        for format in ("json", "html"):
            target = self.root / f"report.{format}"
            self.assertEqual(self.invoke("export", "--format", format, "--output", str(target))[0], 0)
            self.assertTrue(target.is_file())
            self.assertEqual(self.invoke("export", "--format", format, "--output", str(target))[0], 1)
        self.assertEqual(self.invoke("export", "--output", str(self.path))[0], 1)
        self.assertEqual(Review(self.path).get(ID)["comments"], "CLI comment")

    def test_module_entrypoint_reopens_existing_review(self):
        self.review.update(ID, "Compliant", "Preserved assessment", 0)
        result = subprocess.run(
            [
                sys.executable, "-m", "review_checklists", "--review", str(self.path),
                "show", ID,
            ],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
        )
        item = json.loads(result.stdout)
        self.assertEqual(item["status"], "Compliant")
        self.assertEqual(item["comments"], "Preserved assessment")

    def test_cli_init_and_errors(self):
        corpus = self.root / "corpus"
        corpus.mkdir()
        (corpus / "reco.yaml").write_text(yaml.safe_dump(RECO), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            code = main(["--review", str(self.root / "new.sqlite3"), "init", "--corpus", str(corpus)])
        self.assertEqual(code, 0)
        self.assertEqual(self.invoke("update", ID)[0], 1)
        self.assertEqual(self.invoke("run", ID, "--subscriptions", "")[0], 1)
        self.assertEqual(self.invoke("serve", "--port", "0")[0], 1)


if __name__ == "__main__":
    unittest.main()
