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
   * reported. `error` at `#ef5350` was the sole failure — `warning`, `success`,
   * `primary` and `secondary` sit far enough from white that MUI picks black and
   * they clear the bar by 8.9-10.8. That is a measurement, and this sweep is what
   * keeps it one instead of an assumption.
   *
   * Three directions, because a dark role can fail any of them independently and
   * each candidate repair for `error` failed a different one (see `palette.ts`).
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
      expect(getContrastRatio(color.contrastText, color.main)).toBeGreaterThanOrEqual(
        AA_NORMAL_TEXT,
      );
    });

    it('keeps the contained-button hover surface legible', () => {
      // MUI swaps to `.dark` on hover and keeps `contrastText`. This is the
      // direction that refuted `error: { contrastText: '#000000' }` — the repair
      // #1337 proposed — at 3.31:1, while its resting state passed at 6.02.
      expect(getContrastRatio(color.contrastText, color.dark)).toBeGreaterThanOrEqual(
        AA_NORMAL_TEXT,
      );
    });

    it('is legible as a label on the dark page background', () => {
      // Outlined/`text` variants paint their own label in `main` on
      // `background.default`. This is the direction that refuted darkening
      // `error.main` to `#c62828`, at 3.34:1.
      expect(
        getContrastRatio(color.main, palette.background.default),
      ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    });
  });

  it('draws a filled error Alert legibly without a MuiAlert override', () => {
    // Same second path as light `info`: a filled Alert derives its label from
    // `getContrastText(main)` rather than reading `contrastText`, so a fix to
    // `contrastText` alone would leave the Alert failing (measured in #1289).
    const alertLabel = palette.getContrastText(palette.error.main);
    expect(getContrastRatio(alertLabel, palette.error.main)).toBeGreaterThanOrEqual(
      AA_NORMAL_TEXT,
    );
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
