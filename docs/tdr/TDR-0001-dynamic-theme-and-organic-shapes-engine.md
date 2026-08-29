# TDR-0001: Dynamische Corporate Design & Shape Engine

## Status
Akzeptiert (Accepted)

## Kontext
Die Webapplikation für Atemtherapie benötigt ein leichtes, beruhigendes und naturverbundenes Erscheinungsbild (orientiert an der Referenz `https://psychotherapie-aarberg.ch/`).
Die Praxisinhaberin soll in der Lage sein, Farbwelten und organische Formensprachen direkt in der Administrationskonsole auszuwählen und live zu editieren, ohne Code ändern oder Server neu starten zu müssen.

## Entscheidung
1. **Pusteblumen-Leitmotiv:**
   - Verwendung einer hochauflösenden botanischen Pusteblumen-Illustration (`dandelion_hero.png`) und animierten Schirmchen-Partikeln (`dandelion_seed_floating.png`), freigestellt ohne Hintergrund.
   - Symbolisiert die Leichtigkeit des Atems, das Loslassen von Anspannung und sanfte Entfaltung.

2. **5 Pastell-Farbkonzepte:**
   - `salbei_sand`: Sanftes Salbeigrün (#4A6C50) + Sand (#FAF8F5) (Standard)
   - `lavendel_nebel`: Lavendelblau (#5E5B7E) + Nebelgrau (#F8F7FB)
   - `terrakotta_puder`: Terrakotta (#965646) + Pudriges Altrosa (#FAF6F4)
   - `ozean_kiesel`: Nordisches Blau (#3D6473) + Kieselgrau (#F6F9FA)
   - `sonne_weizen`: Warmes Bernstein (#8C6838) + Elfenbein (#FBF9F3)

3. **5 Geometrische & Organische Formen:**
   - `dandelion_seed`: Pusteblumen-Samen (42% 58% 70% 30% / 45% 45% 55% 55%)
   - `soft_pebble`: Sanfter Kiesel (60% 40% 30% 70% / 60% 30% 70% 40%)
   - `breath_wave`: Atem-Welle (50% 50% 30% 70% / 50% 30% 70% 50%)
   - `zen_circle`: Zen-Atemringe (50%)
   - `fluid_capsule`: Fliessende Kapsel (2rem 6rem 2rem 6rem)

4. **Architektur-Integration:**
   - Entkopplung via Clean Architecture:
     - `ThemeConfig` in Domain Layer
     - `IThemeRepository` ABC
     - `SqlAlchemyThemeRepository` in Infrastructure
     - `ThemeService` in Application Layer zur Generierung dynamischer `:root` CSS-Variablen
     - `AdminController` Endpunkte `/admin/design`

## Konsequenzen
- **Vorteile:**
  - 100% dynamische Farbanpassung in Echtzeit ohne Build-Step
  - Volle Typensicherheit und Testbarkeit aller Presets
  - Hohe Barrierefreiheit und Lesbarkeit (Kontrastverhältnisse geprüft)
- **Neutral:**
  - Zusätzliche Tabelle `theme_configs` in der Datenbank.
