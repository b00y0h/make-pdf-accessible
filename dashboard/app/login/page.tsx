'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Eye, EyeOff, Mail, Lock, ArrowRight, Shield, Zap, Users } from 'lucide-react'

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

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    
    // Mock login - in a real app this would call your auth API
    setTimeout(() => {
      setIsLoading(false)
      router.push('/dashboard')
    }, 1000)
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
                  <div className="flex items-center justify-between">
                    <label className="flex items-center space-x-2 text-sm">
                      <input type="checkbox" className="rounded" />
                      <span>Remember me</span>
                    </label>
                    <Link
                      href="/forgot-password"
                      className="text-sm text-blue-600 hover:text-blue-500"
                    >
                      Forgot password?
                    </Link>
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
                
                <div className="mt-6 text-center">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Don't have an account?{' '}
                    <Link
                      href="/signup"
                      className="font-medium text-blue-600 hover:text-blue-500"
                    >
                      Contact sales
                    </Link>
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Demo Credentials */}
            <div className="mt-6 text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                <strong>Demo credentials:</strong>
                <br />Email: admin@example.com
                <br />Password: demo123
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
