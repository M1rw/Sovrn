type MetricTagValue = string | number | boolean | null | undefined;
type MetricTags = Record<string, MetricTagValue>;

export interface ClientMetricEvent {
  name: string;
  value: number;
  tags?: MetricTags;
  timestamp: string;
}

interface MetricAggregate {
  count: number;
  sum: number;
  min: number;
  max: number;
  lastValue: number;
  lastTimestamp: string;
  lastTags?: MetricTags;
  recentValues: number[];
}

export interface MetricSnapshot {
  count: number;
  sum: number;
  mean: number;
  min: number;
  max: number;
  p50: number;
  p95: number;
  p99: number;
  last_value: number;
  last_timestamp: string;
  last_tags?: MetricTags;
}

const MAX_RECENT_VALUES = 512;
const metricStore = new Map<string, MetricAggregate>();

function percentile(values: number[], p: number): number {
  if (values.length === 0) {
    return 0;
  }

  const sorted = [...values].sort((a, b) => a - b);
  if (sorted.length === 1) {
    return sorted[0];
  }

  const rank = (sorted.length - 1) * (p / 100);
  const lower = Math.floor(rank);
  const upper = Math.ceil(rank);

  if (lower === upper) {
    return sorted[lower];
  }

  const weight = rank - lower;
  return sorted[lower] + (sorted[upper] - sorted[lower]) * weight;
}

function parseEvent(input: unknown): ClientMetricEvent | null {
  if (!input || typeof input !== 'object') {
    return null;
  }

  const candidate = input as Partial<ClientMetricEvent>;
  if (typeof candidate.name !== 'string' || candidate.name.trim().length === 0) {
    return null;
  }

  if (!Number.isFinite(candidate.value)) {
    return null;
  }

  const timestamp =
    typeof candidate.timestamp === 'string' && candidate.timestamp.trim().length > 0
      ? candidate.timestamp
      : new Date().toISOString();

  return {
    name: candidate.name,
    value: Number(candidate.value),
    tags: candidate.tags,
    timestamp,
  };
}

export function ingestClientMetricEvent(input: unknown): boolean {
  const event = parseEvent(input);
  if (!event) {
    return false;
  }

  const existing = metricStore.get(event.name);
  const nextRecentValues = existing ? [...existing.recentValues, event.value] : [event.value];
  if (nextRecentValues.length > MAX_RECENT_VALUES) {
    nextRecentValues.splice(0, nextRecentValues.length - MAX_RECENT_VALUES);
  }

  if (!existing) {
    metricStore.set(event.name, {
      count: 1,
      sum: event.value,
      min: event.value,
      max: event.value,
      lastValue: event.value,
      lastTimestamp: event.timestamp,
      lastTags: event.tags,
      recentValues: nextRecentValues,
    });
    return true;
  }

  metricStore.set(event.name, {
    count: existing.count + 1,
    sum: existing.sum + event.value,
    min: Math.min(existing.min, event.value),
    max: Math.max(existing.max, event.value),
    lastValue: event.value,
    lastTimestamp: event.timestamp,
    lastTags: event.tags,
    recentValues: nextRecentValues,
  });

  return true;
}

export function getClientMetricAggregateSnapshot(): {
  generated_at: string;
  metrics: Record<string, MetricSnapshot>;
} {
  const metrics: Record<string, MetricSnapshot> = {};

  for (const [name, aggregate] of metricStore.entries()) {
    metrics[name] = {
      count: aggregate.count,
      sum: aggregate.sum,
      mean: aggregate.count > 0 ? aggregate.sum / aggregate.count : 0,
      min: aggregate.min,
      max: aggregate.max,
      p50: percentile(aggregate.recentValues, 50),
      p95: percentile(aggregate.recentValues, 95),
      p99: percentile(aggregate.recentValues, 99),
      last_value: aggregate.lastValue,
      last_timestamp: aggregate.lastTimestamp,
      last_tags: aggregate.lastTags,
    };
  }

  return {
    generated_at: new Date().toISOString(),
    metrics,
  };
}

export function resetClientMetricAggregateForTests(): void {
  metricStore.clear();
}
