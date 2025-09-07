'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Eye, EyeOff, Mail, Lock, ArrowRight, Shield, Zap, Users } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { getAuthUrls } from '@/lib/auth-config'

const features = [
  {
    icon: Shield,
    title: 'WCAG Compliant',
    description: 'Automated accessibility compliance for all your PDFs',
  },
  {
    icon: Zap,
    title: 'Lightning Fast',
    description: 'Process hundreds of documents in minutes',
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description: 'Work together with your team on accessibility projects',
  },
]

const testimonials = [
  {
    quote: "AccessPDF has transformed our document workflow. We've made all our training materials accessible in record time.",
    author: "Sarah Johnson",
    role: "Accessibility Manager",
    company: "TechCorp",
  },
  {
    quote: "The automated alt-text generation is incredibly accurate. It's saved us hundreds of hours of manual work.",
    author: "Michael Chen",
    role: "Content Director",
    company: "EduPlatform",
  },
]

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()
  const { login, isAuthenticated, isLoading: authLoading } = useAuth()

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, router])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    // For email/password, still redirect to Cognito Hosted UI
    // In production, you could implement direct auth here
    login()
  }

  const handleSSOLogin = (provider: string) => {
    // All providers go through Cognito Hosted UI
    // The identity provider (Google) is handled by Cognito
    login()
  }

  const handleDirectLogin = () => {
    login()
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50 flex items-center justify-center">
        <div className="text-center">
          <Shield className="h-12 w-12 text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      <div className="grid lg:grid-cols-2 min-h-screen">
        {/* Left Side - Hero Content */}
        <div className="flex flex-col justify-center px-8 py-12 lg:px-16">
          <div className="max-w-md mx-auto lg:mx-0">
            {/* Logo */}
            <div className="flex items-center gap-3 mb-8">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  AccessPDF
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Admin Dashboard
                </p>
              </div>
            </div>

            {/* Hero Content */}
            <div className="space-y-6 mb-8">
              <div>
                <h2 className="text-4xl font-bold text-gray-900 dark:text-white leading-tight">
                  Make your PDFs
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-600">
                    {' '}accessible
                  </span>
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-300 mt-4">
                  Automated WCAG compliance, intelligent alt-text generation, and seamless team collaboration.
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">WCAG 2.1 AA</Badge>
                <Badge variant="secondary">508 Compliant</Badge>
                <Badge variant="secondary">AI-Powered</Badge>
              </div>
            </div>

            {/* Features */}
            <div className="space-y-4 mb-8">
              {features.map((feature, index) => {
                const Icon = feature.icon
                return (
                  <div key={index} className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
                      <Icon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">
                        {feature.title}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Testimonial */}
            <div className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 border border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-300 italic mb-2">
                "{testimonials[0].quote}"
              </p>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                <strong>{testimonials[0].author}</strong>, {testimonials[0].role} at {testimonials[0].company}
              </div>
            </div>
          </div>
        </div>

        {/* Right Side - Login Form */}
        <div className="flex flex-col justify-center px-8 py-12 lg:px-16 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
          <div className="max-w-sm mx-auto w-full">
            <Card className="border-0 shadow-xl">
              <CardHeader className="space-y-1 text-center">
                <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
                <CardDescription>
                  Sign in to your AccessPDF admin dashboard
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* SSO Buttons - Priority Order */}
                <div className="space-y-3 mb-6">
                  {/* Google - Primary, Large Button */}
                  <Button
                    variant="outline"
                    size="lg"
                    className="w-full h-12 text-base font-medium"
                    onClick={handleDirectLogin}
                  >
                    <svg className="mr-3 h-5 w-5" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Continue with Google
                  </Button>

                  {/* Other SSO Options - Smaller */}
                  <div className="grid grid-cols-3 gap-2">
                    <Button
                      variant="outline"
                      className="h-10"
                      onClick={handleDirectLogin}
                      title="Sign in with GitHub"
                    >
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 0C5.374 0 0 5.373 0 12 0 17.302 3.438 21.8 8.207 23.387c.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
                      </svg>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-10"
                      onClick={handleDirectLogin}
                      title="Sign in with Microsoft"
                    >
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z"/>
                      </svg>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-10"
                      onClick={handleDirectLogin}
                      title="Sign in with Apple"
                    >
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"/>
                      </svg>
                    </Button>
                  </div>
                </div>

                {/* Divider */}
                <div className="relative mb-6">
                  <Separator />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="bg-white px-2 text-sm text-gray-500">or</span>
                  </div>
                </div>

                {/* Email/Password Form */}
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        type="email"
                        placeholder="Email address"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="pl-10 pr-10"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      'Signing in...'
                    ) : (
                      <>
                        Sign in
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </form>
                
                {/* Links */}
                <div className="mt-6 space-y-3 text-center text-sm">
                  <div className="flex justify-center space-x-4 text-blue-600">
                    <button onClick={handleDirectLogin} className="hover:text-blue-500">
                      Use single sign-on
                    </button>
                    <span className="text-gray-300">•</span>
                    <button onClick={handleDirectLogin} className="hover:text-blue-500">
                      Reset password
                    </button>
                  </div>
                  <p className="text-gray-600 dark:text-gray-400">
                    Don't have an account?{' '}
                    <button
                      onClick={handleDirectLogin}
                      className="font-medium text-blue-600 hover:text-blue-500"
                    >
                      Create account
                    </button>
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* OAuth Information */}
            <div className="mt-6 text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                <strong>Authentication:</strong>
                <br />Uses AWS Cognito with Google OAuth
                <br />All options redirect to secure hosted UI
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
