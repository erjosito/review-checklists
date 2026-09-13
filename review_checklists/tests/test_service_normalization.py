"""Catalogue, alias compatibility, scope preservation and auditable stage checks."""

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.modules import cl_services
from scripts.modules.cl_services import (
    classify_applicability, classifications_equivalent, normalize_resource_types,
    normalize_service_name, normalize_services, resource_types_for_service,
    service_catalogue, service_dictionary, services_for_resource_type,
)
from scripts.modules.cl_v1tov2 import get_resource_type_name, get_standard_service_name
from scripts.modules.cl_analyze_v2 import reco_matches_criteria
from review_checklists.filters import filter_items, services_for
from review_checklists.service_normalization import (
    normalized_document, protected_hash, replay_normalization, rewrite_fields, sha256,
)
from review_checklists.tests.service_stage import (
    ROOT, normalization_report, stage_file_bytes,
)
from review_checklists.tests.followup_stage import (
    pre_followup_bytes, pre_followup_catalogue, pre_followup_document, pre_followup_paths,
)


class ServiceCatalogueTests(unittest.TestCase):
    def test_all_catalogue_aliases_and_legacy_consumers(self):
        entries = service_dictionary()
        for entry in entries:
            for alias in [entry["service"], entry["displayName"]] + entry["names"]:
                if "/" not in alias:
                    self.assertEqual(normalize_service_name(alias.swapcase()), entry["displayName"])
            # Additive fields must not affect either legacy adapter's first-match contract.
            legacy = [{k: v for k, v in e.items() if k in {"service", "arm", "names"}} for e in entries]
            for alias in entry["names"]:
                self.assertEqual(get_standard_service_name(alias, entries),
                                 get_standard_service_name(alias, legacy))
                self.assertEqual(get_resource_type_name(alias, entries),
                                 get_resource_type_name(alias, legacy))

    def test_normalization_is_cosmetic_only(self):
        self.assertEqual(normalize_services([" AKS ", "aks", "Azure Kubernetes Service"]),
                         ["Azure Kubernetes Service"])
        self.assertEqual(normalize_resource_types([" Microsoft.Web/sites ", "microsoft.web/SITES"]),
                         ["microsoft.web/sites"])
        self.assertEqual(normalize_service_name("Unknown Product"), "Unknown Product")
        self.assertEqual(normalize_services([]), [])
        self.assertTrue(classifications_equivalent(
            {"services": ["AKS"], "resourceTypes": ["Microsoft.Web/Sites"]},
            {"services": ["Azure Kubernetes Service"], "resourceTypes": ["microsoft.web/sites"]},
        ))
        self.assertFalse(classifications_equivalent({}, {"services": []}))
        self.assertFalse(classifications_equivalent(
            {"services": ["AKS"]}, {"services": ["Azure App Service"]},
        ))

    def test_ambiguous_types_never_infer_specific_services(self):
        for resource_type in ("Microsoft.Web/sites", "Microsoft.Storage/storageAccounts",
                              "Microsoft.Network/virtualNetworkGateways"):
            self.assertGreater(len(services_for_resource_type(resource_type)), 1)
            self.assertEqual(services_for({"resourceTypes": [resource_type]}), [resource_type.lower()])
            self.assertEqual(normalize_service_name(resource_type), resource_type.lower())
        self.assertIn("microsoft.app/managedenvironments", resource_types_for_service("Container Apps"))
        self.assertIn("microsoft.app/containerapps", resource_types_for_service("Container Apps"))
        self.assertEqual(len(service_catalogue()), len({e["displayName"] for e in service_dictionary()}))

    def test_raw_type_filters_do_not_convert_to_a_service(self):
        items = [
            {"id": "functions", "recommendation": {"services": ["Functions"], "resourceTypes": ["Microsoft.Web/sites"]}},
            {"id": "app", "recommendation": {"services": ["App Service"], "resourceTypes": ["Microsoft.Web/serverFarms"]}},
            {"id": "unclassified", "recommendation": {"services": [], "resourceTypes": ["Microsoft.Web/sites"]}},
        ]
        self.assertEqual({i["id"] for i in filter_items(items, service="Microsoft.Web/sites")},
                         {"functions", "unclassified"})
        self.assertEqual({i["id"] for i in filter_items(items, service="Functions")},
                         {"functions", "unclassified"})

    def test_many_to_many_cross_cutting_and_contradictions(self):
        self.assertEqual(classify_applicability({
            "services": ["Azure Advisor", "Azure Virtual Machines"],
            "resourceTypes": ["Microsoft.Compute/virtualMachines", "Microsoft.Compute/disks"],
        })["possibleContradictions"], [])
        self.assertEqual(classify_applicability({
            "services": ["AKS"], "resourceTypes": ["Microsoft.Storage/storageAccounts"],
        })["possibleContradictions"], ["Azure Kubernetes Service"])
        unknown = classify_applicability({"services": ["Uncatalogued"], "resourceTypes": ["Microsoft.X/widgets"]})
        self.assertEqual(unknown["unknownServices"], ["Uncatalogued"])
        self.assertEqual(unknown["unknownResourceTypes"], ["microsoft.x/widgets"])
        self.assertEqual(classify_applicability({})["missingFields"], ["services", "resourceTypes"])

    def test_optional_waf_host_capability_is_not_inferred_from_the_host_type(self):
        for resource_type, product in (
            ("microsoft.network/applicationgateways", "Application Gateway"),
            ("microsoft.network/frontdoors", "Azure Front Door"),
        ):
            self.assertIn(resource_type, resource_types_for_service("WAF"))
            self.assertEqual(services_for_resource_type(resource_type), [product])
            self.assertEqual(classify_applicability({
                "services": ["WAF", product], "resourceTypes": [resource_type],
            })["possibleContradictions"], [])
        self.assertNotIn("Web Application Firewall", services_for_resource_type("microsoft.cdn/profiles"))
        self.assertEqual(services_for_resource_type("microsoft.network/frontdoorwebapplicationfirewallpolicies"),
                         ["Web Application Firewall"])

    def test_legacy_and_modern_data_factory_types_remain_distinct(self):
        for resource_type in ("microsoft.datafactory/datafactories", "microsoft.datafactory/factories"):
            self.assertEqual(services_for_resource_type(resource_type), ["Data Factory"])
        self.assertFalse(classifications_equivalent(
            {"resourceTypes": ["Microsoft.DataFactory/datafactories"]},
            {"resourceTypes": ["Microsoft.DataFactory/factories"]},
        ))

    def test_checklist_service_selectors_accept_aliases_without_type_inference(self):
        for alias, display in (("WAF", "Web Application Firewall"), ("ADF", "Data Factory"),
                               ("AppGW", "Application Gateway"), ("Databricks", "Azure Databricks")):
            with self.subTest(alias=alias):
                self.assertTrue(reco_matches_criteria({"services": [display]}, services=[alias]))
                self.assertTrue(reco_matches_criteria({"services": [alias]}, services=[display]))
        self.assertFalse(reco_matches_criteria({
            "services": [], "resourceTypes": ["microsoft.network/applicationgateways"],
        }, services=["WAF"]))
        self.assertTrue(reco_matches_criteria({"services": []}, services=["none"]))

    def test_inferred_capability_types_must_be_a_unique_applicability_subset(self):
        entry = {
            "service": "Example", "displayName": "Example", "names": ["Example"],
            "resourceTypes": ["microsoft.test/hosts"],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue.json"
            with patch.object(cl_services, "CATALOG_PATH", path):
                for invalid in (["microsoft.test/other"], ["microsoft.test/hosts"] * 2, "not a list"):
                    path.write_text(json.dumps([dict(entry, inferredResourceTypes=invalid)]), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "unique subset"):
                        cl_services.service_dictionary.__wrapped__()
                path.write_text(json.dumps([dict(entry, inferredResourceTypes=[])]), encoding="utf-8")
                self.assertEqual(cl_services.service_dictionary.__wrapped__()[0]["inferredResourceTypes"], [])

    def test_byte_rewrite_changes_only_classification_blocks(self):
        before = {"id": "example", "services": ["AKS"], "resourceTypes": ["Microsoft.Web/sites"],
                  "queries": {"arg": "Resources\n| where type == 'Microsoft.Web/sites'\n"}}
        raw = (b"id: example\r\nservices: [AKS]\r\nresourceTypes:\r\n- Microsoft.Web/sites\r\n"
               b"queries:\r\n  arg: |\r\n    Resources\r\n    | where type == 'Microsoft.Web/sites'\r\n")
        after = normalized_document(before)
        changed, edits = rewrite_fields(raw, before, after)
        self.assertEqual(protected_hash(before), protected_hash(after))
        self.assertEqual(raw[raw.index(b"queries:"):], changed[changed.index(b"queries:"):])
        self.assertEqual({e["field"] for e in edits}, {"services", "resourceTypes"})


class ServiceCorpusTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(pre_followup_catalogue())

    def test_every_canonical_classification_and_complete_report(self):
        report = normalization_report()
        self.assertEqual(sha256(pre_followup_bytes(ROOT / "scripts" / "service_dictionary.json")),
                         report["catalogueSha256"])
        records = {r["id"]: r for r in report["records"]}
        classifications = {r["id"]: r for r in report["classifications"]}
        inventory = {r["id"]: r for r in report["corpusBefore"]}
        counts = Counter()
        for path in pre_followup_paths():
            actual = pre_followup_document(path)
            identifier = actual["id"]
            counts["canonical"] += 1
            counts["aliases"] += len(actual.get("aliases", []))
            self.assertEqual(actual, normalized_document(actual), identifier)
            result = classify_applicability(actual)
            self.assertEqual(result, {k: v for k, v in classifications[identifier].items()
                                      if k not in {"id", "path"}}, identifier)
            self.assertEqual(result["unknownServices"], [], identifier)
            self.assertEqual(result["missingFields"], [], identifier)
            self.assertEqual(result["possibleContradictions"], [], identifier)
            original = stage_file_bytes(path)
            self.assertEqual(sha256(original), inventory[identifier]["sha256"])
            if identifier in records:
                restored = replay_normalization(actual, report, reverse=True)
                self.assertEqual(protected_hash(restored), protected_hash(actual))
                self.assertEqual(replay_normalization(restored, report), actual)
                self.assertEqual(restored.get("queries"), actual.get("queries"))
                self.assertTrue(classifications_equivalent(restored, actual))
            counts[result["classification"]] += 1
            counts["unknownResourceTypes"] += bool(result["unknownResourceTypes"])
            counts["ambiguousResourceTypes"] += bool(result["ambiguousResourceTypes"])
        for key, count in counts.items():
            self.assertEqual(count, report["summary"][key], key)
        self.assertEqual(set(classifications), set(inventory))
        self.assertEqual(report["summary"]["changed"], len(records))


if __name__ == "__main__":
    unittest.main()
