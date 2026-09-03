import { createTheme, darken, type Theme } from '@mui/material/styles';
import { lightPalette, darkPalette, highContrastPalette } from './palette';
import { typography } from './typography';
import { breakpoints, radii } from './tokens';
import { kioskThemeOverrides } from '@/kiosk/kioskTheme';

const reducedMotion = '@media (prefers-reduced-motion: reduce)';

function buildTheme(mode: 'light' | 'dark'): Theme {
  const palette = mode === 'light' ? lightPalette : darkPalette;

  return createTheme({
    palette,
    typography,
    breakpoints,
    shape: {
      borderRadius: radii.md,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          [reducedMotion]: {
            '*, *::before, *::after': {
              animationDuration: '0.01ms !important',
              animationIterationCount: '1 !important',
              transitionDuration: '0.01ms !important',
              scrollBehavior: 'auto !important',
            },
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        styleOverrides: {
          // Same rule as `MuiChip` below, same reason: a warning Button that
          // draws its own label — outlined or text — paints it in
          // `warning.main`, which is 3.11:1 on white and 2.85:1 on the app's
          // `#f5f5f5` background. `warning.dark` (#a54c01) is MUI's own darkened
          // tone of the same brand orange and reaches 5.34:1 there.
          //
          // Written as two classes. The previous single-class form,
          // `&.MuiButton-outlinedWarning`, matched nothing in MUI 9 — the
          // library emits `MuiButton-outlined` and `MuiButton-colorWarning`
          // separately and no combined class — so the rule had been silently
          // inert and outlined warning Buttons were still measured at 2.85:1
          // while the comment above claimed they were fixed. The sibling
          // `MuiChip` override survived only because it was already written this
          // way. The `text` variant is covered too: it has the same defect and
          // two live call sites (the AccountSettings reset dialogs).
          //
          // Light mode only (#1337 review): in dark mode `warning.main` already
          // reads at 8.6:1 on paper, and `warning.dark` (rgb 178,116,26) would
          // take it down to 4.3 — the override would create the defect it
          // exists to remove.
          root: ({ theme }) => ({
            textTransform: 'none',
            fontWeight: 600,
            ...(theme.palette.mode === 'light'
              ? {
                  '&.MuiButton-outlined.MuiButton-colorWarning': {
                    color: theme.palette.warning.dark,
                    borderColor: theme.palette.warning.dark,
                  },
                  '&.MuiButton-text.MuiButton-colorWarning': {
                    color: theme.palette.warning.dark,
                  },
                }
              : {}),
            // A *contained* warning Button keeps `contrastText` as its label on
            // hover but swaps the background to `warning.dark` — so flipping
            // `warning.contrastText` to black (#1289) would have taken this
            // surface from 5.82:1 (white on #a54b01, passing) down to 3.60:1:
            // the palette fix would have broken a state that was fine before.
            // Measured, not assumed. Darkening by 12% instead of going all the
            // way to `warning.dark` still reads as a hover and keeps black at
            // 5.35:1. Derived from the token rather than a second hard-coded
            // hex, so it cannot drift away from `warning.main`.
            //
            // Two classes, not the combined `MuiButton-containedWarning`: MUI 9
            // emits `MuiButton-contained` and `MuiButton-colorWarning` as
            // separate classes and no combined one, so a selector written the
            // combined way matches nothing and the rule is silently inert. That
            // is not hypothetical — see the `outlinedWarning` selector above.
            '&.MuiButton-contained.MuiButton-colorWarning:hover': {
              backgroundColor: darken(theme.palette.warning.main, 0.12),
            },
          }),
        },
      },
      // A *filled* warning Alert never reads `warning.contrastText`: MUI derives
      // its label from `palette.getContrastText(warning.main)`, which re-runs
      // the `contrastThreshold` (3) decision and picks white again — 3.11:1. The
      // #1289 palette change alone therefore leaves this surface failing, and
      // that issue's acceptance criterion ("a filled warning chip *and* a
      // warning Alert both reach >= 4.5:1") would have been reported as met with
      // the Alert half untouched. Pointed at `contrastText` so the Alert follows
      // the same single decision as every other filled warning surface.
      //
      // In dark mode the same applies to EVERY role, for a different reason:
      // MUI paints a dark filled Alert on `.dark` and derives the label with
      // `getContrastText(dark)`, which picks white for `info`, `primary` and
      // `secondary` (3.9-4.3:1) and a translucent black for the rest that
      // composites below 4.5 on the derived `.dark` (#1337 review, measured
      // with alpha composited). Each dark role declares a `contrastText` that
      // clears its `.dark`, so the filled Alert reads that single decision too.
      MuiAlert: {
        styleOverrides: {
          root: ({ theme }) => ({
            '&.MuiAlert-filled.MuiAlert-colorWarning': {
              color: theme.palette.warning.contrastText,
            },
            ...(theme.palette.mode === 'dark'
              ? Object.fromEntries(
                  (['error', 'info', 'success', 'primary', 'secondary'] as const).map((role) => [
                    `&.MuiAlert-filled.MuiAlert-color${role[0].toUpperCase()}${role.slice(1)}`,
                    { color: theme.palette[role].contrastText },
                  ]),
                )
              : {}),
          }),
        },
      },
      MuiCard: {
        defaultProps: {
          variant: 'outlined',
        },
      },
      // `warning.main` (#ed6c02) reaches only 3.11:1 on white, so wherever it is
      // used as *text* it misses WCAG AA's 4.5:1 (UI-NFR-002). The outlined Chip
      // is the construct that does exactly that — its label and border are drawn
      // in the palette colour — and its label is the one axe reports.
      //
      // Fixed here rather than per call site: three outlined warning chips exist
      // (dashboard plant grid, pest gallery, AI response) and patching only the
      // one the nightly happened to scan is how the sibling call sites drift
      // apart. `warning.dark` is MUI's own darkened tone of the same brand
      // orange (#a54c01, 5.78:1), so the brand colour itself is untouched and
      // still fills icons, alerts and filled chips.
      //
      // Class-based rather than an `ownerState` callback: the classes are the
      // stable part of MUI's Chip API across versions, and this override has to
      // survive the next minor bump without silently becoming a no-op.
      MuiChip: {
        styleOverrides: {
          // Light mode only — same reason as the Button override above.
          root: ({ theme }) => ({
            ...(theme.palette.mode === 'light'
              ? {
                  '&.MuiChip-outlined.MuiChip-colorWarning': {
                    color: theme.palette.warning.dark,
                    borderColor: theme.palette.warning.dark,
                  },
                }
              : {}),
          }),
        },
      },
      MuiTextField: {
        defaultProps: {
          size: 'small',
          variant: 'outlined',
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 600,
          },
        },
      },
    },
  });
}

/**
 * UI-NFR-019 §2.7 — high-contrast theme. Pure black/white surfaces (R-041),
 * medium+ font weight (R-042), no elevation/gradients/hover tints (R-043).
 * Built on the light base so shared component conventions are preserved.
 */
function buildHighContrastTheme(): Theme {
  return createTheme(buildTheme('light'), {
    palette: highContrastPalette,
    typography: {
      // R-042 — minimum Medium weight throughout.
      fontWeightRegular: 500,
      body1: { fontWeight: 500 },
      body2: { fontWeight: 500 },
    },
    components: {
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: { backgroundImage: 'none', boxShadow: 'none' },
        },
      },
      MuiCard: {
        defaultProps: { variant: 'outlined' },
        styleOverrides: {
          root: { borderColor: '#000000', borderWidth: 2, boxShadow: 'none' },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { boxShadow: 'none' },
          outlined: { borderWidth: 2, borderColor: '#000000' },
        },
      },
      MuiAppBar: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: { boxShadow: 'none', borderBottom: '2px solid #000000' },
        },
      },
    },
  });
}

export const lightTheme = buildTheme('light');
export const darkTheme = buildTheme('dark');
export const highContrastTheme = buildHighContrastTheme();

/** Kiosk theme = high-contrast base + touch-target overrides (UI-NFR-019). */
export const kioskHighContrastTheme = createTheme(highContrastTheme, kioskThemeOverrides);
export const kioskLightTheme = createTheme(lightTheme, kioskThemeOverrides);
export const kioskDarkTheme = createTheme(darkTheme, kioskThemeOverrides);

/**
 * Resolve the effective application theme from the current mode and kiosk flags
 * (UI-NFR-019). The switch is pure so {@link ThemeContext} can flip themes
 * without a page reload (R-004).
 */
export function selectAppTheme(
  mode: 'light' | 'dark',
  isKiosk: boolean,
  highContrast: boolean,
): Theme {
  if (isKiosk) {
    if (highContrast) return kioskHighContrastTheme;
    return mode === 'dark' ? kioskDarkTheme : kioskLightTheme;
  }
  if (highContrast) return highContrastTheme;
  return mode === 'dark' ? darkTheme : lightTheme;
}
