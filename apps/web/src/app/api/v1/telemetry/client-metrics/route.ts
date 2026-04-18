import { NextRequest, NextResponse } from 'next/server';

import {
  getClientMetricAggregateSnapshot,
  ingestClientMetricEvent,
} from '@/lib/server/client-metrics-aggregate';

export const dynamic = 'force-dynamic';

export async function GET(): Promise<NextResponse> {
  return NextResponse.json(getClientMetricAggregateSnapshot(), { status: 200 });
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON payload' }, { status: 400 });
  }

  const events = Array.isArray(payload) ? payload : [payload];
  let ingested = 0;
  for (const event of events) {
    if (ingestClientMetricEvent(event)) {
      ingested += 1;
    }
  }

  if (ingested === 0) {
    return NextResponse.json({ detail: 'No valid metric events found' }, { status: 400 });
  }

  return NextResponse.json({ ok: true, ingested }, { status: 202 });
}
