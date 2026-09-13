from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from review_checklists.catalog import make_bundle
from review_checklists.corpus import load_corpus, read_document, select_checklist
from review_checklists.corpus_history import read_stage
from review_checklists.refresh import apply_refresh, plan_refresh
from review_checklists.review import Review
from review_checklists.tests.followup_stage import ROOT, REPORTS, corpus_documents, pre_followup_files
from scripts.modules.cl_services import classify_applicability, normalize_resource_types, normalize_services


class FollowupRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = read_stage(REPORTS / "followup-2026-09-13-application.json")
        cls.before = {row["id"]: row for row in corpus_documents(pre_followup_files())}
        cls.current = {
            row["id"]: {k: v for k, v in row.items() if k != "corpus_file"}
            for row in load_corpus(ROOT / "v2" / "recos", require_current=True)
        }
        cls.retired = {
            alias["id"]: row["id"] for row in cls.current.values() for alias in row.get("aliases", [])
        }

    def test_exact_stage_counts_and_all_original_identities_survive(self):
        self.assertEqual(self.stage["beforeCorpus"]["contentHash"],
                         "sha256:1a9879553910a9fdb7271e507973d717dee75862726f23ea7ba9f0af858ffe58")
        self.assertEqual((len(self.before), len(self.current), len(self.retired)), (2011, 2008, 58))
        self.assertEqual(self.stage["summary"], {
            "canonicalBefore": 2011, "canonicalAfter": 2008, "aliasesBefore": 55, "aliasesAfter": 58,
            "sourceAmendments": 19, "guidanceAmendments": 18, "provenanceOnlyAmendments": 1,
            "mergeGroups": 2, "updatedRecommendationFiles": 21, "retiredRecommendationFiles": 3,
            "addedRecommendationFiles": 0, "catalogueFiles": 1,
        })
        def identities(records):
            return {item["id"]: item["name"] for row in records
                    for item in [row, *row.get("aliases", [])]}
        self.assertEqual(identities(self.before.values()), identities(self.current.values()))
        self.assertEqual(Counter(row["waf"] for row in self.current.values()), {
            "Cost": 229, "Operations": 362, "Performance": 238, "Reliability": 573, "Security": 606,
        })

    def test_source_amendments_match_proposals_and_preserve_protected_fields(self):
        key_vault = json.loads((REPORTS / "key-vault-followup-2026-09-13.json").read_text(encoding="utf-8"))
        for row in key_vault["records"]:
            self.assertEqual(self.current[row["id"]], row["after"])
        classification = json.loads((REPORTS / "classification-followup-2026-09-13.json").read_text(encoding="utf-8"))
        sources = {row["id"]: row for row in classification["sources"]}
        for row in classification["records"]:
            expected = deepcopy(self.before[row["id"]])
            if row["status"] == "proposed-semantic-amendment":
                expected.update(deepcopy(row["after"]))
                for source_id in row["sourceRefs"]:
                    reference = {k: sources[source_id][k] for k in ("url", "title", "accessedAt")}
                    if reference not in expected["provenance"]["sources"]:
                        expected["provenance"]["sources"].append(reference)
            self.assertEqual(self.current[row["id"]], expected, row["id"])
        for row in self.stage["amendments"]:
            before, after = self.before[row["id"]], self.current[row["id"]]
            for field in ("id", "name", "aliases", "labels", "source", "queries", "severity", "constraints"):
                self.assertEqual(before.get(field), after.get(field), (row["id"], field))
            for field in ("upstreamRevision", "lastReviewed"):
                self.assertEqual(before["provenance"].get(field), after["provenance"].get(field))
            self.assertEqual(before["automation"].get("validatedAt"), after["automation"].get("validatedAt"))

    def test_unrelated_guidance_and_all_query_text_are_unchanged(self):
        changed = {row["id"] for row in self.stage["amendments"]}
        changed.update(group["canonicalId"] for group in self.stage["mergeResult"]["groups"])
        for identifier, before in self.before.items():
            resolved = identifier if identifier in self.current else self.retired[identifier]
            after = self.current[resolved]
            self.assertEqual(before.get("queries"), after.get("queries"), identifier)
            if identifier == resolved and identifier not in changed:
                self.assertEqual(before, after, identifier)
        for source in self.stage["sources"]:
            self.assertEqual(hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(), source["sha256"])

    def test_aliases_preserve_sources_labels_and_all_three_legacy_selectors(self):
        for group in self.stage["mergeResult"]["groups"]:
            canonical = self.current[group["canonicalId"]]
            aliases = {row["id"]: row for row in canonical["aliases"]}
            for identifier in group["retiredIds"]:
                before = self.before[identifier]
                for field in ("id", "name", "source", "labels"):
                    self.assertEqual(aliases[identifier][field], before.get(field, {}))
                for selector in (
                    {"guidSelector": [identifier]}, {"nameSelector": [before["name"]]},
                    {"labelSelector": {"guid": identifier}},
                ):
                    matched = select_checklist(list(self.current.values()), {"include": selector})
                    self.assertEqual([row["id"] for row in matched], [canonical["id"]])

    def test_checklist_changes_are_exact_and_prior_placements_resolve(self):
        changes = {}
        for entry in self.stage["checklists"]:
            definition = read_document(ROOT / entry["path"])
            actual = {
                row["id"]: {"area": row["area"], "subarea": row["subarea"]}
                for row in select_checklist(list(self.current.values()), definition, allow_empty=True)
            }
            self.assertEqual(actual, entry["after"], entry["path"])
            for identifier, placement in entry["before"].items():
                resolved = identifier if identifier in self.current else self.retired[identifier]
                self.assertEqual(actual[resolved], placement, (entry["path"], identifier))
            changes[Path(entry["path"]).name] = (len(entry["before"]), len(actual))
        self.assertEqual(changes["app_delivery.yaml"], (38, 42))
        self.assertEqual(changes["alz.yaml"], (236, 236))
        self.assertEqual(changes["waf_sg_security.yaml"], (167, 165))
        self.assertEqual(changes["all_recos.yaml"], (2011, 2008))
        self.assertEqual(len(changes), 10)

    def test_current_classifications_are_normalized_without_unknown_type_spellings(self):
        for row in self.current.values():
            self.assertEqual(row["services"], normalize_services(row["services"]), row["id"])
            self.assertEqual(row["resourceTypes"], normalize_resource_types(row["resourceTypes"]), row["id"])
            result = classify_applicability(row)
            for field in ("unknownServices", "unknownResourceTypes", "possibleContradictions"):
                self.assertEqual(result[field], [], (row["id"], field))

    def test_explicit_review_refresh_preserves_assessments_and_retired_rows(self):
        semantic = "892ca809-e2b5-9a47-924a-71132bf6f902"
        provenance_only = "08be36ad-0190-4740-b002-9adae9be0cca"
        unchanged = "ab91932c-9fc9-4d1b-a881-37f5e6c0cb9e"
        identifiers = {semantic, provenance_only, unchanged}
        for group in self.stage["mergeResult"]["groups"]:
            identifiers.update([group["canonicalId"], *group["retiredIds"]])
        targets = {identifier if identifier in self.current else self.retired[identifier]
                   for identifier in identifiers}
        bundle = make_bundle([self.current[identifier] for identifier in sorted(targets)], "followup-fixture")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = Review.create(root / "review.sqlite3", "Isolated follow-up", [
                self.before[identifier] for identifier in sorted(identifiers)
            ], root)
            for identifier in identifiers:
                review.update(identifier, "Compliant", "Preserve notes " + identifier, 0)
            plan = plan_refresh(review, bundle)
            result = apply_refresh(review, bundle, token=plan["token"])
            self.assertTrue(result["applied"])
            self.assertEqual(len(review.items()), len(identifiers))
            for identifier in identifiers:
                row = review.get(identifier)
                self.assertEqual(row["status"], "Compliant")
                self.assertEqual(row["comments"], "Preserve notes " + identifier)
                if identifier not in self.current:
                    self.assertEqual(row["refresh_state"]["currency"], "superseded")
            self.assertTrue(review.get(semantic)["refresh_state"]["needs_reassessment"])
            self.assertFalse(review.get(provenance_only)["refresh_state"]["needs_reassessment"])
            self.assertFalse(review.get(unchanged)["refresh_state"]["needs_reassessment"])
