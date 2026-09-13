# APRL import: deprecated manual fallback

Automatic upstream imports are disabled. Prefer LLM-assisted curation with
explicit source references, schema validation, and human review. This fallback
only stages legacy JSON; importing is not evidence that a query was validated
or a recommendation reviewed.

Run **Deprecated manual APRL import** from GitHub Actions using **Run workflow**,
or invoke from the repository root after installing this action's requirements:

```powershell
python .github\actions\get_aprl\entrypoint.py '.\checklists-ext\aprl_checklist.en.json' 'true'
```

Inputs: `output_file` (default `./checklists/aprl_checklist.en.json`) and
`verbose` (default `true`). The manual workflow proposes a PR; it does not
authorize merging or assigning new identities to existing recommendations.

For YAML conversion, install `scripts\requirements.txt` and use
`python -m scripts.cl v1tov2 --input-file INPUT --output-folder OUTPUT`.
Conversion enriches and validates metadata; unknown service classifications,
query meanings, upstream revisions, and review dates must remain unknown.
Reconcile existing curated metadata and aliases explicitly before overwriting.
Validate the resulting corpus with
`python -m review_checklists corpus validate --corpus v2/recos`
before human review and merge.
