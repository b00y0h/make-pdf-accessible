import { NextRequest } from 'next/server';
import { forwardToApi } from '@/lib/dashboard-api-proxy';

export async function POST(request: NextRequest) {
  return forwardToApi(request, '/documents/upload/presigned', {
    method: 'POST',
    body: await request.text(),
  });
}
