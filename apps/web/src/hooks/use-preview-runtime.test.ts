import { buildBridgeScript, injectBridgeScript } from './use-preview-runtime';

describe('use-preview-runtime bridge helpers', () => {
  it('builds bridge script with secure channel and handshake events', () => {
    const script = buildBridgeScript('channel-123');

    expect(script).toContain('channel-123');
    expect(script).toContain('__sovrnPreviewBridge');
    expect(script).toContain('sovrn.preview.ready');
    expect(script).toContain('sovrn.preview.ping');
    expect(script).toContain('sovrn.preview.pong');
    expect(script).toContain('sovrn.preview.reload');
    expect(script).toContain('sovrn.preview.node.select');
  });

  it('injects bridge script before closing body tag when present', () => {
    const html = '<html><body><main>Hello</main></body></html>';
    const injected = injectBridgeScript(html, 'channel-abc');

    expect(injected).toContain('<main>Hello</main>');
    expect(injected).toContain('channel-abc');
    expect(injected.indexOf('sovrn.preview.ready')).toBeGreaterThan(-1);
    expect(injected.indexOf('sovrn.preview.ready')).toBeLessThan(injected.indexOf('</body>'));
  });

  it('wraps html fragment and injects bridge script when no document tags exist', () => {
    const injected = injectBridgeScript('<div>Fragment</div>', 'channel-fragment');

    expect(injected.toLowerCase()).toContain('<!doctype html>');
    expect(injected).toContain('<div>Fragment</div>');
    expect(injected).toContain('channel-fragment');
    expect(injected).toContain('sovrn.preview.reload');
  });
});
