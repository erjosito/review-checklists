from collections import Counter
import json
from pathlib import Path
import unittest

from review_checklists.corpus_admin import DEFAULT_REPORTS, maintenance_history
from review_checklists.tests.followup_stage import corpus_documents, pre_followup_files


ROOT = Path(__file__).resolve().parents[2]
REPORTS = DEFAULT_REPORTS / "full-refresh-2026-09-11"


class FullRefreshIntegrationTests(unittest.TestCase):
    def test_frozen_slices_partition_original_corpus_and_account_for_all_additions(self):
        specifications = (
            ("cost-refresh-manifest.json", "records", "contentOutcome", 226, 0),
            ("security-manifest.json", "records", "outcome", 565, 0),
            ("reliability-manifest.json", "entries", "outcome", 427, 1),
            ("performance-manifest.json", "records", "outcome", 175, 3),
            ("operations-manifest.json", "records", "outcome", 279, 2),
            ("aprl-review.json", "records", "status", 333, 0),
        )
        baseline_ids, added_ids, outcomes = set(), set(), Counter()
        for filename, records_key, status_key, baseline_count, addition_count in specifications:
            with self.subTest(filename=filename):
                report = json.loads((REPORTS / filename).read_text(encoding="utf-8"))
                records = report[records_key]
                identities = {record["id"] for record in records}
                self.assertEqual(len(records), baseline_count)
                self.assertEqual(len(identities), baseline_count)
                self.assertFalse(baseline_ids.intersection(identities))
                baseline_ids.update(identities)
                additions = {record["id"] for record in report.get("additions", [])}
                self.assertEqual(len(additions), addition_count)
                self.assertFalse(added_ids.intersection(additions))
                added_ids.update(additions)
                for record in records:
                    outcomes[record[status_key].replace("_", "")] += 1
        self.assertEqual(len(baseline_ids), 2005)
        self.assertEqual(len(added_ids), 6)
        self.assertFalse(baseline_ids.intersection(added_ids))
        self.assertEqual(outcomes, {
            "updated": 329, "supportedunchanged": 320, "needsmanualreview": 1356,
        })
        corpus = corpus_documents(pre_followup_files())
        self.assertEqual({record["id"] for record in corpus}, baseline_ids | added_ids)
        self.assertEqual(sum(len(record.get("aliases", [])) for record in corpus), 55)
        self.assertEqual(Counter(record.get("waf", "Unclassified") for record in corpus), {
            "Cost": 229, "Security": 608, "Reliability": 573, "Performance": 238,
            "Operations": 362, "Unclassified": 1,
        })

    def test_all_six_slice_events_are_displayed_without_duplicate_accounting(self):
        history = maintenance_history(DEFAULT_REPORTS)
        self.assertEqual(history["errors"], [])
        events = [event for event in history["events"]
                  if event["filename"].startswith("full-refresh-2026-09-11-")]
        self.assertEqual(len(events), 6)
        self.assertEqual(sum(event["summary"].get(
            "baselineRecordsAccountedFor", event["summary"].get("baselineRecordsAssessed", 0),
        ) for event in events), 2005)
        self.assertEqual(sum(event["summary"]["appliedAdditions"] for event in events), 6)
