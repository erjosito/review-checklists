from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.modules.cl_corpus import CorpusError, dump_recommendation, enrich_recommendation
from review_checklists.catalog import content_hash
from review_checklists.corpus import load_corpus
from review_checklists.merge import merge_confirmed, read_merge_manifest


IDS = [f"00000000-0000-4000-8000-{number:012d}" for number in range(1, 6)]


class CorpusMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "recos"
        self.root.mkdir()
        self.records = []
        for index in range(2):
            self.records.append(enrich_recommendation({
                "name": f"test-Recommendation-{index}", "title": "Enable the same monitoring control",
                "severity": 1, "waf": "Operations",
                "source": {"type": "revcl", "file": f"source-{index}.json"},
                "resourceTypes": ["Microsoft.Test/resources"], "labels": {"guid": IDS[index]},
                "queries": {}, "description": "Keep the monitoring evidence.",
            }))
        self.group = {"canonicalId": IDS[0], "retiredIds": [IDS[1]], "reason": "Confirmed same requirement"}
        self.write_records()

    def write_records(self):
        for index, reco in enumerate(self.records):
            (self.root / f"{index}.yaml").write_text(
                "# Original comment\n" + dump_recommendation(reco), encoding="utf-8",
            )

    def bytes(self):
        return {path.name: path.read_bytes() for path in self.root.iterdir()}

    def assert_rejected_without_writes(self, groups, pattern=None):
        before = self.bytes()
        with self.assertRaisesRegex(CorpusError, pattern or "."):
            merge_confirmed(self.root, groups, write=True)
        self.assertEqual(self.bytes(), before)

    def test_bad_group_shapes(self):
        for groups in [None, {}, "groups", [], [None], [[]], ["x"], [1], [True]]:
            with self.subTest(groups=groups):
                self.assert_rejected_without_writes(groups)

    def test_bad_group_fields(self):
        cases = [
            {"canonicalId": []}, {"canonicalId": None}, {"canonicalId": ""},
            {"retiredIds": IDS[1]}, {"retiredIds": []}, {"retiredIds": [None]},
            {"retiredIds": [""]}, {"retiredIds": [IDS[1], IDS[1]]},
            {"reason": ""}, {"reason": True}, {"description": []},
            {"beforeContentHash": 1}, {"beforeContentHash": "sha256:" + "z" * 64},
            {"unapproved": True},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assert_rejected_without_writes([dict(self.group, **changes)])

    def test_unknown_self_and_overlapping_identities(self):
        for groups in [
            [dict(self.group, canonicalId=IDS[4])],
            [dict(self.group, retiredIds=[IDS[0]])],
            [self.group, self.group],
        ]:
            with self.subTest(groups=groups):
                self.assert_rejected_without_writes(groups)

    def test_strict_manifest_parser(self):
        manifest = self.base / "manifest.json"
        for text in [
            "null", "[]", "{}", '{"groups":[]}',
            '{"groups":[],"groups":[]}', '{"groups":[NaN]}',
            '{"groups":[],"extra":1}', '{"groups":[{"reason":"x","reason":"y"}]}', "{",
        ]:
            with self.subTest(text=text):
                manifest.write_text(text, encoding="utf-8")
                with self.assertRaises(CorpusError):
                    read_merge_manifest(manifest)
        manifest.write_text(json.dumps({"groups": [self.group]}), encoding="utf-8")
        self.assertEqual(read_merge_manifest(manifest), [self.group])
        with self.assertRaises(CorpusError):
            read_merge_manifest(self.base / "missing.json")

    def test_cli_dispatch_uses_strict_manifest_and_defaults_to_dry_run(self):
        from review_checklists.__main__ import main
        path = self.base / "manifest.json"
        arguments = ["corpus", "merge", "--corpus", str(self.root), "--manifest", str(path)]
        before = self.bytes()
        path.write_text(json.dumps({"groups": [self.group]}), encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            self.assertEqual(main(arguments), 0)
        self.assertEqual(json.loads(output.getvalue())["mode"], "dry-run")
        self.assertEqual(self.bytes(), before)
        path.write_text(json.dumps({"groups": [self.group], "ignored": True}), encoding="utf-8")
        error = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(error):
            self.assertEqual(main(arguments), 1)
        self.assertIn("only a groups array", error.getvalue())
        self.assertEqual(self.bytes(), before)

    def test_scope_differences_are_deferred(self):
        original = deepcopy(self.records[1])
        differences = [
            {"waf": "Security"}, {"severity": 0}, {"services": ["other"]},
            {"resourceTypes": []},
            {"constraints": [{"field": "region", "operator": "equals", "value": "west", "effect": "show"}]},
            {"labels": {"guid": IDS[1], "area": "Other area"}},
            {"source": {"type": "wafsg", "file": "other.json"}},
        ]
        for changes in differences:
            with self.subTest(changes=changes):
                self.records[1] = dict(deepcopy(original), **changes)
                self.write_records()
                self.assert_rejected_without_writes([self.group], "applicability")

    def test_equal_constraints_and_resource_casing_are_allowed(self):
        constraint = [{"field": "sku", "operator": "equals", "value": "v2", "effect": "show"}]
        for reco in self.records:
            reco["constraints"] = constraint
        self.records[1]["resourceTypes"] = ["microsoft.test/resources"]
        self.write_records()
        self.assertEqual(merge_confirmed(self.root, [self.group])["retired"], 1)

    def test_conflicting_automation_and_legacy_metadata_are_deferred(self):
        original = deepcopy(self.records[1])
        for changes in [
            {"automation": {"status": "manual", "validatedAt": None}},
            {"automation": {"status": "unknown", "validatedAt": None, "notes": "Different evidence"}},
            {"automatable": False}, {"reviewedDate": "2026-09-01"},
            {"duplicates": [IDS[4]]},
        ]:
            with self.subTest(changes=changes):
                self.records[1] = dict(deepcopy(original), **changes)
                self.write_records()
                self.assert_rejected_without_writes([self.group], "conflicting")

    def test_different_queries_and_query_donation_are_rejected(self):
        self.records[1]["queries"] = {"arg": "resources | project id"}
        self.records[1]["automation"] = {
            "status": "query_available", "validatedAt": None, "resultSemantics": "unknown",
        }
        self.write_records()
        self.assert_rejected_without_writes([self.group], "queries")
        self.records[0]["automation"] = deepcopy(self.records[1]["automation"])
        self.records[0]["queries"] = {"arg": "resources | project name"}
        self.write_records()
        self.assert_rejected_without_writes([self.group], "queries")

    def test_query_bytes_and_validation_metadata_are_preserved(self):
        query = "// Exact query text\nresources\n| project id\n\n"
        automation = {
            "status": "query_available", "validatedAt": "2026-09-01",
            "resultSemantics": "inventory", "notes": "Offline fixture",
        }
        for reco in self.records:
            reco["queries"] = {"arg": query}
            reco["automation"] = deepcopy(automation)
        self.write_records()
        merge_confirmed(self.root, [self.group], write=True)
        merged = load_corpus(self.root, require_current=True)[0]
        self.assertEqual(merged["queries"]["arg"], query)
        self.assertEqual(merged["automation"], automation)

    def test_provenance_scalar_and_same_url_conflicts_are_deferred(self):
        original = deepcopy(self.records[1]["provenance"])
        for changes in [{"upstreamRevision": "different"}, {"lastReviewed": "2026-09-01"}]:
            self.records[1]["provenance"] = dict(original, **changes)
            self.write_records()
            self.assert_rejected_without_writes([self.group], "provenance")
        self.records[1]["provenance"] = original
        for index, reco in enumerate(self.records):
            reco["provenance"]["sources"] = [{"url": "https://example.com/source", "revision": str(index)}]
        self.write_records()
        self.assert_rejected_without_writes([self.group], "conflicting provenance")

    def test_compatible_sources_links_and_aliases_are_preserved(self):
        self.records[1]["aliases"] = [{"id": IDS[2], "name": "older-Recommendation"}]
        for index, reco in enumerate(self.records):
            reco["links"] = [{"type": "docs", "url": f"https://example.com/{index}"}]
            reco["provenance"]["sources"] = [{"url": f"https://example.com/source-{index}"}]
        self.write_records()
        before = self.bytes()
        dry = merge_confirmed(self.root, [self.group])
        self.assertEqual(self.bytes(), before)
        actual = merge_confirmed(self.root, [self.group], write=True)
        self.assertEqual(actual["groups"], dry["groups"])
        merged = load_corpus(self.root, require_current=True)[0]
        self.assertEqual([a["id"] for a in merged["aliases"]], [IDS[2], IDS[1]])
        retired = merged["aliases"][1]
        self.assertEqual(retired["source"], self.records[1]["source"])
        self.assertEqual(retired["labels"], self.records[1]["labels"])
        self.assertEqual(retired["name"], self.records[1]["name"])
        self.assertEqual(retired["corpusFile"], "1.yaml")
        self.assertEqual(len(merged["links"]), 2)
        self.assertEqual(len(merged["provenance"]["sources"]), 2)
        self.assertEqual(actual["groups"][0]["originalRecommendations"], self.records)

    def test_distinct_and_retired_only_upstream_mappings_are_preserved_once(self):
        first = {
            "sourceId": "fixture-source", "recommendationId": "CHECK-1",
            "url": "https://example.com/check-1", "coverage": "partial", "assessedAt": "2026-09-13",
            "upstreamContentHash": "sha256:" + "a" * 64, "notes": "Explicit fixture scope comparison",
        }
        second = dict(first, recommendationId="CHECK-2", url="https://example.com/check-2")
        for canonical_refs in ([], [first]):
            with self.subTest(canonical_refs=canonical_refs):
                self.records[0]["provenance"]["upstreamRecommendations"] = canonical_refs
                self.records[1]["provenance"]["upstreamRecommendations"] = [first, second]
                self.write_records()
                dry = merge_confirmed(self.root, [self.group])
                actual = merge_confirmed(self.root, [self.group], write=True)
                self.assertEqual(dry["groups"], actual["groups"])
                merged = load_corpus(self.root)[0]
                self.assertEqual(merged["provenance"]["upstreamRecommendations"], [first, second])

    def test_conflicting_same_upstream_identity_is_never_silently_selected(self):
        reference = {
            "sourceId": "fixture-source", "recommendationId": "CHECK-1",
            "url": "https://example.com/check-1", "coverage": "partial", "assessedAt": "2026-09-13",
            "upstreamContentHash": "sha256:" + "a" * 64, "notes": "Explicit fixture scope comparison",
        }
        for changes in ({"coverage": "full"}, {"notes": "A different scope"},
                        {"upstreamContentHash": "sha256:" + "b" * 64}, {"assessedAt": "2026-09-12"}):
            with self.subTest(changes=changes):
                self.records[0]["provenance"]["upstreamRecommendations"] = [reference]
                self.records[1]["provenance"]["upstreamRecommendations"] = [dict(reference, **changes)]
                self.write_records()
                self.assert_rejected_without_writes([self.group], "conflicting upstream mapping")

    def test_descriptions_require_explicit_lossless_reconciliation(self):
        self.records[1]["description"] = "Keep the additional qualifier."
        self.write_records()
        self.assert_rejected_without_writes([self.group], "reconciled description")
        self.assert_rejected_without_writes([dict(self.group, description="Replacement prose.")], "remove original")
        description = "\n\n".join(reco["description"] for reco in self.records)
        merge_confirmed(self.root, [dict(self.group, description=description)], write=True)
        self.assertEqual(load_corpus(self.root)[0]["description"], description)

    def test_unique_description_can_fill_empty_canonical(self):
        self.records[0].pop("description")
        self.write_records()
        merge_confirmed(self.root, [self.group], write=True)
        self.assertEqual(load_corpus(self.root)[0]["description"], self.records[1]["description"])

    def test_stale_approval_hash_is_rejected(self):
        self.assert_rejected_without_writes(
            [dict(self.group, beforeContentHash="sha256:" + "0" * 64)], "beforeContentHash",
        )
        approved = dict(self.group, beforeContentHash=content_hash(self.records))
        self.assertEqual(merge_confirmed(self.root, [approved])["retired"], 1)

    def test_invalid_later_group_never_writes_first_group(self):
        self.assert_rejected_without_writes(
            [self.group, dict(self.group, canonicalId=IDS[4])],
        )

    def test_alias_collision_and_invalid_final_description_are_preflighted(self):
        self.records[0]["aliases"] = [{"id": IDS[2], "name": "older-Recommendation"}]
        self.records[1]["aliases"] = [{"id": IDS[2], "name": "conflicting-Recommendation"}]
        self.write_records()
        self.assert_rejected_without_writes([self.group], "Duplicate")
        self.records[0].pop("aliases")
        self.records[1].pop("aliases")
        self.write_records()
        self.assert_rejected_without_writes(
            [dict(self.group, description=self.records[0]["description"] + "x" * 2000)],
        )

    def test_changes_during_parsing_are_detected_against_original_bytes(self):
        import review_checklists.merge as module
        real_load = module.yaml.load
        path = self.root / "0.yaml"
        original = path.read_bytes()
        calls = 0

        def mutate(*args, **kwargs):
            nonlocal calls
            calls += 1
            result = real_load(*args, **kwargs)
            if calls == 1:
                path.write_bytes(original + b"\n# Concurrent edit\n")
            return result

        with patch.object(module.yaml, "load", side_effect=mutate):
            with self.assertRaisesRegex(CorpusError, "changed during merge preflight"):
                merge_confirmed(self.root, [self.group], write=True)
        self.assertEqual(path.read_bytes(), original + b"\n# Concurrent edit\n")
        self.assertTrue((self.root / "1.yaml").exists())

    def test_staging_failure_leaves_all_originals_untouched(self):
        before = self.bytes()
        with patch("review_checklists.merge._stage", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(CorpusError, "disk full"):
                merge_confirmed(self.root, [self.group], write=True)
        self.assertEqual(self.bytes(), before)
        self.assertEqual(list(self.base.glob(".corpus-merge-*")), [])

    def test_serialization_failure_never_mutates_corpus(self):
        before = self.bytes()
        with patch("review_checklists.merge.dump_recommendation", side_effect=CorpusError("cannot serialize")):
            with self.assertRaisesRegex(CorpusError, "cannot serialize"):
                merge_confirmed(self.root, [self.group], write=True)
        self.assertEqual(self.bytes(), before)

    def test_malformed_source_and_duplicate_keys_never_write(self):
        path = self.root / "1.yaml"
        original = path.read_bytes()
        for extra in [b"\nseverity: 2\n", b"\nbad: [\n"]:
            with self.subTest(extra=extra):
                path.write_bytes(original + extra)
                self.assert_rejected_without_writes([self.group])

    def test_aliases_are_written_before_retired_files_are_removed(self):
        real_replace = os.replace
        operations = []

        def record_operation(source, destination):
            operations.append((Path(source), Path(destination)))
            return real_replace(source, destination)

        with patch("review_checklists.merge.os.replace", side_effect=record_operation):
            merge_confirmed(
                self.root, [dict(self.group, canonicalId=IDS[1], retiredIds=[IDS[0]])], write=True,
            )
        self.assertEqual(operations[0][1], self.root / "1.yaml")
        self.assertEqual(operations[1][0], self.root / "0.yaml")

    def test_mid_commit_failure_rolls_back_exact_original_bytes(self):
        before = self.bytes()
        real_replace = os.replace
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected replacement failure")
            return real_replace(source, destination)

        with patch("review_checklists.merge.os.replace", side_effect=fail_second):
            with self.assertRaisesRegex(CorpusError, "rolled back"):
                merge_confirmed(self.root, [self.group], write=True)
        self.assertEqual(self.bytes(), before)
        self.assertEqual(list(self.base.glob(".corpus-merge-*")), [])

    def test_new_file_after_staging_aborts_without_merges(self):
        import review_checklists.merge as module
        real_stage = module._stage
        added = False

        def add_file(*args):
            nonlocal added
            real_stage(*args)
            if not added:
                added = True
                extra = deepcopy(self.records[0])
                extra["id"] = extra["labels"]["guid"] = IDS[4]
                extra["name"] = "extra-Recommendation"
                (self.root / "extra.yaml").write_text(dump_recommendation(extra), encoding="utf-8")

        with patch.object(module, "_stage", side_effect=add_file):
            with self.assertRaisesRegex(CorpusError, "Corpus files changed"):
                merge_confirmed(self.root, [self.group], write=True)
        self.assertEqual(len(load_corpus(self.root)), 3)
        self.assertEqual(load_corpus(self.root)[0].get("aliases", []), [])

    def test_rollback_does_not_overwrite_concurrent_edits(self):
        real_replace = os.replace
        calls = 0
        path = self.root / "0.yaml"

        def conflict(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                path.write_bytes(path.read_bytes() + b"\n# External update\n")
                raise OSError("injected failure")
            return real_replace(source, destination)

        with patch("review_checklists.merge.os.replace", side_effect=conflict):
            with self.assertRaisesRegex(CorpusError, "Rollback incomplete.*backups retained"):
                merge_confirmed(self.root, [self.group], write=True)
        self.assertIn(b"# External update", path.read_bytes())
        backups = list(self.base.glob(".corpus-merge-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(list(backups[0].glob("*.original")))


if __name__ == "__main__":
    unittest.main()
