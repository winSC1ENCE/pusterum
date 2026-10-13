/**
 * Applies the visitor's saved font size before the first paint (no flash of the default size).
 * Loaded synchronously in <head>; the control itself is components/font-size.js.
 */
(function () {
    try {
        var level = window.localStorage.getItem("pusterum_font_scale");
        if (level === "1" || level === "2") {
            document.documentElement.setAttribute("data-font-scale", level);
        }
    } catch (e) {
        // Storage blocked (private mode, policies): keep the default size.
    }
})();
