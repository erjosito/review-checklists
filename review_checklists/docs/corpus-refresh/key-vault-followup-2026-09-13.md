# Bounded Key Vault source-verification follow-up — 2026-09-13

**Proposal only; corpus unchanged.** Eight existing records explicitly marked
`needsmanualreview` in `full-refresh-2026-09-11/security-manifest.json` were frozen
against their live corpus documents before research. Outcomes: **seven proposed
guidance updates, one supported unchanged, zero unresolved source decisions**.
Deployment-specific limitations remain recorded; this is not human approval,
live validation, or comprehensive Key Vault coverage.

The [JSON companion](key-vault-followup-2026-09-13.json) is the authoritative
machine-readable proposal: exact full `before` and proposed `after` documents,
field-level `proposedEdits` (including absence versus null), original file and
content hashes, historical-entry hashes, aliases, evidence and per-record query
caveats. All proposals are `applied: false`. Parent integration must recheck the
frozen hashes and apply only accepted edits in a separate follow-up stage.
Do not replace the historical Security manifest or its recorded outcomes.

## Frozen scope and decisions

The bound is Key Vault access/delegation, usage auditing, certificate renewal,
and direct certificate/secret integration with APIM, VMs, AKS and Application
Gateway. It excludes other Security records, vault geography/disaster recovery,
disk encryption, Managed HSM and other service families. No IDs were added,
merged, renamed or retired.

### 1. Key Vault delegation — proposed update

`b12308ca-5017-4f15-9e3a-b3693829e7e3`

**Before:** “Delegate Key Vault instantiation and privileged access and use Azure
Policy to enforce a consistent compliant configuration.”

**Proposed title:** “Delegate Key Vault provisioning and privileged access through
least-privilege Azure RBAC, and enforce vault configuration with Azure Policy.”

The proposed description separates control-plane provisioning from data-plane
object access, scopes delegation, introduces eligible just-in-time privileged
roles where applicable, and clarifies that Azure Policy configuration checks do
not replace authorization review. This preserves the delegation requirement
rather than treating every vault contributor as an authorized secret reader.
Evidence: **kv-secure**, **kv-rbac**.

### 2. Key Vault usage auditing — proposed update

`17d6326a-f625-4ca4-9e56-95f2223ace8c`

**Before:** “Use the platform-central Azure Monitor Log Analytics workspace to
audit key, certificate, and secret usage within each instance of Key Vault.”

**Proposed title:** “Enable Key Vault audit logging and route key, certificate,
and secret usage events to the designated security monitoring destination.”

Require diagnostic settings collecting `AuditEvent`; preserve platform-central
Log Analytics when organizational architecture requires it, without falsely
making one workspace topology a universal service requirement. Other supported
destinations are valid. Verify ingestion, retention and access. Automatically
collected metrics and subscription Activity Log are not substitutes for
data-plane resource logs. Evidence: **kv-monitor**, **kv-monitor-reference**,
**kv-secure**.

### 3. Certificate-authority renewal — proposed update

`6d70ba6c-97be-4995-8904-83845c986cb2`

**Before:** “Automate the certificate management and renewal process with public
certificate authorities to ease administration.”

**Proposed title:** “Automate Key Vault certificate renewal with supported
integrated certificate authorities, and define renewal workflows for other issuers.”

Distinguish built-in integrated DigiCert/GlobalSign renewal from nonintegrated CA
expiry notification and external/manual issuance/import. Renewal creates a new
version; consumers must actually retrieve and use it. Storing an imported
certificate is not proof of automatic issuer renewal. Evidence:
**kv-certificate-renewal**.

### 4. APIM named-value secrets — proposed update

`f8af3d94-1d2b-4070-846f-849197524258`

**Before:** “Ensure that secrets (Named values) are stored an Azure Key Vault so
they can be securely accessed and updated”

**Proposed title:** “Store secret API Management named values in Azure Key Vault
where the integration is supported.”

Scope the recommendation to secret values, not ordinary plain named values.
Require managed-identity secret access and versionless references for automatic
refresh; document the four-hour interval and workspace exclusion. Restrict
policy editing and tracing because resolved secret values can still be exposed
through authorized APIM functionality. Evidence: **apim-named-values**.

### 5. APIM TLS certificates — proposed update

`39460bdb-156f-4dc2-a87f-1e8c11ab0998`

**Before:** “Ensure that custom SSL certificates are stored an Azure Key Vault
so they can be securely accessed and updated”

**Proposed title:** “Use Azure Key Vault to manage customer-provided TLS
certificates for API Management where Key Vault integration is supported.”

Use certificate objects and the required managed-identity access to their secret
material. Distinguish custom-domain synchronization from backend-client
certificate rotation. The latter documents a four-hour refresh and versionless
references; the custom-domain page says updates can take one to two days in SLA
tiers and describes cached-certificate expiry when access fails. Do not turn
these into a universal four-hour promise. Backend-client Key Vault integration
is unavailable in workspaces. Evidence: **apim-custom-domain**,
**apim-backend-certificates**, **kv-rbac**.

The separate free managed-certificate preview and its dated suspension notice
were not used to infer current availability. No TLS trust or chain-validation
changes are proposed.

### 6. VM certificate delivery — supported unchanged

`08be36ad-0190-4740-b002-9adae9be0cca`

**Before and proposed guidance, unchanged:** “Protect secrets such as the
certificates that you need to protect data in transit. Consider using the Azure
Key Vault extension for Windows or Linux that automatically refreshes the
certificates stored in a key vault. When it detects a change in the certificates,
the extension retrieves and installs the corresponding certificates.”

Both platform documents directly support that behavior. Only provenance
citations are proposed. Current 4.x operating-system, identity, secret-URL and
upgrade constraints remain deployment checks, not a mandate to force a major
upgrade. Successful retrieval/installation does not prove application reload.
Evidence: **vm-key-vault-windows**, **vm-key-vault-linux**.

### 7. AKS secrets delivery — proposed update

`5e3df584-eccc-4d97-a3b6-bcda3b50eb2e`

**Before:** “Store your secrets in Azure Key Vault with the CSI Secrets Store driver”

**Proposed title:** “Mount secrets stored in Azure Key Vault into AKS workloads
with the Azure Key Vault provider for Secrets Store CSI Driver.”

The provider mounts existing source objects; it is not a credential-issuance
mechanism. Configure `SecretProviderClass` and authorized identity access.
Enable rotation when new source versions must propagate and verify application
reload. Kubernetes Secret synchronization is optional. Environment-variable
consumers require pod restarts; `subPath` mounts do not automatically update.
Evidence: **aks-csi-provider**, **aks-csi-rotation**.

### 8. Application Gateway TLS — proposed update

`5692cf86-c36a-4c1b-a73f-1a73f5728cd0`

**Before title:** “Use Azure Key Vault to store TLS certificates”

**Before description:** “Application Gateway can be integrated with Key Vault.
This provides stronger security, easier separation of roles and responsibilities,
support for managed certificates, and an easier certificate renewal and rotation
process.”

**Proposed title:** “Use Azure Key Vault certificates for Application Gateway v2
HTTPS listeners.”

Specify v2 support, an enabled software-backed PFX certificate with exportable
private key, a user-assigned identity and secret-read permission. Prefer a
versionless secret identifier for four-hour polling. Verify connectivity and
alert on access failures that can disable listeners. HSM-backed certificates
are unsupported. Evidence: **appgw-key-vault**.

Existing alias `2e0b6e8f-2784-4ea8-bec5-a128ddce6c98`
(`wafsg-AzureKeyVaultTlsCertificates`) and its source/labels remain unchanged.
It represents the same TLS/Key Vault requirement and is not a separate
canonical record in the historical Security manifest. No further merge is proposed.

## Verified public sources and actual access

All sources below were fetched as public document content on **2026-09-13,
UTC+03:00** (the research window starts on September 12 in UTC). Search snippets
were discovery only. The JSON records the read sections and bounds: a fetched
section is not a claim that every paragraph or linked article was reviewed.
Page-reported revisions are observations, not separately verified repository
commits and not replacements for unknown corpus `upstreamRevision`.

| Evidence key | Fetched source |
|---|---|
| kv-secure | [Secure your Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault) — previous best-practices URL redirects here |
| kv-rbac | [Grant permission to applications to access an Azure key vault using Azure RBAC](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide) |
| kv-monitor | [Monitor Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/monitor-key-vault) |
| kv-monitor-reference | [Monitoring data reference for Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/monitor-key-vault-reference) |
| kv-certificate-renewal | [About Azure Key Vault certificate renewal](https://learn.microsoft.com/en-us/azure/key-vault/certificates/overview-renew-certificate) |
| apim-named-values | [How to Use Named Values in Azure API Management policies](https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-properties) |
| apim-custom-domain | [Configure custom domain name for Azure API Management instance](https://learn.microsoft.com/en-us/azure/api-management/configure-custom-domain) |
| apim-backend-certificates | [Secure API Management Backend Using Client Certificate Authentication](https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-mutual-certificates) |
| vm-key-vault-windows | [Azure Key Vault VM extension for Windows](https://learn.microsoft.com/en-us/azure/virtual-machines/extensions/key-vault-windows) |
| vm-key-vault-linux | [Azure Key Vault virtual machine extension for Linux](https://learn.microsoft.com/en-us/azure/virtual-machines/extensions/key-vault-linux) |
| aks-csi-provider | [Use the Azure Key Vault Provider for Secrets Store CSI Driver for AKS Secrets](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver) |
| aks-csi-rotation | [Azure Key Vault Provider for Secrets Store CSI Driver for AKS Configuration Options](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-configuration-options) |
| appgw-key-vault | [TLS termination with Azure Key Vault certificates](https://learn.microsoft.com/en-us/azure/application-gateway/key-vault-certs) |

## Query and evidence boundaries

All eight existing `queries` objects are empty. They remain empty, and existing
`automation.status: unknown`, `automation.validatedAt: null`,
`provenance.lastReviewed: null` and `provenance.upstreamRevision: null` remain
unchanged. No ARG, deployment, tenant lookup, certificate/private-key download
or secret retrieval occurred.

Configuration inventory does not prove effective authorization, audit ingestion,
certificate renewal, secret rotation, runtime application reload or compliance.
The JSON records the distinct additional evidence each requirement needs.
Empty results would not prove compliance. No executable query or automatic
verdict is proposed.

No remote inventory or upstream recommendation-ID mapping was created.
Thirteen document sources are not a source recommendation denominator;
upstream coverage percentage is explicitly null. Seven proposed updates are
not seven applied changes or seven human-approved requirements.

## Apply and validation handoff

1. Recheck the eight frozen IDs, canonical names, aliases and before hashes.
2. Reconcile any concurrent duplicate/classification proposals by GUID. Preserve
   existing GUID/name/source/aliases and unchanged classification/query fields.
3. If accepted, apply the explicit field edits through the parent's separate
   follow-up ledger; retain the original historical manifest byte-for-byte.
4. Validate accepted records and run affected historical replay/integration
   tests through that stage. Source-backed prose alone is not a runtime test.

The JSON validation section records offline checks of the frozen live files,
historical hashes, exact edit replay, proposed recommendation schema validity,
identity preservation and null dates. It does not claim tests of deployed Azure
behavior.
