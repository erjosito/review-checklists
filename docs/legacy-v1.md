# Legacy v1 spreadsheet and checklist guide

**Historical reference, not the current setup or contribution workflow.**
The current project on this branch is the
[local-first Python CLI/localhost app](../review_checklists/README.md).
It needs neither Excel macros nor a cloud database. This guide preserves useful
v1 mechanics for existing assets; it does not promise that old releases, remote
downloads, cloud workflows or integrations still work.

The v1 design separated JSON checklist content from its presentation in a
macro-enabled Excel spreadsheet. See the [spreadsheet source](../spreadsheet),
[VBA sheet code](../spreadsheet/Sheet1.vb), and
[historical overview](../pictures/overview.png).
The JSON parsing code used [VBA-JSON](https://github.com/VBA-tools/VBA-JSON/).

## Historical entry points and maturity labels

The [upstream spreadsheet release download](https://github.com/Azure/review-checklists/releases/latest/download/review_checklist.xlsm)
is a legacy asset from `Azure/review-checklists`, not a release of this branch's
local app. Similarly, the old [FastTrack web frontend link](https://aka.ms/ftaaas)
and [sister repository](https://github.com/Azure/fta-aas) are historical external
references, not a hosted backend provided by this prototype.

The former README labelled ALZ, WAF, AKS, AVD, Cost, Multitenancy, Application
Delivery Networking and SAP checklists GA; ARO, AVS design/implementation,
API Management, Stack HCI, Spring Apps, Azure DevOps and SQL Migration Preview;
and Security Deprecated. These are **historical v1 labels**, not current
support/freshness guarantees or the release status of the v3 app. Consult
[CODEOWNERS](../CODEOWNERS) for repository review ownership rather than treating
the old checklist table as a maintained owner roster.

## Using an existing spreadsheet

1. Obtain the macro-enabled spreadsheet from a trusted, approved source. The
   [repository copy](../spreadsheet/review_checklist.xlsm) and upstream download
   above are legacy references.
2. Select the technology and language in its dropdowns.
3. Choose **Import latest checklist** and confirm the prompt. This legacy action
   retrieves the selected remote v1 JSON; it does not load the current YAML
   corpus or a versioned bundle, and "latest" does not mean current-branch content.
4. Work through the rows, selecting a status and recording comments, applicability,
   owners and tradeoffs. **More Info** links provide additional context. Reviewing
   one area or priority at a time can make a large checklist manageable.
5. Use the **Dashboard** sheet to inspect review progress.

![Legacy spreadsheet](../pictures/spreadsheet_screenshot.png)
![Legacy dashboard](../pictures/spreadsheet_screenshot_dashboard.png)

The old VBA workflow did not support Excel for Mac because of missing libraries.
A macro-free `.xlsx` copy can be distributed where macros are not available or
permitted, but it loses checklist and ARG JSON import capabilities. This is a
spreadsheet workaround, not an import/export path into the current application.

### Macro warnings

Downloaded `.xlsm` files may be blocked or report a format/extension error.
Follow your organization's macro policy and verify the source/integrity before
opening one. The old guide illustrated Windows file **Unblock** and Defender
exceptions; those are not prerequisites for the current app and are not general
recommendations to bypass security controls. Do not disable protection to use
these assets. Use the current app or an approved macro-free copy if macros are
not permitted.

![Historical Excel macro warning](../pictures/macro_warning.png)

## Spreadsheet JSON export and old authoring mechanics

For maintaining an existing v1 asset, the spreadsheet's **Advanced** controls
include **Export checklist to JSON**:

1. Load the English checklist and make the intended row changes.
2. Raw hyperlinks can be entered in cells; the legacy exporter handled locale
   normalization. Blank GUID cells caused it to generate IDs for new rows.
   Preserve IDs for existing requirements.
3. Export to a local JSON file. The historical repository naming convention was
   `<technology>_checklist.en.json`.

![Legacy advanced controls](../pictures/advanced_buttons.png)

The old contribution workflow accepted edits to English JSON or a spreadsheet
export, and used [template.json](../checklists/template.json) when starting a new
checklist. Translations and workbooks were generated derivatives. Those mechanics
are retained here to explain the artifacts, **not to recommend hand-editing
generated JSON or submitting spreadsheet exports as current corpus changes**.
Use [canonical YAML authoring](../CONTRIBUTING.md#author-recommendations-in-yaml)
and preserve canonical IDs/aliases instead. There is no implemented spreadsheet
or legacy JSON review migration into SQLite.

If deliberately maintaining spreadsheet code, the historical editable assets are
the `.xlsm` file and VBA sources under `spreadsheet`. Close Excel before preparing
a diff and exclude lock/temporary files and any engagement data. Coordinate such
legacy-only changes separately from the current app.

## Legacy ARG evidence import

The Bash [checklist_graph.sh](../scripts/checklist_graph.sh) adapter reads v1
checklists and can produce JSON for **Import Graph Results** in the spreadsheet.
Load the same checklist before importing; results populate the comments column.
See the explicitly [legacy script instructions](../scripts/README.md#legacy-azure-resource-graph-reviews)
for the historical commands and examples.

![Legacy ARG result import](../pictures/graph_import_result.png)

Older automation expected `id` and `compliant` fields, including a boolean
`compliant` column for some workbook renderers. That convention does not prove
query correctness and is not a universal rule for current queries. Review the
query, scope, permissions and result meaning; empty or incomplete results are
not a pass. The current app stores evidence separately and never changes a
reviewer's status from ARG output.

## Other retained surfaces

- [Legacy JSON checklists](../checklists/README.md): localized v1 artifacts, not the current authoring source.
- [Legacy scripts](../scripts/README.md): Bash/spreadsheet adapters alongside current deterministic authoring tools.
- [Legacy Azure Monitor workbooks](../workbooks/README.md): retained renderings and manual import history.
- [Legacy MySQL/ACI web prototype](../web/README.md): old deployment architecture and known limitations, not the current localhost UI.

The former automatic Azure Translator and Text Analytics dependencies are
decommissioned. Scheduled APRL, AKS-checklist and WAF service-guide imports are
deprecated; any retained manual fallback remains subject to human review and
deterministic validation. Archived cloud workflows are not automatically running
or supported setup instructions. See the [decision log](../v2/docs/next-generation-design.md)
for the current direction and [root disclaimer](../README.md#disclaimer).
