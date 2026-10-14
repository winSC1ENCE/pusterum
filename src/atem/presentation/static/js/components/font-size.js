/**
 * Discreet font size control (mobile menu and footer, three steps) – Alpine component for the
 * CSP build. Scales the root font size (Tailwind uses rem) via html[data-font-scale]; the choice
 * stays in this browser only (localStorage, no cookie, nothing sent to the server).
 */
const FONT_SCALE_KEY = "pusterum_font_scale";
const FONT_SCALE_MAX = 2;
const FONT_SCALE_LABELS = ["normal", "mittel", "gross"];

document.addEventListener("alpine:init", () => {
    Alpine.data("fontSize", () => ({
        level: 0,
        init() {
            this.level = Number(document.documentElement.getAttribute("data-font-scale") || 0);
        },
        smaller(event) {
            this.apply(this.level - 1, event.currentTarget);
        },
        larger(event) {
            this.apply(this.level + 1, event.currentTarget);
        },
        apply(level, anchor) {
            const next = Math.min(FONT_SCALE_MAX, Math.max(0, level));
            if (next === this.level) return;
            // The page gets longer/shorter: keep the clicked button where it was on screen
            // (otherwise the footer slides away and the page seems to jump to the top).
            const anchorTop = anchor.getBoundingClientRect().top;
            this.level = next;
            const root = document.documentElement;
            if (next === 0) root.removeAttribute("data-font-scale");
            else root.setAttribute("data-font-scale", String(next));
            const shift = anchor.getBoundingClientRect().top - anchorTop;
            if (shift !== 0) window.scrollBy({ top: shift, behavior: "instant" });
            try {
                if (next === 0) window.localStorage.removeItem(FONT_SCALE_KEY);
                else window.localStorage.setItem(FONT_SCALE_KEY, String(next));
            } catch (e) {
                // Storage blocked: the size still applies to this page view.
            }
            // Keep the other control (menu ↔ footer) in sync
            window.dispatchEvent(new CustomEvent("font-size-changed", { detail: next }));
        },
        sync(event) {
            this.level = event.detail;
        },
        dotClass(step) {
            return step <= this.level ? "opacity-90" : "opacity-25";
        },
        get atMin() {
            return this.level === 0;
        },
        get atMax() {
            return this.level === FONT_SCALE_MAX;
        },
        get levelText() {
            return "Schriftgrösse " + FONT_SCALE_LABELS[this.level];
        },
    }));
});
