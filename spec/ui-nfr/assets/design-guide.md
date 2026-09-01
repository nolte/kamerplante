# Kamerplanter Design Guide

> **Version:** 1.0
> **Status:** Entwurf
> **Datum:** 2026-03-02
> **Basis:** UI-NFR-009 (Visual Identity), UI-NFR-006 (Design-System), Konzept A „Keim im Topf"
> **Zweck:** Verbindliche Referenz fuer die Generierung aller visuellen Assets (Icons, Illustrationen, Maskottchen, Patterns) und fuer Design-Anpassungen in der Anwendung.
> **Generator:** Agnostisch — Stilbeschreibungen sind fuer jeden Bildgenerator (Gemini, Midjourney, DALL-E, Stable Diffusion, Flux) anpassbar.

---

## 1. Design-Philosophie

### 1.1 Leitmotiv: „Natur trifft Technologie"

Kamerplanter verbindet organische Pflanzenwelt mit datengetriebener Agrartechnologie. Das visuelle Design spiegelt dieses Spannungsfeld wider:

| Dimension | Auspraegung |
|-----------|-------------|
| **Organisch** | Weiche Formen, abgerundete Ecken (8px Basis), pflanzliche Motive, lebendige Gruentoene |
| **Technisch** | Klare Layouts, praezise Datenvisualisierung, strukturierte Grids, Indigo als Wissenschafts-Akzent |
| **Einladend** | Comic-Illustrationsstil, Maskottchen „Kami", freundliche Bildsprache |
| **Professionell** | Clean UI (MUI Material Design), keine uebertriebene Verspieltheit im Kern-Interface |

### 1.2 Design-DNA Attribute

```
Modern ......... Flat Design mit Tiefe (Soft Outlines, Layering), kein Skeuomorphismus
Natuerlich ..... Gruentoene dominieren, pflanzliche Formensprache in Illustrationen
Comic-artig .... Klare Outlines, flaechige Farben, freundliche Proportionen
Warm ........... Einladende Tonalitaet, keine kalte Industrieaesthetik
Verspielt ...... Humorvolle Details in Illustrationen, nicht im Kern-UI
Professionell .. Trotz Comic-Stil klar und funktional — kein Kinderspielzeug
```

### 1.3 Zwei-Welten-Prinzip

Das Design trennt bewusst zwischen **UI-Welt** und **Illustrations-Welt**:

| Ebene | Stilistik | Farbwelt | Beispiele |
|-------|-----------|----------|-----------|
| **UI-Welt** | MUI Material Design, clean, sachlich | Implementierte Palette (Abschnitt 2) | Buttons, Cards, Navigation, Formulare, Tabellen |
| **Illustrations-Welt** | Comic-Stil, verspielt, warm | Erweiterte Natur-Palette (Abschnitt 2.3) | Logo, Kami-Maskottchen, Empty States, Onboarding, Phasen-Icons |

Die UI-Welt darf NICHT mit Comic-Elementen ueberladen werden. Illustrationen erscheinen nur an definierten Stellen (Logo, Empty States, Onboarding, Erfolgs-/Fehlermeldungen, Ladeanimationen).

---

## 2. Verbindliche Farbpalette

### 2.1 UI-Kernpalette (Implementiert — Quelle der Wahrheit)

Diese Werte stammen aus `src/frontend/src/theme/palette.ts` und sind verbindlich.

#### Light Mode

| Rolle | Hex | RGB | Verwendung |
|-------|-----|-----|------------|
| **Primary** | `#2e7d32` | 46, 125, 50 | Hauptfarbe, CTAs, aktive Elemente, Links — sattes Blattgruen |
| Primary Light | `#60ad5e` | 96, 173, 94 | Hover-States, weiche Highlights |
| Primary Dark | `#005005` | 0, 80, 5 | Aktive States, Kontrast, Schatten |
| Primary Contrast | `#ffffff` | 255, 255, 255 | Text auf Primary-Flaechen |
| **Secondary** | `#5c6bc0` | 92, 107, 192 | Wissenschaftliche/technische Akzente — Indigo |
| Secondary Light | `#8e99f3` | 142, 153, 243 | Sekundaere Highlights |
| Secondary Dark | `#26418f` | 38, 65, 143 | Sekundaere Kontraste |
| Secondary Contrast | `#ffffff` | 255, 255, 255 | Text auf Secondary-Flaechen |
| **Error** | `#d32f2f` | 211, 47, 47 | Fehler, Schaedlingsbefall, kritische Warnungen |
| **Warning** | `#ed6c02` | 237, 108, 2 | Hinweise, Pflegebedarf, Aufmerksamkeit |
| Warning Contrast | `#000000` | 0, 0, 0 | Text auf gefuellten Warning-Flaechen — siehe Hinweis unten |
| Warning Dark | `#a54c01` | 165, 76, 1 | Warning **als Text** auf hellem Grund (Chip/Button `outlined` + `text`) |
| Warning Hover | `#d15f02` | 209, 95, 2 | Hover-Flaeche des gefuellten Warning-Buttons |
| **Info** | `#01579b` | 1, 87, 155 | Neutrale Hinweise, Zusatzinformation — siehe Hinweis unten |
| **Success** | `#2e7d32` | 46, 125, 50 | Erfolg, gesunde Pflanzen (= Primary) |
| **Background** | `#f5f5f5` | 245, 245, 245 | Seitenhintergrund |
| **Paper** | `#ffffff` | 255, 255, 255 | Karten, Dialoge, Oberflaechen |

> **Hinweis zu Warning (Issue #1289): schwarzer statt weisser Text auf Orange.**
>
> `#ed6c02` bleibt unveraendert die Marken-Warnfarbe. Als **Flaeche, Icon oder
> Illustration** schuldet sie nur 3:1 (WCAG 1.4.11) und erreicht das. Das Problem
> ist der **Text, den MUI darauf setzt**: `contrastText` wird aus
> `contrastThreshold` abgeleitet (Standard 3), `#ed6c02` erfuellt diese Schwelle,
> also waehlt MUI Weiss — und Weiss auf diesem Orange misst **3.11:1**, unter den
> 4.5:1, die WCAG 2.2 AA fuer normalen Text fordert (UI-NFR-002). Kontrast ist
> symmetrisch, es sind also in beide Leserichtungen dieselben 3.11:1.
>
> Entschieden wurde `warning.contrastText: '#000000'` — **6.75:1** auf demselben
> Orange, eine Zeile, alle gefuellten Warning-Flaechen auf einmal. Die
> Alternativen wurden wegen ihrer Reichweite verworfen, nicht wegen des
> Aussehens:
>
> - `contrastThreshold` auf 4.5 anheben wuerde stillschweigend auch `error`
>   (`#d32f2f`, grenzwertig ~4.5:1) und jeden kuenftigen Paletteneintrag zwischen
>   3 und 4.5 neu entscheiden;
> - `warning.main` abdunkeln wuerde den Marken-Token verschieben, der zugleich an
>   sechs Stellen die Favoriten-Stern-Farbe ist.
>
> Zwei Flaechen folgen dieser Entscheidung **nicht von allein** und sind deshalb
> im Theme nachgezogen:
>
> - Der **gefuellte Warning-Alert** liest `contrastText` gar nicht, sondern
>   leitet seine Schrift ueber `palette.getContrastText(warning.main)` her — das
>   wiederholt die Schwellenentscheidung und waehlt erneut Weiss (3.11:1).
> - Der **gefuellte Warning-Button** behaelt im Hover `contrastText` als Schrift,
>   tauscht aber die Flaeche gegen `warning.dark` (`#a54c01`). Schwarz darauf
>   ergaebe 3.60:1 — der Palettenfix haette also einen zuvor intakten Zustand
>   (Weiss auf `#a54c01`, 5.82:1) verschlechtert. Die Hover-Flaeche wird daher nur
>   um 12 % abgedunkelt (`#d15f02`), womit Schwarz bei 5.35:1 bleibt.
>
> Als **Text auf hellem Grund** bleibt `#ed6c02` unzureichend (2.85:1 auf
> `#f5f5f5`). Dort gilt weiterhin `warning.dark` `#a54c01` (5.34:1) — verwendet
> von Chip und Button in den Varianten `outlined` und `text`.
>
> Dark Mode und High-Contrast-Palette sind nicht betroffen: dort leitet MUI auf
> `#ffa726` bereits Nahezu-Schwarz ab (9.14:1), und die High-Contrast-Palette
> setzt ihr `contrastText` selbst auf einem deutlich dunkleren Orange (7.54:1).

> **Hinweis zu Info (Issue #1323): Farbe abgedunkelt statt Schrift umgestellt.**
>
> `lightPalette` hat `info` frueher gar nicht definiert. Damit galt MUIs
> Standardwert `#0288d1`, auf den `getContrastText` Weiss legt — **3.85:1**, also
> unter den 4.5:1 fuer normalen Text (UI-NFR-002). Betroffen waren **beide**
> Leserichtungen: gefuellte Info-Flaechen (Chip, Button, Alert) mit weisser
> Schrift *und* die Varianten `outlined`/`text`, die `#0288d1` selbst als Schrift
> auf dem Seitenhintergrund `#f5f5f5` zeichnen (**3.53:1**).
>
> Entschieden wurde `info.main: '#01579b'` — bewusst **anders** als bei Warning.
> Dort erzwang ein dokumentierter Marken-Token den Weg ueber `contrastText`;
> `#0288d1` ist dagegen kein Marken-Token, sondern MUIs Voreinstellung, steht in
> keiner Tabelle dieses Leitfadens und an keiner Aufrufstelle als Literal. Der
> Grund, der das Abdunkeln bei Warning ausgeschlossen hat, existiert hier also
> nicht.
>
> `#01579b` ist MUIs eigenes `lightBlue[900]`, der `dark`-Ton derselben Rampe —
> ein Wert, der im System bereits vorkommt, kein erfundener Hex. Er repariert
> **beide** Richtungen mit einer Zeile, was `contrastText` nicht geleistet
> haette: Weiss darauf **7.4:1**, und als Schrift auf `#f5f5f5` **6.79:1**.
>
> Daraus folgt bewusst, was hier **nicht** noetig war:
>
> - **Kein** `MuiChip`/`MuiButton`-Override auf `info.dark`, wie Warning es
>   braucht — die Rollenfarbe selbst genuegt jetzt als Schrift. Damit existiert
>   fuer Info auch kein Klassenselektor, der still wirkungslos werden koennte
>   (`MuiButton-outlinedWarning` war aus genau diesem Grund eine Woche lang
>   inert; MUI 9 kennt nur `MuiButton-outlined` **und** `MuiButton-colorWarning`
>   getrennt).
> - **Kein** `info`-Zweig im `MuiAlert`-Override. Der gefuellte Alert liest
>   `contrastText` zwar weiterhin nicht, sondern `getContrastText(info.main)` —
>   auf `#01579b` waehlt das aber von allein Weiss und landet bei **7.4:1**
>   (gemessen, nicht angenommen).
> - **Kein** explizites `contrastText`. Es waere eine zweite Stelle, die
>   mitgepflegt werden muss, und wuerde Weiss festnageln, falls `main` je wieder
>   aufgehellt wird.
>
> `light` und `dark` bleiben abgeleitet. Der Hover des gefuellten Info-Buttons
> tauscht die Flaeche gegen `info.dark` — der Zustand, der bei #1289 beinahe
> kaputtgegangen waere — und misst **11.27:1** (Weiss auf `#003c6c`). Der
> Standard- und der Outlined-Alert leiten aus `light` ab und haben sich
> **verbessert** statt verschlechtert: 9.58:1 auf 11.96:1 bzw. 9.74:1 auf 12.5:1.
> Sichtbar ist die Aenderung dort als etwas kuehlerer, weniger himmelblauer
> Farbton der Flaeche.
>
> Dark Mode und High-Contrast-Palette sind nicht betroffen: `darkPalette` laesst
> `info` ebenfalls offen, MUIs Dunkel-Voreinstellung `#29b6f6` traegt aber
> bereits Nahezu-Schwarz (9.12:1), und die High-Contrast-Palette setzt ihr
> eigenes `#0b3d91` (10.04:1).

#### Dark Mode

| Rolle | Hex | RGB | Verwendung |
|-------|-----|-----|------------|
| **Primary** | `#66bb6a` | 102, 187, 106 | Hauptfarbe — helleres, leuchtendes Gruen |
| Primary Light | `#98ee99` | 152, 238, 153 | Hover-States |
| Primary Dark | `#338a3e` | 51, 138, 62 | Aktive States |
| Primary Contrast | `#000000` | 0, 0, 0 | Text auf Primary-Flaechen |
| **Secondary** | `#9fa8da` | 159, 168, 218 | Akzente — helles Lavendel-Indigo |
| Secondary Light | `#d1d9ff` | 209, 217, 255 | Sekundaere Highlights |
| Secondary Dark | `#6f79a8` | 111, 121, 168 | Sekundaere Kontraste |
| Secondary Contrast | `#000000` | 0, 0, 0 | Text auf Secondary-Flaechen |
| **Error** | `#ff8a80` | 255, 138, 128 | Fehler — siehe Hinweis unten |
| **Warning** | `#ffa726` | 255, 167, 38 | Hinweise |
| **Success** | `#66bb6a` | 102, 187, 106 | Erfolg (= Primary) |
| **Background** | `#121212` | 18, 18, 18 | Seitenhintergrund |
| **Paper** | `#1e1e1e` | 30, 30, 30 | Karten, Dialoge |

> **Hinweis zu Error im Dark Mode (Issue #1337): Farbe aufgehellt, nicht Schrift umgestellt.**
>
> `darkPalette.error` stand auf `#ef5350` ohne eigenes `contrastText`. Weiss
> darauf misst **3.49:1** — MUIs `contrastThreshold` ist 3, `#ef5350` erfuellt
> diese Schwelle knapp, MUI waehlt daher Weiss, und jede gefuellte Error-Flaeche
> (Chip, Button, Alert) lag unter den 4.5:1 fuer normalen Text (UI-NFR-002).
>
> **`error` war die einzige betroffene Dunkel-Rolle.** Gemessen, nicht
> angenommen: `warning` (`#ffa726`), `success` (`#66bb6a`), `primary` und
> `secondary` liegen weit genug von Weiss entfernt, dass MUI Schwarz waehlt, und
> erreichen 8,9-10,8:1. Der reflexhafte Geschwister-Sweep war hier unnoetig.
>
> Eine Dunkel-Rolle muss in **drei** Richtungen bestehen, und jeder naheliegende
> Kandidat scheitert an einer anderen:
>
> | Kandidat | Fuellung | Hover (`.dark`) | Schrift auf `#121212` |
> |---|---|---|---|
> | `#ef5350` (vorher) | **3.49** | 6.36 | 5.38 |
> | `contrastText: '#000000'` | 6.02 | **3.31** | — |
> | `#c62828` (abgedunkelt) | 5.61 | 9.29 | **3.34** |
> | `#e57373` (MUI red 300) | 7.04 | **3.76** | 6.29 |
> | **`#ff8a80` (MUI red A100)** | **9.20** | **4.72** | **8.21** |
>
> Der in #1337 vorgeschlagene Weg — `contrastText: '#000000'`, also die Loesung
> von #1289 fuer helles Warning — ist damit **widerlegt**: MUI tauscht die
> Flaeche des gefuellten Buttons im Hover gegen `error.dark` und behaelt die
> Schrift, und Schwarz auf diesem dunkleren Rot misst 3.31:1. Abdunkeln von
> `main` scheitert an der Gegenrichtung, in der ein `outlined`-Chip seine Schrift
> in `main` auf den `#121212`-Seitenhintergrund zeichnet.
>
> Eine dunkle Palette will einen **helleren** Akzent — deshalb ist `#ff8a80`
> (MUIs `red.A100`, ein Token der bestehenden Rampe, kein erfundener Hex) zugleich
> die konventionelle und die einzig bestehende Antwort.
>
> Die Hover-Reserve ist mit 4.72:1 knapp, weil MUI `dark` aus `main` ableitet.
> Deshalb pinnt `src/frontend/src/test/theme/paletteContrast.test.ts` alle drei
> Richtungen fuer **jede** Dunkel-Rolle: eine Aenderung an dieser Ableitung kann
> nicht mehr still durchgehen. Der Test ist auch die einzige Instanz, die
> Buttons ueberhaupt sieht — axe-core meldet MUI-Buttons unter `color-contrast`
> als `incomplete`, weil die TouchRipple-Span das Label ueberlagert.

### 2.2 Phasenfarben (Pflanzenlebenszyklus)

Diese Farben werden sowohl in der UI (Phase-Badges, Timeline, Gantt-Charts) als auch in Illustrationen verwendet:

| Phase | Hex | Name | Verwendung |
|-------|-----|------|------------|
| Keimung | `#a5d6a7` | Zartgruen | Samen, erste Keimlinge |
| Saemling | `#66bb6a` | Fruehlings-Gruen | Junge Pflanze, erste echte Blaetter |
| Vegetativ | `#2e7d32` | Sattes Blattgruen | Volle Wachstumsphase (= Primary Light Mode) |
| Bluete | `#ab47bc` | Violett/Magenta | Bluehende Pflanze, Reproduktion |
| Ernte | `#ffa726` | Goldgelb | Reife Fruechte, Ernte (= Warning Dark Mode) |

### 2.3 Erweiterte Illustrations-Palette

Diese Farben ergaenzen die UI-Palette ausschliesslich in Illustrationen, im Maskottchen und in dekorativen Elementen:

| Rolle | Hex | Name | Verwendung in Illustrationen |
|-------|-----|------|------------------------------|
| **Terracotta** | `#8d6e63` | Erdton | Blumentoepfe, Erde, Substrat, Topf von Kami |
| Terracotta Hell | `#a1887f` | Heller Erdton | Highlights auf Toepfen |
| Terracotta Dunkel | `#6d4c41` | Dunkler Erdton | Schatten auf Toepfen |
| **Himmelblau** | `#4fc3f7` | Wasser | Bewaesserung, Wassertropfen, Regen, Giesskanne |
| **Sonnengelb** | `#ffb74d` | Warmgelb | Sonnenlicht, Photosynthese, warme Highlights |
| **Blueten-Violett** | `#ab47bc` | Violett | Blueten, Bluehphase-Illustrationen |
| **Erde Braun** | `#795548` | Dunkelbraun | Erde, Wurzeln, Baumrinde |
| **Blatt Hellgruen** | `#81c784` | Frisches Gruen | Junge Blaetter, Fruehlingsaustrieb |
| **Stiel** | `#43a047` | Mittelgruen | Pflanzenstiele, Aeste |

### 2.4 Farb-Hierarchie fuer Bildgeneratoren

Bei der Prompt-Formulierung fuer jeden Generator diese Verteilung einhalten:

```
Illustrations-Prompt Farbgewichtung:
  60% .... Gruentoene (#2e7d32, #66bb6a, #81c784, #43a047, #a5d6a7)
  20% .... Terracotta/Erdtoene (#8d6e63, #6d4c41, #795548)
  10% .... Akzente je nach Kontext (Himmelblau, Sonnengelb, Violett)
   5% .... Indigo (#5c6bc0) — nur bei Technologie-Bezug
   5% .... Neutraltoene (Weiss, Grau, Schwarz fuer Outlines)
```

---

## 3. Visuelles Konzept: „Keim im Topf" (Konzept A)

### 3.1 Kernidee

Das gesamte visuelle System basiert auf dem Motiv eines **freundlichen Keimlings in einem Terracotta-Topf**. Dieses Motiv zieht sich als roter Faden durch alle visuellen Assets:

- **Logo** — Stilisierter Keimling mit zwei Blaettern im Topf
- **Maskottchen „Kami"** — Anthropomorphe Version des Keimlings
- **Illustrationen** — Szenen rund um den Keimling und seine Welt
- **Icons** — Vereinfachte Pflanzen-/Topf-Motive
- **Patterns** — Subtile Blatt- und Ranken-Elemente

### 3.2 Formensprache

```
Grundformen des „Keim im Topf"-Systems:

  Blaetter ............. Organisch, leicht asymmetrisch, Tropfenform
                         Enden abgerundet, nie spitz oder aggressiv
                         2 Blaetter = Keimling, mehr = aeltere Pflanze

  Topf ................. Trapezfoermig (oben breiter), leicht konisch
                         Abgerundete obere Kante, flacher Boden
                         Dekorativer Mittelstreifen (Terracotta-Bandage)

  Stiel ................ Duenn, leicht geschwungen (nicht kerzengerade)
                         Kann sich in Maskottchen-Version zum „Hals" werden

  Wurzeln .............. Nur in Querschnitt-Darstellungen sichtbar
                         3-5 geschwungene Linien, asymmetrisch

  Gesicht (Maskottchen)  Grosse, runde Augen (Punkt oder Kreis)
                         Kleiner Mund (Linie oder Bogen)
                         Keine Nase, keine Ohren
                         Ausdruck ueber Augenform + Mundform + Blattwinkel
```

### 3.3 Strichstaerke & Outline-System

| Element | Strichstaerke | Stil |
|---------|--------------|------|
| Aeussere Kontur (Logo, Maskottchen) | 2.5–3px | Gleichmaessig, leicht abgerundet (round cap/join) |
| Innere Details (Blattadern, Topfstreifen) | 1.5–2px | Etwas duenner als Aussenkontur |
| Feine Akzente (Augen, Mund, kleine Details) | 1–1.5px | Duennste Stufe |
| Icon-Outlines (vereinfachte Varianten) | 2px einheitlich | Keine Abstufung bei Icons |

**Farbgebung der Outlines:**
- Light Mode: `#1b5e20` (sehr dunkles Gruen, NICHT reines Schwarz)
- Dark Mode: `#c8e6c9` (helles Gruen) oder `#ffffff` (Weiss)
- Monochrom: Reines Schwarz `#000000` bzw. Weiss `#ffffff`

### 3.4 Schatten & Tiefe

```
Schattensystem fuer Illustrationen:

  KEIN harter Drop-Shadow
  KEIN Photorealismus

  Stattdessen:
  - Weicher Flaechen-Schatten innerhalb der Form (Inner Shadow / Soft Shading)
  - Topf: Unterseite 10–15% dunkler als Basisfarbe
  - Blaetter: Basis zur Spitze leicht heller werdend
  - Optional: Sehr subtiler Kontaktschatten unter dem Topf (5% Opazitaet)

  Ziel: 2.5D-Eindruck — flach, aber mit Volumen-Anmutung
```

---

## 4. Logo-Spezifikation

### 4.1 Varianten-Matrix

| Variante | Format | Mindestgroesse | Hintergrund | Einsatzort |
|----------|--------|----------------|-------------|------------|
| **Primaer (horizontal)** | Bildmarke links + Schriftzug rechts | 160×40px | Transparent | Navbar, E-Mail-Header, Marketing |
| **Gestapelt (vertikal)** | Bildmarke oben + Schriftzug unten | 120×120px | Transparent | Login-Screen, Splash, Visitenkarten |
| **Bildmarke allein** | Nur Keimling im Topf, kein Text | 32×32px | Transparent | App-Icon, Favicon, kleine Kontexte |
| **Monochrom Schwarz** | Alle Formen in Schwarz | 32×32px | Transparent | Stempel, Wasserzeichen, Druck s/w |
| **Monochrom Weiss** | Alle Formen in Weiss | 32×32px | Transparent | Dark-Mode-Navbar, dunkle Hintergruende |

### 4.2 Logo-Aufbau (Bildmarke)

```
Anatomie der Bildmarke:

                 ╱╲
                ╱  ╲  .............. Linkes Blatt: leicht nach links geneigt
  Rechtes .... ╱    ╲              (organisch, nicht symmetrisch)
  Blatt       ╱      ╲
             ╱    ╲╱   ╲
                  │
                  │ ................ Stiel: duenn, leicht geschwungen
                  │
            ┌─────┴─────┐
            │           │ ......... Topf: Trapezform, Terracotta
            │  ═══════  │ ......... Dekostreifen: hellerer Terracotta-Ton
            │           │
            └───────────┘
```

**Proportionen:**
- Blaetter-Bereich: ca. 55% der Gesamthoehe
- Topf-Bereich: ca. 35% der Gesamthoehe
- Stiel: ca. 10% (Verbindung)
- Gesamtverhaeltnis Bildmarke: ca. 1:1.2 (Breite:Hoehe)

### 4.3 Logo-Schutzzone

```
Freiraum um das Logo = Halbe Hoehe der Bildmarke auf jeder Seite

          ┊         ┊
    ┈ ┈ ┈ ╱╲ ┈ ┈ ┈ ┈ ┈
          ╱  ╲
    ┊    ╱    ╲    ┊
         │    │
    ┊  ┌─┴────┐   ┊
       └──────┘
    ┈ ┈ ┈ ┈ ┈ ┈ ┈ ┈ ┈
          ┊         ┊

  Innerhalb der Schutzzone: KEINE anderen Elemente
```

### 4.4 Logo-Typografie

| Eigenschaft | Wert |
|------------|------|
| Font | Quicksand Bold (priorisiert) oder Comfortaa Bold (Alternative) |
| Stil | Gerundete Sans-Serif, freundlich, organisch |
| Laufweite | Leicht erhoehtes Letter-Spacing (+0.5–1px) |
| Gewicht | Bold (700) |
| Groesse | Relativ zur Bildmarke: Versalhoehe = ca. 30% der Bildmarkenhoehe |

**Hinweis:** Die Logo-Typografie ist NICHT identisch mit der UI-Typografie (Roboto). Das Logo hat eine eigene Schriftwelt.

### 4.5 Stilbeschreibung fuer Bildgeneratoren

#### Primaerlogo (horizontal)

```
Stilbeschreibung:
  Modernes, flaches Vektor-Logo fuer eine Agrartech-App namens „Kamerplanter".
  Ein freundlicher Comic-Keimling mit zwei gruenen Blaettern waechst aus einem
  kleinen Terracotta-Topf. Klare, gleichmaessige Outlines (2-3px) in dunklem
  Gruen, flaechige Farben mit subtiler weicher Schattierung fuer Tiefe.
  Der Keimling hat optional ein minimales freundliches Gesicht (Punktaugen,
  kleines Laecheln). Neben der Pflanze der Schriftzug „Kamerplanter" in einer
  gerundeten Sans-Serif-Schrift (Quicksand Bold).

  Farben exakt:
  - Blaetter: Frisches Gruen #66bb6a (Hauptton), Highlights #98ee99, Schatten #2e7d32
  - Topf: Terracotta #8d6e63, Highlight #a1887f, Schatten #6d4c41
  - Outline: Dunkles Gruen #1b5e20 (NICHT schwarz)
  - Hintergrund: Transparent

  Stil: Professioneller, moderner Cartoon/Comic-Stil. Vektor-Illustration.
  Kein Fotorealismus, keine Gradienten, keine 3D-Render-Optik.
  Seitverhaeltnis: 16:9
```

#### Bildmarke allein (App-Icon)

```
Stilbeschreibung:
  Minimales Comic-App-Icon eines freundlichen Keimlings mit zwei kleinen
  gruenen Blaettern in einem Terracotta-Topf. Optional winziges, freundliches
  Gesicht mit Punktaugen und kleinem Laecheln. Klare Outlines (2px),
  flaechige Farben, subtiler Schatten fuer Tiefe.

  Farben exakt:
  - Blaetter: #66bb6a (Haupt), #98ee99 (Highlight), #2e7d32 (Schatten)
  - Topf: #8d6e63, Streifen #a1887f
  - Outline: #1b5e20
  - Hintergrund: Transparent oder Weiss #ffffff

  Zentrierte Komposition. Safe Area fuer abgerundetes Quadrat beachten.
  Muss bei 32x32px noch erkennbar sein — minimale Details.
  Seitverhaeltnis: 1:1
  KEIN Text, KEINE Buchstaben im Bild.
```

#### Monochrom-Varianten

```
Schwarz:
  Schwarze Silhouette des Keimlings im Topf. Klare Outlines, minimale
  weisse Detail-Linien (Blattadern, Topfstreifen). Ikonisch, bei kleinen
  Groessen erkennbar. Schwarz auf weissem/transparentem Hintergrund.
  Vektor-Stil, Ein-Farben-Logo.

Weiss (Dark Mode):
  Weisse Silhouette des Keimlings im Topf auf dunklem Hintergrund (#1e1e1e).
  Klare Outlines, minimale dunkle Detail-Linien. Gleiche Form wie
  Schwarz-Variante, nur invertiert.
```

---

## 5. Maskottchen „Kami"

### 5.1 Charakter-Steckbrief

| Eigenschaft | Wert |
|------------|------|
| **Name** | Kami (Kurzform von Kamerplanter) |
| **Art** | Anthropomorpher Keimling in Terracotta-Topf |
| **Charakter** | Froehlich, hilfsbereit, neugierig, etwas tollpatschig |
| **Alter-Anmutung** | Jung, kindlich-unschuldig, aber nicht infantil |
| **Stilrichtung** | Kawaii-beeinflusst, aber professionell — kein reiner Kawaii |

### 5.2 Anatomie

```
Kami — Anatomische Referenz:

         🍃    🍃       Blaetter: 2 Stueck, tropfenfoermig, leicht asymmetrisch
          ╲  ╱           Fungieren als „Haare/Ohren" — druecken Stimmung aus
           ╲╱            (aufrecht = happy, haengend = traurig, schraeg = neugierig)
        ┌──────┐
        │ ◉  ◉ │         Augen: Gross, rund, ausdrucksstark, leichter Glanzpunkt
        │  ◡   │         Mund: Klein, einfache Form (Bogen/Linie), keine Zaehne
        └──┬───┘
           │              Stiel/Hals: Duenn, verbindet Kopfbereich mit Topf
       ┌───┴───┐
      ╱│       │╲        Arme: Duenne Stiel-Arme seitlich am Topf
       │  ═══  │         Dekostreifen am Topf: Hellerer Terracotta-Ring
       │       │         Topf: Konische Trapezform, Terracotta-Farben
       └───────┘
```

**Proportionen:**
- Kopf (Augenbereich bis Blaetter): ca. 45% der Gesamthoehe
- Topf: ca. 40% der Gesamthoehe
- Stiel: ca. 15%
- Blaetter-Spannweite: ca. 80% der Kopfbreite
- Augen: ca. 25% der Kopfbreite pro Auge

### 5.3 Stimmungsvarianten

Kami MUSS in den folgenden Stimmungen/Posen verfuegbar sein:

#### Pose 1: Happy (Standardpose)

```
Beschreibung: Aufrechte Haltung, Blaetter leicht nach oben, offene Augen
mit Glanzpunkt, laechelnder Mund (nach oben gebogene Linie). Arme locker
seitlich. Neutrale, freundliche Grundhaltung.

Einsatz: Default-Avatar, Profilbild, neutrale Zustaende
```

#### Pose 2: Feiernd (Erfolg/Phasenwechsel)

```
Beschreibung: Arme nach oben geworfen, Augen geschlossen vor Freude (^^),
Mund weit offen laechelnd. Eine kleine Bluete spriesst an einem Blatt.
Optionale Konfetti-Partikel um Kami herum. Blaetter aufgerichtet und
leicht wippend.

Einsatz: Phasenwechsel-Erfolg, Aufgabe erledigt, Ernte-Benachrichtigung
Akzentfarben: Goldgelb #ffa726 (Konfetti), Violett #ab47bc (Bluete)
```

#### Pose 3: Nachdenklich (Laden/Suche)

```
Beschreibung: Ein Arm am Kinn, Blick leicht nach oben gerichtet, ein Auge
etwas groesser als das andere (neugieriger Ausdruck). Fragezeichen schwebt
ueber einem Blatt. Blaetter leicht schraeg geneigt.

Einsatz: Ladezustand (mit Ladeanimation kombinierbar), Suchvorgaenge
```

#### Pose 4: Traurig (Fehler/Problem)

```
Beschreibung: Blaetter haengen herunter, Augen nach unten gerichtet mit
kleiner Traene. Mund als nach unten gebogene Linie. Arme haengen seitlich.
Gesamthaltung leicht zusammengesunken.

Einsatz: Fehlermeldungen, Verbindungsprobleme, fehlgeschlagene Aktionen
Hinweis: NICHT deprimierend — sympathisch-traurig, „es tut mir leid"-Ausdruck
```

#### Pose 5: Winkend (Willkommen/Onboarding)

```
Beschreibung: Ein Arm ausgestreckt und winkend, breites freundliches Laecheln.
Blaetter aufgerichtet und lebendig. Offene, einladende Koerperhaltung.

Einsatz: Onboarding-Wizard Schritt 1, Willkommensbildschirm, Login
```

#### Pose 6: Mit Lupe (Empty State)

```
Beschreibung: Ein Arm haelt eine Lupe vor ein Auge (Auge erscheint komisch
vergroessert durch die Linse). Neugieriger, suchender Ausdruck.
Blaetter leicht nach vorne geneigt.

Einsatz: Leere Listen, keine Suchergebnisse, keine Sensordaten
```

#### Pose 7: Mit Giesskanne (Ladevorgang)

```
Beschreibung: Haelt eine kleine Giesskanne und giesst sich selbst. Augen
geschlossen, zufriedener Ausdruck. Blaue Wassertropfen (#4fc3f7) fallen
vom Giesskannenhals.

Einsatz: Daten werden geladen, Synchronisation laeuft
```

### 5.4 Stilbeschreibung fuer Bildgeneratoren (Kami)

```
Stilbeschreibung — Character Sheet (alle Posen):
  Character-Design-Sheet des Maskottchens „Kami" fuer eine Pflanzen-App.
  Der Charakter ist ein kleiner, anthropomorpher gruener Keimling der aus
  einem kleinen Terracotta-Topf waechst. Zwei Blaetter oben wie Haare,
  grosse ausdrucksstarke Comic-Augen, kleiner Mund, duenne Stiel-Arme
  seitlich am Topf. Topf hat einen dekorativen Streifen.

  Sieben Posen in einer Reihe:
  (1) Froehlich stehend — Standardpose
  (2) Feiernd mit Konfetti und kleiner Bluete
  (3) Nachdenklich mit Fragezeichen
  (4) Traurig mit Traene, haengende Blaetter
  (5) Winkend, einladend
  (6) Mit Lupe am Auge, suchend
  (7) Giesst sich selbst mit kleiner Giesskanne

  Farben exakt:
  - Blaetter/Stiel: #66bb6a (Haupt), #98ee99 (Highlight), #2e7d32 (Schatten)
  - Topf: #8d6e63 (Basis), #a1887f (Streifen/Highlight), #6d4c41 (Schatten)
  - Outline: #1b5e20 (dunkles Gruen)
  - Augen: Schwarz mit weissem Glanzpunkt
  - Wasser (Pose 7): #4fc3f7
  - Konfetti (Pose 2): #ffa726, #ab47bc
  - Hintergrund: Transparent/Weiss

  Stil: Comic-Cartoon, Kawaii-Einfluss aber professionell.
  Klare Outlines (2-3px), flaechige Farben, weiche Schatten.
  Vektor-Illustrationsstil. KEIN Fotorealismus, KEINE 3D-Render-Optik.
  Seitverhaeltnis: 16:5 (Reihe) oder 1:1 (Einzelpose)
```

---

## 6. Illustrationsstil-Richtlinien

### 6.1 Allgemeine Stilmerkmale

Alle Kamerplanter-Illustrationen MUESSEN diesen Merkmalen folgen:

| Merkmal | Spezifikation |
|---------|--------------|
| **Outlines** | Gleichmaessige Strichstaerke (2-3px), runde Enden (round cap/join), dunkles Gruen (#1b5e20) — NICHT schwarz |
| **Flaechenfuellung** | Solide Farben aus der Illustrations-Palette, KEINE fotorealistischen Texturen |
| **Schatten** | Weiche Flaechenschatten (10-15% dunkler als Basisfarbe), KEIN harter Drop-Shadow |
| **Proportionen** | Leicht ueberproportionierte Blaetter und Blueten (freundlich, lebendig), realistische Grundform |
| **Farbpalette** | Maximal 6-8 Farben pro Illustration (aus der definierten Palette) |
| **Hintergruende** | Einfarbig oder transparent, KEINE komplexen Szenerien im Hintergrund |
| **Perspektive** | Leichte Schraegansicht (3/4-Ansicht) oder frontale Ansicht, KEINE extreme Perspektive |
| **Details** | Reduziert auf das Wesentliche — bei kleinen Groessen muessen Motive erkennbar bleiben |

### 6.2 Pflanzen-Darstellung

```
DO:
  + Blaetter mit sichtbaren Blattadern (1-3 Linien, vereinfacht)
  + Leicht asymmetrische, organische Formen
  + Lebendige Gruentoene mit Farbvariation (nicht alles ein Gruen)
  + Erdreich im Topf als Farbflaeche (#795548)
  + Tropfenform fuer Blaetter, Bogenform fuer Blueten

DON'T:
  - Botanisch exakte Darstellungen (kein Lehrbuch-Stil)
  - Tote, welke oder haessliche Pflanzen (ausser Error-State)
  - Mehr als 8 Blaetter pro Pflanze (Klarheit)
  - Realistische Insekten (bei IPM-Illustrationen stilisieren)
  - Photorealistische Texturen auf Blaettern oder Toepfen
```

### 6.3 Szenen-Komposition (Empty States, Onboarding)

| Szenentyp | Komposition | Stimmung | Kami-Pose |
|-----------|-------------|----------|-----------|
| **Leerer Garten** | Indoor-Regal mit leeren Toepfen, Licht durch Fenster | Einladend, Potenzial | Lupe (suchend) |
| **Erfolg/Phasenwechsel** | Bluehende Pflanze, Konfetti, Funkeln | Feiernd, stolz | Feiernd |
| **Fehler/Problem** | Regen-Szene, kleine Wolke, Regenschirm | Mitfuehlend, nicht deprimierend | Traurig |
| **Laden** | Gewaechshaus-Innenansicht, Pflanzen auf Regalen | Ruhig, geduldig | Giesskanne |
| **Onboarding Schritt 1** | Kami allein, einladende Geste | Warm, willkommen | Winkend |
| **Onboarding Schritt 2–5** | Kontextabhaengig (Pflanze waehlen, Standort, etc.) | Hilfreich, begleitend | Nachdenklich/Happy |
| **Keine Suchergebnisse** | Kami mit Lupe, leere Flaeche | Verstaendnisvoll | Lupe |
| **Offline/Kein Netzwerk** | Kami mit durchgetrenntem Kabel/WLAN-Symbol | Mitfuehlend | Traurig |

### 6.4 Stilbeschreibung fuer Szenen-Illustration

```
Stilbeschreibung — Szene „Leerer Garten" (Beispiel):
  Charmante Comic-Illustration einer Indoor-Gartenszene. Ein Regal mit
  leeren Terracotta-Toepfen, einem kleinen Beutel Erde und einer winzigen
  Giesskanne. Sonnenlicht faellt durch ein Fenster. Im Zentrum steht Kami
  (kleiner Keimling-Charakter im Topf) und haelt eine Lupe, schaut
  neugierig umher.

  Farben exakt:
  - Kami: #66bb6a/#2e7d32 (Blaetter), #8d6e63 (Topf)
  - Toepfe/Regal: #8d6e63, #a1887f (Terracotta-Toene)
  - Sonnenlicht: #ffb74d (warme Akzente)
  - Hintergrund: Weiches Beige #fafaf5 oder transparent
  - Regal/Holz: #a1887f / #6d4c41

  Stil: Flat-Vector-Illustration, klare Outlines, naturinspiriert,
  gemuetliche Indoor-Szene. Warm und einladend.
  Seitverhaeltnis: 16:9
  KEIN Fotorealismus, KEINE Menschen, KEINE 3D-Render-Optik.
```

---

## 7. Phasen-Illustrationen

### 7.1 Fuenf-Phasen-Reihe

Die fuenf Wachstumsphasen werden als zusammenhaengende Illustrations-Reihe dargestellt. Jede Phase zeigt dieselbe Pflanze in fortschreitender Entwicklung, im selben Topf, im selben Stil:

| Phase | Pflanze | Phasenfarbe | Details |
|-------|---------|-------------|---------|
| **1. Keimung** | Samen bricht auf, winziger Trieb | `#a5d6a7` Zartgruen | Erdreich sichtbar, erster weisser Keim |
| **2. Saemling** | Keimling mit Keimblaettern + erste echte Blaetter | `#66bb6a` Fruehlings-Gruen | 2-4 kleine Blaetter, duenner Stiel |
| **3. Vegetativ** | Buschige Pflanze mit vielen Blaettern | `#2e7d32` Sattes Gruen | Kraeftig, viele Blaetter, stabiler Stiel |
| **4. Bluete** | Pflanze mit Blueten | `#ab47bc` Violett | 2-3 Blueten, Blaetter weiterhin gruen |
| **5. Ernte** | Pflanze mit reifen Fruechten | `#ffa726` Goldgelb | Fruechte in Goldgelb, einige Blaetter |

### 7.2 Stilbeschreibung fuer Phasen-Reihe

```
Stilbeschreibung:
  Fuenf Wachstumsphasen einer Pflanze in konsistentem Comic-Stil,
  von links nach rechts angeordnet:
  (1) Samen keimt in Erde, blassgruen #a5d6a7
  (2) Kleiner Saemling mit ersten echten Blaettern, fruehlings-gruen #66bb6a
  (3) Buschige vegetative Pflanze mit vielen Blaettern, sattes gruen #2e7d32
  (4) Blutende Pflanze mit violett-magenta Blueten #ab47bc
  (5) Erntereife Pflanze mit goldgelben Fruechten #ffa726

  Alle in gleichen Terracotta-Toepfen (#8d6e63). Outlines in dunklem
  Gruen (#1b5e20), 2-3px gleichmaessig. Flaechige Farben, weiche Schatten.
  Konsistenter Comic-Stil, Wachstumsprogression.

  Stil: Vektor-Illustration, botanisch inspiriert aber vereinfacht.
  Seitverhaeltnis: 16:5 (Reihe) oder je 1:1.5 (einzeln)
  KEIN Fotorealismus, KEINE 3D-Optik.
```

---

## 8. Icon-System

### 8.1 Zwei Icon-Ebenen

| Ebene | Typ | Stil | Verwendung |
|-------|-----|------|------------|
| **UI-Icons** | MUI Material Icons (Filled) | Standard-Material-Design | Navigation, Aktions-Buttons, Listen-Icons, Toolbar |
| **Feature-Icons** | Custom Kamerplanter-Illustrationen | Vereinfachter Comic-Stil | Feature-Highlights, Marketing, Onboarding-Schritte |

Die UI bleibt bei MUI Material Icons fuer funktionale Zwecke. Custom-Illustrierte Icons kommen NUR an besonderen Stellen zum Einsatz.

### 8.2 Custom Feature-Icons (illustriert)

Fuer Feature-Seiten, Marketing und Onboarding koennen illustrierte Icons erstellt werden:

| Feature | Motiv | Farb-Akzent |
|---------|-------|-------------|
| Stammdaten | Offenes Buch mit Blatt | Primary Gruen |
| Phasensteuerung | Zeitstrahl mit Phasenfarben | Phasen-Gradient |
| Duenge-Logik | Reagenzglas mit Naehrloesung | Indigo #5c6bc0 |
| Sensorik | Thermometer mit Blatt | Himmelblau #4fc3f7 |
| Aufgaben | Checkliste mit Pflanzenmotiv | Primary Gruen |
| Ernte | Korb mit goldenen Fruechten | Goldgelb #ffa726 |
| IPM / Pflanzenschutz | Schild mit Blatt | Primary Gruen + Error Rot |
| Kalender | Kalenderblatt mit Keimling | Primary Gruen |
| Bewaesserung | Giesskanne mit Tropfen | Himmelblau #4fc3f7 |
| Tankmanagement | Tank/Eimer mit Wasser | Himmelblau #4fc3f7 |
| Standortverwaltung | Gewaechshaus-Silhouette | Terracotta #8d6e63 |
| Onboarding | Kami (winkend) | Vollfarb-Palette |

### 8.3 Stilbeschreibung fuer Feature-Icons

```
Stilbeschreibung:
  Set von 12 Feature-Icons fuer eine Agrartech-App. Jedes Icon zeigt ein
  vereinfachtes Motiv in einem einheitlichen Comic-Stil: klare Outlines
  (2px, dunkles Gruen #1b5e20), flaechige Farben aus der Kamerplanter-
  Palette, keine Gradienten, runde Ecken, minimale Details.

  Jedes Icon zentriert auf transparentem Hintergrund.
  Icons muessen bei 24x24px noch erkennbar sein.
  Seitverhaeltnis: 1:1
  Gittergroessen: 24×24, 48×48, 96×96 (identisches Motiv, gleiche Details)

  Primaer-Farben:
  - Gruene Elemente: #2e7d32 (dunkel), #66bb6a (mittel), #a5d6a7 (hell)
  - Terracotta: #8d6e63
  - Wasser/Blau: #4fc3f7
  - Frucht/Gelb: #ffa726
  - Technik/Indigo: #5c6bc0
  - Outline: #1b5e20

  Stil: Flat, clean, ikonisch. Vektor-tauglich.
  KEIN Text in den Icons. KEIN Fotorealismus.
```

---

## 9. Hintergrund-Patterns & Dekoelemente

### 9.1 Subtiles Blatt-Pattern (Login/Splash)

```
Stilbeschreibung:
  Nahtloses, kachelbares Muster aus sehr subtilen, minimalen Linien-
  Zeichnungen von Blaettern und kleinen botanischen Elementen. Nur duenne,
  feine Outlines (0.5-1px), KEINE Fuellung. Sehr helles Salbeibegruen
  (#c8e6c9 bei ca. 30% Opazitaet) auf weissem Hintergrund.

  Sparsam, elegant, NICHT busy. Kleine Blaetter, winzige Aeste, zarte Punkte.
  Minimalistisches botanisches Muster, dekorativer Hintergrund.

  Seitverhaeltnis: 1:1 (kachelbar/tileable)
  KEIN Fotorealismus, KEINE kraeftigen Farben, KEINE dicken Linien.
```

### 9.2 Dark-Mode-Variante des Patterns

```
Stilbeschreibung:
  Gleiches botanisches Linien-Muster wie Light-Version, aber in sehr
  dunklem, dezentem Gruen (#1b5e20 bei ca. 10% Opazitaet) auf fast-
  schwarzem Hintergrund (#121212).

  Kaum sichtbar, nur bei genauem Hinsehen erkennbar. Atmosphaerisch,
  nicht ablenkend.
```

### 9.3 Dekorative Eck-Ornamente

```
Stilbeschreibung:
  Set von 8-10 kleinen dekorativen botanischen Eckverzierungen und
  Trennlinien im Comic-Stil. Einfache gruene Blattzweige, winzige
  Ranken-Kringel, kleine Bluetenknospen, minimale Ast-Elemente.

  Farben: Gruen #2e7d32, Terracotta #8d6e63 (sparsam), weisser Hintergrund.
  Klare Outlines, flaechige Farben. UI-Dekorationselemente.

  Seitverhaeltnis: 1:1 (Grid-Anordnung)
  KEIN Fotorealismus, NICHT komplex, NICHT ueberladen.
```

---

## 10. App-Icon & Favicon Spezifikation

### 10.1 Groessen-Matrix

| Kontext | Groessen (px) | Format | Besonderheiten |
|---------|--------------|--------|----------------|
| **Favicon** | 16, 32 | ICO, PNG | Stark vereinfacht: nur Silhouette |
| **Web App** | 48, 64, 128, 192, 256, 512 | PNG | Volle Detailstufe ab 48px |
| **Apple Touch** | 180 | PNG | Kein Transparenz-Hintergrund, abgerundete Ecken vom OS |
| **Android Adaptive** | 108 (Foreground) + 108 (Background) | PNG | Safe Area beachten (66% sichtbar) |
| **PWA Maskable** | 512 | PNG | Extra Padding fuer maskable Area |
| **SVG** | Skalierbar | SVG | Primaerformat, optimiert (svgo) |

### 10.2 Vereinfachung fuer kleine Groessen

```
512px .... Volle Details: Blaetter mit Adern, Topf-Streifen, optionales Gesicht
128px .... Leicht reduziert: Blattadern entfernt, Streifen vereinfacht
 48px .... Stark reduziert: Nur Silhouetten von Blaettern und Topf, kein Gesicht
 32px .... Nur Grundform: Zwei Blaetter + Trapez-Topf, keine inneren Details
 16px .... Maximal reduziert: Abstrahierte Form, kaum erkennbar als Einzelheiten
```

---

## 11. Typografie-System

### 11.1 UI-Typografie (implementiert)

| Rolle | Font | Groesse | Gewicht | Zeilenhoehe |
|-------|------|---------|---------|-------------|
| H1 | Roboto | 2rem (32px) | 600 (Semi-Bold) | 1.2 |
| H2 | Roboto | 1.75rem (28px) | 600 | 1.3 |
| H3 | Roboto | 1.5rem (24px) | 600 | 1.3 |
| H4 | Roboto | 1.25rem (20px) | 600 | 1.4 |
| H5 | Roboto | 1.125rem (18px) | 600 | 1.4 |
| H6 | Roboto | 1rem (16px) | 600 | 1.5 |
| Body1 | Roboto | 1rem (16px) | 400 | 1.5 |
| Body2 | Roboto | 0.875rem (14px) | 400 | 1.43 |
| Caption | Roboto | 0.75rem (12px) | 400 | 1.66 |
| Button | Roboto | — | 600 | — |

### 11.2 Logo-Typografie (eigenstaendig)

| Rolle | Font | Gewicht | Stil |
|-------|------|---------|------|
| Logo-Schriftzug | Quicksand (primaer) | Bold (700) | Gerundete Sans-Serif |
| Fallback | Comfortaa | Bold (700) | Gerundete Sans-Serif |

### 11.3 Hinweis fuer Generatoren

Bei der Logo-Generierung IMMER angeben:
```
Schrift: "Rounded sans-serif font like Quicksand Bold or Comfortaa Bold"
Nicht: Roboto, Arial, Helvetica oder andere eckige Sans-Serif-Fonts
```

---

## 12. Design-Tokens Referenz

### 12.1 Spacing (4px-Basis)

| Token | Wert | Verwendung |
|-------|------|------------|
| `spacing.xs` | 4px | Minimaler Abstand, Icon-Padding |
| `spacing.sm` | 8px | Kompakte Elemente, Button-Padding |
| `spacing.md` | 16px | Standard-Abstand, Card-Padding |
| `spacing.lg` | 24px | Sektions-Abstand |
| `spacing.xl` | 32px | Grosse Abstaende |
| `spacing.xxl` | 48px | Maximale Abstaende, Hero-Padding |

### 12.2 Border-Radii

| Token | Wert | Verwendung |
|-------|------|------------|
| `radii.sm` | 4px | Kleine Elemente (Badges, Chips) |
| `radii.md` | 8px | **Standard** (Cards, Buttons, Inputs) |
| `radii.lg` | 12px | Groessere Karten, Dialoge |
| `radii.xl` | 16px | Hervorgehobene Elemente |
| `radii.round` | 50% | Kreisfoermige Elemente (Avatare, FABs) |

### 12.3 Sidebar

| Token | Wert |
|-------|------|
| `sidebarWidth` | 240px |

---

## 13. Asset-Organisation

### 13.1 Verzeichnisstruktur

```
assets/brand/
  ├── logo/
  │   ├── logo-kamerplanter-horizontal.svg
  │   ├── logo-kamerplanter-horizontal-dark.svg
  │   ├── logo-kamerplanter-stacked.svg
  │   ├── logo-kamerplanter-icon.svg
  │   ├── logo-kamerplanter-mono-black.svg
  │   ├── logo-kamerplanter-mono-white.svg
  │   └── png/
  │       ├── logo-kamerplanter-icon-16.png
  │       ├── logo-kamerplanter-icon-32.png
  │       ├── logo-kamerplanter-icon-48.png
  │       ├── logo-kamerplanter-icon-64.png
  │       ├── logo-kamerplanter-icon-128.png
  │       ├── logo-kamerplanter-icon-192.png
  │       ├── logo-kamerplanter-icon-256.png
  │       └── logo-kamerplanter-icon-512.png
  ├── mascot/
  │   ├── mascot-kami-happy.svg
  │   ├── mascot-kami-celebrating.svg
  │   ├── mascot-kami-thinking.svg
  │   ├── mascot-kami-sad.svg
  │   ├── mascot-kami-waving.svg
  │   ├── mascot-kami-magnifier.svg
  │   ├── mascot-kami-watering.svg
  │   └── lottie/
  │       ├── mascot-kami-idle.lottie
  │       └── mascot-kami-watering.lottie
  ├── illustrations/
  │   ├── scene-empty-garden.svg
  │   ├── scene-success-celebration.svg
  │   ├── scene-error-rain.svg
  │   ├── scene-loading-greenhouse.svg
  │   ├── scene-onboarding-welcome.svg
  │   └── phases/
  │       ├── phase-germination.svg
  │       ├── phase-seedling.svg
  │       ├── phase-vegetative.svg
  │       ├── phase-flowering.svg
  │       └── phase-harvest.svg
  ├── icons/
  │   ├── icon-stammdaten.svg
  │   ├── icon-phases.svg
  │   ├── icon-fertilizer.svg
  │   ├── icon-sensors.svg
  │   ├── icon-tasks.svg
  │   ├── icon-harvest.svg
  │   ├── icon-ipm.svg
  │   ├── icon-calendar.svg
  │   ├── icon-watering.svg
  │   ├── icon-tank.svg
  │   ├── icon-location.svg
  │   └── icon-onboarding.svg
  └── patterns/
      ├── pattern-leaves-light.svg
      ├── pattern-leaves-dark.svg
      └── pattern-ornaments.svg
```

### 13.2 Namenskonvention

```
[typ]-[name]-[variante].[format]

Typen:     logo, mascot, scene, phase, icon, pattern
Varianten: happy, sad, light, dark, mono-black, mono-white, horizontal, stacked
Formate:   svg (primaer), png (raster), webp (optimiert), lottie (animation)
```

---

## 14. Checkliste fuer Bildgenerator-Prompts

Bei JEDEM Prompt fuer einen Bildgenerator diese Punkte einhalten:

### 14.1 Pflicht-Bestandteile

- [ ] **Exakte Hex-Farben** aus Abschnitt 2 angeben (nie nur „green" oder „brown")
- [ ] **Outline-Farbe** spezifizieren: `#1b5e20` (NICHT schwarz, ausser bei Monochrom)
- [ ] **Outline-Staerke** angeben: 2-3px fuer Hauptelemente, 1.5-2px fuer Details
- [ ] **Stil explizit** beschreiben: „flat vector illustration, comic/cartoon style, clean outlines"
- [ ] **Negative Anweisungen**: „NO photorealism, NO 3D render, NO realistic textures, NO gradients"
- [ ] **Hintergrund** spezifizieren: transparent, weiss, oder spezifische Farbe
- [ ] **Seitverhaeltnis** angeben
- [ ] **Format-Absicht** angeben: „suitable for SVG conversion", „vector illustration aesthetic"

### 14.2 Empfohlene Negative Anweisungen

```
Vermeiden (in jeden Prompt einbauen):
- Photorealistische Texturen
- 3D-gerenderte Optik
- Komplexe Hintergruende
- Text/Typografie im Bild (wird von KI schlecht generiert)
- Clip-Art-Stil (zu generisch)
- Kindlich-infantiler Cartoon-Stil (zu unserioes)
- Wasserzeichen
- Markenlogos anderer Firmen
- Fotografische menschliche Gesichter
- Harte Schlagschatten
```

### 14.3 Generator-spezifische Anpassungen

| Generator | Besonderheiten | Prompt-Anpassung |
|-----------|---------------|-----------------|
| **Gemini Imagen** | Gutes Farbverstaendnis, akzeptiert Hex-Werte | Farben als „Color: [name] (#hex)" formulieren |
| **Midjourney** | Stark bei Illustration, eigene Syntax | `--ar`, `--s`, `--v`, `--no` Parameter anhaengen |
| **DALL-E 3** | Gutes Textverstaendnis, natuerliche Sprache | Ausfuehrliche Prosabeschreibung, keine Sonder-Parameter |
| **Stable Diffusion** | Negative Prompts separat, Gewichtung mit `()` | Positive + Negative Prompts trennen, Gewichtung nutzen |
| **Flux** | Gutes Text-Rendering, natuerliche Sprache | Aehnlich DALL-E, ausfuehrliche Beschreibung |

---

## 15. Abgrenzung: Was dieses Dokument NICHT abdeckt

| Thema | Referenz-Dokument |
|-------|-------------------|
| Exakte MUI-Komponenten-Tokens | UI-NFR-006 |
| Responsive Breakpoints | UI-NFR-001 |
| Barrierefreiheit / WCAG | UI-NFR-002 |
| Lottie-Animations-Specs (Dauer, Dateigr.) | UI-NFR-009 §3.3 R-019 |
| Kiosk-Modus-Design | UI-NFR-019 |
| Konkrete Midjourney-Prompts (toolspezifisch) | `spec/ui-nfr/assets/midjourney-prompts.md` |

---

## Aenderungshistorie

| Version | Datum | Aenderung |
|---------|-------|-----------|
| 1.0 | 2026-03-02 | Initiale Version. Konzept A „Keim im Topf" als verbindliche Grundlage. Implementierte Palette als Quelle der Wahrheit. Generatoragnostische Stilbeschreibungen. |
