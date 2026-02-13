# Milestone 1: Dependabot Security Fixes - Roadmap

## Overview

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Direct Dependency Updates | ✅ Complete | Updated axios, better-auth, next (dashboard), playwright, postcss |
| 2 | Next.js Major Upgrade (web/) | 🔲 Pending | Upgrade web/ from Next.js 13.4.19 to 15.x |
| 3 | Transitive & Verification | 🔲 Pending | Fix transitive deps, resolve overrides, verify builds |

---

## Phase 1: Direct Dependency Updates

**Objective:** Update all direct dependencies that have known vulnerabilities (except Next.js in web/ which requires migration work).

### Packages to Update

| Package | Location | Current | Target | Severity |
|---------|----------|---------|--------|----------|
| axios | root, web/, dashboard/ | 1.5.0-1.11.0 | ≥1.13.5 | HIGH |
| better-auth | dashboard/ | 1.3.9 | ≥1.4.5 | HIGH |
| @playwright/test | root, dashboard/ | 1.40.1 | latest | HIGH |
| postcss | web/, dashboard/ | 8.4.29/8.4.32 | ≥8.5.x | MEDIUM |
| next | dashboard/ | 15.5.7 | ≥15.5.10 | HIGH/CRITICAL |

### Tasks

1. Update dashboard/package.json:
   - `next`: 15.5.7 → ≥15.5.10
   - `better-auth`: 1.3.9 → ≥1.4.5
   - `axios`: 1.11.0 → ≥1.13.5
   - `postcss`: 8.4.32 → latest

2. Update web/package.json:
   - `axios`: 1.5.0 → ≥1.13.5
   - `postcss`: 8.4.29 → latest

3. Update root package.json:
   - `axios`: 1.11.0 → ≥1.13.5
   - `@playwright/test`: 1.40.1 → latest

4. Run `pnpm install` to regenerate lockfile

5. Verify:
   - `pnpm -r type-check`
   - `pnpm -r lint`
   - `pnpm -r test`

### Deliverables

- [x] All direct dependencies updated
- [x] pnpm-lock.yaml regenerated
- [x] Type checking passes (dashboard)
- [ ] Tests pass (deferred - disk space constraints)

---

## Phase 2: Next.js Major Upgrade (web/)

**Objective:** Upgrade web/ from Next.js 13.4.19 to 15.x to resolve 58 security vulnerabilities.

### Breaking Changes to Address

1. **App Router Changes** (if using app/ directory)
2. **React 18 → 19 RC** (dashboard uses RC, web uses 18.2.0)
3. **API Routes** → Route Handlers
4. **Image Component** changes
5. **Font handling** changes
6. **Metadata API** changes

### Tasks

1. Review Next.js 14 and 15 migration guides
2. Update web/package.json dependencies:
   - `next`: 13.4.19 → ≥15.5.10
   - `react`: 18.2.0 → 19.x (or 19-rc to match dashboard)
   - `react-dom`: 18.2.0 → 19.x
   - `eslint-config-next`: 13.4.19 → ≥15.x
   - `@types/react`: 18.2.21 → ≥18.3.x or 19.x
   - `@types/react-dom`: 18.2.7 → ≥18.3.x or 19.x

3. Fix breaking changes:
   - Update any deprecated APIs
   - Fix type errors
   - Update next.config.js if needed

4. Test thoroughly:
   - Build verification
   - All pages render
   - API routes work
   - Form submissions work

### Deliverables

- [ ] Next.js 15.x running in web/
- [ ] All pages functional
- [ ] All tests passing
- [ ] No TypeScript errors

---

## Phase 3: Transitive Dependencies & Verification

**Objective:** Resolve remaining transitive dependency vulnerabilities and perform final verification.

### Transitive Dependencies to Resolve

| Package | Via | Strategy |
|---------|-----|----------|
| fast-xml-parser | @aws-sdk/* | npm overrides |
| qs | various | npm overrides |
| tar-fs | playwright | updated in Phase 1 |
| jws | jsonwebtoken | check if updated |
| glob | various | npm overrides |
| js-yaml | various | npm overrides |
| lodash | various | npm overrides |
| vite | vitest | update vitest |
| @smithy/config-resolver | @aws-sdk/* | npm overrides |

### Tasks

1. Add npm `overrides` section to root package.json:
   ```json
   "pnpm": {
     "overrides": {
       "fast-xml-parser": ">=5.3.4",
       "qs": ">=6.14.2",
       "glob": ">=9.0.0",
       "js-yaml": ">=4.1.0",
       "lodash": ">=4.17.23",
       "@smithy/config-resolver": ">=4.4.0"
     }
   }
   ```

2. Update vitest if needed for vite vulnerability

3. Run full verification:
   - `pnpm install`
   - `pnpm -r build`
   - `pnpm -r test`
   - Docker build test

4. Verify Dependabot alerts cleared:
   - Push to branch
   - Check Dependabot dashboard
   - Address any remaining alerts

### Deliverables

- [ ] All transitive vulnerabilities resolved
- [ ] Full build passes
- [ ] All tests pass
- [ ] Dependabot shows 0 open alerts (or documented exceptions)

---

## Execution Order

```
Phase 1: Direct Dependencies
    ├─→ Update dashboard (direct deps)
    ├─→ Update web (direct deps except Next.js)
    └─→ Update root (direct deps)
         ↓
Phase 2: Next.js Migration (web/)
    ├─→ Review migration guides
    ├─→ Update dependencies
    ├─→ Fix breaking changes
    └─→ Verify functionality
         ↓
Phase 3: Transitive & Final
    ├─→ Add overrides
    ├─→ Update lockfile
    ├─→ Full verification
    └─→ Confirm alerts resolved
```

---

## Success Criteria

1. **Zero CRITICAL/HIGH Dependabot alerts**
2. **All builds passing** (`pnpm -r build`)
3. **All tests passing** (`pnpm -r test`)
4. **Applications functional** (manual smoke test)
5. **CI pipeline green** (after PR)

---

## Rollback Plan

If major issues arise:
1. Git revert to previous commit
2. `pnpm install` to restore lockfile
3. Investigate specific breaking change
4. Consider incremental upgrade path (13 → 14 → 15)
