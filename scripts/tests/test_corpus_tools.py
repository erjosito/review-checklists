from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts.modules import cl_analyze_v2, cl_v1tov2, cl_v2tov1
from scripts.modules.cl_corpus import (
    CorpusError, enrich_recommendation, load_yaml_document, validate_corpus,
)
from scripts.validate_corpus import validate_recommendation_folder


ROOT = Path(__file__).resolve().parents[2]
GUID = '11111111-1111-4111-8111-111111111111'
OLD_GUID = '22222222-2222-4222-8222-222222222222'
OTHER_GUID = '33333333-3333-4333-8333-333333333333'


def recommendation(guid=GUID, name='test-recommendation'):
    return enrich_recommendation({
        'name': name, 'title': 'Keep this exact recommendation',
        'description': 'A description with trailing spaces  \n\n',
        'labels': {'guid': guid}, 'source': {'type': 'revcl', 'file': 'original.json'},
        'resourceTypes': [], 'severity': 1, 'links': [],
        'queries': {'arg': 'resources\n| project id  \n\n'},
    })


class CorpusToolsTests(unittest.TestCase):
    def test_alias_selectors_and_exclusions(self):
        reco = recommendation()
        reco['aliases'] = [{'id': OLD_GUID, 'name': 'old-recommendation'}]
        validate_corpus([reco])
        self.assertTrue(cl_analyze_v2.reco_matches_criteria(reco, guids=[OLD_GUID.upper()]))
        self.assertTrue(cl_analyze_v2.reco_matches_criteria(reco, names=['OLD-RECOMMENDATION']))
        self.assertEqual(cl_analyze_v2.get_reco_name_from_guid([reco], OLD_GUID), reco['name'])
        include = cl_analyze_v2.get_object_selectors({'nameSelector': [reco['name'], 'old-recommendation']})
        exclude = cl_analyze_v2.get_object_selectors({'nameSelector': ['old-recommendation']})
        self.assertEqual(cl_analyze_v2.filter_v2_recos([reco], include), [reco])
        self.assertEqual(cl_analyze_v2.filter_v2_recos([reco], include, exclude), [])

    def test_empty_services_remain_unclassified(self):
        reco = recommendation()
        self.assertTrue(cl_analyze_v2.reco_matches_criteria(reco, services=['none']))
        include = cl_analyze_v2.get_object_selectors({'serviceSelector': ['none']})
        self.assertEqual(cl_analyze_v2.filter_v2_recos([reco], include), [reco])
        self.assertEqual(cl_analyze_v2.v2_stats_from_object([reco])['services'], {'undefined': 1})
        self.assertNotIn('service', cl_v2tov1.get_v1_from_v2(reco))
        reco['services'] = ['Explicit Service']
        self.assertFalse(cl_analyze_v2.reco_matches_criteria(reco, services=['none']))
        self.assertEqual(cl_v2tov1.get_v1_from_v2(reco)['service'], 'Explicit Service')
        self.assertEqual(cl_v2tov1.get_v1_from_v2(reco)['guid'], GUID)

    def test_alias_source_and_guid_label_selectors_preserve_membership(self):
        reco = recommendation()
        reco['aliases'] = [{
            'id': OLD_GUID, 'name': 'old-aprl-recommendation',
            'source': {'type': 'aprl', 'file': 'upstream.yaml'},
        }]
        validate_corpus([reco])
        for source in ('revcl', 'APRL'):
            with self.subTest(source=source):
                self.assertTrue(cl_analyze_v2.reco_matches_criteria(reco, sources=[source]))
        self.assertFalse(cl_analyze_v2.reco_matches_criteria(reco, sources=['wafsg']))
        self.assertFalse(cl_analyze_v2.reco_matches_criteria(reco, sources=['none']))
        for guid in (GUID, OLD_GUID.upper()):
            self.assertTrue(cl_analyze_v2.reco_matches_criteria(reco, labels={'guid': guid}))
        self.assertFalse(cl_analyze_v2.reco_matches_criteria(reco, labels={'guid': OTHER_GUID}))
        include = cl_analyze_v2.get_object_selectors({
            'labelSelector': {'guid': OLD_GUID}, 'sourceSelector': ['aprl'],
            'serviceSelector': ['none'],
        })
        self.assertEqual(cl_analyze_v2.filter_v2_recos([reco], include), [reco])
        exclude = cl_analyze_v2.get_object_selectors({'sourceSelector': ['aprl']})
        self.assertEqual(cl_analyze_v2.filter_v2_recos([reco], include, exclude), [])
        exclude = cl_analyze_v2.get_object_selectors({'labelSelector': {'guid': OLD_GUID}})
        self.assertEqual(cl_analyze_v2.filter_v2_recos([reco], include, exclude), [])
        reco['services'] = ['Explicit Service']
        self.assertEqual(cl_analyze_v2.filter_v2_recos([reco], include), [])

    def test_alias_without_source_does_not_invent_source_membership(self):
        reco = recommendation()
        reco['aliases'] = [{'id': OLD_GUID, 'name': 'old-recommendation'}]
        self.assertEqual(cl_analyze_v2.recommendation_sources(reco), {'revcl'})
        self.assertFalse(cl_analyze_v2.reco_matches_criteria(reco, sources=['aprl']))
        del reco['source']
        self.assertTrue(cl_analyze_v2.reco_matches_criteria(reco, sources=['none']))

    def test_writer_preserves_content_and_removes_transient_paths(self):
        reco = recommendation()
        reco['filepath'] = 'transient'
        reco['corpus_file'] = 'transient'
        original = deepcopy(reco)
        with tempfile.TemporaryDirectory() as directory:
            cl_v1tov2.store_v2(directory, [reco])
            path, = Path(directory).rglob('*.yaml')
            stored = load_yaml_document(path)
            self.assertEqual(stored, enrich_recommendation(original))
            self.assertEqual(stored['queries'], original['queries'])
            self.assertEqual(stored['description'], original['description'])
            self.assertEqual(reco, original)
            self.assertEqual(validate_recommendation_folder(directory), 1)

    def test_invalid_batch_leaves_existing_files_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            reco = recommendation()
            cl_v1tov2.store_v2(directory, [reco])
            path, = Path(directory).rglob('*.yaml')
            before = path.read_bytes()
            changed = deepcopy(reco)
            changed['title'] = 'An explicitly changed title'
            invalid = recommendation(OTHER_GUID, 'invalid-recommendation')
            invalid['id'] = GUID
            with self.assertRaises(CorpusError):
                cl_v1tov2.store_v2(directory, [changed, invalid], overwrite=True)
            self.assertEqual(path.read_bytes(), before)

    def test_failed_replace_preserves_original_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            reco = recommendation()
            cl_v1tov2.store_v2(directory, [reco])
            path, = Path(directory).rglob('*.yaml')
            before = path.read_bytes()
            reco['title'] = 'An explicitly changed title'
            with patch.object(cl_v1tov2.os, 'replace', side_effect=OSError('write failed')):
                with self.assertRaisesRegex(OSError, 'write failed'):
                    cl_v1tov2.store_v2(directory, [reco], overwrite=True)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(list(Path(directory).rglob('*.tmp')))

    def test_retired_identity_cannot_be_reimported(self):
        with tempfile.TemporaryDirectory() as directory:
            survivor = recommendation()
            survivor['aliases'] = [{'id': OLD_GUID, 'name': 'old-recommendation'}]
            cl_v1tov2.store_v2(directory, [survivor])
            with self.assertRaises(CorpusError):
                cl_v1tov2.store_v2(directory, [recommendation(OLD_GUID, 'reimported-recommendation')])
            without_aliases = recommendation()
            with self.assertRaisesRegex(CorpusError, 'curated aliases'):
                cl_v1tov2.store_v2(directory, [without_aliases], overwrite=True)

    def test_optional_alias_provenance_survives_write_and_lookup(self):
        reco = recommendation()
        alias = {
            'id': OLD_GUID, 'name': 'old-recommendation',
            'source': {'type': 'revcl', 'file': 'old-source.json'},
            'corpusFile': 'Practices/Cost/old-recommendation.yaml',
        }
        reco['aliases'] = [alias]
        with tempfile.TemporaryDirectory() as directory:
            cl_v1tov2.store_v2(directory, [reco])
            survivor, = cl_analyze_v2.get_reco_from_guid(directory, OLD_GUID)
            self.assertEqual(survivor['id'], GUID)
            self.assertEqual(survivor['aliases'], [alias])
            survivor['title'] = 'A human-reviewed title change'
            cl_v1tov2.store_v2(directory, [survivor], overwrite=True)
            survivor, = cl_analyze_v2.get_reco_from_name(directory, alias['name'])
            self.assertEqual(survivor['aliases'], [alias])
            self.assertEqual(validate_recommendation_folder(directory), 1)

    def test_strict_gate_requires_metadata_that_enrichment_supplies(self):
        for section, field in (
            ('automation', 'validatedAt'), ('automation', 'status'),
            ('provenance', 'upstreamRevision'), ('provenance', 'lastReviewed'),
            ('provenance', 'sources'),
        ):
            with self.subTest(section=section, field=field):
                reco = recommendation()
                del reco[section][field]
                with self.assertRaises(CorpusError):
                    validate_corpus([reco])
                enriched = enrich_recommendation(reco)
                validate_corpus([enriched])
                self.assertNotIn(field, reco[section])

    def test_manual_generator_enriches_without_guessing_meaning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text(json.dumps({'items': [{
                'guid': GUID, 'text': 'Keep source recommendation text',
                'graph': 'resources\n| project id  \n\n',
                'severity': 'Medium', 'description': 'Preserve description  \n',
            }]}), encoding='utf-8')
            generated = cl_v1tov2.generate_v2(str(path))
            validate_corpus(generated)
            reco, = generated
            self.assertEqual(reco['id'], GUID)
            self.assertEqual(reco['labels']['guid'], GUID)
            self.assertEqual(reco['services'], [])
            self.assertEqual(reco['automation']['resultSemantics'], 'unknown')
            self.assertIsNone(reco['automation']['validatedAt'])
            self.assertIsNone(reco['provenance']['lastReviewed'])
            self.assertEqual(reco['queries']['arg'], 'resources\n| project id  \n\n')

    def test_load_aliases_and_reject_duplicate_yaml_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            reco = recommendation()
            reco['aliases'] = [{'id': OLD_GUID, 'name': 'old-recommendation'}]
            path = Path(directory) / 'reco.yaml'
            path.write_text(yaml.safe_dump(reco), encoding='utf-8')
            self.assertEqual(cl_analyze_v2.get_reco_from_guid(directory, OLD_GUID)[0]['id'], GUID)
            self.assertEqual(cl_analyze_v2.get_reco_from_name(directory, 'old-recommendation')[0]['id'], GUID)
            path.write_text('name: first\nname: second\n', encoding='utf-8')
            with self.assertRaises(CorpusError):
                cl_analyze_v2.load_v2_files(directory)

    def test_readonly_json_reader_still_accepts_legacy_recommendations(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = {'name': 'legacy-recommendation', 'labels': {'guid': GUID}}
            (Path(directory) / 'legacy.json').write_text(json.dumps(legacy), encoding='utf-8')
            self.assertEqual(cl_analyze_v2.load_v2_files(directory, format='json'), [legacy])

    def test_strict_gate_and_both_cli_invocations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reco.yaml'
            path.write_text(yaml.safe_dump(recommendation()), encoding='utf-8')
            for command in ([sys.executable, '-m', 'scripts.cl'],
                            [sys.executable, str(ROOT / 'scripts' / 'cl.py')]):
                with self.subTest(command=command):
                    result = subprocess.run(command + ['validate-recos', '--input-folder', directory],
                                            cwd=ROOT, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            invalid = recommendation()
            del invalid['schemaVersion']
            path.write_text(yaml.safe_dump(invalid), encoding='utf-8')
            with self.assertRaises(CorpusError):
                validate_recommendation_folder(directory)
            result = subprocess.run(
                [sys.executable, '-m', 'scripts.cl', 'validate-recos', '--input-folder', directory],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_legacy_v1_readonly_command_and_deprecated_review_stamping(self):
        result = subprocess.run(
            [sys.executable, '-m', 'scripts.cl', 'analyze-v1', '--help'],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(
            [sys.executable, '-m', 'scripts.cl', 'update-recos', '--reviewed'],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Bulk review-date stamping', result.stderr)

    def test_upstream_import_workflows_are_manual_only(self):
        for name in ('get_aprl.yml', 'get_theakschecklist.yml', 'get_waf_sg.yml'):
            with self.subTest(workflow=name):
                workflow = yaml.load(
                    (ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8'),
                    Loader=yaml.BaseLoader,
                )
                self.assertEqual(set(workflow['on']), {'workflow_dispatch'})


if __name__ == '__main__':
    unittest.main()
