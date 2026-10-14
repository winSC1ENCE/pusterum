/**
 * Discreet font size control «Schrift A− A+» (mobile menu and footer, three steps) – Alpine
 * component for the CSP build. Scales the root font size (Tailwind uses rem) via
 * html[data-font-scale]; the choice stays in this browser only (localStorage, no cookie,
 * nothing sent to the server).
 */
const FONT_SCALE_KEY = "pusterum_font_scale";
const FONT_SCALE_MAX = 2;

document.addEventListener("alpine:init", () => {
    Alpine.data("fontSize", () => ({
        level: 0,
        init() {
            this.level = Number(document.documentElement.getAttribute("data-font-scale") || 0);
        },
        smaller() {
            this.apply(this.level - 1);
        },
        larger() {
            this.apply(this.level + 1);
        },
        apply(level) {
            this.level = Math.min(FONT_SCALE_MAX, Math.max(0, level));
            const root = document.documentElement;
            if (this.level === 0) root.removeAttribute("data-font-scale");
            else root.setAttribute("data-font-scale", String(this.level));
            try {
                if (this.level === 0) window.localStorage.removeItem(FONT_SCALE_KEY);
                else window.localStorage.setItem(FONT_SCALE_KEY, String(this.level));
            } catch (e) {
                // Storage blocked: the size still applies to this page view.
            }
            // Keep the other control (menu ↔ footer) in sync
            window.dispatchEvent(new CustomEvent("font-size-changed", { detail: this.level }));
        },
        sync(event) {
            this.level = event.detail;
        },
        get atMin() {
            return this.level === 0;
        },
        get atMax() {
            return this.level === FONT_SCALE_MAX;
        },
    }));
});
