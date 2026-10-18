/**
 * Live editor for logged-in admins (ADR-0002): Alpine.js in-context inline editor and image
 * manager. Loaded only when an admin session is active – the public app.js stays free of any
 * admin endpoints, so anonymous visitors never see that an admin area exists.
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
                    if (inputField.tagName === "TEXTAREA" && inputField.rows === 1) {
                        inputField.style.height = inputField.scrollHeight + "px";
                    }
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
        // Single-line text blocks use a one-row textarea that grows with the content (TDR-0011)
        autoGrow(event) {
            const field = event.target;
            field.style.height = "auto";
            field.style.height = field.scrollHeight + "px";
        },
        // Rich-text toolbar: wrap the selection in markup (bold/italic/underline) or turn the
        // selected lines into a bullet list. Rendered server-side by presentation/rich_text.py.
        format(kind) {
            const rootEl = this.$root || (this.$el ? this.$el.closest(".editable-block-container") : null);
            const field = rootEl ? rootEl.querySelector("textarea[name='content']") : null;
            if (!field) return;
            const value = field.value;
            const start = field.selectionStart;
            const end = field.selectionEnd;

            if (kind === "list") {
                const lineStart = value.lastIndexOf("\n", start - 1) + 1;
                const lines = value.slice(lineStart, end).split("\n");
                const listed = lines.map((line) => (line.startsWith("- ") || line === "" ? line : "- " + line)).join("\n");
                field.value = value.slice(0, lineStart) + listed + value.slice(end);
                field.setSelectionRange(lineStart, lineStart + listed.length);
            } else {
                const markers = { bold: "**", italic: "*", underline: "__" };
                const marker = markers[kind];
                if (!marker) return;
                const selected = value.slice(start, end);
                const text = selected || "Text";
                field.value = value.slice(0, start) + marker + text + marker + value.slice(end);
                field.setSelectionRange(start + marker.length, start + marker.length + text.length);
            }
            field.focus();
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

        /** Alt+S while the picker is open (CSP build: no inline statements in templates). */
        saveShortcut() {
            if (this.isOpen) this.applyAndSave();
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

});
