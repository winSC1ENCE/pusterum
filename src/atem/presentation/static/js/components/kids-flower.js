/**
 * «Atmende Blume» – guided breathing exercise for children (Alpine component, CSP build).
 *
 * Stages: intro → flower (one chosen variant, BREATHS_PER_VARIANT calm breaths, no breath
 * holding) → variantDone (again / next flower / blow) → blow (dandelion game: hold while
 * breathing in, release while breathing out and a few seeds fly away) → done.
 * Each variant card in the section starts its own flower («Mitmachen», event
 * `kids-flower-start`). Variant titles/texts/photos come from content blocks via
 * data-variants (JSON). Used inline in the «Atmen mit Kindern» section and in the widget.
 */
document.addEventListener("alpine:init", () => {
    const INHALE_SECONDS = 3;
    const EXHALE_SECONDS = 4;
    const BREATHS_PER_VARIANT = 5;
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
        scope: "",
        root: null,

        init() {
            this.root = this.$el;
            this.scope = this.$el.dataset.scope || "";
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
        get isVariantDone() { return this.stage === "variantDone"; },
        get isBlow() { return this.stage === "blow"; },
        get isDone() { return this.stage === "done"; },
        get showsFlower() { return this.isIntro || this.isFlower || this.isVariantDone; },
        get isInhale() { return this.phase === "inhale"; },
        get currentVariant() {
            return this.variants[this.variantIndex] || { title: "", text: "" };
        },
        get hasNextVariant() {
            return this.variantIndex < this.variants.length - 1;
        },
        get variantLabel() {
            return "Blume " + (this.variantIndex + 1);
        },
        get variantDoneLabel() {
            return "Blume " + (this.variantIndex + 1) + " geschafft!";
        },
        get breathLabel() {
            return "Atemzug " + this.breath + " von " + BREATHS_PER_VARIANT;
        },
        get phaseLabel() {
            return this.isInhale ? "Einatmen – die Blüte öffnet sich" : "Ausatmen – die Blüte schliesst sich";
        },
        // Each flower moves in its own way (v1 bud … v4 meadow), see styles.css
        get flowerClass() {
            const variant = this.isFlower || this.isVariantDone ? " v" + (this.variantIndex + 1) : "";
            const state = this.isFlower && this.isInhale ? " is-open is-inhale" : " is-exhale";
            return "kids-flower" + variant + state;
        },

        // ------------------------------------------------------------- background photos
        get photoClosed() { return this.currentVariant.photo_closed || ""; },
        get photoOpen() { return this.currentVariant.photo_open || ""; },
        get hasPhotos() {
            return (this.isFlower || this.isVariantDone) && Boolean(this.photoClosed || this.photoOpen);
        },
        get photoOpenClass() {
            const visible = this.isFlower && this.isInhale && this.photoOpen;
            return "kids-photo" + (visible ? " is-visible" : "") + (this.isInhale ? " is-inhale" : "");
        },
        get photoClosedClass() {
            const visible = !(this.isFlower && this.isInhale) && this.photoClosed;
            return "kids-photo" + (visible ? " is-visible" : "") + (this.isInhale ? " is-inhale" : "");
        },

        // ------------------------------------------------------------- blow game helpers
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
            return { transform: "rotate(" + seed.angle + "deg) translateY(-48px)" };
        },
        seedClass(seed) {
            if (seed.gone) return "kids-seed is-gone";
            return seed.flying ? "kids-seed is-flying" : "kids-seed";
        },

        // ------------------------------------------------------------- flower stage
        startFlower() {
            this.startVariant(0);
        },
        startVariant(index) {
            this.clearTimer();
            if (!this.variants.length) {
                this.startBlow();
                return;
            }
            this.stage = "flower";
            this.variantIndex = Math.min(Math.max(Number(index) || 0, 0), this.variants.length - 1);
            this.breath = 1;
            this.announceVariant();
            this.runPhase("inhale");
        },
        // «Mitmachen» on a variant card (section player only)
        startFrom(event) {
            if (this.scope !== "section") return;
            const detail = event && event.detail ? event.detail : {};
            this.startVariant(detail.index);
            this.scrollIntoViewIfNeeded();
        },
        repeatVariant() {
            this.startVariant(this.variantIndex);
        },
        nextVariant() {
            if (this.hasNextVariant) this.startVariant(this.variantIndex + 1);
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
                this.runPhase("inhale");
                return;
            }
            this.timerId = null;
            this.stage = "variantDone";
        },

        // ------------------------------------------------------------- blow game
        startBlow() {
            this.clearTimer();
            this.announceVariant(-1);
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
            if (!scope || scope === this.scope) this.stop();
        },
        stop() {
            this.clearTimer();
            this.announceVariant(-1);
            this.stage = "intro";
            this.phase = "exhale";
            this.pressed = false;
        },
        // Lets the variant cards next to the player highlight the active flower (-1 = none).
        announceVariant(index) {
            const active = index === undefined ? this.variantIndex : index;
            window.dispatchEvent(new CustomEvent("kids-flower-variant", {
                detail: { scope: this.scope, index: active },
            }));
        },
        // On phones the cards sit above the player – bring it into view after «Mitmachen».
        scrollIntoViewIfNeeded() {
            if (!this.root || typeof this.root.getBoundingClientRect !== "function") return;
            const rect = this.root.getBoundingClientRect();
            if (rect.top < 0 || rect.bottom > window.innerHeight) {
                this.root.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        },
        clearTimer() {
            if (this.timerId) clearTimeout(this.timerId);
            this.timerId = null;
        },
    }));

    // Variant cards in the «Atmen mit Kindern» section: start a flower, highlight the active one.
    Alpine.data("kidsVariantList", () => ({
        activeIndex: -1,
        start(index) {
            window.dispatchEvent(new CustomEvent("kids-flower-start", { detail: { index: index } }));
        },
        onVariant(event) {
            const detail = event && event.detail ? event.detail : {};
            if (detail.scope === "section") this.activeIndex = Number(detail.index);
        },
        cardClass(index) {
            return index === this.activeIndex ? "kids-card-active" : "";
        },
        isActive(index) {
            return index === this.activeIndex;
        },
    }));
});
