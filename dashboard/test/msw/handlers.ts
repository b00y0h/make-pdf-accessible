import { http, HttpResponse } from 'msw';

export const handlers = [
  // Dashboard specific API endpoints
  http.get('/api/auth/get-session', () => {
    return HttpResponse.json({
      user: {
        id: '1',
        email: 'admin@example.com',
        name: 'Admin User',
        role: 'admin',
      },
      session: {
        id: 'session-123',
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      },
    });
  }),

  http.get('/api/admin/users', () => {
    return HttpResponse.json({
      success: true,
      data: {
        users: [
          {
            id: '1',
            email: 'user1@example.com',
            name: 'User One',
            role: 'user',
            createdAt: new Date().toISOString(),
            documentCount: 5,
            documentsCompleted: 3,
          },
          {
            id: '2',
            email: 'user2@example.com',
            name: 'User Two',
            role: 'admin',
            createdAt: new Date().toISOString(),
            documentCount: 10,
            documentsCompleted: 8,
          },
        ],
        total: 2,
        totalPages: 1,
      },
    });
  }),

  http.patch('/api/admin/users/:userId/role', async ({ request, params }) => {
    const body = (await request.json()) as { role: string };
    return HttpResponse.json({
      success: true,
      message: `User role updated to ${body.role}`,
    });
  }),

  http.delete('/api/admin/users/:userId', () => {
    return HttpResponse.json({
      success: true,
      message: 'User deleted successfully',
    });
  }),
];
