import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { server } from '../../setupTests';
import { http, HttpResponse } from 'msw';

// Mock ProtectedRoute component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch('/api/me')
      .then((res) => res.json())
      .then((data) => {
        setUser(data.id ? data : null);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>Please sign in</div>;
  return <>{children}</>;
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it('shows loading state initially', () => {
    render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows protected content when user is authenticated', async () => {
    render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(screen.getByText('Protected content')).toBeInTheDocument();
    });
  });

  it('shows sign in prompt when user is not authenticated', async () => {
    // Override the /api/me handler to return no user
    server.use(
      http.get('/api/me', () => {
        return HttpResponse.json({}, { status: 401 });
      })
    );

    render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>
    );

    await waitFor(() => {
      expect(screen.getByText('Please sign in')).toBeInTheDocument();
    });

    expect(screen.queryByText('Protected content')).not.toBeInTheDocument();
  });
});
