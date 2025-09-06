import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock a simple component for accessibility testing
const MockComponent = () => (
  <div>
    <h1>Accessible Component</h1>
    <button type="button" aria-label="Close dialog">
      ×
    </button>
    <img src="/test.jpg" alt="Test image description" />
    <form>
      <label htmlFor="email">Email Address</label>
      <input type="email" id="email" required />
      <button type="submit">Submit</button>
    </form>
  </div>
);

describe('Accessibility Tests', () => {
  it('should not have any accessibility violations', async () => {
    const { container } = render(<MockComponent />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper ARIA labels', () => {
    const { getByLabelText, getByRole } = render(<MockComponent />);

    // Check for proper labeling
    expect(getByLabelText(/email address/i)).toBeInTheDocument();
    expect(getByRole('button', { name: /close dialog/i })).toBeInTheDocument();
  });

  it('should have proper heading hierarchy', () => {
    const { getByRole } = render(<MockComponent />);

    const heading = getByRole('heading', { level: 1 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent('Accessible Component');
  });

  it('should have alt text for images', () => {
    const { getByAltText } = render(<MockComponent />);

    expect(getByAltText(/test image description/i)).toBeInTheDocument();
  });

  it('should have proper form structure', () => {
    const { getByRole, getByLabelText } = render(<MockComponent />);

    const form = getByRole('form');
    const emailInput = getByLabelText(/email address/i);
    const submitButton = getByRole('button', { name: /submit/i });

    expect(form).toBeInTheDocument();
    expect(emailInput).toBeRequired();
    expect(submitButton).toHaveAttribute('type', 'submit');
  });
});
