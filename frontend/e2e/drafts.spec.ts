import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks, setupEmptyApiMocks } from "./fixtures";

test.describe("Drafts Page", () => {
  test("shows draft cards with content", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    await expect(page.getByText("Review Drafts")).toBeVisible();
    // Use .first() since text appears in both card summary and caption textarea
    await expect(page.getByText(/morning kirtan/i).first()).toBeVisible();
    await expect(page.getByText(/organic vegetables/i).first()).toBeVisible();
  });

  test("shows empty state when no drafts", async ({ page }) => {
    await setupAuth(page);
    await setupEmptyApiMocks(page);
    await page.goto("/drafts");

    await expect(page.getByText("All caught up!")).toBeVisible();
    await expect(page.getByText(/no pending drafts/i)).toBeVisible();
  });

  test("select all and deselect all", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page.getByLabel("Select all").click();
    await expect(page.getByText("2 selected")).toBeVisible();

    await page.getByLabel("Select all").click();
    await expect(page.getByText("2 selected")).not.toBeVisible();
  });

  test("shows batch approve bar when drafts selected", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    await expect(page.getByText("Review Drafts")).toBeVisible();
    await page.getByLabel("Select all").click();
    await expect(
      page.getByRole("button", { name: /approve.*postiz/i }),
    ).toBeVisible();
  });

  test("shows platform tabs on draft cards", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    // First draft has instagram and facebook tabs
    await expect(page.getByText("IG").first()).toBeVisible();
    await expect(page.getByText("FB").first()).toBeVisible();
  });

  test("shows content pillar badges", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    await expect(page.getByText("Spiritual Education")).toBeVisible();
    await expect(page.getByText("Farm & Community")).toBeVisible();
  });

  test("draft cards are clickable", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    // Draft cards have clickable content areas with button role
    const firstCard = page.locator("[role='button']").first();
    await expect(firstCard).toBeVisible();
    await expect(firstCard).toContainText(/morning kirtan/i);
  });

  test("shows formatted date on draft cards", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    // Dates are formatted as "MMM d, h:mm a" — "2026-03-20" → "Mar 20"
    await expect(page.getByText(/Mar 20/i).first()).toBeVisible();
    await expect(page.getByText(/Mar 21/i).first()).toBeVisible();
  });
});
