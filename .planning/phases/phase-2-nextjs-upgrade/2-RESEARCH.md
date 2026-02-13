# Phase 2: Next.js Major Upgrade (web/) - Research

**Research Date:** 2026-02-13
**Phase Goal:** Upgrade web/ from Next.js 13.4.19 to 15.5.10+ to resolve 58 security vulnerabilities
**Confidence Level:** HIGH (well-documented migration path, small codebase)

---

## Executive Summary

The web/ application is a **small Next.js 13 App Router application** with only 4 page components and 7 utility components. The migration to Next.js 15 is straightforward because:

1. **All pages are client components** (`'use client'`) - No async API migration needed
2. **No usage of `cookies()`, `headers()`, `searchParams` from `next/headers`** - The main breaking change doesn't apply
3. **Simple `useParams()` usage** - Works identically in client components
4. **Small dependency footprint** - Only TanStack Query v4 needs a major upgrade

**Estimated Effort:** 2-4 hours (low complexity)

---

## Standard Stack

### Target Dependencies

```json
{
  "dependencies": {
    "next": "^15.5.10",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.90.0",
    "axios": "^1.13.5",
    "clsx": "^2.0.0",
    "lucide-react": "^0.470.0",
    "react-dropzone": "^14.2.3",
    "uuid": "^13.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.3.2",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@types/node": "^22.0.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.5.10",
    "typescript": "^5.4.0"
  }
}
```

### Dependency Notes

| Package | Current | Target | Migration Notes |
|---------|---------|--------|-----------------|
| next | 13.4.19 | ^15.5.10 | Codemod handles most changes |
| react | 18.2.0 | ^19.0.0 | Compatible with existing code |
| @tanstack/react-query | ^4.35.0 | ^5.90.0 | **API changes** - refactoring needed |
| lucide-react | ^0.279.0 | ^0.470.0 | Pin to avoid ESM issues in 0.471+ |
| react-dropzone | ^14.2.3 | Keep | Use `--legacy-peer-deps` for React 19 |
| @testing-library/react | ^13.4.0 | ^16.3.2 | Required for React 19 |

---

## Architecture Patterns

### Current Codebase Analysis

**Pages (4 total):**
| File | Type | Async APIs Used | Migration Complexity |
|------|------|-----------------|---------------------|
| `app/layout.tsx` | Server Component | None | LOW - metadata already compatible |
| `app/page.tsx` | Client Component | None | NONE - `'use client'` unchanged |
| `app/upload/page.tsx` | Client Component | None | NONE - `'use client'` unchanged |
| `app/documents/[id]/page.tsx` | Client Component | `useParams()` | NONE - hook works same way |

**Components (7 total):**
| Component | Uses Async APIs | Migration Complexity |
|-----------|-----------------|---------------------|
| `Providers.tsx` | No | LOW - QueryClient pattern update needed |
| `FileUpload.tsx` | No | NONE |
| `PDFProcessor.tsx` | No | NONE |
| `PDFUploader.tsx` | No | NONE |
| `AltTextReview.tsx` | No | NONE |
| `SignInModal.tsx` | No | NONE |
| `UserAvatar.tsx` | No | NONE |

### Key Finding: No Async API Migration Needed

The biggest Next.js 15 breaking change is that `cookies()`, `headers()`, `params`, and `searchParams` are now async. **This codebase uses NONE of these from `next/headers`.**

The only dynamic route parameter usage is in `documents/[id]/page.tsx`:
```typescript
'use client';
const params = useParams();
const docId = params.id as string;
```

This `useParams()` hook usage in client components **requires NO changes**.

### Required Pattern Updates

#### 1. QueryClient Creation (Providers.tsx)

**Current (problematic):**
```typescript
const queryClient = new QueryClient({...}); // Outside component

export function Providers({ children }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

**After (recommended for Next.js 15):**
```typescript
'use client';

import { useState } from 'react';

export function Providers({ children }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5,
        retry: (failureCount, error) => {
          if (error && typeof error === 'object' && 'status' in error) {
            const status = (error as any).status;
            if (status >= 400 && status < 500) return false;
          }
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      },
      mutations: { retry: 1 },
    },
  }));

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

#### 2. next.config.js Updates

**Current:**
```javascript
experimental: {
  appDir: true,  // Remove - default in 15
},
swcMinify: true,  // Remove - default in 15
```

**After:**
```javascript
// Remove experimental.appDir and swcMinify - both are defaults now
const nextConfig = {
  reactStrictMode: true,
  async rewrites() { ... },
  async headers() { ... },
};
```

---

## Don't Hand-Roll

1. **Codemod execution** - Use `npx @next/codemod@latest upgrade 15` instead of manual updates
2. **React 19 type definitions** - Use official `@types/react@19`, don't create custom types
3. **TanStack Query v5 migration** - Follow official migration guide, don't guess API changes
4. **ESLint flat config** - Either migrate fully or use `ESLINT_USE_FLAT_CONFIG=false`

---

## Common Pitfalls

### 1. TanStack Query v4 → v5 Breaking Changes

**Common mistakes:**
- Using `cacheTime` (renamed to `gcTime`)
- Using `useErrorBoundary` (renamed to `throwOnError`)
- Not updating query function signatures

**Key v5 changes:**
```typescript
// v4
useQuery(['key'], fetchFn, { cacheTime: 1000 })

// v5
useQuery({ queryKey: ['key'], queryFn: fetchFn, gcTime: 1000 })
```

### 2. lucide-react Version Mismatch

**Problem:** Versions 0.471+ have ESM/CommonJS issues with Next.js 15
**Solution:** Pin to `^0.470.0` (current 0.279.0 is safe, but if upgrading, stop at 0.470.0)

### 3. react-dropzone Peer Dependency Warnings

**Problem:** Only officially supports React 18
**Solution:** Use `pnpm install --legacy-peer-deps` or add to pnpm overrides

### 4. Test Library Version Mismatch

**Problem:** `@testing-library/react@13` requires React 18
**Solution:** Upgrade to `@testing-library/react@16` for React 19 support

### 5. Type Definition Mismatches

**Problem:** Using `@types/react@18` with React 19 causes TypeScript errors
**Solution:** Always upgrade type definitions together with React

---

## Automation Tools

### Primary: Next.js Upgrade Codemod

```bash
cd web/
npx @next/codemod@latest upgrade 15
```

**What it handles automatically:**
- Updates `next`, `react`, `react-dom` versions in package.json
- Removes deprecated `experimental.appDir`
- Removes deprecated `swcMinify`
- Updates deprecated imports

**What it does NOT handle (manual work):**
- TanStack Query v4 → v5 migration
- `@testing-library/react` upgrade
- Custom ESLint configuration
- `Providers.tsx` QueryClient pattern

### TanStack Query Migration

```bash
# Install v5
pnpm add @tanstack/react-query@^5.90.0

# Check for breaking changes
# No automated codemod - manual review required
```

---

## Code Examples

### Example 1: layout.tsx Metadata Type

**Before (valid but can improve):**
```typescript
export const metadata = {
  title: 'Next.js',
  description: 'Generated by Next.js',
};
```

**After (explicit typing):**
```typescript
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'PDF Accessibility',
  description: 'AI-powered PDF accessibility processing',
};
```

### Example 2: Children Type in Layout

**Before:**
```typescript
export default function RootLayout({ children }: { children: any }) {
```

**After:**
```typescript
export default function RootLayout({ children }: { children: React.ReactNode }) {
```

### Example 3: TanStack Query Hook (if applicable)

**Before (v4):**
```typescript
const { data } = useQuery(['document', id], () => fetchDocument(id));
```

**After (v5):**
```typescript
const { data } = useQuery({
  queryKey: ['document', id],
  queryFn: () => fetchDocument(id),
});
```

---

## Verification Checklist

### Pre-Migration
- [ ] Backup current `pnpm-lock.yaml`
- [ ] Document current working state
- [ ] Verify Node.js ≥ 18.17.0

### Migration Execution
- [ ] Run Next.js codemod
- [ ] Update remaining dependencies manually
- [ ] Fix `Providers.tsx` QueryClient pattern
- [ ] Update `next.config.js`
- [ ] Fix any TypeScript errors

### Post-Migration Verification
- [ ] `pnpm install` completes without errors
- [ ] `pnpm run build` succeeds
- [ ] `pnpm run dev` starts without warnings
- [ ] `pnpm run lint` passes
- [ ] `pnpm run type-check` passes
- [ ] `pnpm test` passes (if tests exist)

### Functional Testing
- [ ] Home page loads (`/`)
- [ ] Upload page works (`/upload`)
- [ ] File upload succeeds
- [ ] Document detail page displays (`/documents/[id]`)
- [ ] File download works
- [ ] No console errors or React warnings

---

## Migration Order

1. **Run codemod** - Handles Next.js core upgrade
2. **Update TanStack Query** - v4 → v5 with API changes
3. **Update testing libraries** - For React 19 compatibility
4. **Fix Providers.tsx** - QueryClient pattern
5. **Update next.config.js** - Remove deprecated options
6. **Fix type errors** - Any remaining TypeScript issues
7. **Verify build** - Full build and test
8. **Manual smoke test** - All pages functional

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| TanStack Query API breaks | MEDIUM | LOW | Hooks are minimal, follow migration guide |
| Build failures | LOW | MEDIUM | Well-documented upgrade path |
| Runtime errors | LOW | LOW | All client components, minimal server-side |
| Test failures | LOW | LOW | Jest tests should work with @testing-library v16 |

**Overall Risk: LOW** - Small codebase, client-side focus, no async API usage

---

## Sources

- [Next.js 15 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-15)
- [React 19 Upgrade Guide](https://react.dev/blog/2024/04/25/react-19-upgrade-guide)
- [TanStack Query v5 Migration](https://tanstack.com/query/latest/docs/framework/react/guides/migrating-to-v5)
- [Next.js Codemods](https://nextjs.org/docs/app/guides/upgrading/codemods)
