"use strict";

(() => {
    if (!window.fetch || !window.AbortController || !window.FormData || !window.URLSearchParams) {
        return;
    }
    const dirtyRows = new Set();
    const controllers = new WeakMap();
    const overview = document.getElementById("overview-stale");
    const markOverviewStale = () => {
        overview.hidden = false;
        document.getElementById("overview-title").textContent = "Assessment overview (needs refresh)";
    };
    const equal = (a, b) => a.status === b.status && a.comments === b.comments;

    const controllerFor = (cell) => {
        if (controllers.has(cell)) {
            return controllers.get(cell);
        }
        cell.dispatchEvent(new Event("assessment-activate", {bubbles: true}));
        const form = document.getElementById(cell.dataset.assessment);
        const status = cell.querySelector('[name="status"]');
        const comments = cell.querySelector('[name="comments"]');
        const revision = cell.querySelector('[name="revision"]');
        const feedback = cell.querySelector(".save-state");
        const button = cell.querySelector(".save-assessment");
        const compare = cell.querySelector(".conflict-help");
        const preview = cell.querySelector(".comments-preview");
        const current = () => ({status: status.value, comments: comments.value});
        const initial = {
            status: Array.from(status.options).find((option) => option.defaultSelected).value,
            comments: comments.defaultValue,
        };
        const state = {
            acknowledged: initial, saving: false, saved: false, unacknowledged: false,
            error: null, timer: null,
        };
        feedback.setAttribute("role", "status");
        feedback.setAttribute("aria-live", "polite");

        const render = () => {
            const dirty = !equal(current(), state.acknowledged);
            if (dirty || state.saving || state.error || state.unacknowledged) {
                dirtyRows.add(state);
            } else {
                dirtyRows.delete(state);
            }
            preview.textContent = comments.value.slice(0, 100) || "No comments";
            button.hidden = !state.error;
            button.disabled = state.saving || state.error?.kind === "conflict";
            button.textContent = "Retry save";
            compare.hidden = !state.error;
            if (state.error) {
                feedback.textContent = `Error (${state.error.kind}): ${state.error.message} Draft retained here.`;
                cell.dataset.saveState = "error";
            } else if (state.saving) {
                feedback.textContent = "Saving... Edits remain unsaved until acknowledged.";
                cell.dataset.saveState = "saving";
            } else if (dirty || state.unacknowledged) {
                feedback.textContent = "Unsaved";
                cell.dataset.saveState = "unsaved";
            } else {
                feedback.textContent = state.saved ? "Saved" : "No unsaved changes";
                cell.dataset.saveState = state.saved ? "saved" : "clean";
            }
        };

        const save = async () => {
            clearTimeout(state.timer);
            state.timer = null;
            if (state.saving || state.error || (equal(current(), state.acknowledged) && !state.unacknowledged)) {
                return;
            }
            const submitted = current();
            // Match the server's Unicode character limit, not UTF-16 code units.
            if (Array.from(submitted.comments).length > 20000) {
                state.error = {kind: "validation", message: "Comments must be at most 20,000 characters. Shorten them and retry."};
                render();
                return;
            }
            const expectedRevision = Number(revision.value);
            const body = new URLSearchParams(new FormData(form));
            body.set("status", submitted.status);
            body.set("comments", submitted.comments);
            state.saving = true;
            state.unacknowledged = true;
            render();
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 15000);
            try {
                const response = await fetch(form.action, {
                    method: "POST", headers: {Accept: "application/json"},
                    credentials: "same-origin", body, signal: controller.signal,
                    redirect: "error",
                });
                if (!response.headers.get("Content-Type")?.includes("application/json")) {
                    throw new Error("Unexpected server response. Save outcome is unknown; compare the saved assessment before retrying.");
                }
                const result = await response.json();
                if (!response.ok) {
                    state.error = result.error || {
                        kind: "server", message: `HTTP ${response.status}. Check the terminal before retrying.`,
                    };
                    if (state.error.kind === "conflict") {
                        state.error.message += " Copy your draft, compare the saved version, then reload and reconcile. No automatic retry.";
                    } else if (state.error.kind === "auth") {
                        state.error.message += " Copy your draft before reloading to renew the session.";
                    }
                    markOverviewStale();
                } else {
                    if (result.revision !== expectedRevision + 1 || !equal(result, submitted)) {
                        throw new Error("Invalid save acknowledgement. Compare the saved assessment before retrying.");
                    }
                    if (submitted.status !== state.acknowledged.status) {
                        markOverviewStale();
                    }
                    revision.value = String(result.revision);
                    state.acknowledged = submitted;
                    state.unacknowledged = false;
                    state.saved = true;
                }
            } catch (error) {
                state.error = {
                    kind: "network",
                    message: error.name === "AbortError"
                        ? "Request timed out; save outcome is unknown. Compare the saved assessment before retrying."
                        : `${error.message} Connection failed or the response could not be verified. Retry when available.`,
                };
                markOverviewStale();
            } finally {
                clearTimeout(timeout);
                state.saving = false;
                render();
            }
            // Only an acknowledged request can advance the revision and drain newer edits.
            if (!state.error && !equal(current(), state.acknowledged) && !state.timer) {
                save();
            }
        };
        const changed = (immediate) => {
            if (status.value !== state.acknowledged.status) {
                markOverviewStale();
            }
            clearTimeout(state.timer);
            state.timer = null;
            render();
            if (!state.error) {
                if (immediate) {
                    save();
                } else {
                    state.timer = setTimeout(save, 700);
                }
            }
        };
        const retry = () => {
            if (state.error?.kind === "conflict" || state.saving) {
                return;
            }
            state.error = null;
            render();
            save();
        };
        const controller = {changed, save, retry};
        controllers.set(cell, controller);
        return controller;
    };

    const hasPending = () => dirtyRows.size > 0;
    const warning = "Unsaved or in-flight recommendation edits remain. Wait for Saved, or fix the error and Retry save before continuing. Drafts stay on this page. To discard them deliberately, reload or close the tab and accept the browser warning.";
    document.addEventListener("input", (event) => {
        if (event.target.matches('[data-assessment] textarea[name="comments"]')) {
            controllerFor(event.target.closest("[data-assessment]")).changed(false);
        }
    });
    document.addEventListener("change", (event) => {
        if (event.target.matches('[data-assessment] select[name="status"]')) {
            controllerFor(event.target.closest("[data-assessment]")).changed(true);
        }
    });
    document.addEventListener("blur", (event) => {
        if (event.target.matches('[data-assessment] textarea[name="comments"]')) {
            controllerFor(event.target.closest("[data-assessment]")).save();
        }
    }, true);
    document.addEventListener("submit", (event) => {
        if (event.target.matches(".assessment-form")) {
            event.preventDefault();
            controllerFor(event.target.closest("[data-assessment]")).retry();
        } else if (hasPending()) {
            event.preventDefault();
            window.alert(warning);
        }
    }, true);
    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href]");
        if (!link || link.target === "_blank" || event.ctrlKey || event.metaKey || event.shiftKey) {
            return;
        }
        const target = new URL(link.href);
        const sameDocument = target.origin === location.origin && target.pathname === location.pathname
            && target.search === location.search && target.hash;
        if (!sameDocument && hasPending()) {
            event.preventDefault();
            window.alert(warning);
        }
    });
    window.addEventListener("beforeunload", (event) => {
        if (hasPending()) {
            event.preventDefault();
            event.returnValue = "";
        }
    });
    // Read once for pre-initialization/browser-restored drafts; clean rows need no controller or writes.
    for (const field of document.querySelectorAll(
        '[data-assessment] select[name="status"], [data-assessment] textarea[name="comments"]',
    )) {
        const initial = field.tagName === "SELECT"
            ? field.querySelector("option[selected]").value : field.defaultValue;
        if (field.value !== initial) {
            controllerFor(field.closest("[data-assessment]")).changed(false);
        }
    }
    document.documentElement.classList.add("autosave-enabled");
    document.getElementById("autosave-mode").textContent =
        "Autosave enabled for recommendation status and comments. Status saves immediately; comments save after 700 ms of inactivity or on leaving the field. Wait for Saved before leaving. Review details use their separate Save button.";
})();
