"""Loopback-only web surface over the shared review operations."""

import logging
import json
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit

import yaml
from flask import (
    Flask, Response, abort, flash, has_request_context, jsonify, redirect, render_template,
    request, session, url_for,
)
from werkzeug.exceptions import HTTPException

from review_checklists.arg import query_azure, run_query, run_selected
from review_checklists.azure_context import get_cli_subscription
from review_checklists.corpus import ReviewError, has_arg_query
from review_checklists.filters import (
    MULTI_FILTERS, filter_options, filter_values, service_name, services_for,
)
from review_checklists.review import Review, RevisionConflict, STATUSES, assessment_summary
from review_checklists.catalog import canonical_json, reject_constant, unique_object
from review_checklists.refresh import RefreshConflict, apply_refresh, plan_refresh, validate_scope
from review_checklists.corpus_admin import create_corpus_blueprint
from scripts.modules.cl_corpus import CorpusError, StrictLoader, json_value


def create_app(review: Review, executor=query_azure, subscription_lookup=get_cli_subscription) -> Flask:
    app = Flask(__name__)
    app.register_blueprint(create_corpus_blueprint(), url_prefix="/corpus")
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        # Form-encoding 20,000 four-byte characters can require 240 KB.
        MAX_CONTENT_LENGTH=256 * 1024,
        REVIEW_REFRESH_MAX_REQUEST_BYTES=16 * 1024 * 1024,
        REVIEW_REFRESH_MAX_BUNDLE_BYTES=12 * 1024 * 1024,
        REVIEW_REFRESH_MAX_CHECKLIST_BYTES=256 * 1024,
        REVIEW_REFRESH_PREVIEW_TTL=900,
        REVIEW_REFRESH_MAX_PREVIEWS=8,
        REVIEW_REFRESH_MAX_SESSION_PREVIEWS=2,
        REVIEW_REFRESH_CACHE_BYTES=64 * 1024 * 1024,
        TRUSTED_HOSTS=["127.0.0.1", "localhost", "[::1]"],
    )
    previews = {}
    preview_lock = threading.Lock()
    app.extensions["review_refresh_previews"] = previews

    @app.before_request
    def protect_local_session():
        if request.endpoint == "review_refresh_preview":
            request.max_content_length = app.config["REVIEW_REFRESH_MAX_REQUEST_BYTES"]
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
            "default-src 'self'; script-src 'self'; connect-src 'self'; style-src 'self'; "
            "img-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
        )
        return response

    def wants_json():
        return request.accept_mimetypes.best == "application/json"

    def edit_error(message, kind, code):
        if wants_json():
            return jsonify(error={"kind": kind, "message": message}), code
        if request.endpoint == "update_row" and code in (400, 403, 409, 500):
            return render_template(
                "edit_error.html", error=message, kind=kind, statuses=STATUSES,
            ), code
        return render_template("error.html", error=message), code

    @app.errorhandler(ReviewError)
    def review_error(error):
        app.logger.warning("Review operation failed: %s", error)
        conflict = isinstance(error, (RevisionConflict, RefreshConflict))
        return edit_error(
            str(error), "conflict" if conflict else "validation",
            409 if conflict and (
                wants_json() or request.endpoint == "update_row" or isinstance(error, RefreshConflict)
            ) else 400,
        )

    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        app.logger.error("Review storage failed: %s", error)
        return edit_error(
            "Review storage failed. See the terminal for details.", "storage", 500,
        )

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.method == "POST" or wants_json():
            app.logger.warning("Web request failed (%s): %s", error.code, error.description)
        if wants_json():
            kind = "auth" if error.code in (401, 403) else "validation"
            if error.code >= 500:
                kind = "server"
            return jsonify(error={"kind": kind, "message": error.description}), error.code
        if request.endpoint == "update_row" and error.code == 403:
            return edit_error(error.description, "auth", 403)
        return error

    def listing_parameters():
        return {
            key: request.args.getlist(key) if key in MULTI_FILTERS else request.args[key]
            for key in ("search", "status", "severity", "waf", "service", "with_arg", "paginate", "page")
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

    def expire_previews():
        now = time.monotonic()
        for handle, record in list(previews.items()):
            if record["expires_at"] <= now:
                del previews[handle]

    def uploaded_text(field, limit):
        upload = request.files.get(field)
        if upload is None or not upload.filename:
            raise ReviewError(f"Choose a {field} file to upload.")
        data = upload.stream.read(limit + 1)
        if len(data) > limit:
            abort(413, f"The {field} file exceeds its {limit // 1024} KiB upload limit.")
        try:
            return data.decode("utf-8")
        except UnicodeError as exc:
            raise ReviewError(f"The {field} file must be UTF-8 text.") from exc

    @app.get("/review-refresh")
    def review_refresh():
        metadata = review.metadata
        try:
            scope = validate_scope(json.loads(metadata["review_scope"]) if "review_scope" in metadata else None)
        except (ValueError, TypeError) as exc:
            raise ReviewError("The saved review scope is invalid. Inspect it before refreshing.") from exc
        return render_template(
            "review_refresh.html", metadata=metadata, saved_scope=scope,
            bundle_limit=app.config["REVIEW_REFRESH_MAX_BUNDLE_BYTES"] // (1024 * 1024),
        )

    @app.post("/review-refresh/preview")
    def review_refresh_preview():
        if (
            set(request.form) - {"csrf", "add_new", "refresh_scope"}
            or set(request.files) - {"bundle", "checklist"}
            or any(len(request.form.getlist(key)) != 1 for key in request.form)
            or any(len(request.files.getlist(key)) != 1 for key in request.files)
        ):
            raise ReviewError("Ambiguous or unsupported refresh upload fields.")
        add_new = request.form.get("add_new", "")
        if add_new not in ("", "1"):
            raise ReviewError("Invalid add-new selection.")
        mode = request.form.get("refresh_scope", "saved")
        if mode not in ("saved", "all", "checklist"):
            raise ReviewError("Choose the saved scope, all corpus, or an uploaded checklist.")
        scope = {"kind": "all"} if mode == "all" else None
        try:
            bundle = json.loads(
                uploaded_text("bundle", app.config["REVIEW_REFRESH_MAX_BUNDLE_BYTES"]),
                object_pairs_hook=unique_object, parse_constant=reject_constant,
            )
            if mode == "checklist":
                text = uploaded_text("checklist", app.config["REVIEW_REFRESH_MAX_CHECKLIST_BYTES"])
                if any(isinstance(event, yaml.AliasEvent) for event in yaml.parse(text)):
                    raise ReviewError("Checklist YAML aliases are not supported; upload an expanded definition.")
                scope = {"kind": "checklist", "definition": json_value(yaml.load(text, Loader=StrictLoader))}
            elif request.files.get("checklist") and request.files["checklist"].filename:
                raise ReviewError("Select uploaded checklist scope to use the checklist file.")
        except (ValueError, CorpusError, yaml.YAMLError, RecursionError) as exc:
            raise ReviewError(f"Invalid refresh upload: {exc}") from exc
        options = {"add_new": add_new == "1", "scope": scope}
        plan = plan_refresh(review, bundle, **options)
        size = len(canonical_json({"bundle": bundle, "plan": plan}).encode("utf-8"))
        owner = session["csrf"]
        with preview_lock:
            expire_previews()
            if sum(record["owner"] == owner for record in previews.values()) >= app.config["REVIEW_REFRESH_MAX_SESSION_PREVIEWS"]:
                abort(429, "This session already has two pending previews. Apply one or wait for them to expire.")
            if (
                len(previews) >= app.config["REVIEW_REFRESH_MAX_PREVIEWS"]
                or size + sum(record["size"] for record in previews.values()) > app.config["REVIEW_REFRESH_CACHE_BYTES"]
            ):
                abort(503, "Local refresh preview storage is full or this preview is too large. Wait for expiry or use the CLI.")
            handle = secrets.token_urlsafe(32)
            previews[handle] = {
                "owner": owner, "expires_at": time.monotonic() + app.config["REVIEW_REFRESH_PREVIEW_TTL"],
                "size": size, "bundle": bundle, "options": options, "token": plan["token"],
            }
        return render_template(
            "review_refresh_preview.html", plan=plan, handle=handle,
            expiry_minutes=app.config["REVIEW_REFRESH_PREVIEW_TTL"] / 60,
        )

    @app.post("/review-refresh/apply")
    def review_refresh_apply():
        if set(request.form) != {"csrf", "handle"} or any(len(request.form.getlist(key)) != 1 for key in request.form):
            raise ReviewError("Apply accepts only its stored preview handle. Preview again to change options.")
        handle = request.form["handle"]
        with preview_lock:
            expire_previews()
            record = previews.get(handle)
            if record is None:
                abort(410, "This preview is missing, expired, or already used. Create a new preview.")
            if not secrets.compare_digest(record["owner"], session["csrf"]):
                abort(403, "This preview belongs to another browser session. Create your own preview.")
            # Consume before releasing the lock: even concurrent double clicks cannot replay apply.
            del previews[handle]
        result = apply_refresh(review, record["bundle"], token=record["token"], **record["options"])
        if result["applied"]:
            flash(f"Refresh applied. Assessments and evidence were retained. Backup: {result['backup_path']}")
        else:
            flash("No changes were needed. No backup or history entry was created.")
        return redirect(url_for("review_refresh_history"), code=303)

    @app.get("/review-refresh/history")
    def review_refresh_history():
        history = list(reversed(review.refresh_history()))
        return render_template("review_refresh_history.html", history=history, metadata=review.metadata)

    @app.get("/refresh", endpoint="refresh")
    @app.get("/")
    def index(scope_error=None):
        if request.args.get("with_arg", "") not in ("", "1"):
            raise ReviewError("The ARG-only filter must be absent or set to 1")
        if request.args.get("paginate", "") not in ("", "1"):
            raise ReviewError("Pagination must be absent or set to 1")
        # Existing bookmarked page URLs keep their paginated behavior.
        pagination_enabled = request.args.get("paginate") == "1" or "page" in request.args
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
        pages = max(1, (len(items) + 49) // 50) if pagination_enabled else 1
        if request.endpoint == "refresh":
            parameters = listing_parameters()
            if "page" in parameters:
                parameters["page"] = max(1, min(page, pages))
            return redirect(url_for("index", **parameters), code=303)
        if not 1 <= page <= pages:
            raise ReviewError(f"Page must be between 1 and {pages}")
        page_items = items[(page - 1) * 50:page * 50] if pagination_enabled else items
        navigation_filters = dict(filters, **({"paginate": "1"} if pagination_enabled else {}))
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
            "index.html", metadata=review.metadata, review_file=review.path.name, items=page_items,
            total=len(items), page=page, pages=pages, filters=filters,
            pagination_enabled=pagination_enabled, navigation_filters=navigation_filters,
            options=dict(filter_options(review.items()), statuses={value: value for value in STATUSES}),
            refresh_url=url_for("refresh", **listing_parameters()),
            item_services={item["id"]: services_for(item["recommendation"]) for item in page_items},
            query_ids={item["id"] for item in page_items if has_arg_query(item["recommendation"])},
            matching_query_count=sum(has_arg_query(item["recommendation"]) for item in items),
            runnable_url=url_for(
                "index", _anchor="query-controls",
                **dict(navigation_filters, with_arg="1", **({"page": 1} if pagination_enabled else {})),
            ),
            summary=summary, segments=segments, scope_error=scope_error,
            reassessment_count=sum(item["refresh_state"]["needs_reassessment"] for item in items),
            retained_count=sum(item["refresh_state"]["currency"] != "current" for item in items),
            context_url=url_for("azure_context", _anchor="query-scope", **listing_parameters()),
            selected_ids=set(request.form.getlist("selected")),
        )

    @app.post("/metadata")
    def update_metadata():
        try:
            revision = int(request.form.get("revision", ""))
        except ValueError as exc:
            raise ReviewError("Missing or invalid metadata revision. Reload before saving.") from exc
        review.update_metadata(
            name=request.form.get("name", ""), description=request.form.get("description", ""),
            revision=revision,
        )
        flash("Review details saved. The database filename was not changed.")
        return redirect(url_for("index", **listing_parameters()), code=303)

    @app.get("/item/<item_id>")
    def detail(item_id, scope_error=None):
        item = review.get(item_id)
        return render_template(
            "item.html", item=item, evidence=review.evidence(item_id),
            metadata=review.metadata,
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
        confirmation = request.form.get("confirm_current_assessment", "")
        if confirmation not in ("", "1"):
            raise ReviewError("Invalid assessment confirmation.")
        review.update(
            item_id, request.form.get("status", ""), request.form.get("comments", ""), revision,
            confirm_current_assessment=confirmation == "1",
        )
        flash("Review saved.")
        return redirect(url_for("detail", item_id=item_id, **listing_parameters()), code=303)

    @app.post("/item/<item_id>/assessment")
    def update_row(item_id):
        raw_revision = request.form.get("revision", "")
        if not raw_revision.isascii() or not raw_revision.isdecimal() or len(raw_revision) > 16:
            raise ReviewError("Missing or invalid item revision. Reload before saving.")
        revision = int(raw_revision)
        status = request.form.get("status", "")
        comments = request.form.get("comments", "")
        review.update(item_id, status, comments, revision)
        if wants_json():
            # A subsequent read could observe a different writer's revision.
            return jsonify(revision=revision + 1, status=status, comments=comments)
        flash("Assessment saved.")
        return redirect(url_for("refresh", **listing_parameters()), code=303)

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
