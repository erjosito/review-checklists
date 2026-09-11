"""Loopback-only web surface over the shared review operations."""

import logging
import secrets
import sqlite3
from urllib.parse import urlsplit

from flask import (
    Flask, Response, abort, flash, has_request_context, redirect, render_template,
    request, session, url_for,
)

from review_checklists.arg import query_azure, run_query, run_selected
from review_checklists.azure_context import get_cli_subscription
from review_checklists.corpus import ReviewError, has_arg_query
from review_checklists.filters import (
    MULTI_FILTERS, filter_options, filter_values, service_name, services_for,
)
from review_checklists.review import Review, STATUSES, assessment_summary


def create_app(review: Review, executor=query_azure, subscription_lookup=get_cli_subscription) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        MAX_CONTENT_LENGTH=64 * 1024,
        TRUSTED_HOSTS=["127.0.0.1", "localhost", "[::1]"],
    )

    @app.before_request
    def protect_local_session():
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if origin and (
                urlsplit(origin).netloc != request.host
                or urlsplit(origin).scheme != request.scheme
            ):
                abort(403, "Cross-origin requests are not allowed")
            supplied = request.form.get("csrf", "")
            expected = session.get("csrf", "")
            if not expected or not supplied.isascii() or not secrets.compare_digest(supplied, expected):
                abort(403, "Invalid form token. Reload the page.")
        elif "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)

    @app.after_request
    def secure_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # no-referrer makes browser form POSTs send Origin: null, failing our origin check.
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'none'; style-src 'self'; "
            "img-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
        )
        return response

    @app.errorhandler(ReviewError)
    def review_error(error):
        app.logger.warning("Review operation failed: %s", error)
        return render_template("error.html", error=str(error)), 400

    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        app.logger.error("Review storage failed: %s", error)
        return render_template(
            "error.html", error="Review storage failed. See the terminal for details."
        ), 500

    def listing_parameters():
        return {
            key: request.args.getlist(key) if key in MULTI_FILTERS else request.args[key]
            for key in ("search", "status", "severity", "waf", "service", "with_arg", "page")
            if key in request.args
        }

    @app.context_processor
    def navigation_context():
        if not has_request_context():
            return {}
        parameters = listing_parameters()
        return {
            "listing_args": parameters,
            "review_url": url_for("index", **parameters),
            "active_subscription": session.get("active_subscription"),
        }

    def selected_scope():
        mode = request.form.get("scope_mode", "manual")
        if mode == "manual":
            return request.form.get("subscriptions", "")
        if mode == "current":
            shown_id = request.form.get("shown_subscription_id")
            displayed = session.get("active_subscription")
            if shown_id is not None and (not shown_id or not displayed or shown_id != displayed["id"]):
                raise ReviewError("The displayed subscription is stale or missing. Refresh it before running.")
            active = subscription_lookup()
            session["active_subscription"] = active
            if shown_id and shown_id != active["id"]:
                raise ReviewError(
                    "The Azure CLI subscription changed since it was displayed. "
                    "Refresh the subscription details and confirm the new scope before running."
                )
            return active["id"]
        raise ReviewError("Choose the Azure CLI subscription or manual subscription IDs")

    @app.get("/")
    def index(scope_error=None):
        if request.args.get("with_arg", "") not in ("", "1"):
            raise ReviewError("The ARG-only filter must be absent or set to 1")
        filters = {
            "search": request.args.get("search", ""),
            "status": filter_values(request.args.getlist("status")),
            "severity": filter_values(request.args.getlist("severity"), str.casefold),
            "waf": filter_values(request.args.getlist("waf"), str.casefold),
            "service": filter_values(
                request.args.getlist("service"), lambda value: service_name(value).casefold(),
            ),
            "with_arg": request.args.get("with_arg", ""),
        }
        items = review.items(**dict(filters, with_arg=filters["with_arg"] == "1"))
        try:
            page = int(request.args.get("page", "1"))
        except ValueError as exc:
            raise ReviewError("Page must be an integer") from exc
        pages = max(1, (len(items) + 49) // 50)
        if not 1 <= page <= pages:
            raise ReviewError(f"Page must be between 1 and {pages}")
        page_items = items[(page - 1) * 50:page * 50]
        summary = assessment_summary(items)
        segments = []
        offset = 0
        for status, count in summary["counts"].items():
            percentage = 100 * count / summary["total"] if summary["total"] else 0
            segments.append({
                "status": status, "count": count, "percentage": percentage,
                "offset": offset, "class": status.lower().replace(" ", "-"),
            })
            offset += percentage
        return render_template(
            "index.html", metadata=review.metadata, items=page_items,
            total=len(items), page=page, pages=pages, filters=filters,
            options=dict(filter_options(review.items()), statuses={value: value for value in STATUSES}),
            item_services={item["id"]: services_for(item["recommendation"]) for item in page_items},
            query_ids={item["id"] for item in page_items if has_arg_query(item["recommendation"])},
            matching_query_count=sum(has_arg_query(item["recommendation"]) for item in items),
            runnable_url=url_for(
                "index", page=1, _anchor="query-controls", **dict(filters, with_arg="1"),
            ),
            summary=summary, segments=segments, scope_error=scope_error,
            context_url=url_for("azure_context", _anchor="query-scope", **listing_parameters()),
            selected_ids=set(request.form.getlist("selected")),
        )

    @app.get("/item/<item_id>")
    def detail(item_id, scope_error=None):
        item = review.get(item_id)
        return render_template(
            "item.html", item=item, evidence=review.evidence(item_id),
            statuses=STATUSES, services=services_for(item["recommendation"]),
            has_query=has_arg_query(item["recommendation"]), scope_error=scope_error,
            context_url=url_for(
                "azure_context", item_id=item_id, _anchor="query-scope", **listing_parameters(),
            ),
        )

    @app.post("/azure-context", defaults={"item_id": None})
    @app.post("/item/<item_id>/azure-context")
    def azure_context(item_id):
        if item_id is not None:
            review.get(item_id)
        session.pop("active_subscription", None)
        error = None
        try:
            session["active_subscription"] = subscription_lookup()
        except ReviewError as exc:
            error = str(exc)
            app.logger.warning("Azure CLI context lookup failed: %s", error)
        page = detail(item_id, scope_error=error) if item_id is not None else index(scope_error=error)
        return page, 400 if error else 200

    @app.post("/item/<item_id>/update")
    def update(item_id):
        try:
            revision = int(request.form.get("revision", ""))
        except ValueError as exc:
            raise ReviewError("Missing or invalid item revision. Reload before saving.") from exc
        review.update(
            item_id, request.form.get("status", ""), request.form.get("comments", ""), revision,
        )
        flash("Review saved.")
        return redirect(url_for("detail", item_id=item_id, **listing_parameters()), code=303)

    @app.post("/item/<item_id>/run")
    def run(item_id):
        result = run_query(review, item_id, selected_scope(), executor)
        flash(
            f"Saved {len(result['rows'])} evidence rows"
            + (" (TRUNCATED)." if result["truncated"] else ".")
            + " Compliance status was not changed."
        )
        return redirect(url_for("detail", item_id=item_id, **listing_parameters()), code=303)

    @app.post("/run-selected")
    def run_selection():
        result = run_selected(
            review, request.form.getlist("selected"), selected_scope(), executor,
        )
        if result["failed"]:
            app.logger.warning("Selected ARG run: %s checks failed", result["failed"])
        return render_template("batch.html", result=result), 502 if result["failed"] else 200

    @app.get("/export/<format>")
    def export(format):
        if format == "json":
            content, mimetype = review.export(), "application/json"
        elif format == "html":
            content, mimetype = render_template("report.html", report=review.report()), "text/html"
        else:
            abort(404)
        return Response(content, mimetype=mimetype, headers={
            "Content-Disposition": f'attachment; filename="review.{format}"',
        })

    logging.getLogger("azure").setLevel(logging.WARNING)
    return app
