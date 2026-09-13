# Legacy Azure Monitor workbooks

**Historical v1 output, not the current review UI or report format.**
Use the [local-first application](../review_checklists/README.md) for pinned
SQLite reviews and JSON/HTML reports. These retained workbooks consume queries
from legacy checklist JSON; they do not open current reviews or write assessments
back to the application.

The v1 pipeline rendered workbook JSON and ARM templates from the
[building blocks](blocks) and [legacy checklists](../checklists/README.md).
Their presence here is not a claim that cloud workflows still run automatically,
that the files track the current YAML corpus, or that deployment/query behavior
has been validated against current Azure services.

## Retained artifacts

| Legacy workbook | Workbook JSON | ARM template |
| --- | --- | --- |
| Landing Zone | [Workbook](alz_checklist.en_workbook.json) | [Template](alz_checklist.en_workbook_template.json) |
| AKS | [Workbook](aks_checklist.en_workbook.json) | [Template](aks_checklist.en_workbook_template.json) |
| Landing Zone network counters | See template | [Template](alz_checklist.en_network_counters_template.json) |
| Application delivery network counters | See template | [Template](appdelivery_checklist.en_network_counters_workbook_template.json) |

These links point to this checkout's artifacts instead of one-click deployment
buttons targeting a different branch's upstream files. Deploying a template is a
separate Azure operation, not a prerequisite for local review.

## Historical manual import

The old workflow copied workbook JSON into the **Advanced Editor** of an Azure
Monitor workbook. If maintaining an existing workbook, inspect the source,
queries, parameters and subscription scope before doing so. Azure access and
appropriate permissions are needed; opening a workbook can execute queries.

![Legacy advanced editor](pictures/advanced_editor.png)

Queries were grouped by checklist category. Some legacy renderers expected `id`
and `compliant` output columns and displayed resource-level results:

![Legacy AKS BC/DR results](pictures/aks_bcdr.png)

Treat those displays as evidence requiring interpretation, not an architecture
sign-off. Empty, incomplete or permission-limited results do not establish
compliance. Inventory and optimization candidates are not automatic violations
or proven savings. The current app likewise never changes reviewer statuses
from query output.

## Contributions

Do not hand-edit generated workbook JSON to change a recommendation. Author
current guidance in [`v2/recos`](../v2/recos) using
[Contributing](../CONTRIBUTING.md) and the
[corpus contract](../review_checklists/docs/corpus-contract.md). A YAML change is
not a promise that these legacy workbook files will be regenerated automatically.
If maintaining a renderer or block, coordinate that explicitly as a legacy change
and regenerate/review its output through the applicable deterministic tools.

See [scripts](../scripts/README.md) and the [legacy guide](../docs/legacy-v1.md)
for related adapters and spreadsheet history.
