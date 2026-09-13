"""Offline, strict validation for recommendation sources and legacy checklists."""

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .modules.cl_corpus import CorpusError, load_yaml_document, validate_corpus


def validate_recommendation_folder(folder):
    folder = Path(folder)
    if not folder.is_dir():
        raise CorpusError(f"Recommendation folder does not exist: {folder}")
    documents = []
    for path in sorted(folder.rglob('*')):
        if path.suffix.lower() in ('.yaml', '.yml'):
            documents.append(load_yaml_document(path))
    validate_corpus(documents)
    return len(documents)


def validate_checklist_folder(folder, schema_path):
    folder = Path(folder)
    if not folder.is_dir():
        raise CorpusError(f"Checklist folder does not exist: {folder}")
    schema = json.loads(Path(schema_path).read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    count = 0
    for path in sorted(folder.rglob('*')):
        if path.suffix.lower() in ('.yaml', '.yml'):
            document = load_yaml_document(path)
            errors = sorted(validator.iter_errors(document), key=lambda error: str(error.path))
            if errors:
                raise CorpusError(f"{path}: {errors[0].message}")
            count += 1
    if not count:
        raise CorpusError(f"No checklist documents found: {folder}")
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('v2'))
    args = parser.parse_args(argv)
    try:
        recommendations = validate_recommendation_folder(args.root / 'recos')
        checklists = validate_checklist_folder(
            args.root / 'checklists', args.root / 'schema' / 'checklist.schema.json',
        )
    except (CorpusError, OSError, ValueError, SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Validated {recommendations} recommendations and {checklists} checklists.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
