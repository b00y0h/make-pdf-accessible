'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  MoreHorizontal,
  Plus,
  Key,
  Copy,
  Trash2,
  Edit,
  Eye,
  EyeOff,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useToast } from '@/hooks/use-toast';

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  permissions: string[];
  expires_at?: string;
  last_used_at?: string;
  created_at: string;
  is_active: boolean;
  rate_limit?: number;
  usage_count: number;
}

interface CreateAPIKeyRequest {
  name: string;
  permissions: string[];
  expires_in_days?: number;
  rate_limit?: number;
}

interface UsageStats {
  total_keys: number;
  active_keys: number;
  total_usage: number;
  last_used?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const AVAILABLE_PERMISSIONS = [
  { id: 'documents.read', label: 'Read Documents', category: 'Documents' },
  { id: 'documents.upload', label: 'Upload Documents', category: 'Documents' },
  { id: 'documents.delete', label: 'Delete Documents', category: 'Documents' },
  {
    id: 'documents.process',
    label: 'Process Documents',
    category: 'Documents',
  },
  { id: 'reports.read', label: 'Read Reports', category: 'Reports' },
  { id: 'reports.download', label: 'Download Reports', category: 'Reports' },
  { id: 'queue.read', label: 'Read Queue', category: 'Queue' },
  { id: 'queue.manage', label: 'Manage Queue', category: 'Queue' },
  { id: 'users.read', label: 'Read Users (Admin)', category: 'Admin' },
  { id: 'users.manage', label: 'Manage Users (Admin)', category: 'Admin' },
  { id: 'admin', label: 'Full Admin Access', category: 'Admin' },
];

export function APIKeyManager() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const { toast } = useToast();

  // Create form state
  const [createForm, setCreateForm] = useState<CreateAPIKeyRequest>({
    name: '',
    permissions: [
      'documents.read',
      'documents.upload',
      'documents.process',
      'reports.read',
    ],
    expires_in_days: undefined,
    rate_limit: undefined,
  });

  const getAuthHeaders = async () => {
    // Get JWT token from BetterAuth
    const response = await fetch('/api/auth/token', {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to get auth token');
    }

    const { token } = await response.json();
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const loadAPIKeys = useCallback(async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api-keys`, { headers });

      if (!response.ok) {
        throw new Error('Failed to load API keys');
      }

      const keys = await response.json();
      setApiKeys(keys);
    } catch (error) {
      console.error('Error loading API keys:', error);
      toast({
        title: 'Error',
        description: 'Failed to load API keys',
        variant: 'destructive',
      });
    }
  }, [toast]);

  const loadUsageStats = useCallback(async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api-keys/usage-stats`, {
        headers,
      });

      if (!response.ok) {
        throw new Error('Failed to load usage stats');
      }

      const stats = await response.json();
      setUsageStats(stats);
    } catch (error) {
      console.error('Error loading usage stats:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAPIKeys();
    loadUsageStats();
  }, [loadAPIKeys, loadUsageStats]);

  const createAPIKey = async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api-keys`, {
        method: 'POST',
        headers,
        body: JSON.stringify(createForm),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to create API key');
      }

      const { api_key, key } = await response.json();
      setNewApiKey(key);
      setApiKeys([api_key, ...apiKeys]);

      // Reset form
      setCreateForm({
        name: '',
        permissions: [
          'documents.read',
          'documents.upload',
          'documents.process',
          'reports.read',
        ],
        expires_in_days: undefined,
        rate_limit: undefined,
      });

      toast({
        title: 'Success',
        description: 'API key created successfully',
      });
    } catch (error) {
      console.error('Error creating API key:', error);
      toast({
        title: 'Error',
        description:
          error instanceof Error ? error.message : 'Failed to create API key',
        variant: 'destructive',
      });
    }
  };

  const deleteAPIKey = async (keyId: string) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api-keys/${keyId}`, {
        method: 'DELETE',
        headers,
      });

      if (!response.ok) {
        throw new Error('Failed to delete API key');
      }

      setApiKeys(apiKeys.filter((key) => key.id !== keyId));
      toast({
        title: 'Success',
        description: 'API key deleted successfully',
      });
    } catch (error) {
      console.error('Error deleting API key:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete API key',
        variant: 'destructive',
      });
    }
  };

  const copyToClipboard = async (text: string, description: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: 'Copied',
        description: `${description} copied to clipboard`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to copy to clipboard',
        variant: 'destructive',
      });
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">Loading...</div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Usage Stats */}
      {usageStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{usageStats.total_keys}</div>
              <p className="text-sm text-muted-foreground">Total Keys</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-green-600">
                {usageStats.active_keys}
              </div>
              <p className="text-sm text-muted-foreground">Active Keys</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">
                {usageStats.total_usage.toLocaleString()}
              </div>
              <p className="text-sm text-muted-foreground">Total Usage</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-sm font-medium">
                {usageStats.last_used
                  ? formatDate(usageStats.last_used)
                  : 'Never'}
              </div>
              <p className="text-sm text-muted-foreground">Last Used</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* API Keys Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                API Keys
              </CardTitle>
              <CardDescription>
                Manage API keys for programmatic access to your account
              </CardDescription>
            </div>
            <Dialog
              open={isCreateDialogOpen}
              onOpenChange={setIsCreateDialogOpen}
            >
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create API Key
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Create API Key</DialogTitle>
                  <DialogDescription>
                    Create a new API key for programmatic access
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                  <div>
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      placeholder="My API Key"
                      value={createForm.name}
                      onChange={(e) =>
                        setCreateForm({ ...createForm, name: e.target.value })
                      }
                    />
                  </div>

                  <div>
                    <Label>Permissions</Label>
                    <div className="space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                      {AVAILABLE_PERMISSIONS.map((permission) => (
                        <div
                          key={permission.id}
                          className="flex items-center space-x-2"
                        >
                          <Checkbox
                            id={permission.id}
                            checked={createForm.permissions.includes(
                              permission.id
                            )}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setCreateForm({
                                  ...createForm,
                                  permissions: [
                                    ...createForm.permissions,
                                    permission.id,
                                  ],
                                });
                              } else {
                                setCreateForm({
                                  ...createForm,
                                  permissions: createForm.permissions.filter(
                                    (p) => p !== permission.id
                                  ),
                                });
                              }
                            }}
                          />
                          <Label htmlFor={permission.id} className="text-sm">
                            {permission.label}
                            <span className="text-xs text-muted-foreground ml-1">
                              ({permission.category})
                            </span>
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="expires">Expires In (days)</Label>
                    <Input
                      id="expires"
                      type="number"
                      placeholder="Never expires"
                      min="1"
                      max="365"
                      value={createForm.expires_in_days || ''}
                      onChange={(e) =>
                        setCreateForm({
                          ...createForm,
                          expires_in_days: e.target.value
                            ? parseInt(e.target.value)
                            : undefined,
                        })
                      }
                    />
                  </div>

                  <div>
                    <Label htmlFor="rateLimit">Rate Limit (req/min)</Label>
                    <Input
                      id="rateLimit"
                      type="number"
                      placeholder="No limit"
                      min="1"
                      max="10000"
                      value={createForm.rate_limit || ''}
                      onChange={(e) =>
                        setCreateForm({
                          ...createForm,
                          rate_limit: e.target.value
                            ? parseInt(e.target.value)
                            : undefined,
                        })
                      }
                    />
                  </div>
                </div>

                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setIsCreateDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={createAPIKey}
                    disabled={
                      !createForm.name.trim() ||
                      createForm.permissions.length === 0
                    }
                  >
                    Create Key
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>

        <CardContent>
          {apiKeys.length === 0 ? (
            <div className="text-center py-8">
              <Key className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No API Keys</h3>
              <p className="text-muted-foreground mb-4">
                You haven&apos;t created any API keys yet.
              </p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                Create your first API key
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Permissions</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys.map((apiKey) => (
                  <TableRow key={apiKey.id}>
                    <TableCell className="font-medium">{apiKey.name}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <code className="text-sm bg-muted px-2 py-1 rounded">
                          {apiKey.key_prefix}
                        </code>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            copyToClipboard(apiKey.key_prefix, 'Key prefix')
                          }
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={apiKey.is_active ? 'default' : 'secondary'}
                      >
                        {apiKey.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {apiKey.permissions.slice(0, 3).map((permission) => (
                          <Badge
                            key={permission}
                            variant="outline"
                            className="text-xs"
                          >
                            {permission}
                          </Badge>
                        ))}
                        {apiKey.permissions.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{apiKey.permissions.length - 3} more
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{apiKey.usage_count.toLocaleString()}</TableCell>
                    <TableCell>{formatDate(apiKey.created_at)}</TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => deleteAPIKey(apiKey.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* New API Key Dialog */}
      {newApiKey && (
        <Dialog open={!!newApiKey} onOpenChange={() => setNewApiKey(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>API Key Created</DialogTitle>
              <DialogDescription>
                Your API key has been created. Copy it now as it won&apos;t be
                shown again.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div>
                <Label>Your new API key</Label>
                <div className="flex items-center gap-2 mt-1">
                  <Input
                    readOnly
                    value={newApiKey}
                    className="font-mono text-sm"
                  />
                  <Button
                    size="sm"
                    onClick={() => copyToClipboard(newApiKey, 'API key')}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex">
                  <div className="text-yellow-600 text-sm">
                    <strong>Important:</strong> This is the only time
                    you&apos;ll see this key. Store it securely as you
                    won&apos;t be able to view it again.
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={() => setNewApiKey(null)}>
                I&apos;ve copied the key
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
