import { auth } from '@/lib/auth-server';

export async function POST(request: Request) {
  try {
    // Pass the request directly to BetterAuth
    const response = await auth.handler(request);
    return response;
  } catch (error) {
    console.error('Sign-in email POST error:', error);
    return Response.json({ error: 'Internal server error' }, { status: 500 });
  }
}
