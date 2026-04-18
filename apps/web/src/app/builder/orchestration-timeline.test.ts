import { parseJobOrchestrationTimeline } from './orchestration-timeline';

describe('parseJobOrchestrationTimeline', () => {
  it('returns null when orchestration payload is missing', () => {
    expect(parseJobOrchestrationTimeline({})).toBeNull();
    expect(parseJobOrchestrationTimeline(null)).toBeNull();
  });

  it('normalizes orchestration metadata and timeline steps', () => {
    const parsed = parseJobOrchestrationTimeline({
      orchestration: {
        aqe_level: 'Q2',
        lane: 'interactive',
        ui_quality_mode: 'high',
        target_mode: 'quality',
        degraded: true,
        cancelled: false,
        stages: [
          {
            id: 'architect',
            label: 'Architect',
            status: 'completed',
            detail: 'Completed',
            duration_ms: 345,
            attempt: 1,
            max_attempts: 1,
          },
          {
            id: 'critic',
            label: 'Critic',
            status: 'cancelled',
            detail: 'Cancelled by user',
            attempt: 1,
            max_attempts: 2,
          },
          {
            id: null,
            label: 'Bad stage',
            status: 'running',
          },
        ],
      },
    });

    expect(parsed).not.toBeNull();
    expect(parsed?.aqeLevel).toBe('Q2');
    expect(parsed?.lane).toBe('interactive');
    expect(parsed?.uiQualityMode).toBe('high');
    expect(parsed?.targetMode).toBe('quality');
    expect(parsed?.degraded).toBe(true);
    expect(parsed?.cancelled).toBe(false);
    expect(parsed?.steps).toHaveLength(2);

    expect(parsed?.steps[0]).toEqual({
      id: 'architect',
      label: 'Architect',
      status: 'completed',
      detail: 'Completed',
      durationMs: 345,
      attempt: 1,
      maxAttempts: 1,
    });

    expect(parsed?.steps[1]).toEqual({
      id: 'critic',
      label: 'Critic',
      status: 'failed',
      detail: 'Cancelled by user',
      durationMs: undefined,
      attempt: 1,
      maxAttempts: 2,
    });
  });
});
