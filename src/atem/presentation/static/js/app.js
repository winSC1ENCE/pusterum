/**
 * Frontend JavaScript helpers for the public website: smooth scrolling, scroll restoration,
 * contact-form subject preselection and Alpine.js re-initialisation after HTMX swaps.
 */

// Re-initialize Alpine.js on HTMX swaps so reactivity is never lost
document.addEventListener("htmx:afterSwap", (evt) => {
    if (window.Alpine && typeof Alpine.initTree === "function" && evt.detail && evt.detail.target) {
        Alpine.initTree(evt.detail.target);
    }
});

document.addEventListener("DOMContentLoaded", () => {
    // Preserve scroll position before full page navigation
    window.addEventListener("beforeunload", () => {
        sessionStorage.setItem("atem_scroll_y", String(window.scrollY));
    });

    const savedY = sessionStorage.getItem("atem_scroll_y");
    if (savedY !== null && !window.location.hash) {
        window.scrollTo({ top: parseInt(savedY, 10), behavior: "instant" });
        sessionStorage.removeItem("atem_scroll_y");
    }

    // «Termin anfragen» on an offering preselects its subject in the contact form
    // (delegated, so it keeps working after HTMX swaps the form card)
    document.addEventListener("click", (e) => {
        const trigger = e.target instanceof Element ? e.target.closest("[data-contact-subject]") : null;
        const select = document.getElementById("subject");
        if (!trigger || !select) return;
        const wanted = trigger.getAttribute("data-contact-subject");
        const option = Array.from(select.options).find((o) => o.value === wanted);
        if (option) select.value = option.value;
    });

    // Smooth scroll for anchor navigation
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", function (e) {
            const targetId = this.getAttribute("href");
            if (targetId && targetId !== "#") {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: "smooth",
                        block: "start",
                    });
                }
            }
        });
    });

    // Log HTMX events in dev mode for debugging
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
        document.body.addEventListener("htmx:responseError", function (evt) {
            console.error("HTMX Response Error:", evt.detail);
        });
    }
});
