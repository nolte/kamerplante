import { describe, it, expect } from 'vitest';
import { getContrastRatio } from '@mui/material/styles';
import { lightTheme, darkTheme, highContrastTheme } from '@/theme/theme';

/**
 * UI-NFR-002 — WCAG 2.2 AA demands 4.5:1 between normal text and the surface
 * behind it. The palette decides that for every filled/outlined role surface at
 * once, so it is checkable here rather than only in a browser (#1289, #1323).
 *
 * These assertions read the *resolved theme*, not the palette literals, so they
 * follow MUI's own derivations (`contrastText`, `light`, `dark`) instead of
 * restating them. A test that re-derived the values by hand would agree with
 * itself while the app painted something else.
 *
 * Why axe alone is not enough for this: measured against a real headless Chrome,
 * axe-core reports MUI Buttons as *incomplete*, not as violations — the
 * TouchRipple span overlaps the label, so axe refuses to determine the
 * background ("Element's background color could not be determined because it is
 * overlapped by another element"). Every contained/outlined/text Button in the
 * app is therefore invisible to the contrast rule of the nightly scan. This file
 * is the guard that does see them.
 */

const AA_NORMAL_TEXT = 4.5;

/**
 * Composite a possibly translucent foreground over an opaque surface, the way
 * the browser paints it. MUI's `getContrastRatio` ignores alpha: it reads
 * `rgba(0,0,0,0.87)` as pure black and reported the dark `error` hover at 4.72
 * where the browser paints 4.29. Measuring the painted colour is the only
 * reading that cannot certify a derivation the app never shows.
 */
function channels(color: string): [number, number, number, number] {
  const hex = color.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const digits = hex[1].length === 3 ? [...hex[1]].map((d) => d + d).join('') : hex[1];
    const n = parseInt(digits, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1];
  }
  const fn = color.match(/^rgba?\(([^)]+)\)$/);
  if (!fn) throw new Error(`unsupported colour ${color}`);
  const [r, g, b, a = '1'] = fn[1].split(',').map((part) => part.trim());
  return [Number(r), Number(g), Number(b), Number(a)];
}

function painted(foreground: string, surface: string): string {
  const [fr, fg, fb, fa] = channels(foreground);
  const [sr, sg, sb, sa] = channels(surface);
  if (sa !== 1) throw new Error(`surface ${surface} is not opaque`);
  const mix = (f: number, s: number) => Math.round(f * fa + s * (1 - fa));
  return `rgb(${mix(fr, sr)}, ${mix(fg, sg)}, ${mix(fb, sb)})`;
}

function ratio(foreground: string, surface: string): number {
  return getContrastRatio(painted(foreground, surface), surface);
}

/** A `styleOverrides.root` entry, resolved the way MUI resolves it for `theme`. */
function resolveOverride(override: unknown, theme: typeof darkTheme): Record<string, unknown> {
  return typeof override === 'function'
    ? (override as (props: { theme: typeof darkTheme }) => Record<string, unknown>)({ theme })
    : ((override ?? {}) as Record<string, unknown>);
}

describe('light palette role contrast (UI-NFR-002)', () => {
  const { palette } = lightTheme;

  describe.each([
    ['info', palette.info],
    ['warning', palette.warning],
    ['error', palette.error],
    ['success', palette.success],
    ['primary', palette.primary],
    ['secondary', palette.secondary],
  ] as const)('%s', (role, color) => {
    it('carries text on its filled surface that clears 4.5:1', () => {
      // Filled Chip / contained Button: label is `contrastText` on `main`.
      expect(getContrastRatio(color.contrastText, color.main)).toBeGreaterThanOrEqual(
        AA_NORMAL_TEXT,
      );
    });

    it('keeps the contained-button hover surface legible', () => {
      // MUI swaps a contained Button's surface to `.dark` on hover while
      // keeping `contrastText` as the label. #1289 found that this state can
      // fail while the resting one passes, so it is asserted separately.
      const hoverSurface =
        role === 'warning'
          ? // warning overrides its own hover surface in `theme.ts`; see the
            // comment there. Asserted at its declared value so this test cannot
            // pass by accident if that override is removed.
            '#d15f02'
          : color.dark;
      expect(getContrastRatio(color.contrastText, hoverSurface)).toBeGreaterThanOrEqual(
        AA_NORMAL_TEXT,
      );
    });
  });

  it('draws a filled info Alert legibly without a MuiAlert override', () => {
    // A filled Alert does NOT read `contrastText`; it derives its label from
    // `getContrastText(main)`, which re-runs the `contrastThreshold` decision.
    // That is precisely why warning needed its own `MuiAlert` override (#1289).
    // Info must clear the bar down this second, independent path too.
    const alertLabel = palette.getContrastText(palette.info.main);
    expect(getContrastRatio(alertLabel, palette.info.main)).toBeGreaterThanOrEqual(
      AA_NORMAL_TEXT,
    );
  });

  it('is legible as a label on the page background in the outlined/text variants', () => {
    // The other failure direction: an outlined or `text` info Chip/Button paints
    // its own label in `info.main` on `background.default`. `#0288d1` was
    // 3.53:1 there. Because `info.main` itself now clears the bar, info needs
    // none of the `.dark` overrides `warning` carries — and this assertion is
    // what keeps that true.
    expect(
      getContrastRatio(palette.info.main, palette.background.default),
    ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });

  it('keeps warning legible as a label only via warning.dark', () => {
    // Documents the asymmetry between the two roles: warning's brand token is
    // pinned and still fails as a label, so its overrides must stay.
    expect(getContrastRatio(palette.warning.main, palette.background.default)).toBeLessThan(
      AA_NORMAL_TEXT,
    );
    expect(
      getContrastRatio(palette.warning.dark, palette.background.default),
    ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });
});

describe('dark palette role contrast (UI-NFR-002, #1337)', () => {
  const { palette } = darkTheme;

  /**
   * The dark theme is swept across every role rather than only the one that was
   * reported, and every reading composites alpha first (see `painted`): the
   * first pass of #1337 certified `error` and `success` hover surfaces at 4.72
   * and 4.56 that the browser paints at 4.29 and 4.15, because MUI's derived
   * `contrastText` is `rgba(0,0,0,0.87)` and `getContrastRatio` reads it as
   * black. The roles now declare pure black and, where the derived `.dark` was
   * too close, an explicit `dark` (see `palette.ts`).
   *
   * Four surfaces, because a dark role can fail any of them independently and
   * each candidate repair for `error` failed a different one.
   */
  describe.each([
    ['info', palette.info],
    ['warning', palette.warning],
    ['error', palette.error],
    ['success', palette.success],
    ['primary', palette.primary],
    ['secondary', palette.secondary],
  ] as const)('%s', (_role, color) => {
    it('carries legible text on its filled surface', () => {
      expect(ratio(color.contrastText, color.main)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    });

    it('keeps the contained-button hover surface legible', () => {
      // MUI swaps to `.dark` on hover and keeps `contrastText`. This is the
      // direction that refuted `#ef5350` with black text (3.31:1) — and, once
      // alpha is composited, the derived `contrastText` on the derived `.dark`.
      expect(ratio(color.contrastText, color.dark)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    });

    it('draws a filled Alert legibly on the surface dark mode actually uses', () => {
      // In dark mode MUI paints a filled Alert on `.dark`, not on `main`, and
      // would derive the label with `getContrastText(dark)` — white for info /
      // primary / secondary at 3.9-4.3, translucent black below 4.5 elsewhere.
      // `theme.ts` points every dark filled Alert at the role's `contrastText`
      // instead; both halves are asserted, the override's presence and what it
      // paints. The first pass asserted `main`, a surface the dark Alert never
      // shows.
      const selector = `&.MuiAlert-filled.MuiAlert-color${_role[0].toUpperCase()}${_role.slice(1)}`;
      const alertRoot = resolveOverride(darkTheme.components?.MuiAlert?.styleOverrides?.root, darkTheme);
      expect(Object.keys(alertRoot)).toContain(selector);
      expect((alertRoot[selector] as { color: string }).color).toBe(color.contrastText);
      expect(ratio(color.contrastText, color.dark)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    });

    it.each([
      ['page', palette.background.default],
      ['paper', palette.background.paper],
    ])('is legible as a label on the dark %s background', (_surface, background) => {
      // Outlined/`text` variants paint their own label in `main`. Both surfaces,
      // because `theme.ts` once repainted warning labels in `warning.dark`
      // regardless of mode, which on dark paper measured 4.29 while `main` on
      // the page background looked fine.
      expect(ratio(color.main, background)).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    });
  });

  it('does not repaint warning labels in warning.dark in dark mode', () => {
    // The outlined/text overrides in `theme.ts` exist for the light theme, where
    // `warning.main` is too light on white. In dark mode they would take a
    // label that reads at 8.6:1 down to 4.3 — so they are gated on the mode,
    // and this asserts the gate rather than the colour it happens to produce.
    const dark = (component: 'MuiButton' | 'MuiChip') =>
      resolveOverride(darkTheme.components?.[component]?.styleOverrides?.root, darkTheme);
    // `Object.keys`, not `toHaveProperty`: the selector contains dots, which
    // `toHaveProperty` would read as a path.
    expect(Object.keys(dark('MuiButton'))).not.toContain(
      '&.MuiButton-outlined.MuiButton-colorWarning',
    );
    expect(Object.keys(dark('MuiChip'))).not.toContain('&.MuiChip-outlined.MuiChip-colorWarning');
    // Positive control: the same override is present where it belongs.
    expect(
      Object.keys(resolveOverride(lightTheme.components?.MuiChip?.styleOverrides?.root, lightTheme)),
    ).toContain('&.MuiChip-outlined.MuiChip-colorWarning');
  });
});

describe('info contrast in the high-contrast theme', () => {
  it('clears 4.5:1 on filled surfaces', () => {
    const { info } = highContrastTheme.palette;
    expect(getContrastRatio(info.contrastText, info.main)).toBeGreaterThanOrEqual(
      AA_NORMAL_TEXT,
    );
  });
});
