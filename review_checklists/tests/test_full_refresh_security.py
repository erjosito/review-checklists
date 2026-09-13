"""Frozen-scope regression checks for the Security corpus refresh."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.modules.cl_corpus import (
    CorpusError, dump_recommendation, validate_corpus,
    validate_recommendation,
)
from review_checklists.tests.service_stage import load_stage_document as load_yaml_document, stage_file_bytes
from review_checklists.source_coverage import (
    coverage_report, item_content_hash, validate_inventory,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "review_checklists" / "docs" / "corpus-refresh" / "full-refresh-2026-09-11"
BASELINE_HASH = "sha256:3e0bb33f7de5c16cf3515bbd771514b2f7053b6a7349f62293a2691e15ab364f"
WITHDRAWN_QUERY_IDS = {
    "ce7f2a7c-297c-47c6-adea-a6ff838db665",
    "6c46b91a-1107-4485-ad66-3183e2a8c266",
    "58d7c892-ddb1-407d-9769-ae669ca48e4a",
    "a0477a20-9945-4bda-9333-4f2491163418",
    "baf8e317-2397-4d49-b3d1-0dcc16d8778d",
    "c115775c-2ea5-45b4-9ad4-8408ee72734b",
    "d9bd3baf-cda3-4b54-bb2e-b03dd9a25827",
}
UPDATED_IDS = {
    "2223ece8-1b12-4318-8a54-17415833fb4a", "829e2edb-2173-4676-aff6-691b4935ada4",
    "09945bda-4333-44f2-9911-634182ba5275", "b86ad884-08e3-4727-94b8-75ba18f20459",
    "4348bf81-7573-4512-8f46-9061cc198fea", "01365d38-e43f-49cc-ad86-8266abca264f",
    "53e8908a-e28c-484c-93b6-b7808b9fe5c4", "14658d35-58fd-4772-99b8-21112df27ee4",
    "1049d403-a923-4c34-94d0-0018ac6a9e01", "984a859c-773e-47d2-9162-3a765a917e1f",
    "387e5ced-126c-4d13-8af5-b20c6998a646", "f4dcf690-1b30-407d-abab-6f8aa780d3a3",
    "85e2223e-ce8b-4b12-907c-a5f16f158e3e", "d2e0d5d7-71d4-41e3-910c-c57b4a4b1410",
    "d1008f3b-5c0d-42ff-8513-fcd6b064fc5d", "913156a1-2476-4e49-b541-acdce979377b",
    "2ba52752-6944-4008-ae7d-7e4843276d8b", "dc055bcf-619e-48a1-9f98-879525d62688",
    "4ac6b67c-b3a4-4ff9-8e87-b07a7ce7bbdb", "cdb3751a-b2ab-413a-ba6e-55d7d8a2adb1",
    "352beee0-79b5-488d-bfc4-972cd3cd21bf", "9f89dc7b-33be-42a1-a27f-7b9e91be1f38",
    "3f1d5e87-2e52-4e36-81cc-58b4a4b1510e", "3e3453a3-c863-4964-ab65-2d6c15f51296",
    "028a71ff-e1ce-415d-b3f0-d5e772d41e36", "77036e5e-6b4b-4ed3-b503-547c1347dc56",
    "e7a8dc4a-20e2-47c3-b297-11b1352beee0", "ad53cc7c-e1d7-4aaa-a357-1449ab8053d8",
    "a07d96be-b231-444c-8b2e-3123950de82f", "3195423b-0513-45e2-951b-87f9c5d534b0",
    "5efa7ffa-1cc0-4a74-bd15-c809185ccb58", "02be562a-9a28-4e56-94a3-a3671dd382fc",
    "0148ed98-3b9a-4b7f-81c2-8b550f56f793", "b174e3db-c952-4b33-a72e-874f60a0f671",
    "b9cbb598-dcaa-431a-bae0-f8a7909f577b", "68266abc-a264-4f9a-89ae-d9c55d04c2c3",
    "eb2eb03d-d9a2-4582-918d-2ddb10725769", "dbeebd4f-c94a-4060-a2ac-c523b3e64a3d",
    "59402f53-7298-4295-b919-609d8fc73876", "78fd4f02-98f6-459c-882c-5f0d659a2251",
    "ef64b1c3-a41f-4913-8ac4-27be04d96d10", "703d13a6-d768-443b-b9f9-4e31d74767f9",
} | WITHDRAWN_QUERY_IDS


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def content_hash(document):
    return sha(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


class FullRefreshSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((ARTIFACTS / "security-baseline.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ARTIFACTS / "security-manifest.json").read_text(encoding="utf-8"))
        cls.before = {r["id"]: r for r in cls.baseline["records"]}
        cls.entries = {r["id"]: r for r in cls.manifest["records"]}
        cls.current = {
            identifier: load_yaml_document(ROOT / row["path"])
            for identifier, row in cls.before.items()
        }
        cls.sources = {
            source["id"]: source for source in
            json.loads((ARTIFACTS / "security-sources.json").read_text(encoding="utf-8"))["sources"]
        }

    def test_frozen_scope_is_exact_and_excludes_aprl(self):
        self.assertEqual(sha((ARTIFACTS / "security-baseline.json").read_bytes()), BASELINE_HASH)
        self.assertEqual(self.manifest["baselineArtifactHash"], BASELINE_HASH)
        self.assertEqual(len(self.baseline["records"]), 565)
        self.assertEqual(len(self.before), 565)
        self.assertEqual(len(self.manifest["records"]), 565)
        self.assertEqual(self.entries.keys(), self.before.keys())
        self.assertEqual(self.manifest["additions"], [])
        for row in self.before.values():
            self.assertEqual(row["before"]["waf"], "Security")
            self.assertNotEqual(row["before"]["source"]["type"], "aprl")

    def test_original_identity_aliases_import_source_and_scope_survive(self):
        aliases = 0
        for identifier, row in self.before.items():
            before, after = row["before"], self.current[identifier]
            with self.subTest(id=identifier):
                for field in ("id", "name", "guid", "labels", "aliases", "source", "waf",
                              "services", "resourceTypes", "severity", "links", "reviewedDate"):
                    self.assertEqual(after.get(field), before.get(field), field)
                self.assertEqual(row["path"], self.entries[identifier]["path"])
                aliases += len(before.get("aliases", []))
        self.assertEqual(aliases, 18)

    def test_outcomes_and_guidance_are_not_provenance_counts(self):
        outcomes = Counter(row["outcome"] for row in self.entries.values())
        self.assertEqual(outcomes, {"updated": 49, "supportedunchanged": 35, "needsmanualreview": 481})
        self.assertEqual({r["id"] for r in self.entries.values() if r["guidanceChanged"]}, UPDATED_IDS)
        self.assertEqual(len(UPDATED_IDS), 49)
        self.assertEqual(self.manifest["counts"]["sourceVerified"], 84)
        self.assertEqual(self.manifest["counts"]["unverified"], 481)
        self.assertEqual(self.manifest["counts"]["provenanceOnly"], 35)
        self.assertEqual(sum(outcomes.values()), 565)

    def test_exact_snapshots_fields_and_file_hashes(self):
        for identifier, row in self.entries.items():
            before = self.before[identifier]["before"]
            after = self.current[identifier]
            with self.subTest(id=identifier):
                self.assertEqual(after, row["after"])
                self.assertEqual(sha(stage_file_bytes(ROOT / row["path"])), row["afterFileHash"])
                self.assertEqual(row["beforeFileHash"], self.before[identifier]["beforeFileHash"])
                self.assertEqual(content_hash(before), row["beforeContentHash"])
                self.assertEqual(content_hash(after), row["afterContentHash"])
                fields = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
                self.assertEqual(fields, row["changedFields"])
                self.assertEqual(row["beforeFields"], {k: before.get(k) for k in fields})
                self.assertEqual(row["afterFields"], {k: after.get(k) for k in fields})
                self.assertLessEqual(set(fields), {"title", "description", "automation", "queries", "provenance"})

    def test_unverified_records_are_unchanged_and_have_explicit_gaps(self):
        for identifier, row in self.entries.items():
            with self.subTest(id=identifier):
                if row["outcome"] == "needsmanualreview":
                    self.assertEqual(row["changedFields"], [])
                    self.assertEqual(row["evidence"], [])
                    self.assertEqual(row["beforeFileHash"], row["afterFileHash"])
                    self.assertEqual(row["unverifiedGap"]["requirement"], self.current[identifier]["title"])
                    self.assertTrue(row["unverifiedGap"]["requiredFollowUp"])
                    self.assertTrue(row["unverifiedGap"]["queryGap"])
                else:
                    self.assertTrue(row["evidence"])
                    self.assertIsNone(row["unverifiedGap"])
                if row["outcome"] == "supportedunchanged":
                    self.assertEqual(row["changedFields"], ["provenance"])
                    self.assertFalse(row["guidanceChanged"])

    def test_provenance_is_additive_and_dates_are_not_approval(self):
        for identifier, row in self.entries.items():
            before = self.before[identifier]["before"]
            after = self.current[identifier]
            with self.subTest(id=identifier):
                for key in ("lastReviewed", "upstreamRevision"):
                    self.assertEqual(after["provenance"].get(key), before["provenance"].get(key))
                self.assertIsNone(after["automation"]["validatedAt"])
                for reference in before["provenance"]["sources"]:
                    self.assertIn(reference, after["provenance"]["sources"])
                for evidence in row["evidence"]:
                    source = self.sources[evidence["sourceRef"]]
                    self.assertTrue(evidence["supports"])
                    self.assertIn({
                        "url": source["url"], "title": source["title"], "accessedAt": "2026-09-11",
                    }, after["provenance"]["sources"])

    def test_exact_kql_withdrawals_and_untouched_queries(self):
        withdrawn = set()
        before_count = after_count = 0
        for identifier, row in self.before.items():
            before = row["before"].get("queries", {}).get("arg", "")
            after = self.current[identifier].get("queries", {}).get("arg", "")
            before_count += bool(before.strip())
            after_count += bool(after.strip())
            with self.subTest(id=identifier):
                if identifier in WITHDRAWN_QUERY_IDS:
                    self.assertTrue(before.strip())
                    self.assertEqual(after, "")
                    self.assertIn(self.current[identifier]["automation"]["status"], ("manual", "candidate"))
                    self.assertNotIn("resultSemantics", self.current[identifier]["automation"])
                    withdrawn.add(identifier)
                else:
                    self.assertEqual(after, before)
                if after.strip():
                    self.assertEqual(self.entries[identifier]["outcome"], "needsmanualreview")
                    self.assertEqual(self.current[identifier]["automation"]["resultSemantics"], "unknown")
        self.assertEqual(withdrawn, WITHDRAWN_QUERY_IDS)
        self.assertEqual((before_count, after_count), (39, 32))

    def test_schema_and_lossless_serialization(self):
        validate_corpus(list(self.current.values()))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "roundtrip.yaml"
            for identifier, after in self.current.items():
                with self.subTest(id=identifier):
                    validate_recommendation(after)
                    path.write_text(dump_recommendation(after), encoding="utf-8")
                    self.assertEqual(load_yaml_document(path), after)
            path.write_text("name: first\nname: duplicate\n", encoding="utf-8")
            with self.assertRaises(CorpusError):
                load_yaml_document(path)
        bad = deepcopy(next(iter(self.current.values())))
        bad["id"] = "not-a-guid"
        with self.assertRaises(CorpusError):
            validate_recommendation(bad)

    def test_key_corrections_retain_technical_qualifiers(self):
        required = {
            "984a859c-773e-47d2-9162-3a765a917e1f": ("at least two", "permanent active", "90 days"),
            "387e5ced-126c-4d13-8af5-b20c6998a646": ("ABAC", "not honored", "before switching"),
            "d1008f3b-5c0d-42ff-8513-fcd6b064fc5d": ("Cilium", "September 30, 2026", "September 30, 2028"),
            "4ac6b67c-b3a4-4ff9-8e87-b07a7ce7bbdb": ("cryptographic keys", "not the general store"),
            "352beee0-79b5-488d-bfc4-972cd3cd21bf": ("Log", "Block", "HDFS", "three-day"),
            "59402f53-7298-4295-b919-609d8fc73876": ("24 hours", "rotated separately", "nonsecret"),
            "a07d96be-b231-444c-8b2e-3123950de82f": ("supports encryption in transit", "does not provide Kerberos"),
            "3f1d5e87-2e52-4e36-81cc-58b4a4b1510e": ("account-level", "does not immediately purge"),
        }
        for identifier, phrases in required.items():
            record = self.current[identifier]
            text = record["title"] + " " + record["description"]
            for phrase in phrases:
                with self.subTest(id=identifier, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_upstream_ids_match_complete_dated_canonical_inventory(self):
        inventory = json.loads((ARTIFACTS / "security-waf-inventory.json").read_text(encoding="utf-8"))
        validate_inventory(inventory)
        self.assertEqual(inventory["sourceId"], "waf-security-checklist")
        self.assertEqual(inventory["inventoryStatus"], "complete")
        self.assertEqual(inventory["asOf"], "2026-09-11")
        self.assertTrue(inventory["retrievedAt"])
        items = {item["id"]: item for item in inventory["items"]}
        self.assertEqual(set(items), {f"SE:{number:02}" for number in range(1, 13)})
        references = []
        for identifier, document in self.current.items():
            for reference in document["provenance"].get("upstreamRecommendations", []):
                if reference["sourceId"] != inventory["sourceId"]:
                    continue
                with self.subTest(id=identifier, control=reference["recommendationId"]):
                    item = items[reference["recommendationId"]]
                    self.assertEqual(set(item["payload"]), {"id", "code", "recommendation"})
                    self.assertEqual(item["contentHash"], item_content_hash(item["payload"]))
                    self.assertEqual(reference["upstreamContentHash"], item["contentHash"])
                    self.assertEqual(reference["url"], item["url"])
                    self.assertEqual(reference["assessedAt"], "2026-09-11")
                    self.assertIn("draft", reference["notes"])
                    self.assertIn("not human approval", reference["notes"])
                    if reference["coverage"] == "full":
                        self.assertEqual(identifier, "b86ad884-08e3-4727-94b8-75ba18f20459")
                        self.assertEqual(reference["recommendationId"], "SE:12")
                    references.append(reference)
        self.assertEqual(len(references), 79)
        report = coverage_report(inventory, list(self.current.values()))
        self.assertEqual(report["denominator"], 12)
        self.assertEqual(report["counts"], {"full": 1, "partial": 9, "stale": 0, "supporting": 0, "unknown": 2})
        self.assertEqual(report["coveragePercent"], 8.33)
        saved = json.loads((ARTIFACTS / "security-waf-coverage.json").read_text(encoding="utf-8"))
        for key, value in report.items():
            self.assertEqual(saved[key], value)
        self.assertIn("draft", saved["reviewStatus"])

    def test_advisor_empty_inventory_is_unknown_not_zero_coverage(self):
        inventory = json.loads((ARTIFACTS / "security-advisor-inventory.json").read_text(encoding="utf-8"))
        validate_inventory(inventory)
        self.assertEqual(inventory["sourceId"], "advisor-security-catalog")
        self.assertEqual(inventory["inventoryStatus"], "unknown")
        self.assertEqual(inventory["items"], [])
        report = coverage_report(inventory, list(self.current.values()))
        self.assertIsNone(report["denominator"])
        self.assertIsNone(report["coveragePercent"])
        self.assertIsNone(report["partialPercent"])
        self.assertTrue(report["reason"])
        self.assertFalse(any(
            reference["sourceId"] == "advisor-security-catalog"
            for document in self.current.values()
            for reference in document["provenance"].get("upstreamRecommendations", [])
        ))

    def test_source_id_normalization_preserves_exact_central_evidence(self):
        audit = json.loads((ARTIFACTS / "security-source-id-normalization.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["counts"], {"changedRecords": 79, "renamedReferences": 79, "guidanceChanges": 0})
        self.assertFalse(audit["guidanceChanged"])
        self.assertFalse(audit["newUpstreamFetch"])
        self.assertEqual(audit["baselineFileHash"], BASELINE_HASH)
        central_path = ROOT / audit["centralInventoryPath"]
        self.assertEqual(sha(central_path.read_bytes()), audit["centralInventoryFileHash"])
        central = json.loads(central_path.read_text(encoding="utf-8"))
        local = json.loads((ARTIFACTS / "security-waf-inventory.json").read_text(encoding="utf-8"))
        self.assertEqual(local["sourceId"], central["sourceId"])
        self.assertEqual(local["items"], central["items"])
        self.assertEqual(len(central["items"]), 12)
        self.assertEqual(len(audit["records"]), 79)
        for row in audit["records"]:
            with self.subTest(id=row["id"]):
                self.assertEqual(row["afterFileHash"], self.entries[row["id"]]["afterFileHash"])
                self.assertEqual(row["afterContentHash"], self.entries[row["id"]]["afterContentHash"])
                for change in row["referenceChanges"]:
                    before, after = deepcopy(change["before"]), deepcopy(change["after"])
                    self.assertEqual(before.pop("sourceId"), "azure-waf-security")
                    self.assertEqual(after.pop("sourceId"), "waf-security-checklist")
                    self.assertEqual(before, after)
                    self.assertIn(change["after"], self.current[row["id"]]["provenance"]["upstreamRecommendations"])
        for row in audit["reports"]:
            self.assertEqual(sha((ARTIFACTS / row["path"]).read_bytes()), row["afterFileHash"])


if __name__ == "__main__":
    unittest.main()
