import { NextRequest, NextResponse } from 'next/server';
import { headers } from 'next/headers';
import { auth } from '@/lib/auth-server';
import { createAthenaQueryService } from '@/lib/costs/athena-client';
import { type CostFilters } from '@/lib/costs/types';

export async function GET(request: NextRequest) {
  try {
    // Check authentication and admin role using better-auth
    const session = await auth.api.getSession({
      headers: await headers(),
    });

    if (!session?.user) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    if ((session.user as any).role !== 'admin') {
      return NextResponse.json(
        { error: 'Admin access required' },
        { status: 403 }
      );
    }

    // Parse query parameters
    const { searchParams } = new URL(request.url);

    const filters: CostFilters = {
      dateRange: {
        preset: (searchParams.get('preset') as any) || '12months',
        custom:
          searchParams.get('start') && searchParams.get('end')
            ? {
                start: searchParams.get('start')!,
                end: searchParams.get('end')!,
              }
            : undefined,
      },
      metric: (searchParams.get('metric') as any) || 'UnblendedCost',
      granularity: (searchParams.get('granularity') as any) || 'MONTHLY',
      services: searchParams.get('services')?.split(',').filter(Boolean) || [],
      accounts: searchParams.get('accounts')?.split(',').filter(Boolean) || [],
      regions: searchParams.get('regions')?.split(',').filter(Boolean) || [],
      tags: JSON.parse(searchParams.get('tags') || '{}'),
    };

    // Create Athena service and fetch data
    const athenaService = createAthenaQueryService();
    const data = await athenaService.getTimeseries(filters);

    // Add cache headers (shorter TTL for Athena since data is less frequently updated)
    const response = NextResponse.json(data);
    response.headers.set(
      'Cache-Control',
      'public, max-age=3600, stale-while-revalidate=1800'
    ); // 1 hour cache

    return response;
  } catch (error) {
    console.error('Athena timeseries error:', error);

    // Handle specific Athena errors
    if (error instanceof Error) {
      if (error.message.includes('Query failed')) {
        return NextResponse.json(
          { error: 'Query execution failed', details: error.message },
          { status: 400 }
        );
      }

      if (error.message.includes('timed out')) {
        return NextResponse.json(
          { error: 'Query execution timed out' },
          { status: 408 }
        );
      }
    }

    return NextResponse.json(
      { error: 'Failed to fetch Athena cost data' },
      { status: 500 }
    );
  }
}
