import crypto from 'crypto';

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
  key: string;
}

export interface CacheOptions {
  ttl?: number; // Time to live in seconds (default: 6 hours)
  keyPrefix?: string;
  enabled?: boolean;
}

/**
 * Simple in-memory cache for Cost Explorer responses
 * In production, this should be replaced with Redis or similar
 */
export class CostExplorerCache {
  private cache = new Map<string, CacheEntry<any>>();
  private defaultTTL = 6 * 60 * 60 * 1000; // 6 hours in milliseconds
  private keyPrefix = 'costs:ce:';

  constructor(private options: CacheOptions = {}) {
    this.defaultTTL = (options.ttl || 6 * 60 * 60) * 1000; // Convert to milliseconds
    this.keyPrefix = options.keyPrefix || 'costs:ce:';
  }

  /**
   * Generate cache key from parameters
   */
  generateKey(params: Record<string, any>): string {
    // Sort keys for consistent hashing
    const sortedParams = Object.keys(params)
      .sort()
      .reduce(
        (obj, key) => {
          obj[key] = params[key];
          return obj;
        },
        {} as Record<string, any>
      );

    const paramString = JSON.stringify(sortedParams);
    const hash = crypto.createHash('sha256').update(paramString).digest('hex');
    return `${this.keyPrefix}${hash}`;
  }

  /**
   * Get cached data
   */
  async get<T>(key: string): Promise<T | null> {
    if (!this.options.enabled) return null;

    const entry = this.cache.get(key);
    if (!entry) return null;

    // Check if expired
    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  /**
   * Set cached data
   */
  async set<T>(key: string, data: T, ttl?: number): Promise<void> {
    if (!this.options.enabled) return;

    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl: ttl ? ttl * 1000 : this.defaultTTL,
      key,
    };

    this.cache.set(key, entry);
  }

  /**
   * Cache wrapper for Cost Explorer operations
   */
  async wrap<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    // Try to get from cache first
    const cached = await this.get<T>(key);
    if (cached) {
      // Add cache metadata
      if (
        typeof cached === 'object' &&
        cached !== null &&
        'metadata' in cached
      ) {
        (cached as any).metadata = {
          ...(cached as any).metadata,
          cached: true,
          cacheKey: key,
        };
      }
      return cached;
    }

    // Fetch fresh data
    const data = await fetcher();

    // Cache the result
    await this.set(key, data, ttl);

    return data;
  }

  /**
   * Invalidate cache by pattern
   */
  async invalidate(pattern?: string): Promise<void> {
    if (!pattern) {
      // Clear all cache
      this.cache.clear();
      return;
    }

    // Remove entries matching pattern
    const keysToDelete: string[] = [];
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach((key) => this.cache.delete(key));
  }

  /**
   * Get cache statistics
   */
  getStats(): {
    size: number;
    keys: string[];
    hitRate?: number;
  } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }

  /**
   * Clean up expired entries
   */
  cleanup(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach((key) => this.cache.delete(key));
  }

  /**
   * Start periodic cleanup
   */
  startCleanup(intervalMinutes: number = 30): NodeJS.Timeout {
    return setInterval(
      () => {
        this.cleanup();
      },
      intervalMinutes * 60 * 1000
    );
  }
}

// Global cache instance
export const costExplorerCache = new CostExplorerCache({
  enabled: process.env.NODE_ENV !== 'test', // Disable in tests
  ttl: 6 * 60 * 60, // 6 hours
  keyPrefix: 'costs:ce:',
});

// Helper function to create cache key for API routes
export function createCacheKey(
  endpoint: string,
  params: URLSearchParams
): string {
  const paramObject: Record<string, string> = {};

  // Convert URLSearchParams to object
  params.forEach((value, key) => {
    paramObject[key] = value;
  });

  // Add endpoint to params for uniqueness
  paramObject._endpoint = endpoint;

  return costExplorerCache.generateKey(paramObject);
}

// Middleware for API routes to add caching
export function withCache<T>(
  handler: () => Promise<T>,
  cacheKey: string,
  ttl?: number
): Promise<T> {
  return costExplorerCache.wrap(cacheKey, handler, ttl);
}
