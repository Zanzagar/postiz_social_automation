import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks } from "./fixtures";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
  });

  test("shows stats cards", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Pending Drafts")).toBeVisible();
    await expect(page.getByText("Scheduled This Week")).toBeVisible();
    await expect(page.getByText("Posts Published")).toBeVisible();
  });

  test("shows Quick Create link that navigates", async ({ page }) => {
    await page.goto("/");

    const createLink = page.getByRole("link", { name: /create content/i });
    await expect(createLink).toBeVisible();
    await createLink.click();
    await expect(page.getByText("Create & Generate")).toBeVisible();
  });

  test("shows system health status on dashboard", async ({ page }) => {
    await page.goto("/");

    const healthSection = page.getByTestId("health-status");
    await expect(healthSection.getByText("Postiz")).toBeVisible();
    await expect(healthSection.getByText("Google Sheets")).toBeVisible();
    await expect(healthSection.getByText("Content Engine")).toBeVisible();
  });

  test("shows loading skeletons while data fetches", async ({ page }) => {
    // Override with hanging routes to keep loading state
    await page.route("**/api/drafts", () => {});
    await page.route("**/api/calendar", () => {});
    await page.route("**/api/health", () => {});

    await page.goto("/");
    await expect(page.getByTestId("skeleton-card").first()).toBeVisible();
  });
});
