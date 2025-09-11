import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

// Mock Header component for testing
const Header = ({
  title,
  user,
}: {
  title: string;
  user?: { name: string; role: string };
}) => {
  return (
    <header className="bg-white shadow">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {user && (
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                Welcome, {user.name}
              </span>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  user.role === 'admin'
                    ? 'bg-purple-100 text-purple-800'
                    : 'bg-green-100 text-green-800'
                }`}
              >
                {user.role}
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

describe('Header Component', () => {
  it('renders title correctly', () => {
    render(<Header title="Dashboard" />);
    expect(
      screen.getByRole('heading', { name: /dashboard/i })
    ).toBeInTheDocument();
  });

  it('displays user information when user is provided', () => {
    const user = { name: 'John Doe', role: 'admin' };
    render(<Header title="Admin Panel" user={user} />);

    expect(screen.getByText('Welcome, John Doe')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  it('applies correct role styling for admin', () => {
    const adminUser = { name: 'Admin User', role: 'admin' };
    render(<Header title="Dashboard" user={adminUser} />);

    const roleSpan = screen.getByText('admin');
    expect(roleSpan).toHaveClass('bg-purple-100', 'text-purple-800');
  });

  it('applies correct role styling for regular user', () => {
    const regularUser = { name: 'Regular User', role: 'user' };
    render(<Header title="Dashboard" user={regularUser} />);

    const roleSpan = screen.getByText('user');
    expect(roleSpan).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('does not display user info when no user provided', () => {
    render(<Header title="Dashboard" />);

    expect(screen.queryByText(/welcome/i)).not.toBeInTheDocument();
  });
});
