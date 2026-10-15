/**
 * Tailwind CSS build configuration (compiled at build time – no runtime compiler in the
 * browser, which keeps the Content-Security-Policy strict). Build: scripts/build-css.sh
 */
module.exports = {
  content: [
    "./src/atem/presentation/templates/**/*.html",
    "./src/atem/presentation/static/js/app.js",
    "./src/atem/presentation/static/js/components/**/*.js",
    "./src/atem/presentation/static/js/admin/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // RGB channels (theme.css, ThemeService) so opacity steps like bg-theme-primary/20 work
        theme: {
          primary: "rgb(var(--theme-primary-rgb, 74 108 80) / <alpha-value>)",
          "primary-hover": "rgb(var(--theme-primary-hover-rgb, 60 86 65) / <alpha-value>)",
          secondary: "rgb(var(--theme-secondary-rgb, 206 222 207) / <alpha-value>)",
          accent: "rgb(var(--theme-accent-rgb, 127 164 133) / <alpha-value>)",
          bg: "rgb(var(--theme-bg-rgb, 250 248 245) / <alpha-value>)",
          surface: "rgb(var(--theme-surface-rgb, 255 255 255) / <alpha-value>)",
          "surface-muted": "rgb(var(--theme-surface-muted-rgb, 243 239 232) / <alpha-value>)",
          "text-main": "rgb(var(--theme-text-main-rgb, 30 41 59) / <alpha-value>)",
          "text-muted": "rgb(var(--theme-text-muted-rgb, 100 116 139) / <alpha-value>)",
          border: "rgb(var(--theme-border-rgb, 230 222 209) / <alpha-value>)",
          // Aliases used in the templates: border-theme / divide-theme, bg-theme-main|card|muted
          DEFAULT: "rgb(var(--theme-border-rgb, 230 222 209) / <alpha-value>)",
          main: "rgb(var(--theme-bg-rgb, 250 248 245) / <alpha-value>)",
          card: "rgb(var(--theme-surface-rgb, 255 255 255) / <alpha-value>)",
          muted: "rgb(var(--theme-surface-muted-rgb, 243 239 232) / <alpha-value>)",
        },
      },
      fontFamily: {
        heading: ["var(--font-heading, Lora)", "serif"],
        body: ["var(--font-body, Plus Jakarta Sans)", "sans-serif"],
      },
      borderRadius: {
        organic: "var(--theme-shape-radius, 42% 58% 70% 30% / 45% 45% 55% 55%)",
      },
    },
  },
};
