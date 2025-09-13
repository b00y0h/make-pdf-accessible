import { NextRequest, NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { CostExplorerService } from '@/lib/costs/client';
import { CostExplorerError } from '@/lib/costs/types';

async function getCostTimeseriesHandler(
  request: AuthenticatedRequest
): Promise<NextResponse> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const metric = (searchParams.get('metric') || 'UnblendedCost') as 'UnblendedCost' | 'AmortizedCost';
    const granularity = (searchParams.get('granularity') || 'MONTHLY') as 'MONTHLY' | 'DAILY';
    const preset = searchParams.get('preset') || '12months';
    
    // Use preset or custom date range
    let startDate = searchParams.get('startDate');
    let endDate = searchParams.get('endDate');
    
    if (!startDate || !endDate) {
      const dateRange = CostExplorerService.getDateRange(preset as any);
      startDate = dateRange.start;
      endDate = dateRange.end;
    }

    const costExplorer = new CostExplorerService();
    
    // Get timeseries data (total monthly cost with no grouping)
    const costSeries = await costExplorer.getTimeseries({
      timePeriod: { start: startDate, end: endDate },
      granularity,
      metric,
    });
    
    return NextResponse.json({
      ok: true,
      data: {
        metric,
        granularity,
        timePeriod: {
          start: startDate,
          end: endDate,
        },
        series: costSeries.series,
        metadata: costSeries.metadata,
      },
    });
  } catch (error) {
    console.error('Error in getCostTimeseriesHandler:', error);
    
    if (error instanceof CostExplorerError) {
      return NextResponse.json(
        {
          ok: false,
          error: 'Cost Explorer API error',
          details: error.message,
          code: error.code,
        },
        { status: error.statusCode || 500 }
      );
    }
    
    return NextResponse.json(
      {
        ok: false,
        error: 'Failed to fetch cost timeseries',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getCostTimeseriesHandler, { requiredRole: 'admin' });