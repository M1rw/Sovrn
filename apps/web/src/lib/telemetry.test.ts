import { recordClientMetric } from './telemetry';

describe('recordClientMetric', () => {
  const originalWindow = globalThis.window;
  const originalNavigator = globalThis.navigator;
  const originalFetch = globalThis.fetch;
  const originalCustomEvent = globalThis.CustomEvent;

  beforeEach(() => {
    const dispatchEvent = jest.fn();
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: { dispatchEvent },
    });

    class CustomEventMock<T> {
      type: string;
      detail: T;
      constructor(type: string, init: { detail: T }) {
        this.type = type;
        this.detail = init.detail;
      }
    }

    Object.defineProperty(globalThis, 'CustomEvent', {
      configurable: true,
      value: CustomEventMock,
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();

    if (originalWindow) {
      Object.defineProperty(globalThis, 'window', {
        configurable: true,
        value: originalWindow,
      });
    } else {
      delete (globalThis as Partial<typeof globalThis>).window;
    }

    if (originalNavigator) {
      Object.defineProperty(globalThis, 'navigator', {
        configurable: true,
        value: originalNavigator,
      });
    } else {
      delete (globalThis as Partial<typeof globalThis>).navigator;
    }

    if (originalFetch) {
      globalThis.fetch = originalFetch;
    } else {
      delete (globalThis as Partial<typeof globalThis>).fetch;
    }

    if (originalCustomEvent) {
      Object.defineProperty(globalThis, 'CustomEvent', {
        configurable: true,
        value: originalCustomEvent,
      });
    } else {
      delete (globalThis as Partial<typeof globalThis>).CustomEvent;
    }
  });

  it('dispatches a browser metric event and ingests via sendBeacon when available', () => {
    const sendBeacon = jest.fn().mockReturnValue(true);
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: { sendBeacon },
    });

    const fetchSpy = jest.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    recordClientMetric('builder_preview_stream_update_count', 1, { source: 'sse' });

    expect(globalThis.window.dispatchEvent).toHaveBeenCalledTimes(1);
    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(sendBeacon.mock.calls[0][0]).toBe('/api/v1/telemetry/client-metrics');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('falls back to fetch keepalive when sendBeacon is unavailable or returns false', () => {
    const sendBeacon = jest.fn().mockReturnValue(false);
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: { sendBeacon },
    });

    const fetchSpy = jest.fn().mockResolvedValue({ ok: true });
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    recordClientMetric('builder_preview_runtime_restart_count', 1, { runtime_kind: 'iframe' });

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, options] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/telemetry/client-metrics');
    expect(options.keepalive).toBe(true);
    expect(options.method).toBe('POST');
  });

  it('ignores non-finite metric values', () => {
    const sendBeacon = jest.fn();
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: { sendBeacon },
    });

    const fetchSpy = jest.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    recordClientMetric('builder_preview_render_ms', Number.NaN);

    expect(globalThis.window.dispatchEvent).not.toHaveBeenCalled();
    expect(sendBeacon).not.toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
