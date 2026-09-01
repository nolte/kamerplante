import { screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import i18n from 'i18next';
import SpeciesThumbnail from '@/pages/stammdaten/SpeciesThumbnail';
import { renderWithProviders } from '../helpers';

describe('SpeciesThumbnail', () => {
  beforeEach(() => {
    i18n.changeLanguage('de');
  });

  it('renders the external image when a URL is provided', () => {
    renderWithProviders(
      <SpeciesThumbnail
        imageUrl="https://example.org/leaf.jpg"
        attribution="Jane Doe"
        license="CC-BY"
        alt="Monstera deliciosa"
      />,
    );
    const img = screen.getByRole('img', { name: 'Monstera deliciosa' }) as HTMLImageElement;
    expect(img.getAttribute('src')).toBe('https://example.org/leaf.jpg');
    expect(img.getAttribute('referrerpolicy')).toBe('no-referrer');
    expect(img.getAttribute('loading')).toBe('lazy');
  });

  it('shows the icon fallback when no URL is provided', () => {
    renderWithProviders(<SpeciesThumbnail imageUrl={null} alt="Ocimum basilicum" />);
    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByTestId('species-thumbnail')).toBeTruthy();
  });

  it('leaves the icon fallback unnamed rather than naming a role-less element', () => {
    // #1337 — the fallback carried `aria-label={alt}` on a source-less MUI
    // Avatar, which renders a `<div>`: ARIA forbids naming a `generic` element,
    // so axe reported `aria-prohibited-attr` (serious) and the name was dropped
    // anyway. 25 such nodes stood on `/stammdaten/species`.
    //
    // Asserted as the *absence of the attribute*, not as "no accessible name":
    // the browser dropping the name is what made this invisible in the first
    // place, so a name-based assertion would have passed against the defect.
    renderWithProviders(<SpeciesThumbnail imageUrl={null} alt="Ocimum basilicum" />);

    expect(screen.getByTestId('species-thumbnail').hasAttribute('aria-label')).toBe(false);
  });

  it('still names the image itself when there is one', () => {
    // The other half of the decision: `alt` remains a real accessible name on
    // the `<img>`, where naming is valid. Dropping it there too would have been
    // a wider change than the defect, and a caller may need it.
    renderWithProviders(
      <SpeciesThumbnail imageUrl="https://example.org/leaf.jpg" alt="Monstera deliciosa" />,
    );

    expect(screen.getByRole('img', { name: 'Monstera deliciosa' })).toBeTruthy();
  });

  it('falls back to the icon when the external image fails to load', () => {
    renderWithProviders(
      <SpeciesThumbnail imageUrl="https://example.org/broken.jpg" alt="Broken" />,
    );
    const img = screen.getByRole('img', { name: 'Broken' });
    fireEvent.error(img);
    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByTestId('species-thumbnail')).toBeTruthy();
  });
});
