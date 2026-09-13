"""Exact second-round Cost decisions and live corpus, independent of other pillars."""

from collections import Counter
import hashlib
import json
from pathlib import Path, PureWindowsPath
import unittest
from urllib.parse import urlparse

from scripts.modules.cl_corpus import (
    dump_recommendation, validate_corpus, validate_recommendation,
)
from review_checklists.tests.service_stage import (
    load_stage_document as load_yaml_document, stage_file_bytes, stage_file_text,
)
from review_checklists.tests.followup_stage import pre_followup_paths
from review_checklists.source_coverage import coverage_report, item_content_hash, validate_inventory


ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "review_checklists" / "docs" / "corpus-refresh"
ARTIFACTS = HISTORY / "full-refresh-2026-09-11"
UPDATED_IDS = {
    "0d6d5b07-c475-408c-8f6a-fa8c92b96957", "550bf6a6-0fd6-4f5e-a447-fefda36067bc",
    "73965cc9-1763-43c1-82aa-549b3ea75f4e", "3100afcf-2db1-4f14-901c-bd5e33bc29ff",
    "9e2fb33a-0e01-43c6-9de0-2409778ad08d", "8c51bdd3-d4cb-4742-a323-89917c6ac87e",
    "a1abac7c-cce9-4443-97e8-2faf150559d4", "d310e9bc-ae3d-4eff-90a1-8356d72a1376",
    "fb012775-b93d-442c-916c-81ca72d7bc91", "393a040f-d329-4479-ab11-88b2c5a46ceb",
    "a6bcca2b-4fea-41db-b3dd-95d48c7c891d", "544451e1-92d3-4442-a3c7-628637a551c5",
    "620cb68e-2005-464b-90d3-0e767babcfcd", "afad2446-229b-4b5c-89fc-33e0a1ffdf05",
    "45c1b3bf-8e01-4337-984d-e8b03a969e4c", "1d3deb66-a7cf-4c9e-8071-3b3e3d60c478",
    "3da1dae2-cc88-4147-8607-c1cca0e61465", "8dd458e9-2713-49b8-8110-2dbd6eaf11e6",
    "f397a438-b320-46f8-a41a-f94545db3412", "9dd18ccf-33eb-4da0-9710-7b3d64290faa",
    "54bceac0-695d-4d3a-9e50-91fdb4c9f51a", "72af3409-f6b8-43b7-b254-31990577bb73",
    "bb6048c7-29fd-4388-aa22-de89fdbb39ea", "72b9477f-3c39-4633-a052-90b1203f9be5",
    "f3dd18d1-9937-413e-99a6-6abbe25b574c", "220f8243-dcba-41cd-95c1-70b8b0cc3bd2",
    "f3715e13-e5c7-4830-b1a0-4319523efab1",
}
NEW_QUERY_IDS = {
    "544451e1-92d3-4442-a3c7-628637a551c5": "e10b1381-5f0a-47ff-8c7b-37bd13d7c974",
    "a6bcca2b-4fea-41db-b3dd-95d48c7c891d": "0eb54047-acd9-4f26-8ffb-8cec713782d6",
    "f397a438-b320-46f8-a41a-f94545db3412": "1c7fc5ab-f776-4aee-8236-ab478519f68f",
}
WAF_MAPPINGS = {
    ("CO:01", "wafsg-CostSavingGoalsCloudFinancialDiscipline"): "partial",
    ("CO:02", "cost-WorkloadCostModelUnitEconomics"): "full",
    ("CO:03", "revcl-SetupCostReportingAzureCostManagement"): "partial",
    ("CO:03", "revcl-ForecastedBudgetAlertsActual"): "partial",
    ("CO:04", "wafsg-CostGuardrailsGovernancePolicies"): "partial",
    ("CO:05", "wafsg-RightBillingModelCommitmentBasedModels"): "partial",
    ("CO:06", "wafsg-AzureOpenaiPriceBreakpointsNextBillingPeriod"): "partial",
    ("CO:07", "cost-AppServiceEmptyPlans"): "partial",
    ("CO:08", "wafsg-EnvironmentCostsPreProductionEnvironments"): "partial",
    ("CO:10", "revcl-LowerTierCustomizedRule"): "partial",
    ("CO:11", "wafsg-CheaperVmSizesResourceUsage"): "partial",
    ("CO:12", "wafsg-CostEffectiveApproachPriorityQueues"): "partial",
    ("CO:14", "wafsg-HighAvailabilityRequirementsCentralizedServices"): "partial",
}
ADVISOR_MAPPINGS = {
    ("e10b1381-5f0a-47ff-8c7b-37bd13d7c974", "revcl-Vms"): "full",
    ("e10b1381-5f0a-47ff-8c7b-37bd13d7c974", "revcl-RightSizingVmsUsage"): "partial",
    ("94aea435-ef39-493f-a547-8408092c22a7", "revcl-RightSizingVmsUsage"): "partial",
    ("0eb54047-acd9-4f26-8ffb-8cec713782d6", "revcl-LargerDisksTib"): "partial",
    ("1c7fc5ab-f776-4aee-8236-ab478519f68f", "wafsg-AzureFrontDoorOriginGroupSingleBackEndPools"): "partial",
    ("39a8510f-5bbf-4304-9bcd-4106c996473b", "cost-AppServiceEmptyPlans"): "full",
    ("a4255ba5-b07e-45ae-99ca-25e6c2079e3c", "cost-CosmosIdleContainers"): "full",
    ("cdf51428-a41b-4735-ba23-39f3b7cde20c", "cost-CosmosThroughputEconomics"): "partial",
    ("10aedd06-621e-4b4f-a45c-5256573e0191", "revcl-AzureVmwareSolutionInstances"): "full",
    ("afdf4c1a-e46b-4817-a5d6-4b9909f58e2a", "revcl-ServerlessApacheSparkAutomaticPauseFeatureTimeoutValue"): "partial",
    ("5b8ddf04-be28-44ec-ab2c-a63a34d1de13", "wafsg-ConsistentUsagePatternDedicatedComputeInstances"): "partial",
}


class FullRefreshCostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((ARTIFACTS / "cost-baseline.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ARTIFACTS / "cost-refresh-manifest.json").read_text(encoding="utf-8"))
        cls.sources = json.loads((ARTIFACTS / "cost-sources.json").read_text(encoding="utf-8"))
        cls.coverage = json.loads((ARTIFACTS / "cost-source-coverage.json").read_text(encoding="utf-8"))
        cls.before = {r["id"]: r for r in cls.baseline["records"]}
        cls.decisions = {r["id"]: r for r in cls.manifest["records"]}
        cls.paths, cls.live = {}, {}
        for path in pre_followup_paths():
            document = load_yaml_document(path)
            # This stage owns frozen IDs, not APRL checks classified as Cost later.
            if document["id"] in cls.before:
                if document["id"] in cls.live:
                    raise AssertionError("Duplicate Cost canonical ID")
                cls.live[document["id"]] = document
                cls.paths[document["id"]] = path

    def test_frozen_history_is_pinned_and_all_226_records_are_accounted_for(self):
        self.assertEqual(self.manifest["status"], "applied")
        self.assertEqual(hashlib.sha256((ARTIFACTS / "cost-baseline.json").read_bytes()).hexdigest(),
                         self.manifest["baselineSha256"])
        self.assertEqual(self.manifest["historicalArtifacts"], self.baseline["historicalArtifacts"])
        for name, expected in self.baseline["historicalArtifacts"].items():
            self.assertEqual(hashlib.sha256((HISTORY / name).read_bytes()).hexdigest(), expected)
        self.assertEqual(len(self.baseline["records"]), 226)
        self.assertEqual(len(self.manifest["records"]), 226)
        self.assertEqual(set(self.live), set(self.before))
        self.assertTrue(all(record.get("waf") == "Cost" for record in self.live.values()))
        self.assertEqual(set(self.decisions), set(self.before))
        self.assertEqual(self.manifest["additions"], [])
        self.assertEqual(Counter(r["contentOutcome"] for r in self.decisions.values()), {
            "updated": 27, "supported_unchanged": 122, "needs_manual_review": 77,
        })
        self.assertEqual({guid for guid, r in self.decisions.items() if r["contentOutcome"] == "updated"},
                         UPDATED_IDS)

    def test_exact_live_results_and_unchanged_records_match_the_manifest(self):
        allowed = {"title", "description", "automation", "queries", "provenance"}
        for guid, before_row in self.before.items():
            with self.subTest(id=guid):
                before, actual = before_row["document"], self.live[guid]
                decision = self.decisions[guid]
                expected = decision.get("after", before)
                self.assertEqual(actual, expected)
                changed = {key for key in set(before) | set(actual) if before.get(key) != actual.get(key)}
                self.assertEqual(changed, set(decision["changedFields"]))
                self.assertTrue(changed <= allowed)
                self.assertEqual(decision["beforeFileSha256"], before_row["fileSha256"])
                self.assertEqual(hashlib.sha256(stage_file_bytes(self.paths[guid])).hexdigest(),
                                 decision["afterFileSha256"])
                self.assertEqual(self.paths[guid],
                                 ROOT.joinpath(*PureWindowsPath(decision["corpusFile"]).parts))
                if guid not in UPDATED_IDS:
                    if decision["upstreamMappings"]:
                        self.assertEqual(changed, {"provenance"})
                        self.assertEqual({k: v for k, v in actual.items() if k != "provenance"},
                                         {k: v for k, v in before.items() if k != "provenance"})
                    else:
                        self.assertEqual(actual, before)
                        self.assertEqual(decision["afterFileSha256"], before_row["fileSha256"])
                else:
                    self.assertEqual(stage_file_text(self.paths[guid]), dump_recommendation(actual))
                    self.assertNotEqual(actual["title"], before["title"])
                    self.assertTrue(actual["description"])

    def test_identity_import_origin_aliases_and_review_dates_are_exact(self):
        aliases = []
        for guid, before_row in self.before.items():
            with self.subTest(id=guid):
                before, actual = before_row["document"], self.live[guid]
                for field in ("id", "guid", "name", "source", "labels", "aliases", "reviewedDate",
                              "services", "resourceTypes", "severity", "waf", "automatable", "links"):
                    self.assertEqual(actual.get(field), before.get(field), field)
                for field in ("lastReviewed", "upstreamRevision"):
                    self.assertEqual(actual["provenance"][field], before["provenance"][field])
                self.assertIsNone(actual["automation"]["validatedAt"])
                for source in before["provenance"]["sources"]:
                    self.assertIn(source, actual["provenance"]["sources"])
                aliases.extend(actual.get("aliases", []))
        self.assertEqual(len(aliases), 9)
        self.assertEqual(len({a["id"] for a in aliases}), 9)
        self.assertFalse(set(self.live) & {a["id"] for a in aliases})
        for pair in self.manifest["deferredMergeGroups"]:
            self.assertEqual(len(pair), 2)
            self.assertTrue(set(pair) <= set(self.live))

    def test_every_supported_decision_has_specific_public_source_evidence(self):
        sources = {s["id"]: s for s in self.sources["sourceInventory"]}
        self.assertEqual(len(sources), 19)
        for source in sources.values():
            self.assertEqual(urlparse(source["url"]).hostname, "learn.microsoft.com")
            self.assertEqual(urlparse(source["url"]).scheme, "https")
            self.assertEqual(source["accessedAt"], "2026-09-11")
            self.assertTrue(source["readingScope"])
            self.assertTrue(source["title"])
            self.assertEqual(set(source["supportsIds"]), {
                guid for guid, d in self.decisions.items() if source["id"] in d["sourceRefs"]
            })
        for guid, decision in self.decisions.items():
            with self.subTest(id=guid):
                self.assertTrue(decision["reason"].strip())
                self.assertTrue(set(decision["sourceRefs"]) <= set(sources))
                if decision["contentOutcome"] == "needs_manual_review":
                    self.assertEqual(decision["sourceRefs"], [])
                    self.assertEqual(decision["changedFields"], [])
                else:
                    self.assertTrue(decision["sourceRefs"])
                if guid in UPDATED_IDS:
                    actual_sources = self.live[guid]["provenance"]["sources"]
                    for ref in decision["sourceRefs"]:
                        source = sources[ref]
                        self.assertIn({k: source[k] for k in ("url", "title", "accessedAt")}, actual_sources)
        self.assertEqual(self.sources["coverageStatus"], "measured_for_two_explicit_inventory_scopes")
        for decision in self.decisions.values():
            self.assertEqual(decision["mappingOutcome"], "explicit_id_assessment" if decision["upstreamMappings"]
                             else "not_assessed_against_inventory")

    def test_mappings_match_exact_upstream_ids_payloads_and_scope_metrics(self):
        expected = {"waf-cost-checklist": WAF_MAPPINGS, "advisor-cost-catalog": ADVISOR_MAPPINGS}
        self.assertEqual(len(self.sources["upstreamInventories"]), 2)
        for origin in self.sources["upstreamInventories"]:
            source_id = origin["sourceId"]
            inventory = json.loads((ARTIFACTS / origin["artifact"]).read_text(encoding="utf-8"))
            original_path = ROOT.joinpath(*PureWindowsPath(origin["originalArtifact"]).parts)
            self.assertEqual(hashlib.sha256(original_path.read_bytes()).hexdigest(), origin["originalFileSha256"])
            original = json.loads(original_path.read_text(encoding="utf-8"))
            self.assertEqual(original["sourceId"], origin["originalSourceId"])
            self.assertEqual(original["sourceId"], source_id)
            self.assertEqual(inventory, original)
            self.assertTrue(origin["payloadAndHashAgreement"])
            self.assertEqual(origin["verifiedItemCount"], len(original["items"]))
            validate_inventory(inventory)
            items = {item["id"]: item for item in inventory["items"]}
            actual_pairs = {}
            for guid, document in self.live.items():
                references = document["provenance"].get("upstreamRecommendations", [])
                self.assertEqual(references, self.decisions[guid]["upstreamMappings"])
                for reference in references:
                    if reference["sourceId"] != source_id:
                        continue
                    key = (reference["recommendationId"], document["name"])
                    self.assertNotIn(key, actual_pairs)
                    actual_pairs[key] = reference["coverage"]
                    item = items[reference["recommendationId"]]
                    self.assertEqual(reference["upstreamContentHash"], item_content_hash(item["payload"]))
                    self.assertEqual(reference["upstreamContentHash"], item["contentHash"])
                    self.assertEqual(reference["url"], item["url"])
                    self.assertEqual(reference["assessedAt"], "2026-09-11")
                    self.assertIn("not independent human approval or live Azure validation", reference["notes"])
            self.assertEqual(actual_pairs, expected[source_id])
            report = coverage_report(inventory, list(self.live.values()))
            self.assertEqual(report, self.coverage["reports"][source_id])
            self.assertEqual(report["counts"], {
                "full": 1, "partial": 11, "stale": 0, "supporting": 0, "unknown": 2,
            } if source_id == "waf-cost-checklist" else {
                "full": 4, "partial": 6, "stale": 0, "supporting": 0, "unknown": 56,
            })
            self.assertEqual(report["denominator"], 14 if source_id == "waf-cost-checklist" else 66)
            self.assertEqual(report["referencesOutsideInventory"], [])

    def test_three_new_queries_have_exact_grounded_filters_and_inventory_semantics(self):
        queries = {q["recommendationId"]: q for q in self.sources["queryCatalog"]}
        self.assertEqual(set(queries), set(NEW_QUERY_IDS))
        template = self.before["570cc0b7-8bcc-54bc-b0a3-abf24374c97b"]["document"]["queries"]["arg"]
        for guid, remote_id in NEW_QUERY_IDS.items():
            with self.subTest(id=guid):
                expected = template.replace(
                    "| project id,",
                    f"| where tostring(properties.recommendationTypeId) in~ ('{remote_id}')\n| project id,",
                    1,
                )
                actual = self.live[guid]
                self.assertEqual(actual["queries"], {"arg": expected})
                self.assertEqual(queries[guid]["kql"], expected)
                self.assertEqual(queries[guid]["upstreamRecommendationIds"], [remote_id])
                self.assertEqual(queries[guid]["role"], "primary")
                self.assertFalse(queries[guid]["liveExecuted"])
                self.assertIsNone(queries[guid]["validatedAt"])
                self.assertEqual(actual["automation"]["status"], "query_available")
                self.assertEqual(actual["automation"]["resultSemantics"], "inventory")
                self.assertIn("Empty or truncated results do not establish compliance", actual["automation"]["notes"])
                self.assertNotIn("complianceColumn", actual["automation"])
                self.assertNotRegex(expected, r"(?i)\bcompliant\b|\bjoin\b|\btake\b")
        for guid, document in self.live.items():
            if guid not in NEW_QUERY_IDS:
                self.assertEqual(document.get("queries"), self.before[guid]["document"].get("queries"))
        self.assertEqual(sum(bool(d.get("queries", {}).get("arg", "").strip()) for d in self.live.values()), 34)
        self.assertEqual(len({d["queries"]["arg"] for d in self.live.values()
                              if d.get("queries", {}).get("arg", "").strip()}), 31)

    def test_fixed_technical_claims_do_not_regress(self):
        assertions = {
            "3da1dae2-cc88-4147-8607-c1cca0e61465": ["only HTTP 200", "HTTP 204 is a failed", "HEAD"],
            "8dd458e9-2713-49b8-8110-2dbd6eaf11e6": ["HEAD", "unconditional successful response"],
            "f3715e13-e5c7-4830-b1a0-4319523efab1": ["overflow", "provisioned v1", "differential"],
            "bb6048c7-29fd-4388-aa22-de89fdbb39ea": ["Soft-Deleted Usage", "recovery"],
            "73965cc9-1763-43c1-82aa-549b3ea75f4e": ["Do not assume generating 100 images", "token-based or time-based"],
            "3100afcf-2db1-4f14-901c-bd5e33bc29ff": ["not a guarantee", "client-side batching alone"],
            "393a040f-d329-4479-ab11-88b2c5a46ceb": ["no availability SLA", "not an auction", "retained-disk charges"],
            "a6bcca2b-4fea-41db-b3dd-95d48c7c891d": ["P30 through P80", "per matching disk SKU", "Premium SSD v2"],
            "620cb68e-2005-464b-90d3-0e767babcfcd": ["not Azure Resource Manager", "not guaranteed"],
        }
        for guid, phrases in assertions.items():
            for phrase in phrases:
                self.assertIn(phrase, self.live[guid]["description"])
        for guid in ("550bf6a6-0fd6-4f5e-a447-fefda36067bc", "d310e9bc-ae3d-4eff-90a1-8356d72a1376"):
            self.assertIn("max_output_tokens", self.live[guid]["description"])
            self.assertIn("max_completion_tokens", self.live[guid]["description"])
        for guid in ("9877f353-2591-4e8b-8381-e9043fed1010", "71dc00cd-4392-4262-8949-20c05e6c0333"):
            self.assertEqual(self.decisions[guid]["contentOutcome"], "needs_manual_review")
            self.assertIn("SAP", self.decisions[guid]["reason"])

    def test_stage_metrics_distinguish_content_review_and_historical_cohorts(self):
        summary = self.manifest["summary"]
        self.assertEqual(summary["changedYamlFiles"], 45)
        self.assertEqual(summary["mappingOnlyYamlFiles"], 18)
        self.assertEqual(summary["mappedCanonicalRecords"], 22)
        self.assertEqual(summary["upstreamMappingAssignments"], 24)
        self.assertEqual(summary["baselineCostCanonical"], 226)
        self.assertEqual(summary["finalCostCanonical"], 226)
        self.assertEqual(summary["finalCostAliases"], 9)
        self.assertEqual(summary["baselinePrimaryAssignments"], 31)
        self.assertEqual(summary["finalPrimaryAssignments"], 34)
        self.assertEqual(summary["newPrimaryQueries"], 3)
        self.assertEqual(summary["newSupplementalQueries"], 0)
        self.assertEqual(summary["historicalSupplementalQueries"], 6)
        self.assertEqual(summary["historicalCohorts"], {
            "first-round-addition": {"supported_unchanged": 5, "needs_manual_review": 3},
            "first-round-update": {"supported_unchanged": 15, "needs_manual_review": 33},
            "previously-untouched-merge-survivor": {"supported_unchanged": 8, "needs_manual_review": 1},
            "truly-untouched-original": {"updated": 27, "supported_unchanged": 94, "needs_manual_review": 40},
        })
        for cohort, outcomes in summary["historicalCohorts"].items():
            self.assertEqual(outcomes, Counter(d["contentOutcome"] for d in self.decisions.values()
                                               if d["historicalCohort"] == cohort))

    def test_shared_schema_and_durable_artifact_path_hygiene(self):
        validate_corpus(list(self.live.values()))
        for document in self.live.values():
            validate_recommendation(document)
        for path in ARTIFACTS.glob("cost-*"):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"(?i)\b[a-z]:[\\/]")
                self.assertNotIn(".copilot", text)
                self.assertNotIn("Users\\", text)
