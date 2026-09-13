"""Bounded Operations refresh: exact ownership, evidence and query safeguards."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.modules.cl_corpus import (
    dump_recommendation,
    validate_corpus,
)
from review_checklists.tests.service_stage import load_stage_document as load_yaml_document, stage_file_bytes
from review_checklists.tests.followup_stage import pre_followup_paths
from review_checklists.source_coverage import coverage_report, item_content_hash, validate_inventory


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "review_checklists" / "docs" / "corpus-refresh" / "full-refresh-2026-09-11"
GUID_HASH = "f181032b378471c61106a7f4fd0890242b0731dbf5f8372e63a87b815be7e363"
NEW_IDS = {
    "482a84af-0360-55ab-be33-6d8e4706b580": "operations-VersionedOperationalRunbooks",
    "eac9d939-9c58-5bf4-aa1d-1c77d8068036": "operations-ReliableLifecycleAutomation",
}
EXPECTED_QUERIES = {
    "eaa8dc4a-2436-47b3-9697-15b1752beee0": (
        "Resources\n"
        "| where type =~ 'microsoft.containerservice/managedclusters'\n"
        "| project id, name, resourceGroup, subscriptionId, monitoringEnabled = properties.addonProfiles.omsagent.enabled, workspaceResourceId = properties.addonProfiles.omsagent.config.logAnalyticsWorkspaceResourceID, useManagedIdentity = properties.addonProfiles.omsagent.config.useAADAuth\n"
    ),
    "73b32a5a-67f7-4a9e-b5b3-1f38c3f39812": (
        "Resources\n"
        "| where type =~ 'microsoft.containerservice/managedclusters'\n"
        "| project id, name, resourceGroup, subscriptionId, nodeResourceGroup = properties.nodeResourceGroup\n"
    ),
}
REMOVED_QUERIES = {
    "c755562f-2b4e-4456-9b4d-874a748b662e",
    "af95c92d-d723-4f4a-98d7-8722324efd4d",
}


def content_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def file_hash(path):
    return "sha256:" + hashlib.sha256(stage_file_bytes(path)).hexdigest()


def corpus_path(relative):
    return ROOT.joinpath(*relative.replace("\\", "/").split("/"))


class FullRefreshOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((REPORTS / "operations-baseline.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((REPORTS / "operations-manifest.json").read_text(encoding="utf-8"))
        cls.originals = {r["id"]: r for r in cls.baseline["records"]}
        cls.outcomes = {r["id"]: r for r in cls.manifest["records"]}
        cls.current = {
            identifier: load_yaml_document(corpus_path(item["path"]))
            for identifier, item in cls.originals.items()
        }
        cls.additions = {
            item["id"]: load_yaml_document(corpus_path(item["path"]))
            for item in cls.manifest["additions"]
        }

    def test_frozen_ownership_and_exact_accounting(self):
        identifiers = sorted(self.originals)
        self.assertEqual(len(identifiers), 279)
        self.assertEqual(hashlib.sha256("\n".join(identifiers).encode()).hexdigest(), GUID_HASH)
        self.assertEqual(set(self.outcomes), set(self.originals))
        self.assertEqual(len(self.manifest["records"]), 279)
        self.assertEqual(
            Counter(item["outcome"] for item in self.outcomes.values()),
            {"updated": 38, "supportedunchanged": 38, "needsmanualreview": 203},
        )
        self.assertEqual(self.manifest["outcomes"], dict(Counter(r["outcome"] for r in self.outcomes.values())))
        for original in self.originals.values():
            self.assertEqual(original["before"]["waf"], "Operations")
            self.assertNotEqual(original["before"]["source"]["type"], "aprl")

    def test_identity_origin_aliases_and_classification_preserved(self):
        self.assertEqual(sum(len(r["before"].get("aliases", [])) for r in self.originals.values()), 11)
        for identifier, item in self.originals.items():
            with self.subTest(id=identifier):
                current = self.current[identifier]
                for key in ("id", "name", "aliases", "labels", "source", "resourceTypes", "services", "waf", "severity"):
                    self.assertEqual(current.get(key), item["before"].get(key), key)
                self.assertNotEqual(current["source"]["type"], "aprl")

    def test_exact_before_after_fields_and_file_hashes(self):
        for identifier, outcome in self.outcomes.items():
            with self.subTest(id=identifier):
                before = self.originals[identifier]["before"]
                after = self.current[identifier]
                self.assertEqual(outcome["beforeContentHash"], content_hash(before))
                self.assertEqual(outcome["afterContentHash"], content_hash(after))
                self.assertEqual(outcome["afterFileHash"], file_hash(corpus_path(outcome["path"])))
                changes = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
                self.assertEqual(outcome["changedFields"], changes)
                self.assertEqual(outcome["fieldChanges"], {
                    key: {"before": before.get(key), "after": after.get(key)} for key in changes
                })
                if outcome["outcome"] != "updated":
                    self.assertEqual(after, before)
                    self.assertEqual(outcome["beforeFileHash"], outcome["afterFileHash"])

    def test_honest_source_and_review_metadata(self):
        sources = {s["id"]: s for s in self.manifest["sourceInventory"]}
        self.assertEqual(len(sources), 28)
        for source in sources.values():
            self.assertEqual(source["accessedAt"], "2026-09-11")
            self.assertTrue(source["url"].startswith("https://learn.microsoft.com/"))
            self.assertTrue(source["readScope"])
        for identifier, outcome in self.outcomes.items():
            self.assertTrue(outcome["reason"])
            self.assertTrue(outcome["gap"])
            self.assertTrue(outcome["sourceRefs"])
            self.assertTrue(set(outcome["sourceRefs"]) <= set(sources))
            before = self.originals[identifier]["before"]
            after = self.current[identifier]
            for key in ("upstreamRevision", "lastReviewed"):
                self.assertEqual(after["provenance"][key], before["provenance"][key])
            self.assertEqual(after["automation"]["validatedAt"], before["automation"]["validatedAt"])
            if outcome["outcome"] == "updated":
                for ref in outcome["sourceRefs"]:
                    self.assertIn(
                        {k: sources[ref][k] for k in ("url", "title", "accessedAt")},
                        after["provenance"]["sources"],
                    )
            elif outcome["outcome"] == "needsmanualreview":
                self.assertEqual(after["provenance"], before["provenance"])

    def test_all_four_query_heuristics_reconciled(self):
        prior_queries = {
            identifier for identifier, item in self.originals.items()
            if item["before"].get("queries", {}).get("arg", "").strip()
        }
        self.assertEqual(prior_queries, set(EXPECTED_QUERIES) | REMOVED_QUERIES)
        queries = {
            identifier: record["queries"]["arg"]
            for identifier, record in self.current.items()
            if record.get("queries", {}).get("arg", "").strip()
        }
        self.assertEqual(queries, EXPECTED_QUERIES)
        self.assertEqual(self.manifest["primaryQueriesBefore"], 4)
        self.assertEqual(self.manifest["primaryQueriesAfter"], 2)
        for identifier, query in queries.items():
            record = self.current[identifier]
            self.assertEqual(record["automation"]["resultSemantics"], "inventory")
            self.assertIsNone(record["automation"]["validatedAt"])
            self.assertNotIn("compliant", query.lower())
            self.assertNotIn("complianceColumn", record["automation"])
            self.assertIn("zero rows", record["description"])
        for identifier in REMOVED_QUERIES:
            self.assertEqual(self.current[identifier]["automation"]["status"], "manual")
            self.assertFalse(self.current[identifier]["queries"].get("arg", "").strip())

    def test_stale_guidance_corrections_remain_explicit(self):
        self.assertIn("March 31, 2026", self.outcomes["619e8a13-f988-4795-85d6-26886d70ba6c"]["reason"])
        avs = self.current["4ed90dae-2cc8-44c4-9b6b-781cbafe6c46"]
        self.assertNotIn("Deploy the Log Analytics Agents", avs["title"])
        self.assertIn("Azure Monitor Agent", avs["title"])
        self.assertIn("does not make a client support a newer TLS", self.current["1e9aecf0-747c-47c6-936e-a0c404ae8e21"]["description"])
        self.assertIn("same", self.originals["d4909fdf-867b-43b7-828d-197247a83530"]["before"]["title"])
        self.assertIn("shared capacity", self.current["d4909fdf-867b-43b7-828d-197247a83530"]["description"])

    def test_curated_additions_are_unique_manual_checks_with_overlap_decisions(self):
        self.assertEqual({k: r["name"] for k, r in self.additions.items()}, NEW_IDS)
        self.assertEqual(self.manifest["additionsCount"], 2)
        for item in self.manifest["additions"]:
            record = self.additions[item["id"]]
            self.assertEqual(record["source"]["type"], "curated")
            self.assertEqual(record["waf"], "Operations")
            self.assertEqual(record["automation"], {"status": "manual", "validatedAt": None})
            self.assertFalse(record["queries"])
            self.assertTrue(item["reason"])
            self.assertEqual(item["afterContentHash"], content_hash(record))
            self.assertEqual(item["afterFileHash"], file_hash(corpus_path(item["path"])))
        all_records = [load_yaml_document(path) for path in pre_followup_paths()]
        validate_corpus(all_records)

    def test_shared_strict_round_trip_for_owned_records(self):
        records = [*self.current.values(), *self.additions.values()]
        validate_corpus(records)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recommendation.yaml"
            for record in records:
                path.write_text(dump_recommendation(record), encoding="utf-8")
                self.assertEqual(load_yaml_document(path), record)

    def test_upstream_ids_are_real_current_inventory_items(self):
        reports = json.loads((REPORTS / "operations-source-coverage.json").read_text(encoding="utf-8"))
        expected = {
            "waf-operations-checklist": ("operations-waf-inventory.json", 11, 2, 6, 3),
            "advisor-operations-catalog": ("operations-advisor-inventory.json", 122, 3, 2, 117),
        }
        external = [
            {key: value for key, value in mapping.items() if key != "storage"}
            for mapping in self.manifest["upstreamMappings"]
            if mapping["storage"] == "external-report"
        ]
        records = [*self.current.values(), *self.additions.values()]
        for saved in reports["sources"]:
            filename, total, full, partial, unknown = expected[saved["sourceId"]]
            inventory = json.loads((REPORTS / filename).read_text(encoding="utf-8"))
            validate_inventory(inventory)
            self.assertEqual(inventory["inventoryStatus"], "complete")
            self.assertEqual(inventory["asOf"], "2026-09-11")
            self.assertTrue(inventory["retrievedAt"])
            self.assertEqual(len(inventory["items"]), total)
            current = coverage_report(inventory, records, external)
            self.assertEqual(saved, current)
            self.assertEqual(current["counts"], {
                "full": full, "partial": partial, "unknown": unknown,
                "supporting": 0, "stale": 0,
            })
            self.assertEqual(current["denominator"], total)
            self.assertEqual(current["referencesOutsideInventory"], [])
            for row in current["items"]:
                self.assertTrue(all(a["hashMatches"] for a in row["assessments"]))
        proposal = reports["crossOwnedProposals"][0]
        self.assertEqual(proposal["status"], "proposed-not-applied")
        self.assertNotIn(proposal["corpusId"], self.current)

    def test_source_id_normalization_preserves_evidence_and_accounting(self):
        audit = json.loads((REPORTS / "operations-source-id-normalization.json").read_text(encoding="utf-8"))
        renames = {
            "azure-waf-operations": "waf-operations-checklist",
            "azure-advisor-operations": "advisor-operations-catalog",
        }
        self.assertEqual(audit["sourceIdRenames"], renames)
        self.assertTrue(audit["noNetworkFetch"])
        self.assertFalse(audit["guidanceChanged"])
        self.assertFalse(audit["coverageCountsChanged"])
        self.assertEqual(audit["changedRecordCount"], 23)
        self.assertEqual(audit["changedReferenceCount"], 24)
        self.assertEqual(audit["changedExternalReferenceCount"], 3)
        self.assertEqual(sum(m["storage"] == "external-report" for m in self.manifest["upstreamMappings"]), 3)
        self.assertEqual(len(audit["records"]), 23)
        self.assertEqual(sum(len(r["referenceChanges"]) for r in audit["records"]), 24)
        records = {**self.current, **self.additions}
        for entry in audit["records"]:
            current = records[entry["id"]]
            prior = json.loads(json.dumps(current))
            for change in entry["referenceChanges"]:
                matching = [
                    ref for ref in prior["provenance"]["upstreamRecommendations"]
                    if ref["sourceId"] == change["afterSourceId"]
                    and ref["recommendationId"] == change["recommendationId"]
                ]
                self.assertEqual(len(matching), 1)
                self.assertEqual(renames[change["beforeSourceId"]], change["afterSourceId"])
                self.assertEqual(matching[0]["upstreamContentHash"], change["unchangedUpstreamContentHash"])
                matching[0]["sourceId"] = change["beforeSourceId"]
            self.assertEqual(content_hash(prior), entry["beforeContentHash"])
            self.assertEqual(
                "sha256:" + hashlib.sha256(dump_recommendation(prior).encode("utf-8")).hexdigest(),
                entry["beforeFileHash"],
            )
            self.assertEqual(content_hash(current), entry["afterContentHash"])
            self.assertEqual(file_hash(corpus_path(entry["path"])), entry["afterFileHash"])
        for record in records.values():
            for ref in record["provenance"].get("upstreamRecommendations", []):
                self.assertNotIn(ref["sourceId"], renames)
        for mapping in self.manifest["upstreamMappings"]:
            self.assertNotIn(mapping["sourceId"], renames)
        for entry in audit["inventories"]:
            inventory = json.loads(corpus_path(entry["path"]).read_text(encoding="utf-8"))
            self.assertEqual(inventory["sourceId"], entry["afterSourceId"])
            self.assertEqual(entry["beforeItemsHash"], entry["afterItemsHash"])
            self.assertEqual(item_content_hash({"items": inventory["items"]}), entry["afterItemsHash"])
            if entry["centralAgreement"] == "exact-all-item-payloads-and-hashes":
                central = json.loads(corpus_path(entry["centralInventory"]).read_text(encoding="utf-8"))
                self.assertEqual(central["sourceId"], inventory["sourceId"])
                self.assertEqual(
                    {item["id"]: (item["payload"], item["contentHash"]) for item in central["items"]},
                    {item["id"]: (item["payload"], item["contentHash"]) for item in inventory["items"]},
                )
                self.assertEqual(entry["matchingItemCount"], len(inventory["items"]))
            else:
                self.assertEqual(entry["centralAgreement"], "pending-pipeline-integration")
                self.assertNotIn("matchingItemCount", entry)

    def test_artifact_paths_are_repository_relative(self):
        for item in [*self.manifest["records"], *self.manifest["additions"]]:
            path = item["path"].replace("\\", "/")
            self.assertTrue(path.startswith("v2/recos/"))
            self.assertNotIn("..", path.split("/"))
            self.assertNotIn(":", path)
        for path in REPORTS.glob("operations-*.json"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("C:\\\\Users\\\\", text)
            self.assertNotIn("C:/Users/", text)


if __name__ == "__main__":
    unittest.main()
