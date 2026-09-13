"""Scoped evidence and identity contract for the September Reliability slice."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from review_checklists.catalog import make_bundle, read_bundle
from review_checklists.source_coverage import (
    coverage_report, item_content_hash, validate_inventory,
)
from scripts.modules.cl_corpus import (
    dump_recommendation, validate_corpus,
    validate_recommendation,
)
from review_checklists.tests.service_stage import load_stage_document as load_yaml_document, stage_file_bytes
from review_checklists.tests.followup_stage import pre_followup_files, pre_followup_paths


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "review_checklists/docs/corpus-refresh/full-refresh-2026-09-11"
NEW_ID = "c6c87882-4b54-5f08-9950-5a8b7ac0f546"
METADATA_ONLY_ID = "874fa451-0ef2-4638-8cfd-c07cef131d7f"
BASELINE_SHA = "dfff7b8af5070254ad76df6c68dd2d6d8a55f7fbc1fe7a53993f61f8703c1d4b"
QUERY_IDS = {
    "060c6964-52b5-48db-af8b-83e4b2d85349",
    "135bf4ac-f9db-461f-b76b-2ee9e30b12c0",
}
EXPECTED_QUERY = """Resources
| where type =~ 'microsoft.network/applicationgateways'
| project id, name, resourceGroup, subscriptionId, location, zones,
    skuName = tostring(properties.sku.name), skuTier = tostring(properties.sku.tier),
    configuredCapacity = properties.sku.capacity,
    autoscaleMinCapacity = properties.autoscaleConfiguration.minCapacity,
    autoscaleMaxCapacity = properties.autoscaleConfiguration.maxCapacity
"""


def content_hash(document):
    return hashlib.sha256(json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()


class FullRefreshReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline_bytes = (REPORTS / "reliability-baseline.json").read_bytes()
        cls.baseline = json.loads(cls.baseline_bytes)
        cls.manifest = json.loads((REPORTS / "reliability-manifest.json").read_text(encoding="utf-8"))
        cls.originals = {r["id"]: r for r in cls.baseline["records"]}
        cls.entries = {r["id"]: r for r in cls.manifest["entries"]}
        cls.documents = [
            load_yaml_document(path) for path in pre_followup_paths()
        ]
        cls.current = {d["id"]: d for d in cls.documents}

    def test_frozen_scope_and_complete_outcome_accounting(self):
        self.assertEqual(hashlib.sha256(self.baseline_bytes).hexdigest(), BASELINE_SHA)
        self.assertEqual(len(self.originals), 427)
        self.assertEqual(set(self.entries), set(self.originals))
        self.assertEqual(set(self.manifest["baselineIds"]), set(self.originals))
        expected = {"updated": 34, "supportedunchanged": 8, "needsmanualreview": 385}
        self.assertEqual(dict(Counter(e["outcome"] for e in self.entries.values())), expected)
        self.assertEqual(self.manifest["summary"], expected)
        owned_now = {
            d["id"] for d in self.documents
            if d.get("waf") == "Reliability" and d["source"]["type"] != "aprl"
        }
        self.assertEqual(owned_now, set(self.originals) | {NEW_ID})
        self.assertEqual(self.manifest["additionCount"], 1)
        for record in self.originals.values():
            self.assertEqual(record["document"]["waf"], "Reliability")
            self.assertNotEqual(record["document"]["source"]["type"], "aprl")

    def test_identity_aliases_original_source_and_scope_preserved(self):
        for identifier, record in self.originals.items():
            before, after = record["document"], self.current[identifier]
            with self.subTest(id=identifier):
                for field in (
                    "id", "name", "labels", "guid", "aliases", "source",
                    "waf", "severity", "resourceTypes", "services", "reviewedDate",
                    "links", "automatable",
                ):
                    self.assertEqual(before.get(field), after.get(field), field)
                    self.assertEqual(field in before, field in after, field)
                self.assertIn(Path(record["path"]).as_posix(), pre_followup_files())

    def test_before_after_hashes_fields_and_unchanged_bytes(self):
        for identifier, entry in self.entries.items():
            before = self.originals[identifier]["document"]
            after = self.current[identifier]
            with self.subTest(id=identifier):
                self.assertEqual(entry["beforeContentSha256"], content_hash(before))
                self.assertEqual(entry["afterContentSha256"], content_hash(after))
                raw = stage_file_bytes(ROOT / entry["path"])
                self.assertEqual(entry["afterFileSha256"], hashlib.sha256(raw).hexdigest())
                fields = {
                    k for k in set(before) | set(after)
                    if before.get(k) != after.get(k) or (k in before) != (k in after)
                }
                self.assertEqual(fields, set(entry["changedFields"]))
                for field, change in entry["changedFields"].items():
                    self.assertEqual(change["before"], before.get(field))
                    self.assertEqual(change["after"], after.get(field))
                    self.assertEqual(change["beforePresent"], field in before)
                    self.assertEqual(change["afterPresent"], field in after)
                if identifier == METADATA_ONLY_ID:
                    self.assertEqual(entry["outcome"], "supportedunchanged")
                    self.assertEqual(fields, {"provenance"})
                    without_mapping = deepcopy(after)
                    without_mapping["provenance"].pop("upstreamRecommendations")
                    self.assertEqual(without_mapping, before)
                elif entry["outcome"] != "updated":
                    self.assertEqual(after, before)
                    self.assertEqual(entry["afterFileSha256"], self.originals[identifier]["fileSha256"])
                else:
                    self.assertTrue(fields <= {"title", "description", "automation", "queries", "provenance"})
                    self.assertIn("provenance", fields)

    def test_evidence_and_honest_gaps(self):
        sources = self.manifest["sourceInventory"]
        self.assertEqual(len(sources), 18)
        for source in sources.values():
            self.assertEqual(source["accessedAt"], "2026-09-11")
            self.assertTrue(source["url"].startswith("https://learn.microsoft.com/"))
            self.assertTrue(source["readingLimits"])
        for identifier, entry in self.entries.items():
            with self.subTest(id=identifier):
                self.assertTrue(entry["evidence"])
                if entry["outcome"] == "needsmanualreview":
                    self.assertTrue(entry["gap"])
                    self.assertEqual(entry["sourceKeys"], [])
                    self.assertIn(self.originals[identifier]["document"]["title"], entry["evidence"])
                else:
                    self.assertTrue(entry["sourceKeys"])
                    self.assertTrue(set(entry["sourceKeys"]) <= set(sources))
                if entry["outcome"] == "updated":
                    current = self.current[identifier]
                    self.assertIsNone(current["provenance"]["lastReviewed"])
                    self.assertIsNone(current["provenance"]["upstreamRevision"])
                    self.assertIsNone(current["automation"]["validatedAt"])
                    self.assertTrue(current["provenance"]["sources"])

    def test_exact_inventory_query_payloads_and_inherited_queries(self):
        changed = set()
        before_count = after_count = 0
        for identifier, entry in self.entries.items():
            before = self.originals[identifier]["document"].get("queries", {}).get("arg")
            after = self.current[identifier].get("queries", {}).get("arg")
            before_count += bool(before)
            after_count += bool(after)
            if before != after:
                changed.add(identifier)
            self.assertEqual(entry["queryAssessment"]["before"], before)
            self.assertEqual(entry["queryAssessment"]["after"], after)
        self.assertEqual(changed, QUERY_IDS)
        self.assertEqual((before_count, after_count), (15, 15))
        for identifier in QUERY_IDS:
            document = self.current[identifier]
            self.assertEqual(document["queries"]["arg"], EXPECTED_QUERY)
            self.assertEqual(document["automation"], {
                "status": "query_available", "resultSemantics": "inventory", "validatedAt": None,
            })
            self.assertIn("zero rows do not establish compliance", document["description"])
            self.assertNotIn("compliant =", document["queries"]["arg"])
        inherited = [e for e in self.entries.values()
                     if e["queryAssessment"]["after"] and e["id"] not in QUERY_IDS]
        self.assertEqual(len(inherited), 13)
        self.assertTrue(all(e["outcome"] == "needsmanualreview" for e in inherited))

    def test_new_check_has_global_overlap_evidence_and_no_identity_collisions(self):
        self.assertEqual([a["id"] for a in self.manifest["additions"]], [NEW_ID])
        addition = self.manifest["additions"][0]
        self.assertEqual(addition["document"], self.current[NEW_ID])
        self.assertEqual(addition["afterContentSha256"], content_hash(self.current[NEW_ID]))
        self.assertEqual(addition["afterFileSha256"],
                         hashlib.sha256(stage_file_bytes(ROOT / addition["path"])).hexdigest())
        self.assertTrue(addition["overlapSearch"]["candidates"])
        self.assertIn("aliases", addition["overlapSearch"]["scope"])
        self.assertEqual(self.current[NEW_ID]["source"]["type"], "curated")
        self.assertEqual(self.current[NEW_ID]["queries"], {})
        self.assertEqual(self.current[NEW_ID]["automation"]["status"], "manual")
        validate_corpus(self.documents)

    def test_shared_schema_and_yaml_roundtrip(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "roundtrip.yaml"
            for identifier in set(self.originals) | {NEW_ID}:
                with self.subTest(id=identifier):
                    document = self.current[identifier]
                    validate_recommendation(document)
                    path.write_text(dump_recommendation(document), encoding="utf-8")
                    self.assertEqual(load_yaml_document(path), document)

    def test_upstream_item_hashes_and_reproducible_coverage(self):
        documents = [self.current[i] for i in set(self.originals) | {NEW_ID}]
        for name, source_id in (("waf", "waf-reliability-checklist"),
                                ("advisor", "advisor-reliability-catalog")):
            inventory = json.loads((REPORTS / f"reliability-{name}-inventory.json").read_text(encoding="utf-8"))
            stored = json.loads((REPORTS / f"reliability-{name}-coverage.json").read_text(encoding="utf-8"))
            validate_inventory(inventory)
            self.assertEqual(inventory["sourceId"], source_id)
            self.assertEqual(inventory["asOf"], "2026-09-11")
            self.assertTrue(inventory["retrievedAt"])
            for item in inventory["items"]:
                self.assertEqual(item["contentHash"], item_content_hash(item["payload"]))
            actual = coverage_report(inventory, documents)
            self.assertEqual(actual, stored)
            if name == "waf":
                self.assertEqual(actual["denominator"], 10)
                self.assertEqual(actual["counts"],
                                 {"full": 1, "partial": 9, "stale": 0, "supporting": 0, "unknown": 0})
                self.assertEqual(actual["coveragePercent"], 10.0)
                self.assertEqual(actual["partialPercent"], 90.0)
            else:
                self.assertEqual(actual["inventoryStatus"], "partial")
                self.assertEqual(actual["observedCount"], 9)
                self.assertIsNone(actual["denominator"])
                self.assertIsNone(actual["coveragePercent"])
                self.assertIsNone(actual["partialPercent"])
                self.assertTrue(actual["reason"])

    def test_mapping_provenance_matches_captured_items_not_just_urls(self):
        mappings = self.manifest["upstreamMappings"]
        self.assertEqual(len(mappings), 19)
        observed = {}
        for name in ("waf", "advisor"):
            inventory = json.loads((REPORTS / f"reliability-{name}-inventory.json").read_text(encoding="utf-8"))
            observed.update({(inventory["sourceId"], item["id"]): item for item in inventory["items"]})
        external = self.manifest["externalUpstreamMappings"]
        self.assertEqual(len(external), 1)
        for mapping in mappings:
            item = observed[(mapping["sourceId"], mapping["recommendationId"])]
            self.assertEqual(mapping["upstreamContentHash"], item["contentHash"])
            self.assertEqual(mapping["url"], item["url"])
            self.assertEqual(mapping["assessedAt"], "2026-09-11")
            self.assertTrue(mapping["notes"])
            identifier = mapping["corpusId"]
            reference = {k: v for k, v in mapping.items() if k != "corpusId"}
            self.assertIn(reference, self.current[identifier]["provenance"]["upstreamRecommendations"])

    def test_bundle_lineage_coverage_needs_no_sidecar(self):
        documents = [self.current[i] for i in set(self.originals) | {NEW_ID}]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "lineage-bundle.json"
            path.write_text(json.dumps(make_bundle(documents, "reliability-lineage-test")), encoding="utf-8")
            bundled = read_bundle(path)["recommendations"]
        self.assertEqual(sum(len(d["provenance"].get("upstreamRecommendations", []))
                             for d in bundled), 19)
        for name in ("waf", "advisor"):
            inventory = json.loads((REPORTS / f"reliability-{name}-inventory.json").read_text(encoding="utf-8"))
            stored = json.loads((REPORTS / f"reliability-{name}-coverage.json").read_text(encoding="utf-8"))
            self.assertEqual(coverage_report(inventory, bundled), stored)
            self.assertTrue(all(len(item["assessments"]) == 1 for item in stored["items"]))
        changes = self.manifest["mappingOnlyMetadataChanges"]
        self.assertEqual([c["id"] for c in changes], [METADATA_ONLY_ID])
        change = changes[0]
        self.assertEqual(change["beforeContentSha256"],
                         content_hash(self.originals[METADATA_ONLY_ID]["document"]))
        self.assertEqual(change["afterContentSha256"], content_hash(self.current[METADATA_ONLY_ID]))
        self.assertEqual(change["referenceCopiedExactly"], {
            k: v for k, v in self.manifest["externalUpstreamMappings"][0].items()
            if k != "corpusId"
        })
        self.assertEqual(self.manifest["lineageIntegration"]["newSemanticAssessments"], 0)
        self.assertEqual(self.manifest["lineageIntegration"]["newNetworkFetches"], 0)
        self.assertFalse(self.manifest["lineageIntegration"]["coverageRequiresExternalMappings"])

    def test_source_id_normalization_preserves_exact_upstream_evidence(self):
        record = json.loads((REPORTS / "reliability-source-id-normalization.json").read_text(encoding="utf-8"))
        self.assertEqual(record["normalizations"], {
            "azure-waf-reliability": "waf-reliability-checklist",
            "azure-advisor-reliability": "advisor-reliability-catalog",
        })
        self.assertEqual(record["newNetworkFetches"], 0)
        self.assertEqual(record["corpusRecordsChanged"], 16)
        self.assertEqual(record["baselineFileSha256Unchanged"], BASELINE_SHA)
        for change in record["records"]:
            expected = deepcopy(change["beforeReferences"])
            for reference in expected:
                reference["sourceId"] = record["normalizations"].get(
                    reference["sourceId"], reference["sourceId"],
                )
            self.assertEqual(expected, change["afterReferences"])
            self.assertEqual(self.current[change["id"]]["provenance"]["upstreamRecommendations"], expected)
            self.assertEqual(change["afterContentSha256"], content_hash(self.current[change["id"]]))
        check = next(c for c in record["centralInventoryChecks"]
                     if c["sourceId"] == "waf-reliability-checklist")
        self.assertEqual(check["exactCentralPayloadHashAgreement"], 10)
        local = json.loads((ROOT / check["localPath"]).read_text(encoding="utf-8"))
        central = json.loads((ROOT / check["centralPath"]).read_text(encoding="utf-8"))
        self.assertEqual(
            {i["id"]: i for i in local["items"]},
            {i["id"]: i for i in central["items"]},
        )
        for mapping in self.manifest["upstreamMappings"]:
            self.assertIn(mapping["sourceId"], {
                "waf-reliability-checklist", "advisor-reliability-catalog",
            })

    def test_stale_and_supporting_mappings_do_not_become_full_coverage(self):
        inventory = json.loads((REPORTS / "reliability-waf-inventory.json").read_text(encoding="utf-8"))
        documents = deepcopy([self.current[i] for i in set(self.originals) | {NEW_ID}])
        new = next(d for d in documents if d["id"] == NEW_ID)
        new["provenance"]["upstreamRecommendations"][0]["upstreamContentHash"] = "sha256:" + "0" * 64
        stale = coverage_report(inventory, documents)
        self.assertEqual(stale["counts"]["stale"], 1)
        self.assertEqual(stale["counts"]["full"], 0)
        for document in documents:
            for reference in document["provenance"].get("upstreamRecommendations", []):
                reference["coverage"] = "supporting"
                reference.pop("upstreamContentHash", None)
        supporting = coverage_report(inventory, documents)
        self.assertEqual(supporting["counts"]["supporting"], 10)
        self.assertIsNone(supporting["coveragePercent"])
        self.assertIsNone(supporting["partialPercent"])

    def test_material_corrections_do_not_reintroduce_old_guarantees(self):
        self.assertIn("7 to 90", self.current["cbfa96b0-5249-4e6f-947c-d0e79509708c"]["title"])
        self.assertIn("April 28, 2026", self.current["1b30c500-4ccd-4608-be41-d21c58fb0bb4"]["description"])
        self.assertNotIn("unless there is a compelling reason", self.current["1b30c500-4ccd-4608-be41-d21c58fb0bb4"]["title"])
        self.assertIn("not an automatic ceiling", self.current["0962db49-c5c0-45b4-9064-c5da949a67b3"]["description"])
        self.assertIn("does not support", self.current["6104ed5f-a4ee-4d87-82dd-1f7bafd7c468"]["description"])
        self.assertIn("an hour or more", self.current["a47e4d1e-bb79-43f9-bf87-69e1032b72fe"]["description"])


if __name__ == "__main__":
    unittest.main()
