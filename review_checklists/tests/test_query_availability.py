from copy import deepcopy
import html
import re
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from review_checklists.review import Review
from review_checklists.tests.test_prototype import RECO, ReviewFixture
from review_checklists.web import create_app


def cost_recommendations():
    recommendations = []
    for index in range(52):
        reco = deepcopy(RECO)
        reco.update(id=str(UUID(int=index + 1)), waf="Cost", title=f"Cost check {index + 1}")
        if index < 50:
            reco["queries"] = {}
        recommendations.append(reco)
    return recommendations


class QueryAvailabilityTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        self.review = Review.create(
            self.root / "cost.sqlite3", "Cost", cost_recommendations(), self.root,
        )
        self.client = create_app(self.review).test_client()

    def test_no_queries_on_current_page_explains_other_page_availability(self):
        response = self.client.get("/?waf=cost&severity=medium")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"0 runnable ARG checks on this page", response.data)
        self.assertIn(b"2 of 52 matching checks have ARG queries", response.data)
        self.assertIn(b"No checks on this page have an ARG query", response.data)
        self.assertRegex(response.text, r'<button[^>]*disabled[^>]*>Run selected queries</button>')
        target = html.unescape(re.search(
            r'<a href="([^"]+)">Show only checks with ARG queries</a>', response.text,
        ).group(1))
        self.assertEqual(parse_qs(urlsplit(target).query), {
            "page": ["1"], "waf": ["cost"], "severity": ["medium"], "with_arg": ["1"],
        })
        filtered = self.client.get(target)
        self.assertEqual(filtered.status_code, 200)
        self.assertIn(b"2 runnable ARG checks on this page", filtered.data)
        self.assertEqual(filtered.data.count(b'name="selected"'), 2)
        self.assertNotRegex(filtered.text, r'<button[^>]*disabled[^>]*>Run selected queries</button>')

    def test_truly_manual_results_and_no_matches_have_distinct_explanations(self):
        manual = self.client.get("/?search=Cost+check+10")
        self.assertIn(b"None of the matching checks contains an ARG query", manual.data)
        self.assertNotIn(b">Show only checks with ARG queries</a>", manual.data)
        empty = self.client.get("/?waf=security")
        self.assertIn(b"No checks match the current filters", empty.data)

    def test_later_query_page_is_enabled_without_changing_filters(self):
        response = self.client.get("/?waf=cost&page=2")
        self.assertIn(b"2 runnable ARG checks on this page", response.data)
        self.assertIn(b"2 of 52 matching checks have ARG queries", response.data)
        self.assertNotRegex(response.text, r'<button[^>]*disabled[^>]*>Run selected queries</button>')
