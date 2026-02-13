import Redis from 'ioredis';
import { createHash } from 'crypto';

export interface CacheOptions {
  ttl?: number; // TTL in seconds
  prefix?: string;
}

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expires: number;
}

export class RedisCache {
  private redis: Redis;
  private defaultTTL: number = 6 * 60 * 60; // 6 hours default
  private keyPrefix: string = 'costs:';

  constructor() {
    // Initialize Redis connection
    this.redis = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD,
      maxRetriesPerRequest: 3,
      lazyConnect: true,
      // Handle connection errors gracefully
      retryStrategy: (times: number) => {
        if (times > 3) {
          console.warn(
            'Redis connection failed after 3 retries, falling back to memory cache'
          );
          return null; // Stop retrying
        }
        return Math.min(times * 100, 3000);
      },
    });

    // Set up event listeners
    this.redis.on('error', (error: Error) => {
      console.warn('Redis connection error:', error.message);
    });

    this.redis.on('connect', () => {
      console.log('Connected to Redis cache');
    });
  }

  /**
   * Generate a cache key from parameters
   */
  private generateKey(baseKey: string, params: Record<string, any>): string {
    // Sort parameters for consistent key generation
    const sortedParams = Object.keys(params)
      .sort()
      .reduce(
        (obj, key) => {
          obj[key] = params[key];
          return obj;
        },
        {} as Record<string, any>
      );

    // Create hash of parameters for shorter, consistent keys
    const paramsHash = createHash('sha256')
      .update(JSON.stringify(sortedParams))
      .digest('hex')
      .substring(0, 16);

    return `${this.keyPrefix}${baseKey}:${paramsHash}`;
  }

  /**
   * Get cached data
   */
  async get<T>(
    key: string,
    params: Record<string, any> = {}
  ): Promise<T | null> {
    try {
      const cacheKey = this.generateKey(key, params);
      const cached = await this.redis.get(cacheKey);

      if (!cached) {
        return null;
      }

      const entry: CacheEntry<T> = JSON.parse(cached);

      // Check if expired (additional check beyond Redis TTL)
      if (Date.now() > entry.expires) {
        await this.delete(key, params);
        return null;
      }

      return entry.data;
    } catch (error) {
      console.warn('Cache get error:', error);
      return null; // Fail gracefully
    }
  }

  /**
   * Set cached data
   */
  async set<T>(
    key: string,
    data: T,
    params: Record<string, any> = {},
    options: CacheOptions = {}
  ): Promise<void> {
    try {
      const ttl = options.ttl || this.defaultTTL;
      const cacheKey = this.generateKey(key, params);

      const entry: CacheEntry<T> = {
        data,
        timestamp: Date.now(),
        expires: Date.now() + ttl * 1000,
      };

      await this.redis.setex(cacheKey, ttl, JSON.stringify(entry));
    } catch (error) {
      console.warn('Cache set error:', error);
      // Don't throw - caching failures shouldn't break the app
    }
  }

  /**
   * Delete cached data
   */
  async delete(key: string, params: Record<string, any> = {}): Promise<void> {
    try {
      const cacheKey = this.generateKey(key, params);
      await this.redis.del(cacheKey);
    } catch (error) {
      console.warn('Cache delete error:', error);
    }
  }

  /**
   * Check if data is cached
   */
  async has(key: string, params: Record<string, any> = {}): Promise<boolean> {
    try {
      const cacheKey = this.generateKey(key, params);
      const exists = await this.redis.exists(cacheKey);
      return exists === 1;
    } catch (error) {
      console.warn('Cache exists check error:', error);
      return false;
    }
  }

  /**
   * Get cache metadata (timestamp, TTL, etc.)
   */
  async getMetadata(
    key: string,
    params: Record<string, any> = {}
  ): Promise<{
    timestamp: number;
    expires: number;
    ttl: number;
  } | null> {
    try {
      const cacheKey = this.generateKey(key, params);
      const [cached, ttl] = await Promise.all([
        this.redis.get(cacheKey),
        this.redis.ttl(cacheKey),
      ]);

      if (!cached) {
        return null;
      }

      const entry: CacheEntry<any> = JSON.parse(cached);

      return {
        timestamp: entry.timestamp,
        expires: entry.expires,
        ttl: ttl > 0 ? ttl : 0,
      };
    } catch (error) {
      console.warn('Cache metadata error:', error);
      return null;
    }
  }

  /**
   * Clear all cache entries matching a pattern
   */
  async clearPattern(pattern: string): Promise<number> {
    try {
      const keys = await this.redis.keys(`${this.keyPrefix}${pattern}*`);
      if (keys.length === 0) {
        return 0;
      }

      await this.redis.del(...keys);
      return keys.length;
    } catch (error) {
      console.warn('Cache clear pattern error:', error);
      return 0;
    }
  }

  /**
   * Clear all cost-related cache
   */
  async clearAll(): Promise<number> {
    return this.clearPattern('');
  }

  /**
   * Get cache statistics
   */
  async getStats(): Promise<{
    totalKeys: number;
    memoryUsage: string;
    connected: boolean;
  }> {
    try {
      const keys = await this.redis.keys(`${this.keyPrefix}*`);
      const info = await this.redis.info('memory');
      const memoryMatch = info.match(/used_memory_human:(.+)/);

      return {
        totalKeys: keys.length,
        memoryUsage: memoryMatch ? memoryMatch[1].trim() : 'Unknown',
        connected: this.redis.status === 'ready',
      };
    } catch (error) {
      console.warn('Cache stats error:', error);
      return {
        totalKeys: 0,
        memoryUsage: 'Unknown',
        connected: false,
      };
    }
  }

  /**
   * Close Redis connection
   */
  async disconnect(): Promise<void> {
    try {
      await this.redis.quit();
    } catch (error) {
      console.warn('Redis disconnect error:', error);
    }
  }
}

// Singleton instance
let cacheInstance: RedisCache | null = null;

export function getCacheInstance(): RedisCache {
  if (!cacheInstance) {
    cacheInstance = new RedisCache();
  }
  return cacheInstance;
}

// Memory fallback cache for when Redis is unavailable
class MemoryCache {
  private cache = new Map<string, CacheEntry<any>>();
  private maxSize = 100; // Limit memory usage

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() > entry.expires) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  set<T>(key: string, data: T, ttl: number): void {
    // Remove oldest entries if cache is full
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      expires: Date.now() + ttl * 1000,
    });
  }

  delete(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }
}

export const memoryCache = new MemoryCache();
