'use client';

import React, { useEffect, useState } from 'react';
import { User, LogOut } from 'lucide-react';

interface UserSession {
  user: {
    id: string;
    email: string;
    name?: string;
    image?: string;
  };
}

export default function UserAvatar() {
  const [session, setSession] = useState<UserSession | null>(null);
  const [showMenu, setShowMenu] = useState(false);

  useEffect(() => {
    // Check for Better Auth session
    const checkAuth = async () => {
      try {
        const response = await fetch('http://localhost:3001/api/auth/get-session', {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        if (response.ok) {
          const sessionData = await response.json();
          if (sessionData && sessionData.session && sessionData.user) {
            setSession({ user: sessionData.user });
          }
        }
      } catch (error) {
        console.log('Not authenticated');
      }
    };
    
    checkAuth();
  }, []);

  const handleSignOut = async () => {
    // Sign out from Better Auth
    try {
      await fetch('http://localhost:3001/api/auth/sign-out', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Sign out error:', error);
    }
    setSession(null);
    // Reload page to reset state
    window.location.reload();
  };

  if (!session) {
    return null;
  }

  const initials = session.user.name 
    ? session.user.name.split(' ').map(n => n[0]).join('').toUpperCase()
    : session.user.email[0].toUpperCase();

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        {session.user.image ? (
          <img 
            src={session.user.image} 
            alt={session.user.name || session.user.email}
            className="w-8 h-8 rounded-full"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center text-white text-sm font-medium">
            {initials}
          </div>
        )}
        <span className="text-sm font-medium text-gray-700 hidden md:block">
          {session.user.name || session.user.email}
        </span>
      </button>

      {showMenu && (
        <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          <div className="px-4 py-2 border-b border-gray-200">
            <p className="text-sm font-medium text-gray-900">{session.user.name || 'User'}</p>
            <p className="text-xs text-gray-500">{session.user.email}</p>
          </div>
          <a
            href="http://localhost:3001/dashboard"
            className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <User className="w-4 h-4 mr-2" />
            Dashboard
          </a>
          <button
            onClick={handleSignOut}
            className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}