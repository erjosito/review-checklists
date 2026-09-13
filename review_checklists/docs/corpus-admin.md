# Read-only corpus administration

The corpus administration pages inspect the **public source corpus**, not customer
reviews. They show source content identity, metadata distributions, recorded source
coverage and maintenance evidence. They never create/open a `Review`, connect to a
review database, execute ARG, fetch sources, run an importer, invoke an LLM, or write
corpus/report files.

This is a local prototype, not an authenticated hosted administration service.
The word "administration" describes visibility and diagnostics; there are no
editing, approval, refresh or execution controls.

## Standalone, without a review

Use the application's existing Python 3.11+ environment and
[requirements/setup instructions](../README.md). From the repository root:

```powershell
.\.venv\Scripts\python.exe -m review_checklists.corpus_admin
```

Open `http://127.0.0.1:8767/corpus/`. Stop with Ctrl+C. The standalone server uses
Waitress and binds only to `127.0.0.1`; there is no configurable public bind address.
It does not need `init`, `--review`, an Azure login, or a database service.

Explicit paths and another port are supported:

```powershell
.\.venv\Scripts\python.exe -m review_checklists.corpus_admin `
    --corpus v2\recos `
    --reports review_checklists\docs\corpus-refresh `
    --port 8768
```

The defaults are repository-relative source locations resolved by the package,
not the working directory's review database. Only point `--reports` at a directory
of approved **public maintenance artifacts**, never an engagement-data directory.

## Blueprint integration contract

The normal review app already registers this blueprint. Use **Corpus
administration** in its header, or open `/corpus/` on the same localhost port.
These pages inspect the working public corpus, not the review's pinned bundle.
The standalone command above remains available when no review exists.

The owning application can register the blueprint without changing the review
model or initializing a corpus snapshot at startup:

```python
from review_checklists.corpus_admin import create_corpus_blueprint

app.register_blueprint(
    create_corpus_blueprint(corpus_path, reports_path),
    url_prefix="/corpus",
)
```

Use `url_for("corpus_admin.index")` for a header/navigation link. The blueprint
has its own `corpus_base.html` and local stylesheet; it does not extend the
customer-review template or require review metadata. The standalone factory is
`review_checklists.corpus_admin.create_app(corpus_path, reports_path)`.

| GET route under `/corpus` | Endpoint suffix | Purpose |
| --- | --- | --- |
| `/` | `index` | Corpus hash and metadata overview |
| `/recommendations` | `recommendations` | Canonical recommendation filters and pagination |
| `/recommendations/<identity>` | `recommendation` | Canonical or retired-alias ID drilldown |
| `/sources` | `sources` | Recorded upstream coverage, origins and supporting references |
| `/sources/<source_id>` | `source` | Source scope, denominator, reconciliation and inventory history |
| `/history` | `history` | Application events, aggregate/audit snapshots and technical deferrals |
| `/reports/<name>` | `report` | Allowlisted public JSON/Markdown download as plain text |
| `/assets/corpus.css` | `static` | Local stylesheet |

All endpoint names begin with `corpus_admin.`. GET/HEAD and Flask's automatic
OPTIONS are the only supported methods. Unknown records return 404; invalid
drilldown filters return 400. Invalid/unavailable corpus data returns an explicit
503 page rather than successful-looking zero statistics.

## Corpus identity and distributions

The working YAML corpus is loaded with the shared **strict current-schema**
validator. No compatibility enrichment silently repairs invalid source files.
The content hash uses the same canonical JSON representation as versioned bundle
generation: recommendations sorted by canonical ID, excluding the runtime-only
`corpus_file`. Working YAML has no invented release version.

Counts are computed from the loaded source, never hardcoded from a refresh report:

- Canonical records and retired aliases are separate populations.
- Service classification distinguishes explicit metadata, resource-type inference
  through the existing service dictionary, and missing classification.
- Service/pillar cells count each canonical record once per service. Multi-service
  rows overlap, so adding service totals does not yield a corpus total.
- Available primary ARG queries, recorded validation dates, automation status and
  query-result semantics are distinct. A validation date is metadata, not an ARG
  check performed by this dashboard.
- Original canonical source families, preserved alias origins and supporting
  provenance references remain separate.
- Missing human-review dates, references/access dates, upstream revisions,
  service metadata and query semantics have drilldowns. No arbitrary freshness
  threshold, synthetic quality score or automatic compliance grade is applied.

Recommendation filters accept one value each: `search`, `service`, `waf`,
`origin`, `quality`, `arg`, and `reference`. They combine with AND. Search includes
canonical and alias IDs/names. `arg` accepts `available`, `validated`,
`unvalidated`, or `missing`; `service=none` selects records without explicit or
inferred service metadata. The page form supplies the other supported values.
Lists use 50 rows per page and preserve filters in navigation links.

## Upstream coverage is a dated reconciliation

Coverage answers a specific question such as **"How many identified recommendations
from this source are fully represented, for this scope and unit as of this date?"**
It does not measure generic service breadth, source URL count, or all Azure guidance.
For example, a WAF checklist's control rows form a bounded inventory, not a
denominator for every recommendation on Microsoft Learn.

The UI uses the pure functions in [`source_coverage.py`](../source_coverage.py):
`validate_inventory`, `coverage_report`, and `diff_inventories`. It reads local
JSON files under `reports_path / "source-inventories"` that satisfy the
[inventory schema](../schema/source-inventory.schema.json). Source discovery is
not limited to Advisor or to a built-in list of source families.

Inventories are grouped by their declared `sourceId`, not by guessed titles,
domains, service names, or filename equality. Versioned artifact names such as
`source-id--date--revision--hash.json` are supported. Filenames are not accepted
as arbitrary paths from a request.

The UI reads the central [source registry](../source-registry.json) using the
maintenance tooling's read-only `load_registry` helper. It never invokes that
tooling's fetch functions. Registry scope, unit and fingerprint definitions must
agree with the selected inventory. Unknown source IDs are explicit diagnostics,
not uncovered counts or duplicate source rows. No source-name aliases are guessed.
Owners normalize references and inventories through a recorded maintenance change;
the dashboard never rewrites them.

Canonical registered pillar scopes use `waf-<pillar>-checklist` and
`advisor-<pillar>-catalog`. Other sources retain their actual scoped registry ID,
such as `aprl-virtual-machines`; a VM subset is not whole-APRL coverage. Registered
but unmeasured or unsupported scopes remain visible with their recorded reason
and no percentage.

For each source, identical copied snapshots are deduplicated. The newest
`asOf`, then `retrievedAt`, selects the current observation; undated snapshots
sort before dated ones. The previous distinct snapshot supplies the comparison.
Different scope/unit/fingerprint definitions or conflicting snapshots with the
same observation date/time are visible errors requiring reconciliation, not
opportunities to choose whichever snapshot produces higher coverage.

Mappings come from each canonical recommendation's explicit
`provenance.upstreamRecommendations` entries in the
[corpus contract](corpus-contract.md). Matching source IDs and upstream
recommendation IDs matter: a similar source name or an ordinary supporting URL
does not create a mapping.

The pure reconciler counts unique upstream IDs, not the number of corpus rows
or aliases pointing to them. Full/partial assessments require a matching
`upstreamContentHash`; stale hashes, supporting citations and unknown entries
do not enter the full-coverage numerator. A complete, dated, nonempty inventory
is required for a denominator. Without current full/partial ID assessments,
coverage remains **Not measured**, even when the denominator is known.
Missing, partial, undated or empty inventories never imply 0% or 100%.

Source details show the complete scope/unit/date, numerator and denominator,
partial count, limitations and underlying assessments. `state=full`, `partial`,
`stale`, `supporting`, or `unknown` filters the paginated drilldown **without
changing source-wide percentage math**.

When comparable previous evidence exists, the page shows recorded new, changed
and removed upstream IDs; removed entries retain their historical titles/hashes.
Absence from an incomplete inventory or absence of a corpus mapping does not
prove removal. References outside the inventory are reported separately.

This UI does not assess semantic equivalence, assert human approval, or refresh
the recorded upstream observations. Source-auditor tooling is a separate,
explicitly authorized maintenance workflow.

## Maintenance events versus aggregate snapshots

History is interpreted from known JSON report contracts, not Markdown scraping
or filename timestamps. Recognized refresh manifests are
`<pillar>-refresh-manifest.json` for Cost, Security, Reliability, Performance and
Operations, with matching `artifactSchema: "<pillar>-refresh-manifest/1"`.
Applied entries must have `status: applied`, explicit `updates`/`additions`
arrays, and any recorded summary counts must agree with those arrays.

The original non-Cost and later Cost merge transactions come from
`alias-migration.json` and `cost-alias-migration.json` respectively. Their
`mergeResult` before/after/retired counts are displayed as transaction facts.
`finalStageSummary` is an aggregate snapshot, not another application event.
Other recognized duplicate audits, proposal manifests, research and normalization
reports remain separate snapshots. No combined event total is fabricated from
overlapping artifacts.

The applied `service-normalization.json` is a mechanical event with checked
inventory/change counts, not a claim that guidance was refreshed. The
`followup-2026-09-13-application.json` adapter verifies its recorded file hashes,
canonical/alias deltas, amendment counts and merge accounting. Its three
research proposals and the standalone merge result remain snapshots, not extra
application events. The public audit redaction record is also available.

The finalized `full-refresh-2026-09-11/operations-manifest.json` has a separate,
explicit adapter because it predates that generic manifest envelope. Its
`records` outcomes and `additions` are checked against `baselineCount`, `outcomes`
and `additionsCount`. Only `updated` records and additions count as changes;
`supportedunchanged` and `needsmanualreview` remain separate outcomes. Supporting
baseline, source-inventory and source-coverage artifacts are not additional events.
The allowlisted download token `full-refresh-2026-09-11-operations-manifest.json`
maps to that fixed public subdirectory; requests cannot supply arbitrary paths.

Likewise, the existing `full-refresh-2026-09-11/security-manifest.json` uses its
own `security-refresh-manifest/1` adapter: `records`, `counts`, `date`, `scope`
and per-record `guidanceChanged`/`changedFields` evidence. It is one bounded
implemented-draft event. Guidance changes, provenance-only changes, additions
and unverified/manual-review outcomes remain separate; source-verified records
are not all labelled guidance updates. Security mapping proposals and supporting
baseline/inventory/query-audit artifacts are not extra application events.
Its fixed download token is `full-refresh-2026-09-11-security-manifest.json`.

The custom `full-refresh-2026-09-11/reliability-manifest.json` adapter reconciles
`entries` with the exact frozen `baselineIds` and `baselineCount`, and checks
`summary` outcomes plus `additionCount` against those records. Only `updated`
entries and additions are refresh changes; supported-unchanged and manual-review
entries remain separate. Source-coverage percentages and mapping counts are not
refresh counts. Its download token is
`full-refresh-2026-09-11-reliability-manifest.json`.

The original recorded technical-deferral list is
`alias-migration.json / finalTechnicalDeferrals`. When present, the explicit
September 13 duplicate adjudication supersedes it: rejected distinct requirements
are not pending duplicates, and mergeable groups remain pending until a matching
separate application is recorded. The current application leaves 14 technical
deferrals. Earlier candidate lists are not added to that total. An absent list
means **Not recorded**, not zero unresolved issues. These remain dated recorded
decisions, not a fresh semantic audit performed by the UI.

See the [public maintenance reports](corpus-refresh/README.md). A new report
schema needs an explicit history adapter before it can affect event statistics.
Invalid recognized reports remain visible as errors alongside valid records.
Neither history nor source errors silently alter the corpus.

## Read-only and data-handling boundaries

The validated corpus cache holds one snapshot per blueprint. Every corpus page
checks the source-file set, modification/change timestamps, sizes and file
identities; changes trigger a full strict reload. Files changing during loading
produce a retryable error rather than a mixed snapshot. Invalid edits discard
cached success instead of serving stale data as current. History/inventory pages
read their recorded files on request; they do not initiate a background poller.

Source load limits are 50,000 files and 2 MiB per recommendation file. Reports
and inventory files are limited to 16 MiB each; at most 200 inventory files are
processed. Limits produce visible errors, not truncation presented as complete
coverage. Corpus/inventory symlinks and report links escaping the configured
public directory are rejected.

All rendered strings are escaped. Only explicit HTTP(S) source URLs become
clickable; embedded Markdown or source/report HTML is not rendered as trusted HTML.
Public report downloads use an explicit filename allowlist, `text/plain`,
attachment disposition and `nosniff`, with no arbitrary file-browser endpoint.
The app uses local assets and restrictive CSP/cache headers; no third-party
scripts, stylesheets or automatic URL previews are loaded.

Loopback binding is not user authentication. Do not expose this prototype through
a public proxy or substitute a directory of private customer artifacts.

## Validation

Run the isolated administration tests:

```powershell
.\.venv\Scripts\python.exe -m unittest review_checklists.tests.test_corpus_admin -v
```

Fixtures use temporary corpora/reports rather than `.reviews`. Coverage includes
strict/lazy loading, hash/cache invalidation, canonical versus alias counts,
service/pillar intersections, source-wide denominator math, stale/partial/unknown
states, inventory histories, escaping, safe downloads, GET-only routes and
no database/network access during page rendering. Standalone serving is checked
separately from source fetching. Live Azure or source-auditor execution is not
part of this test suite.
