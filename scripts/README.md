# Review checklist authoring tools and legacy adapters

For current reviews, use the [local-first Python CLI and localhost UI](../review_checklists/README.md),
not the spreadsheet-oriented Bash adapter below. This directory contains shared
corpus validation/authoring tools as well as retained legacy scripts; their
commands are not interchangeable with `python -m review_checklists`.
See [Contributing](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md) before changing
recommendations or pipeline behavior.

## Versioned recommendation authoring

Use Python 3.11 or newer and an activated virtual environment. For these authoring
tools, install `python -m pip install -r scripts\requirements.txt`. From the
repository root, `python -m scripts.cl` and `python scripts\cl.py` are supported
without modifying `PYTHONPATH`. Read-only legacy v1 commands remain available.

Automatic APRL, AKS, and WAF service-guide imports are disabled. The importers
are deprecated manual fallbacks; their workflow-dispatch runs stage legacy
JSON in review PRs. Prefer LLM-assisted curation with source references.
Both approaches require validation and human review, not automatic ingestion.

The old Azure Translator and Text Analytics endpoints are decommissioned.
Do not provision these cloud services as a prerequisite for local review or
assume archived translation/enrichment workflows are operational. The fallback
name behavior below does not require Text Analytics.

`v1tov2` enriches and validates recommendations before writing individual YAML
files. Existing GUIDs are retained; new metadata remains unknown unless
explicitly supplied. Without text analytics, an existing name is retained or
the source GUID becomes the name. `store_v2` preflights the full resulting
corpus, rejects retired-ID/name collisions and loss of curated metadata, and
replaces individual files atomically. Updating existing recommendations requires
`--overwrite`; reconcile curated metadata and aliases explicitly first.
Bulk `update-recos --reviewed` date stamping is no longer supported: record
`provenance.lastReviewed` only after human review.

Author canonical YAML under `v2/recos`, not generated JSON or translations.
The single recommendation schema is `v2/schema/recommendation.schema.json`;
shared parsing and validation live in `scripts/modules/cl_corpus.py`.
Validation is strict and does not fill missing metadata. Partial validation and
alternate recommendation schemas are not supported. Preserve canonical IDs,
explicit service classification, automation semantics, provenance and aliases
according to the [corpus contract](../review_checklists/docs/corpus-contract.md).

```powershell
python -m scripts.cl validate-recos --input-folder v2\recos
python -m scripts.validate_corpus --root v2
python -m unittest discover -s scripts\tests -v
```

Legacy GUID/name selectors also resolve retired identities from `aliases`,
returning the canonical survivor. `labelSelector` with a `guid` also recognizes
retired IDs; `sourceSelector` matches either the canonical source or an explicitly
preserved alias source, so cross-source merges retain checklist membership.
Empty `services` matches `serviceSelector: ['none']` and means not explicitly curated,
not a guessed service classification. Versioned JSON releases are built by
`python -m review_checklists corpus build`; CI compares repeated builds and
uploads the catalog artifact without running importers or cloud queries.

See the [bundle build instructions](../review_checklists/docs/corpus-contract.md#distribution)
and [source-backed refresh records](../review_checklists/docs/corpus-refresh/cost-sources.md).
Passing deterministic checks does not prove query validity or human approval.

## Legacy Azure Resource Graph reviews

**Historical v1 Bash/spreadsheet workflow, not the current review CLI.** The
script [checklist_graph.sh](./checklist_graph.sh) runs queries from legacy JSON
in the [checklists directory](../checklists/README.md). The following examples
preserve its old usage; they do not query the current pinned YAML/JSON-bundle
snapshot or store evidence in SQLite. Query results require human interpretation:
even a legacy `compliant` field or empty result is not proof of compliance.

Use the [current ARG guide](../review_checklists/README.md#running-arg) for local
reviews. Run legacy queries only with explicitly authorized Azure scope.

### Legacy installation

> :warning: ***The `checklist_graph.sh` script must be run from a Bash environment shell. If you are using Azure Cloud Shell be sure to select the correct environment.***

> Note: In case you are in the context of a private AKS cluster (API server is private), there is no restriction to use Azure Cloud Shell to run the `checklist_graph.sh` script.
> Make sure that the identity (the one Azure Cloud Shell uses) used to execute the checklist_graph script, [has appropriate rights in Azure RBAC with at least read access to the resources you want to query](https://learn.microsoft.com/azure/governance/resource-graph/overview#permissions-in-azure-resource-graph) (in this case AKS cluster(s)).
> Without at least read permissions to the Azure object or object group, results won't be returned.
> The script just queries the Azure Resource Graph API and does not communicate with the API Server(s) of your clusters(s).

The old instructions downloaded the script into an Azure CLI-capable Bash
environment such as [Azure Cloud Shell](https://shell.azure.com). This URL targets
the upstream `main` branch, **not this checkout**; inspect that version before
using it. No download or Azure operation is needed for the current local app.
Historical download commands (Bash, not PowerShell):

```bash
wget --quiet --output-document ./checklist_graph.sh https://raw.githubusercontent.com/Azure/review-checklists/main/scripts/checklist_graph.sh
chmod +xr ./checklist_graph.sh
```

### Basic usage

You can run the script to produce a JSON-formatted output of all the checklist items with documented Azure Resource Graph queries. For example, to run the Azure Resource Graph queries for the AKS checklist:

```Shell
./checklist_graph.sh --technology=aks --format=json > ./graph_results.json
```

The previous command will generate a JSON file `./graph_results.json`. You can go now to your Excel spreadsheet. Make sure you have loaded up the corresponding checklist already (AKS in this example), and use the Advanced command "Import Graph Results" to import this file into the spreadsheet:

![Advanced buttons](../pictures/advanced_buttons.png)

The spreadsheet's "Comments" column receives query output, including any
resource IDs and compliance labels supplied by the legacy query. The screenshot
shows a historical AKS import, not a validated assessment of current guidance:

![Advanced ](../pictures/graph_import_result.png)

The following sections will show more advanced usage of the script.

### Listing the available checklists available

You can run the script to find out which checklists are available. Note that not all checklists will contain Azure Resource Graph queries:

```
./checklist_graph.sh --list-technologies
```

### Listing the existing categories in a checklist

You can run the script as well to generate a more human-readable output. For example, run this in order to execute analysis scoped to a single category. Command:

```
./checklist_graph.sh --technology=aks --list-categories
```

Output:

```
0: - Identity and Access Management
1: - Network Topology and Connectivity
2: - BC and DR
3: - Governance and Security
4: - Cost Governance
5: - Operations
6: - Application Deployment
```

### Doing a review for all categories with console output

This example shows how to run this for analysis on all categories in a single subscription. The output can be copy/pasted to the Excel spreadsheet (category by category). Command:

```
./checklist_graph.sh --technology=aks --format=text
```

Illustrative historical output (truncated, with placeholder resource IDs).
The old recommendation wording and computed labels below are not current
technical guidance or independently verified compliance:

```
CHECKLIST ITEM: Use Availability Zones if supported in your Azure region:
/subscriptions/<subscription-guid>/resourceGroups/<resource-group>/providers/Microsoft.ContainerService/managedClusters/<cluster>: non-compliant
CHECKLIST ITEM: Use the SLA-backed AKS offering:
/subscriptions/<subscription-guid>/resourceGroups/<resource-group>/providers/Microsoft.ContainerService/managedClusters/<cluster>: non-compliant
CHECKLIST ITEM: Use managed identities instead of Service Principals:
/subscriptions/<subscription-guid>/resourceGroups/<resource-group>/providers/Microsoft.ContainerService/managedClusters/<cluster>: compliant
...
```

### Run the graph queries scoped to a Management Group

All previous commands can be scoped to a management group, instead of to a single subscription by using the `--management-group` flag, to specify a management group name (make sure to specify the **name** and not the **display name** of the management group). Example:

```
./checklist_graph.sh --technology=aks --category=1 --management-group=mymgmtgroup
```

The output is the same as the previous examples, depending on which flags are used.

### Troubleshoot

To troubleshoot the execution of the `checklist_graph.sh` script you can run the command:

```
./checklist_graph.sh --technology=aks --format=json --debug
```

and check the debug messages being written in the Azure Cloud Shell console
