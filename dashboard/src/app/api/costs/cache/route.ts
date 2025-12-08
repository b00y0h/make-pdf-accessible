import { NextRequest, NextResponse } from 'next/server';
import { headers } from 'next/headers';
import { auth } from '@/lib/auth-server';
import { getCacheInstance } from '@/lib/cache/redis-cache';

async function checkAdminAuth() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session?.user) {
    return { error: 'Authentication required', status: 401 };
  }

  if ((session.user as any).role !== 'admin') {
    return { error: 'Admin access required', status: 403 };
  }

  return { session };
}

export async function GET(request: NextRequest) {
  try {
    const authResult = await checkAdminAuth();
    if ('error' in authResult) {
      return NextResponse.json(
        { error: authResult.error },
        { status: authResult.status }
      );
    }

    const cache = getCacheInstance();
    const stats = await cache.getStats();

    return NextResponse.json({
      ok: true,
      data: {
        stats,
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    console.error('Cache stats error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch cache statistics' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const authResult = await checkAdminAuth();
    if ('error' in authResult) {
      return NextResponse.json(
        { error: authResult.error },
        { status: authResult.status }
      );
    }

    const { searchParams } = new URL(request.url);
    const pattern = searchParams.get('pattern');
    const cache = getCacheInstance();

    let clearedCount = 0;

    if (pattern) {
      // Clear specific pattern
      clearedCount = await cache.clearPattern(pattern);
    } else {
      // Clear all cost-related cache
      clearedCount = await cache.clearAll();
    }

    return NextResponse.json({
      ok: true,
      data: {
        message: `Cleared ${clearedCount} cache entries`,
        clearedCount,
        pattern: pattern || 'all',
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    console.error('Cache clear error:', error);
    return NextResponse.json(
      { error: 'Failed to clear cache' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const authResult = await checkAdminAuth();
    if ('error' in authResult) {
      return NextResponse.json(
        { error: authResult.error },
        { status: authResult.status }
      );
    }

    const body = await request.json();
    const { action, key, params } = body;

    const cache = getCacheInstance();

    switch (action) {
      case 'invalidate':
        // Invalidate specific cache entry
        if (key && params) {
          await cache.delete(key, params);
          return NextResponse.json({
            ok: true,
            data: {
              message: `Invalidated cache entry: ${key}`,
              timestamp: new Date().toISOString(),
            },
          });
        }
        break;

      case 'metadata':
        // Get cache metadata for specific entry
        if (key && params) {
          const metadata = await cache.getMetadata(key, params);
          return NextResponse.json({
            ok: true,
            data: {
              key,
              params,
              metadata,
              timestamp: new Date().toISOString(),
            },
          });
        }
        break;

      case 'warmup':
        // Trigger cache warmup (could trigger background data fetch)
        return NextResponse.json({
          ok: true,
          data: {
            message: 'Cache warmup triggered',
            timestamp: new Date().toISOString(),
          },
        });

      default:
        return NextResponse.json(
          {
            error:
              'Invalid action. Supported actions: invalidate, metadata, warmup',
          },
          { status: 400 }
        );
    }

    return NextResponse.json(
      { error: 'Missing required parameters' },
      { status: 400 }
    );
  } catch (error) {
    console.error('Cache management error:', error);
    return NextResponse.json(
      { error: 'Failed to perform cache operation' },
      { status: 500 }
    );
  }
}
