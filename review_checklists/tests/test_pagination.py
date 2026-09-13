import html
import re
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from review_checklists.review import Review
from review_checklists.tests.test_prototype import RECO, SCOPE, ReviewFixture
from review_checklists.web import create_app


class PaginationTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        recos = [dict(RECO, id=str(index)) for index in range(101)]
        self.review = Review.create(self.root / "many.sqlite3", "Many", recos, self.root)
        self.executor = Mock(return_value={"rows": [], "truncated": False})
        self.lookup = Mock(return_value={"id": SCOPE, "name": "Offline"})
        self.client = create_app(self.review, self.executor, self.lookup).test_client()
        self.client.get("/")
        with self.client.session_transaction() as session:
            self.csrf = session["csrf"]

    def test_default_shows_all_filtered_items_and_no_navigation(self):
        response = self.client.get("/?waf=security")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b"<td><a "), 101)
        self.assertEqual(response.data.count(b'name="selected"'), 101)
        self.assertIn(b"Showing all results", response.data)
        self.assertNotIn(b">Next</a>", response.data)
        self.assertNotIn(b">Previous</a>", response.data)
        self.assertNotRegex(response.text, r'name="paginate"[^>]*checked')
        self.assertEqual(len(self.client.get("/export/json").json["items"]), 101)

    def test_enabled_pages_preserve_choice_and_dashboard(self):
        response = self.client.get("/?waf=security&paginate=1")
        self.assertEqual(response.data.count(b"<td><a "), 50)
        self.assertIn(b"Assessment status for 101 matching checks", response.data)
        link = html.unescape(re.search(r'<a href="([^"]+)">Next</a>', response.text).group(1))
        self.assertEqual(parse_qs(urlsplit(link).query),
                         {"waf": ["security"], "paginate": ["1"], "page": ["2"]})
        self.assertEqual(self.client.get(link).data.count(b"<td><a "), 50)
        self.assertEqual(self.client.get("/?paginate=1&page=3").data.count(b"<td><a "), 1)
        self.assertEqual(self.client.get("/?page=3").data.count(b"<td><a "), 1)
        self.assertIn(b"Showing all results", self.client.get("/?waf=security").data)
        self.assertEqual(len(self.client.get("/export/json?paginate=1").json["items"]), 101)

    def test_invalid_pagination_parameters_are_explicit_errors(self):
        for query in ("paginate=no", "paginate=0", "page=bad", "paginate=1&page=0",
                      "paginate=1&page=4"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/?" + query).status_code, 400)
        self.assertEqual(self.client.get("/?paginate=1&search=missing").status_code, 200)

    def test_mode_survives_preview_details_and_metadata_save(self):
        for query, expected_count in (("waf=security", 101), ("waf=security&paginate=1", 50)):
            response = self.client.post("/azure-context?" + query, data={"csrf": self.csrf})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.count(b"<td><a "), expected_count)
            detail = self.client.get("/item/0?" + query)
            self.assertIn(html.escape("/?" + query, quote=True).encode(), detail.data)
            response = self.client.post("/metadata?" + query, data={
                "csrf": self.csrf, "revision": self.review.metadata["metadata_revision"],
                "name": "Renamed", "description": "",
            })
            self.assertEqual(parse_qs(urlsplit(response.location).query), parse_qs(query))
        self.executor.assert_not_called()

    def test_unpaginated_selection_limit_stays_fifty(self):
        form = {"csrf": self.csrf, "scope_mode": "manual", "subscriptions": SCOPE,
                "selected": [str(index) for index in range(51)]}
        response = self.client.post("/run-selected", data=form)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Select between 1 and 50", response.data)
        self.executor.assert_not_called()
        form["selected"] = form["selected"][:50]
        response = self.client.post("/run-selected", data=form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.executor.call_count, 50)
        self.assertEqual(self.review.get("50")["revision"], 0)
        self.assertEqual(self.review.evidence("50"), [])
