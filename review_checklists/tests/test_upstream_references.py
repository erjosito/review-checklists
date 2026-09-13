from copy import deepcopy
import unittest

from review_checklists.tests.test_prototype import RECO
from scripts.modules.cl_corpus import CorpusError, enrich_recommendation, validate_recommendation


class UpstreamReferenceTests(unittest.TestCase):
    def setUp(self):
        self.reco = enrich_recommendation(deepcopy(RECO))
        self.reference = {
            "sourceId": "example-source", "recommendationId": "UP-01",
            "url": "https://example.org/recommendations/UP-01",
            "coverage": "full", "assessedAt": "2026-09-11",
            "upstreamContentHash": "sha256:" + "a" * 64,
            "notes": "The requirement and applicability are represented by this check.",
        }

    def test_optional_multiple_sources_preserve_original_origin(self):
        original = deepcopy(self.reco["source"])
        validate_recommendation(self.reco)
        self.reco["provenance"]["upstreamRecommendations"] = [
            self.reference, dict(self.reference, sourceId="another-source"),
        ]
        validate_recommendation(self.reco)
        self.assertEqual(self.reco["source"], original)
        self.assertIsNone(self.reco["provenance"]["lastReviewed"])

    def test_coverage_requires_versioned_evidence_and_explicit_assessment(self):
        for field in ("sourceId", "recommendationId", "url", "coverage", "assessedAt",
                      "upstreamContentHash", "notes"):
            with self.subTest(field=field):
                reference = dict(self.reference)
                del reference[field]
                self.reco["provenance"]["upstreamRecommendations"] = [reference]
                with self.assertRaises(CorpusError):
                    validate_recommendation(self.reco)
        supporting = dict(self.reference, coverage="supporting")
        del supporting["upstreamContentHash"]
        self.reco["provenance"]["upstreamRecommendations"] = [supporting]
        validate_recommendation(self.reco)

    def test_duplicate_or_invalid_mappings_are_rejected(self):
        self.reco["provenance"]["upstreamRecommendations"] = [self.reference, self.reference]
        with self.assertRaisesRegex(CorpusError, "Duplicate upstream"):
            validate_recommendation(self.reco)
        for change in ({"coverage": "automatic"}, {"assessedAt": "yesterday"},
                       {"upstreamContentHash": "not-a-hash"}, {"notes": " "},
                       {"recommendationId": ""}):
            with self.subTest(change=change):
                self.reco["provenance"]["upstreamRecommendations"] = [dict(self.reference, **change)]
                with self.assertRaises(CorpusError):
                    validate_recommendation(self.reco)
