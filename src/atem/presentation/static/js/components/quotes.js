/**
 * Rotating breath quotes band (TDR-0003) - Alpine component for the CSP build.
 * Changes every 7 s; dots, horizontal swipe (touch) and arrow keys switch manually and restart
 * the interval so a quote picked by hand stays visible for the full 7 s.
 */
const QUOTE_INTERVAL_MS = 7000;
const SWIPE_MIN_PX = 40; // horizontal distance that counts as a swipe

document.addEventListener("alpine:init", () => {
    Alpine.data("quoteRotator", () => ({
        active: 0,
        count: 0,
        paused: false,
        timer: null,
        touchX: null,
        touchY: null,
        init() {
            this.count = Number(this.$el.dataset.count || 0);
            this.start();
        },
        start() {
            clearInterval(this.timer);
            this.timer = null;
            if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
            this.timer = setInterval(() => {
                if (!this.paused) this.next();
            }, QUOTE_INTERVAL_MS);
        },
        next() {
            if (this.count > 0) this.active = (this.active + 1) % this.count;
        },
        prev() {
            if (this.count > 0) this.active = (this.active - 1 + this.count) % this.count;
        },
        go(index) {
            this.active = index;
            this.start();
        },
        showNext() {
            this.next();
            this.start();
        },
        showPrev() {
            this.prev();
            this.start();
        },
        onTouchStart(event) {
            const touch = event.changedTouches[0];
            this.touchX = touch.clientX;
            this.touchY = touch.clientY;
        },
        onTouchEnd(event) {
            if (this.touchX === null) return;
            const touch = event.changedTouches[0];
            const dx = touch.clientX - this.touchX;
            const dy = touch.clientY - this.touchY;
            this.touchX = null;
            this.touchY = null;
            // Vertical scrolling wins: only a clearly horizontal gesture switches the quote
            if (Math.abs(dx) < SWIPE_MIN_PX || Math.abs(dx) <= Math.abs(dy)) return;
            if (dx < 0) this.showNext();
            else this.showPrev();
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
        destroy() {
            clearInterval(this.timer);
        },
    }));
});
