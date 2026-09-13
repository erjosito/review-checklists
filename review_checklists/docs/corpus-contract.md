# Recommendation corpus contract

Individual YAML files remain the authoring source of truth under `v2/recos`.
The directory name is historical; recommendation `schemaVersion: 1` is the first
explicit version of the strengthened contract. The single authoritative schema is
`v2/schema/recommendation.schema.json`. `scripts/modules/cl_corpus.py` supplies
shared parsing, enrichment and validation for the app and authoring tools.

## Identity and compatibility

Every recommendation has a required top-level `id` (canonical lowercase UUID).
Existing GUIDs are reused, never regenerated during metadata migration.
Legacy `labels.guid` / `guid`, when present, must agree with `id`.

A confirmed duplicate merge keeps one existing canonical ID and records the retired
IDs/names in `aliases`. Canonical IDs, alias IDs, canonical names and alias names
must not collide across the corpus. Alias entries can retain the original source
and corpus-relative filename for provenance. Related-but-different requirements
must not be merged merely because their wording is similar.

Saved reviews remain pinned to their recommendation snapshots unless the reviewer
explicitly previews and applies a [review refresh](review-refresh.md). Refresh
preserves statuses/comments/evidence and retains removed or retired IDs as separate
records; assessments are never merged, renamed or deleted. Newly created reviews
contain the canonical recommendation and resolve retired GUIDs to it.
Editing or running a query through an alias targets that canonical item once.
Legacy checklist name/GUID and GUID-label selectors also resolve aliases. Source
selectors recognize explicitly retained alias sources; this preserves membership
when equivalent requirements from different source families are merged.

## Required metadata

```yaml
schemaVersion: 1
id: 00000000-0000-0000-0000-000000000001
name: curated-ExampleRecommendation
title: Example recommendation requiring author review
severity: 1
waf: Cost
source:
  type: curated
  url: https://learn.microsoft.com/azure/well-architected/cost-optimization/
resourceTypes: []
services: []
automation:
  status: unknown
  validatedAt: null
provenance:
  upstreamRevision: null
  lastReviewed: null
  sources: []
```

`services` is an explicit classification, not a claim inferred from a generic
resource type. An empty array means no explicit classification is recorded.
The app retains its resource-type fallback for compatibility and labels that
fallback as inferred on the detail page. Prefer the existing service dictionary's
friendly `displayName` labels when authoring classifications. Legacy service keys
and aliases remain accepted. Shared ARM types retain technical fallback labels;
they do not imply a particular service. See [service catalogue](service-catalog.md)
for the many-to-many mapping, normalization audit and unresolved type spellings.

`automation.status` distinguishes:

| Status | Meaning |
| --- | --- |
| `unknown` | No supported determination has been recorded |
| `manual` | Author has explicitly identified a human/manual assessment |
| `candidate` | Potential automation identified, but no ARG query is available |
| `query_available` | Nonempty ARG text exists; this does **not** mean it is correct or validated |

Available queries must declare `resultSemantics`: `unknown`, `violations`,
`inventory`, or `compliance`. `compliance` also requires `complianceColumn`.
Do not classify an inventory query as violations merely because it might reveal
optimization candidates. `validatedAt` remains null until an actual query
validation is recorded; documentation review is not live ARG validation.

`provenance.upstreamRevision` and `lastReviewed` can be null. Existing import
timestamps are not reinterpreted as review dates. `provenance.sources` records
public URLs with optional title, access date and upstream revision. A source
access date is not a claim of human approval or query execution.

### Upstream recommendation identity and coverage

`source` remains the original import/authoring origin. A recommendation can
additionally map to several independently identified upstream recommendations
through optional `provenance.upstreamRecommendations` entries:

| Field | Meaning |
| --- | --- |
| `sourceId` | Stable source-registry identifier, including the documented inventory scope |
| `recommendationId` | Real upstream recommendation ID or other explicitly documented upstream identifier |
| `url` | Public evidence URL for the upstream requirement |
| `coverage` | `full`, `partial`, or `supporting`; a citation alone is not full coverage |
| `assessedAt` | Date of the mapping assessment, not human approval or live query validation |
| `upstreamContentHash` | Exact upstream inventory item's `sha256:` fingerprint; required for full/partial mappings |
| `notes` | Rationale for the mapping and any applicability limitations |

A source/ID pair can occur only once per corpus recommendation. Several corpus
recommendations may reference the same upstream ID; coverage counts that upstream
unit once, not once per reference. A recommendation can reference multiple sources
without changing its canonical ID or replacing its original `source`.

Programmatic comparison detects newly published IDs, removed IDs, and changed
upstream fingerprints. It cannot establish semantic equivalence on its own.
Changed fingerprints make previous mappings stale until reassessed; supporting
citations do not count as fully implemented recommendations.

A percentage needs a complete, nonempty, dated inventory with an explicit unit.
Coverage of WAF checklist rows, for example, is not coverage of every paragraph
in all WAF guidance. Missing or partial inventories are **not measured**, not
zero or 100 percent. Historical reports remain tied to their dated snapshots.

Safe parsing rejects duplicate YAML/JSON keys, unsupported value types and
non-finite numbers. Schema validation checks types, dates, UUIDs, URLs and
automation/query consistency. Corpus-wide validation checks identity collisions.
It does not prove the truth of a recommendation or the safety/correctness of KQL.

## Migration

```powershell
.\.venv\Scripts\python.exe -m review_checklists corpus migrate
.\.venv\Scripts\python.exe -m review_checklists corpus migrate --write
.\.venv\Scripts\python.exe -m review_checklists corpus validate
```

Migration first validates the entire proposed corpus. The default is a dry run;
`--write` applies metadata changes. Original titles, descriptions, queries and
GUIDs are preserved. Metadata is appended without reformatting the original body,
including YAML block scalars and explicit document-end markers. A transient
machine-local `filepath` field is removed rather than distributed.

Migration only infers facts from existing data: nonempty ARG means
`query_available` with unknown semantics; an explicit old `automatable` boolean
maps to `candidate`/`manual` when no query exists. Missing automation information
remains `unknown`. No service specialization, review dates, source commit IDs or
query meanings are fabricated.

Two pre-existing documentation URLs needed whitespace-only normalization before
the strict full-corpus merge gate could pass. This is recorded separately in
`corpus-refresh/url-normalization.json`, not described as an inferred content
refresh or a source-validation date.

The loader still accepts legacy unversioned YAML through this compatibility
enrichment, without rewriting the source. CI validation and bundle builds require
the explicit current schema instead, so newly authored files cannot silently skip
the migration. Partially migrated or conflicting authored fields are rejected
for explicit correction.

## Distribution

```powershell
.\.venv\Scripts\python.exe -m review_checklists corpus build `
    --version "2026.09.11-draft" --output dist\catalog.json
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\from-bundle.sqlite3 `
    init --bundle dist\catalog.json
```

Bundles contain `schemaVersion`, `corpusVersion`, `contentHash`, and a
`recommendations` array sorted by canonical ID. The hash covers canonical JSON of
that array; runtime-only source paths are excluded. Identical inputs and version
produce byte-identical bundles, with no build timestamp or random IDs.

The loader checks the bundle envelope, every recommendation, identity uniqueness
and the content hash. A hash detects corruption; it is not a publisher signature.
The version/hash are pinned in new review metadata. A checklist can additionally
select a subset of a bundle without changing the recorded bundle identity.
Publishing or loading a new corpus does not update existing reviews. The explicit
[review-refresh workflow](review-refresh.md) previews a versioned bundle, creates
a consistent backup before apply, and records per-item origins and history.
Assessment-relevant guidance changes flag reviewed checks for reassessment
without changing their saved status.

Bundles belong in generated output (`dist` is ignored), not among source YAMLs.
Build/export commands refuse to overwrite existing files. GitHub workflow
artifacts can distribute a bundle without committing a second editable corpus.

## Confirmed duplicate merge workflow

A proposed JSON manifest contains a `groups` array. Each group identifies an
existing `canonicalId`, one or more existing `retiredIds`, and a nonempty `reason`.
If different descriptions need consolidation, include an explicit reconciled
`description`; never silently discard one.

```powershell
.\.venv\Scripts\python.exe -m review_checklists corpus merge `
    --manifest proposed-merges.json
.\.venv\Scripts\python.exe -m review_checklists corpus merge `
    --manifest proposed-merges.json --write
```

The first command is a dry run. Validation rejects malformed manifests,
identity collisions and unresolved scope/constraint, automation, query or
provenance conflicts. Before writing, the tool checks that source bytes still
match its preflight; replacements are staged and recoverable write failures
trigger rollback. This is not a database transaction across files or a guarantee
against an interrupted process/machine failure. Inspect the worktree after any
interruption before retrying.

Compatible `provenance.upstreamRecommendations` from every member survive on
the canonical recommendation. Identical source/ID mappings are deduplicated;
different sources or upstream IDs are retained. Conflicting evidence for the
same source/ID (including coverage, hash, date or rationale) blocks the merge
for explicit reconciliation, rather than silently choosing the survivor's mapping.

Keep the application result, alias mapping, content hashes and checklist
membership comparison in a durable report. Applied manifests are audit records,
not commands to rerun: their retired IDs no longer exist as independent files.
Unresolved overlaps remain separate and have explicit deferral reasons.

## Refresh and review policy

LLM-assisted refreshes propose curated edits backed by public sources. Deterministic
parsing/schema/identity checks and artifact assembly remain mandatory. Deprecated
mechanical importers are manual fallbacks, not scheduled sources of autonomous
corpus changes. Semantic duplicate detection is a review aid, not proof that two
requirements are interchangeable.

Keep unsupported or uncertain findings visible in the refresh/audit report.
Do not invent ARG queries when the rule depends on unavailable utilization,
billing, licensing or business context. Do not infer compliance from zero rows.

The [Cost source inventory](corpus-refresh/cost-sources.md) documents the bounded
reference set, actual coverage and remaining gaps. The
[Cost refresh report](corpus-refresh/cost-refresh-report.md) separates applied
guidance from supplemental query research. Machine-readable audit and migration
reports in that directory preserve the evidence for future refresh sessions.
The [initial refresh summary](corpus-refresh/README.md) explains that stage's
counts and local draft bundle. The
[September 13 follow-up](corpus-refresh/followup-2026-09-13.md) records later
source-backed amendments and merges separately.

Later amendments must not rewrite historical outcomes or hashes. The applied
follow-up ledger captures exact before/after file bytes, hashes, identity counts,
source-report hashes and checklist membership/placement deltas. The read-only
`corpus_history` verifier refuses stale or inconsistent after-state evidence
before reversing a declared change. Historical regression tests reconstruct
their recorded stage through that chain; separate tests validate current
guidance, identities and review-refresh behavior. A future change needs a new
ledger and corresponding replay boundary, not an edited past report.

The repository's `.gitattributes` disables automatic line-ending conversion for
the authoring recommendations, service catalogue and refresh reports. Their
byte-level evidence must survive Windows and Linux checkouts unchanged; do not
bulk-normalize these files or regenerate historical hashes.
