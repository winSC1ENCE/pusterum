/**
 * Frontend JavaScript helpers for Atemtherapie Application
 * Includes Smooth Scrolling, HTMX Debugging, Alpine.js In-Context Inline Editor & Image Manager (ADR-0002).
 */

/**
 * CSRF header for fetch() POSTs (token rendered into <meta name="csrf-token">).
 * HTMX requests get the same header via hx-headers on <body>.
 */
function csrfHeaders() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? { "x-csrftoken": meta.content } : {};
}

document.addEventListener("alpine:init", () => {
    // 1. Text & Inline Element Editor Component
    Alpine.data("inlineEditor", (key, type) => ({
        key: key,
        type: type,
        isEditing: false,
        startEdit() {
            const rootEl = this.$root || (this.$el ? this.$el.closest(".editable-block-container") : null) || this.$el;
            const domId = (rootEl && rootEl.id) ? rootEl.id : ("content-block-" + String(this.key).replace(/\./g, "-"));
            const imgEl = rootEl ? rootEl.querySelector("img") : null;
            const currentSrc = imgEl ? (imgEl.getAttribute("src") || imgEl.src || "") : "";
            const imgClass = (rootEl ? rootEl.getAttribute("data-img-class") : "") || (imgEl ? imgEl.className : "");
            const imgAlt = (rootEl ? rootEl.getAttribute("data-img-alt") : "") || (imgEl ? imgEl.getAttribute("alt") : "");
            const tag = (rootEl ? rootEl.getAttribute("data-tag") : "") || "p";
            const cssClass = (rootEl ? rootEl.getAttribute("data-css-class") : "") || "";
            const rows = (rootEl ? rootEl.getAttribute("data-rows") : "") || "3";

            if (this.type === "image") {
                window.dispatchEvent(new CustomEvent("open-image-picker", {
                    detail: {
                        blockKey: this.key,
                        currentUrl: currentSrc,
                        domId: domId,
                        imgClass: imgClass,
                        imgAlt: imgAlt,
                        tag: tag,
                        cssClass: cssClass,
                        rows: rows,
                    }
                }));
                return;
            }
            this.isEditing = true;
            this.$nextTick(() => {
                const targetRoot = this.$root || (this.$el ? this.$el.closest(".editable-block-container") : null) || this.$el;
                const inputField = targetRoot ? targetRoot.querySelector("input[name='content'], textarea[name='content']") : null;
                if (inputField) {
                    inputField.focus();
                    if (inputField.select && typeof inputField.select === "function") {
                        inputField.select();
                    }
                }
            });
        },
        cancelEdit() {
            this.isEditing = false;
        },
        submitForm(formEl) {
            if (typeof htmx !== "undefined" && formEl) {
                htmx.trigger(formEl, "submit");
            }
        },
    }));

    // 2. Global Non-Clipped Image Picker & Upload Modal Component
    Alpine.data("imagePickerModal", () => ({
        isOpen: false,
        blockKey: "",
        selectedUrl: "",
        domId: "",
        imgClass: "",
        imgAlt: "",
        tag: "p",
        cssClass: "",
        rows: "3",
        activeTab: "gallery",
        images: [],
        uploading: false,
        uploadError: "",
        isDragging: false,

        openModal(detail) {
            this.blockKey = detail.blockKey || "";
            this.selectedUrl = detail.currentUrl || "";
            this.domId = detail.domId || ("content-block-" + String(detail.blockKey).replace(/\./g, "-"));
            this.imgClass = detail.imgClass || "";
            this.imgAlt = detail.imgAlt || "";
            this.tag = detail.tag || "p";
            this.cssClass = detail.cssClass || "";
            this.rows = detail.rows || "3";
            this.activeTab = "gallery";
            this.uploadError = "";
            this.isOpen = true;
            this.fetchImages();
        },

        closeModal() {
            this.isOpen = false;
            this.uploadError = "";
            this.uploading = false;
        },

        selectImage(url) {
            this.selectedUrl = url;
        },

        async fetchImages() {
            try {
                const res = await fetch("/admin/images/list");
                if (res.ok) {
                    this.images = await res.json();
                }
            } catch (err) {
                console.error("Error loading images list:", err);
            }
        },

        handleFileSelect(event) {
            const files = event.target.files;
            if (files && files[0]) {
                this.uploadFile(files[0]);
            }
        },

        handleDrop(event) {
            this.isDragging = false;
            const files = event.dataTransfer.files;
            if (files && files[0]) {
                this.uploadFile(files[0]);
            }
        },

        async uploadFile(file) {
            if (!file) return;
            this.uploading = true;
            this.uploadError = "";

            const formData = new FormData();
            formData.append("data", file);

            try {
                const res = await fetch("/admin/images/upload", {
                    headers: csrfHeaders(),
                    method: "POST",
                    body: formData,
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || errData.message || "Upload fehlgeschlagen.");
                }

                const data = await res.json();
                this.uploading = false;
                this.selectedUrl = data.url;
                await this.fetchImages();
                this.activeTab = "gallery";
            } catch (err) {
                this.uploading = false;
                this.uploadError = err.message || "Fehler beim Hochladen.";
            }
        },

        async applyAndSave() {
            if (!this.selectedUrl || !this.blockKey) {
                this.closeModal();
                return;
            }

            const chosenUrl = this.selectedUrl;
            const domId = this.domId || ("content-block-" + String(this.blockKey).replace(/\./g, "-"));
            const targetEl = document.getElementById(domId);
            const imgClass = this.imgClass || (targetEl ? targetEl.getAttribute("data-img-class") : "") || "";
            const imgAlt = this.imgAlt || (targetEl ? targetEl.getAttribute("data-img-alt") : "") || "";
            const tag = this.tag || (targetEl ? targetEl.getAttribute("data-tag") : "") || "p";
            const cssClass = this.cssClass || (targetEl ? targetEl.getAttribute("data-css-class") : "") || "";
            const rows = this.rows || (targetEl ? targetEl.getAttribute("data-rows") : "") || "3";

            // 1. Immediately update image preview in live DOM
            if (targetEl) {
                const imgEl = targetEl.querySelector("img");
                if (imgEl) {
                    imgEl.src = chosenUrl;
                }
            }

            // 2. Persist to server via form data
            const formData = new FormData();
            formData.append("content", chosenUrl);
            formData.append("img_class", imgClass);
            formData.append("img_alt", imgAlt);
            formData.append("tag", tag);
            formData.append("css_class", cssClass);
            formData.append("rows", rows);

            try {
                const res = await fetch(`/admin/content/${this.blockKey}/save`, {
                    headers: csrfHeaders(),
                    method: "POST",
                    body: formData,
                });
                if (res.ok) {
                    const html = await res.text();
                    const currentTargetEl = document.getElementById(domId);
                    if (currentTargetEl && html) {
                        currentTargetEl.outerHTML = html;
                        const newEl = document.getElementById(domId);
                        if (newEl && window.Alpine && typeof Alpine.initTree === "function") {
                            Alpine.initTree(newEl);
                        }
                    }
                } else {
                    const errData = await res.json().catch(() => ({}));
                    console.error("Save error:", errData);
                    alert("Fehler beim Speichern: " + (errData.detail || "Serverfehler"));
                }
            } catch (err) {
                console.error("Save error:", err);
                alert("Netzwerkfehler beim Speichern des Bildes.");
            }

            this.closeModal();
        },
    }));

    // 3. Design Studio Live Sliders & Autosave Component
    Alpine.data("designStudio", (initialSize = 48, initialOpacity = 80) => ({
        seedSize: initialSize,
        seedOpacity: initialOpacity,
        init() {
            this.updateLivePreview();
        },
        updateLivePreview() {
            const previewEl = document.getElementById("seed-live-preview-img");
            if (previewEl) {
                previewEl.style.width = Math.min(this.seedSize, 90) + "px";
                previewEl.style.opacity = String(this.seedOpacity / 100);
            }
            const sizeBadge = document.getElementById("seed-size-badge");
            if (sizeBadge) sizeBadge.textContent = this.seedSize + " px";
            const opacityBadge = document.getElementById("seed-opacity-badge");
            if (opacityBadge) opacityBadge.textContent = this.seedOpacity + " %";
        },
    }));
});

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
