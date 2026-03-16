import { test, expect } from "@playwright/test";

// These tests require an authenticated session.
// Set TEST_PASSWORD env var to your API password.

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.getByLabel("Password").fill(process.env.TEST_PASSWORD ?? "test");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText("Dashboard")).toBeVisible();
  });

  test("navigate to Create page", async ({ page }) => {
    await page.getByRole("link", { name: /create/i }).first().click();
    await expect(page.getByText("Create & Generate")).toBeVisible();
  });

  test("navigate to Drafts page", async ({ page }) => {
    await page.getByRole("link", { name: /drafts/i }).first().click();
    await expect(page.getByText("Review Drafts")).toBeVisible();
  });

  test("navigate to Calendar page", async ({ page }) => {
    await page.getByRole("link", { name: /calendar/i }).first().click();
    await expect(page.getByText("Content Calendar")).toBeVisible();
  });

  test("navigate to Health page", async ({ page }) => {
    await page.getByRole("link", { name: /health/i }).first().click();
    await expect(page.getByText("System Health")).toBeVisible();
  });
});
