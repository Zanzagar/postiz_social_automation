import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks, setupEmptyApiMocks } from "./fixtures";

test.describe("Calendar Page", () => {
  test("defaults to weekly view", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    await expect(
      page.getByRole("heading", { name: "Content Calendar" }),
    ).toBeVisible();
    // Weekly tab should be active
    await expect(page.getByRole("tab", { name: "Weekly" })).toHaveAttribute(
      "data-state",
      "active",
    );
  });

  test("shows entries in list view with date range dropdown", async ({
    page,
  }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    // Switch to list view
    await page.getByRole("tab", { name: "List" }).click();

    // Date range dropdown should appear
    await expect(page.getByText("Showing:")).toBeVisible();

    // Switch to All to see all mock data
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: "All content" }).click();

    await expect(page.getByText(/March 20/)).toBeVisible();
  });

  test("shows status badges on entries", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");
    await page.getByRole("tab", { name: "List" }).click();
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: "All content" }).click();

    await expect(page.getByText("scheduled", { exact: true })).toBeVisible();
    await expect(page.getByText("posted", { exact: true })).toBeVisible();
  });

  test("shows platform tags", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");
    await page.getByRole("tab", { name: "List" }).click();
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: "All content" }).click();

    await expect(page.getByText("instagram").first()).toBeVisible();
  });

  test("shows content pillar labels", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");
    await page.getByRole("tab", { name: "List" }).click();
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: "All content" }).click();

    await expect(page.getByText("Spiritual Education")).toBeVisible();
    await expect(page.getByText("Events")).toBeVisible();
  });

  test("shows entry text content", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");
    await page.getByRole("tab", { name: "List" }).click();
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: "All content" }).click();

    await expect(page.getByText(/morning kirtan/i)).toBeVisible();
    await expect(page.getByText(/spring festival/i)).toBeVisible();
  });

  test("shows empty state when no entries", async ({ page }) => {
    await setupAuth(page);
    await setupEmptyApiMocks(page);
    await page.goto("/calendar");

    await expect(page.getByText("No scheduled content")).toBeVisible();
    await expect(page.getByText(/create content to see it/i)).toBeVisible();
  });

  test("monthly view shows navigation", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    await page.getByRole("tab", { name: "Monthly" }).click();
    // Should show month name and navigation arrows
    await expect(page.getByText(/March 2026|2026/)).toBeVisible();
  });
});
