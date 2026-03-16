import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks, setupEmptyApiMocks } from "./fixtures";

test.describe("Suggestions Page", () => {
  test("shows suggestion cards", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/suggestions");

    await expect(page.getByText("Content Suggestions")).toBeVisible();
    await expect(page.getByText(/greenhouse construction/i)).toBeVisible();
    await expect(page.getByText(/bhagavad gita verse/i)).toBeVisible();
  });

  test("shows pillar badges", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/suggestions");

    await expect(page.getByText("Farm & Community")).toBeVisible();
    await expect(page.getByText("Spiritual Education")).toBeVisible();
  });

  test("shows rationale text", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/suggestions");

    await expect(
      page.getByText(/community members have been asking/i),
    ).toBeVisible();
    await expect(
      page.getByText(/highest engagement rates/i),
    ).toBeVisible();
  });

  test("shows media suggestions", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/suggestions");

    await expect(page.getByText(/photo of the greenhouse/i)).toBeVisible();
    await expect(page.getByText(/verse text overlay/i)).toBeVisible();
  });

  test("shows suggested dates", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/suggestions");

    await expect(page.getByText(/2026-03-25/)).toBeVisible();
    await expect(page.getByText(/2026-03-27/)).toBeVisible();
  });

  test("shows empty state when no suggestions", async ({ page }) => {
    await setupAuth(page);
    await setupEmptyApiMocks(page);
    await page.goto("/suggestions");

    await expect(page.getByText("No suggestions")).toBeVisible();
    await expect(
      page.getByText(/ai suggestions will appear/i),
    ).toBeVisible();
  });
});
