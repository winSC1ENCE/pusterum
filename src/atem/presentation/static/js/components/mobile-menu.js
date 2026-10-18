/**
 * Mobile navigation (navbar.html) - Alpine component for the CSP build.
 * Closes on a link, on a click outside the header, on the backdrop below the panel and with
 * Escape (focus then returns to the menu button).
 */
document.addEventListener("alpine:init", () => {
    Alpine.data("mobileMenu", () => ({
        open: false,
        toggle() {
            this.open = !this.open;
        },
        close() {
            this.open = false;
        },
        closeWithEscape() {
            if (!this.open) return;
            this.open = false;
            this.$refs.toggle.focus();
        },
        get ariaExpanded() {
            return this.open ? "true" : "false";
        },
        get toggleText() {
            return this.open ? "Schliessen" : "Menü";
        },
    }));
});
