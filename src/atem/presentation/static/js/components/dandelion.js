/**
 * Dandelion ambient effects (TDR-0002) as Alpine components for the CSP build.
 * Seed size/opacity come from data attributes rendered by components/dandelion_ambient.html.
 */
document.addEventListener("alpine:init", () => {
    const seedConfig = (el) => ({
        size: Number(el.dataset.seedSize || 48),
        opacity: Number(el.dataset.seedOpacity || 0.8),
    });

    // MODE 2: Die Reise des Samens – a seed glides from the hero flower along the page.
    Alpine.data("seedJourney", () => ({
        progress: 0,
        initialLeft: 76,
        initialTop: 28,
        seed: { size: 48, opacity: 0.8 },
        init() {
            this.seed = seedConfig(this.$el);
            this.measureFlower();
            this.update();
            const onScroll = () => requestAnimationFrame(() => this.update());
            const onResize = () => {
                this.measureFlower();
                this.update();
            };
            window.addEventListener("scroll", onScroll, { passive: true });
            window.addEventListener("resize", onResize, { passive: true });
            window.addEventListener("load", onResize, { passive: true });
        },
        measureFlower() {
            const el = document.getElementById("hero-dandelion-artwork");
            if (!el || window.innerWidth <= 0 || window.innerHeight <= 0) return;
            const rect = el.getBoundingClientRect();
            const scrollY = window.pageYOffset || document.documentElement.scrollTop;
            // Upper-right crown of the dandelion head where seeds naturally detach
            const flowerX = rect.left + rect.width * 0.54;
            const flowerY = rect.top + scrollY + rect.height * 0.24;
            this.initialLeft = Math.min(Math.max((flowerX / window.innerWidth) * 100, 50), 90);
            this.initialTop = Math.min(Math.max((flowerY / window.innerHeight) * 100, 10), 50);
        },
        update() {
            const total = document.documentElement.scrollHeight - window.innerHeight;
            const scrollY = window.pageYOffset || document.documentElement.scrollTop;
            this.progress = total > 0 ? Math.min(Math.max(scrollY / total, 0), 1) : 0;
        },
        getLeft() {
            const p = this.progress;
            const startX = this.initialLeft || 76;
            if (p <= 0.02) return startX;
            if (p < 0.25) return startX - ((p - 0.02) / 0.23) * (startX - 30);
            if (p < 0.5) return 30 + ((p - 0.25) / 0.25) * 38;
            if (p < 0.75) return 68 - ((p - 0.5) / 0.25) * 40;
            return 28 + ((p - 0.75) / 0.25) * 44;
        },
        getTop() {
            const p = this.progress;
            const startY = this.initialTop || 28;
            if (p <= 0.02) return startY;
            return startY + ((p - 0.02) / 0.98) * (82 - startY);
        },
        getRotation() {
            const p = this.progress;
            if (p <= 0.02) return 26; // start angle matches the seed on the flower
            const localP = (p - 0.02) / 0.98;
            const blend = Math.min(localP * 6, 1);
            const aeroAngle =
                10 - Math.sin(localP * Math.PI * 4) * 42 + Math.sin(localP * Math.PI * 8) * 7;
            return Math.round(26 * (1 - blend) + aeroAngle * blend);
        },
        get journeyStyle() {
            const atStart = this.progress <= 0.02;
            return {
                top: `${this.getTop()}vh`,
                left: `${this.getLeft()}vw`,
                transform: `translate3d(0, 0, 0) rotate(${this.getRotation()}deg)`,
                opacity: atStart ? this.seed.opacity : Math.round(this.seed.opacity * 90) / 100,
                width: `${atStart ? this.seed.size : Math.round(this.seed.size * 0.9)}px`,
            };
        },
    }));

    // MODE 4: Die interaktive Atem-Pause – guided 4-4-6 breathing widget.
    Alpine.data("breathWidget", () => ({
        isOpen: false,
        phase: "inhale",
        totalSeconds: 4,
        currentSecond: 1,
        phaseProgress: 0,
        intervalId: null,
        get phaseLabel() {
            if (this.phase === "inhale") return "EINATMEN";
            if (this.phase === "hold") return "HALTEN & SPÜREN";
            return "AUSATMEN & LOSLASSEN";
        },
        get phaseInstruction() {
            if (this.phase === "inhale") return "Sanft & tief durch die Nase einatmen";
            if (this.phase === "hold") return "In der Stille ankommen & Atem halten";
            return "Langsam & vollständig durch den Mund ausatmen";
        },
        get phaseBadgeClass() {
            if (this.phase === "inhale") return "text-emerald-700 bg-emerald-100/90 border-emerald-300";
            if (this.phase === "hold") return "text-amber-700 bg-amber-100/90 border-amber-300";
            return "text-sky-700 bg-sky-100/90 border-sky-300";
        },
        get ringStrokeColor() {
            if (this.phase === "inhale") return "#10B981";
            if (this.phase === "hold") return "#F59E0B";
            return "#0284C7";
        },
        get strokeDashoffset() {
            const circumference = 364.4; // 2 * PI * 58
            if (this.phase === "inhale") return circumference * (1 - this.phaseProgress / 100);
            if (this.phase === "hold") return 0;
            return circumference * (this.phaseProgress / 100);
        },
        startBreathCycle() {
            this.clearIntervals();
            this.runPhase("inhale", 4);
        },
        runPhase(phaseName, durationSec) {
            if (!this.isOpen) return;
            this.phase = phaseName;
            this.totalSeconds = durationSec;
            this.currentSecond = 1;
            this.phaseProgress = 0;
            const startTime = Date.now();
            const totalMs = durationSec * 1000;
            this.intervalId = setInterval(() => {
                if (!this.isOpen) {
                    this.clearIntervals();
                    return;
                }
                const elapsed = Date.now() - startTime;
                this.currentSecond = Math.min(Math.floor(elapsed / 1000) + 1, durationSec);
                this.phaseProgress = Math.min((elapsed / totalMs) * 100, 100);
                if (elapsed >= totalMs) {
                    clearInterval(this.intervalId);
                    if (!this.isOpen) return;
                    const next = { inhale: ["hold", 4], hold: ["exhale", 6], exhale: ["inhale", 4] };
                    this.runPhase(...next[phaseName]);
                }
            }, 40);
        },
        clearIntervals() {
            if (this.intervalId) clearInterval(this.intervalId);
        },
        openWidget() {
            this.isOpen = true;
            this.startBreathCycle();
        },
        closeWidget() {
            this.isOpen = false;
            this.clearIntervals();
        },
    }));

    // MODE 5: Sanfter Hauch – tiny seeds drift up where the mouse moves.
    Alpine.data("whisperTrail", () => ({
        particles: [],
        lastSpawn: 0,
        seed: { size: 48, opacity: 0.8 },
        init() {
            this.seed = seedConfig(this.$el);
            window.addEventListener("mousemove", (e) => this.handleMove(e), { passive: true });
        },
        handleMove(e) {
            const now = Date.now();
            if (now - this.lastSpawn < 300) return; // max ~3 seeds per second
            this.lastSpawn = now;
            const id = now + Math.random();
            this.particles.push({ id, x: e.clientX, y: e.clientY, rotation: (Math.random() - 0.5) * 30 });
            setTimeout(() => {
                this.particles = this.particles.filter((p) => p.id !== id);
            }, 1200);
        },
        particleStyle(p) {
            return {
                left: `${p.x - 10}px`,
                top: `${p.y - 35}px`,
                transform: `rotate(${p.rotation}deg)`,
                width: `${Math.round(this.seed.size * 0.7)}px`,
                opacity: this.seed.opacity,
            };
        },
    }));
});
