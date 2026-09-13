# Corpus refresh: September 2026

**Historical first stage.** The subsequent
[all-pillar/APRL assessment](full-refresh-2026-09-11/README.md) adds six records
and records further source-backed corrections and explicit review gaps.
The counts and draft bundle below describe this initial Cost/merge stage.
The [September 13 follow-up](followup-2026-09-13.md) records subsequent
classification/Key Vault corrections and two further confirmed storage merges.

This is a bounded, source-backed refresh and conservative deduplication pass, not
an assertion that every recommendation is current or every duplicate is resolved.
The YAML corpus remains authoritative; existing saved reviews remain pinned.

## Integrated result

| Measure | Before | After |
| --- | ---: | ---: |
| Canonical recommendations | 2,052 | 2,005 |
| Retired identities retained as aliases | 0 | 55 |
| Recommendations with a primary ARG query | 397 | 426 |
| Canonical Cost recommendations | 227 | 226 |
| Cost recommendations with a primary ARG query | 2 | 31 |

The canonical count is **2,052 + 8 additions - 55 retirements = 2,005**.
The 55 retirements span 54 confirmed groups: 45 non-Cost groups and nine Cost
groups. Existing original identities remain addressable through canonical IDs
or aliases; saved-review assessments and evidence were not merged or rewritten.

The Cost content stage updated 48 existing recommendations and added eight,
temporarily producing 235 Cost records. The separate follow-on merge stage
consolidated 18 previously unrefreshed records into nine survivors, producing
226 Cost records. All 56 refreshed/added files were unchanged by that merge
stage; 161 original Cost records remain truly untouched.

The ALZ checklist still selects 236 records. Application delivery now selects 38
rather than 37: the refreshed orphan-networking recommendation
`64f9a19a-f29c-495d-94c6-c7919ca0f6c5` has corrected resource applicability.
That is a documented Cost scope correction, not a duplicate-merge side effect.

## Evidence map

- [Cost sources and coverage](cost-sources.md): the 30 verified public sources,
  access dates, supported themes, reading boundaries, gaps and refresh procedure.
- [Cost refresh report](cost-refresh-report.md): applied content changes,
  query accounting, additional evidence requirements and technical limitations.
- [Cost research](cost-research.json): proposals, verified source inventory,
  all 34 query variants and rejected or qualified source samples.
- [Cost refresh manifest](cost-refresh-manifest.json): the historical content
  stage, exact affected GUIDs, before snapshots and application rationale.
- [Cost alias migration](cost-alias-migration.json): actual follow-on merge
  mappings, before snapshots and content hashes.
- [Duplicate audit](duplicate-audit.json): full-corpus candidate retrieval and
  bounded semantic adjudication, including uncertain and rejected matches.
- [Alias migration](alias-migration.json): applied merge accounting and identity/
  checklist compatibility evidence across the stages.
- [Post-refresh Cost duplicate review](post-cost-duplicate-review.json):
  reconciliation of the 11 initially deferred Cost groups.
- [URL normalization](url-normalization.json): two whitespace-only URL repairs
  required for strict source validation.

The applied manifests, including `non-cost-merge-manifest.json` and
`post-cost-safe-merge-manifest.json`, are audit records, not commands to rerun.

## Limits and follow-up

Seventeen confirmed duplicate groups remain technically deferred because scope,
classification, severity, automation or guidance requires reconciliation.
The original audit also records 22 uncertain groups and 393 unadjudicated
candidate pairs. Candidate pairs and groups are different units and must not
be summed into a count of duplicate recommendations.

All 31 refreshed primary Cost queries are **unvalidated inventory**. There are
28 unique primary KQL texts and six supplemental-only variants retained in the
research catalog. Supplemental variants are not executed by the UI. No live
Azure query, savings verification or compliance certification occurred.

Validation covers schema/identity consistency, deterministic bundles, historical
identity resolution and checklist membership. It cannot establish exhaustive
service coverage, technical truth or resource-property availability in a live
subscription. See the Cost coverage report before choosing the next refresh.

## Local draft bundle

The ignored generated artifact `dist\catalog-2026.09.11-draft.json` has version
`2026.09.11-draft` and content hash:

```text
sha256:813606c7b45c0cb5fc6a6e510fe1bc68671fa9be857ed9718c311851df2c003c
```

Repeated builds produced identical bytes, and a temporary review initialized
from the bundle resolved every retired alias. The file is generated output, not
a committed release or a publisher-signed artifact. Rebuild using the
[corpus contract](../corpus-contract.md); use a new output path if one exists.
