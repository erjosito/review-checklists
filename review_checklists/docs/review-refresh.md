# Refreshing a saved review

Refresh is a local, preview-first operation against a **versioned JSON bundle**.
It never edits source YAML or runs Azure queries. Bundle versions are opaque
labels, not semantic versions; content hashes and the exact preview token matter.
Hashes detect corruption, not publisher authenticity.

```powershell
python -m review_checklists --review .reviews\review.sqlite3 refresh --bundle dist\catalog.json

# Copy the token from that JSON preview. Repeat the same options when applying.
python -m review_checklists --review .reviews\review.sqlite3 refresh --bundle dist\catalog.json `
    --apply --token "TOKEN-FROM-PREVIEW"
```

Preview does not write the review, create extension tables, or make a backup.
Apply revalidates the bundle and recomputes the entire plan while holding SQLite's
writer lock. Changes to assessments, evidence, review metadata, prior refresh
state, the target, or options invalidate the token. Preview again after a conflict.
Submitting an edited plan cannot alter the operation: only the token and options
are accepted.

## Preservation and scope

Existing canonical IDs receive new recommendation snapshots, preserving their
status, comments, evidence, and existing area/subarea placement. Semantic changes
to title, description, resource/service applicability, constraints, severity,
pillar, query text or result meaning mark reviewed checks **Needs reassessment**.
Source/access-date/provenance-only edits do not. Known service-name aliases,
resource-type casing, and ordering or duplicate labels within those scope lists
are compared canonically and do not trigger reassessment by themselves. Actual
service or resource-type scope additions, removals, or changes still do; explicit
service scope is not replaced by resource-type inference for this comparison.
The flag is separate from status.
Comments alone never acknowledge it. A deliberate status change acknowledges it;
to retain the status after reviewing the new guidance, explicitly confirm:

```powershell
python -m review_checklists --review .reviews\review.sqlite3 update RECOMMENDATION-ID `
    --confirm-current-assessment --revision 3
```

Removed checks stay with their original guidance as **no-longer-current**.
Retired IDs now aliased to another recommendation stay as distinct **superseded**
checks with their canonical relationship. Their assessments are never merged.
The preview reports consolidation groups whenever multiple retained review items
map to one canonical ID.

New checks are excluded by default. Use `--add-new` on **both** preview and apply
to add selected canonical IDs as **Not reviewed**. New CLI `init` captures either
all-corpus scope or the complete checklist definition (not a path that may change).
Direct `Review.create` calls without scope, and older reviews, have unknown scope.
Unknown scope allows existing-only refresh; additions require an explicit scope:

```powershell
python -m review_checklists --review .reviews\review.sqlite3 refresh `
    --bundle dist\catalog.json --add-new --checklist v2\checklists\example.yaml
# Or use --all-corpus instead of --checklist.
```

An explicit scope is persisted by apply for future additions. It does not drop
existing checks or prevent the full target bundle from updating their IDs.
Existing placements remain unchanged; newly added checks use the chosen checklist
placements. An empty target checklist selection is valid and adds nothing.

## Persistence, backup, and compatibility

Before any mutation, apply creates a consistent SQLite backup alongside the review:
`review.sqlite3.before-refresh-<uuid>.sqlite3`. It uses SQLite's backup API, not a
copy of a potentially live database file. The backup and the review contain private
assessment/evidence data; protect both the same way. No backups are uploaded.

All schema, item, state, metadata, and history changes commit in one transaction.
Backup failure aborts without mutation. Storage/transaction failures roll back and
report the backup path when available; a successfully created backup may remain
after a failed apply. Close review clients before manually restoring a backup.
An identical target/options with no changes creates no backup or history and
does not increment revisions. Changed retained items increment their revision,
so stale assessment forms cannot silently save over the refresh.

New reviews and applied refreshes use SQLite schema **2**, with additive
`refresh_item_state` and `refresh_history` tables. Schema-1 reviews remain readable
without migration on open or preview. Older schema-1-only binaries reject schema 2
instead of silently ignoring reassessment state. Opening a review never creates
extension tables. An old, already-open process must be restarted with current code.

Original review identity, name, description, creation metadata, unknown metadata
keys, and initial corpus identity remain intact. `corpus_sha256` is the original
snapshot hash; `baseline_snapshot_hash` preserves it explicitly after refresh.
`reviewed_snapshot_hash` hashes actual currently stored recommendations, including
retained legacy guidance. `last_applied_source` identifies the latest input bundle,
**not** the origin of every item. Each item's `refresh_state.source` identifies its
snapshot source. History retains source/target identity, before/after guidance,
per-item relevance flags, decisions, and the pre-apply fingerprint. JSON exports
include this state and history rather than claiming the whole review is current.

## Shared API / UI contract

`review_checklists.refresh` exposes:

```python
plan_refresh(review, bundle, *, add_new=False, scope=None)
apply_refresh(review, bundle, *, token, add_new=False, scope=None)
```

Both accept a dictionary from `catalog.read_bundle`; both defensively revalidate
schema, identities/aliases, and hash. `scope` is `{"kind": "all"}`,
`{"kind": "unknown"}`, or `{"kind": "checklist", "definition": {...}}`.
Omitted scope uses saved scope.

Plan fields: `plan_version`, `review_id`, `review_fingerprint`, `source`, `target`,
`counts`, `changes`, `consolidations`, `scope`, `has_changes`, and `token`.
Changes include `id`, `action`, `canonical_id`, `assessment_relevant`,
`needs_reassessment`, `changed_fields`, `before`, `after`, `previous_state`,
and `state`. Counts include unchanged/updated/removed/superseded/added and the
total still needing reassessment (including flags already present).
Apply returns `applied`, `plan`, `backup_path`, and `refresh_id`.
`RefreshConflict` derives from `ReviewError`; map it to an explicit stale-preview
conflict, not a successful response.

`Review.get/items` expose `refresh_state`: `currency`, `canonical_id`,
`needs_reassessment`, and `source`. `Review.refresh_history()` returns the durable
records, and `Review.report()` includes `refresh_history`. Schema-1 defaults
require no writes. `Review.update(..., confirm_current_assessment=True)` explicitly
acknowledges the current snapshot, subject to the existing revision check.
Status changes also acknowledge; comment-only autosave does not.

The localhost UI implements this flow at `/review-refresh`, with POST endpoints
`/review-refresh/preview` and `/review-refresh/apply`, and GET history at
`/review-refresh/history`. The existing `/refresh` route only reloads the
assessment list.

Bundle uploads are limited to 12 MiB, checklist YAML/JSON to 256 KiB, and preview
requests to 16 MiB. Ordinary form limits remain unchanged at 256 KiB. Checklist
YAML aliases are rejected. Validation is local; no sources or Azure services are
queried. A preview retains the bundle, options, and token only on the server;
the apply form contains an opaque handle and CSRF token, not editable decisions.
The handle is browser-session-bound, expires after 15 minutes, and is consumed
before calling apply. Concurrent or repeated submissions cannot replay it.

The in-memory cache allows two pending previews per session, eight per server,
and a conservative 64 MiB serialized bundle/plan budget. Expired entries are
discarded on the next preview/apply interaction; restarting the server clears
all previews. Capacity, authentication, expiry, stale-review, and storage errors
are explicit. A rejected stale/apply operation requires a fresh preview.

The list, detail, history, and HTML/JSON exports distinguish saved assessments
from current guidance, including per-item origins, retained legacy records and
reassessment flags. The detail form provides explicit unchanged-status
confirmation. Existing inline-draft navigation protection covers refresh/history
links; no-JavaScript users must save each row before navigating.
