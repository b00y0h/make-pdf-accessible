import { NextRequest, NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { CostExplorerService } from '@/lib/costs/client';
import { CostExplorerError } from '@/lib/costs/types';

async function getCostByTagHandler(
  request: AuthenticatedRequest
): Promise<NextResponse> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const tag = searchParams.get('tag') || 'environment';
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
    
    // Get costs grouped by tag - this will validate supported tags
    const costSeries = await costExplorer.getCostsByTag({
      timePeriod: { start: startDate, end: endDate },
      tag,
      granularity,
      metric,
    });
    
    return NextResponse.json({
      ok: true,
      data: {
        metric,
        granularity,
        groupBy: `TAG$${tag}`,
        timePeriod: {
          start: startDate,
          end: endDate,
        },
        series: costSeries.series,
        metadata: costSeries.metadata,
      },
    });
  } catch (error) {
    console.error('Error in getCostByTagHandler:', error);
    
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
        error: 'Failed to fetch cost by tag',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getCostByTagHandler, { requiredRole: 'admin' });