/**
 * Integration tests for CostsOverview component
 * Tests the complete flow from data loading to chart rendering
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { CostsOverview } from '../CostsOverview';
import { CostFilters } from '@/lib/costs/types';

// Mock recharts to avoid canvas issues in tests
jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children }: any) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: () => <div data-testid="area" />,
}));

describe('CostsOverview Integration Tests', () => {
  const mockFilters: CostFilters = {
    dateRange: { preset: '6months' },
    metric: 'UnblendedCost',
    granularity: 'MONTHLY',
    services: [],
    accounts: [],
    regions: [],
    tags: {},
  };

  const mockTimeseries = [
    { time: '2024-01', amount: 1000, unit: 'USD', estimated: false },
    { time: '2024-02', amount: 1200, unit: 'USD', estimated: false },
    { time: '2024-03', amount: 900, unit: 'USD', estimated: false },
    { time: '2024-04', amount: 1100, unit: 'USD', estimated: false },
    { time: '2024-05', amount: 1300, unit: 'USD', estimated: false },
    { time: '2024-06', amount: 1050, unit: 'USD', estimated: false },
  ];

  const mockSummary = [
    { time: '2024-01', service: 'EC2', amount: 500, unit: 'USD' },
    { time: '2024-01', service: 'S3', amount: 300, unit: 'USD' },
    { time: '2024-01', service: 'Lambda', amount: 200, unit: 'USD' },
    { time: '2024-02', service: 'EC2', amount: 600, unit: 'USD' },
    { time: '2024-02', service: 'S3', amount: 350, unit: 'USD' },
    { time: '2024-02', service: 'Lambda', amount: 250, unit: 'USD' },
  ];

  describe('Loading States', () => {
    it('should show loading skeletons when loading', () => {
      render(
        <CostsOverview
          timeseries={[]}
          summary={[]}
          loading={true}
          error={null}
          filters={mockFilters}
        />
      );

      // Should show loading skeletons
      expect(screen.getByTestId('loading-kpis')).toBeInTheDocument();
      expect(screen.getByTestId('loading-chart')).toBeInTheDocument();
      expect(screen.getByTestId('loading-table')).toBeInTheDocument();
    });

    it('should hide loading state when data is loaded', () => {
      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      // Loading skeletons should not be present
      expect(screen.queryByTestId('loading-kpis')).not.toBeInTheDocument();
      expect(screen.queryByTestId('loading-chart')).not.toBeInTheDocument();
      expect(screen.queryByTestId('loading-table')).not.toBeInTheDocument();
    });
  });

  describe('Error States', () => {
    it('should display error message when error occurs', () => {
      const errorMessage = 'Failed to fetch cost data';

      render(
        <CostsOverview
          timeseries={[]}
          summary={[]}
          loading={false}
          error={errorMessage}
          filters={mockFilters}
        />
      );

      expect(screen.getByText(/error loading cost data/i)).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it('should show retry button on error', () => {
      render(
        <CostsOverview
          timeseries={[]}
          summary={[]}
          loading={false}
          error="Network error"
          filters={mockFilters}
        />
      );

      expect(screen.getByText(/try again/i)).toBeInTheDocument();
    });
  });

  describe('Data Rendering', () => {
    it('should render KPIs with correct values', async () => {
      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      await waitFor(() => {
        // Should show total cost
        expect(screen.getByText('$6,550')).toBeInTheDocument(); // Sum of all months

        // Should show MoM change (last month vs previous)
        expect(screen.getByText(/-4.6%/)).toBeInTheDocument(); // June vs May change
      });
    });

    it('should render trend chart with data', async () => {
      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('line-chart')).toBeInTheDocument();
        expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
      });
    });

    it('should render service cost breakdown chart', async () => {
      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('area-chart')).toBeInTheDocument();
      });
    });

    it('should render top services table', async () => {
      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      await waitFor(() => {
        // Should show service names
        expect(screen.getByText('EC2')).toBeInTheDocument();
        expect(screen.getByText('S3')).toBeInTheDocument();
        expect(screen.getByText('Lambda')).toBeInTheDocument();
      });
    });
  });

  describe('Interactive Features', () => {
    it('should handle service click when callback provided', async () => {
      const mockOnServiceClick = jest.fn();

      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
          onServiceClick={mockOnServiceClick}
        />
      );

      await waitFor(() => {
        const ec2Row = screen.getByText('EC2').closest('tr');
        expect(ec2Row).toHaveClass('cursor-pointer');
      });

      // Click on EC2 service row
      fireEvent.click(screen.getByText('EC2').closest('tr')!);
      expect(mockOnServiceClick).toHaveBeenCalledWith('EC2');
    });

    it('should export CSV when export button clicked', async () => {
      // Mock URL.createObjectURL
      global.URL.createObjectURL = jest.fn(() => 'mock-url');
      global.URL.revokeObjectURL = jest.fn();

      // Mock anchor click
      const mockClick = jest.fn();
      const mockAnchor = { click: mockClick, href: '', download: '' };
      jest.spyOn(document, 'createElement').mockImplementation((tagName) => {
        if (tagName === 'a') return mockAnchor as any;
        return document.createElement(tagName);
      });

      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      await waitFor(() => {
        const exportButton = screen.getByText(/export csv/i);
        fireEvent.click(exportButton);
      });

      expect(mockClick).toHaveBeenCalled();
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  describe('Empty States', () => {
    it('should show empty state when no data available', () => {
      render(
        <CostsOverview
          timeseries={[]}
          summary={[]}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      expect(screen.getByText(/no cost data available/i)).toBeInTheDocument();
    });

    it('should show helpful message for filtered data with no results', () => {
      const filteredFilters: CostFilters = {
        ...mockFilters,
        services: ['NonExistentService'],
      };

      render(
        <CostsOverview
          timeseries={[]}
          summary={[]}
          loading={false}
          error={null}
          filters={filteredFilters}
        />
      );

      expect(
        screen.getByText(/try adjusting your filters/i)
      ).toBeInTheDocument();
    });
  });

  describe('Data Processing', () => {
    it('should handle unsorted timeseries data', () => {
      const unsortedTimeseries = [
        { time: '2024-03', amount: 900, unit: 'USD', estimated: false },
        { time: '2024-01', amount: 1000, unit: 'USD', estimated: false },
        { time: '2024-02', amount: 1200, unit: 'USD', estimated: false },
      ];

      render(
        <CostsOverview
          timeseries={unsortedTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      // Should still render without errors
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    });

    it('should handle mixed currencies gracefully', () => {
      const mixedCurrencyData = [
        { time: '2024-01', amount: 1000, unit: 'USD', estimated: false },
        { time: '2024-02', amount: 850, unit: 'EUR', estimated: false },
      ];

      render(
        <CostsOverview
          timeseries={mixedCurrencyData}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      // Should render without crashing
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    });

    it('should handle very large numbers', () => {
      const largeNumberData = [
        { time: '2024-01', amount: 1e12, unit: 'USD', estimated: false },
        { time: '2024-02', amount: 2e12, unit: 'USD', estimated: false },
      ];

      render(
        <CostsOverview
          timeseries={largeNumberData}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      // Should format large numbers appropriately
      expect(screen.getByText(/\$1\.00T/)).toBeInTheDocument();
    });

    it('should handle zero values correctly', () => {
      const zeroValueData = [
        { time: '2024-01', amount: 0, unit: 'USD', estimated: false },
        { time: '2024-02', amount: 100, unit: 'USD', estimated: false },
      ];

      render(
        <CostsOverview
          timeseries={zeroValueData}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      // Should show 100% increase MoM
      expect(screen.getByText(/\+∞%/)).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should adapt to different screen sizes', () => {
      // Test mobile view
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });

      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      // Charts should still be responsive
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels for charts', async () => {
      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      await waitFor(() => {
        // Charts should have descriptive labels
        expect(
          screen.getByLabelText(/cost trend over time/i)
        ).toBeInTheDocument();
        expect(
          screen.getByLabelText(/service cost breakdown/i)
        ).toBeInTheDocument();
      });
    });

    it('should be keyboard navigable', async () => {
      render(
        <CostsOverview
          timeseries={mockTimeseries}
          summary={mockSummary}
          loading={false}
          error={null}
          filters={mockFilters}
        />
      );

      // Tab through interactive elements
      const exportButton = screen.getByText(/export csv/i);
      exportButton.focus();
      expect(document.activeElement).toBe(exportButton);
    });
  });
});
