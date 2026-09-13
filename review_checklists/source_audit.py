"""Explicit read-only public source checks; never imports recommendations."""

import argparse
from datetime import date, datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
from urllib.error import URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import yaml

from .source_coverage import (
    SourceCoverageError, coverage_report, diff_inventories, item_content_hash,
    validate_inventory,
)


REGISTRY_PATH = Path(__file__).with_name('source-registry.json')
SNAPSHOT_DIRECTORY = Path(__file__).with_name('docs') / 'corpus-refresh' / 'source-inventories'


class SourceAuditError(ValueError):
    """Unsupported, malformed, incomplete, or unsafe source retrieval."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceAuditError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise SourceAuditError(f"Non-finite JSON value: {value}")


def read_json(path):
    return parse_json(Path(path).read_text(encoding='utf-8'))


def parse_json(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)


class _YamlLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise SourceAuditError("YAML mapping keys must be strings")
            if key in result:
                raise SourceAuditError(f"Duplicate YAML key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def parse_yaml(text):
    if any(isinstance(token, (yaml.AliasToken, yaml.AnchorToken)) for token in yaml.scan(text)):
        raise SourceAuditError("Source YAML anchors/aliases are not supported")
    document = yaml.load(text, Loader=_YamlLoader)

    def json_value(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: json_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [json_value(item) for item in value]
        return value

    return json_value(document)


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise SourceAuditError(f"Redirect refused; configure the canonical public URL: {new_url}")


class PublicReader:
    """Bounded, anonymous HTTPS reads. No proxies, tokens, cookies, or execution."""

    def __init__(self, allowed_hosts, timeout=20, max_bytes=4_000_000, max_requests=85):
        self.allowed_hosts = set(allowed_hosts)
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_requests = max_requests
        self.requests = 0

    def text(self, url):
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.hostname not in self.allowed_hosts
                or parsed.username or parsed.password or parsed.port not in (None, 443)
                or any(character.isspace() for character in url)):
            raise SourceAuditError(f"Only registered public HTTPS URLs are allowed: {url}")
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
            raise SourceAuditError(f"Non-public network destination refused: {parsed.hostname}")
        if self.requests >= self.max_requests:
            raise SourceAuditError("Public source request budget exceeded")
        self.requests += 1
        request = Request(url, headers={
            'User-Agent': 'review-checklists-source-audit/1',
            'Accept': 'application/json, text/markdown, text/plain;q=0.9',
            'Accept-Encoding': 'identity',
        })
        opener = build_opener(ProxyHandler({}), _NoRedirects())
        with opener.open(request, timeout=self.timeout) as response:
            if response.status != 200:
                raise SourceAuditError(f"Unexpected HTTP status {response.status}: {url}")
            if re.search(r'rel\s*=\s*"?next', response.headers.get('Link', ''), re.IGNORECASE):
                raise SourceAuditError(f"Paginated response cannot establish completeness: {url}")
            length = response.headers.get('Content-Length')
            if length is not None and int(length) > self.max_bytes:
                raise SourceAuditError(f"Source response exceeds byte limit: {url}")
            data = response.read(self.max_bytes + 1)
            if len(data) > self.max_bytes:
                raise SourceAuditError(f"Source response exceeds byte limit: {url}")
            if length is not None and len(data) != int(length):
                raise SourceAuditError(f"Truncated source response: {url}")
            return data.decode('utf-8')

    def json(self, url):
        return parse_json(self.text(url))


def split_frontmatter(text):
    match = re.match(r'\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z', text, re.DOTALL)
    if not match:
        raise SourceAuditError("Expected a published Markdown page with version frontmatter")
    metadata = parse_yaml(match[1])
    if not isinstance(metadata, dict):
        raise SourceAuditError("Published page frontmatter must be an object")
    return metadata, match[2]


def _item(identifier, title, url, payload):
    if not isinstance(identifier, str) or not identifier.strip():
        raise SourceAuditError("Source recommendation has no stable upstream string ID")
    if not isinstance(title, str) or not title.strip():
        raise SourceAuditError(f"Source recommendation has no title: {identifier}")
    return {'id': identifier, 'title': title, 'url': url,
            'contentHash': item_content_hash(payload), 'payload': payload}


def parse_waf_checklist(body, base_url, prefix):
    section = re.search(r'^## Checklist\s*\r?\n(.*?)(?=^## |\Z)', body, re.MULTILINE | re.DOTALL)
    if not section:
        raise SourceAuditError("Published WAF Checklist section was not found")
    lines = [line.strip() for line in section[1].splitlines() if line.strip().startswith('|')]
    if len(lines) < 3:
        raise SourceAuditError("WAF checklist table is absent or empty")

    def cells(line):
        return [value.strip() for value in re.split(r'(?<!\\)\|', line.strip('|'))]

    if cells(lines[0])[-2:] != ['Code', 'Recommendation']:
        raise SourceAuditError("WAF table headers changed; parser review required")
    if not all(re.fullmatch(r':?-+:?', cell) for cell in cells(lines[1])):
        raise SourceAuditError("Invalid WAF table separator")
    items = []
    code_occurrences = 0
    for line in lines[2:]:
        row = cells(line)
        if len(row) != 3:
            raise SourceAuditError("Unexpected WAF table row shape")
        pattern = r'\[(' + re.escape(prefix) + r':\d+)\]\(([^)]+)\)'
        links = re.findall(pattern, row[1])
        if (not links or len({identifier for identifier, _ in links}) != 1
                or re.sub(pattern, '', row[1]).strip() or not row[2]):
            raise SourceAuditError(f"Unrecognized WAF checklist row: {row[1]}")
        identifier, target = links[0]
        code_occurrences += len(links)
        bold = re.search(r'\*\*(.+?)\*\*', row[2])
        title = bold[1] if bold else row[2]
        payload = {'id': identifier, 'code': row[1], 'recommendation': row[2]}
        evidence_url = urljoin(base_url, target) if len(links) == 1 else base_url
        items.append(_item(identifier, title, evidence_url, payload))
    expected = re.findall(r'\[' + re.escape(prefix) + r':\d+\]\(', section[1])
    if len(expected) != code_occurrences:
        raise SourceAuditError("WAF IDs outside parsed rows prevent complete enumeration")
    return items


def parse_advisor_catalog(body, base_url):
    sections = list(re.finditer(r'^#### (.+)\r?$', body, re.MULTILINE))
    if not sections:
        raise SourceAuditError("Published Advisor recommendation sections were not found")
    marker = r'Recommendation\s+ID\s*:\s*([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})'
    items = []
    for number, section in enumerate(sections):
        end = sections[number + 1].start() if number + 1 < len(sections) else len(body)
        content = body[section.end():end]
        content = re.split(r'^#{1,3} ', content, maxsplit=1, flags=re.MULTILINE)[0].strip()
        identifiers = re.findall(marker, content)
        if len(identifiers) != 1:
            raise SourceAuditError(f"Expected exactly one Advisor GUID in section: {section[1]}")
        identifier = identifiers[0]
        payload = {'id': identifier, 'title': section[1].strip(), 'content': content}
        items.append(_item(identifier, section[1].strip(), base_url, payload))
    if len(re.findall(marker, body)) != len(items):
        raise SourceAuditError("Unparsed Advisor GUIDs prevent complete enumeration")
    return items


def parse_records(document, config, evidence_url):
    records = document
    for key in config.get('recordPath', '').split('.'):
        if key:
            if not isinstance(records, dict) or key not in records:
                raise SourceAuditError(f"Missing structured record path: {config['recordPath']}")
            records = records[key]
    if not isinstance(records, list) or not records:
        raise SourceAuditError("Expected a nonempty structured recommendation list")
    items = []
    for record in records:
        if not isinstance(record, dict):
            raise SourceAuditError("Structured recommendation must be an object")
        identifier = record.get(config['idField'])
        title = record.get(config['titleField'])
        items.append(_item(identifier, title, evidence_url, record))
    return items


def _repository_revision(config, reader):
    repository = config['repository']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise SourceAuditError("Invalid configured GitHub repository")
    commit = reader.json(f"https://api.github.com/repos/{repository}/commits/{quote(config['ref'], safe='')}")
    revision = commit.get('sha', '')
    tree = commit.get('commit', {}).get('tree', {}).get('sha', '')
    if not re.fullmatch(r'[0-9a-f]{40}', revision) or not re.fullmatch(r'[0-9a-f]{40}', tree):
        raise SourceAuditError("Cannot pin repository commit and tree")
    return revision, tree


def fetch_inventory(config: dict, reader=None, observed_at=None) -> dict:
    if config['adapter'] == 'unsupported':
        raise SourceAuditError(config['unsupportedReason'])
    reader = reader or PublicReader(config['allowedHosts'])
    observed_at = observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise SourceAuditError("Inventory observation time must include a timezone")
    observed_at = observed_at.astimezone(timezone.utc)
    result = {
        'schemaVersion': 1, 'sourceId': config['sourceId'], 'title': config['title'],
        'scope': config['scope'], 'unit': config['unit'],
        'asOf': observed_at.date().isoformat(),
        'retrievedAt': observed_at.isoformat().replace('+00:00', 'Z'),
        'upstreamRevision': None, 'inventoryStatus': 'complete', 'sourceUrls': [],
        'fingerprintScope': config['fingerprintScope'], 'items': [],
        'limitations': list(config['limitations']),
    }
    adapter = config['adapter']
    if adapter in ('learn-waf-checklist', 'learn-advisor-catalog'):
        url = config['url']
        metadata, body = split_frontmatter(reader.text(url + '?accept=text/markdown'))
        if metadata.get('canonicalUrl') != url:
            raise SourceAuditError("Published page canonical URL differs from registry")
        revision = metadata.get('git_commit_id')
        if revision is not None and not re.fullmatch(r'[0-9a-f]{40}', str(revision)):
            raise SourceAuditError("Unrecognized published page revision")
        result['upstreamRevision'] = revision
        result['sourceUrls'] = [url]
        if adapter == 'learn-waf-checklist':
            result['items'] = parse_waf_checklist(body, url, config['idPrefix'])
        else:
            result['items'] = parse_advisor_catalog(body, url)
    elif adapter in ('github-records', 'github-tree-records'):
        revision, tree = _repository_revision(config, reader)
        result['upstreamRevision'] = revision
        repository = config['repository']
        if adapter == 'github-records':
            paths = [config['path']]
        else:
            tree_document = reader.json(
                f'https://api.github.com/repos/{repository}/git/trees/{tree}?recursive=1',
            )
            if tree_document.get('truncated') is not False or not isinstance(tree_document.get('tree'), list):
                raise SourceAuditError("GitHub tree is truncated or lacks explicit completeness metadata")
            paths = sorted(entry['path'] for entry in tree_document['tree']
                           if entry.get('type') == 'blob'
                           and entry['path'].startswith(config['pathPrefix'])
                           and entry['path'].endswith(config['pathSuffix']))
            if not paths:
                raise SourceAuditError("No configured recommendation files found in pinned tree")
            if len(paths) > config['maxFiles']:
                result['inventoryStatus'] = 'partial'
                result['limitations'].append(
                    f"File budget: fetched {config['maxFiles']} of {len(paths)} matching files; no complete denominator.",
                )
                paths = paths[:config['maxFiles']]
        for path in paths:
            if path.startswith('/') or '..' in path.split('/') or '\\' in path:
                raise SourceAuditError("Unsafe repository path")
            evidence = f'https://github.com/{repository}/blob/{revision}/{quote(path, safe="/")}'
            raw = f'https://raw.githubusercontent.com/{repository}/{revision}/{quote(path, safe="/")}'
            text = reader.text(raw)
            document = parse_json(text) if config['format'] == 'json' else parse_yaml(text)
            result['items'].extend(parse_records(document, config, evidence))
            result['sourceUrls'].append(evidence)
    else:
        raise SourceAuditError(f"Unsupported source adapter: {adapter}")
    if not result['items']:
        raise SourceAuditError("Parser produced no source units; refusing an empty success snapshot")
    result['items'].sort(key=lambda item: item['id'])
    validate_inventory(result)
    return result


def save_inventory(inventory, directory=SNAPSHOT_DIRECTORY):
    """Create an immutable versioned snapshot; identical observations reuse it."""
    validate_inventory(inventory)
    semantic = {key: value for key, value in inventory.items() if key != 'retrievedAt'}
    digest = item_content_hash(semantic).split(':')[1][:12]
    revision = inventory['upstreamRevision'] or 'unknown'
    revision = re.sub(r'[^a-zA-Z0-9_-]', '-', revision)[:40]
    filename = f"{inventory['sourceId']}--{inventory['asOf'] or 'undated'}--{revision}--{digest}.json"
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    if destination.exists():
        existing = read_json(destination)
        validate_inventory(existing)
        if {key: value for key, value in existing.items() if key != 'retrievedAt'} != semantic:
            raise SourceAuditError(f"Refusing to overwrite a historical snapshot: {destination}")
        return destination
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         dir=directory, prefix='.inventory-', suffix='.tmp',
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(inventory, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n')
        try:
            os.link(temporary, destination)
        except FileExistsError:
            return save_inventory(inventory, directory)
    finally:
        if temporary is not None:
            temporary.unlink()
    return destination


def load_registry(path=REGISTRY_PATH):
    registry = read_json(path)
    if registry.get('schemaVersion') != 1 or not isinstance(registry.get('sources'), list):
        raise SourceAuditError("Unsupported source registry")
    sources = {}
    for source in registry['sources']:
        if not isinstance(source, dict):
            raise SourceAuditError("Registry source must be an object")
        identifier = source.get('sourceId', '')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', identifier) or identifier in sources:
            raise SourceAuditError(f"Invalid/duplicate registry sourceId: {identifier}")
        for key in ('title', 'scope', 'unit', 'adapter'):
            if not isinstance(source.get(key), str) or not source[key].strip():
                raise SourceAuditError(f"{identifier}: missing registry {key}")
        adapter = source['adapter']
        if adapter == 'unsupported':
            if not isinstance(source.get('unsupportedReason'), str) or not source['unsupportedReason'].strip():
                raise SourceAuditError(f"{identifier}: unsupported provider needs an explicit reason")
        else:
            if adapter not in ('learn-waf-checklist', 'learn-advisor-catalog', 'github-records', 'github-tree-records'):
                raise SourceAuditError(f"{identifier}: unknown adapter")
            for key in ('allowedHosts', 'limitations'):
                if not isinstance(source.get(key), list) or not all(
                        isinstance(value, str) and value.strip() for value in source[key]):
                    raise SourceAuditError(f"{identifier}: invalid registry {key}")
            if not source['allowedHosts'] or not isinstance(source.get('fingerprintScope'), str):
                raise SourceAuditError(f"{identifier}: allowed hosts and fingerprint scope are required")
            if adapter == 'github-tree-records' and (
                    type(source.get('maxFiles')) is not int or not 1 <= source['maxFiles'] <= 80):
                raise SourceAuditError(f"{identifier}: maxFiles must be between 1 and 80")
        sources[identifier] = source
    return sources


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('list', help='List registered scopes and unsupported units; offline')
    fetch = subparsers.add_parser('fetch', help='Explicit anonymous public HTTPS reads; saves inventory only')
    fetch.add_argument('--source', required=True)
    fetch.add_argument('--output-dir', type=Path, default=SNAPSHOT_DIRECTORY)
    validate = subparsers.add_parser('validate', help='Validate a local inventory; offline')
    validate.add_argument('inventory', type=Path)
    diff = subparsers.add_parser('diff', help='Compare local inventory snapshots; offline')
    diff.add_argument('previous', type=Path)
    diff.add_argument('current', type=Path)
    coverage = subparsers.add_parser('coverage', help='Report explicit source ID mappings; offline')
    coverage.add_argument('inventory', type=Path)
    coverage.add_argument('--corpus', type=Path, default=Path('v2') / 'recos')
    coverage.add_argument('--mappings', type=Path,
                          help='Optional local draft assessments with corpusId (canonical or alias); no writes')
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            result = list(load_registry().values())
        elif args.command == 'fetch':
            sources = load_registry()
            if args.source not in sources:
                raise SourceAuditError(f"Unregistered source: {args.source}")
            inventory = fetch_inventory(sources[args.source])
            destination = save_inventory(inventory, args.output_dir)
            result = {'path': str(destination), 'sourceId': inventory['sourceId'],
                      'inventoryStatus': inventory['inventoryStatus'], 'items': len(inventory['items']),
                      'limitations': inventory['limitations']}
        elif args.command == 'validate':
            inventory = read_json(args.inventory)
            validate_inventory(inventory)
            result = {'valid': True, 'sourceId': inventory['sourceId'], 'items': len(inventory['items'])}
        elif args.command == 'diff':
            result = diff_inventories(read_json(args.previous), read_json(args.current))
        else:
            from scripts.modules.cl_corpus import load_yaml_document, validate_corpus
            if not args.corpus.is_dir():
                raise SourceAuditError(f"Corpus directory does not exist: {args.corpus}")
            recommendations = [load_yaml_document(path) for path in sorted(args.corpus.rglob('*'))
                               if path.suffix.lower() in ('.yaml', '.yml')]
            validate_corpus(recommendations)
            result = coverage_report(read_json(args.inventory), recommendations,
                                     read_json(args.mappings) if args.mappings else None)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (SourceCoverageError, SourceAuditError, OSError, URLError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
