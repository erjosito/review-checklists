"""Exact first-round/merge history, pinned to the immutable second-round baseline."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PureWindowsPath
import unittest
from urllib.parse import urlparse
from uuid import UUID

from scripts.modules.cl_corpus import (
    dump_recommendation, load_yaml_document, validate_corpus, validate_recommendation,
)
from review_checklists.catalog import canonical_json, content_hash
from review_checklists.merge import read_merge_manifest


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "review_checklists" / "docs" / "corpus-refresh"
UPDATE_IDS = {
    "fc6998a5-35e3-4378-a7e3-1c67d68cf6a6",
    "d0102cac-6aae-401e-9a84-de5de36d1d92",
    "9269756b-3f6f-4066-907b-a24ef20d44c9",
    "a491dfc4-9353-4213-9217-eef0949f9467",
    "c7acbe49-bbe6-44dd-a9f2-e87778468d55",
    "cb1f7d57-59ae-4568-aa38-d4985e2213db",
    "72eb7a10-acdd-47f4-ac63-c2366162dca0",
    "75c1e945-b459-4837-bf7a-e7c6d3b475a5",
    "59ae568b-a38d-4498-9e22-13dbd7bb012f",
    "6e2065b3-a76a-4f4a-991e-8839ada46667",
    "d7bb012f-7b95-4e06-b158-e2ea3992c2de",
    "6aae01e6-a84d-4e5d-b36d-1d92881a1bd5",
    "92d34429-3c76-4286-97a5-51c5b04e4f18",
    "64f9a19a-f29c-495d-94c6-c7919ca0f6c5",
    "f4e7926a-ec35-476e-a412-5dd17136bd62",
    "7025b442-f6e9-4af6-b11f-c9574916016f",
    "c36e0c83-11b4-409a-a4a6-2118b52a380f",
    "7947e534-c9a8-435b-9e03-d300143b5f74",
    "c1b1cd52-1e54-4a29-a9de-39ac0e7c28dc",
    "ff159e4c-281f-4c30-aa1c-819ce3c94aad",
    "1104dc91-14f0-4330-ac7d-fa85039a0802",
    "f82cb8eb-8c0a-4a63-a25a-4956eaa8dc4a",
    "357e61fe-86e6-41c6-b446-3f0def6d8bcf",
    "3c328ad3-02b3-4b44-b833-e8e0edcf8fd8",
    "a95b86ad-8840-48e3-9273-4b875ba18f20",
    "674b5ed8-5a85-49c7-933b-e2a1a27b765a",
    "91be1f38-8ef3-494c-8bd4-63cbbac75819",
    "29fd366b-a180-452b-9bd7-954b7700c667",
    "32952499-58c8-4e6f-ada5-972e67893d55",
    "35e33789-7e31-4c67-b68c-f6a62a119495",
    "389aca19-a7d5-4abb-82f6-66716e25023a",
    "e68a487c-dec4-4861-ac3b-c10ae77e26e4",
    "d5a3bec2-c4e2-4436-a133-6db55f17960e",
    "c4e2436b-1336-4db5-9f17-960eee0bdf5c",
    "d1e44a19-659d-4395-afd7-7289b835556d",
    "edc3f7bc-6b6c-41a8-8f11-1485781fdf58",
    "4fb53237-e44f-4292-a7a5-f8e79d55fc4e",
    "6a667592-f9c4-45ba-81c8-bb4841aa8781",
    "11b05f06-7a9a-4f25-9816-f41f893897b4",
    "f455ac95-f1e3-4a9a-9fab-044e7faeff2f",
    "ff5136bd-dcf1-4d2b-ae52-39333efdf45a",
    "45901365-d38e-443f-abcb-d868266abca2",
    "84808948-46c4-4cd5-aa74-b79826a19b32",
    "1572941a-e08a-4d0c-bae6-5af048bbcc2a",
    "ad53cc7d-e2e8-4aaa-a357-1549ab9153d8",
    "0e7c28dc-9366-4572-82bf-f4564b0d934a",
    "359c363e-7dd6-4162-9a36-4a907ebae38e",
    "6e043e2a-a359-4271-ae6e-205172676ae4",
}
ADDITION_IDS = {
    "570cc0b7-8bcc-54bc-b0a3-abf24374c97b": "cost-AdvisorActionBacklog",
    "ccf66d9e-1364-576b-9b40-16f91a5b52b7": "cost-WorkloadCostModelUnitEconomics",
    "4f3e4c7b-78e3-5170-8ef9-903de93cd563": "cost-SqlDatabaseComputeModel",
    "82a6242d-ee75-51c0-bf02-bd357c422c30": "cost-SqlEmptyElasticPools",
    "ed807702-4e85-5b2e-b191-3fc76fe70a60": "cost-CosmosThroughputEconomics",
    "577a5f04-5ce3-5bf2-be7b-28c1ec86f362": "cost-CosmosIdleContainers",
    "28856508-bfa7-5f94-82d8-7f6b53817bfe": "cost-ManagedDiskSnapshotLifecycle",
    "fe224a34-ae94-57de-8570-e8bae87812f7": "cost-AppServiceEmptyPlans",
}
EXPRESSROUTE_IDS = {
    "f4e7926a-ec35-476e-a412-5dd17136bd62",
    "7025b442-f6e9-4af6-b11f-c9574916016f",
}
RETIRED_TO_CANONICAL = {
    "96bcda1b-240a-4d4b-93fa-6872b549d711": "d0c4b44f-7b43-428c-93f2-dedd7bf00799",
    "30cbe437-b17d-45ad-a42e-a26bef6f4b77": "6f1432ef-61d2-4037-8f85-58e005d16b8c",
    "0ce550b6-f2ed-428c-b8c2-b224c065a0db": "ac8bb190-71ba-48ec-9fef-351c1cd5501f",
    "7327aac3-008f-4878-bf49-a6c3f76746a1": "edd459fa-3105-4a03-b009-4f983d23da5a",
    "96599299-4653-4e94-989b-8c7fe64cb2bd": "92eec823-61dd-486c-b46e-0339fc02987e",
    "5473960a-7ac3-44a0-8d01-695132b782cd": "18f1f2f6-de79-405d-b7a1-65fb571c0493",
    "f0c38fed-fc9f-458d-aab7-9b03b8a0dfea": "a5675d94-de9f-44b1-8b21-f8032cdf3f3d",
    "2d710fcf-b8bc-461d-81a1-895193ce91cc": "73967d95-39ff-47bb-b4f4-33ddade69d1f",
    "a36bac4f-bf10-44c6-a51e-0d845162b3af": "3c5f0966-3c57-4e15-a6b0-6cb73405bbf1",
}


class CostRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ARTIFACTS / "cost-refresh-manifest.json").read_text(encoding="utf-8"))
        cls.research = json.loads((ARTIFACTS / "cost-research.json").read_text(encoding="utf-8"))
        cls.migration = json.loads((ARTIFACTS / "cost-alias-migration.json").read_text(encoding="utf-8"))
        cls.approved_merges = read_merge_manifest(ARTIFACTS / "post-cost-safe-merge-manifest.json")
        cls.merge_originals = {
            document["id"]: document for group in cls.migration["mergeResult"]["groups"]
            for document in group["originalRecommendations"]
        }
        cls.sources = {source["id"]: source for source in cls.research["sourceInventory"]}
        cls.catalog = cls.research["queryCatalog"]
        round_dir = ARTIFACTS / "full-refresh-2026-09-11"
        baseline_path = round_dir / "cost-baseline.json"
        cls.next_manifest = json.loads((round_dir / "cost-refresh-manifest.json").read_text(encoding="utf-8"))
        cls.stage = json.loads(baseline_path.read_text(encoding="utf-8"))
        if hashlib.sha256(baseline_path.read_bytes()).hexdigest() != cls.next_manifest["baselineSha256"]:
            raise AssertionError("Second-round baseline no longer matches its pinned manifest")
        cls.stage_by_path = {
            ROOT.joinpath(*PureWindowsPath(row["corpusFile"]).parts): row
            for row in cls.stage["records"]
        }
        cls.documents = [
            load_yaml_document(path) for path in (ROOT / "v2" / "recos").rglob("*.yaml")
        ]
        cls.documents = [d for d in cls.documents if d.get("waf") != "Cost"] + [
            row["document"] for row in cls.stage["records"]
        ]
        cls.cost = {d["id"]: d for d in cls.documents if d.get("waf") == "Cost"}
        cls.entries = cls.manifest["updates"] + cls.manifest["additions"]
        cls.proposals = {
            guid: update["proposed"] for guid, update in cls.research["updatesByExistingGuid"].items()
        }
        cls.proposals.update({
            addition["suggestedId"]: addition for addition in cls.research["proposedAdditions"]
        })

    def test_expected_ids_counts_and_unchanged_cost_records(self):
        self.assertEqual({entry["id"] for entry in self.manifest["updates"]}, UPDATE_IDS)
        self.assertEqual(
            {entry["id"]: entry["name"] for entry in self.manifest["additions"]}, ADDITION_IDS,
        )
        self.assertEqual(set(self.research["updatesByExistingGuid"]), UPDATE_IDS)
        baseline = set(self.manifest["baselineCostIds"])
        self.assertEqual(len(baseline), 227)
        self.assertEqual(set(self.cost), (baseline | set(ADDITION_IDS)) - set(RETIRED_TO_CANONICAL))
        self.assertEqual(len(self.cost), 226)
        all_identities = {
            identity["id"] for document in self.cost.values()
            for identity in [document, *document.get("aliases", [])]
        }
        self.assertEqual(all_identities, baseline | set(ADDITION_IDS))
        untouched = self.manifest["untouchedCostContentSha256"]
        self.assertEqual(set(untouched), baseline - UPDATE_IDS)
        self.assertEqual(len(untouched), 179)
        participants = set(RETIRED_TO_CANONICAL) | set(RETIRED_TO_CANONICAL.values())
        self.assertEqual(set(self.merge_originals), participants)
        self.assertFalse(participants & set(self.proposals))
        self.assertEqual(len(set(untouched) - participants), 161)
        for guid, expected in untouched.items():
            with self.subTest(id=guid):
                document = self.merge_originals[guid] if guid in participants else self.cost[guid]
                actual = hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()
                self.assertEqual(actual, expected)
        self.assertEqual(self.manifest["deferredAdditions"], [])
        self.assertEqual(self.manifest["summary"]["deferredAdditions"], 0)

    def test_only_approved_merges_preserve_exact_content_and_retired_identities(self):
        groups = self.migration["mergeResult"]["groups"]
        approved = {group["canonicalId"]: group for group in self.approved_merges}
        self.assertEqual(len(groups), 9)
        self.assertEqual({
            retired: group["canonicalId"] for group in groups for retired in group["retiredIds"]
        }, RETIRED_TO_CANONICAL)
        self.assertEqual({
            retired: group["canonicalId"]
            for group in self.approved_merges for retired in group["retiredIds"]
        }, RETIRED_TO_CANONICAL)
        self.assertEqual({
            entry["retiredId"]: entry["canonicalId"] for entry in self.migration["retiredToCanonical"]
        }, RETIRED_TO_CANONICAL)
        aliases = {
            alias["id"]: (document["id"], alias) for document in self.cost.values()
            for alias in document.get("aliases", [])
        }
        self.assertEqual({guid: owner for guid, (owner, _) in aliases.items()}, RETIRED_TO_CANONICAL)
        deferred_ids = {
            "7947e534-c9a8-435b-9e03-d300143b5f74", "74ad737c-cbb8-4e91-84b7-2aa937b37ede",
            "c36e0c83-11b4-409a-a4a6-2118b52a380f", "271b6cfe-4507-4afa-a1e5-000e3be105ac",
        }
        self.assertTrue(deferred_ids <= set(self.cost))
        self.assertFalse(deferred_ids & set(aliases))
        for group in groups:
            with self.subTest(id=group["canonicalId"]):
                canonical_id = group["canonicalId"]
                approval = approved[canonical_id]
                originals = group["originalRecommendations"]
                self.assertEqual([document["id"] for document in originals],
                                 [canonical_id, *approval["retiredIds"]])
                self.assertEqual(group["reason"], approval["reason"])
                self.assertEqual(group["beforeContentHash"], approval["beforeContentHash"])
                self.assertEqual(content_hash(originals), approval["beforeContentHash"])
                original_files = {entry["id"]: entry for entry in group["originalFiles"]}
                self.assertEqual(set(original_files), {document["id"] for document in originals})
                expected = deepcopy(originals[0])
                expected["links"] = list({
                    canonical_json(link): link
                    for document in originals for link in document.get("links", [])
                }.values())
                expected["provenance"]["sources"] = list({
                    source["url"]: source
                    for document in originals for source in document["provenance"]["sources"]
                }.values())
                expected["aliases"] = []
                for original in originals:
                    self.assertEqual(original["waf"], "Cost")
                    self.assertEqual(original["queries"], {})
                    self.assertEqual(original["automation"], {"status": "unknown", "validatedAt": None})
                    self.assertEqual(original["provenance"], {
                        "upstreamRevision": None, "lastReviewed": None, "sources": [],
                    })
                    self.assertNotIn("aliases", original)
                    original_file = original_files[original["id"]]
                    self.assertRegex(original_file["sha256"], r"^[0-9a-f]{64}$")
                    if original["id"] != canonical_id:
                        expected_alias = {
                            "id": original["id"], "name": original["name"],
                            "source": original["source"], "labels": original.get("labels", {}),
                            "corpusFile": original_file["path"],
                        }
                        expected["aliases"].append(expected_alias)
                        self.assertEqual(aliases[original["id"]], (canonical_id, expected_alias))
                        retired_path = ROOT.joinpath("v2", "recos", *PureWindowsPath(original_file["path"]).parts)
                        self.assertFalse(retired_path.exists())
                    if original.get("description"):
                        self.assertIn(original["description"], expected["description"])
                actual = self.cost[canonical_id]
                self.assertEqual(actual, expected)
                self.assertEqual(content_hash([actual]), group["afterContentHash"])
                canonical_path = ROOT.joinpath("v2", "recos", *PureWindowsPath(group["canonicalFile"]).parts)
                stage_row = self.stage_by_path[canonical_path]
                self.assertEqual(stage_row["document"], actual)
                self.assertEqual(stage_row["fileSha256"], group["afterFileSha256"])
                self.assertEqual(hashlib.sha256(dump_recommendation(actual).encode()).hexdigest(),
                                 group["afterFileSha256"])
        for entry in self.migration["retiredToCanonical"]:
            original = self.merge_originals[entry["retiredId"]]
            canonical = self.cost[entry["canonicalId"]]
            self.assertEqual(entry["retiredName"], original["name"])
            self.assertEqual(entry["canonicalName"], canonical["name"])
            alias = aliases[entry["retiredId"]][1]
            self.assertEqual(PureWindowsPath(entry["retiredFile"]), PureWindowsPath(alias["corpusFile"]))
            canonical_path = ROOT.joinpath("v2", "recos", *PureWindowsPath(entry["canonicalFile"]).parts)
            self.assertEqual(self.stage_by_path[canonical_path]["document"], canonical)

    def test_merge_stage_metrics_and_historical_evidence_remain_distinct(self):
        migration = self.migration
        self.assertEqual(migration["status"], "applied")
        self.assertEqual(migration["mergeResult"]["mode"], "write")
        self.assertEqual(migration["mergeResult"]["before"], 2014)
        self.assertEqual(migration["mergeResult"]["after"], 2005)
        self.assertEqual(migration["mergeResult"]["retired"], 9)
        for path, hash_key in (
            ("post-cost-safe-merge-manifest.json", "approvalManifestSha256"),
            ("cost-refresh-manifest.json", "historicalRefreshManifestSha256"),
            ("cost-research.json", "researchArtifactSha256"),
        ):
            self.assertEqual(hashlib.sha256((ARTIFACTS / path).read_bytes()).hexdigest(), migration[hash_key])
        statuses = dict(Counter(document["automation"]["status"] for document in self.cost.values()))
        self.assertEqual(migration["afterMetrics"], {
            "canonicalRecommendations": 2005, "aliases": 55,
            "costCanonicalRecommendations": len(self.cost),
            "costAliases": sum(len(document.get("aliases", [])) for document in self.cost.values()),
            "costPrimaryAssignments": sum(bool(document.get("queries", {}).get("arg", "").strip())
                                        for document in self.cost.values()),
            "costUniquePrimaryQueries": len({
                document["queries"]["arg"] for document in self.cost.values()
                if document.get("queries", {}).get("arg", "").strip()
            }),
            "costAutomationStatusCounts": statuses,
        })
        self.assertEqual(statuses, {"unknown": 170, "manual": 11, "candidate": 14, "query_available": 31})
        self.assertEqual(migration["beforeMetrics"], {
            "canonicalRecommendations": 2014, "aliases": 46, "costCanonicalRecommendations": 235,
            "costAliases": 0, "costPrimaryAssignments": 31, "costUniquePrimaryQueries": 28,
            "costAutomationStatusCounts": {"unknown": 179, "manual": 11, "candidate": 14, "query_available": 31},
        })
        self.assertEqual(migration["coverageAccounting"], {
            "originalCostIdentities": 227, "refreshUpdatedIdentities": 48, "refreshAddedIdentities": 8,
            "refreshStageUntouchedIdentities": 179, "previouslyUntouchedMergeParticipants": 18,
            "previouslyUntouchedSurvivingCanonicals": 9, "previouslyUntouchedRetiredAliases": 9,
            "trulyUntouchedCanonicalRecords": 161, "refreshedOrAddedCanonicalsUnchangedByMerges": 56,
            "primarySourceCountUnchanged": 30, "researchQueryVariantsUnchanged": 34,
            "supplementalOnlyQueryVariantsUnchanged": 6,
        })

    def test_updates_preserve_identity_and_all_unmodified_legacy_fields(self):
        allowed = {
            "title", "description", "services", "resourceTypes", "automation", "queries", "provenance",
        }
        for entry in self.manifest["updates"]:
            with self.subTest(id=entry["id"]):
                before, after = entry["before"], self.cost[entry["id"]]
                self.assertEqual(
                    {k: v for k, v in before.items() if k not in allowed},
                    {k: v for k, v in after.items() if k not in allowed},
                )
                self.assertEqual(after["id"], before["id"])
                self.assertEqual(after["labels"]["guid"], before["labels"]["guid"])
                self.assertEqual(after["source"], before["source"])
                for key in ("upstreamRevision", "lastReviewed"):
                    self.assertEqual(after["provenance"][key], before["provenance"][key])
                for source in before["provenance"]["sources"]:
                    self.assertIn(source, after["provenance"]["sources"])
                self.assertEqual(set(entry["changedFields"]), {
                    key for key in after if before.get(key) != after[key]
                })
                recorded = self.research["updatesByExistingGuid"][entry["id"]]
                for old, field in (
                    ("existingName", "name"), ("existingTitle", "title"),
                    ("existingDescription", "description"), ("existingQueries", "queries"),
                ):
                    self.assertEqual(recorded[old], before.get(field))

    def test_guidance_and_services_match_approved_proposals_without_inferred_aliases(self):
        for guid, proposal in self.proposals.items():
            with self.subTest(id=guid):
                actual = self.cost[guid]
                for key in ("title", "description", "services", "resourceTypes", "severity", "waf"):
                    self.assertEqual(actual[key], proposal[key])
                self.assertEqual(actual["queries"], proposal["queries"])
                self.assertEqual(actual["automation"]["status"], proposal["automation"]["status"])
                self.assertIn(proposal["automation"]["reason"], actual["automation"]["notes"])
                for unsupported in ("sourceRefs", "queryRefs", "sources", "liveValidated"):
                    self.assertNotIn(unsupported, actual)

    def test_source_inventory_and_provenance_are_public_and_honest(self):
        self.assertEqual(len(self.sources), 30)
        used_sources = set()
        for source in self.sources.values():
            self.assertEqual(urlparse(source["url"]).scheme, "https")
            self.assertEqual(urlparse(source["url"]).hostname, "learn.microsoft.com")
            self.assertEqual(source["accessedDate"], "2026-09-11")
            self.assertTrue(source["verification"])
        for entry in self.entries:
            with self.subTest(id=entry["id"]):
                proposal = self.proposals[entry["id"]]
                expected_refs = set(proposal["sourceRefs"])
                for query_ref in proposal["queryRefs"]:
                    expected_refs.update(self.catalog[query_ref]["sourceRefs"])
                self.assertEqual(set(entry["sourceRefs"]), expected_refs)
                used_sources.update(expected_refs)
                actual = self.cost[entry["id"]]
                self.assertIsNone(actual["automation"]["validatedAt"])
                self.assertIsNone(actual["provenance"]["lastReviewed"])
                self.assertIsNone(actual["provenance"]["upstreamRevision"])
                provenance = {source["url"]: source for source in actual["provenance"]["sources"]}
                for ref in expected_refs:
                    source = self.sources[ref]
                    self.assertEqual(provenance[source["url"]], {
                        "url": source["url"], "title": source["title"], "accessedAt": "2026-09-11",
                    })
        self.assertEqual(used_sources, set(self.sources))

    def test_additions_have_curated_sources_and_collision_free_uuid5_identities(self):
        ids, names = [], []
        for document in self.documents:
            for identity in [document, *document.get("aliases", [])]:
                if identity["id"] in ADDITION_IDS:
                    ids.append(identity["id"])
                if identity["name"].casefold() in {name.casefold() for name in ADDITION_IDS.values()}:
                    names.append(identity["name"].casefold())
        self.assertEqual(Counter(ids), Counter(ADDITION_IDS.keys()))
        self.assertEqual(Counter(names), Counter(name.casefold() for name in ADDITION_IDS.values()))
        for entry in self.manifest["additions"]:
            with self.subTest(id=entry["id"]):
                document = self.cost[entry["id"]]
                self.assertEqual(UUID(document["id"]).version, 5)
                self.assertEqual(document["source"]["type"], "curated")
                self.assertIn(document["source"]["url"], self.proposals[entry["id"]]["sources"])
                self.assertNotIn("aliases", document)
                self.assertNotIn("reviewedDate", document)
                self.assertTrue(entry["overlapDecision"])

    def test_primary_and_supplemental_query_counts_and_exact_text(self):
        self.assertEqual(len(self.catalog), 34)
        primary, supplemental = [], []
        for entry in self.entries:
            with self.subTest(id=entry["id"]):
                refs = self.proposals[entry["id"]]["queryRefs"]
                self.assertEqual(entry["primaryQueryRef"], refs[0] if refs else None)
                self.assertEqual(entry["supplementalQueryRefs"], refs[1:])
                supplemental.extend(refs[1:])
                document = self.cost[entry["id"]]
                if refs:
                    primary.append(refs[0])
                    self.assertEqual(document["queries"]["arg"], self.catalog[refs[0]]["kql"])
                    self.assertEqual(document["automation"]["resultSemantics"], "inventory")
                    self.assertNotIn("complianceColumn", document["automation"])
                    self.assertNotRegex(document["queries"]["arg"], r"(?i)\bcompliant\b")
                    self.assertIn("Empty or truncated results do not establish compliance",
                                  document["automation"]["notes"])
                else:
                    self.assertFalse(document["queries"].get("arg", "").strip())
                    self.assertIn(document["automation"]["status"], ("manual", "candidate"))
        self.assertEqual(len(primary), 31)
        self.assertEqual(len(set(primary)), 28)
        self.assertEqual(len(supplemental), 6)
        self.assertEqual(set(supplemental), {
            "advisor-aks-autoscale", "advisor-aks-spot", "aged-snapshots",
            "ddos-unassociated", "lb-empty", "nat-unassociated",
        })
        self.assertFalse(set(primary) & set(supplemental))
        self.assertEqual(set(primary) | set(supplemental), set(self.catalog))
        self.assertEqual(set(primary), set(self.manifest["wiredPrimaryQueryRefs"]))
        self.assertEqual(set(supplemental), set(self.manifest["supplementalOnlyQueryRefs"]))
        for query in self.catalog.values():
            self.assertEqual(query["resultSemantics"], "inventory")
            self.assertEqual(query["validation"]["status"], "unvalidated")
            self.assertIs(query["validation"]["liveExecuted"], False)
            self.assertIsNone(query["validation"]["validatedAt"])
            self.assertTrue(query["requiredDataAndScopes"])
            self.assertTrue(query["caveatsAndFalsePositives"])
            self.assertTrue(set(query["sourceRefs"]) <= set(self.sources))
            self.assertNotRegex(query["kql"], r"(?i)\bcompliant\b")

    def test_expressroute_heuristics_are_replaced_not_relabelled(self):
        before = {entry["id"]: entry["before"] for entry in self.manifest["updates"]}
        self.assertEqual({
            guid for guid, document in before.items()
            if document.get("queries", {}).get("arg", "").strip()
        }, EXPRESSROUTE_IDS)
        for guid in EXPRESSROUTE_IDS:
            with self.subTest(id=guid):
                self.assertIn("compliant", before[guid]["queries"]["arg"])
                actual = self.cost[guid]
                self.assertNotEqual(actual["queries"], before[guid]["queries"])
                self.assertEqual(actual["queries"]["arg"], self.catalog["expressroute-inventory"]["kql"])
                self.assertEqual(actual["automation"]["resultSemantics"], "inventory")

    def test_measured_increase_and_classifications_match_manifest(self):
        with_arg = {
            guid for guid, document in self.cost.items()
            if document.get("queries", {}).get("arg", "").strip()
        }
        self.assertEqual(len(with_arg), 31)
        self.assertEqual(len(with_arg & UPDATE_IDS), 25)
        self.assertEqual(len(with_arg & set(ADDITION_IDS)), 6)
        statuses = Counter(self.cost[guid]["automation"]["status"] for guid in self.proposals)
        self.assertEqual(statuses, {"query_available": 31, "candidate": 14, "manual": 11})
        summary = self.manifest["summary"]
        self.assertEqual(summary, {
            "baselineCostCount": 227, "finalCostCount": 235,
            "appliedUpdates": 48, "appliedAdditions": 8, "deferredAdditions": 0,
            "baselineCostWithArg": 2, "finalCostWithArg": 31,
            "existingArgReplacements": 2, "existingRulesGainingFirstArg": 23,
            "newRulesWithArg": 6, "sourceInventoryCount": 30, "provenanceSourceCount": 30,
            "queryCatalogCount": 34, "wiredPrimaryAssignments": 31,
            "wiredUniquePrimaryQueries": 28, "supplementalQueryAssignments": 6,
            "supplementalOnlyUniqueQueries": 6, "refreshedAutomationStatusCounts": dict(statuses),
        })

    def test_schema_and_serialization_use_the_shared_contract(self):
        validate_corpus(list(self.cost.values()))
        for entry in self.entries:
            with self.subTest(id=entry["id"]):
                path = ROOT.joinpath(*PureWindowsPath(entry["corpusFile"]).parts)
                self.assertIn("Cost", path.parts)
                row = self.stage_by_path[path]
                actual = row["document"]
                self.assertEqual(actual, self.cost[entry["id"]])
                validate_recommendation(actual)
                self.assertEqual(hashlib.sha256(dump_recommendation(actual).encode()).hexdigest(),
                                 row["fileSha256"])

    def test_durable_artifacts_do_not_leak_machine_local_paths(self):
        for path in ARTIFACTS.glob("cost-*"):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"(?i)\b[a-z]:[\\/]")
                self.assertNotIn(".copilot", text)
                self.assertNotIn("Users\\", text)
