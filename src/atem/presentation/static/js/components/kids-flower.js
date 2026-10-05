/**
 * «Atmende Blume» – guided breathing exercise for children (Alpine component, CSP build).
 *
 * Stages: intro → flower (variants 1–3, BREATHS_PER_VARIANT calm breaths each, no breath
 * holding) → blow (dandelion game: hold while breathing in, release while breathing out and
 * a few seeds fly away) → done. Variant titles/texts come from content blocks via
 * data-variants (JSON). Used inline in the «Atmen mit Kindern» section and in the widget.
 */
document.addEventListener("alpine:init", () => {
    const INHALE_SECONDS = 3;
    const EXHALE_SECONDS = 4;
    const BREATHS_PER_VARIANT = 4;
    const SEED_COUNT = 10;
    const BLOW_BREATHS = 5;
    const MIN_INHALE_MS = 700;
    const FLY_MS = 1600;

    const buildSeeds = () =>
        Array.from({ length: SEED_COUNT }, (_, i) => {
            const angle = (360 / SEED_COUNT) * i;
            return { id: i, angle: angle, flying: false, gone: false };
        });

    Alpine.data("kidsFlower", () => ({
        stage: "intro",
        variants: [],
        variantIndex: 0,
        breath: 1,
        phase: "exhale",
        timerId: null,
        seeds: buildSeeds(),
        blowBreaths: 0,
        pressed: false,
        pressStartedAt: 0,

        init() {
            try {
                this.variants = JSON.parse(this.$el.dataset.variants || "[]");
            } catch (e) {
                this.variants = [];
            }
        },
        destroy() {
            this.clearTimer();
        },

        // ------------------------------------------------------------- derived values
        get isIntro() { return this.stage === "intro"; },
        get isFlower() { return this.stage === "flower"; },
        get isBlow() { return this.stage === "blow"; },
        get isDone() { return this.stage === "done"; },
        get isInhale() { return this.phase === "inhale"; },
        get currentVariant() {
            return this.variants[this.variantIndex] || { title: "", text: "" };
        },
        get variantLabel() {
            return "Blume " + (this.variantIndex + 1) + " von " + this.variants.length;
        },
        get breathLabel() {
            return "Atemzug " + this.breath + " von " + BREATHS_PER_VARIANT;
        },
        get phaseLabel() {
            return this.isInhale ? "Einatmen – die Blüte öffnet sich" : "Ausatmen – die Blüte schliesst sich";
        },
        get flowerClass() {
            return this.isInhale ? "kids-flower is-open is-inhale" : "kids-flower is-exhale";
        },
        get seedsLeft() {
            return this.seeds.filter((s) => !s.flying && !s.gone).length;
        },
        get blowLabel() {
            if (this.pressed) return "Einatmen … und jetzt loslassen und auspusten!";
            return "Halte gedrückt und atme dabei ein";
        },
        get headClass() {
            return this.pressed ? "kids-dandelion is-growing" : "kids-dandelion";
        },
        seedStyle(seed) {
            return { transform: "rotate(" + seed.angle + "deg) translateY(-46px)" };
        },
        seedClass(seed) {
            if (seed.gone) return "kids-seed is-gone";
            return seed.flying ? "kids-seed is-flying" : "kids-seed";
        },

        // ------------------------------------------------------------- flower stage
        startFlower() {
            this.clearTimer();
            if (!this.variants.length) {
                this.startBlow();
                return;
            }
            this.stage = "flower";
            this.variantIndex = 0;
            this.breath = 1;
            this.runPhase("inhale");
        },
        runPhase(phase) {
            this.phase = phase;
            const seconds = phase === "inhale" ? INHALE_SECONDS : EXHALE_SECONDS;
            this.timerId = setTimeout(() => this.nextPhase(), seconds * 1000);
        },
        nextPhase() {
            if (this.stage !== "flower") return;
            if (this.phase === "inhale") {
                this.runPhase("exhale");
                return;
            }
            if (this.breath < BREATHS_PER_VARIANT) {
                this.breath += 1;
            } else if (this.variantIndex < this.variants.length - 1) {
                this.variantIndex += 1;
                this.breath = 1;
            } else {
                this.startBlow();
                return;
            }
            this.runPhase("inhale");
        },

        // ------------------------------------------------------------- blow game
        startBlow() {
            this.clearTimer();
            this.stage = "blow";
            this.phase = "exhale";
            this.seeds = buildSeeds();
            this.blowBreaths = 0;
            this.pressed = false;
        },
        pressStart(event) {
            if (!this.isBlow || this.pressed) return;
            // Keep the pointer on the button while held (scrolling/finger drift is no release)
            if (event && event.pointerId !== undefined && event.currentTarget && event.currentTarget.setPointerCapture) {
                event.currentTarget.setPointerCapture(event.pointerId);
            }
            this.pressed = true;
            this.pressStartedAt = Date.now();
        },
        pressEnd() {
            if (!this.isBlow || !this.pressed) return;
            this.pressed = false;
            if (Date.now() - this.pressStartedAt < MIN_INHALE_MS) return;
            this.blowBreaths += 1;
            const remaining = this.seeds.filter((s) => !s.flying && !s.gone);
            const perBreath = Math.ceil(SEED_COUNT / BLOW_BREATHS);
            const count = this.blowBreaths >= BLOW_BREATHS ? remaining.length : perBreath;
            remaining.slice(0, count).forEach((seed) => {
                seed.flying = true;
                setTimeout(() => { seed.gone = true; }, FLY_MS);
            });
            if (this.blowBreaths >= BLOW_BREATHS || count >= remaining.length) {
                this.timerId = setTimeout(() => { this.stage = "done"; }, FLY_MS);
            }
        },

        // ------------------------------------------------------------- controls
        // Widget tab switch / close: only the player in the matching scope stops.
        stopFrom(event) {
            const scope = event && event.detail ? event.detail.scope : "";
            if (!scope || scope === this.$el.dataset.scope) this.stop();
        },
        stop() {
            this.clearTimer();
            this.stage = "intro";
            this.phase = "exhale";
            this.pressed = false;
        },
        clearTimer() {
            if (this.timerId) clearTimeout(this.timerId);
            this.timerId = null;
        },
    }));
});
