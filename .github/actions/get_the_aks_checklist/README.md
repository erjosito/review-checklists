# Retrieve recommendations from the-aks-checklist

> **Deprecated manual fallback.** Automatic imports are disabled. Prefer
> LLM-assisted curation with explicit source references, schema validation, and
> human review. Use **Run workflow** on **Deprecated manual AKS import**.
> The importer stages legacy JSON, not reviewed or validated YAML.

Manual invocation from the repository root after installing this action's requirements:

```powershell
python .github\actions\get_the_aks_checklist\entrypoint.py '.\checklists-ext\theaks_checklist.en.json' '.\checklists\aks_checklist.en.json' 'true'
```

Install `scripts\requirements.txt` for `python -m scripts.cl v1tov2`.
Conversion enriches and validates metadata, preserving source GUIDs.
Reconcile curated metadata and retired-ID aliases explicitly before overwriting;
never infer query meaning or review evidence from an import.
Run `python -m review_checklists corpus validate --corpus v2/recos` and obtain
human review before merging manual or LLM-curated changes.

This action retrieves the recommendations stored in [the-aks-checklist repo](https://github.com/lgmorand/the-aks-checklist/tree/master/data/en/items) and stores it as a new checklist.

## Inputs

## `output_file`

**Optional** File where the new checklist will be stored. Default `"./checklists/theaks_checklist.en.json"`.

## `checklist_file`

**Optional** File where the existing checklist is located. Default `"./checklists/aks_checklist.en.json"`.

## `verbose`

**Optional** Whether verbose output is generated. Default `"true"`.


## Example usage

```
uses: ./.github/actions/get_the_aks_checklist
with:
  output_file: './checklists/theaks_checklist.en.json'
  checklist_file: './checklists/aks_checklist.en.json'
```