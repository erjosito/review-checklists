from contextlib import redirect_stderr, redirect_stdout
import io
import json
from unittest.mock import patch
from uuid import UUID

from review_checklists.__main__ import main
from review_checklists.corpus import ReviewError
from review_checklists.review import Review
from review_checklists.tests.test_prototype import ID, RECO, ReviewFixture
from review_checklists.web import create_app


class MetadataTests(ReviewFixture):
    def test_creation_uses_explicit_filename_and_persistent_metadata(self):
        path = self.root / "custom.sqlite3"
        review = Review.create(
            path, "Friendly name", [RECO], self.root, description="Scope\nand context",
        )
        metadata = Review(path).metadata
        self.assertEqual(metadata["name"], "Friendly name")
        self.assertEqual(metadata["description"], "Scope\nand context")
        self.assertEqual(str(UUID(metadata["review_id"])), metadata["review_id"])
        self.assertEqual(metadata["metadata_updated_at"], metadata["created_at"])
        self.assertEqual(review.path.name, "custom.sqlite3")
        self.assertFalse((self.root / "Friendly name.sqlite3").exists())
        self.assertEqual(json.loads(review.export())["metadata"], metadata)

    def test_partial_updates_preserve_identity_state_and_unknown_metadata(self):
        self.review.update(ID, "Non-compliant", "Keep assessment", 0)
        self.review.add_evidence(ID, {"outcome": "success", "rows": []})
        with self.review.connection() as connection:
            connection.execute("INSERT INTO metadata VALUES ('future_field', 'keep')")
        before = self.review.report()
        other_handle = Review(self.path)
        self.review.update_metadata(name="New name", revision=0)
        self.review.update_metadata(description="New context", revision=1)
        after = other_handle.report()
        self.assertEqual(after["items"], before["items"])
        for key in ("review_id", "created_at", "corpus_path", "corpus_sha256", "future_field"):
            self.assertEqual(after["metadata"][key], before["metadata"][key])
        self.assertEqual(after["metadata"]["name"], "New name")
        self.assertEqual(after["metadata"]["description"], "New context")
        self.assertEqual(after["metadata"]["metadata_revision"], "2")
        self.assertNotEqual(after["metadata"]["metadata_updated_at"], before["metadata"]["metadata_updated_at"])
        self.review.update_metadata(description="")
        self.assertEqual(self.review.metadata["description"], "")
        self.assertTrue(self.path.is_file())

    def test_stale_and_invalid_updates_do_not_change_metadata(self):
        self.review.update_metadata(name="First", revision=0)
        before = self.review.metadata
        with self.assertRaisesRegex(ReviewError, "Reload"):
            self.review.update_metadata(description="Stale", revision=0)
        for changes in ({}, {"name": "  "}, {"name": 3}, {"description": 3},
                        {"description": "x" * 20001}):
            with self.subTest(changes=list(changes)):
                with self.assertRaises(ReviewError):
                    self.review.update_metadata(**changes)
        self.assertEqual(self.review.metadata, before)
        self.review.update_metadata(description="x" * 20000)
        self.assertEqual(len(self.review.metadata["description"]), 20000)

    def test_legacy_reads_do_not_write_and_first_edit_extends_metadata(self):
        new_keys = ("review_id", "description", "metadata_revision", "metadata_updated_at")
        with self.review.connection() as connection:
            connection.executemany("DELETE FROM metadata WHERE key = ?", [(key,) for key in new_keys])
        before = self.path.read_bytes()
        legacy = Review(self.path)
        self.assertEqual(legacy.metadata["description"], "")
        self.assertEqual(legacy.metadata["metadata_revision"], "0")
        self.assertNotIn("review_id", legacy.metadata)
        legacy.export()
        self.assertEqual(self.path.read_bytes(), before)
        legacy.update_metadata(description="Added later", revision=0)
        UUID(legacy.metadata["review_id"])
        self.assertEqual(legacy.metadata["name"], "Test review")
        self.assertEqual(legacy.get(ID)["revision"], 0)

    def test_invalid_creation_does_not_leave_a_file(self):
        for name, description in (("", ""), ("Valid", "x" * 20001)):
            path = self.root / "invalid.sqlite3"
            with self.assertRaises(ReviewError):
                Review.create(path, name, [RECO], self.root, description=description)
            self.assertFalse(path.exists())

    def test_cli_create_show_update_and_clear_description(self):
        path = self.root / "LitwareReview01.sqlite3"
        prefix = ["--review", str(path)]
        with patch("review_checklists.__main__.load_corpus", return_value=[RECO]), redirect_stdout(io.StringIO()):
            self.assertEqual(main(prefix + ["init", "--name", "LitwareReview01",
                                            "--description", "Initial context"]), 0)
        for arguments, expected in (
            (["metadata"], "Initial context"),
            (["metadata", "--description", "Updated", "--revision", "0"], "Updated"),
            (["metadata", "--description", ""], ""),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(prefix + arguments), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["file"], str(path.resolve()))
            self.assertEqual(result["metadata"]["description"], expected)
            self.assertEqual(result["metadata"]["name"], "LitwareReview01")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(prefix + ["metadata", "--name", "Stale", "--revision", "0"]), 1)
            self.assertEqual(main(prefix + ["metadata", "--revision", "0"]), 1)
        self.assertEqual(Review(path).metadata["name"], "LitwareReview01")

    def test_web_metadata_save_filter_preservation_and_stale_edit(self):
        client = create_app(self.review).test_client()
        page = client.get("/")
        self.assertIn(b"review.sqlite3", page.data)
        with client.session_transaction() as session:
            csrf = session["csrf"]
        form = {"csrf": csrf, "revision": "0", "name": "LitwareReview01",
                "description": "<script>not executable</script>"}
        response = client.post("/metadata?waf=cost&waf=security", data=form)
        self.assertEqual(response.status_code, 303)
        self.assertIn("waf=cost&waf=security", response.location)
        page = client.get("/")
        self.assertIn(b"LitwareReview01", page.data)
        self.assertNotIn(b"<script>", page.data)
        self.assertIn(b"&lt;script&gt;", page.data)
        html = client.get("/export/html")
        self.assertIn(b"&lt;script&gt;", html.data)
        self.assertIn(self.review.metadata["review_id"].encode(), html.data)
        self.assertEqual(client.post("/metadata", data=form).status_code, 400)
        form["revision"] = "bad"
        self.assertEqual(client.post("/metadata", data=form).status_code, 400)
        self.assertEqual(self.review.metadata["metadata_revision"], "1")

    def test_web_metadata_requires_csrf_and_same_origin(self):
        client = create_app(self.review).test_client()
        client.get("/")
        with client.session_transaction() as session:
            csrf = session["csrf"]
        form = {"revision": "0", "name": "Changed", "description": ""}
        self.assertEqual(client.post("/metadata", data=form).status_code, 403)
        form["csrf"] = csrf
        response = client.post("/metadata", data=form, headers={"Origin": "https://example.org"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.review.metadata["name"], "Test review")
