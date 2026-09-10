import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import i18n from 'i18next';
import LoadingStatus from '@/components/common/LoadingStatus';

/**
 * #1324 — the announcement half of every loading placeholder. Each assertion
 * here guards one of the three properties that were measured in Chrome's
 * accessibility tree and that a well-meaning simplification would remove.
 */
describe('LoadingStatus', () => {
  it('announces with the translated wording by default', () => {
    render(<LoadingStatus />);
    const status = screen.getByRole('status');
    expect(i18n.t('common.loading')).not.toBe('common.loading');
    expect(status).toHaveAccessibleName(i18n.t('common.loading'));
    expect(status).toHaveTextContent(i18n.t('common.loading'));
  });

  it('lets a region override the generic wording', () => {
    render(<LoadingStatus label="Lade Bilder" />);
    expect(screen.getByRole('status')).toHaveAccessibleName('Lade Bilder');
    expect(screen.getByRole('status')).toHaveTextContent('Lade Bilder');
  });

  it('carries both a name and content, because they do different work', () => {
    // `status` takes its name from the author only, never from content, so
    // dropping `aria-label` leaves the region nameless; a live region announces
    // its content, not its name, so dropping the text leaves it silent.
    render(<LoadingStatus label="Lade" />);
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-label', 'Lade');
    expect(status.textContent).toBe('Lade');
  });

  it('is a polite live region and is not itself marked busy', () => {
    render(<LoadingStatus />);
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).not.toHaveAttribute('aria-busy');
  });

  it('is visually hidden but not hidden from assistive technology', () => {
    render(<LoadingStatus />);
    const status = screen.getByRole('status');
    expect(status).not.toHaveAttribute('aria-hidden');
    // `visuallyHidden` clips the element rather than using display:none, which
    // would take it out of the accessibility tree along with the announcement.
    expect(getComputedStyle(status).position).toBe('absolute');
  });

  it('accepts a test id for callers that need to address it', () => {
    render(<LoadingStatus data-testid="widget-loading-status" />);
    expect(screen.getByTestId('widget-loading-status')).toHaveAttribute('role', 'status');
  });

  /**
   * #1337 — the stay-mounted mode. A caller that loads repeatedly (the dashboard
   * refetches its aggregate on every layout change) cannot unmount the region
   * between loads: a live region has to exist *before* its content changes for
   * the change to be announced.
   */
  describe('active={false}', () => {
    it('stays mounted as a live region', () => {
      render(<LoadingStatus active={false} data-testid="dashboard-loading-status" />);
      const status = screen.getByTestId('dashboard-loading-status');
      expect(status).toHaveAttribute('role', 'status');
      expect(status).toHaveAttribute('aria-live', 'polite');
      expect(status).not.toHaveAttribute('aria-hidden');
    });

    it('says nothing and is unnamed', () => {
      // Empty *and* unnamed: content is what a live region announces, and a name
      // left behind would describe a finished load to anyone navigating onto it.
      render(<LoadingStatus active={false} label="Lade" data-testid="s" />);
      const status = screen.getByTestId('s');
      expect(status.textContent).toBe('');
      expect(status).not.toHaveAttribute('aria-label');
      expect(status).toHaveAccessibleName('');
    });

    it('speaks again when it is re-activated, on the same node', () => {
      const { rerender } = render(<LoadingStatus active={false} label="Lade" data-testid="s" />);
      const before = screen.getByTestId('s');

      rerender(<LoadingStatus active label="Lade" data-testid="s" />);

      const after = screen.getByTestId('s');
      // The *same* element, not a replacement: an empty → text transition on an
      // existing region is what gets announced; a freshly inserted region with
      // its text already in place is not reliably announced at all.
      expect(after).toBe(before);
      expect(after).toHaveTextContent('Lade');
      expect(after).toHaveAccessibleName('Lade');
    });

    it('defaults to active, so existing call sites are unchanged', () => {
      render(<LoadingStatus label="Lade" data-testid="s" />);
      expect(screen.getByTestId('s')).toHaveTextContent('Lade');
    });
  });
});
