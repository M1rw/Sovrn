import {
  getClientMetricAggregateSnapshot,
  ingestClientMetricEvent,
  resetClientMetricAggregateForTests,
} from './client-metrics-aggregate';

describe('client metric aggregate store', () => {
  beforeEach(() => {
    resetClientMetricAggregateForTests();
  });

  it('ingests metric values and computes aggregate percentiles', () => {
    const metricName = 'builder_preview_render_ms';
    [10, 20, 30, 40, 50].forEach((value, index) => {
      const ingested = ingestClientMetricEvent({
        name: metricName,
        value,
        timestamp: `2026-04-17T00:00:0${index}Z`,
      });
      expect(ingested).toBe(true);
    });

    const snapshot = getClientMetricAggregateSnapshot();
    const metric = snapshot.metrics[metricName];
    expect(metric.count).toBe(5);
    expect(metric.sum).toBe(150);
    expect(metric.mean).toBe(30);
    expect(metric.min).toBe(10);
    expect(metric.max).toBe(50);
    expect(metric.p50).toBe(30);
    expect(metric.p95).toBeCloseTo(48, 5);
    expect(metric.p99).toBeCloseTo(49.6, 5);
  });

  it('tracks count-style metrics with tags and last value metadata', () => {
    const metricName = 'builder_preview_stream_reconnect_count';

    ingestClientMetricEvent({
      name: metricName,
      value: 1,
      timestamp: '2026-04-17T00:00:01Z',
      tags: { previous_state: 'stale' },
    });
    ingestClientMetricEvent({
      name: metricName,
      value: 1,
      timestamp: '2026-04-17T00:00:02Z',
      tags: { previous_state: 'error' },
    });

    const snapshot = getClientMetricAggregateSnapshot();
    const metric = snapshot.metrics[metricName];
    expect(metric.count).toBe(2);
    expect(metric.sum).toBe(2);
    expect(metric.last_value).toBe(1);
    expect(metric.last_timestamp).toBe('2026-04-17T00:00:02Z');
    expect(metric.last_tags).toEqual({ previous_state: 'error' });
  });

  it('rejects malformed metric payloads', () => {
    expect(ingestClientMetricEvent(null)).toBe(false);
    expect(ingestClientMetricEvent({})).toBe(false);
    expect(ingestClientMetricEvent({ name: '', value: 1 })).toBe(false);
    expect(ingestClientMetricEvent({ name: 'builder_preview_render_ms', value: Number.NaN })).toBe(false);
  });
});
