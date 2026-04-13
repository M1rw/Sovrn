import { NextRequest, NextResponse } from 'next/server';

export async function POST(_request: NextRequest) {
  return NextResponse.json(
    {
      error: 'Deprecated endpoint',
      detail: '/api/v1/mml/generate has been removed as a generation path.',
      canonical: {
        enqueue: '/api/v1/projects/:projectId/generate',
        status: '/api/v1/jobs/:jobId',
      },
    },
    { status: 410 }
  );
}
