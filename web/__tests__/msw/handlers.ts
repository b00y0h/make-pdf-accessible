import { http, HttpResponse } from 'msw';

export const handlers = [
  // Mock API endpoints
  http.get('/api/me', () => {
    return HttpResponse.json({
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'user',
    });
  }),

  http.post('/api/login', async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };

    if (body.email === 'test@example.com' && body.password === 'password') {
      return HttpResponse.json({
        success: true,
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
        },
      });
    }

    return HttpResponse.json({ error: 'Invalid credentials' }, { status: 401 });
  }),

  http.get('/api/documents', () => {
    return HttpResponse.json({
      documents: [
        {
          id: '1',
          name: 'Test Document',
          status: 'processed',
          createdAt: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      totalPages: 1,
    });
  }),
];
