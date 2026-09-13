# Working in this repository

## Project map

- `review_checklists/`: the current local-first Python CLI and localhost web app.
  The package/command name is independent of branch names and release versions.
- `v2/recos/`: authoritative, individually authored YAML recommendations. The
  directory name is historical; do not rename it just because a release changes.
- `v2/schema/recommendation.schema.json`: the single authoritative recommendation
  schema. `scripts/modules/cl_corpus.py` supplies shared parsing and validation.
- `v2/checklists/`: selectors assembling recommendations into checklists.
- `scripts/` and `.github/`: legacy adapters, validators, renderers and workflows.
- `checklists/`, `spreadsheet/`, `workbooks/`, and the older web app: legacy
  surfaces. Avoid unrelated rewrites or manual edits to generated output.
- `docs/legacy-v1.md`: preserved spreadsheet instructions, not the current app's
  setup guide. Implementation archival requires a separate dependency review.

Start with `review_checklists/README.md`,
`review_checklists/docs/corpus-contract.md`, and the decision log at
`v2/docs/next-generation-design.md`. The provider/MCP documents describe future
contracts, not implemented integrations.

## Working practices

- Inspect the worktree and relevant implementation before editing. Preserve
  unrelated changes and coordinate file ownership when working in parallel.
- Make complete, focused changes across affected CLI, UI, persistence, exports,
  tests and documentation. Reuse shared operations rather than duplicate logic.
- Do not commit or push unless requested. Do not include review databases,
  credentials, customer data, virtual environments or generated release bundles.
- Surface invalid input, failed saves, missing dependencies and partial results
  explicitly. Do not turn failures into successful-looking empty results.
- Python 3.11+ is supported. Examples below use PowerShell and Windows paths;
  the application is also tested on Linux.

## Refreshing recommendation content

Use the durable refresh records, not an agent's conversation history:

- [Cost sources and coverage](review_checklists/docs/corpus-refresh/cost-sources.md)
  identifies the primary references and limits of the bounded Cost refresh.
- Machine-readable `cost-*.json` files in the same directory preserve the
  source-backed changes and query variants for subsequent comparisons.
- `duplicate-audit.json`, `non-cost-merge-manifest.json`, and
  `alias-migration.json` distinguish identified duplicates, intended merges,
  actual migrations and deferred decisions.
- `post-cost-duplicate-review.json` and `cost-alias-migration.json` record the
  post-refresh Cost reconciliation and applied aliases separately from the
  original content-refresh manifest.
- `full-refresh-2026-09-11/README.md` and its frozen slice ledgers account for the
  later all-pillar/APRL pass. Ownership is by baseline GUID, not by a record's
  newly assigned WAF pillar. Historical and normalization stages remain separate.
- `followup-2026-09-13.md` and its application ledger record subsequent
  classification/Key Vault amendments and two storage merges. The three proposal
  reports are frozen research, not additional application events. Preserve their
  hashes and use a new stage for later changes; historical tests rewind exact
  declared file changes before replaying earlier normalization.

For each refresh:

1. Read the applicable source/coverage report and existing recommendations,
   including aliases. Revisit primary Microsoft Learn, Azure Advisor, WAF and
   relevant FinOps documentation; do not assume an old access date proves current
   guidance. Search results alone are not source verification.
2. Prefer an update to an existing GUID over a new overlapping recommendation.
   Compare technical requirement, service/resource applicability, WAF pillar,
   severity and query meaning, not only title similarity.
3. Record the source URL, title and actual access date, what changed and why.
   Distinguish additions, updates, untouched areas, rejected proposals and gaps.
   Never describe a bounded pass as exhaustive coverage.
4. Preserve existing canonical IDs/names and legacy GUIDs. New recommendations
   need stable unique IDs and appropriate provenance, normally `source.type:
   curated`. Use established service classifications; do not invent specificity.
5. Do not equate a source fetch or an LLM edit with human approval, an upstream
   commit, or live query validation. Unknown `upstreamRevision`, `lastReviewed`
   and `validatedAt` values remain null.
6. Validate the corpus and build the deterministic bundle. Review the semantic
   diff and retain a durable source/change/coverage report for human review.
   Schema success alone does not prove a recommendation is technically correct.

Record actual upstream IDs in optional `provenance.upstreamRecommendations`
when recommendation-level source identity is available. Use the source registry's
exact identifier and inventory item hash; do not invent remote GUIDs, substitute a
corpus hash for an upstream hash, or claim full coverage from a link alone.
Full/partial mappings need an explicit rationale and hash-matched upstream
evidence. Count unique upstream items against a complete dated inventory; unknown
denominators and changed upstream content must remain visible. Source inventory
comparison is read-only discovery, not authorization to import changes.

Scheduled APRL, AKS-checklist and WAF service-guide imports are deprecated.
Their manual fallback paths must not bypass validation and human review.
Deterministic parsing, validation, assembly and rendering remain required; an
LLM-assisted refresh is a proposal workflow, not autonomous publication.

### Queries and duplicate merges

- Query availability is not validity. Use explicit `automation.status`,
  `resultSemantics` and validation metadata per the corpus contract.
- Inventory, optimization candidates and Advisor findings are not automatic
  compliance verdicts or proven savings. Zero rows do not establish compliance.
- Do not invent ARG evidence for utilization, billing, licensing or business
  facts that ARG does not provide. Explain required supplementary evidence.
- The app executes one primary `queries.arg` per recommendation. Retain additional
  researched variants and caveats in the refresh report; do not imply the UI
  executes them or add undocumented schema fields.
- Merge only confirmed equivalent requirements. Keep the survivor's existing ID
  and preserve retired IDs, names, source and labels as aliases. Use the merge
  manifest/dry-run workflow; do not delete recommendations based on similarity.
- Conflicting scopes, constraints, severity, WAF classifications, executable KQL
  or provenance require explicit reconciliation or deferral, not silent loss.
  Check old checklist selectors and area/subarea memberships after merging.

## Review state and browser behavior

- Reviews are pinned SQLite snapshots. A corpus refresh must not silently alter
  existing assessments, comments, evidence or recommendation snapshots.
- `--review` is a global option placed **before** the subcommand. Its filename is
  independent of the friendly review name. The default is `.reviews\review.sqlite3`.
  Never rename or modify a user's active review database as part of development.
- Review-wide name/description metadata differs from per-recommendation
  status/comments. Preserve unknown metadata keys and existing review compatibility.
- Statuses are `Not reviewed`, `Compliant`, `Non-compliant`, `Not applicable`.
  They are reviewer decisions, including offline assessments. Query execution
  must never overwrite them. Preserve optimistic revision checks on edits.
- Keep save state and errors visible. Autosave must preserve in-flight edits and
  stale-edit protection; it must not discard drafts or report success prematurely.
- Pagination is optional and disabled by default. Multi-select filters use OR
  within a group and AND across groups. The explicit query-run limit remains
  50 selected checks, independently of how many rows are displayed.
- Preserve loopback binding, trusted hosts, CSRF checks, same-site cookies and
  strict origin validation. Keep `Referrer-Policy: same-origin`: `no-referrer`
  previously caused legitimate browser POSTs to send `Origin: null`.
- Browser enhancement scripts must be local external assets under a restrictive
  CSP. Do not add inline handlers, `eval`, third-party scripts or unsafe HTML
  insertion. Keep a usable no-JavaScript fallback.

## Validation and data boundaries

From the repository root, using the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s review_checklists\tests -v
.\.venv\Scripts\python.exe -m review_checklists corpus validate
.\.venv\Scripts\python.exe -m review_checklists corpus build `
    --version "local-review" --output dist\catalog-local-review.json
```

Build/export commands refuse overwrites. Choose a fresh output path rather than
deleting an unknown artifact. For focused changes, run the relevant test modules
first, then the integration checks needed for affected surfaces. Corpus count
changes should be explained by actual additions/aliases, not hidden by weakening
tests.

Browser tests use isolated temporary reviews and fake Azure functions:

```powershell
$env:REVIEW_TEST_BROWSER_CHANNEL = "chrome"
.\.venv\Scripts\python.exe -m review_checklists.tests.browser_forms -v
```

See the app README for optional browser dependencies and Chromium setup. Never
point automated tests at `.reviews` or the user's running server.

Do not execute live ARG, change Azure CLI subscriptions, deploy resources, call
paid AI services, or transmit customer review data without explicit authorization
and scope. Public-source research is separate from customer data. Keep source
reports free of machine-local absolute paths, secrets and raw customer evidence.
