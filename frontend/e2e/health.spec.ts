import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks, setupEmptyApiMocks } from "./fixtures";

test.describe("Health Page", () => {
  test("shows service statuses", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/health");

    await expect(
      page.getByRole("heading", { name: "System Health" }),
    ).toBeVisible();
    await expect(page.getByText("Postiz", { exact: true })).toBeVisible();
    await expect(page.getByText("Google Sheets")).toBeVisible();
    await expect(page.getByText("Content Engine")).toBeVisible();
  });

  test("shows status badges for each service", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/health");

    await expect(page.getByText("healthy").first()).toBeVisible();
    await expect(page.getByText("degraded")).toBeVisible();
  });

  test("shows service status messages", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/health");

    await expect(page.getByText("Connected")).toBeVisible();
    await expect(page.getByText("Accessible")).toBeVisible();
    await expect(page.getByText("High latency")).toBeVisible();
  });

  test("shows integrations list", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/health");

    await expect(page.getByText("Postiz Integrations")).toBeVisible();
    await expect(page.getByText("Gita Valley IG")).toBeVisible();
    await expect(page.getByText("Gita Valley FB")).toBeVisible();
  });

  test("shows integration platform badges", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/health");

    // Platform badges in the integrations section
    await expect(page.getByText("instagram", { exact: true })).toBeVisible();
    await expect(page.getByText("facebook", { exact: true })).toBeVisible();
  });

  test("shows empty states when no services or integrations", async ({
    page,
  }) => {
    await setupAuth(page);
    await setupEmptyApiMocks(page);
    await page.goto("/health");

    await expect(page.getByText("No services configured")).toBeVisible();
    await expect(
      page.getByText("No Postiz integrations found"),
    ).toBeVisible();
  });
});
