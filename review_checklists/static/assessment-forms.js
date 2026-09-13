"use strict";

// Chrome repeatedly lays out large tables while extracting thousands of native forms.
// Keep untouched forms off-DOM, but restore native submission before any interaction.
(() => {
    if (!window.MutationObserver) {
        return;
    }
    const detached = new WeakMap();
    const processed = new WeakSet();
    const activate = (event) => {
        const row = event.target.closest?.("[data-assessment]");
        const form = row && detached.get(row);
        if (form) {
            row.append(form);
            detached.delete(row);
        }
    };
    for (const event of ["pointerdown", "focusin", "input", "change", "click", "assessment-activate"]) {
        document.addEventListener(event, activate, true);
    }

    const detach = (form) => {
        // The final link marks a complete editor even when the parser delivers partial rows.
        if (processed.has(form) || !form.querySelector(".conflict-help")) {
            return;
        }
        processed.add(form);
        const row = document.createElement("div");
        row.className = "assessment";
        row.dataset.assessment = form.dataset.assessment;
        const active = form.contains(document.activeElement) ? document.activeElement : null;
        for (const control of form.querySelectorAll("input, select, textarea, button")) {
            control.setAttribute("form", form.id);
        }
        row.append(...form.childNodes);
        form.removeAttribute("data-assessment");
        form.hidden = true;
        form.replaceWith(row);
        detached.set(row, form);
        if (active) {
            row.append(form);
            detached.delete(row);
            active.focus({preventScroll: true});
        }
    };
    const observer = new MutationObserver((records) => {
        const forms = new Set();
        for (const record of records) {
            const owner = record.target.closest?.("form.assessment-form");
            if (owner) {
                forms.add(owner);
                continue;
            }
            for (const node of record.addedNodes) {
                if (node.nodeType !== Node.ELEMENT_NODE) {
                    continue;
                }
                if (node.matches("form.assessment-form")) {
                    forms.add(node);
                } else if (node.firstElementChild) {
                    for (const form of node.querySelectorAll("form.assessment-form")) {
                        forms.add(form);
                    }
                }
            }
        }
        for (const form of forms) {
            detach(form);
        }
    });
    observer.observe(document.documentElement, {childList: true, subtree: true});
    document.addEventListener("DOMContentLoaded", () => {
        observer.disconnect();
        for (const form of document.querySelectorAll("form.assessment-form")) {
            detach(form);
        }
    }, {once: true});
})();
