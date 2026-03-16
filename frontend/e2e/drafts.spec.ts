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

  test("inline caption editing in draft card", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeVisible();
    await textarea.fill("Edited caption text");
    await expect(textarea).toHaveValue("Edited caption text");
  });

  test("shows date on draft cards", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/drafts");

    await expect(page.getByText("2026-03-20")).toBeVisible();
    await expect(page.getByText("2026-03-21")).toBeVisible();
  });
});
