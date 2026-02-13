import { NextRequest, NextResponse } from 'next/server';
import { getCacheInstance } from '../cache/redis-cache';

export interface RateLimitConfig {
  windowMs: number; // Time window in milliseconds
  maxRequests: number; // Maximum requests per window
  keyGenerator?: (request: NextRequest) => string; // Custom key generator
  skipIf?: (request: NextRequest) => boolean; // Skip rate limiting condition
  onLimitReached?: (request: NextRequest) => void; // Callback when limit is reached
}

export interface RateLimitResult {
  success: boolean;
  limit: number;
  remaining: number;
  resetTime: Date;
  retryAfter?: number; // Seconds to wait before retrying
}

export class RateLimiter {
  private cache = getCacheInstance();
  private keyPrefix = 'ratelimit:';

  constructor(private config: RateLimitConfig) {}

  async checkLimit(request: NextRequest): Promise<RateLimitResult> {
    // Check if rate limiting should be skipped
    if (this.config.skipIf?.(request)) {
      return {
        success: true,
        limit: this.config.maxRequests,
        remaining: this.config.maxRequests,
        resetTime: new Date(Date.now() + this.config.windowMs),
      };
    }

    // Generate rate limit key
    const key =
      this.config.keyGenerator?.(request) || this.getDefaultKey(request);
    const cacheKey = `${this.keyPrefix}${key}`;

    const now = Date.now();
    const windowStart = now - this.config.windowMs;

    try {
      // Get current request count and timestamps
      const existing = await this.cache.get<{
        count: number;
        windowStart: number;
      }>(cacheKey, {});

      let count = 0;
      let resetTime = new Date(now + this.config.windowMs);

      if (
        existing &&
        existing.windowStart !== undefined &&
        existing.windowStart > windowStart
      ) {
        // Within current window
        count = existing.count;
        resetTime = new Date(existing.windowStart + this.config.windowMs);
      }

      // Check if limit exceeded
      if (count >= this.config.maxRequests) {
        this.config.onLimitReached?.(request);

        return {
          success: false,
          limit: this.config.maxRequests,
          remaining: 0,
          resetTime,
          retryAfter: Math.ceil((resetTime.getTime() - now) / 1000),
        };
      }

      // Increment counter
      const newCount = count + 1;
      const newWindowStart =
        existing?.windowStart !== undefined &&
        existing.windowStart > windowStart
          ? existing.windowStart
          : now;

      await this.cache.set(
        cacheKey,
        {
          count: newCount,
          windowStart: newWindowStart,
        },
        {},
        { ttl: Math.ceil(this.config.windowMs / 1000) }
      );

      return {
        success: true,
        limit: this.config.maxRequests,
        remaining: Math.max(0, this.config.maxRequests - newCount),
        resetTime: new Date(newWindowStart + this.config.windowMs),
      };
    } catch (error) {
      console.warn('Rate limiting error, allowing request:', error);
      // Fail open - allow request if rate limiting fails
      return {
        success: true,
        limit: this.config.maxRequests,
        remaining: this.config.maxRequests - 1,
        resetTime: new Date(now + this.config.windowMs),
      };
    }
  }

  private getDefaultKey(request: NextRequest): string {
    // Use IP address as default key
    const forwarded = request.headers.get('x-forwarded-for');
    const ip = forwarded
      ? forwarded.split(',')[0]
      : request.headers.get('x-real-ip') || 'unknown';

    // Include user agent to distinguish different clients from same IP
    const userAgent = request.headers.get('user-agent') || 'unknown';
    const userAgentHash = this.simpleHash(userAgent);

    return `${ip}:${userAgentHash}`;
  }

  private simpleHash(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36);
  }
}

// Pre-configured rate limiters for different use cases
export const costExplorerRateLimit = new RateLimiter({
  windowMs: 60 * 1000, // 1 minute
  maxRequests: 30, // 30 requests per minute (AWS CE has generous limits)
  keyGenerator: (request) => {
    // Rate limit per user for cost explorer requests
    const url = new URL(request.url);
    const userId = request.headers.get('x-user-id') || 'anonymous';
    return `ce:${userId}`;
  },
  skipIf: (request) => {
    // Skip rate limiting for internal requests
    const userAgent = request.headers.get('user-agent') || '';
    return userAgent.includes('internal') || userAgent.includes('healthcheck');
  },
  onLimitReached: (request) => {
    console.warn('Cost Explorer rate limit reached:', {
      url: request.url,
      userAgent: request.headers.get('user-agent'),
      timestamp: new Date().toISOString(),
    });
  },
});

export const athenaRateLimit = new RateLimiter({
  windowMs: 5 * 60 * 1000, // 5 minutes
  maxRequests: 10, // 10 requests per 5 minutes (Athena is more limited)
  keyGenerator: (request) => {
    const userId = request.headers.get('x-user-id') || 'anonymous';
    return `athena:${userId}`;
  },
  onLimitReached: (request) => {
    console.warn('Athena rate limit reached:', {
      url: request.url,
      timestamp: new Date().toISOString(),
    });
  },
});

export const generalApiRateLimit = new RateLimiter({
  windowMs: 60 * 1000, // 1 minute
  maxRequests: 100, // 100 requests per minute for general API
  keyGenerator: (request) => {
    const forwarded = request.headers.get('x-forwarded-for');
    const ip = forwarded
      ? forwarded.split(',')[0]
      : request.headers.get('x-real-ip') || 'unknown';
    return `api:${ip}`;
  },
});

// Middleware function to apply rate limiting
export function withRateLimit(rateLimiter: RateLimiter) {
  return async function rateLimitMiddleware(
    request: NextRequest,
    handler: (request: NextRequest) => Promise<NextResponse>
  ): Promise<NextResponse> {
    const result = await rateLimiter.checkLimit(request);

    if (!result.success) {
      return new NextResponse(
        JSON.stringify({
          error: 'Rate limit exceeded',
          message: `Too many requests. Try again in ${result.retryAfter} seconds.`,
          retryAfter: result.retryAfter,
        }),
        {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'X-RateLimit-Limit': result.limit.toString(),
            'X-RateLimit-Remaining': result.remaining.toString(),
            'X-RateLimit-Reset': result.resetTime.toISOString(),
            'Retry-After': result.retryAfter?.toString() || '60',
          },
        }
      );
    }

    // Add rate limit headers to successful responses
    const response = await handler(request);

    response.headers.set('X-RateLimit-Limit', result.limit.toString());
    response.headers.set('X-RateLimit-Remaining', result.remaining.toString());
    response.headers.set('X-RateLimit-Reset', result.resetTime.toISOString());

    return response;
  };
}

// Helper to create quota enforcement for cost data
export interface QuotaConfig {
  dailyLimit: number;
  monthlyLimit: number;
  resetTime?: string; // UTC time for reset (e.g., "00:00")
}

export class QuotaEnforcer {
  private cache = getCacheInstance();
  private keyPrefix = 'quota:';

  constructor(private config: QuotaConfig) {}

  async checkQuota(
    userId: string,
    requestCost: number = 1
  ): Promise<{
    allowed: boolean;
    dailyUsed: number;
    monthlyUsed: number;
    dailyLimit: number;
    monthlyLimit: number;
    resetTime: Date;
  }> {
    const now = new Date();
    const dailyKey = `${this.keyPrefix}daily:${userId}:${now.toISOString().split('T')[0]}`;
    const monthlyKey = `${this.keyPrefix}monthly:${userId}:${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}`;

    try {
      const [dailyUsedResult, monthlyUsedResult] = await Promise.all([
        this.cache.get<number>(dailyKey, {}),
        this.cache.get<number>(monthlyKey, {}),
      ]);

      const dailyUsed = dailyUsedResult ?? 0;
      const monthlyUsed = monthlyUsedResult ?? 0;

      const newDailyUsed = dailyUsed + requestCost;
      const newMonthlyUsed = monthlyUsed + requestCost;

      const allowed =
        newDailyUsed <= this.config.dailyLimit &&
        newMonthlyUsed <= this.config.monthlyLimit;

      if (allowed) {
        // Update usage counters
        await Promise.all([
          this.cache.set(dailyKey, newDailyUsed, {}, { ttl: 24 * 60 * 60 }), // 24 hours
          this.cache.set(
            monthlyKey,
            newMonthlyUsed,
            {},
            { ttl: 31 * 24 * 60 * 60 }
          ), // 31 days
        ]);
      }

      // Calculate next reset time
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(0, 0, 0, 0);

      return {
        allowed,
        dailyUsed: allowed ? newDailyUsed : dailyUsed,
        monthlyUsed: allowed ? newMonthlyUsed : monthlyUsed,
        dailyLimit: this.config.dailyLimit,
        monthlyLimit: this.config.monthlyLimit,
        resetTime: tomorrow,
      };
    } catch (error) {
      console.warn('Quota check error, allowing request:', error);
      // Fail open
      return {
        allowed: true,
        dailyUsed: 0,
        monthlyUsed: 0,
        dailyLimit: this.config.dailyLimit,
        monthlyLimit: this.config.monthlyLimit,
        resetTime: new Date(now.getTime() + 24 * 60 * 60 * 1000),
      };
    }
  }
}

// Default quota enforcer for cost data requests
export const costDataQuotaEnforcer = new QuotaEnforcer({
  dailyLimit: 1000, // 1000 requests per day per user
  monthlyLimit: 10000, // 10000 requests per month per user
});
