# TDR-0002: Pusteblumen- & Samen-Aesthetik Engine (5 Modi & Deaktiviert)

## Status
Akzeptiert (Accepted)

## Kontext
Um die Markenidentität von «PUSTERUM» (dän. „Raum zum Atmen“) visuell erlebbar zu machen, soll das Leitmotiv der Pusteblume und ihrer fliegenden Samen über die gesamte Webseite hinweg dezent spürbar sein.
Die Praxisinhaberin benötigt in der Administrationskonsole (`/admin/design`) die volle Kontrolle, um zwischen 5 kreativen, dezenten Hintergrund- und Interaktionsmodi zu wählen oder alle Effekte vollständig zu deaktivieren.

## Entscheidung
1. **Betriebsmodi (`DandelionEffectMode`):**
   - `disabled` (**0. Deaktiviert**): Standard-Einstellung. Vollständig statische Seite ohne Hintergrund-Partikel oder Widgets.
   - `breathing_flow` (**1. Sanfter Atem-Drift**): 5–6 zarte Vektor-Schirmchensamen schweben im Hintergrund mit 3–5% Opazität in einem 4s/6s-Atemrhythmus.
   - `scroll_journey` (**2. Die Reise des Samens**): Ein einzelner, zarter Schirmchen-Samen löst sich oben und begleitet den Besucher beim Scrollen etappenweise bis zum Kontaktbereich.
   - `watermark_accents` (**3. Wasserzeichen-Akzente**): 100% statische, hochauflösende Vektor-Wasserzeichen an Sektionsrändern und beim Zitat, farblich synchronisiert mit dem Pastell-Theme.
   - `breath_widget` (**4. Interaktive Atem-Pause**): Schwebendes Zen-Widget unten rechts zum gemeinsamen Durchatmen im geführten 4-4-6 Atemrhythmus (Einatmen 4s, Halten 4s, Ausatmen 6s).
   - `whisper_trail` (**5. Sanfter Hauch bei Bewegung**): Ephemere, hauchdünne Samenpartikel entstehen bei sanfter Mausbewegung und verfliegen lautlos nach 1.2s.
   - `kids_flower` (**6. Atmende Blume für Kinder**, Ergänzung 2026-10): Geführte Kinder-Atemübung ohne Atemanhalten (3 s ein / 4 s aus, je 4 Atemzüge für Blume 1–3) mit sich öffnender SVG-Blüte und abschliessendem Pusten-Spiel (gedrückt halten = einatmen, loslassen = Samen fliegen). Teilt sich mit Modus 4 **einen** schwebenden Button: Sind beide aktiv, zeigt das Fenster Tabs («Atem-Pause» | «Atmende Blume»); es läuft immer nur die sichtbare Übung. Der Player (`components/kids_flower_player.html`, `js/components/kids-flower.js`) wird auch in der Sektion «Atmen mit Kindern» (`#kinder`) verwendet; Texte sind Content-Blöcke `kids.*`, druckbare A5-Karte unter `/atmende-blume/karte`.

2. **Technische Umsetzung & Performance-Garantien:**
   - **Reine Vektor-SVGs:** Keine externen Bild-Requests, gestochen scharfe Vektordarstellung bei minimaler DOM-Größe.
   - **GPU-beschleunigtes CSS:** Alle Schwebebewegungen laufen über `transform: translate3d()` und CSS-Keyframes (0 CPU-Last auf Mobilgeräten).
   - **Throttling & Lifecycle:** Partikel in Modus 5 sind auf max. 3 pro Sekunde limitiert und werden nach Ablauf von 1.2s automatisch aus dem Alpine-Array entfernt.
   - **Barrierefreiheit (`prefers-reduced-motion`):** Nutzer mit Bewegungsempfindlichkeit erhalten bei aktiven Animationsmodi automatisch eine statische, beruhigte Darstellung.
   - **Theme-Farbsynchronisation:** Alle Samen-Elemente verwenden `currentColor` und die CSS-Variablen `--theme-primary` / `--theme-secondary` mit dynamischen Alpha-Transparenzen.

3. **Architektur & Persistence:**
   - Domain Model: `DandelionEffectMode` Enum in `atem.domain.models.theme`
   - Data Layer: Spalte `dandelion_mode` in `theme_configs` Tabelle
   - Controller: Endpunkt `POST /admin/design/dandelion`
   - Template: `src/atem/presentation/templates/components/dandelion_ambient.html` eingebunden im `base.html` Layout.

## Konsequenzen
- **Vorteile:**
  - 100% Kontrolle für die Praxisinhaberin über die Intensität der visuellen Effekte.
  - Höchste Performance (60fps, Zero CPU Idle).
  - Hohe therapeutische Kohärenz zum Thema Atem und Entschleunigung.
- **Neutral:**
  - Zusätzliche Spalte `dandelion_mode` in `theme_configs`.
