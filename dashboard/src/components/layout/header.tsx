'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Bell, Search, User, Settings, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { useSession, signOut } from '@/lib/auth-client';

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const [isClient, setIsClient] = useState(false);
  const { data: session, isPending } = useSession();

  // Handle hydration
  useEffect(() => {
    setIsClient(true);
  }, []);

  const user = session?.user;
  const userWithRole = user as any;
  const isAdmin = userWithRole?.role === 'admin';

  const logout = async () => {
    await signOut();
    window.location.href = '/sign-in';
  };

  // Show loading during SSR and hydration
  if (!isClient) {
    return (
      <header className="flex h-16 items-center justify-between border-b bg-background px-6">
        <div className="flex items-center gap-4">
          {title && <h1 className="text-xl font-semibold">{title}</h1>}
        </div>
        <div className="flex items-center gap-4">
          <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
        </div>
      </header>
    );
  }

  const getUserInitials = () => {
    if (user?.name) {
      return user.name
        .split(' ')
        .map((n) => n.charAt(0))
        .join('')
        .toUpperCase();
    }
    return user?.email?.charAt(0)?.toUpperCase() || 'U';
  };

  // Show loading state while auth is initializing
  if (isPending) {
    return (
      <header className="flex h-16 items-center justify-between border-b bg-background px-6">
        <div className="flex items-center gap-4">
          {title && <h1 className="text-xl font-semibold">{title}</h1>}
        </div>
        <div className="flex items-center gap-4">
          <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
        </div>
      </header>
    );
  }

  return (
    <header className="flex h-16 items-center justify-between border-b bg-background px-6">
      <div className="flex items-center gap-4">
        {title && <h1 className="text-xl font-semibold">{title}</h1>}
      </div>

      <div className="flex items-center gap-4">
        {/* Admin Link - Only visible to admin users */}
        {isAdmin && (
          <Link href="/admin">
            <Button variant="outline" size="sm" className="gap-2">
              <ShieldCheck className="h-4 w-4" />
              Admin Panel
            </Button>
          </Link>
        )}

        {/* Search */}
        <div className="relative hidden md:block">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search documents..." className="w-64 pl-8" />
        </div>

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          <Badge
            variant="destructive"
            className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 text-xs"
          >
            3
          </Badge>
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarImage src={user?.image || undefined} alt="User avatar" />
                <AvatarFallback>{getUserInitials()}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">
                  {user?.name || 'No name set'}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email}
                </p>
                {userWithRole?.role && (
                  <p className="text-xs leading-none text-muted-foreground capitalize">
                    {userWithRole.role} User
                  </p>
                )}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />

            {/* Admin-only menu item */}
            {isAdmin && (
              <>
                <DropdownMenuItem asChild>
                  <Link href="/admin" className="w-full cursor-pointer">
                    <ShieldCheck className="mr-2 h-4 w-4" />
                    Admin Panel
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}

            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuItem>Support</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-red-600">
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
