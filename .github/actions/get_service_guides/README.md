# Retrieve recommendations from Well Architected service guides

> **Deprecated manual fallback.** Automatic imports are disabled. Prefer
> LLM-assisted curation with source references, schema validation, and human
> review. Fetching content does not establish review dates or query semantics.
> Use **Run workflow** on **Deprecated manual WAF service guide import**.
> The importer only stages legacy JSON; inspect GUID reuse carefully before
> conversion. Preserve existing identities and retired-ID aliases.

Manual invocation from the repository root after installing this action's requirements:

```powershell
python .github\actions\get_service_guides\entrypoint.py 'Azure Firewall' '.\checklists-ext' 'true'
```

Install `scripts\requirements.txt` for `python -m scripts.cl v1tov2`.
That conversion enriches and validates YAML metadata. Reconcile curated
metadata explicitly before overwriting existing recommendations, then run
`python -m review_checklists corpus validate --corpus v2/recos`.
Manual and LLM-curated changes both require human review before merge.

This action retrieves the recommendations described in [Well-Architected Service Guides](https://learn.microsoft.com/azure/well-architected/service-guides/?product=popular) and stores it as a new checklist.

## Inputs

## `services`

**Optional** Service(s) whose service guide will be downloaded (leave blank for all service guides). You can specify multiple comma-separated values. Default `""`.

## `output_folder`

**Optional** Folder where the new checklists will be stored. Default `"./checklists-ext"`.

## `verbose`

**Optional** Whether script output is verbose or not. Default `"true"`.

## Example usage

```
uses: ./.github/actions/get_service_guides
with:
  output_folder: './checklists-ext'
  services: 'Azure Kubernetes Service'
```
