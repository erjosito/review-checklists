"""Run with python -m review_checklists from the repository root."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from review_checklists.corpus import ReviewError, load_corpus, read_document, select_checklist
from review_checklists.filters import SEVERITIES, WAF_PILLARS
from review_checklists.review import Review, STATUSES


ROOT = Path(__file__).resolve().parent.parent


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Local-first Azure review checklists")
    result.add_argument("--review", type=Path, default=Path(".reviews") / "review.sqlite3")
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a review with a pinned v2 corpus snapshot")
    init.add_argument("--corpus", type=Path, default=ROOT / "v2" / "recos")
    init.add_argument("--checklist", type=Path, help="Optional v2 YAML checklist definition")
    init.add_argument("--name", default="Azure review")
    listing = commands.add_parser("list", help="List review items as JSON")
    listing.add_argument("--search", default="")
    listing.add_argument("--status", choices=STATUSES, nargs="+", action="extend", default=[],
                         help="One or more statuses (OR); this option can be repeated")
    listing.add_argument("--severity", type=str.casefold, choices=SEVERITIES,
                         nargs="+", action="extend", default=[],
                         help="One or more severities (OR); this option can be repeated")
    listing.add_argument("--waf", type=str.casefold, choices=WAF_PILLARS,
                         nargs="+", action="extend", default=[],
                         help="One or more WAF pillars (OR); 'none' includes unspecified pillars")
    listing.add_argument("--service", nargs="+", action="extend", default=[],
                         help="One or more service names/aliases or ARM types (OR); 'none' includes general guidance")
    listing.add_argument("--with-arg", action="store_true", help="Only checks with nonempty ARG queries")
    show = commands.add_parser("show", help="Show a recommendation and its evidence")
    show.add_argument("id")
    update = commands.add_parser("update", help="Set status/comments, preserving unspecified fields")
    update.add_argument("id")
    update.add_argument("--status", choices=STATUSES)
    update.add_argument("--comments")
    update.add_argument("--revision", type=int, help="Reject edits based on an outdated revision")
    run = commands.add_parser("run", help="Explicitly execute one pinned ARG query")
    run.add_argument("id")
    run.add_argument("--subscriptions", required=True, help="Comma-separated subscription GUIDs")
    export = commands.add_parser("export", help="Export a JSON or standalone HTML report")
    export.add_argument("--format", choices=("json", "html"), default="json")
    export.add_argument("--output", required=True, type=Path)
    serve = commands.add_parser("serve", help="Serve the web UI on 127.0.0.1 only")
    serve.add_argument("--port", type=int, default=8765)
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            recos = load_corpus(args.corpus)
            if args.checklist:
                recos = select_checklist(recos, read_document(args.checklist))
            Review.create(args.review, args.name, recos, args.corpus)
            print(f"Created {args.review} with {len(recos)} recommendations.")
            return 0
        review = Review(args.review)
        if args.command == "list":
            print(json.dumps(
                review.items(
                    args.search, args.status, severity=args.severity,
                    waf=args.waf, service=args.service, with_arg=args.with_arg,
                ), ensure_ascii=False, indent=2,
            ))
        elif args.command == "show":
            print(json.dumps(
                dict(review.get(args.id), evidence=review.evidence(args.id)),
                ensure_ascii=False, indent=2,
            ))
        elif args.command == "update":
            if args.status is None and args.comments is None:
                raise ReviewError("Specify --status or --comments")
            item = review.get(args.id)
            review.update(
                args.id, args.status if args.status is not None else item["status"],
                args.comments if args.comments is not None else item["comments"],
                args.revision if args.revision is not None else item["revision"],
            )
            print("Review saved.")
        elif args.command == "run":
            from review_checklists.arg import run_query
            result = run_query(review, args.id, args.subscriptions)
            print(f"Saved {len(result['rows'])} rows; truncated={result['truncated']}. "
                  "Compliance status unchanged.")
        elif args.command == "export":
            if args.format == "html":
                from flask import render_template
                from review_checklists.web import create_app
                with create_app(review).app_context():
                    content = render_template("report.html", report=review.report())
            else:
                content = review.export()
            # Exclusive creation also prevents accidentally overwriting the review database.
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(content)
            print(f"Exported {args.output}")
        elif args.command == "serve":
            if not 1 <= args.port <= 65535:
                raise ReviewError("Port must be between 1 and 65535")
            from waitress import serve
            from review_checklists.web import create_app
            print(f"Open http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
            serve(create_app(review), host="127.0.0.1", port=args.port)
    except (ReviewError, OSError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
