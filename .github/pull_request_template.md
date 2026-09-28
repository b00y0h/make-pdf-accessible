<!--
Title: type(scope): summary, for example "fix(worker): retry OCR when throttled".
Lowercase after the colon and 72 characters or fewer. Add "!" before the colon
when existing callers must change, for example "feat(api)!: require tenant id".
Keep the pull request to one concern, and open it as a draft until it is ready.
-->

## What

<!-- What changes, in two or three sentences or a short list. -->

## Why

<!-- The problem or goal. Link the issue, PRD or ADR. "Closes #123" closes the issue on merge. -->

## How

<!--
The approach and any decision a reviewer should know about, including alternatives
you rejected. Say where to start reading and what is deliberately left out.
-->

## Testing

<!--
How you verified the change: commands you ran and what they showed, tests added or
updated, and manual steps. Add before and after screenshots for UI changes, and a
summary of the terraform plan for infrastructure changes. If a CI check is red for
a reason outside this pull request, name the check and say why.
-->

## Risk and rollout

<!--
What could be affected and how you would roll back. Mention migrations, new
configuration, secrets or variables (names only, never values), and any step
that must happen before or after deploy. If the risk is low, say why.
-->

## Checklist

<!-- Delete the items that do not apply, so the task count reflects real work. -->

- [ ] I reviewed my own diff: no debug output, commented-out code or secrets.
- [ ] Tests cover the change, or Testing explains why not.
- [ ] Docs are updated: README, and the PRDs, ADRs or specs in `docs/` when behavior or a decision changes.
- [ ] Accessibility: UI changes work with a keyboard and a screen reader, and axe reports no new WCAG 2.1 AA issues.
- [ ] Privacy: no document contents or personal data in logs, fixtures or screenshots, and tenant data stays isolated.
- [ ] Infrastructure: `terraform fmt`, `terraform validate` and TFLint pass, and I reviewed the plan.
- [ ] Database: migrations are reversible and safe to run before the code that uses them ships.
- [ ] Marketing copy: claims match what the product does, and `pnpm --filter mpa-marketing check:copy` passes.
