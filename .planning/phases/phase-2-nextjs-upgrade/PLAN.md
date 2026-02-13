# Phase 2: Next.js Major Upgrade (web/) - Execution Plan

**Phase:** 2
**Status:** Ready for Execution
**Created:** 2026-02-13
**Confidence:** HIGH (small codebase, well-documented migration path)

---

## Objective

Upgrade web/ from Next.js 13.4.19 to 15.5.10+ to resolve 58 security vulnerabilities while maintaining full functionality.

---

## Prerequisites

- [ ] Phase 1 completed (direct dependency updates)
- [ ] Clean working directory (`git status` shows no uncommitted changes)
- [ ] Sufficient disk space for package updates (~500MB)
- [ ] Node.js 18.17.0+ available

---

## Prompts

### Prompt 1: Run Next.js Codemod

**Goal:** Update core Next.js dependencies and configuration using official codemod

```
cd web/
npx @next/codemod@latest upgrade 15
```

**Expected Changes:**
- `next`: 13.4.19 → 15.5.10+
- `react`: 18.2.0 → 19.x
- `react-dom`: 18.2.0 → 19.x
- `next.config.js`: Remove `experimental.appDir` and `swcMinify` (now defaults)

**Verification:**
```bash
cat web/package.json | grep -E '"next"|"react"|"react-dom"'
cat web/next.config.js
```

**Commit:** `feat(web): upgrade Next.js 13 to 15 via codemod`

---

### Prompt 2: Align React Version with Dashboard

**Goal:** Use same React versions as dashboard for consistency

**Note:** Dashboard uses React 19 RC with @types/react@18 (works fine). The codemod may install stable React 19. Either version is acceptable - prioritize what the codemod installs.

**If codemod installed stable React 19:**
```bash
cd web/
pnpm add -D @types/react@^19.0.0 @types/react-dom@^19.0.0 @types/node@^22.0.0
```

**If you prefer RC to match dashboard exactly:**
```bash
cd web/
pnpm add react@19.0.0-rc.1 react-dom@19.0.0-rc.1
pnpm add -D @types/react@^18.2.45 @types/react-dom@^18.2.18 @types/node@^20.10.5
```

**Verification:**
```bash
pnpm -F pdf-accessibility-web type-check
```

**Commit:** `chore(web): update TypeScript definitions for React 19`

---

### Prompt 3: Update Testing Library for React 19

**Goal:** Upgrade @testing-library/react to v16 for React 19 compatibility

**Changes:**
```json
{
  "devDependencies": {
    "@testing-library/react": "^16.3.2"
  }
}
```

**Commands:**
```bash
cd web/
pnpm add -D @testing-library/react@^16.3.2
```

**Verification:**
```bash
pnpm -F pdf-accessibility-web test
```

**Commit:** `chore(web): upgrade testing-library for React 19`

---

### Prompt 4: Fix Providers.tsx QueryClient Pattern

**Goal:** Move QueryClient instantiation inside component to avoid SSR hydration issues

**File:** `web/components/Providers.tsx`

**Current Code (lines 7-27):**
```typescript
const queryClient = new QueryClient({...}); // Outside component
```

**Replace With:**
```typescript
'use client';

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 1000 * 60 * 5,
            retry: (failureCount, error) => {
              if (error && typeof error === 'object' && 'status' in error) {
                const status = (error as { status: number }).status;
                if (status >= 400 && status < 500) {
                  return false;
                }
              }
              return failureCount < 3;
            },
            retryDelay: (attemptIndex) =>
              Math.min(1000 * 2 ** attemptIndex, 30000),
          },
          mutations: {
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

**Key Changes:**
1. Move `QueryClient` instantiation inside component with `useState`
2. Change `children: any` to `children: React.ReactNode`

**Verification:**
```bash
pnpm -F pdf-accessibility-web type-check
```

**Commit:** `fix(web): move QueryClient inside component for SSR safety`

---

### Prompt 5: Fix layout.tsx Types

**Goal:** Update RootLayout with proper React 19 types and metadata

**File:** `web/app/layout.tsx`

**Replace With:**
```typescript
import React from 'react';
import type { Metadata } from 'next';
import { Providers } from '../components/Providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'PDF Accessibility',
  description: 'AI-powered PDF accessibility processing',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

**Changes:**
1. Add explicit `Metadata` type import and usage
2. Change `children: any` to `children: React.ReactNode`
3. Update metadata values

**Commit:** `fix(web): add proper types to RootLayout`

---

### Prompt 6: Update ESLint Configuration

**Goal:** Update ESLint dependencies for Next.js 15 compatibility

**Changes:**
```json
{
  "devDependencies": {
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.5.10"
  }
}
```

**Commands:**
```bash
cd web/
pnpm add -D eslint@^9.0.0 eslint-config-next@^15.5.10
```

**Note:** If ESLint flat config issues arise, add to `.env.local`:
```
ESLINT_USE_FLAT_CONFIG=false
```

**Verification:**
```bash
pnpm -F pdf-accessibility-web lint
```

**Commit:** `chore(web): upgrade ESLint for Next.js 15`

---

### Prompt 7: Update next.config.js

**Goal:** Remove deprecated configuration options

**File:** `web/next.config.js`

**Replace With:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // API rewrites for development and production
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.API_BASE_URL
          ? `${process.env.API_BASE_URL}/:path*`
          : 'http://localhost:8000/:path*',
      },
    ];
  },

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

**Changes:**
- Remove `swcMinify: true` (default in Next.js 15)
- Remove `experimental.appDir` (default in Next.js 15)

**Commit:** `chore(web): remove deprecated Next.js config options`

---

### Prompt 8: Full Verification

**Goal:** Verify complete migration success

**Commands:**
```bash
# Install dependencies
pnpm install

# Type checking
pnpm -F pdf-accessibility-web type-check

# Linting
pnpm -F pdf-accessibility-web lint

# Tests
pnpm -F pdf-accessibility-web test

# Build
pnpm -F pdf-accessibility-web build

# Dev server smoke test
pnpm -F pdf-accessibility-web dev &
sleep 10
curl -s http://localhost:3000 | head -20
pkill -f "next dev"
```

**Success Criteria:**
- [ ] `pnpm install` completes without errors
- [ ] `type-check` passes
- [ ] `lint` passes
- [ ] `test` passes
- [ ] `build` completes successfully
- [ ] Dev server starts and serves pages

---

## Verification Matrix

| Check | Command | Expected |
|-------|---------|----------|
| Deps Install | `pnpm install` | Exit 0 |
| Types | `pnpm -F pdf-accessibility-web type-check` | Exit 0 |
| Lint | `pnpm -F pdf-accessibility-web lint` | Exit 0 |
| Tests | `pnpm -F pdf-accessibility-web test` | Exit 0 |
| Build | `pnpm -F pdf-accessibility-web build` | Exit 0, .next/ created |
| Dev | `pnpm -F pdf-accessibility-web dev` | Server on port 3000 |

---

## Rollback Plan

If migration fails:
```bash
git checkout HEAD~N -- web/  # Revert to before changes
pnpm install                  # Restore previous dependencies
```

For incremental approach (13 → 14 → 15), see RESEARCH.md.

---

## Files Modified Summary

| File | Change Type |
|------|-------------|
| `web/package.json` | Dependencies upgraded |
| `web/next.config.js` | Config simplified |
| `web/components/Providers.tsx` | QueryClient pattern fixed |
| `web/app/layout.tsx` | Types improved |
| `web/pnpm-lock.yaml` | Regenerated |

---

## Notes

1. **TanStack Query hooks already use v5 syntax** - No changes needed to `useDocumentPolling.ts` or `useS3Upload.ts`
2. **All pages are client components** - No async API migration required
3. **lucide-react is at 0.279.0** - Safe version, no upgrade needed
4. **react-dropzone** may show peer dep warning for React 19 - acceptable, works fine
