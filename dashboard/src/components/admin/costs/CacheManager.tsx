'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Database,
  Trash2,
  RefreshCw,
  Activity,
  Clock,
  MemoryStick,
  Loader2,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';

interface CacheStats {
  totalKeys: number;
  memoryUsage: string;
  connected: boolean;
}

interface CacheManagerProps {
  onCacheCleared?: () => void;
}

export function CacheManager({ onCacheCleared }: CacheManagerProps) {
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [pattern, setPattern] = useState('');

  // Fetch cache statistics
  const fetchStats = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/costs/cache');

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.ok) {
        setStats(data.data.stats);
      } else {
        throw new Error(data.error || 'Failed to fetch cache stats');
      }
    } catch (error) {
      console.error('Failed to fetch cache stats:', error);
      toast.error('Failed to fetch cache statistics');
      setStats({
        totalKeys: 0,
        memoryUsage: 'Unknown',
        connected: false,
      });
    } finally {
      setLoading(false);
    }
  };

  // Clear cache
  const clearCache = async (clearPattern?: string) => {
    try {
      setClearing(true);

      const url = clearPattern
        ? `/api/costs/cache?pattern=${encodeURIComponent(clearPattern)}`
        : '/api/costs/cache';

      const response = await fetch(url, { method: 'DELETE' });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.ok) {
        toast.success(data.data.message);
        await fetchStats(); // Refresh stats
        onCacheCleared?.();
      } else {
        throw new Error(data.error || 'Failed to clear cache');
      }
    } catch (error) {
      console.error('Failed to clear cache:', error);
      toast.error('Failed to clear cache');
    } finally {
      setClearing(false);
    }
  };

  // Warmup cache
  const warmupCache = async () => {
    try {
      const response = await fetch('/api/costs/cache', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'warmup' }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.ok) {
        toast.success('Cache warmup initiated');
      } else {
        throw new Error(data.error || 'Failed to warmup cache');
      }
    } catch (error) {
      console.error('Failed to warmup cache:', error);
      toast.error('Failed to warmup cache');
    }
  };

  useEffect(() => {
    fetchStats();

    // Auto-refresh stats every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Cache Management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Cache Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium">Status</span>
              </div>
              <div className="flex items-center gap-2">
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : stats?.connected ? (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <Badge
                      variant="default"
                      className="bg-green-100 text-green-800"
                    >
                      Connected
                    </Badge>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-red-600" />
                    <Badge variant="destructive">Disconnected</Badge>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium">Keys</span>
              </div>
              <div className="text-right">
                {loading ? (
                  <div className="h-4 w-8 bg-gray-200 animate-pulse rounded"></div>
                ) : (
                  <span className="text-lg font-bold">
                    {stats?.totalKeys || 0}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <MemoryStick className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium">Memory</span>
              </div>
              <div className="text-right">
                {loading ? (
                  <div className="h-4 w-12 bg-gray-200 animate-pulse rounded"></div>
                ) : (
                  <span className="text-sm font-mono">
                    {stats?.memoryUsage || 'Unknown'}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Cache Actions */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Cache Operations</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchStats}
                disabled={loading}
                className="flex items-center gap-2"
              >
                <RefreshCw
                  className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`}
                />
                Refresh Stats
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Clear All Cache */}
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="destructive"
                    className="flex items-center gap-2 w-full"
                    disabled={clearing}
                  >
                    <Trash2 className="h-4 w-4" />
                    Clear All Cache
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Clear All Cache</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will clear all cached cost data. The next requests
                      will be slower as data is fetched fresh from AWS APIs. Are
                      you sure?
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => clearCache()}
                      className="bg-red-600 hover:bg-red-700"
                    >
                      Clear All
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              {/* Warmup Cache */}
              <Button
                variant="outline"
                className="flex items-center gap-2 w-full"
                onClick={warmupCache}
              >
                <Clock className="h-4 w-4" />
                Warmup Cache
              </Button>
            </div>

            {/* Pattern-based clearing */}
            <div className="space-y-2">
              <Label htmlFor="cache-pattern">Clear by Pattern</Label>
              <div className="flex gap-2">
                <Input
                  id="cache-pattern"
                  placeholder="e.g., timeseries, summary, services"
                  value={pattern}
                  onChange={(e) => setPattern(e.target.value)}
                  className="flex-1"
                />
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="outline"
                      disabled={!pattern.trim() || clearing}
                      className="flex items-center gap-2"
                    >
                      <Trash2 className="h-4 w-4" />
                      Clear Pattern
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Clear Cache Pattern</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will clear all cache entries matching the pattern
                        &quot;{pattern}&quot;. This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => clearCache(pattern)}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        Clear Pattern
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
              <p className="text-xs text-gray-600">
                Common patterns: <code>timeseries</code>, <code>summary</code>,{' '}
                <code>services</code>, <code>forecast</code>
              </p>
            </div>
          </div>

          {/* Cache Information */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">
              Cache Information
            </h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• Cache TTL: 6-12 hours for cost data</li>
              <li>• Manual refresh bypasses cache and fetches fresh data</li>
              <li>• Cache keys are generated from request parameters</li>
              <li>• Redis fallback to memory cache if unavailable</li>
              <li>• Automatic gap filling ensures consistent data</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
