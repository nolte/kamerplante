---

ID: UI-NFR-002
Titel: Barrierefreiheit (Accessibility)
Kategorie: UI-Verhalten Unterkategorie: Accessibility, Inklusion
Technologie: React, TypeScript, MUI, Flutter
Status: Entwurf
Priorität: Hoch
Version: 1.0
Autor: Business Analyst - Agrotech
Datum: 2026-02-26
Tags: [accessibility, wcag, aria, keyboard-navigation, screenreader, a11y]
Abhängigkeiten: [UI-NFR-001]
Betroffene Module: [Frontend, Mobile]
---

# UI-NFR-002: Barrierefreiheit (Accessibility)

## 1. Business Case

### 1.1 User Story

**Als** Nutzer mit eingeschränktem Sehvermögen
**möchte ich** die Anwendung mit einem Screenreader bedienen können
**um** alle Funktionen gleichberechtigt nutzen zu können.

**Als** Nutzer mit motorischen Einschränkungen
**möchte ich** die Anwendung vollständig per Tastatur bedienen können
**um** nicht auf eine Maus angewiesen zu sein.

**Als** Produktmanager
**möchte ich** dass die Anwendung die WCAG 2.1 AA-Richtlinien erfüllt
**um** gesetzliche Anforderungen einzuhalten und die Nutzerbasis zu maximieren.

### 1.2 Geschäftliche Motivation

Barrierefreiheit ist nicht nur eine rechtliche Anforderung, sondern verbessert die Benutzererfahrung für alle Nutzer:

1. **Gesetzliche Pflicht** — In vielen Regionen ist WCAG-Konformität für Web-Anwendungen vorgeschrieben
2. **Erweiterte Nutzerbasis** — Ca. 15% der Weltbevölkerung leben mit einer Behinderung
3. **Verbesserte UX für alle** — Tastaturnavigation, klare Kontraste und strukturierte Inhalte helfen allen Nutzern
4. **SEO-Vorteile** — Semantisches HTML und ARIA-Landmarks verbessern die Auffindbarkeit

---

## 2. Anforderungen

### 2.1 WCAG-Konformität

| # | Regel | Stufe |
|---|-------|-------|
| R-001 | Die Anwendung MUSS die WCAG 2.1 Level AA Richtlinien vollständig erfüllen. | MUSS |
| R-002 | WCAG 2.1 Level AAA Kriterien SOLLEN wo möglich erfüllt werden, sind aber nicht verpflichtend. | SOLL |

### 2.2 Tastaturnavigation

| # | Regel | Stufe |
|---|-------|-------|
| R-003 | Alle interaktiven Elemente MÜSSEN per Tastatur (Tab, Shift+Tab, Enter, Space, Escape, Pfeiltasten) erreichbar und bedienbar sein. | MUSS |
| R-004 | Die Tab-Reihenfolge MUSS der visuellen Lesereihenfolge entsprechen (logische Reihenfolge im DOM). | MUSS |
| R-005 | Der aktuell fokussierte Element MUSS einen deutlich sichtbaren Focus-Indikator haben (mindestens 2px Outline, Kontrastunterschied ≥3:1 zum Hintergrund). | MUSS |
| R-006 | Focus DARF NICHT in Dropdowns, Tooltips oder anderen nicht-modalen Overlay-Elementen gefangen werden — Escape MUSS das Overlay schließen und den Fokus auf das auslösende Element zurücksetzen. | MUSS |
| R-007 | Skip-Links MÜSSEN implementiert werden, um die Hauptnavigation zu überspringen und direkt zum Hauptinhalt zu gelangen. | MUSS |
| R-008 | Tastaturfallen (Focus-Traps) DÜRFEN nur in Modalen eingesetzt werden und MÜSSEN per Escape verlassen werden können. | MUSS |

### 2.3 Screenreader-Kompatibilität

| # | Regel | Stufe |
|---|-------|-------|
| R-009 | Alle interaktiven Elemente MÜSSEN aussagekräftige ARIA-Labels oder sichtbare Labels haben. | MUSS |
| R-010 | Die Seitenstruktur MUSS ARIA-Landmarks verwenden (`banner`, `navigation`, `main`, `contentinfo`). | MUSS |
| R-011 | Dynamische Inhaltsänderungen MÜSSEN über ARIA-Live-Regions (`aria-live="polite"` oder `aria-live="assertive"`) angekündigt werden. | MUSS |
| R-012 | Bilder MÜSSEN aussagekräftige `alt`-Texte haben. Dekorative Bilder MÜSSEN `alt=""` und `aria-hidden="true"` verwenden. | MUSS |
| R-013 | Formulare MÜSSEN Labels haben, die programmatisch mit dem zugehörigen Eingabefeld verknüpft sind (`<label for="...">`). | MUSS |
| R-014 | Fehlermeldungen MÜSSEN programmatisch mit dem betroffenen Feld verknüpft sein (`aria-describedby`). | MUSS |

### 2.4 Farbkontraste

| # | Regel | Stufe |
|---|-------|-------|
| R-015 | Text MUSS ein Kontrastverhältnis von mindestens 4.5:1 gegenüber dem Hintergrund haben (WCAG AA). | MUSS |
| R-016 | Großer Text (≥18pt oder ≥14pt fett) MUSS ein Kontrastverhältnis von mindestens 3:1 haben. | MUSS |
| R-017 | UI-Komponenten und grafische Objekte MÜSSEN ein Kontrastverhältnis von mindestens 3:1 gegenüber angrenzenden Farben haben. | MUSS |
| R-018 | Informationen DÜRFEN NICHT ausschließlich über Farbe vermittelt werden — zusätzliche Indikatoren (Icons, Muster, Text) MÜSSEN verwendet werden. | MUSS |

### 2.5 Schriftgrößen & Zoom

| # | Regel | Stufe |
|---|-------|-------|
| R-019 | Die Anwendung MUSS bei einer Schriftvergrößerung bis 200% vollständig nutzbar bleiben (kein Verlust von Inhalten oder Funktionalität). | MUSS |
| R-020 | Schriftgrößen MÜSSEN in relativen Einheiten (rem, em) definiert werden, nicht in absoluten Pixelwerten. | MUSS |
| R-021 | Die Anwendung SOLL bei Browser-Zoom bis 400% im Reflow-Modus nutzbar bleiben (WCAG 1.4.10). | SOLL |

### 2.6 Animationen & Bewegung

| # | Regel | Stufe |
|---|-------|-------|
| R-022 | Die Anwendung MUSS die `prefers-reduced-motion` Media-Query respektieren und Animationen reduzieren oder deaktivieren. | MUSS |
| R-023 | Kein Inhalt DARF mehr als dreimal pro Sekunde blinken (Epilepsie-Prävention). | MUSS |

### 2.7 Drag-and-Drop-Alternativen & dynamische Layouts

Direktmanipulations-Muster (Drag-and-Drop-Sortieren, frei anordenbare Grids wie das
individualisierbare Dashboard aus REQ-045) sind mit Maus/Touch bedienbar, aber ohne
zusätzliche Vorkehrungen für Tastatur- und Screenreader-Nutzer unzugänglich. Diese Regeln
schließen die Lücke generisch für alle solchen Oberflächen.

| # | Regel | Stufe |
|---|-------|-------|
| R-024 | Jede Drag-and-Drop- oder Resize-Interaktion MUSS eine vollwertige, tastaturbedienbare Alternative bieten (z.B. „nach oben/unten"-Buttons, Größen-Stepper oder ein Kontext-/Kebab-Menü), die dieselben Zustandsänderungen erreicht wie die Zeigergeste. | MUSS |
| R-025 | Drag-/Resize-Handles, die ausschließlich per Maus/Touch funktionieren, DÜRFEN NICHT im Tab-Index liegen (`tabindex="-1"`) — es DÜRFEN keine fokussierbaren, aber funktionslosen Bedienelemente entstehen (WCAG 2.1.1). Die zugehörige Funktion MUSS über die Tastaturalternative (R-024) erreichbar bleiben. | MUSS |
| R-026 | In dynamisch positionierten Layouts (Grids, in denen die visuelle Position von der Einfügereihenfolge abweichen kann) MUSS die DOM-/Tab-/Vorlese-Reihenfolge der visuellen Lesereihenfolge folgen (Sortierung nach Zeile, dann Spalte) — Präzisierung von R-004 für dynamische Layouts (WCAG 1.3.2). | MUSS |
| R-027 | Das Ergebnis einer Umsortier-/Größenänderung per Tastaturalternative MUSS über eine ARIA-Live-Region (`aria-live="polite"`) angekündigt werden (z.B. „Widget an Position 2 von 6"). | MUSS |

---

## 3. Wireframe-Beispiele

### 3.1 Skip-Link-Verhalten

```
┌──────────────────────────────────┐
│ ┌──────────────────────────────┐ │
│ │ Zum Hauptinhalt springen ➜  │ │  ← Nur bei Tab sichtbar
│ └──────────────────────────────┘ │
│  Logo   Nav1   Nav2   Nav3  👤  │
├──────────────────────────────────┤
│                                  │
│  Hauptinhalt                     │  ← Fokus springt hierhin
│                                  │
└──────────────────────────────────┘
```

### 3.2 Focus-Indikator

```
  Nicht fokussiert:           Fokussiert:
  ┌──────────────┐           ╔══════════════╗
  │  Button      │           ║  Button      ║  ← 2px Outline
  └──────────────┘           ╚══════════════╝
                              ↑ Kontrastreich
```

### 3.3 Farbe + zusätzlicher Indikator

```
  ❌ Nur Farbe:               ✅ Farbe + Icon:
  ┌──────────────┐           ┌──────────────┐
  │  ● Erfolg    │           │  ✓ Erfolg    │
  │  ● Fehler    │           │  ✗ Fehler    │
  │  ● Warnung   │           │  ⚠ Warnung   │
  └──────────────┘           └──────────────┘
```

---

## 4. Akzeptanzkriterien

### Definition of Done

> **Jede Zeile nennt ihre durchsetzende Pruefung — oder sagt, dass es keine gibt (#1096).**
>
> Die vorige Fassung war reine Prosa und las sich, als waere alles davon verifiziert.
> Das ist die Fehlerklasse aus NFR-018 §1: eine Regel, die niemand misst, ist von
> einer nicht vorhandenen Regel nicht zu unterscheiden — nur teurer, weil sie
> Abdeckung suggeriert. Stand der Messung: **2026-08-15**.
>
> Es gibt genau **drei** automatisierte Pruefungen, und nur eine davon blockiert:
>
> | Pruefung | Wo | Blockierend? | Was sie wirklich misst |
> |---|---|---|---|
> | **vitest-axe** (`expectNoA11yViolations`, #1094) | `lint-test-build (22)` | **ja** — required Check auf `develop` | axe gegen einzelne Seiten/Komponenten in jsdom, Schwelle `critical`. Seiten brauchen `minElements`, sonst zertifiziert der Test ein Ladeskelett. |
> | **Lighthouse CI** (`categories:accessibility >= 0.98`, error) | Job `Lighthouse CI` | **nein** — advisory, absichtlich nicht in `.github/settings.yml` | Der statisch gebaute SPA-Shell (`./dist`), also die **unauthentifizierte** Huelle. Seiten hinter dem Login erreicht er nicht. |
> | **Kiosk-Theme-Test** (`kioskTheme.test.tsx`) | `lint-test-build (22)` | **ja** | Die MUI-Theme-Overrides (`KIOSK_TOUCH_TARGET = 64`), nicht die gerenderte Groesse eines Elements. Siehe UI-NFR-019. |
>
> Eine E2E-axe-Journey gegen die komponierte Anwendung existiert **nicht** (#1095, offen). Damit ist keine Seite hinter dem Login jemals im Browser auf Barrierefreiheit geprueft worden.

- [ ] **WCAG-Konformität**
    - [x] Automatisierte WCAG-Pruefung — **vitest-axe** (blockierend) + **Lighthouse CI** (advisory)
    - [ ] Manuelle Pruefung der Tastaturnavigation — **nicht durchgesetzt**, kein Gate, keine dokumentierte Durchfuehrung
    - [ ] Screenreader-Test (NVDA/VoiceOver) — **nicht durchgesetzt**, manuell und bisher nicht protokolliert
- [ ] **Tastaturnavigation** — **keine dieser Regeln ist durchgesetzt**
    - [ ] Alle Seiten vollstaendig per Tastatur bedienbar — kein Test; axe in jsdom prueft Fokus-*Reihenfolge* nicht
    - [ ] Tab-Reihenfolge logisch und konsistent — kein Test
    - [ ] Focus-Indikator sichtbar — kein Test (Sichtbarkeit ist eine Renderfrage, jsdom rechnet keine Styles)
    - [ ] Skip-Links implementiert und funktional — kein Test
    - [ ] Modale per Escape schliessbar — kein Test; MUI liefert es per Default, was nicht dasselbe ist wie „geprueft"
- [ ] **Screenreader** — teilweise durchgesetzt
    - [x] Formularfelder haben programmatisch verknuepfte Labels — **vitest-axe** (`label`-Regel, `critical`)
    - [x] Alle Bilder haben `alt`-Texte — **vitest-axe** (`image-alt`-Regel, `critical`)
    - [ ] ARIA-Landmarks auf jeder Seite — **nicht durchgesetzt**: die Landmark-Regeln melden an isoliert gerenderten Komponenten Falschbefunde und liegen unterhalb der `critical`-Schwelle
    - [ ] Dynamische Aenderungen ueber Live-Regions — **nicht durchgesetzt**, statisch nicht pruefbar
- [ ] **Kontraste** — **teilweise durchgesetzt**
    - [x] 4.5:1 fuer die Paletten-Rollen (`contrastText` auf `main`, auf `dark`, und `main` auf `background.default`, beide Themes) — `src/frontend/src/test/theme/paletteContrast.test.ts`, required Check `lint-test-build (22)`; das ist auch die einzige Instanz, die MUI-Buttons ueberhaupt misst (axe meldet sie wegen des TouchRipple-Overlays als `incomplete`)
    - [ ] 4.5:1 fuer komponierte Seiten (Text auf beliebigen Flaechen) — jsdom rechnet keine Farben; Lighthouse prueft es, ist aber advisory und sieht nur die unauthentifizierte Huelle
    - [ ] Keine Information nur ueber Farbe — kein automatisierter Test moeglich, keine Review-Checkliste
- [ ] **Schriftgrößen** — **nicht durchgesetzt**
    - [ ] 200% Zoom nutzbar — kein Test
    - [ ] Schriftgroessen in rem/em — kein Lint-Regel, kein Gate
- [ ] **Testing**
    - [x] Automatisierte Accessibility-Tests in der CI — **vitest-axe** im required Check
    - [ ] Lighthouse-Accessibility-Score als **blockierendes** Gate — heute advisory; Promotion erfolgt auf gemessener Historie per NFR-018 §4, nicht durch Aendern dieses Satzes
    - [ ] Manuelle Tests mit Tastatur und Screenreader — **nicht durchgefuehrt/protokolliert**

---

## 5. Risiken bei Nicht-Einhaltung

| Risiko | Auswirkung | Wahrscheinlichkeit | Mitigation |
|---|---|---|---|
| **Rechtliche Konsequenzen** | Klagen wegen mangelnder Barrierefreiheit | Mittel | WCAG-Compliance automatisiert prüfen |
| **Nutzerausschluss** | 15% der potenziellen Nutzer können die Anwendung nicht verwenden | Hoch | Accessibility von Anfang an mitdenken |
| **Schlechte Tastaturnavigation** | Power-User und Nutzer mit Einschränkungen können nicht effizient arbeiten | Hoch | Tab-Reihenfolge bei jedem Feature prüfen |
| **Unlesbare Texte** | Texte bei schlechtem Kontrast oder kleiner Schrift nicht lesbar | Mittel | Design-System mit geprüften Farbkombinationen |
| **Fehlende Screenreader-Unterstützung** | Blinde und sehbehinderte Nutzer können die Anwendung nicht verwenden | Mittel | ARIA-Labels als Teil der Komponenten-Checklist |

---

**Dokumenten-Ende**

**Version**: 1.0
**Status**: Entwurf
**Letzte Aktualisierung**: 2026-02-26
**Review**: Pending
**Genehmigung**: Pending
