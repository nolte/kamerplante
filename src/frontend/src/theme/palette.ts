import { type PaletteOptions } from '@mui/material/styles';

export const lightPalette: PaletteOptions = {
  mode: 'light',
  primary: {
    main: '#2e7d32',
    light: '#60ad5e',
    dark: '#005005',
    contrastText: '#ffffff',
  },
  secondary: {
    main: '#5c6bc0',
    light: '#8e99f3',
    dark: '#26418f',
    contrastText: '#ffffff',
  },
  error: {
    main: '#d32f2f',
  },
  // `#ed6c02` is the documented brand warning colour and stays exactly as it is:
  // as a fill, icon or illustration colour it owes only 3:1 (WCAG 1.4.11) and
  // clears it. What fails is the *text MUI puts on top of it* — `contrastText`
  // is derived from `contrastThreshold`, which defaults to 3, so `#ed6c02`
  // clears the threshold, MUI picks white, and white on that orange measures
  // 3.11:1, under WCAG AA's 4.5:1 for normal text (UI-NFR-002, issue #1289).
  // Contrast is symmetric, so it is the same 3.11:1 read either way.
  //
  // Black rather than white: 6.75:1 on the same orange, one line, every filled
  // warning surface at once. The alternatives were rejected on blast radius, not
  // on taste — raising `contrastThreshold` to 4.5 would silently re-decide
  // `error` (`#d32f2f`, ~4.5:1 borderline) and every future palette entry
  // between 3 and 4.5, and darkening `main` would move a brand token that is
  // also the favourite-star colour in six places.
  //
  // Light palette only. `darkPalette.warning` is `#ffa726`, on which MUI already
  // derives near-black (measured 9.14:1), and `highContrastPalette` states its
  // own `contrastText` on a much darker orange (7.54:1) — neither is touched.
  warning: {
    main: '#ed6c02',
    contrastText: '#000000',
  },
  // `lightPalette` used to leave `info` undefined, so MUI's default `#0288d1`
  // applied and `getContrastText` picked white on it: 3.85:1, under WCAG 2.2
  // AA's 4.5:1 for normal text (UI-NFR-002, issue #1323). Every *filled* info
  // Chip, Button and Alert was below the bar, and every *outlined*/`text` one
  // too — `#0288d1` as a label on the `#f5f5f5` page background is 3.53:1.
  //
  // Darkened rather than repointing `contrastText` the way `warning` had to
  // (#1289): nothing pins `#0288d1`. It is MUI's default, not a brand token —
  // it appears in no design-guide table and at no call site as a literal, so
  // the constraint that ruled darkening out for `#ed6c02` (which is also the
  // favourite-star colour in six places) simply does not exist here.
  //
  // `#01579b` is MUI's own `lightBlue[900]`, the `dark` tone of the very ramp
  // being replaced — a value already in the system rather than an invented hex.
  // It repairs both failure directions with one line, which `contrastText`
  // could not have done: white on it is 7.4:1 (filled surfaces) and it is
  // 6.79:1 as a label on `#f5f5f5` (outlined and `text` surfaces). So `info`
  // needs none of the `MuiChip`/`MuiButton` `.dark` overrides that `warning`
  // carries — and therefore has no class selector that could go silently inert
  // the way `MuiButton-outlinedWarning` did for a week.
  //
  // Deliberately no explicit `contrastText`. MUI derives white on `#01579b` by
  // itself, and the *filled Alert* would ignore `contrastText` anyway — it
  // calls `getContrastText(main)`, which is exactly why #1289 needed a
  // `MuiAlert` override for warning. Measured here: the filled info Alert lands
  // at 7.4:1 unaided, so it needs no info sibling in that override. Stating
  // `contrastText` would only add a second place to keep in sync, and would
  // pin white in place if `main` were ever lightened again.
  //
  // `light`/`dark` stay derived. The contained-button hover, which swaps the
  // surface to `.dark` — the state that nearly broke in #1289 — measures
  // 11.27:1 (white on `#003c6c`). The standard and outlined info Alerts derive
  // from `.light`; both improved rather than regressed (9.58:1 -> 11.96:1 and
  // 9.74:1 -> 12.5:1).
  //
  // Light palette only. `darkPalette` leaves `info` unset too, but MUI's dark
  // default (`#29b6f6` with near-black text, 9.12:1) already clears AA, and
  // `highContrastPalette` states its own `#0b3d91` (10.04:1).
  info: {
    main: '#01579b',
  },
  success: {
    main: '#2e7d32',
  },
  background: {
    default: '#f5f5f5',
    paper: '#ffffff',
  },
};

/**
 * UI-NFR-019 §2.7 — high-contrast palette for kiosk & outdoor use. Pure
 * black-on-white surfaces (R-041), all text ≥ 7:1 against white (WCAG AAA,
 * R-040). Action colors keep a distinct hue but stay dark enough that their
 * white contrast text also clears 7:1 (used on filled buttons/chips).
 */
export const highContrastPalette: PaletteOptions = {
  mode: 'light',
  common: {
    black: '#000000',
    white: '#ffffff',
  },
  primary: {
    main: '#000000',
    light: '#000000',
    dark: '#000000',
    contrastText: '#ffffff',
  },
  secondary: {
    main: '#0b3d91',
    light: '#0b3d91',
    dark: '#062561',
    contrastText: '#ffffff',
  },
  // R-040 — #b71c1c only reaches 6.57:1 against white, below the required
  // 7:1 (WCAG AAA). #a41919 clears it with margin (7.69:1) while staying
  // recognizably red.
  error: {
    main: '#a41919',
    contrastText: '#ffffff',
  },
  // R-040 — #8a5000 only reaches 6.51:1 against white. #7c4800 clears it
  // with margin (7.54:1) while staying a recognizable amber/brown.
  warning: {
    main: '#7c4800',
    contrastText: '#ffffff',
  },
  success: {
    main: '#1b5e20',
    contrastText: '#ffffff',
  },
  info: {
    main: '#0b3d91',
    contrastText: '#ffffff',
  },
  background: {
    default: '#ffffff',
    paper: '#ffffff',
  },
  text: {
    primary: '#000000',
    secondary: '#000000',
  },
  divider: '#000000',
};

export const darkPalette: PaletteOptions = {
  mode: 'dark',
  primary: {
    main: '#66bb6a',
    light: '#98ee99',
    dark: '#338a3e',
    contrastText: '#000000',
  },
  secondary: {
    main: '#9fa8da',
    light: '#d1d9ff',
    dark: '#6f79a8',
    contrastText: '#000000',
  },
  // #1337 — `#ef5350` let MUI pick white (3.49:1 against it, contrastThreshold
  // is 3), so every filled error Chip, Button and Alert was under WCAG 2.2 AA's
  // 4.5:1 for normal text (UI-NFR-002).
  //
  // A dark role has to clear the bar on three surfaces, each a different
  // expression: `contrastText` on `main` (filled Chip / contained Button),
  // `contrastText` on `dark` (a contained Button's hover surface — and, in dark
  // mode, a filled Alert, which MUI paints on `.dark`), and `main` on the page
  // and paper backgrounds (outlined / text label).
  //
  // The first pass of this fix measured those with MUI's `getContrastRatio`,
  // which ignores alpha. MUI's derived `contrastText` for a light `main` is
  // `rgba(0,0,0,0.87)`, and composited over the derived `error.dark`
  // (rgb 178,96,89) it paints at 4.29:1 — not the 4.72 pure black would give.
  // `success` had the same shape on its derived `.dark` (4.15). So these roles
  // declare what they paint instead of leaving it to a derivation: pure black
  // text, and for `error` and `success` an explicit `dark` from the same MUI
  // ramp with real margin. `paletteContrast.test.ts` composites alpha before
  // measuring, so a derived rgba cannot pass again.
  //
  //   role      main      dark       filled   hover / filled Alert   label on #121212
  //   error     #ff8a80   #e57373    9.20     6.99                   8.21
  //   warning   #ffa726   derived    10.81    5.35                   9.6
  //   success   #66bb6a   #4caf50    8.88     7.56                   8.0
  //
  // `#ef5350` stays refused (white on it 3.49; black on it passes at rest but
  // fails its derived hover at 3.31), and darkening `main` to `#c62828` fails
  // the label direction at 3.34. A dark theme wants a lighter accent.
  error: {
    main: '#ff8a80',
    dark: '#e57373',
    contrastText: '#000000',
  },
  warning: {
    main: '#ffa726',
    contrastText: '#000000',
  },
  success: {
    main: '#66bb6a',
    dark: '#4caf50',
    contrastText: '#000000',
  },
  background: {
    default: '#121212',
    paper: '#1e1e1e',
  },
};
