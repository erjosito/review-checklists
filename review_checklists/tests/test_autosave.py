import re
import sqlite3
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from review_checklists.review import Review
from review_checklists.tests.test_prototype import ID, RECO, ReviewFixture
from review_checklists.web import create_app


class AutosaveTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        self.executor = Mock()
        self.lookup = Mock()
        self.app = create_app(self.review, self.executor, self.lookup)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as session:
            self.csrf = session["csrf"]
        self.url = f"/item/{ID}/assessment"
        self.form = {"csrf": self.csrf, "revision": "0",
                     "status": "Non-compliant", "comments": "Offline decision"}

    def save(self, data=None, headers=None, url=None):
        return self.client.post(url or self.url, data=self.form if data is None else data,
                                headers={"Accept": "application/json", **(headers or {})})

    def test_json_save_persists_only_assessment_and_acknowledges_submitted_values(self):
        before = self.review.metadata
        response = self.save()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {
            "revision": 1, "status": "Non-compliant", "comments": "Offline decision",
        })
        stored = Review(self.path).get(ID)
        self.assertEqual({key: stored[key] for key in response.json}, response.json)
        self.assertEqual(self.review.metadata, before)
        self.assertEqual(self.review.evidence(ID), [])
        self.executor.assert_not_called()
        self.lookup.assert_not_called()

    def test_acknowledgement_cannot_adopt_a_later_writers_revision(self):
        update = self.review.update

        def concurrent_update(*args):
            update(*args)
            update(ID, "Compliant", "Later writer", 1)

        with patch.object(self.review, "update", side_effect=concurrent_update):
            response = self.save()
        self.assertEqual(response.json, {
            "revision": 1, "status": "Non-compliant", "comments": "Offline decision",
        })
        self.assertEqual(self.review.get(ID)["revision"], 2)
        stale = self.save(dict(self.form, revision="1"))
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.review.get(ID)["comments"], "Later writer")

    def test_comment_limit_and_unicode_form_encoding(self):
        for comments in ("x" * 20000, "\U0001f680" * 20000, ""):
            response = self.save(dict(self.form, comments=comments,
                                      revision=str(self.review.get(ID)["revision"])))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["comments"], comments)
        revision = self.review.get(ID)["revision"]
        response = self.save(dict(self.form, comments="x" * 20001, revision=str(revision)))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["kind"], "validation")
        self.assertEqual(self.review.get(ID)["revision"], revision)

    def test_invalid_missing_and_oversized_revisions_do_not_write(self):
        for revision in ("", "-1", "1.0", "bad", " 0", "9" * 100, "\u0660"):
            with self.subTest(revision=revision):
                response = self.save(dict(self.form, revision=revision))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json["error"]["kind"], "validation")
        self.assertEqual(self.save({key: value for key, value in self.form.items()
                                    if key != "revision"}).status_code, 400)
        for status in ("", "Passed", "compliant"):
            response = self.save(dict(self.form, status=status))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["error"]["kind"], "validation")
        self.assertEqual(self.review.get(ID)["revision"], 0)

    def test_stale_conflict_is_explicit_and_never_overwrites(self):
        self.review.update(ID, "Compliant", "Other editor", 0)
        with self.assertLogs(self.app.logger, level="WARNING"):
            response = self.save()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"]["kind"], "conflict")
        self.assertEqual(self.review.get(ID)["comments"], "Other editor")

    def test_csrf_origin_and_methods_remain_enforced_for_json(self):
        for csrf in ("", "wrong", "\u00e9"):
            response = self.save(dict(self.form, csrf=csrf))
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json["error"]["kind"], "auth")
        for origin in ("https://attacker.example", "null", "https://localhost"):
            response = self.save(headers={"Origin": origin})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json["error"]["kind"], "auth")
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.save(headers={"Origin": "http://localhost"}).status_code, 200)
        self.assertEqual(self.review.get(ID)["revision"], 1)

    def test_storage_errors_are_logged_and_have_distinct_json_kind(self):
        with patch.object(self.review, "update", side_effect=sqlite3.OperationalError("disk full")):
            with self.assertLogs(self.app.logger, level="ERROR") as log:
                response = self.save()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json["error"]["kind"], "storage")
        self.assertIn("disk full", log.output[0])
        self.assertEqual(self.review.get(ID)["revision"], 0)

    def test_unknown_id_body_limit_and_missing_session_have_explicit_errors(self):
        response = self.save(url="/item/missing/assessment")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["kind"], "validation")
        response = self.save(dict(self.form, comments="x" * (256 * 1024)))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json["error"]["kind"], "validation")
        response = self.app.test_client().post(self.url, data=self.form,
                                               headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"]["kind"], "auth")
        self.assertEqual(self.review.get(ID)["revision"], 0)

    def test_manual_auth_and_storage_failures_preserve_escaped_draft(self):
        draft = dict(self.form, comments="<script>my draft</script>", csrf="invalid")
        response = self.client.post(self.url, data=draft)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"&lt;script&gt;my draft&lt;/script&gt;", response.data)
        with patch.object(self.review, "update", side_effect=sqlite3.OperationalError("read only")):
            response = self.client.post(self.url, data=dict(draft, csrf=self.csrf))
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"&lt;script&gt;my draft&lt;/script&gt;", response.data)
        self.assertEqual(self.review.get(ID)["revision"], 0)

    def test_form_fallback_preserves_filters_pagination_and_draft_on_error(self):
        query = "waf=security&waf=reliability&paginate=1&page=1&search=tags"
        response = self.client.post(self.url + "?" + query, data=self.form)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(parse_qs(urlsplit(response.location).query), parse_qs(query))
        response = self.client.get(response.location, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Offline decision", response.data)
        response = self.client.post(self.url, data=dict(self.form, comments="<script>draft</script>"))
        self.assertEqual(response.status_code, 409)
        self.assertIn(b"&lt;script&gt;draft&lt;/script&gt;", response.data)
        self.assertIn(b'name="revision" value="0"', response.data)
        self.assertIn(b"Copy it before", response.data)
        self.assertEqual(self.review.get(ID)["comments"], "Offline decision")

    def test_refresh_clamps_a_page_emptied_by_status_filter_edit(self):
        review = Review.create(self.root / "pages.sqlite3", "Many",
                               [dict(RECO, id=f"{i:03}") for i in range(51)], self.root)
        client = create_app(review).test_client()
        client.get("/")
        with client.session_transaction() as session:
            csrf = session["csrf"]
        response = client.post(
            "/item/050/assessment?status=Not+reviewed&paginate=1&page=2",
            data=dict(self.form, csrf=csrf), follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Page 1 of 1", response.data)
        self.assertEqual(response.request.args["status"], "Not reviewed")
        self.assertEqual(response.request.args["paginate"], "1")
        self.assertNotIn(b'data-assessment="assessment-050"', response.data)

    def test_local_script_boundary_and_unenhanced_fallback(self):
        response = self.client.get("/")
        csp = response.headers["Content-Security-Policy"]
        for directive in ("script-src 'self'", "connect-src 'self'", "frame-ancestors 'none'",
                          "form-action 'self'", "base-uri 'none'"):
            self.assertIn(directive, csp)
        self.assertNotIn("'unsafe-inline'", csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        cookie = self.app.test_client().get("/").headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn(b"Autosave is not enabled", response.data)
        self.assertIn(b"Save assessment</button>", response.data)
        self.assertEqual(re.findall(r'<script src="([^"]+)" defer></script>', response.text),
                         ["/static/autosave.js"])
        self.assertEqual(re.findall(r'<script src="([^"]+)"></script>', response.text),
                         ["/static/assessment-forms.js"])
        script = self.client.get("/static/autosave.js")
        self.addCleanup(script.close)
        self.assertEqual(script.status_code, 200)
        self.assertNotIn(b"innerHTML", script.data)
        self.assertNotIn(b"eval(", script.data)
