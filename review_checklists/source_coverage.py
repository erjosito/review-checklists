"""Pure-data source inventories and explicit ID mapping coverage. Never fetches."""

from datetime import date
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker


class SourceCoverageError(ValueError):
    """Invalid inventory, identity, or explicit mapping evidence."""


def _json_safe(value):
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise SourceCoverageError("JSON object keys must be strings")
        for item in value.values():
            _json_safe(item)
    elif isinstance(value, list):
        for item in value:
            _json_safe(item)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise SourceCoverageError("Non-finite values are not JSON evidence")
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise SourceCoverageError(f"Unsupported JSON value: {type(value).__name__}")


def item_content_hash(payload: dict) -> str:
    """Hash adapter-defined meaningful payload, never retrieval metadata."""
    if not isinstance(payload, dict):
        raise SourceCoverageError("A fingerprint payload must be a JSON object")
    _json_safe(payload)
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    return 'sha256:' + hashlib.sha256(encoded).hexdigest()


@lru_cache(maxsize=1)
def _validator():
    path = Path(__file__).with_name('schema') / 'source-inventory.schema.json'
    schema = json.loads(path.read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _https_url(url):
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                 and not parsed.password and parsed.port in (None, 443)
                 and not any(character.isspace() for character in url))
    except (ValueError, TypeError) as exc:
        raise SourceCoverageError(f"Invalid HTTPS evidence URL: {url!r}") from exc
    if not valid:
        raise SourceCoverageError(f"Invalid HTTPS evidence URL: {url!r}")


def validate_inventory(inventory: dict) -> None:
    _json_safe(inventory)
    errors = sorted(_validator().iter_errors(inventory), key=lambda error: str(error.path))
    if errors:
        raise SourceCoverageError(f"Inventory {list(errors[0].path)}: {errors[0].message}")
    for field in ('sourceId', 'title', 'scope', 'unit', 'fingerprintScope'):
        if not inventory[field].strip():
            raise SourceCoverageError(f"Inventory {field} must not be blank")
    identities = set()
    selection = inventory.get('coverageSelection')
    if selection:
        if not set(selection['includedValues']) <= set(selection['knownValues']):
            raise SourceCoverageError("Coverage selection includes an unknown state")
        if any(not selection[key].strip() for key in ('payloadField', 'scope', 'reason')):
            raise SourceCoverageError("Coverage selection fields must not be blank")
    for item in inventory['items']:
        if not item['id'].strip() or not item['title'].strip():
            raise SourceCoverageError("Inventory IDs and titles must not be blank")
        if item['id'] in identities:
            raise SourceCoverageError(f"Duplicate upstream recommendation ID: {item['id']}")
        identities.add(item['id'])
        _https_url(item['url'])
        if item_content_hash(item['payload']) != item['contentHash']:
            raise SourceCoverageError(f"Fingerprint does not match payload: {item['id']}")
        if selection and item['payload'].get(selection['payloadField']) not in selection['knownValues']:
            raise SourceCoverageError(f"Missing or unknown coverage selection state: {item['id']}")
    for url in inventory['sourceUrls']:
        _https_url(url)
    if inventory['inventoryStatus'] == 'complete' and not inventory['sourceUrls']:
        raise SourceCoverageError("Complete inventories require source evidence URLs")


def diff_inventories(previous: dict, current: dict) -> dict:
    """Absence proves removal/newness only against a complete, dated snapshot."""
    validate_inventory(previous)
    validate_inventory(current)
    for field in ('sourceId', 'scope', 'unit', 'fingerprintScope'):
        if previous[field] != current[field]:
            raise SourceCoverageError(f"Cannot compare inventories with different {field}")
    if previous['asOf'] and current['asOf'] and previous['asOf'] > current['asOf']:
        raise SourceCoverageError("Current inventory date precedes previous inventory")
    old = {item['id']: item['contentHash'] for item in previous['items']}
    new = {item['id']: item['contentHash'] for item in current['items']}
    old_complete = previous['inventoryStatus'] == 'complete' and previous['asOf'] is not None
    new_complete = current['inventoryStatus'] == 'complete' and current['asOf'] is not None
    return {
        'schemaVersion': 1, 'sourceId': current['sourceId'],
        'scope': current['scope'], 'unit': current['unit'],
        'previousAsOf': previous['asOf'], 'asOf': current['asOf'],
        'previousRevision': previous['upstreamRevision'],
        'upstreamRevision': current['upstreamRevision'],
        'newIds': sorted(new.keys() - old.keys()) if old_complete else None,
        'removedIds': sorted(old.keys() - new.keys()) if new_complete else None,
        'changedIds': sorted(key for key in old.keys() & new.keys() if old[key] != new[key]),
        'observedOnlyInCurrent': sorted(new.keys() - old.keys()),
        'observedOnlyInPrevious': sorted(old.keys() - new.keys()),
        'completeComparison': bool(old_complete and new_complete),
        'limitations': ([] if old_complete else ['New IDs cannot be confirmed against an incomplete or undated baseline.'])
        + ([] if new_complete else ['Removed IDs cannot be confirmed from an incomplete or undated current snapshot.']),
    }


def _identity_index(recommendations):
    if not isinstance(recommendations, list):
        raise SourceCoverageError("Recommendations must be a list")
    index = {}
    canonical = {}
    for reco in recommendations:
        if not isinstance(reco, dict) or not isinstance(reco.get('labels', {}), dict):
            raise SourceCoverageError("Recommendation and labels must be objects")
        aliases = reco.get('aliases', [])
        if not isinstance(aliases, list) or any(
                not isinstance(alias, dict) or not isinstance(alias.get('id'), str) for alias in aliases):
            raise SourceCoverageError("Aliases must be objects with string IDs")
        raw_ids = [reco.get('id'), reco.get('guid'), reco.get('labels', {}).get('guid')]
        try:
            ids = {str(UUID(value)) for value in raw_ids if value is not None}
        except (ValueError, AttributeError, TypeError) as exc:
            raise SourceCoverageError("Invalid corpus recommendation identity") from exc
        if len(ids) != 1:
            raise SourceCoverageError("Missing or inconsistent canonical corpus identity")
        identifier = ids.pop()
        if identifier in canonical:
            raise SourceCoverageError(f"Duplicate canonical corpus ID: {identifier}")
        canonical[identifier] = reco
        for raw_id in [identifier, *(alias['id'] for alias in reco.get('aliases', []))]:
            try:
                alias_id = str(UUID(raw_id))
            except (ValueError, AttributeError, TypeError) as exc:
                raise SourceCoverageError(f"Invalid corpus alias ID: {raw_id}") from exc
            if alias_id in index:
                raise SourceCoverageError(f"Ambiguous canonical/alias corpus ID: {alias_id}")
            index[alias_id] = identifier
    return index, canonical


def resolve_recommendation_id(identifier: str, recommendations: list[dict]) -> str:
    """Resolve a saved/retired GUID before associating external mapping evidence."""
    index, _ = _identity_index(recommendations)
    try:
        return index[str(UUID(identifier))]
    except (KeyError, ValueError, AttributeError, TypeError) as exc:
        raise SourceCoverageError(f"Unknown corpus recommendation ID: {identifier}") from exc


def _check_reference(reference):
    if not isinstance(reference, dict):
        raise SourceCoverageError("Upstream assessment must be an object")
    for field in ('sourceId', 'recommendationId', 'url', 'coverage', 'assessedAt', 'notes'):
        if not isinstance(reference.get(field), str) or not reference[field].strip():
            raise SourceCoverageError(f"Upstream assessment needs nonblank {field}")
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', reference['sourceId']):
        raise SourceCoverageError("Invalid assessment sourceId")
    if reference['coverage'] not in ('full', 'partial', 'supporting'):
        raise SourceCoverageError("Unknown upstream assessment coverage")
    try:
        if date.fromisoformat(reference['assessedAt']).isoformat() != reference['assessedAt']:
            raise ValueError('Not ISO date')
    except ValueError as exc:
        raise SourceCoverageError("Assessment assessedAt must be an ISO date") from exc
    _https_url(reference['url'])
    content_hash = reference.get('upstreamContentHash')
    if content_hash is not None or reference['coverage'] in ('full', 'partial'):
        if not isinstance(content_hash, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', content_hash):
            raise SourceCoverageError("Full/partial assessments require an upstream content hash")


def coverage_report(inventory: dict, recommendations: list[dict], mappings=None) -> dict:
    """Count unique inventoried upstream IDs, not citations or corpus rows.

    Optional additional mappings have corpusId (canonical or alias GUID) plus
    the provenance.upstreamRecommendations fields. No text/query matching occurs.
    """
    validate_inventory(inventory)
    index, canonical = _identity_index(recommendations)
    references = []
    for canonical_id, reco in canonical.items():
        provenance = reco.get('provenance', {})
        if not isinstance(provenance, dict) or not isinstance(provenance.get('upstreamRecommendations', []), list):
            raise SourceCoverageError("Provenance must contain an upstreamRecommendations list when present")
        for reference in provenance.get('upstreamRecommendations', []):
            references.append((canonical_id, reference))
    if mappings is not None and not isinstance(mappings, list):
        raise SourceCoverageError("External mappings must be a list")
    for reference in mappings or []:
        try:
            canonical_id = index[str(UUID(reference['corpusId']))]
        except (KeyError, ValueError, AttributeError, TypeError) as exc:
            raise SourceCoverageError("External mapping has an unknown canonical/alias corpusId") from exc
        references.append((canonical_id, reference))
    items = {item['id']: item for item in inventory['items']}
    assessments = {identifier: [] for identifier in items}
    outside = set()
    seen = set()
    for canonical_id, reference in references:
        _check_reference(reference)
        identity = (canonical_id, reference['sourceId'], reference['recommendationId'])
        if identity in seen:
            raise SourceCoverageError(f"Duplicate upstream assessment for canonical corpus identity: {identity}")
        seen.add(identity)
        if reference['sourceId'] != inventory['sourceId']:
            continue
        identifier = reference['recommendationId']
        if identifier not in items:
            outside.add(identifier)
            continue
        coverage = reference['coverage']
        fresh = reference.get('upstreamContentHash') == items[identifier]['contentHash']
        state = coverage if fresh or coverage == 'supporting' else 'stale'
        assessments[identifier].append({
            'corpusId': canonical_id, 'coverage': coverage, 'state': state,
            'hashMatches': fresh, 'assessedAt': reference['assessedAt'],
            'url': reference['url'], 'notes': reference['notes'],
        })
    counts = {state: 0 for state in ('full', 'partial', 'stale', 'supporting', 'unknown')}
    rows = []
    excluded_rows = []
    selection = inventory.get('coverageSelection')
    for identifier in sorted(items):
        evidence = assessments[identifier]
        states = {entry['state'] for entry in evidence}
        state = next((value for value in counts if value in states), 'unknown')
        included = not selection or items[identifier]['payload'][selection['payloadField']] in selection['includedValues']
        if included:
            counts[state] += 1
        row = {
            'id': identifier, 'title': items[identifier]['title'], 'url': items[identifier]['url'],
            'contentHash': items[identifier]['contentHash'], 'state': state,
            'corpusIds': sorted({entry['corpusId'] for entry in evidence}),
            'assessments': sorted(evidence, key=lambda value: (value['corpusId'], value['coverage'], value['assessedAt'])),
        }
        if selection:
            row['upstreamState'] = items[identifier]['payload'][selection['payloadField']]
        (rows if included else excluded_rows).append(row)
    reasons = []
    if inventory['inventoryStatus'] != 'complete':
        reasons.append('Inventory is not complete for the stated scope and unit.')
    if not inventory['asOf'] or not inventory['retrievedAt']:
        reasons.append('Inventory observation/retrieval dates are unknown.')
    if not rows:
        reasons.append('Inventory is empty; no nonempty denominator is established.')
    denominator = len(rows) if not reasons else None
    if counts['full'] + counts['partial'] == 0:
        reasons.append('No current full/partial ID assessments; missing, supporting, or stale references are not zero coverage.')
    measurable = denominator is not None and not reasons
    return {
        'schemaVersion': 1, 'sourceId': inventory['sourceId'], 'title': inventory['title'],
        'scope': selection['scope'] if selection else inventory['scope'],
        'unit': inventory['unit'], 'asOf': inventory['asOf'],
        'retrievedAt': inventory['retrievedAt'], 'upstreamRevision': inventory['upstreamRevision'],
        'inventoryStatus': inventory['inventoryStatus'], 'sourceUrls': list(inventory['sourceUrls']),
        'observedCount': len(rows),
        **({'inventoryScope': inventory['scope'], 'inventoryCount': len(items),
            'excludedCount': len(excluded_rows), 'excludedItems': excluded_rows,
            'coverageSelection': dict(selection)} if selection else {}),
        'denominator': denominator, 'counts': counts,
        'coveragePercent': round(100 * counts['full'] / denominator, 2) if measurable else None,
        'partialPercent': round(100 * counts['partial'] / denominator, 2) if measurable else None,
        'reason': ' '.join(reasons) if reasons else None,
        'assessmentBasis': 'Recorded explicit ID mappings with matching content hashes; not independent human semantic review.',
        'limitations': list(inventory['limitations']), 'items': rows,
        'referencesOutsideInventory': sorted(outside),
    }
