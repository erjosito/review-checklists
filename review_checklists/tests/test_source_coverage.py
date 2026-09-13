from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from review_checklists.source_coverage import (
    SourceCoverageError, coverage_report, diff_inventories, item_content_hash,
    resolve_recommendation_id, validate_inventory,
)
from review_checklists.source_audit import (
    PublicReader, SourceAuditError, fetch_inventory, load_registry, parse_advisor_catalog,
    parse_json, parse_records, parse_waf_checklist, parse_yaml, save_inventory,
)


ID = '11111111-1111-4111-8111-111111111111'
ALIAS = '22222222-2222-4222-8222-222222222222'
OTHER = '33333333-3333-4333-8333-333333333333'
URL = 'https://learn.microsoft.com/en-us/azure/well-architected/security/checklist'
ROOT = Path(__file__).resolve().parents[2]


def repository_config():
    return {
        'sourceId': 'test-repository-subset', 'title': 'Test repository subset',
        'scope': 'Test-only Azure resource records', 'unit': 'aprl-guid',
        'adapter': 'github-tree-records', 'repository': 'Azure/Azure-Proactive-Resiliency-Library-v2',
        'ref': 'main', 'pathPrefix': 'azure-resources/', 'pathSuffix': '/recommendations.yaml',
        'maxFiles': 80, 'format': 'yaml', 'recordPath': '', 'idField': 'aprlGuid',
        'titleField': 'description', 'allowedHosts': ['api.github.com', 'raw.githubusercontent.com'],
        'fingerprintScope': 'Test-only complete original YAML recommendation object',
        'limitations': ['Diagnostic subset, not the canonical all-state APRL inventory.'],
    }


def inventory():
    payload = {'id': 'UP:01', 'requirement': 'An explicit source recommendation'}
    return {
        'schemaVersion': 1, 'sourceId': 'test-source', 'title': 'Test source',
        'scope': 'Entire named test checklist', 'unit': 'published-checklist-row',
        'asOf': '2026-09-11', 'retrievedAt': '2026-09-11T17:00:00Z',
        'upstreamRevision': 'a' * 40, 'inventoryStatus': 'complete',
        'sourceUrls': [URL], 'fingerprintScope': 'canonical-json-v1 {id,requirement}',
        'items': [{'id': 'UP:01', 'title': 'Explicit source recommendation',
                   'url': URL, 'payload': payload, 'contentHash': item_content_hash(payload)}],
        'limitations': ['Test checklist rows only, not all guidance paragraphs.'],
    }


def reference(coverage='full'):
    return {
        'sourceId': 'test-source', 'recommendationId': 'UP:01',
        'coverage': coverage, 'url': URL, 'assessedAt': '2026-09-11',
        'notes': 'Draft explicit mapping, pending independent human semantic review.',
        'upstreamContentHash': inventory()['items'][0]['contentHash'],
    }


def reco(identifier=ID, refs=None):
    return {'id': identifier, 'labels': {'guid': identifier},
            'provenance': {'upstreamRecommendations': refs or []}}


class SourceCoverageTests(unittest.TestCase):
    def test_hash_recipe_is_order_independent_and_content_sensitive(self):
        self.assertEqual(item_content_hash({'b': ['x'], 'a': 1}),
                         item_content_hash({'a': 1, 'b': ['x']}))
        self.assertNotEqual(item_content_hash({'title': 'one'}),
                            item_content_hash({'title': 'two'}))
        with self.assertRaises(SourceCoverageError):
            item_content_hash({'date': datetime.now(timezone.utc)})
        for payload in ({1: 'key'}, {'number': float('nan')}, {'number': float('inf')}):
            with self.subTest(payload=payload), self.assertRaises(SourceCoverageError):
                item_content_hash(payload)

    def test_complete_unique_ids_not_rows_or_citations_define_coverage(self):
        report = coverage_report(inventory(), [reco(refs=[reference()]), reco(OTHER, [reference()])])
        self.assertEqual(report['counts']['full'], 1)
        self.assertEqual(report['denominator'], 1)
        self.assertEqual(report['coveragePercent'], 100)
        self.assertEqual(report['items'][0]['corpusIds'], [ID, OTHER])
        self.assertIn('not independent human', report['assessmentBasis'])
        for field in ('inventoryScope', 'inventoryCount', 'excludedCount',
                      'excludedItems', 'coverageSelection'):
            self.assertNotIn(field, report, 'Unselected inventories preserve historical report shape.')

    def test_partial_and_supporting_are_not_full(self):
        partial = coverage_report(inventory(), [reco(refs=[reference('partial')])])
        self.assertEqual(partial['counts']['partial'], 1)
        self.assertEqual(partial['coveragePercent'], 0)
        self.assertEqual(partial['partialPercent'], 100)
        support = reference('supporting')
        del support['upstreamContentHash']
        supporting = coverage_report(inventory(), [reco(refs=[support])])
        self.assertEqual(supporting['counts']['supporting'], 1)
        self.assertIsNone(supporting['coveragePercent'])
        self.assertEqual(supporting['counts']['full'], 0)

    def test_unknown_is_not_zero_and_query_guids_do_not_map(self):
        record = reco()
        record['source'] = {'type': 'test-source', 'file': URL}
        record['queries'] = {'arg': '// UP:01'}
        record['links'] = [{'url': URL}]
        report = coverage_report(inventory(), [record])
        self.assertEqual(report['counts']['unknown'], 1)
        self.assertIsNone(report['coveragePercent'])
        self.assertIn('No current full/partial', report['reason'])

    def test_missing_denominator_metadata_never_gives_percentage(self):
        cases = [('inventoryStatus', 'partial'), ('inventoryStatus', 'unknown'),
                 ('asOf', None), ('retrievedAt', None), ('items', [])]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                document = inventory()
                document[key] = value
                report = coverage_report(document, [reco(refs=[reference()])])
                self.assertIsNone(report['denominator'])
                self.assertIsNone(report['coveragePercent'])
                self.assertTrue(report['reason'])

    def test_changed_content_invalidates_previous_mapping(self):
        document = inventory()
        document['items'][0]['payload']['requirement'] = 'Changed requirement'
        document['items'][0]['contentHash'] = item_content_hash(document['items'][0]['payload'])
        report = coverage_report(document, [reco(refs=[reference()])])
        self.assertEqual(report['counts']['stale'], 1)
        self.assertEqual(report['counts']['full'], 0)
        self.assertIsNone(report['coveragePercent'])

    def test_other_sources_and_absent_ids_are_not_coverage(self):
        wrong_source = dict(reference(), sourceId='another-source')
        removed_id = dict(reference(), recommendationId='removed')
        report = coverage_report(inventory(), [reco(refs=[wrong_source, removed_id])])
        self.assertIsNone(report['coveragePercent'])
        self.assertEqual(report['referencesOutsideInventory'], ['removed'])

    def test_alias_resolves_before_external_mapping(self):
        record = reco()
        record['aliases'] = [{'id': ALIAS, 'name': 'retired-name'}]
        self.assertEqual(resolve_recommendation_id(ALIAS, [record]), ID)
        report = coverage_report(inventory(), [record], [dict(reference(), corpusId=ALIAS)])
        self.assertEqual(report['items'][0]['corpusIds'], [ID])
        self.assertEqual(report['coveragePercent'], 100)
        with self.assertRaises(SourceCoverageError):
            coverage_report(inventory(), [record], [dict(reference(), corpusId=OTHER)])
        with self.assertRaises(SourceCoverageError):
            coverage_report(inventory(), [record, reco(ALIAS)])

    def test_schema_rejects_duplicate_ids_bad_hashes_and_unknown_version(self):
        for mutation in ('duplicate', 'payload', 'version', 'url'):
            with self.subTest(mutation=mutation):
                document = inventory()
                if mutation == 'duplicate':
                    document['items'].append(deepcopy(document['items'][0]))
                elif mutation == 'payload':
                    document['items'][0]['payload']['requirement'] = 'Modified without rehashing'
                elif mutation == 'version':
                    document['schemaVersion'] = 2
                else:
                    document['items'][0]['url'] = 'http://localhost/'
                with self.assertRaises(SourceCoverageError):
                    validate_inventory(document)

    def test_diffs_prove_id_changes_without_similarity_inference(self):
        previous = inventory()
        current = inventory()
        current['items'][0]['payload']['requirement'] = 'Changed'
        current['items'][0]['contentHash'] = item_content_hash(current['items'][0]['payload'])
        added = deepcopy(current['items'][0])
        added['id'] = 'new-id'
        current['items'].append(added)
        delta = diff_inventories(previous, current)
        self.assertEqual(delta['newIds'], ['new-id'])
        self.assertEqual(delta['changedIds'], ['UP:01'])
        self.assertEqual(delta['removedIds'], [])
        current['items'] = []
        self.assertEqual(diff_inventories(previous, current)['removedIds'], ['UP:01'])
        current['inventoryStatus'] = 'partial'
        self.assertIsNone(diff_inventories(previous, current)['removedIds'])
        previous['inventoryStatus'] = 'unknown'
        self.assertIsNone(diff_inventories(previous, current)['newIds'])

    def test_different_scope_unit_or_fingerprint_cannot_be_compared(self):
        for field in ('sourceId', 'scope', 'unit', 'fingerprintScope'):
            with self.subTest(field=field):
                current = inventory()
                current[field] = 'different'
                with self.assertRaises(SourceCoverageError):
                    diff_inventories(inventory(), current)

    def test_registry_identifier_change_preserves_item_hash_but_not_mapping_identity(self):
        document = inventory()
        document['sourceId'] = 'waf-security-checklist'
        validate_inventory(document)
        self.assertEqual(document['items'][0]['contentHash'], inventory()['items'][0]['contentHash'])
        self.assertIsNone(coverage_report(document, [reco(refs=[reference()])])['coveragePercent'])
        matching = dict(reference(), sourceId='waf-security-checklist')
        self.assertEqual(coverage_report(document, [reco(refs=[matching])])['coveragePercent'], 100)

    def test_invalid_assessment_is_explicit_error(self):
        for field in ('notes', 'assessedAt', 'upstreamContentHash'):
            with self.subTest(field=field):
                ref = reference()
                del ref[field]
                with self.assertRaises(SourceCoverageError):
                    coverage_report(inventory(), [reco(refs=[ref])])
        with self.assertRaisesRegex(SourceCoverageError, 'Duplicate upstream assessment'):
            coverage_report(inventory(), [reco(refs=[reference(), reference()])])


class SourceAdapterTests(unittest.TestCase):
    def test_imports_never_initiate_network_access(self):
        code = """
import socket
def refused(*args, **kwargs):
    raise AssertionError('Network access during import')
socket.getaddrinfo = refused
socket.create_connection = refused
import review_checklists.source_coverage
import review_checklists.source_audit
"""
        result = subprocess.run([sys.executable, '-c', code],
                                cwd=Path(__file__).resolve().parents[2],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_waf_pillars_registered_and_broad_scopes_explicitly_unsupported(self):
        registry = load_registry()
        for pillar in ('cost', 'security', 'reliability', 'performance', 'operations'):
            self.assertEqual(registry[f'waf-{pillar}-checklist']['adapter'], 'learn-waf-checklist')
            self.assertIn(f'advisor-{pillar}-catalog', registry)
            self.assertNotIn(f'azure-waf-{pillar}', registry)
            self.assertNotIn(f'azure-advisor-{pillar}', registry)
        self.assertEqual(len(registry), 13)
        for identifier in ('azure-waf-service-guides', 'legacy-review-checklists',
                           'advisor-security-catalog', 'advisor-performance-catalog',
                           'advisor-reliability-catalog', 'aprl'):
            with self.assertRaises(SourceAuditError):
                fetch_inventory(registry[identifier])

    def test_waf_ids_and_meaningful_payload_are_extracted(self):
        body = '## Checklist\n\n| - | Code | Recommendation |\n| --- | --- | --- |\n| x | [SE:01](baseline) | **Establish a baseline** with evidence. |\n'
        item, = parse_waf_checklist(body, URL, 'SE')
        self.assertEqual(item['id'], 'SE:01')
        self.assertEqual(item['payload']['recommendation'], '**Establish a baseline** with evidence.')
        self.assertEqual(item['url'], 'https://learn.microsoft.com/en-us/azure/well-architected/security/baseline')
        for invalid in (body.replace('Code', 'Changed header'), body.replace('[SE:01]', '[unknown]'), ''):
            with self.assertRaises(SourceAuditError):
                parse_waf_checklist(invalid, URL, 'SE')
        repeated = body.replace('[SE:01](baseline)', '[SE:01](baseline)[SE:01](another-link)')
        repeated_item, = parse_waf_checklist(repeated, URL, 'SE')
        self.assertEqual(repeated_item['id'], 'SE:01')
        self.assertEqual(repeated_item['url'], URL)
        self.assertEqual(repeated_item['payload']['code'], '[SE:01](baseline)[SE:01](another-link)')
        ambiguous = body.replace('[SE:01](baseline)', '[SE:01](baseline)[SE:02](another-unit)')
        with self.assertRaises(SourceAuditError):
            parse_waf_checklist(ambiguous, URL, 'SE')

    def test_advisor_guid_sections_are_not_all_advisor(self):
        body = f'## Compute\n#### Right size\nMeaningful requirement.\nRecommendation ID: {ID}\n'
        item, = parse_advisor_catalog(body, URL)
        self.assertEqual(item['id'], ID)
        self.assertIn('Meaningful requirement.', item['payload']['content'])
        with self.assertRaises(SourceAuditError):
            parse_advisor_catalog(body + '\n#### Missing ID\nCannot enumerate.', URL)

    def test_structured_ids_preserved_and_malformed_lists_fail(self):
        config = {'recordPath': 'items', 'idField': 'guid', 'titleField': 'text'}
        document = {'items': [{'guid': ID, 'text': 'Original record', 'graph': 'Exact query  \n'}]}
        item, = parse_records(document, config, URL)
        self.assertEqual(item['id'], ID)
        self.assertEqual(item['payload'], document['items'][0])
        for invalid in ({}, {'items': []}, {'items': [None]}):
            with self.assertRaises(SourceAuditError):
                parse_records(invalid, config, URL)

    def test_repository_retrieval_pins_before_reading_any_source(self):
        config = dict(
            repository_config(), adapter='github-records',
            path='test.json', format='json', recordPath='items', idField='guid', titleField='text',
        )
        reader = Mock()
        reader.json.return_value = {'sha': 'a' * 40, 'commit': {'tree': {'sha': 'b' * 40}}}
        reader.text.return_value = json.dumps({'items': [{'guid': ID, 'text': 'Record text'}]})
        result = fetch_inventory(config, reader)
        self.assertIn('/' + 'a' * 40 + '/', reader.text.call_args.args[0])
        self.assertEqual(result['upstreamRevision'], 'a' * 40)
        self.assertEqual(result['inventoryStatus'], 'complete')

    def test_tree_truncation_is_not_empty_success(self):
        config = repository_config()
        reader = Mock()
        reader.json.side_effect = [
            {'sha': 'a' * 40, 'commit': {'tree': {'sha': 'b' * 40}}},
            {'truncated': True, 'tree': []},
        ]
        with self.assertRaisesRegex(SourceAuditError, 'truncated'):
            fetch_inventory(config, reader)
        reader.text.assert_not_called()

    def test_tree_file_budget_marks_inventory_partial(self):
        config = dict(repository_config(), maxFiles=1)
        reader = Mock()
        reader.json.side_effect = [
            {'sha': 'a' * 40, 'commit': {'tree': {'sha': 'b' * 40}}},
            {'truncated': False, 'tree': [
                {'path': f'azure-resources/{number}/recommendations.yaml', 'type': 'blob'}
                for number in range(2)
            ]},
        ]
        reader.text.return_value = f'- aprlGuid: {ID}\n  description: Original recommendation\n'
        result = fetch_inventory(config, reader)
        self.assertEqual(result['inventoryStatus'], 'partial')
        self.assertIn('1 of 2', result['limitations'][-1])
        self.assertIsNone(coverage_report(result, [])['denominator'])

    def test_strict_input_parsing_rejects_duplicates_nonfinite_and_yaml_aliases(self):
        for text in ('{"id":1,"id":2}', '{"x":NaN}'):
            with self.assertRaises(SourceAuditError):
                parse_json(text)
        for text in ('id: one\nid: two\n', 'a: &ref [1]\nb: *ref\n'):
            with self.assertRaises(SourceAuditError):
                parse_yaml(text)

    def test_historical_snapshots_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            first = inventory()
            path = save_inventory(first, directory)
            before = path.read_bytes()
            second = deepcopy(first)
            second['retrievedAt'] = '2026-09-11T19:00:00Z'
            self.assertEqual(save_inventory(second, directory), path)
            self.assertEqual(path.read_bytes(), before)
            second['items'][0]['payload']['requirement'] = 'Changed content'
            second['items'][0]['contentHash'] = item_content_hash(second['items'][0]['payload'])
            self.assertNotEqual(save_inventory(second, directory), path)
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 2)

    def test_failed_snapshot_install_leaves_no_partial_artifact(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with patch('review_checklists.source_audit.os.link', side_effect=OSError('disk failure')):
                with self.assertRaisesRegex(OSError, 'disk failure'):
                    save_inventory(inventory(), directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_public_reader_refuses_unregistered_or_private_destinations(self):
        reader = PublicReader(['example.org'])
        for url in ('http://example.org/', 'https://other.example/', 'https://user:pass@example.org/'):
            with self.assertRaises(SourceAuditError):
                reader.text(url)
        with patch('review_checklists.source_audit.socket.getaddrinfo',
                   return_value=[(None, None, None, None, ('127.0.0.1', 443))]):
            with self.assertRaisesRegex(SourceAuditError, 'Non-public'):
                reader.text('https://example.org/')

    def test_response_size_and_pagination_limits_fail_explicitly(self):
        reader = PublicReader(['example.org'], max_bytes=4)
        response = Mock()
        response.status = 200
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        with patch('review_checklists.source_audit.socket.getaddrinfo',
                   return_value=[(None, None, None, None, ('8.8.8.8', 443))]), \
                patch('review_checklists.source_audit.build_opener', return_value=opener):
            response.headers = {'Link': '<https://example.org/page2>; rel="next"'}
            with self.assertRaisesRegex(SourceAuditError, 'Paginated'):
                reader.text('https://example.org/')
            response.headers = {}
            response.read.return_value = b'12345'
            with self.assertRaisesRegex(SourceAuditError, 'byte limit'):
                reader.text('https://example.org/')


class RepositorySourceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.modules.cl_corpus import load_yaml_document
        from review_checklists.corpus_admin import source_coverage

        cls.reports = ROOT / 'review_checklists' / 'docs' / 'corpus-refresh'
        cls.directory = cls.reports / 'source-inventories'
        cls.registry = load_registry()
        cls.recommendations = [load_yaml_document(path) for path in
                               sorted((ROOT / 'v2' / 'recos').rglob('*.yaml'))]
        cls.snapshots = [(path, json.loads(path.read_text(encoding='utf-8')))
                         for path in cls.directory.glob('*.json')]
        cls.report = source_coverage(cls.recommendations, cls.reports)
        cls.manifest = json.loads((cls.directory / 'deprecated' / 'index.json').read_text(encoding='utf-8'))

    def test_canonical_cards_have_exact_registered_scopes_and_unambiguous_histories(self):
        self.assertEqual(self.report['errors'], [])
        self.assertEqual(self.report['unknownSources'], {})
        ids = [source['sourceId'] for source in self.report['sources']]
        self.assertEqual(set(ids), set(self.registry))
        self.assertEqual(len(ids), len(set(ids)))
        histories = {}
        for path, document in self.snapshots:
            validate_inventory(document)
            config = self.registry[document['sourceId']]
            for field in ('scope', 'unit', 'fingerprintScope'):
                self.assertEqual(document[field], config[field], (path.name, field))
            timestamp = datetime.fromisoformat(document['retrievedAt'].replace('Z', '+00:00'))
            key = (document['sourceId'], document['asOf'], timestamp)
            if key in histories:
                self.assertEqual(document, histories[key], path.name)
            histories[key] = document

    def test_every_embedded_mapping_is_registered_and_hash_bound_or_explicitly_excepted(self):
        current = {row['sourceId']: row for row in self.report['sources']}
        exceptions = {(row['corpusId'], row['sourceId'], row['recommendationId']): row
                      for row in self.manifest['mappingExceptions']}
        used = set()
        for reco in self.recommendations:
            for ref in reco['provenance'].get('upstreamRecommendations', []):
                self.assertIn(ref['sourceId'], self.registry)
                report = current[ref['sourceId']]
                items = {item['id']: item for item in
                         report['items'] + report.get('excludedItems', [])}
                item = items.get(ref['recommendationId'])
                if item is None or item['contentHash'] != ref.get('upstreamContentHash'):
                    key = (reco['id'], ref['sourceId'], ref['recommendationId'])
                    self.assertIn(key, exceptions, key)
                    self.assertTrue(exceptions[key]['reason'].strip())
                    self.assertIn(exceptions[key]['state'], ('stale', 'absent'))
                    used.add(key)
        self.assertEqual(used, set(exceptions), 'Remove resolved mapping exceptions.')

    def test_promotion_preserves_verified_payloads_dates_and_status(self):
        for entry in self.manifest['promoted']:
            before = json.loads((self.directory / entry['from']).read_text(encoding='utf-8'))
            after = json.loads((self.directory / entry['file']).read_text(encoding='utf-8'))
            for field in ('sourceId', 'scope', 'unit', 'fingerprintScope', 'items',
                          'asOf', 'retrievedAt', 'upstreamRevision', 'inventoryStatus'):
                self.assertEqual(after[field], before[field], (entry['sourceId'], field))

    def test_deprecated_snapshots_are_byte_preserved_and_explicitly_scoped(self):
        archive_files = set()
        for entry in self.manifest['archived']:
            path = self.directory / entry['file']
            archive_files.add(path.name)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['sha256'])
            document = json.loads(path.read_text(encoding='utf-8'))
            validate_inventory(document)
            self.assertEqual(document['sourceId'], entry['originalSourceId'])
            self.assertTrue(entry['reason'].strip())
            self.assertTrue(entry['scopedSourceId'])
            for field in ('scope', 'unit', 'fingerprintScope'):
                self.assertEqual(document[field], entry[field])
            self.assertFalse((self.directory / path.name).exists())
        self.assertEqual(archive_files, {path.name for path in
                         (self.directory / 'deprecated').glob('*.json')} - {'index.json'})

    def test_aprl_active_coverage_preserves_disabled_identity_and_all_state_diffs(self):
        document = next(data for _, data in self.snapshots if data['sourceId'] == 'aprl')
        report = coverage_report(document, self.recommendations)
        self.assertEqual(report['inventoryCount'], 456)
        self.assertEqual(report['denominator'], 393)
        self.assertEqual(report['excludedCount'], 63)
        self.assertEqual(sum(report['counts'].values()), 393)
        self.assertEqual({row['upstreamState'] for row in report['items']}, {'Active'})
        self.assertEqual({row['upstreamState'] for row in report['excludedItems']}, {'Disabled'})
        self.assertEqual(report['referencesOutsideInventory'], [])
        self.assertEqual(diff_inventories(document, deepcopy(document))['changedIds'], [])
        changed = deepcopy(document)
        disabled = next(item for item in changed['items']
                        if item['payload']['recommendationMetadataState'] == 'Disabled')
        disabled['payload']['recommendationMetadataState'] = 'Active'
        disabled['contentHash'] = item_content_hash(disabled['payload'])
        self.assertEqual(diff_inventories(document, changed)['changedIds'], [disabled['id']])
        self.assertEqual(coverage_report(changed, self.recommendations)['denominator'], 394)
        disabled['payload'].pop('recommendationMetadataState')
        disabled['contentHash'] = item_content_hash(disabled['payload'])
        with self.assertRaisesRegex(SourceCoverageError, 'coverage selection state'):
            validate_inventory(changed)

    def test_partial_and_unknown_catalogs_never_produce_percentages(self):
        reports = {row['sourceId']: row for row in self.report['sources']}
        for identifier, count, status in [('advisor-reliability-catalog', 9, 'partial'),
                                           ('advisor-security-catalog', 0, 'unknown')]:
            row = reports[identifier]
            self.assertEqual(row['observedCount'], count)
            self.assertEqual(row['inventoryStatus'], status)
            self.assertIsNone(row['denominator'])
            self.assertIsNone(row['coveragePercent'])
            self.assertIsNone(row['partialPercent'])
        self.assertEqual(reports['advisor-performance-catalog']['denominator'], 150)
        self.assertEqual(reports['advisor-operations-catalog']['denominator'], 122)

    def test_supported_adapter_fixtures_reproduce_canonical_payload_hashes(self):
        for _, document in self.snapshots:
            config = self.registry[document['sourceId']]
            if config['adapter'] == 'learn-waf-checklist':
                item = document['items'][0]
                payload = item['payload']
                body = ('## Checklist\n| - | Code | Recommendation |\n| --- | --- | --- |\n'
                        f"| x | {payload['code']} | {payload['recommendation']} |\n")
                parsed, = parse_waf_checklist(body, config['url'], config['idPrefix'])
            elif config['adapter'] == 'learn-advisor-catalog':
                item = document['items'][0]
                payload = item['payload']
                parsed, = parse_advisor_catalog(f"#### {payload['title']}\n{payload['content']}\n",
                                               config['url'])
            else:
                continue
            self.assertEqual(parsed['contentHash'], item['contentHash'], document['sourceId'])


if __name__ == '__main__':
    unittest.main()
