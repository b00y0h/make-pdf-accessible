import { NextRequest, NextResponse } from 'next/server';
import { withRBAC, AuthenticatedRequest } from '@/lib/rbac-middleware';
import { CostExplorerService } from '@/lib/costs/client';
import { CostExplorerError } from '@/lib/costs/types';

async function getCostForecastHandler(
  request: AuthenticatedRequest
): Promise<NextResponse> {
  try {
    // Extract query parameters
    const { searchParams } = new URL(request.url);
    const metric = (searchParams.get('metric') || 'UNBLENDED_COST') as 'UNBLENDED_COST' | 'BLENDED_COST';
    const granularity = (searchParams.get('granularity') || 'MONTHLY') as 'MONTHLY' | 'DAILY';
    const predictionIntervalLevel = parseInt(searchParams.get('predictionInterval') || '80');

    const costExplorer = new CostExplorerService();
    
    // Get cost forecast (automatically calculates next 3 months)
    const forecastData = await costExplorer.getCostForecast({
      granularity,
      metric,
      predictionIntervalLevel,
    });
    
    return NextResponse.json({
      ok: true,
      data: {
        metric,
        granularity,
        predictionIntervalLevel,
        timePeriod: {
          start: forecastData.forecastResults[0]?.timePeriod.start || '',
          end: forecastData.forecastResults[forecastData.forecastResults.length - 1]?.timePeriod.end || '',
        },
        forecastResultsByTime: forecastData.forecastResults,
        total: forecastData.total,
        metadata: forecastData.metadata,
      },
    });
  } catch (error) {
    console.error('Error in getCostForecastHandler:', error);
    
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
        error: 'Failed to fetch cost forecast',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// Apply RBAC middleware requiring admin role
export const GET = withRBAC(getCostForecastHandler, { requiredRole: 'admin' });