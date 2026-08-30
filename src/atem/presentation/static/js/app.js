/**
 * Frontend JavaScript helpers for Atemtherapie Application
 * Includes Smooth Scrolling, HTMX Debugging, Alpine.js In-Context Inline Editor & Image Manager (ADR-0002).
 */

document.addEventListener("alpine:init", () => {
    // 1. Text & Inline Element Editor Component
    Alpine.data("inlineEditor", (key, type) => ({
        key: key,
        type: type,
        isEditing: false,
        startEdit() {
            if (this.type === "image") {
                const imgEl = this.$el.querySelector("img");
                const currentSrc = imgEl ? imgEl.getAttribute("src") : "";
                const imgClass = this.$el.getAttribute("data-img-class") || (imgEl ? imgEl.className : "");
                const imgAlt = this.$el.getAttribute("data-img-alt") || (imgEl ? imgEl.getAttribute("alt") : "");
                const tag = this.$el.getAttribute("data-tag") || "p";
                const cssClass = this.$el.getAttribute("data-css-class") || "";
                const rows = this.$el.getAttribute("data-rows") || "3";

                window.dispatchEvent(new CustomEvent("open-image-picker", {
                    detail: {
                        blockKey: this.key,
                        currentUrl: currentSrc,
                        domId: this.$el.id,
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
                if (this.$refs.inputField) {
                    this.$refs.inputField.focus();
                    if (this.$refs.inputField.select && typeof this.$refs.inputField.select === "function") {
                        this.$refs.inputField.select();
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
            this.domId = detail.domId || "";
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
            if (!this.selectedUrl || !this.blockKey || !this.domId) {
                this.closeModal();
                return;
            }

            const chosenUrl = this.selectedUrl;
            const targetEl = document.getElementById(this.domId);
            const imgClass = this.imgClass || (targetEl ? targetEl.getAttribute("data-img-class") : "") || "";
            const imgAlt = this.imgAlt || (targetEl ? targetEl.getAttribute("data-img-alt") : "") || "";
            const tag = this.tag || (targetEl ? targetEl.getAttribute("data-tag") : "") || "p";
            const cssClass = this.cssClass || (targetEl ? targetEl.getAttribute("data-css-class") : "") || "";
            const rows = this.rows || (targetEl ? targetEl.getAttribute("data-rows") : "") || "3";

            // 1. Immediately update image preview in DOM
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
                    method: "POST",
                    body: formData,
                });
                if (res.ok) {
                    const html = await res.text();
                    if (targetEl && html) {
                        targetEl.outerHTML = html;
                    }
                }
            } catch (err) {
                console.error("Save error:", err);
            }

            this.closeModal();
        },
    }));
});

document.addEventListener("DOMContentLoaded", () => {
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
