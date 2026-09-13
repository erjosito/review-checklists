from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest
from uuid import UUID

import yaml
from review_checklists.tests.service_stage import load_stage_document, stage_file_bytes

from review_checklists.source_coverage import coverage_report, item_content_hash, validate_inventory
from scripts.modules.cl_corpus import validate_recommendation


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "review_checklists" / "docs" / "corpus-refresh" / "full-refresh-2026-09-11"


def read_report(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def executable(text):
    return bool(re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S).strip())


class FullRefreshAprlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = read_report("aprl-baseline.json")["records"]
        cls.report = read_report("aprl-review.json")
        cls.rows = {row["id"]: row for row in cls.report["records"]}
        cls.inventory = read_report("aprl-inventory-all.json")
        cls.active = read_report("aprl-inventory-active.json")
        cls.items = {item["id"]: item for item in cls.inventory["items"]}
        cls.recos = {
            row["id"]: load_stage_document(ROOT / row["path"])
            for row in cls.baseline
        }

    def by_index(self, index):
        return self.recos[self.baseline[index]["id"]]

    def test_frozen_ownership_and_identity_are_preserved(self):
        self.assertEqual(self.report["status"], "applied")
        self.assertEqual(len(self.baseline), 333)
        self.assertEqual(len({row["id"] for row in self.baseline}), 333)
        self.assertEqual(set(self.rows), set(self.recos))
        for frozen in self.baseline:
            with self.subTest(identifier=frozen["id"]):
                old, current = frozen["recommendation"], self.recos[frozen["id"]]
                self.assertEqual(old["source"]["type"], "aprl")
                self.assertNotIn("waf", old)
                for field in ("id", "name", "source", "aliases", "labels", "services", "constraints"):
                    self.assertEqual(current.get(field), old.get(field), field)
                self.assertEqual(current["id"], str(UUID(current["id"])))
                validate_recommendation(current)

    def test_before_and_after_byte_evidence(self):
        for frozen in self.baseline:
            with self.subTest(identifier=frozen["id"]):
                self.assertEqual(sha(frozen["originalYaml"].encode("utf-8")), frozen["sha256"])
                self.assertEqual(yaml.safe_load(frozen["originalYaml"]), frozen["recommendation"])
                row = self.rows[frozen["id"]]
                self.assertEqual(row["beforeSha256"], frozen["sha256"])
                self.assertEqual(sha(stage_file_bytes(ROOT / frozen["path"])), row["afterSha256"])

    def test_every_frozen_id_has_a_substantive_assessment(self):
        counts = Counter()
        for row in self.rows.values():
            counts[row["status"]] += 1
            self.assertIn(row["status"], ("updated", "supported_unchanged", "needs_manual_review"))
            self.assertTrue(row["classificationRationale"].strip())
            self.assertTrue(row["decisions"] or row["gaps"])
            self.assertEqual(row["status"] == "needs_manual_review", bool(row["gaps"]))
            self.assertFalse(row["queryAssessment"]["runtimeValidated"])
        self.assertEqual(dict(counts), self.report["counts"]["byStatus"])

    def test_classification_uses_requirement_intent_not_aprl_branding(self):
        self.assertEqual(Counter(r.get("waf", "Unclassified") for r in self.recos.values()), {
            "Reliability": 145, "Operations": 81, "Performance": 60,
            "Security": 43, "Cost": 3, "Unclassified": 1,
        })
        for index, pillar in {
            43: "Security", 42: "Performance", 119: "Cost", 147: "Operations",
            156: "Reliability", 185: "Security", 188: "Performance",
            206: "Reliability", 332: "Performance",
        }.items():
            self.assertEqual(self.by_index(index)["waf"], pillar)
        self.assertNotIn("waf", self.by_index(138))
        self.assertIn("conflicts", self.rows[self.baseline[138]["id"]]["classificationRationale"])

    def test_complete_upstream_denominators_and_payload_hashes(self):
        validate_inventory(self.inventory)
        validate_inventory(self.active)
        self.assertEqual(len(self.inventory["items"]), 456)
        self.assertEqual(len(self.active["items"]), 393)
        self.assertEqual(Counter(item["payload"]["recommendationMetadataState"] for item in self.inventory["items"]),
                         {"Active": 393, "Disabled": 63})
        for item in self.inventory["items"]:
            self.assertEqual(item["id"], str(UUID(item["payload"]["aprlGuid"])))
            self.assertEqual(item["contentHash"], item_content_hash(item["payload"]))
            self.assertIn(self.report["upstreamRevision"], item["url"])
            self.assertNotIn("/docs/archetypes/", item["url"])
        self.assertEqual(self.inventory["asOf"], "2026-09-11")

    def test_full_partial_and_supporting_are_not_id_match_equivalents(self):
        counts = Counter()
        for identifier, reco in self.recos.items():
            row = self.rows[identifier]
            counts[row["coverage"]] += 1
            refs = [ref for ref in reco["provenance"].get("upstreamRecommendations", [])
                    if ref["sourceId"] == "aprl"]
            if row["upstreamState"] == "Missing":
                self.assertNotIn(identifier, self.items)
                self.assertEqual(refs, [])
                self.assertEqual(row["coverage"], "unmapped")
                continue
            self.assertEqual(len(refs), 1)
            reference = refs[0]
            self.assertEqual(reference["recommendationId"], identifier)
            self.assertEqual(reference["upstreamContentHash"], self.items[identifier]["contentHash"])
            self.assertEqual(reference["coverage"], row["coverage"])
            self.assertEqual(reference["assessedAt"], "2026-09-11")
            if row["upstreamState"] == "Disabled":
                self.assertEqual(reference["coverage"], "supporting")
            if reference["coverage"] == "full":
                self.assertEqual(row["upstreamState"], "Active")
                self.assertFalse(row["gaps"])
        self.assertEqual(dict(counts), self.report["counts"]["coverage"])
        self.assertEqual(Counter(row["upstreamState"] for row in self.rows.values()),
                         {"Active": 252, "Disabled": 59, "Missing": 22})

    def test_coverage_reports_reproduce_and_do_not_hide_unknown_ids(self):
        for inventory, filename in [
            (self.inventory, "aprl-coverage-all.json"),
            (self.active, "aprl-coverage-active.json"),
        ]:
            expected = coverage_report(inventory, list(self.recos.values()))
            self.assertEqual(read_report(filename), expected)
            self.assertGreater(expected["counts"]["unknown"], 0)
            self.assertEqual(expected["counts"]["stale"], 0)
            self.assertEqual(expected["denominator"], len(inventory["items"]))
        self.assertEqual(read_report("aprl-coverage-active.json")["counts"]["unknown"], 141)

    def test_no_fabricated_review_or_execution_dates(self):
        for frozen in self.baseline:
            old, current = frozen["recommendation"], self.recos[frozen["id"]]
            self.assertEqual(current["provenance"]["lastReviewed"], old["provenance"]["lastReviewed"])
            self.assertEqual(current["automation"]["validatedAt"], old["automation"]["validatedAt"])
            self.assertIsNone(current["automation"]["validatedAt"])
            self.assertEqual(current.get("reviewedDate"), old.get("reviewedDate"))

    def test_comment_only_payloads_are_not_available_queries(self):
        for reco in self.recos.values():
            query = reco["queries"]["arg"]
            if reco["automation"]["status"] == "query_available":
                self.assertTrue(executable(query), reco["id"])
            else:
                self.assertFalse(query.strip(), reco["id"])

    def test_query_changes_are_bounded_and_preserve_other_bodies(self):
        for frozen in self.baseline:
            identifier = frozen["id"]
            row, current = self.rows[identifier], self.recos[identifier]
            old_query = frozen["recommendation"].get("queries", {}).get("arg", "")
            action = row["queryAssessment"]["action"]
            if action == "retained":
                self.assertEqual(current["queries"]["arg"], old_query)
            elif action == "imported_static_review":
                self.assertEqual(row["queryAssessment"]["afterSha256"], row["queryAssessment"]["currentSha256"])
                self.assertEqual(current["automation"]["resultSemantics"], "inventory")
            else:
                self.assertEqual(current["queries"]["arg"], "")
            self.assertEqual(row["queryAssessment"]["beforeSha256"], sha(old_query.encode("utf-8")))
        self.assertEqual(self.report["counts"]["queryAction"], {
            "retained": 169, "removed_non_executable_marker": 156,
            "imported_static_review": 4, "withdrawn_misleading": 4,
        })

    def test_verified_query_predicate_and_false_positive_regressions(self):
        self.assertIn('sku.tier !in~ ("Standard", "Premium")', self.by_index(110)["queries"]["arg"])
        self.assertIn("isempty(replicaServerId)", self.by_index(153)["queries"]["arg"])
        self.assertIn("sourceServerResourceId", self.by_index(153)["queries"]["arg"])
        self.assertIn('properties.storage.type !~ "PremiumV2_LRS"', self.by_index(156)["queries"]["arg"])
        self.assertIn('properties.storage.autoGrow !~ "Enabled"', self.by_index(156)["queries"]["arg"])
        self.assertIn("isempty(properties.AppSettings), false, true", self.by_index(327)["queries"]["arg"])
        for index in (111, 201, 247, 293):
            self.assertEqual(self.by_index(index)["automation"]["status"], "manual")
            self.assertEqual(self.by_index(index)["queries"]["arg"], "")

    def test_verified_product_guidance_corrections(self):
        expectations = {
            48: ("previously used Azure Disk Encryption", "deallocation"),
            59: ("March 31, 2026", "September 30, 2025"),
            67: ("not universally required at both", "allowed by both"),
            85: ("Azure Monitor is the monitoring service", "diagnostic settings"),
            130: ("supported LTS", "Serverless"),
            187: ("7-90 days", "RBAC assignments"),
            204: ("April 28, 2026", "no longer has support or an SLA"),
            236: ("does not itself protect against a region-wide outage", "backend instances"),
            247: ("September 30, 2027", "New NSG flow-log creation is no longer supported"),
            287: ("14 to 180 days", "additional charges"),
            293: ("Basic, Standard, and Premium", "property can be false"),
            297: ("not a region-wide outage", "not DTU Basic or Standard"),
            332: ("not available on the Consumption plan", "not invoked for restarts"),
        }
        for index, snippets in expectations.items():
            for snippet in snippets:
                self.assertIn(snippet, self.by_index(index)["description"])
        self.assertEqual(self.by_index(297)["resourceTypes"], ["Microsoft.Sql/servers/databases"])
        self.assertEqual(self.by_index(249)["resourceTypes"], ["Microsoft.Network/networkWatchers/flowlogs"])
        self.assertIn("2000", self.by_index(310)["title"])
        self.assertIn("not independently verified", " ".join(self.rows[self.baseline[310]["id"]]["gaps"]))

    def test_first_round_duplicate_reports_are_unchanged(self):
        redactions = json.loads(
            (ROOT / "review_checklists" / "docs" / "corpus-refresh" / "report-redactions.json")
            .read_text(encoding="utf-8")
        )["reports"]
        for relative, digest in self.report["immutablePriorReports"].items():
            path = ROOT.joinpath(*relative.replace("\\", "/").split("/"))
            if relative in redactions:
                self.assertEqual(redactions[relative]["beforeSha256"], digest)
                self.assertEqual(
                    sha(path.read_bytes()), redactions[relative]["afterSha256"], relative,
                )
                continue
            self.assertEqual(sha(path.read_bytes()), digest, relative)


if __name__ == "__main__":
    unittest.main()
