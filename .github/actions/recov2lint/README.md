# Validate recommendation sources and checklists

This offline composite action validates every YAML recommendation against the
single versioned contract in `v2/schema/recommendation.schema.json`, including
semantic checks and global canonical/alias ID and name uniqueness. It rejects
duplicate YAML keys, missing metadata, malformed files, and empty corpora rather
than enriching documents during validation. Legacy checklist definitions are
validated against `v2/schema/checklist.schema.json`.

```yaml
- uses: ./.github/actions/recov2lint
  with:
    folder: './v2'
```

`folder` defaults to `./v2`. `verbose` remains accepted for compatibility.
The checkout must contain `scripts` and `v2/schema`; no package-path mutation is
needed. Python 3.13 and the action's requirements are installed by the action.
For local use, install those requirements and run from the repository root:

```powershell
python -m scripts.validate_corpus --root v2
python -m unittest discover -s scripts\tests -v
```

The old Python entrypoint remains a compatibility wrapper for this same module.
Neither validation nor the separate catalog-build CI job retrieves upstream
content or runs cloud queries.
