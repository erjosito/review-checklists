# Upstream source inventories and ID coverage

This is **read-only source auditing**, not automatic recommendation ingestion.
It can discover new, changed, and removed upstream IDs and measure explicit
corpus mappings against a defined source inventory. It does not infer semantic
equivalence, run queries, log in to Azure, change reviews, or certify human review.
The UI must read saved inventories through the pure-data API; it must never
initiate network checks.

## Version 1 inventory contract

The authoritative inventory schema is
[`source-inventory.schema.json`](../schema/source-inventory.schema.json).
Every snapshot contains:

| Field | Meaning |
| --- | --- |
| `schemaVersion` | Integer `1` |
| `sourceId` | Stable lowercase slug identifying exactly one provider/scope/unit |
| `title`, `scope`, `unit` | Human-readable boundary; checklist rows are not all guidance paragraphs |
| `asOf` | ISO date of this observed inventory, or `null` |
| `retrievedAt` | ISO timezone-qualified retrieval timestamp, or `null` |
| `upstreamRevision` | Pinned repository commit, page-reported version, or explicit `null` |
| `inventoryStatus` | `complete`, `partial`, or `unknown` for the stated scope |
| `sourceUrls` | Public HTTPS evidence URLs |
| `fingerprintScope` | Exact adapter payload definition and normalization rules |
| `items` | Objects with `id`, `title`, `url`, `contentHash`, and `payload` |
| `limitations` | Explicit omissions, uncertainty, or restrictions |

`id` is an **opaque upstream recommendation ID**, not a corpus GUID unless that
provider actually uses the same GUID. Do not derive identities from title
similarity, a query filter GUID, citation count, or an unstable row number.
Duplicate upstream IDs within an inventory are errors.

The canonical source IDs are `advisor-{cost,security,reliability,performance,operations}-catalog`,
`waf-{cost,security,reliability,performance,operations}-checklist`, `aprl`,
`legacy-review-checklists`, and `azure-waf-service-guides`. Provider category
spellings such as OperationalExcellence map to the internal `operations` slug.
The registry reserves all 13 IDs, including explicitly unsupported scopes.
Source IDs identify providers/categories; **scope and unit still constrain every
denominator**. In particular, `waf-security-checklist` currently inventories checklist
rows, not every Security paragraph.

An item's `payload` contains the source unit's meaningful content. Its
`contentHash` is computed by `item_content_hash(payload)`:

```python
"sha256:" + hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":"),
               ensure_ascii=False, allow_nan=False).encode("utf-8")
).hexdigest()
```

This precisely specified Python JSON encoding is the v1 recipe, not an
unspecified cross-language canonicalization scheme. Non-string object keys,
non-JSON values, and non-finite numbers are rejected. **Adapters exclude fetch
times and generated commit metadata from payloads**; the hash helper hashes
exactly the supplied payload and does not silently remove fields.

WAF fingerprints use `{id, code, recommendation}` from trimmed Markdown table
cells, preserving Markdown content and links but excluding the checkbox.
Repeated links to the same ID in one code cell remain one source row; their
complete code cell is fingerprinted. Different IDs in one cell are an error.
Advisor Cost fingerprints use `{id, title, content}` for each complete published
recommendation section. Structured repository fingerprints use the original
recommendation object; wrapper checklist metadata is excluded. Source YAML dates
become ISO strings. Separate APRL KQL files are explicitly outside the current
APRL recommendation-record fingerprint.

Use the existing snapshot's `contentHash` when assessing a mapping. If
constructing an inventory, call the canonical helper rather than inventing a
different hash recipe.

## Pure-data APIs

Available from `review_checklists.source_coverage`:

```python
item_content_hash(payload: dict) -> str
validate_inventory(inventory: dict) -> None
diff_inventories(previous: dict, current: dict) -> dict
resolve_recommendation_id(identifier: str, recommendations: list[dict]) -> str
coverage_report(inventory: dict, recommendations: list[dict], mappings=None) -> dict
```

Errors raise `SourceCoverageError(ValueError)`. These functions never perform
network requests. Validation checks schema, duplicate IDs, HTTPS evidence, and
payload/hash agreement.

Coverage reads explicit `provenance.upstreamRecommendations` entries. Optional
standalone `mappings` add `corpusId` to those same fields, allowing a draft
assessment file without editing corpus YAML. Canonical and retired alias GUIDs
resolve before mapping; unknown or ambiguous identities and duplicate mappings
for the same canonical/source/upstream-ID tuple are errors.

```json
{
  "corpusId": "<existing canonical or retired corpus GUID>",
  "sourceId": "waf-security-checklist",
  "recommendationId": "SE:01",
  "url": "https://learn.microsoft.com/en-us/azure/well-architected/security/establish-baseline",
  "coverage": "partial",
  "assessedAt": "2026-09-11",
  "upstreamContentHash": "<copy the current inventory item's sha256 hash>",
  "notes": "Draft assessment: state precisely what is represented and what is missing; human review pending."
}
```

The example placeholders are not valid evidence and must not be committed as
real assessments. Full/partial assessments require matching hashes; a different
hash makes them **stale**, never automatically current. Supporting citations do
not establish full or partial coverage, even when their hashes match.

Reports expose:

- `observedCount`, nullable `denominator`, and unique-ID `counts` for `full`,
  `partial`, `stale`, `supporting`, and `unknown`.
- `coveragePercent` for current explicit **full-ID mappings**, and
  `partialPercent` separately. Neither is a human semantic quality score.
- `reason`, `assessmentBasis`, exact scope/unit/dates/version/evidence, per-ID
  states and canonical `corpusIds`, and `referencesOutsideInventory`.

Numeric percentages require a complete, nonempty, dated inventory and at least
one current full/partial assessment. Missing inventories/metadata, supporting-only
references, and entirely stale mappings return `null` percentages with reasons,
not invented zero or 100 percent. A partial assessment may produce zero **full**
mapping percent while displaying its partial percent separately. Unmapped IDs
remain `unknown`; a measured mapping fraction is not proof that the remaining
requirements are absent from corpus prose. Multiple corpus rows referencing one
upstream ID count once. The strongest current state wins per upstream ID.

## Explicit CLI and immutable snapshots

Use the existing application requirements, including PyYAML and jsonschema.
The standalone command works without modifying the main application CLI:

```powershell
python -m review_checklists.source_audit list
python -m review_checklists.source_audit fetch --source waf-security-checklist
python -m review_checklists.source_audit fetch --source advisor-cost-catalog
python -m review_checklists.source_audit validate INVENTORY.json
python -m review_checklists.source_audit diff OLD.json NEW.json
python -m review_checklists.source_audit coverage INVENTORY.json --corpus v2\recos
python -m review_checklists.source_audit coverage INVENTORY.json --corpus v2\recos --mappings DRAFT-ASSESSMENTS.json
python -m unittest review_checklists.tests.test_source_coverage -q
```

Only `fetch` initiates network access. It writes inventory JSON, not corpus
recommendations. No scheduled imports, application startup requests, Azure
authentication, customer data, or remote code execution are involved.

Snapshots are saved under
[`corpus-refresh/source-inventories/`](corpus-refresh/source-inventories/).
Filenames contain the source ID, observation date, revision, and a fingerprint
of the inventory excluding retrieval time. Writes are atomic and exclusive.
An identical same-day observation reuses its existing snapshot without changing
the original retrieval timestamp; changed observations create a new file.
Historical snapshots are never overwritten.

The September 12 offline normalization restores the canonical IDs already used
by corpus mappings. Superseded `azure-waf-*` and `azure-advisor-cost` name copies
are byte-preserved under `source-inventories/deprecated/`, not loaded as duplicate
dashboard cards. Its `index.json` records original hashes, distinct scoped
identities, reasons, and exact promoted pillar-report artifacts. Original pillar
reports are unchanged. Captures with distinct actual retrieval times are retained
without inventing new dates; promotion is not a fresh source check.

The original 372-record `aprl` Azure-resource-only capture is archived with the
explicit scoped identity `aprl-azure-resources`. The 20-record
`aprl-virtual-machines` and 112-record `legacy-revcl-aks` captures are also indexed
historical diagnostics, not whole-source denominators. Original files retain
their historical labels; the archive index explicitly disambiguates them.

`diff` compares only identical source/scope/unit/fingerprint definitions.
Changed IDs come from hash differences in the intersection. A new ID can only
be confirmed against a complete dated prior inventory; a removed ID can only
be confirmed from a complete dated current inventory. Otherwise the confirmed
list is `null`, with separately named observed-only lists and an explicit reason.
Renames are not inferred: an ID replacement is new plus removed until assessed.

## Registry and bounded public adapters

[`source-registry.json`](../source-registry.json) declares named scopes and
provider formats. Supported adapters are:

| Adapter | Boundary and completeness checks |
| --- | --- |
| `learn-waf-checklist` | One entire published English checklist table with recognized stable codes; unknown rows fail |
| `learn-advisor-catalog` | One published catalog page, each recommendation section containing exactly one GUID; unparsed IDs fail |
| `github-records` | One explicitly scoped JSON/YAML file and configured array/ID/title fields |
| `github-tree-records` | Exact prefix/suffix selection in a nontruncated pinned Git tree; file limits produce `partial` |
| `unsupported` | Explicitly named provider/unit gap; fetch fails with its recorded reason |

To support another structured public provider, configure its public repository,
file path or tree selection, record-array path, stable ID/title fields, exact
unit/scope, and fingerprint definition. Unsupported provider formats need a
reviewed adapter and fixtures, not a guessed parser or synthesized IDs.

Repository adapters resolve one commit/tree first, then read **all files at that
commit**, avoiding branch races. Public Learn pages expose a reported Git commit
in their Markdown response; snapshots record that observation and explicitly
state that the private backing repository was not independently retrieved.
Learn captures are not presented as immutable repository fetches.

Reads are anonymous HTTPS only, limited to registered hosts and public DNS
addresses, with 20-second socket timeouts, a 4 MB response limit, and 85-request
budget. Redirects, truncated bodies, pagination headers, truncated Git trees,
duplicate JSON/YAML keys, YAML aliases, unrecognized rows, and empty parser results
fail explicitly. No environment credentials, proxies, or cookies are used.
The tree adapter is capped at 80 recommendation files. Parser/network failures
do not create successful empty inventories.

## Verified baseline, normalization, and remaining gaps

Public snapshots captured on **2026-09-11**:

| Source ID | Verified source unit count |
| --- | ---: |
| `waf-cost-checklist` | 14 |
| `waf-security-checklist` | 12 |
| `waf-reliability-checklist` | 10 |
| `waf-performance-checklist` | 12 |
| `waf-operations-checklist` | 11 |
| `advisor-cost-catalog` | 66 |
| `advisor-performance-catalog` | 150 (published historical recommendations included) |
| `advisor-operations-catalog` | 122 |
| `advisor-reliability-catalog` | 9 observed; partial, no denominator |
| `advisor-security-catalog` | Unknown; no denominator |
| `aprl` | 456 real GUIDs: 393 Active and 63 Disabled |

The five WAF inventories establish a baseline across **all five pillar
checklists: 59 published row IDs**, not 59 paragraphs or every recommendation
in all service guides. Advisor Cost is not all Advisor. These counts are source
denominators, **not coverage percentages or proof of corpus mappings**.

The public legacy WAF JSON currently repeats GUID
`028a71ff-e1ce-415d-b3f0-d5e772d41e36`; capture deliberately fails rather than
silently dropping duplicates or inventing a complete ID inventory. The reserved
`legacy-review-checklists` source therefore has no verified whole-provider
denominator. A historical AKS-only diagnostic snapshot contains 112 GUIDs but is
not a substitute for that denominator.

The canonical `aprl` inventory captures all 456 real GUID records across
`azure-resources`, `azure-specialized-workloads`, and `azure-waf` at commit
`4ed61607223b49e3d0bdd9ce3127ef6e842b5463`; archetype templates and separate KQL
files are outside the unit. All 311 embedded APRL references matched these item
hashes during normalization, including 59 Disabled references. Assigning the
Active-only inventory to `aprl` would incorrectly make those identities absent.
The original Active-only copy is therefore archived as the distinct diagnostic
scope `aprl-active`, not compared with the all-state inventory.

Optional inventory `coverageSelection` declares a payload field, known states,
included states, exact coverage scope and reason. APRL uses
`recommendationMetadataState`, known `Active`/`Disabled`, and includes `Active`.
`coverage_report` defaults to **393 Active** units: `observedCount`, `denominator`,
`counts`, percentages and `items` apply to that selection. `inventoryCount` remains
456, `inventoryScope` preserves the full scope, and `excludedCount`/`excludedItems`
retain all 63 Disabled identities and their assessments, including stale hashes.
Missing or unrecognized state values fail validation rather than disappearing.
`diff_inventories` always compares all 456 units, so state changes remain detectable.
Selection-specific report fields are emitted only when `coverageSelection` is
present; inventories without it retain their historical report structure.
For an explicit all-state diagnostic, remove `coverageSelection` from an in-memory
copy before calling `coverage_report`; do not overwrite the recorded snapshot.

WAF and Advisor Cost/Operations repeat-fetch adapters match their recorded
fingerprints. Performance's complete inventory uses a different section-digest
payload; the generic Advisor parser is not compatible. Reliability's generic
parser failed on an ID-less section, and Security enumeration remains unknown.
These three Advisor adapters and full-scope APRL are explicitly `unsupported`
for repeat fetch until matching reviewed selectors/parsers exist. This does not
invalidate their recorded local evidence, nor claim an automatic check works.
The old single-prefix APRL adapter must not silently replace the full scope.

All-WAF paragraph coverage and `azure-waf-service-guides` also remain unsupported.
Reserved IDs and ordinary
`provenance.sources` citations do not authorize full/partial mapping claims:
matching inventory hashes and explicit semantic assessment are still required.

Snapshot payloads retain public source text for reproducible fingerprints.
Their evidence URLs and revisions preserve attribution; upstream material
remains subject to its original notices and licenses. Retain those references
when redistributing snapshots. Draft mappings and LLM assessments must be
labelled honestly and reviewed independently before making semantic claims.

### Offline next checks and durable handoff

The normalization ledger is
[`source-inventories/deprecated/index.json`](corpus-refresh/source-inventories/deprecated/index.json).
It records every archived original and promoted inventory, with an explicit
`mappingExceptions` list (empty at normalization). Repository integration tests
require every embedded mapping to be registered and hash-matched, or to have a
specific recorded stale/absent exception; unknown references are never ignored.
They also verify archive hashes, exact scope/unit/fingerprint matches, capture
times, unique cards, Active selection, and null partial/unknown percentages.

```powershell
.\.venv\Scripts\python.exe -m unittest review_checklists.tests.test_source_coverage -q
.\.venv\Scripts\python.exe -m review_checklists.source_audit list
.\.venv\Scripts\python.exe -m review_checklists.source_audit validate INVENTORY.json
.\.venv\Scripts\python.exe -m review_checklists.source_audit coverage INVENTORY.json --corpus v2\recos
.\.venv\Scripts\python.exe -m review_checklists.source_audit diff OLD.json NEW.json
```

These commands are offline. A later authorized `fetch` is a separate public
source check; use a supported canonical registry ID, then inspect its diff and
stale mappings. No corpus YAML, historical pillar assessment, customer review,
or query execution is changed by this normalization.
