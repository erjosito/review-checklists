import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from review_checklists.corpus import ReviewError
from review_checklists.filters import MULTI_FILTERS, filter_values
from review_checklists.review import Review
from review_checklists.tests import test_prototype
from review_checklists.tests.test_filters_and_batch import (
    FilterFixture, ID, MANUAL, MULTI, RECO, SCOPE, SECOND, UNKNOWN,
)
from review_checklists.web import create_app


class SelectedFilters(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.values = {name: [] for name in MULTI_FILTERS}
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") in self.values and "checked" in attrs:
            self.values[attrs["name"]].append(attrs["value"])


class MultiSelectTests(FilterFixture):
    def test_multiple_values_match_any_within_each_category(self):
        self.assertEqual(self.ids(self.review.items(severity=["high", "medium"])), {ID, SECOND, MULTI})
        self.assertEqual(self.ids(self.review.items(waf=["Security", "Reliability"])),
                         {ID, SECOND, MULTI, UNKNOWN})
        self.assertEqual(self.ids(self.review.items(service=["AKS", "AppGW"])), {ID, SECOND, MULTI})
        self.review.update(ID, "Compliant", "", 0)
        self.review.update(SECOND, "Non-compliant", "", 0)
        self.assertEqual(self.ids(self.review.items(status=["Compliant", "Non-compliant"])), {ID, SECOND})

    def test_categories_still_intersect_with_status_search_and_arg_only(self):
        self.review.update(ID, "Compliant", "", 0)
        self.review.update(SECOND, "Non-compliant", "", 0)
        filters = {
            "status": ["Compliant", "Non-compliant"],
            "severity": ["high", "medium"],
            "waf": ["Security", "Reliability"],
            "service": ["AKS", "AppGW"],
            "with_arg": True,
        }
        self.assertEqual(self.ids(self.review.items(**filters)), {ID, SECOND})
        self.assertEqual(self.ids(self.review.items(search="tags", **filters)), {ID})
        self.assertEqual(self.review.items(**dict(filters, severity=["low"])), [])

    def test_unspecified_metadata_can_be_combined_with_specific_values(self):
        self.assertEqual(self.ids(self.review.items(waf=["none", "Reliability"])), {MANUAL, SECOND})
        self.assertEqual(self.ids(self.review.items(service=["none", "AKS"])), {MANUAL, ID, MULTI})

    def test_empty_selections_and_single_string_calls_remain_compatible(self):
        self.assertEqual(self.review.items(status=[], severity=(), waf=[], service=[]), self.review.items())
        self.assertEqual(self.review.items(severity="high"), self.review.items(severity=["high"]))
        self.assertEqual(self.review.items(status="Not reviewed"), self.review.items(status=["Not reviewed"]))
        self.assertEqual(self.review.items(waf="security"), self.review.items(waf=["security"]))

    def test_duplicate_aliases_do_not_duplicate_results(self):
        items = self.review.items(service=["AKS", "Azure Kubernetes Service", "aks"])
        self.assertEqual(len(items), 2)
        self.assertEqual(self.ids(items), {ID, MULTI})
        self.assertEqual(filter_values([" HIGH ", "", "high"], str.casefold), ("high",))

    def test_invalid_member_rejects_the_entire_filter(self):
        for values in (
            {"severity": ["high", "critical"]},
            {"waf": ["Security", "bogus"]},
            {"service": ["AKS", "not-a-service"]},
            {"status": ["Compliant", "unknown"]},
            {"severity": [0, "high"]},
            {"status": {"status": "Compliant"}},
        ):
            with self.subTest(values=values), self.assertRaises(ReviewError):
                self.review.items(**values)

    def test_cli_accepts_multiple_values_and_repeated_options(self):
        for arguments in (
            ("--severity", "high", "medium", "--service", "AKS", "AppGW"),
            ("--severity", "high", "--severity", "medium", "--service", "AKS", "--service", "AppGW"),
        ):
            code, output, error = test_prototype.CliTests.invoke(
                self, "list", *arguments, "--waf", "Security", "Reliability", "--with-arg",
                "--status", "Not reviewed", "Compliant",
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(self.ids(json.loads(output)), {ID, SECOND})


class MultiSelectWebTests(FilterFixture):
    def setUp(self):
        super().setUp()
        self.parameters = {
            "status": ["Not reviewed", "Compliant"],
            "severity": ["high", "medium"],
            "waf": ["security", "reliability"],
            "service": ["aks", "appgw"],
            "with_arg": ["1"],
        }
        self.query = urlencode(self.parameters, doseq=True)

    def assert_parameters(self, url):
        self.assertEqual(parse_qs(urlsplit(html.unescape(url)).query), self.parameters)

    def test_checkbox_groups_show_and_preserve_all_selected_values(self):
        response = self.client.get("/?" + self.query)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"2 matching recommendations", response.data)
        self.assertIn(b"Assessment status for 2 matching checks", response.data)
        selected = SelectedFilters(response.text).values
        for name in MULTI_FILTERS:
            expected = (["azure kubernetes service", "application gateway"] if name == "service"
                        else self.parameters[name])
            self.assertEqual(set(selected[name]), set(expected))
        self.assertIn(b"Severity: 2 selected", response.data)
        self.assertIn(b"Azure service: 2 selected", response.data)
        self.assertNotIn(b'<select name="severity"', response.data)

    def test_clearing_filters_returns_all_items_and_no_checked_filter_options(self):
        self.client.get("/?" + self.query)
        response = self.client.get("/")
        self.assertIn(b"5 matching recommendations", response.data)
        self.assertTrue(all(not values for values in SelectedFilters(response.text).values.values()))
        self.assertIn(b"Severity: All", response.data)

    def test_unknown_later_parameter_is_not_ignored(self):
        for name, valid in (
            ("severity", "high"), ("waf", "security"), ("service", "aks"),
            ("status", "Not reviewed"),
        ):
            response = self.client.get("/", query_string=[(name, valid), (name, "invalid")])
            self.assertEqual(response.status_code, 400)

    def test_navigation_preserves_repeated_values_through_edits_and_runs(self):
        response = self.client.get("/?" + self.query)
        item_link = re.search(r'<td><a href="([^"]+)"', response.text).group(1)
        self.assert_parameters(item_link)
        for action, data in (
            ("update", {"revision": "0", "status": "Compliant", "comments": "Retain all filters"}),
            ("run", {"subscriptions": SCOPE}),
        ):
            response = self.client.post(f"/item/{ID}/{action}?{self.query}", data={
                "csrf": self.csrf(), **data,
            })
            self.assertEqual(response.status_code, 303)
            self.assert_parameters(response.location)
            response = self.client.get(response.location)
            header_link = re.search(r'<header><a href="([^"]+)"', response.text).group(1)
            self.assert_parameters(header_link)

    def test_context_lookup_and_batch_results_retain_all_filter_values(self):
        self.client = create_app(
            self.review, self.executor, lambda: {"id": SCOPE, "name": "Development"},
        ).test_client()
        response = self.client.post("/azure-context?" + self.query, data={
            "csrf": self.csrf(), "selected": [ID],
        })
        self.assertEqual(response.status_code, 200)
        for name, values in SelectedFilters(response.text).values.items():
            expected = (["azure kubernetes service", "application gateway"] if name == "service"
                        else self.parameters[name])
            self.assertEqual(set(values), set(expected))
        self.assertIn(f'name="selected" value="{ID}" checked'.encode(), response.data)
        batch_action = re.search(r'action="([^"]*run-selected[^"]*)"', response.text).group(1)
        self.assert_parameters(batch_action)
        response = self.client.post(html.unescape(batch_action), data={
            "csrf": self.csrf(), "selected": [ID], "scope_mode": "current",
            "shown_subscription_id": SCOPE,
        })
        self.assertEqual(response.status_code, 200)
        back = re.search(r'<a href="([^"]+)">Return to filtered review</a>', response.text).group(1)
        self.assert_parameters(back)

    def test_pagination_retains_all_values_without_double_counting(self):
        recos = [dict(RECO, id=str(index), severity=index % 2,
                      resourceTypes=["Microsoft.ContainerService/managedClusters"]) for index in range(51)]
        review = Review.create(self.root / "multipage.sqlite3", "Multiple pages", recos, self.root)
        client = create_app(review).test_client()
        parameters = dict(self.parameters, service=["aks", "none"], paginate=["1"])
        query = urlencode(parameters, doseq=True)
        response = client.get("/?" + query)
        next_link = re.search(r'<a href="([^"]+)">Next</a>', response.text).group(1)
        expected = dict(parameters, page=["2"], service=["azure kubernetes service", "none"])
        self.assertEqual(parse_qs(urlsplit(html.unescape(next_link)).query), expected)
        response = client.get(html.unescape(next_link))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"51 matching recommendations", response.data)
        self.assertIn(b"Assessment status for 51 matching checks", response.data)
        self.assertEqual(response.data.count(b'name="selected"'), 1)
