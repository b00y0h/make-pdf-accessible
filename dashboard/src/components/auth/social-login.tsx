'use client';

import { Button } from '@/components/ui/button';
import { auth, type SocialProvider } from '@/lib/auth';
import { useState } from 'react';

interface SocialLoginProps {
  redirectTo?: string;
  className?: string;
}

const socialProviders: Array<{
  provider: SocialProvider;
  name: string;
  icon: string;
  bgColor: string;
  textColor: string;
}> = [
  {
    provider: 'google',
    name: 'Google',
    icon: '🔍',
    bgColor: 'bg-white border border-gray-300 hover:bg-gray-50',
    textColor: 'text-gray-700',
  },
  {
    provider: 'github',
    name: 'GitHub',
    icon: '🐙',
    bgColor: 'bg-gray-900 hover:bg-gray-800',
    textColor: 'text-white',
  },
  // {
  //   provider: 'apple',
  //   name: 'Apple',
  //   icon: '🍎',
  //   bgColor: 'bg-black hover:bg-gray-900',
  //   textColor: 'text-white',
  // },
  {
    provider: 'discord',
    name: 'Discord',
    icon: '🎮',
    bgColor: 'bg-indigo-600 hover:bg-indigo-700',
    textColor: 'text-white',
  },
  // {
  //   provider: 'facebook',
  //   name: 'Facebook',
  //   icon: '📘',
  //   bgColor: 'bg-blue-600 hover:bg-blue-700',
  //   textColor: 'text-white',
  // },
];

export function SocialLogin({ redirectTo, className }: SocialLoginProps) {
  const [loading, setLoading] = useState<SocialProvider | null>(null);

  const handleSocialLogin = async (provider: SocialProvider) => {
    try {
      setLoading(provider);
      await auth.signInWithSocial(provider, redirectTo);
    } catch (error) {
      console.error(`Failed to sign in with ${provider}:`, error);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or continue with
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {socialProviders.map(({ provider, name, icon, bgColor, textColor }) => (
          <Button
            key={provider}
            variant="outline"
            onClick={() => handleSocialLogin(provider)}
            disabled={loading !== null}
            className={`${bgColor} ${textColor} w-full`}
          >
            {loading === provider ? (
              <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <span className="mr-2">{icon}</span>
            )}
            Continue with {name}
          </Button>
        ))}
      </div>
    </div>
  );
}
