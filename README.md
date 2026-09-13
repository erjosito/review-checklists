# Azure Review Checklists

**A local-first Python CLI and localhost web UI for Azure architecture reviews.**
On this development branch, the current v3 prototype replaces the spreadsheet
review workflow. Browse recommendations, record assessments and comments offline,
optionally collect Azure Resource Graph (ARG) evidence, and export JSON or HTML.
No hosted backend, cloud database, AI entitlement, or AI endpoint is required.

**Prototype, not a production/team release.** The application has no implemented
AI provider adapters, embedding index, or MCP server. Those are
[future integration designs](review_checklists/docs/integration-design.md), not
features to configure. The older spreadsheet and MySQL/ACI web prototype are
[legacy assets](docs/legacy-v1.md), not prerequisites or hosted versions of this app.

## Start a local review

Use Python **3.11+**. From a checkout of this branch, run in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r review_checklists\requirements.txt
.\.venv\Scripts\python.exe -m review_checklists init `
    --name "My Azure review" --description "Scope and objectives of this review."
.\.venv\Scripts\python.exe -m review_checklists serve
```

Open `http://127.0.0.1:8765`. Stop the server with Ctrl+C. It binds to loopback;
starting it does not sign in to Azure or run queries. The default review database
is `.reviews\review.sqlite3`. **Resume with `serve`, not `init`**: initialization
refuses to overwrite an existing review.

For a separate review with a smaller checklist:

```powershell
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\delivery.sqlite3 init `
    --name "Application delivery" --description "Production ingress design." `
    --checklist v2\checklists\app_delivery.yaml
.\.venv\Scripts\python.exe -m review_checklists --review .reviews\delivery.sqlite3 serve --port 8766
```

**`--review` is a global option: put it BEFORE the subcommand.** Its path chooses
the SQLite file; `--name` is a friendly name stored inside that file, not a filename.
The description is review-wide context, distinct from per-check comments. Reuse
the same `--review` path for every command on that review. Omitting it selects the
default database, even if another review has a similar friendly name.

The package name `review_checklists` is independent of release and branch names.
The historical `v2\recos` and `v2\checklists` paths remain intentional.
See the [application guide](review_checklists/README.md) for detailed UI filtering,
pagination, saving behavior, metadata editing, ARG scope controls, and troubleshooting.

## Assess and export

These examples use the default review. Choose a recommendation ID from `list`:

```powershell
.\.venv\Scripts\python.exe -m review_checklists list --search "tags"
.\.venv\Scripts\python.exe -m review_checklists show "<recommendation-guid>"
.\.venv\Scripts\python.exe -m review_checklists update "<recommendation-guid>" `
    --status "Non-compliant" --comments "Agree a tagging policy with the owner."
.\.venv\Scripts\python.exe -m review_checklists metadata --description "Scope: production subscriptions."
.\.venv\Scripts\python.exe -m review_checklists export --format json --output .reviews\report.json
.\.venv\Scripts\python.exe -m review_checklists export --format html --output .reviews\report.html
```

Statuses are **Not reviewed**, **Compliant**, **Non-compliant**, and
**Not applicable**. They are reviewer decisions and can be recorded without
Azure access. Document applicability and tradeoffs rather than treating design
review as automatic certification.

Optional ARG execution uses an existing Azure CLI login and explicitly selected
subscription scope. It sends query text and scope to Azure and stores evidence
locally; it **never changes assessment status**. Inventory, Advisor findings,
optimization candidates, and empty results are not compliance verdicts or proven
savings. Read [ARG execution and limitations](review_checklists/README.md#running-arg)
before running any query.

JSON exports include the pinned recommendations, review metadata, assessments and
evidence; HTML is a standalone report. Export commands refuse overwrites. SQLite
and reports can contain sensitive customer information and are not encrypted by
the app. Protect them locally and do not commit them to this public repository.
The app does not send review data to an LLM.

## Content and review data

The current local draft contains **2,008 canonical recommendations and 58
preserved aliases**. The latest [bounded follow-up](review_checklists/docs/corpus-refresh/followup-2026-09-13.md)
documents applied corrections, verified sources, checklist effects and remaining gaps.

| Layer | Current role |
| --- | --- |
| [`v2/recos`](v2/recos) | Canonical, individually authored YAML recommendations with stable IDs, services, automation semantics, provenance and duplicate aliases |
| [`v2/checklists`](v2/checklists) | YAML selectors assembling recommendations into checklists |
| [Versioned JSON bundle](review_checklists/docs/corpus-contract.md#distribution) | Deterministic, validated distribution artifact generated from YAML, not a second editable source |
| Local SQLite review | Pinned snapshot initialized from YAML or a bundle, plus that review's metadata, assessments, comments and evidence |
| JSON / HTML report | Explicit export of the review, not an automatic corpus update |

A corpus refresh does not silently update existing reviews. For bundle creation,
initialization from a bundle, identity compatibility, and the single shared schema,
see the [corpus contract](review_checklists/docs/corpus-contract.md).
To adopt a new bundle deliberately, use **Refresh review** in the UI or the
[`refresh` command](review_checklists/docs/review-refresh.md). Preview changes
before applying; existing assessments, comments and evidence are preserved,
with changed guidance flagged for reassessment.

The **Corpus administration** header link shows the current public corpus,
service/pillar distributions, ARG metadata, recorded upstream coverage and
maintenance history. It is separate from the review's pinned snapshot and does
not execute queries or initiate refreshes. It also runs independently:

```powershell
.\.venv\Scripts\python.exe -m review_checklists.corpus_admin
```

Open `http://127.0.0.1:8767/corpus/`. See the
[corpus administration guide](review_checklists/docs/corpus-admin.md).

Content updates are source-backed proposals with deterministic validation and
human review. Automatic APRL, AKS-checklist and WAF service-guide ingestion is
deprecated; manual importer fallbacks do not bypass those gates. LLM-assisted
curation does not mean automatic publication or in-app AI. The former Azure
Translator and Text Analytics dependencies are decommissioned; archived
translation/enrichment workflows are not setup requirements.

## Documentation and contributions

- [Application guide](review_checklists/README.md): current CLI, localhost UI, reports and data boundaries.
- [Contributing](CONTRIBUTING.md) and [agent/contributor guidance](AGENTS.md): authoring, implementation and validation practices.
- [Cost sources and coverage](review_checklists/docs/corpus-refresh/cost-sources.md) and [Cost refresh report](review_checklists/docs/corpus-refresh/cost-refresh-report.md): verified references, exact changes, query caveats and untouched areas. This is a **bounded refresh**, not an exhaustive corpus audit.
- [All-pillar/APRL assessment](review_checklists/docs/corpus-refresh/full-refresh-2026-09-11/README.md): the subsequent 2,005-record accounting pass, six additions, verified changes and explicit manual-review gaps.
- [Applied September 13 follow-up](review_checklists/docs/corpus-refresh/followup-2026-09-13.md): classification/Key Vault corrections, two storage duplicate merges, source evidence and remaining decisions.
- [Source inventory and coverage tools](review_checklists/docs/source-coverage.md): recorded upstream IDs and hashes, dated denominators, and explicit read-only comparison commands.
- [Decision log](v2/docs/next-generation-design.md): current decisions, historical context and deferred work.
- [Scripts](scripts/README.md): current deterministic authoring tools and explicitly legacy adapters.
- [Legacy v1 guide](docs/legacy-v1.md): preserved spreadsheet how-tos and links to legacy JSON, workbooks and the old web prototype.
- [Support](SUPPORT.md), [security reporting](SECURITY.md), and [code of conduct](CODE_OF_CONDUCT.md).

## Disclaimer

- This is not official Microsoft documentation or software.
- This is not an endorsement or a sign-off of an architecture or a design.
- This code sample is provided "AS IT IS" without warranty of any kind, either expressed or implied, including but not limited to the implied warranties of merchantability and/or fitness for a particular purpose.
- This sample is not supported under any Microsoft standard support program or service.
- Microsoft further disclaims all implied warranties, including, without limitation, any implied warranties of merchantability or fitness for a particular purpose.
- The entire risk arising out of the use or performance of the sample and documentation remains with you.
- In no event shall Microsoft, its authors, or anyone else involved in the creation, production, or delivery of the script be liable for any damages whatsoever (including, without limitation, damages for loss of business profits, business interruption, loss of business information, or other pecuniary loss) arising out of the use of or inability to use the sample or documentation, even if Microsoft has been advised of the possibility of such damages
