type MetricTagValue = string | number | boolean | null | undefined;

type MetricTags = Record<string, MetricTagValue>;

interface ClientMetricEvent {
  name: string;
  value: number;
  tags?: MetricTags;
  timestamp: string;
}

const CLIENT_SESSION_STORAGE_KEY = 'sovrn.client_session_id';
const METRIC_EVENT_NAME = 'sovrn:metric';
const DEFAULT_INGEST_ENDPOINT = '/api/v1/telemetry/client-metrics';
const METRIC_INGEST_ENDPOINT =
  process.env.NEXT_PUBLIC_TELEMETRY_INGEST_ENDPOINT?.trim() || DEFAULT_INGEST_ENDPOINT;
const METRIC_INGEST_ENABLED = process.env.NEXT_PUBLIC_TELEMETRY_INGEST_ENABLED !== 'false';

function generateId(): string {
  if (typeof globalThis.crypto !== 'undefined' && typeof globalThis.crypto.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function getClientSessionId(): string {
  if (typeof window === 'undefined') {
    const g = globalThis as typeof globalThis & { __SOVRN_SERVER_SESSION_ID?: string };
    if (!g.__SOVRN_SERVER_SESSION_ID) {
      g.__SOVRN_SERVER_SESSION_ID = `server-${generateId()}`;
    }
    return g.__SOVRN_SERVER_SESSION_ID;
  }

  const existing = window.sessionStorage.getItem(CLIENT_SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const next = `client-${generateId()}`;
  window.sessionStorage.setItem(CLIENT_SESSION_STORAGE_KEY, next);
  return next;
}

export function createCorrelationId(scope: string): string {
  const safeScope = scope.replace(/[^a-zA-Z0-9/_-]/g, '_');
  return `${safeScope}:${generateId()}`;
}

export function recordClientMetric(name: string, value: number, tags?: MetricTags): void {
  if (!Number.isFinite(value)) {
    return;
  }

  const event: ClientMetricEvent = {
    name,
    value,
    tags,
    timestamp: new Date().toISOString(),
  };

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent<ClientMetricEvent>(METRIC_EVENT_NAME, { detail: event }));
  }

  if (process.env.NODE_ENV !== 'production') {
    // Kept lightweight for local diagnostics until backend ingestion endpoint is enabled.
    console.debug('client_metric', event);
  }

  queueMetricIngest(event);
}

function queueMetricIngest(event: ClientMetricEvent): void {
  if (typeof window === 'undefined' || !METRIC_INGEST_ENABLED) {
    return;
  }

  const payload = JSON.stringify(event);

  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    try {
      const blob = new Blob([payload], { type: 'application/json' });
      if (navigator.sendBeacon(METRIC_INGEST_ENDPOINT, blob)) {
        return;
      }
    } catch {
      // Continue to fetch fallback for browsers without Blob/sendBeacon support.
    }
  }

  void fetch(METRIC_INGEST_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: payload,
    keepalive: true,
    credentials: 'same-origin',
  }).catch(() => undefined);
}

export function recordRequestMetric(
  endpoint: string,
  method: string,
  statusCode: number,
  durationMs: number
): void {
  recordClientMetric('http_client_duration_ms', durationMs, {
    endpoint,
    method,
    status_code: statusCode,
  });
}

export function recordUiError(
  error: unknown,
  source: 'error' | 'unhandledrejection' | 'boundary',
  extraTags?: MetricTags
): void {
  const message = error instanceof Error ? error.message : String(error ?? 'unknown_error');
  recordClientMetric('ui_error_count', 1, {
    source,
    message,
    ...extraTags,
  });
}

export function initClientTelemetry(): () => void {
  if (typeof window === 'undefined') {
    return () => undefined;
  }

  // Ensure session id is ready before any API requests are made.
  getClientSessionId();

  const onError = (event: ErrorEvent): void => {
    recordUiError(event.error ?? event.message, 'error', {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  };

  const onUnhandledRejection = (event: PromiseRejectionEvent): void => {
    recordUiError(event.reason, 'unhandledrejection');
  };

  window.addEventListener('error', onError);
  window.addEventListener('unhandledrejection', onUnhandledRejection);

  return () => {
    window.removeEventListener('error', onError);
    window.removeEventListener('unhandledrejection', onUnhandledRejection);
  };
}

export const TELEMETRY_METRIC_EVENT = METRIC_EVENT_NAME;
