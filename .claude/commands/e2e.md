Generate and run end-to-end tests with Playwright, Cypress, or Selenium.

Usage: `/e2e <user flow description>`

Arguments: $ARGUMENTS

## What This Command Does

1. **Generate Test Journeys** - Create E2E tests for user flows
2. **Run Tests** - Execute tests across browsers
3. **Capture Artifacts** - Screenshots, videos, traces on failures
4. **Identify Flaky Tests** - Quarantine unstable tests

## When to Use

- Testing critical user journeys (login, checkout, payments)
- Verifying multi-step flows end-to-end
- Testing UI interactions and navigation
- Validating frontend-backend integration
- Preparing for production deployment

## Test Generation Pattern

The e2e-runner agent will:

1. **Analyze the user flow** and identify test scenarios
2. **Generate tests** using Page Object Model pattern
3. **Run tests** across configured browsers
4. **Capture failures** with screenshots, videos, and traces
5. **Identify flaky tests** and recommend fixes

## Test Framework Detection

| Indicator | Framework |
|-----------|-----------|
| `playwright.config.*` | Playwright |
| `cypress.config.*` | Cypress |
| `selenium` in dependencies | Selenium |
| None detected | Suggest Playwright setup |

## Page Object Model

Tests should use Page Object Model for maintainability:

```typescript
// pages/LoginPage.ts
export class LoginPage {
  constructor(private page: Page) {}
  async goto() { await this.page.goto('/login') }
  async login(email: string, password: string) {
    await this.page.fill('[data-testid="email"]', email)
    await this.page.fill('[data-testid="password"]', password)
    await this.page.click('[data-testid="submit"]')
  }
}
```

## Artifacts

**On All Tests:**
- HTML Report with timeline and results

**On Failure Only:**
- Screenshot of the failing state
- Video recording of the test
- Trace file for step-by-step replay
- Network and console logs

## Flaky Test Detection

```
WARNING: FLAKY TEST DETECTED
Test: tests/e2e/checkout.spec.ts
Pass rate: 7/10 (70%)

Common failure:
"Timeout waiting for element '[data-testid="confirm-btn"]'"

Recommended fixes:
1. Add explicit wait: await page.waitForSelector(...)
2. Increase timeout: { timeout: 10000 }
3. Check for race conditions in component rendering

Quarantine: Mark as test.fixme() until fixed
```

## Best Practices

**DO:**
- Use `data-testid` attributes for selectors
- Wait for API responses, not arbitrary timeouts
- Test critical user journeys end-to-end
- Review artifacts when tests fail

**DON'T:**
- Use brittle CSS class selectors
- Test implementation details
- Run against production
- Ignore flaky tests
- Test every edge case with E2E (use unit tests)

## Quick Commands

```bash
npx playwright test                              # Run all
npx playwright test tests/e2e/login.spec.ts      # Run specific
npx playwright test --headed                     # See browser
npx playwright test --debug                      # Debug mode
npx playwright show-report                       # View report
```

## Integration

- Use `/plan` to identify critical journeys to test
- Use `/tdd` for unit tests (faster, more granular)
- Use `/e2e` for integration and user journey tests
- Part of `/orchestrate feature` pipeline

## Agent

Invokes the **e2e-runner** agent (sonnet, + Bash).
