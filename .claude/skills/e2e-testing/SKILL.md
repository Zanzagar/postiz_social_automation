---
name: e2e-testing
description: Playwright/Cypress patterns, page objects, network interception, visual regression, CI
---
# E2E Testing Skill

## Page Object Pattern

Encapsulate page interactions for reusability and maintainability:

```typescript
// Playwright example
class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }

  async getErrorMessage() {
    return this.page.getByRole('alert').textContent();
  }
}

// Usage in test
test('successful login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('user@example.com', 'password');
  await expect(page).toHaveURL('/dashboard');
});
```

## Network Interception

### Playwright
```typescript
// Mock API response
await page.route('**/api/users', route => {
  route.fulfill({
    status: 200,
    body: JSON.stringify([{ id: 1, name: 'Alice' }]),
  });
});

// Wait for specific request
const [response] = await Promise.all([
  page.waitForResponse('**/api/submit'),
  page.getByRole('button', { name: 'Submit' }).click(),
]);
expect(response.status()).toBe(200);
```

### Cypress
```typescript
cy.intercept('GET', '/api/users', { fixture: 'users.json' }).as('getUsers');
cy.visit('/users');
cy.wait('@getUsers');
cy.get('[data-testid="user-list"]').should('have.length', 3);
```

## Visual Regression

### Playwright Screenshots
```typescript
// Full page comparison
await expect(page).toHaveScreenshot('dashboard.png', {
  maxDiffPixelRatio: 0.01, // Allow 1% pixel difference
});

// Element-level comparison
await expect(page.getByTestId('chart')).toHaveScreenshot('chart.png');

// Update baselines: npx playwright test --update-snapshots
```

### Thresholds
- `maxDiffPixelRatio: 0.01` — 1% pixel difference (recommended)
- `threshold: 0.2` — Per-pixel color difference tolerance
- Anti-aliasing differences: use `{ animations: 'disabled' }`

## CI Integration

### Playwright in GitHub Actions
```yaml
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: test-results
          path: test-results/
```

### Parallel Execution
```typescript
// playwright.config.ts
export default defineConfig({
  workers: process.env.CI ? 2 : undefined, // 2 workers in CI
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0, // Retry flaky tests in CI
});
```

## Test Data Management

### Fixtures
```typescript
// Seed database before tests
test.beforeEach(async ({ request }) => {
  await request.post('/api/test/seed', { data: { scenario: 'basic' } });
});

test.afterEach(async ({ request }) => {
  await request.post('/api/test/cleanup');
});
```

### Factories
```typescript
function createUser(overrides = {}) {
  return {
    name: `User ${Date.now()}`,
    email: `test-${Date.now()}@example.com`,
    ...overrides,
  };
}
```

## Selector Best Practices

**Priority order** (most stable first):
1. `data-testid` — `page.getByTestId('submit-btn')`
2. ARIA roles — `page.getByRole('button', { name: 'Submit' })`
3. Label text — `page.getByLabel('Email')`
4. Placeholder — `page.getByPlaceholder('Enter email')`
5. Text content — `page.getByText('Welcome')`

**Avoid**: CSS classes (change with styling), XPath (brittle), nth-child (order-dependent)
