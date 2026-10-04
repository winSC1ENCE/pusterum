/** Rotating breath quotes band (TDR-0003) – Alpine component for the CSP build. */
document.addEventListener("alpine:init", () => {
    Alpine.data("quoteRotator", () => ({
        active: 0,
        count: 0,
        paused: false,
        timer: null,
        init() {
            this.count = Number(this.$el.dataset.count || 0);
            if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
            this.timer = setInterval(() => {
                if (!this.paused) this.next();
            }, 7000);
        },
        next() {
            if (this.count > 0) this.active = (this.active + 1) % this.count;
        },
        go(index) {
            this.active = index;
        },
        isActive(index) {
            return this.active === index;
        },
        pause() {
            this.paused = true;
        },
        resume() {
            this.paused = false;
        },
    }));
});
