# Azure Review Checklists local prototype

The first v3 milestone replaces the macro-based review workflow with a Python CLI
and a localhost web UI. It reads the existing v2 corpus without modifying it.
No hosted backend, database service, LLM entitlement, or AI endpoint is needed.

The application package and command are named `review_checklists`, independently
of the development branch or release version. Moving to `main` or a future release
does not change the command or existing `.reviews` data.

**Prototype, not a production/team release.** Provider adapters and an MCP server
are designed but not implemented. Content modernization and cloud deployment are
out of scope for this milestone.

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

### Filters and assessment overview

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
commands: `init`, `list`, `show`, `update`, `run`, `export`, `serve`.

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

Only explicitly ticked checks run, not all filtered checks. Selection applies to
the current page (at most 50 checks); it is not carried across pages. Scope and
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
  Corpus changes do not silently alter an ongoing review. There is no refresh,
  migration, or JSON import workflow yet.
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
  escaped templates, and a no-script content policy protect the browser surface.
  This is not a multi-user authentication boundary against other local OS users.
  Do not proxy or expose the port to a network.

## Code layout and validation

`corpus.py` is the read-only v2 adapter; `review.py` owns SQLite state and reports;
`filters.py` derives filter options and matches review items; `arg.py` owns explicit
single/selected-query Azure execution; `azure_context.py` performs optional,
bounded CLI subscription lookup. `__main__.py` and `web.py` are thin surfaces
over those operations. The old Flask/MySQL app and legacy scripts remain unchanged.

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
```

Alternatively, set `$env:REVIEW_TEST_BROWSER_CHANNEL = "chrome"` to use an installed
Chrome instead of downloading Chromium. These tests exercise real form clicks,
including subscription preview, current-subscription execution, and assessment
saves. The same-origin referrer policy preserves browser POST origins while
suppressing referrers to other origins; `no-referrer` would cause legitimate form
requests to send `Origin: null` and be rejected. CSRF and origin checks remain enforced.
Browser coverage also exercises the disabled first-page case, the link to runnable
checks elsewhere, and the single CLI subscription option after preview.

See [provider and MCP contracts](docs/integration-design.md) for the next integration
milestone and the [decision log](../v2/docs/next-generation-design.md) for context.
