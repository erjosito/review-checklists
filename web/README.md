# Legacy MySQL/ACI web prototype

**Historical v1 architecture, not the current localhost application.**
To run the current local-first Python CLI/UI, follow
[`review_checklists/README.md`](../review_checklists/README.md). It uses a pinned
SQLite review and needs neither MySQL nor an Azure Container Instance (ACI).
Although both implementations use Flask, the code in this directory is not
the current app or its deployment template.

This document preserves the older proof of concept and its limitations for
readers maintaining existing assets. It is not a supported deployment guide,
and retained templates/scripts have not been validated against today's Azure
services. See the [legacy guide](../docs/legacy-v1.md) and
[current decision log](../v2/docs/next-generation-design.md).

## Historical architecture

![Legacy high-level overview](../pictures/high_level_web_based_view.png)

The prototype used a MySQL database and an ACI container group with:

| Container | Historical role |
| --- | --- |
| `filldb` (init) | Create the database/tables and load a legacy JSON checklist |
| `fillgraphdb` (init) | Execute checklist ARG queries and store results in MySQL |
| `flask` (main) | Display rows and update per-item status/comments in MySQL |

![Legacy Flask/MySQL interface](../pictures/flaskmysql_screenshot.png)

The old `fillgraphdb` path used service-principal credentials for Azure queries.
User-assigned managed identity was a proposed improvement; the original tests
reported identity access problems in init containers. Neither statement is a
current validation of these authentication paths.

The retained [service-principal deployment script](arm/deploy_sp.azcli) and
[ARM template](arm/template.json) are historical references, not setup steps for
the current project. The script created a principal, assigned subscription-wide
Reader access, and provisioned MySQL/ACI; credentials were not stored in Key Vault.
The historical UI listened on the container group's public IP at TCP port 5000.
Do not expose this prototype as a current hosted review service.

## Known historical limitations

The original design explicitly omitted HTTPS and application authentication,
left the MySQL network firewall open, and disabled MySQL SSL enforcement for its
client library. Those omissions are not supported defaults or guarantees of
safety. Proposed proxies, network restrictions and managed identity work were
ideas, not implemented fixes documented here.

Its UI wrote directly to MySQL. Restarting the container group could rerun
`filldb` and wipe/reinitialize the review; independent query refresh and frontend
restart were proposed but not established in the original guide. Do not use
these containers to open, migrate or resume a current SQLite review.

For current storage, save behavior, localhost boundaries and explicit evidence-only
ARG execution, consult the [application guide](../review_checklists/README.md).
For changes to retained assets, use [Contributing](../CONTRIBUTING.md) and clearly
identify the legacy scope. The [root disclaimer](../README.md#disclaimer) applies.
