import {
  getPreviewStreamFallbackMessage,
  getPreviewStreamStateOnError,
  PreviewStreamState,
  shouldMarkPreviewStreamStale,
  toMountDescriptorFromArtifact,
  toMountDescriptorFromPreviewUpdate,
} from './preview-lifecycle';

describe('preview lifecycle helpers', () => {
  it('builds bootstrap mount descriptor from preview artifact payload', () => {
    const descriptor = toMountDescriptorFromArtifact(
      {
        project_id: 'project-1',
        generation_id: 'generation-1',
        generation_version: 3,
        entrypoint: 'index.html',
        preview_html: '<html><body>artifact preview</body></html>',
        source: 'site_generation',
        files: [
          {
            path: 'index.html',
            content: '<html><body>artifact preview</body></html>',
            language: 'html',
            size_bytes: 41,
          },
          {
            path: 'assets/main.js',
            content: 'console.log("ok")',
            language: 'javascript',
            size_bytes: 17,
          },
        ],
      },
      'index.html',
      '<html><body>fallback</body></html>'
    );

    expect(descriptor.entrypoint).toBe('index.html');
    expect(descriptor.nextGeneratedHtml).toBe('<html><body>artifact preview</body></html>');
    expect(descriptor.fallbackHtml).toBe('<html><body>artifact preview</body></html>');
    expect(descriptor.generatedFiles).toHaveLength(2);
    expect(descriptor.generatedFiles[0].name).toBe('index.html');
    expect(descriptor.generatedFiles[1].type).toBe('javascript');
    expect(descriptor.mountFiles[1]).toEqual({
      path: 'assets/main.js',
      content: 'console.log("ok")',
      language: 'javascript',
    });
  });

  it('normalizes preview.updated payload into mount descriptor and generated files', () => {
    const descriptor = toMountDescriptorFromPreviewUpdate({
      entrypoint: 'preview/custom.html',
      preview_html: '<html><body>stream preview</body></html>',
      files: [
        {
          path: 'preview/custom.html',
          content: '<html><body>stream preview</body></html>',
          language: 'html',
          size_bytes: 39,
        },
        {
          path: '',
          content: 'const x = 1;',
        },
      ],
    });

    expect(descriptor.entrypoint).toBe('preview/custom.html');
    expect(descriptor.generatedFiles[0].name).toBe('preview/custom.html');
    expect(descriptor.generatedFiles[1].name).toBe('stream-file-1.txt');
    expect(descriptor.generatedFiles[1].type).toBe('txt');
    expect(descriptor.nextGeneratedHtml).toBe('<html><body>stream preview</body></html>');
    expect(descriptor.mountFiles).toHaveLength(2);
  });

  it('falls back to generated html when artifact preview html is empty', () => {
    const descriptor = toMountDescriptorFromArtifact(
      {
        project_id: 'project-1',
        generation_id: 'generation-1',
        generation_version: 1,
        entrypoint: 'index.html',
        preview_html: '',
        source: 'site_generation',
        files: [
          {
            path: 'index.html',
            content: '<html><body>from file</body></html>',
            language: 'html',
            size_bytes: 34,
          },
        ],
      },
      'index.html',
      '<html><body>fallback html</body></html>'
    );

    expect(descriptor.nextGeneratedHtml).toBe('<html><body>fallback html</body></html>');
    expect(descriptor.fallbackHtml).toBe('<html><body>fallback html</body></html>');
  });

  it('supports stale and reconnect lifecycle transitions', () => {
    let streamState: PreviewStreamState = 'connecting';
    let lastEventAt: number | null = null;
    let reconnectNonce = 0;

    // Heartbeat transitions stream to live.
    streamState = 'live';
    lastEventAt = 1_000;
    expect(getPreviewStreamFallbackMessage(streamState)).toBeNull();

    // A tick before threshold should not mark stale.
    expect(shouldMarkPreviewStreamStale(lastEventAt, 6_900, 6_000)).toBe(false);
    // A tick at/after threshold should mark stale.
    expect(shouldMarkPreviewStreamStale(lastEventAt, 7_000, 6_000)).toBe(true);

    streamState = 'stale';
    expect(getPreviewStreamFallbackMessage(streamState)).toContain('stale');

    // Reconnect resets live signal and nonce.
    reconnectNonce += 1;
    streamState = 'connecting';
    lastEventAt = null;
    expect(reconnectNonce).toBe(1);
    expect(lastEventAt).toBeNull();

    // Closed stream maps to disconnected state.
    streamState = getPreviewStreamStateOnError(2);
    expect(streamState).toBe('disconnected');
    expect(getPreviewStreamFallbackMessage(streamState)).toContain('disconnected');

    // Non-closed error maps to error state.
    expect(getPreviewStreamStateOnError(1)).toBe('error');
  });
});
