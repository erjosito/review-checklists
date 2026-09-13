# Azure Review Checklists local prototype

The first v3 milestone replaces the macro-based review workflow with a Python CLI
and a localhost web UI. Reviews read the YAML corpus or a versioned JSON bundle
and keep their own pinned snapshot; opening a review does not modify the corpus.
No hosted backend, database service, LLM entitlement, or AI endpoint is needed.

The application package and command are named `review_checklists`, independently
of the development branch or release version. Moving to `main` or a future release
does not change the command or existing `.reviews` data.

**Prototype, not a production/team release.** Provider adapters and an MCP server
are designed but not implemented. The bounded September 2026 corpus refresh and
confirmed duplicate merges are complete; this does not establish exhaustive
coverage or live query validity. Cloud deployment remains out of scope.

## Quick start (PowerShell)

Use Python 3.11 or newer. Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r review_checklists\requirements.txt

# Start a review containing all v2 recommendations.
.\.venv\Scripts\python.exe -m review_checklists init --name "My Azure review"
.\.venv\Scripts\python.exe -m review_checklists serve
```

Open `http://127.0.0.1:8765`. Stop the server with Ctrl+C. It binds only to
loopback, uses Waitress (not Flask debug mode), and never starts Azure login.
Browse/search recommendations, edit status/comments, and download reports from
the UI. There are no AI controls in this milestone.

### Recommendation autosave

On the main list, choose a manual **Status** and expand **Comments** for notes on
that recommendation. Collapsed editors show a short preview, so the complete list
stays compact. These comments are separate from the review-wide description in
**Edit review details**. Assessments work without Azure access; ARG never assigns
or overwrites a status.
The full list retains every native editor, but supported browsers defer rendering
offscreen editors until scrolling or focusing them. Print layout renders all
editors. This is not pagination or removal of offscreen controls. Large lists can
still take longer on a busy machine; use optional 50-row pagination when needed.

**Autosave enabled** appears only after the local enhancement initializes.
Status changes save immediately; comments save after **700 ms** without typing,
or when the field loses focus. Each row shows **Unsaved**, **Saving**, **Saved**,
or an explicit **Error**. **Saved** means the server acknowledged the write, not
merely that a request was sent. Saves are serialized per recommendation, using
the last acknowledged revision; typing during a save is retained and saved next.
Different recommendations can save independently. Comments allow up to 20,000
characters.

Failures retain the editable draft **in the current page**, with **Retry save**;
there is no indefinite automatic retry. Validation, session/CSRF, storage,
network, and stale-revision failures are distinguished. A request times out after
15 seconds. After a network failure or timeout the write may already have reached
SQLite: retry still uses the old revision, so it cannot silently overwrite a
concurrent edit. A conflict stops autosave for that row. Copy the draft, use
**Open saved assessment in a new tab to compare**, and reload/reconcile against
the saved version before saving again. Session failures can require reloading
after copying the draft; storage failures also have details in the server terminal.

Wait for every edited row to show **Saved** before leaving. While drafts, errors,
or in-flight requests remain, navigation links and other forms (filters, query
runs, subscription previews, and review details) are blocked with a warning.
Browser reload/close uses a native unsaved-changes warning where supported.
Drafts are not stored in browser storage and cannot survive a forced close,
crash, or deliberately accepted discard warning; copy important failed drafts
before reloading. Saved assessments remain in SQLite.

Status edits visibly mark the overview, counts, and filter membership as a
**page-load snapshot needing refresh**. Rows are not silently removed from an
active status filter while being edited. After saving, use **Refresh overview
and list**; filters and pagination choice are preserved, and a page emptied by
status changes is clamped to the last available page.

Without JavaScript, or if the asset cannot load, autosave remains explicitly
disabled and each row has a **Save assessment** button. Save one row at a time
before navigating or submitting another form; no-JavaScript mode cannot guard
unsaved edits in other rows. Manual saves retain the filtered list and pagination.
The detail page continues to use its explicit **Save assessment** button, and
review-wide metadata retains its separate **Save review details** action.
Row forms are independent, not nested in the query form: the batch form ends
before the table and only ARG selection checkboxes link back to it. Assessment
fields are never submitted as part of a query run.

### Refresh a saved review from a new bundle

Use **Refresh saved review guidance** on the assessment list to open
`/review-refresh`. The existing `/refresh` URL still reloads the assessment list;
it does not change recommendation guidance.

Upload a versioned JSON bundle and choose **Preview review refresh**. Preview is
read-only and runs no Azure queries or source downloads. Inspect changed fields,
before/after guidance, additions, removed/superseded checks, and consolidation
groups before selecting **Apply this review refresh**. Existing statuses, comments,
evidence, and area/subarea placements are retained. Removed or aliased IDs remain
separate review records; their assessments are never merged.

New checks are excluded unless **Add new checks within the selected scope** is
checked. Saved scope comes from new CLI `init` operations; older reviews and
directly created reviews can have unknown scope. Unknown scope requires an
explicit all-corpus choice or uploaded YAML/JSON checklist before adding checks.
Checklist uploads capture the definition, not a changeable local filename.

Semantic guidance changes mark reviewed checks **Needs reassessment** without
changing their saved status. The list, detail, and HTML/JSON reports distinguish
current, superseded, and no-longer-current guidance. Dashboard counts remain
historical saved assessments, not certification against the latest bundle.
Comment-only autosave does not clear the flag. Change status deliberately, or
open the detail page, check **I reviewed the refreshed guidance and confirm the
current assessment**, and choose **Save assessment** to retain the existing status.

Apply creates a consistent, sensitive SQLite backup alongside the review, then
commits all changes atomically. **Review refresh history** shows source identities,
before/after snapshots, relevance flags, and backup paths. The latest applied
source is distinct from each item's guidance origin and the actual reviewed
snapshot hash. A no-change apply creates no backup or history.

Browser uploads are limited to 12 MiB per bundle and 256 KiB per checklist,
within a 16 MiB preview-request cap. Ordinary forms retain their existing 256 KiB
limit. YAML aliases are rejected. Previews are stored only in local server memory,
bound to the browser session: at most two per session, eight per server, with a
64 MiB serialized bundle/plan budget and 15-minute expiry. Restarting the server
discards them. Apply consumes its opaque handle once; double clicks, expired
handles, intervening review edits, and changed targets cannot replay or silently
alter the approved operation. Errors require a fresh preview; failed applies do
not partially commit. Capacity errors are explicit rather than silently evicting
another browser's preview.

Wait for inline edits to save before following refresh/history links. Existing
draft-navigation protection blocks these links while inline edits are unsaved,
in flight, or failed. Without JavaScript, save each row explicitly first.
New reviews and changed refreshes use schema 2; schema-1 reviews remain readable
without migration on open or preview. Restart older running application versions
before applying a refresh.

For CLI commands and the shared planner/apply API, see
[Review refresh](docs/review-refresh.md).

### Filters and assessment overview

All matching recommendations are shown by default. To split the list into pages,
tick **Paginate results (50 per page)** and click **Filter**. Untick it and apply
the filter again to show everything. The choice follows links, detail edits,
metadata saves, and subscription previews; **Clear filters** restores the
unpaginated default. Existing bookmarked URLs containing `page` still enable
pagination. Exports always include the full review, irrespective of this setting.

Expand **Status**, **Severity**, **WAF pillar**, or **Azure service** to tick any
number of values, then click **Filter**. Values within a group use **OR**; different
groups use **AND**. For example, High + Medium severity and AKS + AppGW selects
checks of either severity for either service. Leaving a group empty means all
values; it does not mean no results.

Combine these selections with search and **Only checks with ARG queries**.
Filters apply across the full review (not just the current page) and remain in
the URL through pagination, item details, saves, subscription lookup and query
execution. Applying filters starts at page 1; **Clear filters** returns to the
complete review. Exports still contain the full review.

Severity values map to the corpus's 0 = High, 1 = Medium, 2 = Low. WAF offers the
five pillars plus **Not specified**. Services are derived from explicit service
metadata when present, otherwise from resource types, using the existing
`scripts\service_dictionary.json` alias mapping. Recommendations can match
multiple services. Unknown resource types appear as their lowercase ARM type;
**Not service-specific** finds guidance without service/resource metadata.
The mapping cannot distinguish services that share the same resource type unless
the recommendation supplies more specific service metadata. This display/filter
mapping does not modify the pinned corpus or existing review database.

The dashboard shows a status-composition donut and two percentages for **all
checks matching the current filters**:

- **Compliance:** compliant / (compliant + non-compliant). Unreviewed and
  not-applicable checks are excluded. Displays **N/A** when none have been assessed
  as applicable, never an invented 100%.
- **Review progress:** all statuses except not-reviewed / total matching checks.
  Not-applicable assessments count as reviewed. Displays **N/A** for no matches.

These are reviewer-assigned assessments. ARG evidence does not change them
automatically. Charts render locally as accessible SVG, without JavaScript or
external chart services.

Review state defaults to `.reviews\review.sqlite3`, ignored by Git. Restarting
`serve` reopens that review; **do not rerun `init` to resume**. Initialization and
CLI export refuse to overwrite an existing file.

For a smaller checklist or a separate engagement:

```powershell
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\delivery.sqlite3 init `
    --name "Application delivery" --checklist v2\checklists\app_delivery.yaml
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\delivery.sqlite3 serve --port 8766
```

`--review` is a global argument and goes **before** the command. Available
commands: `init`, `metadata`, `list`, `show`, `update`, `run`, `export`, `serve`, `corpus`.

### Review filename, name, and description

The database filename is explicitly chosen with `--review`; `--name` is the
friendly name stored **inside** that database, not a filename. For example:

```powershell
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\LitwareReview01.sqlite3 init `
    --name "LitwareReview01" --description "Azure architecture review for Litware."
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\LitwareReview01.sqlite3 serve
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\LitwareReview01.sqlite3 metadata
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\LitwareReview01.sqlite3 metadata `
    --description "Scope: production subscriptions."
```

Use the same `--review` path when reopening, editing, querying, or exporting.
Without it, commands continue to use `.reviews\review.sqlite3`. To rename an
existing database, stop its server and other writers first, move the file with
your file manager, and reopen it with the new `--review` path. Do not initialize
over it or create a fresh review to resume existing assessments.

**Edit review details** in the UI changes the stored name and description without
renaming the file. The `metadata` command displays details as JSON; `--name` and
`--description` edit only supplied fields, and `--description ""` clears it.
Descriptions allow up to 20,000 characters. Web forms reject stale metadata edits;
CLI callers can supply `--revision` using the displayed `metadata_revision`.

New reviews store a stable `review_id`, name, description, creation timestamp,
metadata-update timestamp, and metadata revision alongside corpus provenance.
The extensible SQLite key/value metadata table preserves unknown fields. Metadata
edits never change the pinned checks, assessments, evidence, or creation timestamp.
Name and description appear in both exports. Existing reviews remain readable
without modification: missing descriptions display as empty, and a stable ID and
revision fields are saved on their first explicit metadata edit.

## CLI review and reports

```powershell
.\.venv\Scripts\python.exe -m review_checklists list --search "tags"
.\.venv\Scripts\python.exe -m review_checklists list --severity high --waf Security `
    --service AKS --with-arg
.\.venv\Scripts\python.exe -m review_checklists list --severity high medium `
    --waf Security Reliability --service AKS AppGW `
    --status "Not reviewed" "Non-compliant" --with-arg
.\.venv\Scripts\python.exe -m review_checklists show 5de32c19-9248-4160-9d5d-1e4e614658d3
.\.venv\Scripts\python.exe -m review_checklists update 5de32c19-9248-4160-9d5d-1e4e614658d3 `
    --status "Non-compliant" --comments "Agree a tagging policy with the owner."
.\.venv\Scripts\python.exe -m review_checklists export --format json --output .reviews\report.json
.\.venv\Scripts\python.exe -m review_checklists export --format html --output .reviews\report.html
```

The `list` filters `--status`, `--severity`, `--waf`, and `--service` accept multiple
values and can also be repeated (for example, `--severity high --severity medium`).
Quote service names and statuses containing spaces. Single-value commands and
existing saved URLs remain supported. URL selections use repeated parameters such
as `?severity=high&severity=medium&service=aks&service=appgw`.

Statuses: `Not reviewed`, `Compliant`, `Non-compliant`, `Not applicable`. These are
the prototype's explicit review vocabulary, not an Excel import/export mapping.
Updates preserve fields not supplied on the CLI; `--comments ""` clears comments.
Use `--revision` from `show` for scripted optimistic-concurrency protection. Web
forms always include that revision and reject stale edits instead of losing changes.

JSON includes the pinned recommendations, assessments, snapshot hash, scope,
query text, timestamps, and all saved evidence. It is the git-friendly interchange
format; SQLite is the local working store. HTML is a standalone, escaped report
with no external assets. It includes assessment counts, comments and query history,
showing up to 100 rows per run. Neither format contains AI-generated scoring.

## Running ARG

Azure CLI must be installed and signed in via `az login` with an existing account
that can query the target subscriptions. The app uses `DefaultAzureCredential`
restricted to `AzureCliCredential`; environment/service-principal, managed-identity
and interactive-browser credentials are excluded. It does not grant permissions,
create resources, install extensions, or request consent.

```powershell
.\.venv\Scripts\python.exe -m review_checklists run 5de32c19-9248-4160-9d5d-1e4e614658d3 `
    --subscriptions "<subscription-guid>,<another-subscription-guid>"
```

The same operation is available on each recommendation's web page. Inspect the
pinned query and choose its subscription scope. Only queries already in the
selected corpus can run; no arbitrary KQL input or automatic background scans.

### Use the Azure CLI's selected subscription

Both the single-check and selected-check query forms offer **Show Azure CLI
subscription**, but previewing is optional. There is one **Use Azure CLI
subscription** option, selected initially, and one manual-ID option. Choose the
CLI option and click the run button to resolve its selected subscription at
execution time and run only the checks you selected. No ID copy/paste is required.

The **Show Azure CLI subscription** button only previews the name and ID from
`az account show`, then returns you to the scope controls. The name and ID appear
in the same CLI option, not as another radio choice. Previewing does not sign in,
change subscriptions, run queries, or request permissions. Successful lookup does
not prove the login is still valid or has ARG access.

The lookup preserves ticked checks and active filters. A missing CLI, login
problem, or lookup timeout produces an explicit error; it never silently runs
against a different subscription. Manual entry remains available.

If you previewed a subscription, execution checks that the current CLI selection
still matches the displayed ID. A change in the CLI or another browser tab blocks
execution until you refresh the subscription details and confirm the new scope.
Without a preview, the CLI's current selection is used directly. Save unsaved
assessment edits before refreshing context on a recommendation page.

### Run selected checks from the UI

1. Optionally enable **Only checks with ARG queries** and apply other filters.
2. Tick the checkboxes beside the checks you want to run. Manual-only checks have
   no selection checkbox.
3. Under **Run selected ARG queries**, choose **Use Azure CLI subscription**,
   optionally preview it, or enter IDs manually. Then click **Run selected
   queries**. Your existing Azure CLI login must have access.
4. Review the per-check outcome table; open a check to inspect its saved evidence
   and record your assessment.

Only explicitly ticked checks run, not all filtered checks. Select at most 50
checks per run, even when all results are displayed without pagination. With
pagination enabled, selection is not carried across pages. Scope and
the entire selection are validated before any Azure request. Queries run
sequentially; wait for the response rather than resubmitting. Individual Azure
failures are saved and displayed, while remaining selected queries continue.
Partial failure is explicitly reported, not presented as a successful batch.

The run button is disabled when the **current page** has no query-bearing checks,
not because a subscription is missing. The UI shows runnable counts for both the
page and all matching checks. If runnable checks are on other pages, **Show only
checks with ARG queries** keeps the other filters and jumps to the query-bearing
checks. If no matching checks have queries, the UI explains that they require
manual review. Filtering a pillar or selecting a subscription never automatically
selects checks or supplies missing queries.

**Query execution never changes review status.** Existing corpus queries have
different meanings: some return findings, others inventory or a `compliant` column.
Empty results are not proof of compliance. Assess the evidence manually.

The runner follows ARG pagination up to 10,000 rows or 100 pages per run. Incomplete
results are explicitly marked `truncated`, including responses that Azure truncates
without a continuation token. Azure errors are recorded as failed evidence attempts,
shown as errors, and do not replace earlier evidence or assessments. Invalid scope
and missing queries are rejected before contacting Azure.

This milestone's automated checks use a mocked Azure transport. Live tenant access
and query correctness against customer resources require a separately authorized
smoke test with explicit subscription scope.

## Data handling and boundaries

- Recommendations are copied into each review, keyed by their GUID. Duplicate or
  invalid GUIDs fail initialization rather than merging unrelated items.
- The snapshot preserves the recommendation contents and source-relative filename.
  Corpus changes do not silently alter an ongoing review. The explicit
  [review-refresh workflow](docs/review-refresh.md) previews a versioned JSON
  bundle and backs up the review before applying guidance changes, preserving
  assessments and evidence. This is not an import of assessment data from JSON.
- v2 root/area/subarea include/exclude selectors are supported. Matching reuses
  v2's existing helper: name/GUID matches explicitly include an item; label matches
  are OR; other populated selector categories intersect. Selections from sections
  are unioned by GUID; the last matching section supplies area/subarea. Exclusions
  apply to their own section, not globally to child sections.
- SQLite and exports contain potentially sensitive customer data and are not
  encrypted by the app. Protect them with OS access controls and disk encryption.
  Do not commit them to this public repository. JSON is suitable for a separately
  approved private engagement repository.
- No review data goes to an LLM. Explicit ARG runs send KQL and subscription scope
  to Azure, and documentation links open external sites. "Local-first" does not mean
  those operations are offline.
- Loopback binding, trusted-host checks, CSRF tokens, strict same-site cookies,
  and escaped templates protect the browser surface. The restrictive content
  policy intentionally permits only same-origin external scripts (`script-src
  'self'`) and same-origin connections (`connect-src 'self'`) for local progressive
  enhancement. There are no inline handlers, inline scripts, `eval`, external JS
  dependencies, or third-party autosave services. Autosave uses form-encoded
  same-origin POSTs with the same CSRF/origin checks as manual saves.
  This is not a multi-user authentication boundary against other local OS users.
  Do not proxy or expose the port to a network.

## Corpus authoring and distribution

YAML remains the authoring format under `v2\recos`; generated versioned JSON
bundles are the distribution format, and SQLite holds review state. See the
[corpus contract](docs/corpus-contract.md) for required IDs, automation semantics,
service classifications, provenance, alias handling, and migration/build commands.
Strict validation does not establish technical correctness or live query validity.

The initial bounded Cost refresh updated 48 existing recommendations and added
eight. Its corpus-wide duplicate reconciliation retired 55 identities across 54
confirmed groups into aliases, leaving 2,005 canonical recommendations at that
stage. The later [all-pillar refresh](docs/corpus-refresh/full-refresh-2026-09-11/README.md)
resulted in 2,011 canonical recommendations. The subsequent
[September 13 follow-up](docs/corpus-refresh/followup-2026-09-13.md) applies 19 source
amendments and retires three storage duplicates, leaving 2,008 canonicals and 58
aliases. None of these bounded stages establishes exhaustive coverage. See the
[refresh summary](docs/corpus-refresh/README.md),
[Cost sources and coverage](docs/corpus-refresh/cost-sources.md), and
[Cost refresh report](docs/corpus-refresh/cost-refresh-report.md) for evidence,
scope, and remaining gaps. The Cost queries remain unvalidated inventory, not
verified savings or automatic compliance verdicts.

Scheduled upstream imports are deprecated; the remaining import paths are
deprecated manual fallbacks that still require validation and human review.
LLM-assisted refreshes propose source-backed edits, not autonomous publication.
Deterministic validation and bundle assembly remain required. Existing saved
reviews never silently adopt refreshed guidance or merged identities.

## Code layout and validation

`corpus.py` is the read-only corpus adapter; `review.py` owns SQLite state and reports;
`filters.py` derives filter options and matches review items; `arg.py` owns explicit
single/selected-query Azure execution; `azure_context.py` performs optional,
bounded CLI subscription lookup. `__main__.py` and `web.py` are thin surfaces
over those operations. `catalog.py` handles versioned bundles and metadata migration;
`scripts\modules\cl_corpus.py` owns shared schema and identity validation. The old
Flask/MySQL app remains unchanged.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s review_checklists\tests -v
```

The tests cover the real v2 corpus and selected checklist sizes, persistence and
conflicts, CLI/web workflows, report escaping, local request protections, and
mocked ARG success, failures, pagination, and truncation. They also cover combined
filters, retained navigation, selected-only execution and preflight, partial
batch failures, and dashboard percentage denominators/empty states.
Subscription tests cover opt-in lookup, missing CLI/login, invalid output,
timeouts, preserved selection, manual overrides, and stale or tampered scopes.
Multi-select tests cover OR-within/AND-across matching, empty groups, duplicate
aliases, invalid members, repeated CLI options and query-parameter preservation.

### Real-browser form checks

The browser regression suite uses an isolated temporary review and fake Azure
lookup/query functions; it never runs queries against your subscriptions.

```powershell
.\.venv\Scripts\python.exe -m pip install -r review_checklists\requirements-browser.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m review_checklists.tests.browser_forms -v
.\.venv\Scripts\python.exe -m review_checklists.tests.browser_autosave -v
```

Alternatively, set `$env:REVIEW_TEST_BROWSER_CHANNEL = "chrome"` to use an installed
Chrome instead of downloading Chromium. These tests exercise real form clicks,
including subscription preview, current-subscription execution, and assessment
saves. The same-origin referrer policy preserves browser POST origins while
suppressing referrers to other origins; `no-referrer` would cause legitimate form
requests to send `Origin: null` and be rejected. CSRF and origin checks remain enforced.
Browser coverage also exercises the disabled first-page case, the link to runnable
checks elsewhere, and the single CLI subscription option after preview.
Autosave coverage exercises debounce/blur, edits during delayed saves, concurrent
editor conflicts, network failure/retry and lost acknowledgements, no-script
fallback, independent form ownership, navigation warnings, and honest dashboard
refresh. All browser saves use temporary reviews, not the user's active database.

See [provider and MCP contracts](docs/integration-design.md) for the next integration
milestone and the [decision log](../v2/docs/next-generation-design.md) for context.
