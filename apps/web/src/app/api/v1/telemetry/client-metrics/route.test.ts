import { NextRequest } from 'next/server';

import { resetClientMetricAggregateForTests } from '@/lib/server/client-metrics-aggregate';

import { GET, POST } from './route';

describe('client telemetry route', () => {
  beforeEach(() => {
    resetClientMetricAggregateForTests();
  });

  it('ingests metric payload and exposes aggregate snapshot', async () => {
    const postRequest = new NextRequest('http://localhost/api/v1/telemetry/client-metrics', {
      method: 'POST',
      body: JSON.stringify({
        name: 'builder_preview_render_ms',
        value: 420,
        timestamp: '2026-04-17T00:00:00Z',
      }),
      headers: {
        'content-type': 'application/json',
      },
    });

    const postResponse = await POST(postRequest);
    expect(postResponse.status).toBe(202);
    await expect(postResponse.json()).resolves.toMatchObject({ ok: true, ingested: 1 });

    const getResponse = await GET();
    expect(getResponse.status).toBe(200);

    const snapshot = await getResponse.json();
    expect(snapshot.metrics.builder_preview_render_ms).toBeDefined();
    expect(snapshot.metrics.builder_preview_render_ms.count).toBe(1);
    expect(snapshot.metrics.builder_preview_render_ms.p95).toBe(420);
  });

  it('rejects payloads with no valid metric entries', async () => {
    const invalidRequest = new NextRequest('http://localhost/api/v1/telemetry/client-metrics', {
      method: 'POST',
      body: JSON.stringify({ value: 1 }),
      headers: {
        'content-type': 'application/json',
      },
    });

    const response = await POST(invalidRequest);
    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toMatchObject({
      detail: 'No valid metric events found',
    });
  });
});
