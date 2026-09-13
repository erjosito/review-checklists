from copy import deepcopy
import html
import json
import re
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from azure.core.exceptions import AzureError

from review_checklists.arg import MAX_SELECTED, run_selected
from review_checklists.corpus import ReviewError, has_arg_query
from review_checklists.filters import filter_options, services_for
from review_checklists.review import Review, assessment_summary
from review_checklists.tests import test_prototype
from review_checklists.tests.test_prototype import ID, RECO, ReviewFixture, SCOPE
from review_checklists.web import create_app


SECOND = "22222222-2222-2222-2222-222222222222"
MANUAL = "33333333-3333-3333-3333-333333333333"
MULTI = "44444444-4444-4444-4444-444444444444"
UNKNOWN = "55555555-5555-5555-5555-555555555555"


class FilterFixture(ReviewFixture):
    def setUp(self):
        super().setUp()
        recos = [
            dict(deepcopy(RECO), severity=0, resourceTypes=["Microsoft.ContainerService/managedClusters"]),
            dict(deepcopy(RECO), id=SECOND, title="Application gateway check", severity=1,
                 waf="Reliability", resourceTypes=["Microsoft.Network/applicationGateways"],
                 queries={"arg": "resources | where type =~ 'microsoft.network/applicationgateways'"}),
            dict(deepcopy(RECO), id=MANUAL, severity=2, waf="", resourceTypes=[], queries={}),
            dict(deepcopy(RECO), id=MULTI, severity=1,
                 services=["Azure Kubernetes Service", "Storage Account"],
                 resourceTypes=["Microsoft.Web/sites"], queries={"arg": " \n "}),
            dict(deepcopy(RECO), id=UNKNOWN, severity=2, resourceTypes=["Microsoft.Custom/widgets"]),
        ]
        self.path = self.root / "filters.sqlite3"
        self.review = Review.create(self.path, "Filter review", recos, self.root)
        self.executor = Mock(return_value={"rows": [], "truncated": False})
        self.app = create_app(self.review, self.executor)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def csrf(self):
        self.client.get("/")
        with self.client.session_transaction() as session:
            return session["csrf"]

    @staticmethod
    def ids(items):
        return {item["id"] for item in items}


class FilterTests(FilterFixture):
    def test_severity_zero_and_case_insensitive_pillars(self):
        self.assertEqual(self.ids(self.review.items(severity="HIGH")), {ID})
        self.assertEqual(self.ids(self.review.items(waf="reliability")), {SECOND})
        self.assertEqual(self.ids(self.review.items(waf="None")), {MANUAL})
        self.assertEqual(self.ids(self.review.items(severity="low")), {MANUAL, UNKNOWN})

    def test_service_aliases_multiple_services_and_unknown_arm_types(self):
        for service in ("aks", "Azure Kubernetes Service"):
            self.assertEqual(self.ids(self.review.items(service=service)), {ID, MULTI})
        self.assertEqual(self.ids(self.review.items(service="Microsoft.ContainerService/managedClusters")), {ID})
        self.assertEqual(self.ids(self.review.items(service="Storage")), {MULTI})
        self.assertEqual(self.ids(self.review.items(service="AppGW")), {SECOND})
        self.assertEqual(self.ids(self.review.items(service="none")), {MANUAL})
        self.assertEqual(self.ids(self.review.items(service="microsoft.custom/widgets")), {UNKNOWN})
        self.assertEqual(services_for(self.review.get(MULTI)["recommendation"]), ["Azure Kubernetes Service", "Azure Storage"])

    def test_all_filters_intersect_without_changing_state(self):
        self.review.update(ID, "Non-compliant", "Evidence needed", 0)
        before = self.review.export()
        self.assertEqual(self.ids(self.review.items(
            search="tags", status="Non-compliant", severity="high",
            waf="security", service="AKS", with_arg=True,
        )), {ID})
        self.assertEqual(self.review.items(severity="high", waf="reliability"), [])
        self.assertEqual(before, self.review.export())
        self.assertEqual(len(json.loads(before)["items"]), 5)

    def test_arg_only_excludes_missing_empty_and_whitespace_queries(self):
        self.assertEqual(self.ids(self.review.items(with_arg=True)), {ID, SECOND, UNKNOWN})
        self.assertFalse(has_arg_query({"queries": {"arg": ""}}))
        self.assertFalse(has_arg_query({}))
        self.assertEqual(self.ids(self.review.items(service="AKS", with_arg=True)), {ID})

    def test_invalid_filters_are_errors_not_empty_success(self):
        for arguments in (
            {"severity": "critical"}, {"waf": "unknown"}, {"service": "unknown-service"},
            {"with_arg": "false"},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ReviewError):
                self.review.items(**arguments)

    def test_options_are_deduplicated_and_show_services_not_raw_aliases(self):
        options = filter_options(self.review.items())
        self.assertEqual(options["services"]["azure kubernetes service"], "Azure Kubernetes Service")
        self.assertEqual(options["services"]["application gateway"], "Application Gateway")
        self.assertEqual(options["services"]["none"], "Not service-specific")
        self.assertEqual(options["services"]["microsoft.custom/widgets"], "microsoft.custom/widgets")
        self.assertNotIn("microsoft.containerservice/managedclusters", options["services"])

    def test_cli_combines_filters(self):
        # Reuse the CLI capture helper without launching Azure or a server.
        code, output, error = test_prototype.CliTests.invoke(
            self, "list", "--severity", "HIGH", "--waf", "Security",
            "--service", "Azure Kubernetes Service", "--with-arg",
        )
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(self.ids(json.loads(output)), {ID})


class BatchTests(FilterFixture):
    def test_only_selected_queries_run_and_duplicates_run_once(self):
        result = run_selected(self.review, [SECOND, SECOND], SCOPE, self.executor)
        self.executor.assert_called_once_with(
            self.review.get(SECOND)["recommendation"]["queries"]["arg"], [SCOPE],
        )
        self.assertEqual((result["succeeded"], result["failed"]), (1, 0))
        self.assertEqual(self.review.evidence(ID), [])
        self.assertEqual(self.review.evidence(UNKNOWN), [])
        self.assertEqual(len(self.review.evidence(SECOND)), 1)
        self.assertTrue(all(item["status"] == "Not reviewed" for item in self.review.items()))

    def test_selection_and_scope_preflight_is_all_or_nothing(self):
        for selected, scope in (
            ([], SCOPE), ([ID, "unknown"], SCOPE), ([ID, MANUAL], SCOPE),
            ([ID, MULTI], SCOPE), ([ID], ""), ([str(i) for i in range(MAX_SELECTED + 1)], SCOPE),
        ):
            with self.subTest(selected=selected), self.assertRaises(ReviewError):
                run_selected(self.review, selected, scope, self.executor)
        self.executor.assert_not_called()
        self.assertEqual(self.review.evidence(ID), [])

    def test_individual_failures_are_saved_and_remaining_selected_queries_continue(self):
        self.executor.side_effect = [
            AzureError("Permission denied"),
            {"rows": [{"id": "example"}], "truncated": True},
        ]
        result = run_selected(self.review, [ID, SECOND], SCOPE, self.executor)
        self.assertEqual((result["succeeded"], result["failed"]), (1, 1))
        self.assertEqual(self.review.evidence(ID)[0]["outcome"], "error")
        self.assertTrue(result["results"][1]["truncated"])
        self.assertEqual(self.review.get(SECOND)["status"], "Not reviewed")
        self.assertEqual(self.review.evidence(UNKNOWN), [])


class DashboardTests(FilterFixture):
    def test_percentages_have_explicit_denominators(self):
        self.review.update(ID, "Compliant", "", 0)
        self.review.update(SECOND, "Non-compliant", "", 0)
        self.review.update(MANUAL, "Not applicable", "", 0)
        summary = assessment_summary(self.review.items())
        self.assertEqual(summary["total"], 5)
        self.assertEqual(summary["assessed"], 2)
        self.assertEqual(summary["reviewed"], 3)
        self.assertEqual(summary["compliance_percentage"], 50.0)
        self.assertEqual(summary["progress_percentage"], 60.0)
        self.assertEqual(assessment_summary(self.review.items(severity="high"))["compliance_percentage"], 100.0)

    def test_empty_unreviewed_and_not_applicable_are_not_compliance(self):
        empty = assessment_summary([])
        self.assertIsNone(empty["compliance_percentage"])
        self.assertIsNone(empty["progress_percentage"])
        unreviewed = assessment_summary(self.review.items())
        self.assertIsNone(unreviewed["compliance_percentage"])
        self.assertEqual(unreviewed["progress_percentage"], 0)
        for item in self.review.items():
            self.review.update(item["id"], "Not applicable", "", 0)
        not_applicable = assessment_summary(self.review.items())
        self.assertIsNone(not_applicable["compliance_percentage"])
        self.assertEqual(not_applicable["progress_percentage"], 100)


class FeatureWebTests(FilterFixture):
    def test_filters_controls_and_selections(self):
        response = self.client.get("/?severity=high&waf=security&service=aks&with_arg=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 matching recommendations", response.data)
        self.assertIn(b"Only checks with ARG queries", response.data)
        self.assertIn(b'name="with_arg" value="1" checked', response.data)
        self.assertIn(b'name="severity" value="high" checked', response.data)
        self.assertIn(b'name="waf" value="security" checked', response.data)
        self.assertIn(b'name="service" value="azure kubernetes service" checked', response.data)
        selected = re.findall(r'name="selected" value="([^"]+)"', response.text)
        self.assertEqual(selected, [ID])
        self.assertIn(b"Clear filters", response.data)

    def test_only_query_checks_can_be_ticked_and_invalid_filter_is_visible(self):
        response = self.client.get("/")
        selected = set(re.findall(r'name="selected" value="([^"]+)"', response.text))
        self.assertEqual(selected, {ID, SECOND, UNKNOWN})
        for query in ("with_arg=false", "severity=critical", "waf=bogus", "service=not-real"):
            self.assertEqual(self.client.get("/?" + query).status_code, 400)

    def test_filter_state_survives_detail_update_and_query_run(self):
        query = "severity=high&waf=security&service=aks&with_arg=1&page=1"
        response = self.client.get("/?" + query)
        target = html.unescape(re.search(r'<td><a href="([^"]+)"', response.text).group(1))
        self.assertEqual(parse_qs(urlsplit(target).query), parse_qs(query))
        self.assertIn(b"severity=high", self.client.get(target).data)
        for action, fields in (
            ("update", {"revision": 0, "status": "Compliant", "comments": "Reviewed"}),
            ("run", {"subscriptions": SCOPE}),
        ):
            response = self.client.post(f"/item/{ID}/{action}?{query}", data={
                "csrf": self.csrf(), **fields,
            })
            self.assertEqual(response.status_code, 303)
            self.assertEqual(parse_qs(urlsplit(response.location).query), parse_qs(query))

    def test_filtered_pagination_and_dashboard_cover_all_pages(self):
        recos = [dict(RECO, id=str(index)) for index in range(51)]
        review = Review.create(self.root / "many.sqlite3", "Many", recos, self.root)
        client = create_app(review).test_client()
        query = "severity=medium&waf=security&service=microsoft.test%2Fresources&with_arg=1&paginate=1"
        first = client.get("/?" + query)
        next_url = html.unescape(re.search(r'<a href="([^"]+)">Next</a>', first.text).group(1))
        self.assertEqual(parse_qs(urlsplit(next_url).query), dict(parse_qs(query), page=["2"]))
        second = client.get(next_url)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data.count(b'name="selected"'), 1)
        self.assertIn(b"51 matching recommendations", second.data)
        self.assertIn(b"Assessment status for 51 matching checks", second.data)

    def test_donut_percentages_empty_state_and_no_external_scripts(self):
        self.review.update(ID, "Compliant", "", 0)
        self.review.update(SECOND, "Non-compliant", "", 0)
        self.review.update(MANUAL, "Not applicable", "", 0)
        response = self.client.get("/")
        self.assertIn(b"<svg ", response.data)
        self.assertIn(b"50.0%", response.data)
        self.assertIn(b"60.0%", response.data)
        self.assertIn(b"Not reviewed: 2", response.data)
        self.assertEqual(
            re.findall(r'<script[^>]*src="([^"]+)"[^>]*></script>', response.text),
            ["/static/assessment-forms.js", "/static/autosave.js"],
        )
        self.assertNotIn(b"<script>", response.data)
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
        self.assertNotIn("'unsafe-inline'", response.headers["Content-Security-Policy"])
        self.assertNotIn(b"style=", response.data)
        empty = self.client.get("/?severity=high&waf=reliability")
        self.assertIn(b"0 matching recommendations", empty.data)
        self.assertIn(b"N/A", empty.data)

    def test_selected_post_runs_no_other_checks_and_retains_filters(self):
        response = self.client.post("/run-selected?with_arg=1&service=appgw", data={
            "csrf": self.csrf(), "selected": [SECOND], "subscriptions": SCOPE,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 succeeded; 0 failed", response.data)
        self.assertIn(b"with_arg=1", response.data)
        self.assertEqual(len(self.review.evidence(SECOND)), 1)
        self.assertEqual(self.review.evidence(ID), [])
        self.assertEqual(self.executor.call_count, 1)

    def test_selected_post_validation_and_partial_failure(self):
        self.assertEqual(self.client.get("/run-selected").status_code, 405)
        self.assertEqual(self.client.post("/run-selected").status_code, 403)
        response = self.client.post("/run-selected", data={
            "csrf": self.csrf(), "selected": [], "subscriptions": SCOPE,
        })
        self.assertEqual(response.status_code, 400)
        self.executor.assert_not_called()
        self.executor.side_effect = [
            AzureError("<script>error</script>"), {"rows": [], "truncated": False},
        ]
        response = self.client.post("/run-selected", data={
            "csrf": self.csrf(), "selected": [ID, SECOND], "subscriptions": SCOPE,
        })
        self.assertEqual(response.status_code, 502)
        self.assertIn(b"1 succeeded; 1 failed", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertNotIn(b"<script>", response.data)
