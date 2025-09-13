import { NextRequest, NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { CostExplorerService } from '@/lib/costs/client';
import { CostExplorerError } from '@/lib/costs/types';
import { createCacheKey, withCache } from '@/lib/costs/cache';

async function getCostSummaryHandler(
  request: AuthenticatedRequest
): Promise<NextResponse> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const groupBy = searchParams.get('groupBy') || 'SERVICE';
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

    // Create cache key
    const cacheKey = createCacheKey('summary', searchParams);
    
    // Wrap Cost Explorer call with caching
    const costSeries = await withCache(async () => {
      const costExplorer = new CostExplorerService();
      
      if (groupBy === 'SERVICE') {
        return costExplorer.getCostsByService({
          timePeriod: { start: startDate, end: endDate },
          granularity,
          metric,
        });
      } else {
        // For other group by options, use general getCostAndUsage
        return costExplorer.getCostAndUsage({
          timePeriod: { start: startDate, end: endDate },
          granularity,
          metrics: [metric],
          groupBy: [{ type: 'DIMENSION', key: groupBy }],
        });
      }
    }, cacheKey);
    
    return NextResponse.json({
      ok: true,
      data: {
        metric,
        groupBy,
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
    console.error('Error in getCostSummaryHandler:', error);
    
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
        error: 'Failed to fetch cost summary',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getCostSummaryHandler, { requiredRole: 'admin' });