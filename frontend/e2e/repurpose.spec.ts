import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks } from "./fixtures";

test.describe("Repurpose Content", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
  });

  test("repurpose button appears on each draft card", async ({ page }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    const repurposeButtons = page.getByRole("button", {
      name: /repurpose/i,
    });
    await expect(repurposeButtons.first()).toBeVisible();
    // Each draft card should have a repurpose button
    expect(await repurposeButtons.count()).toBe(2);
  });

  test("repurpose button opens modal in repurpose mode", async ({ page }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page
      .getByRole("button", { name: /repurpose/i })
      .first()
      .click();

    // Should show Repurpose Content title (not Refine Content)
    await expect(
      page.getByRole("heading", { name: "Repurpose Content" }),
    ).toBeVisible();
  });

  test("repurpose modal shows original content reference", async ({
    page,
  }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page
      .getByRole("button", { name: /repurpose/i })
      .first()
      .click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Original Content")).toBeVisible();
    // Shows the original caption text from the mock draft within the dialog
    await expect(
      dialog.getByText(/morning kirtan at the temple/i).first(),
    ).toBeVisible();
  });

  test("repurpose modal shows platform selector checkboxes", async ({
    page,
  }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page
      .getByRole("button", { name: /repurpose/i })
      .first()
      .click();

    await expect(
      page.getByText("Repurpose for these platforms:"),
    ).toBeVisible();

    // All platform checkboxes in the dialog
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByLabel("Instagram")).toBeVisible();
    await expect(dialog.getByLabel("Facebook")).toBeVisible();
    await expect(dialog.getByLabel("TikTok")).toBeVisible();
    await expect(dialog.getByLabel("Threads")).toBeVisible();
    await expect(dialog.getByLabel("LinkedIn")).toBeVisible();
  });

  test("generate button disabled until platforms selected", async ({
    page,
  }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page
      .getByRole("button", { name: /repurpose/i })
      .first()
      .click();

    const generateBtn = page.getByRole("button", {
      name: /generate repurposed captions/i,
    });
    await expect(generateBtn).toBeDisabled();

    // Select a platform
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("TikTok").click();
    await expect(generateBtn).toBeEnabled();
  });

  test("generates repurposed captions and shows tabs", async ({ page }) => {
    await page.route("**/api/generate-sync**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          captions: {
            tiktok: "Quick kitchen vibes at Gita Valley #fyp",
            threads: "Cooking with devotion at Gita Valley",
          },
        }),
      }),
    );

    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page
      .getByRole("button", { name: /repurpose/i })
      .first()
      .click();

    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("TikTok").click();
    await dialog.getByLabel("Threads").click();

    await page
      .getByRole("button", { name: /generate repurposed captions/i })
      .click();

    // After generation, should show platform tabs with generated captions
    await expect(page.getByText("Quick kitchen vibes")).toBeVisible();

    // Default for drafts is merge — button says "Add to Draft"
    await expect(
      page.getByRole("button", { name: /add to draft/i }),
    ).toBeVisible();
  });

  test("separate mode shows Save as New Draft button", async ({ page }) => {
    await page.route("**/api/generate-sync**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          captions: { tiktok: "Separate draft caption" },
          row_id: 99,
        }),
      }),
    );

    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page
      .getByRole("button", { name: /repurpose/i })
      .first()
      .click();

    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("TikTok").click();

    // Switch to separate mode
    await dialog.getByText("Create separate draft").click();

    await page
      .getByRole("button", { name: /generate repurposed captions/i })
      .click();

    await expect(page.getByText("Separate draft caption")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /save as new draft/i }),
    ).toBeVisible();
  });

  test("clicking card still opens refine mode", async ({ page }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    // Click the card content (not the repurpose button)
    await page.getByText(/morning kirtan/i).first().click();

    // Should open in Refine mode
    await expect(
      page.getByRole("heading", { name: "Refine Content" }),
    ).toBeVisible();
  });
});
