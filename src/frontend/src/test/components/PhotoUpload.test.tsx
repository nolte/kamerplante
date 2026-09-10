import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { renderWithProviders } from '@/test/helpers';
import PhotoUpload from '@/components/common/PhotoUpload';

/**
 * PhotoUpload — the task-completion photo control (REQ-006).
 *
 * Until #1339 this posted to `POST /tasks/{key}/photos`, which no backend route
 * served: every upload answered 404, and a task with `requires_photo` could
 * therefore never be completed. The route exists now, on the NFR-013 attachment
 * fundament, so two things are asserted here that a `{ url }`-shaped static file
 * did not need:
 *
 * - the component carries the returned **`uri`** into `photo_refs` (the old
 *   shape's `url` is gone, and reading it would push `undefined`);
 * - the preview renders through `AuthImage`, because the attachment URI is
 *   permission-gated and a native `<img src>` cannot send the Bearer header.
 */

const TENANT = 'test-tenant';
const ATTACHMENT_URI = `/api/v1/t/${TENANT}/attachments/att-1`;

function attachment() {
  return {
    attachment_id: 'att-1',
    uri: ATTACHMENT_URI,
    thumbnail_uris: null,
    mime_type: 'image/jpeg',
    byte_size: 3,
    original_filename: 'p.jpg',
  };
}

function blobResponse() {
  return HttpResponse.arrayBuffer(new Uint8Array([1, 2, 3]).buffer, {
    headers: { 'Content-Type': 'image/jpeg' },
  });
}

describe('PhotoUpload (REQ-006 — task photo upload)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uploads to the task photo route and reports the attachment uri', async () => {
    const user = userEvent.setup();
    let requestedUrl: string | null = null;
    server.use(
      http.post(`/api/v1/t/:tenant/tasks/:key/photos`, ({ request }) => {
        requestedUrl = new URL(request.url).pathname;
        return HttpResponse.json(attachment());
      }),
    );
    const onChange = vi.fn();

    renderWithProviders(<PhotoUpload taskKey="tk1" photoRefs={[]} onChange={onChange} />);

    const input = screen.getByTestId('photo-upload').querySelector('input[type="file"]')!;
    await user.upload(input as HTMLInputElement, new File(['x'], 'p.jpg', { type: 'image/jpeg' }));

    await waitFor(() => expect(onChange).toHaveBeenCalled());
    // The uri, not `undefined` — the response no longer carries a `url` field.
    expect(onChange).toHaveBeenCalledWith([ATTACHMENT_URI]);
    expect(requestedUrl).toBe(`/api/v1/t/${TENANT}/tasks/tk1/photos`);
  });

  it('renders an existing photo through the authenticated image path', async () => {
    let fetched: string | null = null;
    server.use(
      http.get(ATTACHMENT_URI, ({ request }) => {
        fetched = new URL(request.url).pathname;
        return blobResponse();
      }),
    );

    renderWithProviders(
      <PhotoUpload taskKey="tk1" photoRefs={[ATTACHMENT_URI]} onChange={vi.fn()} />,
    );

    const img = (await screen.findByTestId('photo-preview-0')) as HTMLImageElement;
    // A blob Object-URL, never the permission-gated URI in `src`.
    expect(img.src).toMatch(/^blob:/);
    expect(img.src).not.toContain('/attachments/');
    await waitFor(() => expect(fetched).toBe(ATTACHMENT_URI));
  });

  it('keeps the dialog usable and reports nothing when the upload fails', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`/api/v1/t/:tenant/tasks/:key/photos`, () =>
        HttpResponse.json(
          {
            error_id: 'e',
            error_code: 'INTERNAL_ERROR',
            message: 'boom',
            details: [],
            timestamp: '',
            path: '',
            method: '',
          },
          { status: 500 },
        ),
      ),
    );
    const onChange = vi.fn();

    renderWithProviders(<PhotoUpload taskKey="tk1" photoRefs={[]} onChange={onChange} />);

    const input = screen.getByTestId('photo-upload').querySelector('input[type="file"]')!;
    await user.upload(input as HTMLInputElement, new File(['x'], 'p.jpg', { type: 'image/jpeg' }));

    // A failed upload must not push a ref the server never accepted.
    await waitFor(() => expect(screen.getByTestId('photo-upload')).toBeInTheDocument());
    expect(onChange).not.toHaveBeenCalled();
  });

  it('removes a staged photo locally', async () => {
    const user = userEvent.setup();
    server.use(http.get(ATTACHMENT_URI, () => blobResponse()));
    const onChange = vi.fn();

    renderWithProviders(
      <PhotoUpload taskKey="tk1" photoRefs={[ATTACHMENT_URI]} onChange={onChange} />,
    );

    await user.click(await screen.findByTestId('photo-remove-0'));

    expect(onChange).toHaveBeenCalledWith([]);
  });
});
