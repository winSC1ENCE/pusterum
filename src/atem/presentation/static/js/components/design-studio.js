/**
 * Corporate Design Studio state (admin/design.html) – Alpine component for the CSP build.
 * Initial values are rendered as data attributes on <body>.
 */
document.addEventListener("alpine:init", () => {
    Alpine.data("designStudio", () => ({
        activePreset: "",
        activeShape: "",
        activeModes: ["disabled"],
        seedSize: 48,
        seedOpacity: 80,
        kidsPhotoOpacity: 30,
        saveStatus: "Gespeichert",
        isSaving: false,
        init() {
            const data = this.$el.dataset;
            this.activePreset = data.preset || "";
            this.activeShape = data.shape || "";
            this.activeModes = JSON.parse(data.modes || '["disabled"]');
            this.seedSize = Number(data.seedSize || 48);
            this.seedOpacity = Number(data.seedOpacity || 80);
            this.kidsPhotoOpacity = Number(data.kidsPhotoOpacity ?? 30);
        },
        isModeActive(key) {
            return this.activeModes.includes(key);
        },
        toggleMode(key) {
            if (key === "disabled") {
                this.activeModes = ["disabled"];
            } else {
                // Choosing any visual mode (1–5) deselects "disabled"
                this.activeModes = this.activeModes.filter((m) => m !== "disabled");
                if (this.activeModes.includes(key)) {
                    this.activeModes = this.activeModes.filter((m) => m !== key);
                    if (this.activeModes.length === 0) this.activeModes = ["disabled"];
                } else {
                    this.activeModes.push(key);
                }
            }
            this.$nextTick(() => {
                const form = document.getElementById("dandelion-multiselect-form");
                if (form) htmx.trigger(form, "submit");
            });
        },
        get activeModesValue() {
            return this.activeModes.join(",");
        },
        get photoPreviewStyle() {
            return { opacity: this.kidsPhotoOpacity / 100 };
        },
        seedPreviewStyle(factor) {
            return { opacity: (this.seedOpacity / 100) * factor };
        },
        startSaving() {
            this.isSaving = true;
        },
        flashSaved() {
            this.isSaving = false;
            this.saveStatus = "Automatisch gespeichert";
        },
        updateLivePreview() {
            const previewEl = document.getElementById("seed-live-preview-img");
            if (previewEl) {
                previewEl.style.width = `${Math.min(this.seedSize, 90)}px`;
                previewEl.style.opacity = String(this.seedOpacity / 100);
            }
            const sizeBadge = document.getElementById("seed-size-badge");
            if (sizeBadge) sizeBadge.textContent = `${this.seedSize} px`;
            const opacityBadge = document.getElementById("seed-opacity-badge");
            if (opacityBadge) opacityBadge.textContent = `${this.seedOpacity} %`;
        },
    }));
});
