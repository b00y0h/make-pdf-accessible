import React from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Settings as SettingsIcon,
  User,
  Bell,
  Shield,
  Palette,
  Zap,
  HardDrive,
  Users,
  Key,
  AlertTriangle,
} from 'lucide-react';
import { Separator } from '@/components/ui/separator';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and application preferences
        </p>
      </div>

      <div className="grid gap-6">
        {/* Account Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Account Settings
            </CardTitle>
            <CardDescription>
              Manage your account information and preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">Full Name</label>
                <Input placeholder="John Doe" defaultValue="John Doe" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Email Address</label>
                <Input
                  placeholder="john@example.com"
                  defaultValue="admin@example.com"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Organization</label>
              <Input placeholder="Company Name" defaultValue="AccessPDF Corp" />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">
                  Two-Factor Authentication
                </label>
                <p className="text-sm text-muted-foreground">
                  Add an extra layer of security to your account
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="success">Enabled</Badge>
                <Switch defaultChecked />
              </div>
            </div>
            <Button>Save Changes</Button>
          </CardContent>
        </Card>

        {/* Processing Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Processing Settings
            </CardTitle>
            <CardDescription>
              Configure how documents are processed for accessibility
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">
                  Auto-process uploads
                </label>
                <p className="text-sm text-muted-foreground">
                  Automatically start processing when documents are uploaded
                </p>
              </div>
              <Switch defaultChecked />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">
                  AI Alt-text generation
                </label>
                <p className="text-sm text-muted-foreground">
                  Use AI to automatically generate alternative text for images
                </p>
              </div>
              <Switch defaultChecked />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">
                  Advanced OCR processing
                </label>
                <p className="text-sm text-muted-foreground">
                  Use advanced OCR for better text extraction from scanned
                  documents
                </p>
              </div>
              <Switch defaultChecked />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                Default WCAG compliance level
              </label>
              <select className="w-full p-2 border rounded-md">
                <option value="A">WCAG A</option>
                <option value="AA" selected>
                  WCAG AA
                </option>
                <option value="AAA">WCAG AAA</option>
              </select>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Processing timeout (minutes)
                </label>
                <Input type="number" placeholder="30" defaultValue="30" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Max file size (MB)
                </label>
                <Input type="number" placeholder="50" defaultValue="50" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
            <CardDescription>
              Choose how you want to be notified about processing updates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">
                  Email notifications
                </label>
                <p className="text-sm text-muted-foreground">
                  Receive email updates about document processing
                </p>
              </div>
              <Switch defaultChecked />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">
                  Processing completion
                </label>
                <p className="text-sm text-muted-foreground">
                  Get notified when document processing is complete
                </p>
              </div>
              <Switch defaultChecked />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">
                  Processing failures
                </label>
                <p className="text-sm text-muted-foreground">
                  Get notified when document processing fails
                </p>
              </div>
              <Switch defaultChecked />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <label className="text-sm font-medium">Weekly summary</label>
                <p className="text-sm text-muted-foreground">
                  Receive a weekly summary of processing activity
                </p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        {/* Team Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Team Management
            </CardTitle>
            <CardDescription>
              Manage team members and their access permissions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Team Members</h4>
                <p className="text-sm text-muted-foreground">
                  5 of 10 seats used
                </p>
              </div>
              <Button>Invite Members</Button>
            </div>

            <div className="space-y-3">
              {[
                {
                  name: 'John Doe',
                  email: 'john@example.com',
                  role: 'Admin',
                  status: 'Active',
                },
                {
                  name: 'Jane Smith',
                  email: 'jane@example.com',
                  role: 'Editor',
                  status: 'Active',
                },
                {
                  name: 'Bob Johnson',
                  email: 'bob@example.com',
                  role: 'Viewer',
                  status: 'Pending',
                },
              ].map((member, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div>
                    <p className="font-medium">{member.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {member.email}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        member.status === 'Active' ? 'success' : 'warning'
                      }
                    >
                      {member.status}
                    </Badge>
                    <Badge variant="secondary">{member.role}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* API Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Settings
            </CardTitle>
            <CardDescription>Manage API keys and integrations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">API Access</h4>
                <p className="text-sm text-muted-foreground">
                  Enable API access for your applications
                </p>
              </div>
              <Switch />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">Production API Key</p>
                  <p className="text-sm text-muted-foreground font-mono">
                    ak_prod_••••••••••••••••
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    Regenerate
                  </Button>
                  <Button variant="outline" size="sm">
                    Copy
                  </Button>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">Development API Key</p>
                  <p className="text-sm text-muted-foreground font-mono">
                    ak_dev_••••••••••••••••
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    Regenerate
                  </Button>
                  <Button variant="outline" size="sm">
                    Copy
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Storage & Billing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Storage & Billing
            </CardTitle>
            <CardDescription>
              Monitor your storage usage and billing information
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Storage Used</span>
                  <span className="text-sm">2.3 GB / 10 GB</span>
                </div>
                <div className="h-2 bg-secondary rounded-full">
                  <div
                    className="h-2 bg-primary rounded-full"
                    style={{ width: '23%' }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    Documents This Month
                  </span>
                  <span className="text-sm">247 / 1000</span>
                </div>
                <div className="h-2 bg-secondary rounded-full">
                  <div
                    className="h-2 bg-primary rounded-full"
                    style={{ width: '24.7%' }}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
              <div>
                <h4 className="font-medium">Current Plan: Professional</h4>
                <p className="text-sm text-muted-foreground">
                  $99/month • Next billing: Feb 1, 2024
                </p>
              </div>
              <Button variant="outline">Upgrade Plan</Button>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-red-200 dark:border-red-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertTriangle className="h-5 w-5" />
              Danger Zone
            </CardTitle>
            <CardDescription>
              Irreversible actions that affect your account
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-red-200 dark:border-red-900 rounded-lg">
              <div>
                <h4 className="font-medium text-red-600 dark:text-red-400">
                  Delete Account
                </h4>
                <p className="text-sm text-muted-foreground">
                  Permanently delete your account and all associated data
                </p>
              </div>
              <Button variant="destructive">Delete Account</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
