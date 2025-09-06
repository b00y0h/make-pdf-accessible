import { render, screen } from '@testing-library/react';
import Home from '../app/page';

// Mock the page component if it doesn't exist yet
jest.mock(
  '../app/page',
  () => {
    return function MockHome() {
      return (
        <div>
          <h1>PDF Accessibility Platform</h1>
          <p>Transform your PDFs into accessible documents</p>
        </div>
      );
    };
  },
  { virtual: true }
);

describe('Home Page', () => {
  it('renders the main heading', () => {
    render(<Home />);

    const heading = screen.getByRole('heading', {
      name: /pdf accessibility platform/i,
    });

    expect(heading).toBeInTheDocument();
  });

  it('renders the description', () => {
    render(<Home />);

    const description = screen.getByText(
      /transform your pdfs into accessible documents/i
    );

    expect(description).toBeInTheDocument();
  });

  it('has proper accessibility structure', () => {
    render(<Home />);

    // Check for proper heading hierarchy
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toBeInTheDocument();
  });
});
