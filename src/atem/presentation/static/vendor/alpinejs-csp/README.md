# Alpine.js CSP build (vendored)

* Version: @alpinejs/csp@3.17.4 (`dist/cdn.min.js`)
* Lizenz: MIT – https://github.com/alpinejs/alpine
* Quelle: https://cdn.jsdelivr.net/npm/@alpinejs/csp@3.17.4/dist/cdn.min.js
* Warum: kein `eval`/`new Function` → Content-Security-Policy ohne `unsafe-eval`.
  Ausdrücke in Templates: keine Template-Literals, Pfeilfunktionen, Statements oder Globals
  (`window`, `document`, `Math`) – Logik gehört in Komponenten (`static/js/components/`).

SHA-256:

```
0d18d7f8d7910e2e0212f0f056b12f50bebc3abb7d88d2f7c7cb4c336fe4519a  cdn.min.js
```
