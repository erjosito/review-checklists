# Classification follow-up: twelve bounded adjudications

**Assessed:** 2026-09-13. **Status:** proposed, not applied.

The companion [JSON report](classification-followup-2026-09-13.json) records exact
per-GUID before/after field values, absence preconditions, current file/document
hashes, sources actually fetched, scope changes, overlaps and limitations.
Eleven semantic amendments are proposed; one unavailable-source record is
deferred. No YAML, queries, IDs, aliases, source metadata, helpers, tests or prior
reports were changed. This is not an exhaustive refresh.

## Principal findings

### Data Factory: the legacy spelling is real

The current Microsoft-generated [Analytics permissions
reference](https://learn.microsoft.com/en-us/azure/role-based-access-control/permissions/analytics#microsoftdatafactory)
explicitly lists **`Microsoft.DataFactory/datafactories`** read/write/delete
operations and legacy datasets/slices/gateways, separately from `factories` and
integration runtimes. It is not a typo. The official [v1-to-v2 migration
tutorial](https://raw.githubusercontent.com/Azure/Azure-DataFactory/ce4c9cab41e5e4fa66f4bddd042cab649c36a4ca/V1-V2Migration/ADFV1toV2Conversion.md)
treats product-version migration as artifact conversion requiring review.
Several retired documentation URLs now redirect or return 404; those failures
do **not** negate the positive legacy-type evidence.

Five recommendations can be maintained coherently against the current,
explicitly named **v2** model, whose [ARM
type](https://learn.microsoft.com/en-us/azure/templates/microsoft.datafactory/factories)
is `Microsoft.DataFactory/factories`. Each proposal updates guidance together
with its version applicability; none is a lexical normalization.

| GUID | Proposed adjudication |
|---|---|
| `25498f6d-bad3-47da-a43b-c6ce1d7aa9b2` | Scope to v2 Key Vault linked-service dependencies; replace the unconditional “nothing to do” recovery claim with regional exceptions and dependency recovery obligations. |
| `9ef1d6e8-32e5-42e3-911c-818b1a0bc511` | Scope to v2 Git/CI/CD; distinguish retained factory metadata from data, infrastructure, secrets and out-of-Git changes. |
| `e43a18a9-cd29-49cf-b7b1-7db8255562f2` | Scope to v2 SHIR regional recovery; a tested replacement/recovery path is required by workload objectives, not blanket Azure VM replication. |
| `aee4563a-fd83-4393-98b2-62d6dc5f512a` | Scope to v2 dependency networking recovery; remove the universal “sister region”/VNet-copy assumption. |
| `e503547c-d447-4e82-9138-a7200f1cac6d` | Scope to v2, and distinguish automatic core/Azure IR zone redundancy from Azure-SSIS node requirements and customer-owned SHIR resilience. |
| `ab91932c-9fc9-4d1b-a881-37f5e6c0cb9e` | **Defer unchanged.** The sole FTA playbook URL returns 404. `_v1` might identify a document revision, not a product generation; neither is established. |

The original authors' version intentions remain unknown. The proposed v2
amendments do not claim to migrate existing v1 deployments or silently replace
their saved assessments. A future approved catalogue amendment should recognize
both real resource types, **without making them semantic aliases**.

The [current Data Factory reliability
article](https://learn.microsoft.com/en-us/azure/reliability/reliability-data-factory)
was read through its IR, zone, regional failure, recovery, backup and SLA
sections. It supports these qualifications, including trigger-state and regional
failover caveats. The old pipeline DR link now redirects to [secure deployment
guidance](https://learn.microsoft.com/en-us/azure/data-factory/secure-your-azure-data-factory);
it was not presented as an unchanged historical source. The old Key Vault link
similarly redirects to [current Key Vault reliability
guidance](https://learn.microsoft.com/en-us/azure/reliability/reliability-key-vault).

### WAF: policy type, diagnostic host and regional proxy are different

The [current policy reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.network/frontdoorwebapplicationfirewallpolicies)
and its [2018-08-01 resource
format](https://learn.microsoft.com/en-us/azure/templates/microsoft.network/2018-08-01/frontdoorwebapplicationfirewallpolicies)
both identify `Microsoft.Network/FrontDoorWebApplicationFirewallPolicies`.
No retrieved primary evidence establishes the imported
`frontdoorwebapplicationfirewalls` token as an older equivalent. This bounded
finding does not prove that every historical API was searched.

A blanket replacement of all five tokens with the policy type would still be
wrong. [WAF monitoring
documentation](https://learn.microsoft.com/en-us/azure/web-application-firewall/afds/waf-front-door-monitor)
distinguishes Front Door Standard/Premium diagnostic hosts
(`Microsoft.Cdn/profiles`) from classic (`Microsoft.Network/frontdoors`).
Application Gateway has its own diagnostic host. The generic CDN type also
covers other products, so **Azure Front Door SKU and WAF-enabled conditions must
remain explicit**.

| GUID | Proposed applicability and guidance |
|---|---|
| `7f408960-c626-44cb-a018-347c8d790cdf` | Sentinel ingestion from WAF-enabled Front Door and Application Gateway **hosts**, not a single WAF policy type. |
| `89cc5e11-aa4d-4c3b-893d-feb99215266a` | Enable/review WAF diagnostics on those hosts, with tier/category qualifications. |
| `3b22a5a6-7e7a-48ed-9b30-e38c3f29812b` | Front Door WAF plus Application Gateway origin isolation; retain both services and policy/host applicability. |
| `1d7aa9b6-4704-4489-a804-2d88e79d17b7` | Global edge protection using Front Door and its WAF policy, retaining classic and Standard/Premium distinctions. |
| `2363cefe-179b-4599-be0d-5973cd4cd21b` | Regional application-owned WAF/partner-proxy placement, **not Front Door inside a VNet**. Propose explicit service classifications with no guessed exhaustive ARM list. |

The [CAF inbound recommendations](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/plan-for-inbound-and-outbound-internet-connectivity)
explicitly distinguish global ingress from application landing-zone proxies.
[Origin security guidance](https://learn.microsoft.com/en-us/azure/frontdoor/origin-security)
requires the combination of source filtering and the expected Front Door
identifier for public origins, not the shared service tag alone.

[Current WAF overview](https://learn.microsoft.com/en-us/azure/web-application-firewall/afds/afds-overview)
distinguishes Standard custom rules from Premium managed-rule capabilities.
Private Link is not asserted for every tier or origin. Existing classic resources
remain explicitly represented; current documentation gives a March 31, 2027
retirement date. No automatic Premium upgrade is proposed.

**Catalogue prerequisite:** the existing WAF catalogue mapping is policy-only.
Before the parent applies these host-oriented classifications, extend its
many-to-many applicability to the documented hosts. Otherwise its diagnostic
would falsely flag a WAF classification on a logging host. Do not convert this
to a one-service-per-type inference.

### Photon/Spark: reconcile guidance before assigning a pillar

`892ca809-e2b5-9a47-924a-71132bf6f902` currently has a Photon title but a Spark
task-recovery description. The [Databricks reliability
section](https://learn.microsoft.com/en-us/azure/databricks/lakehouse-architecture/reliability/best-practices#use-a-resilient-distributed-data-engine-for-all-workloads)
directly supports the description's resilient distributed-execution requirement.
It separately identifies Photon as a compatible performance engine. The [Photon
article](https://learn.microsoft.com/en-us/azure/databricks/compute/photon) confirms
its acceleration role, supported operations and fallback limitations.

Propose a title and description about **resilient SQL/DataFrame execution**,
then assign **Reliability**, explicitly classify Azure Databricks and mark the
assessment manual. Preserve the canonical Photon-containing name and GUID, empty
ARG, low severity, original import source and High Availability label. Do not
present Photon enablement as the switch for Spark task recovery.

Current public APRL main was rechecked as
`4ed61607223b49e3d0bdd9ce3127ef6e842b5463`, matching the existing dated complete
inventory. Its 29-record Databricks file was fetched and hashed; the target GUID
is absent. Thus **no current recommendation ID/hash or upstream coverage mapping
is invented**. The JSON distinguishes the repository-file hash from the genuine
item hashes of two related, but different, upstream controls.

## Overlap: evidence for coordination, not merge authorization

The JSON records exact neighbouring GUIDs and scope conflicts. Important groups:

- `1d7aa9b6…` and practice record `5e39e530…` have identical titles but different
  prior applicability.
- `3b22a5a6…`, `3f29812b…`, `b039d95d…` and `f3b0ac39…` share an origin-isolation
  theme but differ in severity, scope, pillar and legacy explanatory claims.
- `2363cefe…` overlaps `48b662d6…`; severity, metadata and an administration
  exception differ.
- The two broad logging proposals overlap narrower Front Door/Application
  Gateway logging or Sentinel recommendations. Broad/narrow coverage is not
  automatically equivalent.
- Spark task rescheduling differs from job retry/termination `84e44da6…` and
  streaming checkpoint recovery `12e9d852…`.

No overlap record was edited. The parent's duplicate work must reconcile
ownership and requirements before any merge.

## Approval and verification boundaries

1. Review the explicit semantic/version-scope changes and deferred playbook.
2. Coordinate overlap ownership, then create a **new amendment stage** with
   exact before/after hashes and source provenance additions.
3. Retain all prior manifests, including service normalization, as immutable
   history. Regression replay must verify the amendment stage before replaying
   earlier stages; do not weaken guidance, ID or query checks.
4. Preserve null `lastReviewed`, `upstreamRevision` and `validatedAt` values.
   Source access dates and Learn document revisions are not human approval,
   live validation or recommendation inventory identities.
5. Validate the proposed corpus and deterministic bundle after approved edits.
   Current reports are proposals only; existing review snapshots are untouched.

No Azure calls, deployments, paid AI, customer data, live ARG, commits or pushes
were used. Only the twelve scoped records were adjudicated.
