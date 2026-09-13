"""Scoped regression evidence for the frozen 2026-09-11 Performance refresh."""

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from uuid import NAMESPACE_URL, uuid5

from scripts.modules.cl_corpus import (
    dump_recommendation, validate_corpus, validate_recommendation,
)
from review_checklists.tests.service_stage import load_stage_document as load_yaml_document, stage_file_bytes
from review_checklists.catalog import make_bundle, read_bundle
from review_checklists.source_coverage import (
    SourceCoverageError, coverage_report, item_content_hash, validate_inventory,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "review_checklists" / "docs" / "corpus-refresh" / "full-refresh-2026-09-11"
BASELINE_ID_HASH = "6180f0661f5694948c61440d6a51730f4a11ae97ab7d40ee4384549e4f0fca92"
ADDITIONS = {
    "5c8617a0-c1a5-5d95-9520-646263b48cd9": "performance-FlowPerformanceTargets",
    "0f62530d-f4e5-5687-bba9-8da9e63af7cd": "performance-OperationalTaskBudgets",
    "730f27c7-3b7e-5c10-86e9-00d86105a898": "performance-PerformanceIncidentTriage",
}
POOL_QUERY = """Resources
| where type =~ 'microsoft.containerservice/managedclusters'
| mv-expand pool = properties.agentPoolProfiles
| project id, name, resourceGroup, subscriptionId, poolName = tostring(pool.name),
    vmSize = tostring(pool.vmSize), enableAutoScaling = pool.enableAutoScaling,
    minCount = pool.minCount, maxCount = pool.maxCount, osDiskType = tostring(pool.osDiskType),
    kubeletConfig = pool.kubeletConfig, linuxOSConfig = pool.linuxOSConfig
"""
GATEWAY_QUERY = """Resources
| where type =~ 'microsoft.network/virtualnetworkgateways'
| project id, name, resourceGroup, subscriptionId, location,
    gatewayType = tostring(properties.gatewayType), sku = properties.sku
"""
VNET_QUERY = """Resources
| where type =~ 'microsoft.network/virtualnetworks'
| project id, name, resourceGroup, subscriptionId, location,
    addressSpace = properties.addressSpace, subnets = properties.subnets
"""
QUERY_ASSIGNMENTS = {
    "831c2872-c693-4b39-a887-a561bada49bc": POOL_QUERY,
    "90ce65de-8e13-4f9c-abd4-69266abca264": POOL_QUERY,
    "24367b33-6971-45b1-952b-eee0b9b588de": POOL_QUERY,
    "d4cd21b0-8813-47f5-b6c4-cfd3e504547c": GATEWAY_QUERY,
    "33aad5e8-c68e-41d7-9667-313b4f5664b5": VNET_QUERY,
}


def read_report(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def content_hash(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(data.encode()).hexdigest()


class FullRefreshPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = read_report("performance-baseline.json")
        cls.manifest = read_report("performance-manifest.json")
        cls.rows = cls.manifest["records"]
        cls.additions = cls.manifest["additions"]
        cls.documents = {
            row["id"]: load_yaml_document(ROOT / row["path"])
            for row in cls.rows + cls.additions
        }
        cls.sources = {
            source["id"]: source
            for source in read_report("performance-sources.json")["sources"]
        }
        cls.mappings = read_report("performance-mapping-proposals.json")["mappings"]

    def test_frozen_baseline_and_exact_accounting(self):
        ids = [row["id"] for row in self.baseline["records"]]
        self.assertEqual(len(ids), 175)
        self.assertEqual(len(set(ids)), 175)
        self.assertEqual(hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest(), BASELINE_ID_HASH)
        self.assertEqual({r["id"] for r in self.rows}, set(ids))
        self.assertEqual(len(self.rows), 175)
        self.assertEqual(Counter(r["outcome"] for r in self.rows), {
            "updated": 53, "supported_unchanged": 71, "needs_manual_review": 51,
        })
        self.assertEqual(len(self.documents), 178)
        for row in self.rows:
            self.assertTrue(row["reason"].strip())
            self.assertEqual(row["before"]["waf"], "Performance")
            self.assertNotEqual(row["before"]["source"]["type"], "aprl")
            if row["outcome"] != "needs_manual_review":
                self.assertTrue(row["sourceRefs"], row["id"])
            else:
                self.assertEqual(row["sourceRefs"], [])

    def test_manifest_records_exact_before_after_and_hashes(self):
        baseline = {row["id"]: row for row in self.baseline["records"]}
        for row in self.rows:
            with self.subTest(id=row["id"]):
                original = baseline[row["id"]]
                self.assertEqual(row["before"], original["before"])
                self.assertEqual(row["path"], original["path"])
                self.assertEqual(row["beforeFileHash"], "sha256:" + original["beforeFileHash"])
                self.assertEqual(row["beforeContentHash"], content_hash(row["before"]))
                self.assertEqual(row["after"], self.documents[row["id"]])
                self.assertEqual(row["afterContentHash"], content_hash(row["after"]))
                changed = [
                    k for k in sorted(set(row["before"]) | set(row["after"]))
                    if row["before"].get(k) != row["after"].get(k)
                ]
                self.assertEqual(row["changedFields"], changed)
                self.assertLessEqual(set(changed), {"title", "description", "queries", "automation", "provenance"})
                if row["outcome"] != "updated" and "lineageMetadata" not in row:
                    self.assertEqual(row["afterFileHash"], row["beforeFileHash"])
                    self.assertEqual(changed, [])
                elif row["outcome"] == "supported_unchanged":
                    self.assertEqual(changed, ["provenance"])
                    self.assertEqual(row["lineageMetadata"]["beforeFileHash"], row["beforeFileHash"])
        for row in self.rows + self.additions:
            path = ROOT / row["path"]
            self.assertTrue(path.resolve().is_relative_to(ROOT / "v2" / "recos"))
            self.assertEqual(row["afterFileHash"], "sha256:" + hashlib.sha256(stage_file_bytes(path)).hexdigest())

    def test_original_identity_aliases_classification_and_source_preserved(self):
        aliases = 0
        for row in self.rows:
            before, after = row["before"], self.documents[row["id"]]
            for field in ("id", "name", "source", "aliases", "labels", "waf", "severity", "resourceTypes", "services", "links", "reviewedDate"):
                self.assertEqual(after.get(field), before.get(field), (row["id"], field))
            aliases += len(after.get("aliases", []))
            for field in ("upstreamRevision", "lastReviewed"):
                self.assertEqual(after["provenance"].get(field), before["provenance"].get(field))
        self.assertEqual(aliases, 9)

    def test_scoped_schema_and_yaml_round_trip(self):
        validate_corpus(list(self.documents.values()))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recommendation.yaml"
            for doc in self.documents.values():
                validate_recommendation(doc)
                path.write_text(dump_recommendation(doc), encoding="utf-8")
                self.assertEqual(load_yaml_document(path), doc)

    def test_additions_stable_and_overlap_decisions_recorded(self):
        self.assertEqual({row["id"]: row["after"]["name"] for row in self.additions}, ADDITIONS)
        for row in self.additions:
            doc = row["after"]
            self.assertEqual(doc["id"], str(uuid5(NAMESPACE_URL, "https://github.com/erjosito/review-checklists/" + doc["name"])))
            self.assertEqual(doc, self.documents[doc["id"]])
            self.assertEqual(doc["source"]["type"], "curated")
            self.assertEqual(doc["waf"], "Performance")
            self.assertTrue(row["overlapIds"])
            self.assertTrue(row["reason"])
            self.assertEqual(doc["automation"], {"status": "manual", "validatedAt": None})
            self.assertFalse(doc["queries"])

    def test_exact_queries_are_configuration_inventory_not_compliance(self):
        actual = {identifier: d["queries"]["arg"] for identifier, d in self.documents.items() if d.get("queries", {}).get("arg")}
        self.assertEqual(actual, QUERY_ASSIGNMENTS)
        for identifier, query in actual.items():
            doc = self.documents[identifier]
            self.assertEqual(doc["automation"], {"status": "query_available", "validatedAt": None, "resultSemantics": "inventory"})
            self.assertNotIn("compliant", query.lower())
            self.assertNotIn("cdnresources", query.lower())
            self.assertNotIn("austoscaler", query.lower())
            self.assertIn("zero rows", doc["description"])
            self.assertIn("not been executed", doc["description"])
        queries = read_report("performance-queries.json")
        self.assertEqual({r["id"] for r in queries["removed"]}, {
            "0b5a380c-4bfb-47bc-b1d7-dcfef363a61b", "a13f72f3-8f5c-4864-95e5-75bf37fbbeb1",
        })
        for row in queries["removed"]:
            self.assertEqual(self.documents[row["id"]]["automation"]["status"], "manual")
            self.assertFalse(self.documents[row["id"]].get("queries", {}).get("arg"))
            self.assertTrue(row["arg"])

    def test_honest_additive_source_metadata(self):
        for row in self.rows + self.additions:
            doc = self.documents[row["id"]]
            self.assertIsNone(doc["automation"]["validatedAt"])
            for ref in row.get("sourceRefs", []):
                source = self.sources[ref]
                self.assertEqual(source["accessedAt"], "2026-09-11")
                self.assertTrue(source["readScope"])
                self.assertTrue(source["url"].startswith("https://learn.microsoft.com/"))
            if row.get("outcome") == "updated" or row in self.additions:
                urls = {s["url"] for s in doc["provenance"]["sources"]}
                self.assertTrue({self.sources[key]["url"] for key in row["sourceRefs"]} <= urls)
            for source in row.get("before", {}).get("provenance", {}).get("sources", []):
                self.assertIn(source, doc["provenance"]["sources"])
        text = "\n".join(p.read_text(encoding="utf-8") for p in ARTIFACTS.glob("performance-*.json"))
        self.assertNotIn("C:\\\\Users\\\\", text)
        self.assertNotIn("AppData", text)

    def test_corrected_guidance_and_no_invented_load_test_automation(self):
        self.assertIn("250", self.documents["22f54b29-bade-43aa-b1e8-c38ec9366673"]["description"])
        self.assertIn("native spillover", self.documents["2153dc0b-41f7-4470-abd1-c6ac7522537c"]["title"])
        self.assertIn("not a universal production requirement", self.documents["2b52edf1-c7bc-4108-90c0-d3df81bff610"]["description"])
        self.assertIn("2026-04-28", self.documents["22740e5f-f63b-4b82-8629-fb9d4fd74c36"]["description"])
        self.assertIn("ErGwScale", self.documents["a5327e51-9367-4f91-bca2-71b5724e6acb"]["description"])
        self.assertIn("4 MiB", self.documents["22fb7fa5-e280-4a6a-8ae4-53fcd802c196"]["description"])
        self.assertIn("metadata caching", self.documents["de7e1635-911b-43e8-a887-95b8e13778d1"]["description"])
        for identifier in ("a805eb93-ffa7-4fc8-a8ce-7481da64aa1e", "26455527-f19a-43ef-adf4-29ed5e966a44"):
            self.assertEqual(self.documents[identifier]["automation"]["status"], "manual")
            self.assertIn("percentile", self.documents[identifier]["description"])

    def test_complete_inventories_and_current_explicit_semantic_coverage(self):
        expected = {
            "waf": (12, {"full": 3, "partial": 9, "stale": 0, "supporting": 0, "unknown": 0}),
            "advisor": (150, {"full": 0, "partial": 2, "stale": 0, "supporting": 1, "unknown": 147}),
        }
        for key, (count, states) in expected.items():
            inventory = read_report(f"performance-{key}-inventory.json")
            validate_inventory(inventory)
            self.assertEqual(inventory["inventoryStatus"], "complete")
            self.assertEqual(len(inventory["items"]), count)
            self.assertEqual(inventory["asOf"], "2026-09-11")
            self.assertTrue(inventory["fingerprintScope"])
            for item in inventory["items"]:
                self.assertEqual(item_content_hash(item["payload"]), item["contentHash"])
            report = coverage_report(inventory, list(self.documents.values()))
            self.assertEqual(report, read_report(f"performance-{key}-coverage.json"))
            self.assertEqual(report["denominator"], count)
            self.assertEqual(report["counts"], states)
        self.assertTrue(all(m["corpusId"] in self.documents for m in self.mappings))

    def test_coverage_rejects_stale_or_missing_denominator_as_percentage_evidence(self):
        inventory = read_report("performance-waf-inventory.json")
        stale = deepcopy(list(self.documents.values()))
        for document in stale:
            for mapping in document["provenance"].get("upstreamRecommendations", []):
                mapping["upstreamContentHash"] = "sha256:" + "0" * 64
        result = coverage_report(inventory, stale)
        self.assertIsNone(result["coveragePercent"])
        self.assertEqual(result["counts"]["stale"], 12)
        partial_inventory = deepcopy(inventory)
        partial_inventory["inventoryStatus"] = "partial"
        result = coverage_report(partial_inventory, list(self.documents.values()))
        self.assertIsNone(result["denominator"])
        self.assertIsNone(result["coveragePercent"])
        empty_inventory = deepcopy(inventory)
        empty_inventory["items"] = []
        result = coverage_report(empty_inventory, list(self.documents.values()))
        self.assertIsNone(result["coveragePercent"])

    def test_canonical_source_normalization_and_central_waf_hash_agreement(self):
        normalization = read_report("performance-source-normalization.json")
        entries = {row["toSourceId"]: row for row in normalization["normalizations"]}
        self.assertEqual(set(entries), {"waf-performance-checklist", "advisor-performance-catalog"})
        self.assertEqual({m["sourceId"] for m in self.mappings}, set(entries))
        self.assertEqual(normalization["newUpstreamFetches"], 0)
        self.assertEqual(normalization["foreignFilesModified"], [])
        waf = read_report("performance-waf-inventory.json")
        agreement = entries["waf-performance-checklist"]["centralAgreement"]
        central_path = ROOT / agreement["snapshot"]
        central = json.loads(central_path.read_text(encoding="utf-8"))
        self.assertEqual(waf, central)
        self.assertEqual(agreement["exactPayloadMatches"], 12)
        self.assertEqual(agreement["exactItemHashMatches"], 12)
        self.assertEqual(agreement["fileHash"], "sha256:" + hashlib.sha256(central_path.read_bytes()).hexdigest())
        advisor = read_report("performance-advisor-inventory.json")
        self.assertEqual(advisor["sourceId"], "advisor-performance-catalog")
        self.assertEqual(entries["advisor-performance-catalog"]["itemCount"], 150)
        for row in entries["advisor-performance-catalog"]["itemHashes"]:
            self.assertTrue(row["payloadUnchanged"])
            self.assertEqual(row["before"], row["after"])
        for mapping in self.mappings:
            inventory = waf if mapping["sourceId"] == waf["sourceId"] else advisor
            item = next(i for i in inventory["items"] if i["id"] == mapping["recommendationId"])
            self.assertEqual(mapping["upstreamContentHash"], item["contentHash"])
            self.assertEqual(mapping["url"], item["url"])

    def test_lineage_is_exactly_embedded_with_separate_metadata_only_accounting(self):
        stage = self.manifest["lineageIntegration"]
        self.assertEqual(stage["mappingCount"], 16)
        self.assertEqual(stage["mappedCorpusCount"], 16)
        self.assertEqual(stage["metadataOnlyBaselineCount"], 4)
        self.assertEqual(stage["baselineFilesChangedIncludingLineage"], 57)
        self.assertEqual(stage["baselineByteUnchangedAfterLineage"], 118)
        self.assertEqual(stage["newSemanticAssessments"], 0)
        self.assertEqual(stage["crossOwnedProposalsEmbedded"], 0)
        self.assertFalse(stage["networkAccess"])
        expected = defaultdict(list)
        for mapping in self.mappings:
            expected[mapping["corpusId"]].append({
                key: value for key, value in mapping.items() if key != "corpusId"
            })
        self.assertEqual(len(expected), 16)
        for row in self.rows + self.additions:
            doc = self.documents[row["id"]]
            if row["id"] not in expected:
                self.assertNotIn("lineageMetadata", row)
                self.assertFalse(doc["provenance"].get("upstreamRecommendations"))
                continue
            lineage = row["lineageMetadata"]
            before = lineage["before"]
            self.assertEqual(content_hash(before), lineage["beforeContentHash"])
            self.assertEqual(lineage["addedMappings"], expected[row["id"]])
            self.assertEqual(lineage["changedFields"], ["provenance.upstreamRecommendations"])
            self.assertTrue(lineage["guidanceUnchanged"])
            self.assertEqual(
                doc["provenance"]["upstreamRecommendations"],
                before["provenance"].get("upstreamRecommendations", []) + expected[row["id"]],
            )
            restored = deepcopy(doc)
            if "upstreamRecommendations" in before["provenance"]:
                restored["provenance"]["upstreamRecommendations"] = deepcopy(
                    before["provenance"]["upstreamRecommendations"]
                )
            else:
                del restored["provenance"]["upstreamRecommendations"]
            self.assertEqual(restored, before)
        metadata_only = {
            row["id"] for row in self.rows
            if row["outcome"] == "supported_unchanged" and "lineageMetadata" in row
        }
        self.assertEqual(metadata_only, set(stage["metadataOnlyBaselineIds"]))
        self.assertEqual(sum(row["afterFileHash"] == row["beforeFileHash"] for row in self.rows), 118)

    def test_bundle_retains_lineage_and_coverage_without_sidecars(self):
        bundle = make_bundle(list(self.documents.values()), "performance-lineage-test")
        self.assertEqual(bundle, make_bundle(list(reversed(self.documents.values())), "performance-lineage-test"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bundle.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            reloaded = read_bundle(path)
        self.assertEqual(bundle, reloaded)
        for key in ("waf", "advisor"):
            inventory = read_report(f"performance-{key}-inventory.json")
            self.assertEqual(
                coverage_report(inventory, reloaded["recommendations"]),
                read_report(f"performance-{key}-coverage.json"),
            )
            with self.assertRaises(SourceCoverageError):
                coverage_report(inventory, reloaded["recommendations"], self.mappings)


if __name__ == "__main__":
    unittest.main()
