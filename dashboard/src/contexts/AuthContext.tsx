'use client'

import React, { createContext, useContext, useCallback, useEffect, useState, ReactNode } from 'react'
import axios, { AxiosInstance } from 'axios'
import { jwtDecode } from 'jwt-decode'
import { authConfig, getAuthUrls } from '@/lib/auth-config'

// Types
export interface User {
  sub: string
  email: string
  given_name?: string
  family_name?: string
  picture?: string
  'cognito:groups'?: string[]
  'cognito:username': string
}

export interface AuthTokens {
  accessToken: string
  idToken: string
  refreshToken: string
  expiresAt: number
}

interface AuthContextType {
  user: User | null
  tokens: AuthTokens | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (redirectTo?: string) => void
  logout: () => void
  getAccessToken: () => Promise<string | null>
  refreshTokens: () => Promise<boolean>
  apiClient: AxiosInstance
}

const AuthContext = createContext<AuthContextType | null>(null)

// Token storage utilities
const TOKEN_STORAGE_KEY = 'accesspdf_tokens'
const USER_STORAGE_KEY = 'accesspdf_user'

const storeTokens = (tokens: AuthTokens) => {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens))
  }
}

const getStoredTokens = (): AuthTokens | null => {
  if (typeof window === 'undefined') return null
  try {
    const stored = sessionStorage.getItem(TOKEN_STORAGE_KEY)
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

const clearStoredTokens = () => {
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY)
    sessionStorage.removeItem(USER_STORAGE_KEY)
  }
}

const storeUser = (user: User) => {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
  }
}

const getStoredUser = (): User | null => {
  if (typeof window === 'undefined') return null
  try {
    const stored = sessionStorage.getItem(USER_STORAGE_KEY)
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

// JWT utilities
const isTokenExpired = (token: string): boolean => {
  try {
    const decoded = jwtDecode(token)
    if (!decoded.exp) return true
    return Date.now() >= decoded.exp * 1000 - 30000 // 30 seconds buffer
  } catch {
    return true
  }
}

const parseJwtUser = (idToken: string): User | null => {
  try {
    const decoded = jwtDecode<any>(idToken)
    return {
      sub: decoded.sub,
      email: decoded.email,
      given_name: decoded.given_name,
      family_name: decoded.family_name,
      picture: decoded.picture,
      'cognito:groups': decoded['cognito:groups'],
      'cognito:username': decoded['cognito:username'],
    }
  } catch (error) {
    console.error('Failed to parse JWT user:', error)
    return null
  }
}\n\nexport const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {\n  const [user, setUser] = useState<User | null>(null)\n  const [tokens, setTokens] = useState<AuthTokens | null>(null)\n  const [isLoading, setIsLoading] = useState(true)\n\n  // Create axios instance with interceptor\n  const apiClient = axios.create({\n    baseURL: authConfig.apiBaseUrl,\n    timeout: 10000,\n  })\n\n  const getAccessToken = useCallback(async (): Promise<string | null> => {\n    const currentTokens = tokens || getStoredTokens()\n    if (!currentTokens) return null\n\n    // Check if access token is still valid\n    if (!isTokenExpired(currentTokens.accessToken)) {\n      return currentTokens.accessToken\n    }\n\n    // Try to refresh the token\n    const refreshed = await refreshTokens()\n    if (refreshed && tokens) {\n      return tokens.accessToken\n    }\n\n    return null\n  }, [tokens])\n\n  const refreshTokens = useCallback(async (): Promise<boolean> => {\n    const currentTokens = tokens || getStoredTokens()\n    if (!currentTokens?.refreshToken) {\n      console.error('No refresh token available')\n      return false\n    }\n\n    try {\n      const authUrls = getAuthUrls()\n      const response = await fetch(authUrls.tokenUrl, {\n        method: 'POST',\n        headers: {\n          'Content-Type': 'application/x-www-form-urlencoded',\n        },\n        body: new URLSearchParams({\n          grant_type: 'refresh_token',\n          client_id: authConfig.userPoolWebClientId,\n          refresh_token: currentTokens.refreshToken,\n        }),\n      })\n\n      if (!response.ok) {\n        throw new Error('Failed to refresh token')\n      }\n\n      const data = await response.json()\n      const newTokens: AuthTokens = {\n        accessToken: data.access_token,\n        idToken: data.id_token,\n        refreshToken: currentTokens.refreshToken, // Keep existing refresh token\n        expiresAt: Date.now() + (data.expires_in * 1000),\n      }\n\n      const newUser = parseJwtUser(newTokens.idToken)\n      if (!newUser) {\n        throw new Error('Failed to parse user from refreshed token')\n      }\n\n      setTokens(newTokens)\n      setUser(newUser)\n      storeTokens(newTokens)\n      storeUser(newUser)\n\n      return true\n    } catch (error) {\n      console.error('Failed to refresh tokens:', error)\n      logout()\n      return false\n    }\n  }, [tokens])\n\n  const login = useCallback((redirectTo?: string) => {\n    const authUrls = getAuthUrls()\n    const state = redirectTo ? btoa(redirectTo) : undefined\n    const loginUrl = state \n      ? `${authUrls.loginUrl}&state=${encodeURIComponent(state)}`\n      : authUrls.loginUrl\n    \n    window.location.href = loginUrl\n  }, [])\n\n  const logout = useCallback(() => {\n    setUser(null)\n    setTokens(null)\n    clearStoredTokens()\n    \n    // Redirect to Cognito logout\n    const authUrls = getAuthUrls()\n    window.location.href = authUrls.logoutUrl\n  }, [])\n\n  // Set up axios interceptor\n  useEffect(() => {\n    const requestInterceptor = apiClient.interceptors.request.use(\n      async (config) => {\n        const accessToken = await getAccessToken()\n        if (accessToken) {\n          config.headers.Authorization = `Bearer ${accessToken}`\n        }\n        return config\n      },\n      (error) => Promise.reject(error)\n    )\n\n    const responseInterceptor = apiClient.interceptors.response.use(\n      (response) => response,\n      async (error) => {\n        if (error.response?.status === 401) {\n          // Try to refresh token and retry\n          const refreshed = await refreshTokens()\n          if (refreshed && error.config && !error.config._retry) {\n            error.config._retry = true\n            const newToken = await getAccessToken()\n            if (newToken) {\n              error.config.headers.Authorization = `Bearer ${newToken}`\n              return apiClient.request(error.config)\n            }\n          }\n          \n          // If refresh failed or this is a retry, logout\n          logout()\n        }\n        return Promise.reject(error)\n      }\n    )\n\n    return () => {\n      apiClient.interceptors.request.eject(requestInterceptor)\n      apiClient.interceptors.response.eject(responseInterceptor)\n    }\n  }, [getAccessToken, refreshTokens, logout])\n\n  // Initialize auth state on mount\n  useEffect(() => {\n    const initializeAuth = async () => {\n      try {\n        const storedTokens = getStoredTokens()\n        const storedUser = getStoredUser()\n\n        if (storedTokens && storedUser) {\n          // Check if tokens are still valid\n          if (!isTokenExpired(storedTokens.idToken)) {\n            setTokens(storedTokens)\n            setUser(storedUser)\n          } else {\n            // Try to refresh\n            setTokens(storedTokens) // Set temporarily for refresh\n            const refreshed = await refreshTokens()\n            if (!refreshed) {\n              clearStoredTokens()\n            }\n          }\n        }\n      } catch (error) {\n        console.error('Failed to initialize auth:', error)\n        clearStoredTokens()\n      } finally {\n        setIsLoading(false)\n      }\n    }\n\n    initializeAuth()\n  }, [refreshTokens])\n\n  const isAuthenticated = !!(user && tokens)\n\n  const contextValue: AuthContextType = {\n    user,\n    tokens,\n    isLoading,\n    isAuthenticated,\n    login,\n    logout,\n    getAccessToken,\n    refreshTokens,\n    apiClient,\n  }\n\n  return (\n    <AuthContext.Provider value={contextValue}>\n      {children}\n    </AuthContext.Provider>\n  )\n}\n\nexport const useAuth = (): AuthContextType => {\n  const context = useContext(AuthContext)\n  if (!context) {\n    throw new Error('useAuth must be used within an AuthProvider')\n  }\n  return context\n}\n\n// Helper hook for handling OAuth callback\nexport const useAuthCallback = () => {\n  const [isProcessing, setIsProcessing] = useState(false)\n  const [error, setError] = useState<string | null>(null)\n\n  const handleCallback = useCallback(async (code: string, state?: string) => {\n    setIsProcessing(true)\n    setError(null)\n\n    try {\n      const authUrls = getAuthUrls()\n      const response = await fetch(authUrls.tokenUrl, {\n        method: 'POST',\n        headers: {\n          'Content-Type': 'application/x-www-form-urlencoded',\n        },\n        body: new URLSearchParams({\n          grant_type: 'authorization_code',\n          client_id: authConfig.userPoolWebClientId,\n          code,\n          redirect_uri: authConfig.oauth.redirectSignIn,\n        }),\n      })\n\n      if (!response.ok) {\n        throw new Error('Failed to exchange code for tokens')\n      }\n\n      const data = await response.json()\n      const tokens: AuthTokens = {\n        accessToken: data.access_token,\n        idToken: data.id_token,\n        refreshToken: data.refresh_token,\n        expiresAt: Date.now() + (data.expires_in * 1000),\n      }\n\n      const user = parseJwtUser(tokens.idToken)\n      if (!user) {\n        throw new Error('Failed to parse user from token')\n      }\n\n      // Store tokens and user\n      storeTokens(tokens)\n      storeUser(user)\n\n      // Redirect to intended destination or dashboard\n      const redirectTo = state ? atob(state) : '/dashboard'\n      window.location.href = redirectTo\n    } catch (error) {\n      console.error('OAuth callback error:', error)\n      setError(error instanceof Error ? error.message : 'Authentication failed')\n    } finally {\n      setIsProcessing(false)\n    }\n  }, [])\n\n  return { handleCallback, isProcessing, error }\n}