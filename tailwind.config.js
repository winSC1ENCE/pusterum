/**
 * Tailwind CSS build configuration (compiled at build time – no runtime compiler in the
 * browser, which keeps the Content-Security-Policy strict). Build: scripts/build-css.sh
 */
module.exports = {
  content: [
    "./src/atem/presentation/templates/**/*.html",
    "./src/atem/presentation/static/js/app.js",
    "./src/atem/presentation/static/js/components/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        theme: {
          primary: "var(--theme-primary, #4A6C50)",
          "primary-hover": "var(--theme-primary-hover, #3C5641)",
          secondary: "var(--theme-secondary, #CEDECF)",
          accent: "var(--theme-accent, #7FA485)",
          bg: "var(--theme-bg, #FAF8F5)",
          surface: "var(--theme-surface, #FFFFFF)",
          "surface-muted": "var(--theme-surface-muted, #F3EFE8)",
          "text-main": "var(--theme-text-main, #1E293B)",
          "text-muted": "var(--theme-text-muted, #64748B)",
          border: "var(--theme-border, #E6DED1)",
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
