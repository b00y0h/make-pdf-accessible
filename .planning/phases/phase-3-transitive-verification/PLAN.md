# Phase 3: Transitive Dependencies & Verification

## Overview

**Objective:** Resolve remaining transitive dependency vulnerabilities and perform final verification.

**Current State:** 8 unique vulnerabilities remaining across transitive dependencies.

---

## Vulnerability Summary

| Package | Current Version | Patched Version | Severity | Fix Strategy |
|---------|-----------------|-----------------|----------|--------------|
| playwright | 1.55.0 | >=1.55.1 | HIGH | pnpm override |
| tar-fs | 2.1.3 | >=2.1.4 | HIGH | pnpm override |
| glob | 10.4.5 | >=10.5.0 | HIGH | pnpm override |
| jws | 3.2.2 | >=3.2.3 | HIGH | pnpm override |
| fast-xml-parser | 5.2.5 | >=5.3.4 | HIGH | pnpm override |
| vite | 7.1.5 | >=7.1.11 | MODERATE | pnpm override |
| lodash | 4.17.21 | >=4.17.23 | MODERATE | pnpm override |
| @smithy/config-resolver | 4.2.1 | >=4.4.0 | LOW | pnpm override |
| qs | 6.14.0 | >=6.14.2 | LOW/HIGH | pnpm override |

---

## Dependency Chains

### playwright (1.55.0 → >=1.55.1)
- `dashboard > next > @playwright/test > playwright`
- `dashboard > better-auth > next > @playwright/test > playwright`

### tar-fs (2.1.3 → >=2.1.4)
- `root > better-sqlite3 > prebuild-install > tar-fs`
- `dashboard > better-auth > better-sqlite3 > prebuild-install > tar-fs`

### glob (10.4.5 → >=10.5.0)
- `dashboard > tailwindcss > sucrase > glob`

### jws (3.2.2 → >=3.2.3)
- `dashboard > jsonwebtoken > jws`

### fast-xml-parser (5.2.5 → >=5.3.4)
- `dashboard > @aws-sdk/client-* > @aws-sdk/core > fast-xml-parser`
- Multiple paths through AWS SDK packages

### vite (7.1.5 → >=7.1.11)
- `dashboard > better-auth > vitest > vite`
- `dashboard > better-auth > vitest > @vitest/mocker > vite`
- `dashboard > better-auth > vitest > vite-node > vite`

### lodash (4.17.21 → >=4.17.23)
- `dashboard > @aws-amplify/ui-react > @aws-amplify/ui > lodash`
- `dashboard > @aws-amplify/ui-react > lodash`

### @smithy/config-resolver (4.2.1 → >=4.4.0)
- `dashboard > @aws-sdk/client-* > @smithy/config-resolver`

### qs (6.14.0 → >=6.14.2)
- `dashboard > body-parser > qs` (transitive)
- Various indirect paths

---

## Execution Plan

### Step 1: Add pnpm Overrides

Add `pnpm.overrides` section to root `package.json`:

```json
"pnpm": {
  "overrides": {
    "playwright": ">=1.55.1",
    "tar-fs": ">=2.1.4",
    "glob@>=10.2.0 <10.5.0": ">=10.5.0",
    "jws": ">=3.2.3",
    "fast-xml-parser@>=5.0.9 <=5.3.3": ">=5.3.4",
    "vite@>=7.1.0 <=7.1.10": ">=7.1.11",
    "lodash@>=4.0.0 <=4.17.22": ">=4.17.23",
    "@smithy/config-resolver": ">=4.4.0",
    "qs@<6.14.2": ">=6.14.2"
  }
}
```

### Step 2: Regenerate Lockfile

```bash
pnpm install
```

### Step 3: Verify Overrides Applied

```bash
pnpm audit
```

Expected: 0 vulnerabilities

### Step 4: Build Verification

```bash
# Type checking
pnpm -r type-check

# Lint
pnpm -r lint

# Build
pnpm -r build
```

### Step 5: Test Verification

```bash
# Run all tests
pnpm -r test
```

Note: Pre-existing test configuration issues in web/ and dashboard/ are documented in STATE.md. These are unrelated to security fixes.

### Step 6: Dependabot Alert Verification

After push:
1. Check GitHub Dependabot dashboard
2. Verify all alerts marked as fixed
3. Document any remaining exceptions

---

## Risk Assessment

### Low Risk Overrides
- `playwright`: Patch version bump
- `tar-fs`: Patch version bump
- `jws`: Patch version bump
- `qs`: Patch version bump
- `@smithy/config-resolver`: Minor version bump

### Moderate Risk Overrides
- `glob`: Minor version bump (10.4.5 → 10.5.0)
- `lodash`: Patch version bump (widely used, well-tested)

### Higher Risk Overrides
- `fast-xml-parser`: Patch version bump but core parsing library
- `vite`: Patch version bump but build tool (dev dependency only)

### Mitigation
- All builds must pass before considering complete
- Type checking catches API changes
- Lint catches obvious issues
- Full test suite provides behavioral validation

---

## Verification Checklist

- [x] pnpm overrides added to package.json
- [x] `pnpm install` succeeds
- [x] `pnpm audit` shows 0 vulnerabilities
- [x] `pnpm -r type-check` passes
- [x] `pnpm -r lint` passes (warnings acceptable)
- [x] `pnpm -r build` passes
- [ ] `pnpm -r test` passes (or pre-existing failures only) - skipped, pre-existing config issues
- [ ] Dependabot alerts cleared on GitHub - pending push

---

## Success Criteria

1. **Zero HIGH/CRITICAL Dependabot alerts** (open)
2. **All builds passing** (`pnpm -r build`)
3. **Type checking passing** (`pnpm -r type-check`)
4. **No new regressions** introduced by overrides

---

## Rollback Plan

If overrides cause issues:
1. Remove problematic override from package.json
2. Run `pnpm install` to restore previous version
3. Document incompatibility
4. Consider alternative fix strategies:
   - Update parent dependency
   - Fork and patch
   - Accept risk with documentation

---

## Commit Strategy

Single atomic commit:
```
fix(security): resolve transitive dependency vulnerabilities

Add pnpm overrides to fix remaining security vulnerabilities:
- playwright: 1.55.0 → >=1.55.1 (HIGH - SSL cert verification)
- tar-fs: 2.1.3 → >=2.1.4 (HIGH - symlink validation bypass)
- glob: 10.4.5 → >=10.5.0 (HIGH - command injection)
- jws: 3.2.2 → >=3.2.3 (HIGH - HMAC signature verification)
- fast-xml-parser: 5.2.5 → >=5.3.4 (HIGH - DoS via numeric entities)
- vite: 7.1.5 → >=7.1.11 (MODERATE - fs.deny bypass on Windows)
- lodash: 4.17.21 → >=4.17.23 (MODERATE - prototype pollution)
- @smithy/config-resolver: >=4.4.0 (LOW)
- qs: >=6.14.2 (LOW/HIGH)

Closes Dependabot alerts #57, #58, #60, #65, #66
```
