import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks, setupEmptyApiMocks } from "./fixtures";

test.describe("Calendar Page", () => {
  test("shows entries grouped by date", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    await expect(
      page.getByRole("heading", { name: "Content Calendar" }),
    ).toBeVisible();
    await expect(page.getByText(/March 20/)).toBeVisible();
    await expect(page.getByText(/March 22/)).toBeVisible();
  });

  test("shows status badges on entries", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    // Use locator to find badge-like elements with status text
    await expect(page.getByText("scheduled", { exact: true })).toBeVisible();
    await expect(page.getByText("posted", { exact: true })).toBeVisible();
  });

  test("shows platform tags", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    await expect(page.getByText("instagram").first()).toBeVisible();
  });

  test("shows content pillar labels", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    await expect(page.getByText("Spiritual Education")).toBeVisible();
    await expect(page.getByText("Events")).toBeVisible();
    await expect(page.getByText("Behind the Scenes")).toBeVisible();
  });

  test("shows entry text content", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/calendar");

    await expect(page.getByText(/morning kirtan/i)).toBeVisible();
    await expect(page.getByText(/spring festival/i)).toBeVisible();
    await expect(page.getByText(/day in the life/i)).toBeVisible();
  });

  test("shows empty state when no entries", async ({ page }) => {
    await setupAuth(page);
    await setupEmptyApiMocks(page);
    await page.goto("/calendar");

    await expect(page.getByText("No scheduled content")).toBeVisible();
    await expect(page.getByText(/create content to see it/i)).toBeVisible();
  });
});
