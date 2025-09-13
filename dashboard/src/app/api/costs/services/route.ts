import { NextRequest, NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { CostExplorerService } from '@/lib/costs/client';
import { CostExplorerError } from '@/lib/costs/types';

async function getCostServicesHandler(
  request: AuthenticatedRequest
): Promise<NextResponse> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
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
    
    // Get available service dimensions
    const serviceDimensions = await costExplorer.getServiceDimensions({
      timePeriod: { start: startDate, end: endDate },
    });
    
    return NextResponse.json({
      ok: true,
      data: {
        dimension: 'SERVICE',
        timePeriod: {
          start: startDate,
          end: endDate,
        },
        dimensionValues: serviceDimensions,
        count: serviceDimensions.length,
      },
    });
  } catch (error) {
    console.error('Error in getCostServicesHandler:', error);
    
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
        error: 'Failed to fetch cost services',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getCostServicesHandler, { requiredRole: 'admin' });