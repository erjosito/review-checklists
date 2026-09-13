from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from flask import Flask
from werkzeug.serving import make_server
import yaml

from review_checklists.catalog import make_bundle
from review_checklists.corpus import load_corpus
from review_checklists.corpus_admin import (
    CorpusAdminError, CorpusStore, OPERATIONS_EVENT, RELIABILITY_EVENT, SECURITY_EVENT,
    create_app, create_corpus_blueprint, main,
    load_source_registry, maintenance_history, safe_external_url, source_coverage, summarize_corpus,
)
from review_checklists.source_coverage import SourceCoverageError, coverage_report, item_content_hash


IDS = [f"00000000-0000-4000-8000-{index:012d}" for index in range(1, 7)]


def recommendation(index=0):
    return {
        "schemaVersion": 1, "id": IDS[index], "name": f"test-Recommendation-{index}",
        "title": f"Test recommendation number {index}", "severity": 1, "waf": "Security",
        "source": {"type": "curated", "url": "https://example.org/original"},
        "resourceTypes": [], "services": [],
        "automation": {"status": "manual", "validatedAt": None},
        "provenance": {"upstreamRevision": None, "lastReviewed": None, "sources": []},
    }


def inventory(source_id="waf-security-controls", count=5):
    items = []
    for index in range(1, count + 1):
        payload = {"requirement": f"Upstream control {index}", "scope": "fixture"}
        items.append({"id": f"UP-{index}", "title": f"Upstream requirement {index}",
                      "url": f"https://example.org/controls/UP-{index}", "payload": payload,
                      "contentHash": item_content_hash(payload)})
    return {
        "schemaVersion": 1, "sourceId": source_id, "title": "WAF security control rows",
        "scope": "Security checklist control rows only, not all Azure guidance",
        "unit": "control row", "asOf": "2026-09-11",
        "retrievedAt": "2026-09-11T12:00:00Z", "upstreamRevision": "fixture-revision",
        "inventoryStatus": "complete", "sourceUrls": ["https://example.org/controls"],
        "fingerprintScope": "Requirement text and explicit applicability scope",
        "items": items, "limitations": ["A synthetic fixture, not live Azure source evidence."],
    }


def mapping(source, item_index=0, coverage="full"):
    item = source["items"][item_index]
    return {
        "sourceId": source["sourceId"], "recommendationId": item["id"], "url": item["url"],
        "coverage": coverage, "assessedAt": "2026-09-11",
        "upstreamContentHash": item["contentHash"], "notes": "Explicit requirement comparison.",
    }


class CorpusAdminTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.corpus = self.root / "corpus"
        self.reports = self.root / "reports"
        self.corpus.mkdir()
        self.reports.mkdir()
        self.registry = {}
        registry_patch = patch("review_checklists.corpus_admin.load_source_registry",
                               side_effect=lambda: deepcopy(self.registry))
        registry_patch.start()
        self.addCleanup(registry_patch.stop)
        self.recos = [recommendation(index) for index in range(4)]
        self.recos[0].update(services=["AKS"], waf="Cost",
                             queries={"arg": "resources | project id"})
        self.recos[0]["automation"] = {
            "status": "query_available", "validatedAt": None, "resultSemantics": "inventory",
        }
        self.recos[0]["provenance"]["sources"] = [
            {"url": "https://example.org/shared", "title": "Shared supporting reference",
             "accessedAt": "2026-09-11"},
        ]
        self.recos[1]["resourceTypes"] = ["Microsoft.ContainerService/managedClusters"]
        self.recos[1]["source"] = {"type": "aprl", "url": "https://example.org/aprl"}
        self.recos[1]["queries"] = {"arg": "resources | project id, compliant=true"}
        self.recos[1]["automation"] = {
            "status": "query_available", "validatedAt": "2026-09-01",
            "resultSemantics": "compliance", "complianceColumn": "compliant",
        }
        self.recos[1]["provenance"].update(lastReviewed="2026-09-02", upstreamRevision="revision-one")
        self.recos[1]["provenance"]["sources"] = [{"url": "https://example.org/shared"}]
        self.recos[1]["aliases"] = [{
            "id": IDS[4], "name": "retired-Recommendation",
            "source": {"type": "wafsg", "file": "old-reco.yaml"},
        }]
        self.recos[2]["waf"] = "Operations"
        self.recos[3]["services"] = ["AKS", "AppGW"]
        self.recos[3]["automation"]["status"] = "candidate"
        self.write_corpus()
        self.app = create_app(self.corpus, self.reports)
        self.app.testing = True
        self.client = self.app.test_client()

    def write_corpus(self):
        for index, reco in enumerate(self.recos):
            (self.corpus / f"reco-{index}.yaml").write_text(yaml.safe_dump(reco), encoding="utf-8")

    def write_report(self, name, report):
        (self.reports / name).write_text(json.dumps(report), encoding="utf-8")

    def write_inventory(self, source, previous=False):
        self.registry.setdefault(source["sourceId"], {
            key: source[key] for key in ("sourceId", "title", "scope", "unit", "fingerprintScope")
        })
        directory = self.reports / "source-inventories"
        directory.mkdir(exist_ok=True)
        name = source["sourceId"] + (".previous.json" if previous else ".json")
        (directory / name).write_text(json.dumps(source), encoding="utf-8")

    def snapshot_files(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    def test_canonical_metrics_identity_and_service_matrix(self):
        recos = load_corpus(self.corpus, require_current=True)
        summary = summarize_corpus(recos)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["aliases"], 1)
        self.assertEqual(summary["arg_available"], 2)
        self.assertEqual(summary["arg_validated"], 1)
        self.assertEqual(summary["hash"], make_bundle(recos, "test-version")["contentHash"])
        self.assertEqual(summary["service_modes"], {"explicit": 2, "inferred": 1, "missing": 1})
        self.assertEqual(summary["matrix"]["Azure Kubernetes Service"], {"Cost": 1, "Security": 2})
        self.assertEqual(summary["matrix"]["Application Gateway"], {"Security": 1})
        self.assertEqual(summary["matrix"]["Not service-specific"], {"Operations": 1})
        self.assertEqual(summary["origins"], {"aprl": 1, "curated": 3})
        self.assertEqual(summary["alias_origins"], {"wafsg": 1})
        self.assertEqual(summary["quality"]["missing_review_date"], 3)
        self.assertEqual(summary["quality"]["missing_source_dates"], 1)
        self.assertEqual(len(summary["references"]), 1)
        self.assertEqual(summary["references"][0]["ids"], {IDS[0], IDS[1]})
        self.assertTrue(summary["references"][0]["undated"])
        response = self.client.get("/corpus/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(summary["hash"], response.text)
        self.assertIn("not a tagged release", response.text)
        self.assertNotIn("Review progress", response.text)

    def test_drilldown_filter_intersection_quality_reference_and_alias(self):
        cases = [
            ({"service": "AKS", "waf": "Security"}, [1, 3]),
            ({"quality": "inferred_service"}, [1]),
            ({"quality": "missing_service"}, [2]),
            ({"arg": "validated"}, [1]),
            ({"arg": "unvalidated"}, [0]),
            ({"origin": "aprl"}, [1]),
            ({"reference": "https://example.org/shared"}, [0, 1]),
            ({"search": IDS[4]}, [1]),
            ({"search": "retired-Recommendation"}, [1]),
            ({"service": "none"}, [2]),
            ({"service": "AKS", "waf": "Operations"}, []),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                response = self.client.get("/corpus/recommendations", query_string=query)
                self.assertEqual(response.status_code, 200)
                self.assertIn(f"{len(expected)} matching records.", response.text)
                for index in range(4):
                    self.assertEqual(self.recos[index]["title"] in response.text, index in expected)
        response = self.client.get("/corpus/recommendations/" + IDS[4])
        self.assertEqual(response.status_code, 200)
        self.assertIn("resolves to this canonical record", response.text)
        self.assertIn(IDS[1], response.text)

    def test_invalid_filters_and_pagination_are_visible_client_errors(self):
        for query in ("waf=typo", "origin=typo", "quality=typo", "arg=typo", "service=typo",
                      "page=0", "page=2", "page=not-a-number", "unknown=1", "arg=missing&arg=available"):
            with self.subTest(query=query):
                response = self.client.get("/corpus/recommendations?" + query)
                self.assertEqual(response.status_code, 400)
                self.assertIn('role="alert"', response.text)
        self.assertEqual(self.client.get("/corpus/recommendations/not-an-id").status_code, 404)

    def test_pagination_preserves_filters_and_full_source_denominator(self):
        for index in range(52):
            reco = recommendation()
            reco.update(id=f"00000000-0000-4000-8000-{index + 100:012d}",
                        name=f"pagination-Recommendation-{index}", title=f"Pagination fixture item {index}")
            self.recos.append(reco)
        self.write_corpus()
        response = self.client.get("/corpus/recommendations?search=Pagination")
        self.assertEqual(response.status_code, 200)
        self.assertIn("52 matching records. Page 1 of 2", response.text)
        self.assertIn("search=Pagination&amp;page=2", response.text)
        response = self.client.get("/corpus/recommendations?search=Pagination&page=2")
        self.assertIn("52 matching records. Page 2 of 2", response.text)
        self.assertIn("search=Pagination&amp;page=1", response.text)
        source = inventory(count=52)
        self.write_inventory(source)
        self.recos[0]["provenance"]["upstreamRecommendations"] = [mapping(source)]
        self.write_corpus()
        response = self.client.get("/corpus/sources/" + source["sourceId"] + "?state=unknown")
        self.assertIn("1 / 52", response.text)
        self.assertIn("51 matching records. Page 1 of 2", response.text)
        self.assertIn("state=unknown&amp;page=2", response.text)
        response = self.client.get("/corpus/sources/" + source["sourceId"] + "?state=unknown&page=2")
        self.assertEqual(response.status_code, 200)
        self.assertIn("1 / 52", response.text)
        self.assertIn("51 matching records. Page 2 of 2", response.text)

    def test_lazy_load_invalid_corpus_does_not_break_other_app_routes(self):
        (self.corpus / "reco-0.yaml").write_text("title: invalid\n", encoding="utf-8")
        host = Flask("independent")
        host.testing = True
        with patch("review_checklists.corpus_admin.load_corpus", side_effect=AssertionError("eager load")):
            host.register_blueprint(create_corpus_blueprint(self.corpus, self.reports), url_prefix="/corpus")
        host.add_url_rule("/unrelated", view_func=lambda: "Independent route")
        client = host.test_client()
        self.assertEqual(client.get("/unrelated").status_code, 200)
        response = client.get("/corpus/")
        self.assertEqual(response.status_code, 503)
        self.assertIn("Cannot validate", response.text)
        self.assertIn("No empty or successful-looking statistics", response.text)
        self.assertNotIn(str(self.corpus), response.text)
        self.assertEqual(client.get("/corpus/history").status_code, 200)
        self.assertEqual(client.get("/unrelated").status_code, 200)

    def test_cache_invalidation_and_invalid_edits_never_serve_stale_success(self):
        store = CorpusStore(self.corpus)
        first = store.get()
        self.assertIs(store.get(), first)
        self.recos[0]["title"] = "A changed source recommendation"
        self.write_corpus()
        second = store.get()
        self.assertNotEqual(first.summary["hash"], second.summary["hash"])
        (self.corpus / "reco-0.yaml").write_text("id: not-valid\n", encoding="utf-8")
        with self.assertRaises(CorpusAdminError):
            store.get()
        self.write_corpus()
        self.assertEqual(store.get().summary["hash"], second.summary["hash"])
        (self.corpus / "reco-3.yaml").unlink()
        self.assertEqual(store.get().summary["total"], 3)

    def test_read_only_routes_no_database_network_or_writes(self):
        before = self.snapshot_files()
        with patch("sqlite3.connect", side_effect=AssertionError("Database access forbidden")), \
                patch("socket.create_connection", side_effect=AssertionError("Network access forbidden")), \
                patch("subprocess.run", side_effect=AssertionError("Subprocess access forbidden")):
            for path in ("/corpus/", "/corpus/recommendations", "/corpus/sources",
                         "/corpus/recommendations/" + IDS[0], "/corpus/history"):
                self.assertEqual(self.client.get(path).status_code, 200)
                for method in ("POST", "PUT", "PATCH", "DELETE"):
                    self.assertEqual(self.client.open(path, method=method).status_code, 405)
        self.assertEqual(before, self.snapshot_files())
        self.assertFalse(list(self.root.rglob("*.sqlite3")))

    def test_source_coverage_full_partial_stale_supporting_unknown_and_alias_deduplication(self):
        source = inventory()
        self.write_inventory(source)
        self.recos[0]["provenance"]["upstreamRecommendations"] = [
            mapping(source), mapping(source, 1, "partial"),
            dict(mapping(source, 2), upstreamContentHash="sha256:" + "a" * 64),
            mapping(source, 3, "supporting"),
        ]
        self.recos[1]["provenance"]["upstreamRecommendations"] = [mapping(source)]
        self.write_corpus()
        report = source_coverage(load_corpus(self.corpus, require_current=True), self.reports)
        self.assertFalse(report["errors"])
        current = report["sources"][0]
        self.assertEqual(current["denominator"], 5)
        self.assertEqual(current["counts"], {"full": 1, "partial": 1, "stale": 1, "supporting": 1, "unknown": 1})
        self.assertEqual(current["coveragePercent"], 20)
        self.assertEqual(current["partialPercent"], 20)
        alias_mapped = deepcopy(self.recos)
        alias_mapped[1]["provenance"]["upstreamRecommendations"] = []
        resolved = coverage_report(source, alias_mapped, mappings=[dict(mapping(source), corpusId=IDS[4])])
        self.assertEqual(resolved["counts"], current["counts"])
        self.assertEqual(resolved["items"][0]["corpusIds"], [IDS[0], IDS[1]])
        with self.assertRaisesRegex(SourceCoverageError, "Duplicate upstream assessment"):
            coverage_report(source, self.recos, mappings=[dict(mapping(source), corpusId=IDS[4])])
        before = self.snapshot_files()
        with patch("sqlite3.connect", side_effect=AssertionError("Database forbidden")), \
                patch("socket.create_connection", side_effect=AssertionError("Network forbidden")):
            response = self.client.get("/corpus/sources")
            self.assertEqual(response.status_code, 200)
            self.assertIn("1 / 5", response.text)
            self.assertIn("(20.0%)", response.text)
            self.assertIn(source["scope"], response.text)
            self.assertNotIn("100.0%", response.text)
            detail = self.client.get("/corpus/sources/" + source["sourceId"] + "?state=partial")
            self.assertEqual(detail.status_code, 200)
            self.assertIn("1 / 5", detail.text)
            self.assertIn("1 matching records", detail.text)
            self.assertIn("UP-2 - partial", detail.text)
            self.assertNotIn("UP-1 - full", detail.text)
            self.assertIn("control row", detail.text)
        self.assertEqual(before, self.snapshot_files())
        self.assertEqual(self.client.get("/corpus/sources/" + source["sourceId"] + "?state=invalid").status_code, 400)

    def test_any_source_scope_no_inventory_partial_empty_and_undated_never_synthetic_coverage(self):
        source = inventory("independent-source", count=1)
        self.registry[source["sourceId"]] = {
            key: source[key] for key in ("sourceId", "title", "scope", "unit", "fingerprintScope")
        }
        self.recos[0]["provenance"]["upstreamRecommendations"] = [mapping(source)]
        self.write_corpus()
        response = self.client.get("/corpus/sources")
        self.assertIn("Not measured", response.text)
        self.assertIn("independent-source", response.text)
        self.assertNotIn("100.0%", response.text)
        for changes in ({"inventoryStatus": "partial"}, {"items": []},
                        {"asOf": None}, {"retrievedAt": None}, {"inventoryStatus": "unknown"}):
            with self.subTest(changes=changes):
                changed = dict(source, **changes)
                self.write_inventory(changed)
                current = source_coverage(self.recos, self.reports)["sources"][0]
                self.assertIsNone(current["denominator"])
                self.assertIsNone(current["coveragePercent"])
                response = self.client.get("/corpus/sources/independent-source")
                self.assertEqual(response.status_code, 200)
                self.assertIn("Not measured", response.text)
                self.assertNotIn("100.0%", response.text)
        self.write_inventory(source)
        current = source_coverage(self.recos, self.reports)["sources"][0]
        self.assertEqual(current["coveragePercent"], 100)
        self.assertEqual(current["denominator"], 1)
        for reference in (mapping(source, coverage="supporting"),
                          dict(mapping(source), upstreamContentHash="sha256:" + "b" * 64)):
            self.recos[0]["provenance"]["upstreamRecommendations"] = [reference]
            current = source_coverage(self.recos, self.reports)["sources"][0]
            self.assertIsNone(current["coveragePercent"])
            self.assertEqual(current["denominator"], 1)
        self.recos[0]["provenance"]["upstreamRecommendations"] = []
        self.assertIsNone(source_coverage(self.recos, self.reports)["sources"][0]["coveragePercent"])

    def test_recorded_upstream_changes_and_removed_details(self):
        source = inventory()
        previous = deepcopy(source)
        previous["asOf"] = "2026-09-01"
        previous["items"] = previous["items"][:4]
        previous["items"][0]["payload"] = {"requirement": "Old control wording"}
        previous["items"][0]["contentHash"] = item_content_hash(previous["items"][0]["payload"])
        removed = deepcopy(source["items"][0])
        removed.update(id="REMOVED-1", title="A previously inventoried requirement")
        previous["items"].append(removed)
        self.write_inventory(previous, previous=True)
        self.write_inventory(source)
        response = self.client.get("/corpus/sources/" + source["sourceId"])
        self.assertEqual(response.status_code, 200)
        self.assertIn("New upstream IDs</dt><dd>UP-5", response.text)
        self.assertIn("Changed upstream IDs</dt><dd>UP-1", response.text)
        self.assertIn("Removed upstream ID REMOVED-1", response.text)
        self.assertIn("A previously inventoried requirement", response.text)
        previous["scope"] = "A different source scope"
        self.write_inventory(previous, previous=True)
        response = self.client.get("/corpus/sources")
        self.assertIn("Cannot compare inventories with different scope", response.text)
        self.assertNotIn("100.0%", response.text)

    def test_versioned_inventory_filenames_latest_observation_not_best_percentage(self):
        source = inventory(count=1)
        self.recos[0]["provenance"]["upstreamRecommendations"] = [mapping(source)]
        self.write_inventory(source)
        directory = self.reports / "source-inventories"
        original = directory / (source["sourceId"] + ".json")
        original.rename(directory / "source--2026-09-11--revision--snapshot.json")
        (directory / "identical-copy.json").write_text(json.dumps(source))
        data = source_coverage(self.recos, self.reports)
        self.assertFalse(data["errors"])
        self.assertEqual(len(data["sources"][0]["historyFiles"]), 1)
        self.assertEqual(data["sources"][0]["coveragePercent"], 100)
        newer = deepcopy(source)
        newer.update(asOf="2026-09-12", retrievedAt="2026-09-12T12:00:00Z", inventoryStatus="partial")
        (directory / "newer--snapshot.json").write_text(json.dumps(newer))
        data = source_coverage(self.recos, self.reports)
        self.assertFalse(data["errors"])
        self.assertIsNone(data["sources"][0]["coveragePercent"])
        self.assertEqual(data["sources"][0]["asOf"], "2026-09-12")
        conflict = deepcopy(newer)
        conflict["upstreamRevision"] = "different-at-same-date-and-time"
        (directory / "conflicting--snapshot.json").write_text(json.dumps(conflict))
        data = source_coverage(self.recos, self.reports)
        self.assertIn("Conflicting inventories", data["errors"][0])
        self.assertIsNone(data["sources"][0]["coveragePercent"])

    def test_invalid_inventory_payload_duplicate_keys_and_filenames_visible(self):
        source = inventory()
        source["items"][0]["contentHash"] = "sha256:" + "d" * 64
        self.write_inventory(source)
        response = self.client.get("/corpus/sources")
        self.assertIn("Fingerprint does not match payload", response.text)
        self.assertIn("Invalid inventory", response.text)
        source = inventory()
        source["items"][0]["title"] = "<script>untrusted inventory title</script>"
        source["title"] = "<script>untrusted source title</script>"
        self.write_inventory(source)
        response = self.client.get("/corpus/sources/" + source["sourceId"])
        self.assertNotIn("<script>", response.text)
        self.assertIn("&lt;script&gt;", response.text)
        path = self.reports / "source-inventories" / (source["sourceId"] + ".json")
        path.write_text('{"sourceId":"first","sourceId":"second"}')
        self.assertIn("Duplicate JSON key", self.client.get("/corpus/sources").text)
        path.write_text(json.dumps(dict(source, sourceId="../different-source")))
        self.assertIn("Inventory", self.client.get("/corpus/sources").text)
        self.assertEqual(self.client.get("/corpus/sources/unknown-source").status_code, 404)

    def test_registry_unknown_ids_are_diagnostics_not_uncovered_or_duplicate_sources(self):
        source = inventory("waf-security-checklist", count=1)
        self.write_inventory(source)
        self.recos[0]["provenance"]["upstreamRecommendations"] = [
            dict(mapping(source), sourceId="azure-waf-security"),
        ]
        self.write_corpus()
        data = source_coverage(self.recos, self.reports)
        self.assertEqual([entry["sourceId"] for entry in data["sources"]], ["waf-security-checklist"])
        self.assertIsNone(data["sources"][0]["coveragePercent"])
        self.assertEqual(data["unknownSources"]["azure-waf-security"]["corpusIds"], [IDS[0]])
        response = self.client.get("/corpus/sources")
        self.assertIn("Unknown source IDs require explicit reconciliation", response.text)
        self.assertNotIn("100.0%", response.text)
        unknown = self.client.get("/corpus/sources/azure-waf-security")
        self.assertEqual(unknown.status_code, 200)
        self.assertIn("Unknown source ID in the central registry", unknown.text)
        self.recos[0]["provenance"]["upstreamRecommendations"] = [mapping(source)]
        data = source_coverage(self.recos, self.reports)
        self.assertFalse(data["unknownSources"])
        self.assertEqual(data["sources"][0]["coveragePercent"], 100)
        self.registry.clear()
        data = source_coverage(self.recos, self.reports)
        self.assertFalse(data["sources"])
        self.assertIn("waf-security-checklist", data["unknownSources"])

    def test_invalid_registry_and_registered_scope_mismatch_are_visible(self):
        with patch("review_checklists.corpus_admin.load_source_registry",
                   side_effect=CorpusAdminError("Registry unavailable")):
            response = self.client.get("/corpus/sources")
            self.assertIn("Registry unavailable", response.text)
            self.assertIn("Not measured", response.text)
        source = inventory()
        self.write_inventory(source)
        self.registry[source["sourceId"]]["scope"] = "Different registered scope"
        response = self.client.get("/corpus/sources")
        self.assertIn("differs from the registered source scope", response.text)
        self.assertNotIn("100.0%", response.text)

    def test_registry_wrapper_uses_local_helper_never_fetches(self):
        registry = {"waf-security-checklist": {"sourceId": "waf-security-checklist"}}
        with patch("review_checklists.source_audit.load_registry", return_value=registry) as loader, \
                patch("review_checklists.source_audit.fetch_inventory",
                      side_effect=AssertionError("Source fetching forbidden")):
            self.assertEqual(load_source_registry(), registry)
            loader.assert_called_once_with()
        with patch("review_checklists.source_audit.load_registry",
                   side_effect=json.JSONDecodeError("invalid registry", "{", 1)):
            with self.assertRaisesRegex(CorpusAdminError, "Cannot read the central source registry"):
                load_source_registry()

    def test_escaping_external_urls_and_local_assets(self):
        self.recos[0]["title"] = "<script>alert('source')</script>"
        self.recos[0]["description"] = '<img src=x onerror="alert(1)">'
        self.recos[0]["provenance"]["sources"] = [
            {"url": "javascript:alert(1)", "title": "<script>unsafe title</script>"},
            {"url": "https://example.org/safe", "title": "<b>Safe URL with untrusted title</b>"},
        ]
        self.write_corpus()
        response = self.client.get("/corpus/recommendations/" + IDS[0])
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>", response.text)
        self.assertNotIn("<img src=x", response.text)
        self.assertNotIn('href="javascript:', response.text)
        self.assertIn("&lt;script&gt;", response.text)
        self.assertIn('href="https://example.org/safe"', response.text)
        with self.client.get("/corpus/assets/corpus.css", buffered=True) as asset:
            self.assertEqual(asset.status_code, 200)
        self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        for unsafe in ("javascript:alert(1)", "file:///secret", "//example.org/relative",
                       "https://user:password@example.org", "https://example.org\\@evil",
                       "https://example.org/\npath", "http://[invalid"):
            self.assertIsNone(safe_external_url(unsafe), unsafe)

    def test_history_distinguishes_events_aggregates_and_recorded_deferrals(self):
        self.write_report("cost-refresh-manifest.json", {
            "artifactSchema": "cost-refresh-manifest/1", "asOf": "2026-09-11", "status": "applied",
            "scope": "Bounded fixture", "summary": {"appliedUpdates": 1, "appliedAdditions": 0},
            "updates": [{"id": IDS[0]}], "additions": [],
        })
        migration = {
            "status": "applied", "summary": {"historicalSnapshot": 500},
            "mergeResult": {"mode": "write", "before": 5, "after": 4, "retired": 1, "groups": [{}]},
            "finalStageSummary": {"appliedGroups": 1, "aliasesPreserved": 1},
            "finalTechnicalDeferrals": [{"groupId": "fixture-deferral", "canonicalId": IDS[0],
                                         "reasons": ["Different scopes <script>unsafe</script>"]}],
        }
        self.write_report("alias-migration.json", migration)
        self.write_report("duplicate-audit.json", {
            "summary": {"historicalSnapshot": 500}, "finalTechnicalDeferrals": migration["finalTechnicalDeferrals"],
        })
        history = maintenance_history(self.reports)
        self.assertFalse(history["errors"])
        self.assertEqual(len(history["events"]), 2)
        self.assertEqual(len(history["snapshots"]), 2)
        self.assertEqual(len(history["deferrals"]), 1)
        self.assertEqual(history["events"][1]["summary"]["retired"], 1)
        self.assertNotIn("historicalSnapshot", history["events"][1]["summary"])
        response = self.client.get("/corpus/history")
        self.assertEqual(response.status_code, 200)
        self.assertIn("1 recorded technical deferral groups", response.text)
        self.assertNotIn("<script>", response.text)
        self.assertIn("Aggregate snapshot, not another application event.", response.text)

    def test_reports_invalid_json_records_and_unmeasured_deferrals_visible(self):
        self.write_report("cost-refresh-manifest.json", {
            "artifactSchema": "cost-refresh-manifest/1", "status": "applied",
            "updates": "invalid", "additions": [], "summary": {},
        })
        response = self.client.get("/corpus/history")
        self.assertIn("updates must be an array of objects", response.text)
        self.assertIn("No zero-deferral conclusion", response.text)
        (self.reports / "cost-refresh-manifest.json").write_text('{"status":"applied","status":"other"}')
        self.assertIn("Duplicate JSON key", self.client.get("/corpus/history").text)
        (self.reports / "cost-refresh-manifest.json").write_text('{"invalid":NaN}')
        self.assertIn("Invalid JSON constant", self.client.get("/corpus/history").text)

    def test_finalized_operations_event_is_bounded_and_nested_download_is_allowlisted(self):
        directory = self.reports / "full-refresh-2026-09-11"
        directory.mkdir()
        manifest = {
            "assessedAt": "2026-09-11", "baselineCount": 3, "additionsCount": 1,
            "outcomes": {"updated": 1, "supportedunchanged": 1, "needsmanualreview": 1},
            "records": [
                {"id": IDS[0], "outcome": "updated", "reason": "Applied fixture edit"},
                {"id": IDS[1], "outcome": "supportedunchanged", "reason": "No edit required"},
                {"id": IDS[2], "outcome": "needsmanualreview", "reason": "More evidence required"},
            ],
            "additions": [{"id": IDS[3], "reason": "New distinct requirement"}],
            "upstreamMappings": [{}] * 25, "sourceInventory": [{}] * 30,
        }
        path = directory / "operations-manifest.json"
        path.write_text(json.dumps(manifest))
        (directory / "operations-source-coverage.json").write_text(json.dumps({"updates": 99}))
        history = maintenance_history(self.reports)
        self.assertFalse(history["errors"])
        self.assertEqual(len(history["events"]), 1)
        self.assertEqual(history["events"][0]["summary"], {
            "baselineRecordsAssessed": 3, "appliedUpdates": 1, "appliedAdditions": 1,
            "supportedUnchanged": 1, "needsManualReview": 1,
        })
        response = self.client.get("/corpus/reports/" + OPERATIONS_EVENT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, path.read_bytes())
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(self.client.get("/corpus/reports/operations-source-coverage.json").status_code, 404)
        manifest["outcomes"]["updated"] = 3
        path.write_text(json.dumps(manifest))
        history = maintenance_history(self.reports)
        self.assertFalse(history["events"])
        self.assertIn("disagrees with its Operations records", history["errors"][0])

    def test_security_guidance_and_provenance_only_changes_are_one_distinct_event(self):
        directory = self.reports / "full-refresh-2026-09-11"
        directory.mkdir()
        manifest = {
            "artifactSchema": "security-refresh-manifest/1", "date": "2026-09-11",
            "scope": "Frozen Security fixture", "additions": [],
            "records": [
                {"id": IDS[0], "outcome": "updated", "guidanceChanged": True,
                 "changedFields": ["description", "provenance"], "reason": "Guidance edit"},
                {"id": IDS[1], "outcome": "supportedunchanged", "guidanceChanged": False,
                 "changedFields": ["provenance"], "reason": "Source evidence only"},
                {"id": IDS[2], "outcome": "needsmanualreview", "guidanceChanged": False,
                 "changedFields": [], "reason": "No verified source comparison"},
            ],
            "counts": {"baseline": 3, "after": 3, "updated": 1, "supportedunchanged": 1,
                       "needsmanualreview": 1, "sourceVerified": 2, "unverified": 1,
                       "additions": 0, "guidanceChanged": 1, "provenanceOnly": 1,
                       "explicitUpstreamMappings": 20},
        }
        path = directory / "security-manifest.json"
        path.write_text(json.dumps(manifest))
        (directory / "security-mapping-proposals.json").write_text(json.dumps({"status": "applied"}))
        history = maintenance_history(self.reports)
        self.assertFalse(history["errors"])
        self.assertEqual(len(history["events"]), 1)
        summary = history["events"][0]["summary"]
        self.assertEqual(summary["guidanceUpdates"], 1)
        self.assertEqual(summary["provenanceOnlyUpdates"], 1)
        self.assertEqual(summary["unverifiedNeedsManualReview"], 1)
        self.assertNotIn("explicitUpstreamMappings", summary)
        self.assertIn("not full source refresh", history["events"][0]["status"])
        self.assertEqual(self.client.get("/corpus/reports/" + SECURITY_EVENT).status_code, 200)
        manifest["counts"]["guidanceChanged"] = 2
        path.write_text(json.dumps(manifest))
        history = maintenance_history(self.reports)
        self.assertFalse(history["events"])
        self.assertIn("guidanceChanged disagrees", history["errors"][0])

    def test_reliability_frozen_entry_outcomes_not_entire_baseline_are_refresh_changes(self):
        directory = self.reports / "full-refresh-2026-09-11"
        directory.mkdir()
        manifest = {
            "date": "2026-09-11", "scope": "Frozen non-APRL Reliability fixture",
            "baselineCount": 3, "baselineIds": IDS[:3], "additionCount": 1,
            "summary": {"updated": 1, "supportedunchanged": 1, "needsmanualreview": 1},
            "entries": [
                {"id": IDS[0], "outcome": "updated", "evidence": "Current guidance comparison"},
                {"id": IDS[1], "outcome": "supportedunchanged", "evidence": "Guidance remains supported"},
                {"id": IDS[2], "outcome": "needsmanualreview", "evidence": "Verification gap retained"},
            ],
            "additions": [{"id": IDS[3], "reason": "Distinct new requirement"}],
            "sourceCoverage": {"full": 50}, "upstreamMappings": [{}] * 20,
        }
        path = directory / "reliability-manifest.json"
        path.write_text(json.dumps(manifest))
        (directory / "reliability-baseline.json").write_text(json.dumps({"baselineCount": 3}))
        history = maintenance_history(self.reports)
        self.assertFalse(history["errors"])
        self.assertEqual(len(history["events"]), 1)
        self.assertEqual(history["events"][0]["summary"], {
            "baselineRecordsAccountedFor": 3, "appliedUpdates": 1, "appliedAdditions": 1,
            "supportedUnchanged": 1, "needsManualReview": 1,
        })
        self.assertEqual(self.client.get("/corpus/reports/" + RELIABILITY_EVENT).status_code, 200)
        manifest["baselineIds"] = [IDS[0], IDS[1], IDS[1]]
        path.write_text(json.dumps(manifest))
        history = maintenance_history(self.reports)
        self.assertFalse(history["events"])
        self.assertIn("do not reconcile with the frozen baseline IDs", history["errors"][0])

    def test_report_links_are_allowlisted_plaintext_and_cannot_traverse(self):
        text = '<script>alert("not HTML")</script>\n[relative](../../private.sqlite3)\n'
        (self.reports / "cost-sources.md").write_text(text)
        (self.reports / "private.sqlite3").write_text("DO NOT SERVE")
        response = self.client.get("/corpus/reports/cost-sources.md")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(response.data, (self.reports / "cost-sources.md").read_bytes())
        for path in ("private.sqlite3", "..%2Fprivate.sqlite3", "%2e%2e%5cprivate.sqlite3",
                     "not-allowlisted.md", "..", "C:%5csecret"):
            response = self.client.get("/corpus/reports/" + path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("DO NOT SERVE", response.text)

    def test_public_report_symlink_is_rejected(self):
        outside = self.root / "outside.md"
        outside.write_text("OUTSIDE REPORT ROOT")
        link = self.reports / "cost-sources.md"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Creating symbolic links is not permitted on this platform.")
        self.assertEqual(self.client.get("/corpus/reports/cost-sources.md").status_code, 404)

    def test_standalone_loopback_host_port_and_methods(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/corpus/", headers={"Host": "attacker.example"}).status_code, 400)
        for rule in self.app.url_map.iter_rules():
            self.assertLessEqual(rule.methods, {"GET", "HEAD", "OPTIONS"})
        with patch("waitress.serve") as serve:
            self.assertEqual(main(["--corpus", str(self.corpus), "--reports", str(self.reports),
                                   "--port", "8899"]), 0)
        self.assertEqual(serve.call_args.kwargs, {"host": "127.0.0.1", "port": 8899})
        with patch("waitress.serve") as serve:
            with self.assertRaises(SystemExit):
                main(["--port", "0"])
            serve.assert_not_called()

    def test_standalone_app_responds_over_loopback_without_a_review(self):
        server = make_server("127.0.0.1", 0, self.app)
        thread = Thread(target=server.serve_forever, daemon=True)
        before = self.snapshot_files()
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/corpus/", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"Source corpus overview", response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(before, self.snapshot_files())


if __name__ == "__main__":
    unittest.main()
