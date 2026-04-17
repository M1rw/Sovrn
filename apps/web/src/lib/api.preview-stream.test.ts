import { buildPreviewEventsStreamPath, projectsApi } from './api';

const originalFetch = global.fetch;

function installFetchResponse(payload: unknown): jest.Mock {
  const mockFetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => payload,
  });

  global.fetch = mockFetch as unknown as typeof fetch;
  jest.spyOn(console, 'debug').mockImplementation(() => undefined);
  return mockFetch;
}

afterEach(() => {
  jest.restoreAllMocks();
  if (originalFetch) {
    global.fetch = originalFetch;
  } else {
    delete (globalThis as Partial<typeof globalThis>).fetch;
  }
});

describe('buildPreviewEventsStreamPath', () => {
  it('builds path with all query parameters', () => {
    const path = buildPreviewEventsStreamPath('project-123', {
      generation_id: 'gen-456',
      entrypoint: 'index.html',
      preview_token: 'preview-token-abc',
      poll_interval_ms: 1500,
    });

    expect(path).toContain('/api/v1/projects/project-123/preview-events?');
    expect(path).toContain('generation_id=gen-456');
    expect(path).toContain('entrypoint=index.html');
    expect(path).toContain('preview_token=preview-token-abc');
    expect(path).toContain('poll_interval_ms=1500');
  });

  it('builds path without query when no options are set', () => {
    const path = buildPreviewEventsStreamPath('project-123', {});
    expect(path).toBe('/api/v1/projects/project-123/preview-events');
  });
});

describe('preview bootstrap API contracts', () => {
  it('createPreviewSession posts bootstrap request payload with auth', async () => {
    const mockFetch = installFetchResponse({
      token: 'preview-session-token',
      token_type: 'preview_session',
      expires_at: '2026-04-17T10:00:00Z',
      project_id: 'project-123',
      generation_id: 'gen-456',
      entrypoint: 'index.html',
      artifact_endpoint: '/api/v1/projects/project-123/preview-artifact?generation_id=gen-456&entrypoint=index.html',
    });

    await projectsApi.createPreviewSession('access-token-xyz', 'project-123', {
      generation_id: 'gen-456',
      entrypoint: 'index.html',
      ttl_seconds: 120,
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://127.0.0.1:8000/api/v1/projects/project-123/preview-session');
    expect(options.method).toBe('POST');

    const headers = options.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer access-token-xyz');

    expect(JSON.parse(String(options.body))).toEqual({
      generation_id: 'gen-456',
      entrypoint: 'index.html',
      ttl_seconds: 120,
    });
  });

  it('verifyPreviewSession posts verify payload without auth token when omitted', async () => {
    const mockFetch = installFetchResponse({
      valid: true,
      token_type: 'preview_session',
      project_id: 'project-123',
      generation_id: 'gen-456',
      entrypoint: 'index.html',
      expires_at: '2026-04-17T10:00:00Z',
      artifact_endpoint: '/api/v1/projects/project-123/preview-artifact?generation_id=gen-456&entrypoint=index.html',
    });

    await projectsApi.verifyPreviewSession('project-123', {
      token: 'preview-session-token',
      generation_id: 'gen-456',
      entrypoint: 'index.html',
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://127.0.0.1:8000/api/v1/projects/project-123/preview-session/verify');
    expect(options.method).toBe('POST');

    const headers = options.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();

    expect(JSON.parse(String(options.body))).toEqual({
      token: 'preview-session-token',
      generation_id: 'gen-456',
      entrypoint: 'index.html',
    });
  });

  it('previewArtifactFromEndpoint uses artifact endpoint path directly', async () => {
    const mockFetch = installFetchResponse({
      project_id: 'project-123',
      generation_id: 'gen-456',
      generation_version: 3,
      entrypoint: 'index.html',
      preview_html: '<html><body>ok</body></html>',
      files: [],
      source: 'site_generation',
    });

    const endpoint = '/api/v1/projects/project-123/preview-artifact?generation_id=gen-456&entrypoint=index.html';
    await projectsApi.previewArtifactFromEndpoint('access-token-xyz', endpoint);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`http://127.0.0.1:8000${endpoint}`);

    const headers = options.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer access-token-xyz');
  });
});
