export type TimelineStepStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface TimelineStep {
  id: string;
  label: string;
  status: TimelineStepStatus;
  detail?: string;
  durationMs?: number;
  attempt?: number;
  maxAttempts?: number;
}

export interface TimelineView {
  aqeLevel?: string;
  lane?: string;
  uiQualityMode?: string;
  targetMode?: string;
  degraded: boolean;
  cancelled: boolean;
  steps: TimelineStep[];
}

function normalizeStepStatus(value: unknown): TimelineStepStatus {
  if (value === 'running') {
    return 'running';
  }
  if (value === 'completed') {
    return 'completed';
  }
  if (value === 'failed' || value === 'cancelled') {
    return 'failed';
  }
  return 'pending';
}

function normalizeStep(entry: unknown): TimelineStep | null {
  if (!entry || typeof entry !== 'object') {
    return null;
  }

  const raw = entry as {
    id?: unknown;
    label?: unknown;
    status?: unknown;
    detail?: unknown;
    duration_ms?: unknown;
    attempt?: unknown;
    max_attempts?: unknown;
  };

  const id = typeof raw.id === 'string' && raw.id.trim() ? raw.id : undefined;
  const label = typeof raw.label === 'string' && raw.label.trim() ? raw.label : undefined;

  if (!id || !label) {
    return null;
  }

  return {
    id,
    label,
    status: normalizeStepStatus(raw.status),
    detail: typeof raw.detail === 'string' ? raw.detail : undefined,
    durationMs:
      typeof raw.duration_ms === 'number' && Number.isFinite(raw.duration_ms)
        ? raw.duration_ms
        : undefined,
    attempt:
      typeof raw.attempt === 'number' && Number.isInteger(raw.attempt)
        ? raw.attempt
        : undefined,
    maxAttempts:
      typeof raw.max_attempts === 'number' && Number.isInteger(raw.max_attempts)
        ? raw.max_attempts
        : undefined,
  };
}

export function parseJobOrchestrationTimeline(output: unknown): TimelineView | null {
  if (!output || typeof output !== 'object') {
    return null;
  }

  const root = output as { orchestration?: unknown };
  if (!root.orchestration || typeof root.orchestration !== 'object') {
    return null;
  }

  const orchestration = root.orchestration as {
    aqe_level?: unknown;
    lane?: unknown;
    ui_quality_mode?: unknown;
    target_mode?: unknown;
    degraded?: unknown;
    cancelled?: unknown;
    stages?: unknown;
  };

  const rawStages = Array.isArray(orchestration.stages) ? orchestration.stages : [];
  const steps = rawStages
    .map((entry) => normalizeStep(entry))
    .filter((entry): entry is TimelineStep => Boolean(entry));

  return {
    aqeLevel: typeof orchestration.aqe_level === 'string' ? orchestration.aqe_level : undefined,
    lane: typeof orchestration.lane === 'string' ? orchestration.lane : undefined,
    uiQualityMode:
      typeof orchestration.ui_quality_mode === 'string' ? orchestration.ui_quality_mode : undefined,
    targetMode: typeof orchestration.target_mode === 'string' ? orchestration.target_mode : undefined,
    degraded: Boolean(orchestration.degraded),
    cancelled: Boolean(orchestration.cancelled),
    steps,
  };
}
