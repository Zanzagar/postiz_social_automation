import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks } from "./fixtures";

test.describe("Repurpose Content", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
  });

  test("repurpose button appears inside refine modal", async ({ page }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    // Click a draft to open refine modal
    await page.getByText(/morning kirtan/i).first().click();

    await expect(
      page.getByRole("heading", { name: "Refine Content" }),
    ).toBeVisible();

    // Repurpose button in the footer
    await expect(
      page.getByRole("button", { name: /repurpose/i }),
    ).toBeVisible();
  });

  test("clicking repurpose switches to repurpose mode", async ({ page }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page.getByText(/morning kirtan/i).first().click();
    await page.getByRole("button", { name: /repurpose/i }).click();

    // Title changes to Repurpose Content
    await expect(
      page.getByRole("heading", { name: "Repurpose Content" }),
    ).toBeVisible();

    // Shows original content and platform selector
    await expect(page.getByText("Original Content")).toBeVisible();
    await expect(
      page.getByText("Repurpose for these platforms:"),
    ).toBeVisible();
  });

  test("back to refine button returns to refine mode", async ({ page }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page.getByText(/morning kirtan/i).first().click();
    await page.getByRole("button", { name: /repurpose/i }).click();

    await expect(
      page.getByRole("heading", { name: "Repurpose Content" }),
    ).toBeVisible();

    await page.getByRole("button", { name: /back to refine/i }).click();

    await expect(
      page.getByRole("heading", { name: "Refine Content" }),
    ).toBeVisible();
  });

  test("repurpose modal shows platform checkboxes", async ({ page }) => {
    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page.getByText(/morning kirtan/i).first().click();
    await page.getByRole("button", { name: /repurpose/i }).click();

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

    await page.getByText(/morning kirtan/i).first().click();
    await page.getByRole("button", { name: /repurpose/i }).click();

    const generateBtn = page.getByRole("button", {
      name: /generate repurposed captions/i,
    });
    await expect(generateBtn).toBeDisabled();

    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("TikTok").click();
    await expect(generateBtn).toBeEnabled();
  });

  test("generates repurposed captions with merge option", async ({
    page,
  }) => {
    await page.route("**/api/generate-sync**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          captions: {
            tiktok: "Quick kitchen vibes at Gita Valley #fyp",
          },
        }),
      }),
    );

    await page.goto("/drafts");
    await expect(page.getByText("Review Drafts")).toBeVisible();

    await page.getByText(/morning kirtan/i).first().click();
    await page.getByRole("button", { name: /repurpose/i }).click();

    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("TikTok").click();

    await page
      .getByRole("button", { name: /generate repurposed captions/i })
      .click();

    await expect(page.getByText("Quick kitchen vibes")).toBeVisible();

    // Default for drafts is merge
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

    await page.getByText(/morning kirtan/i).first().click();
    await page.getByRole("button", { name: /repurpose/i }).click();

    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("TikTok").click();
    await dialog.getByText("Create separate draft").click();

    await page
      .getByRole("button", { name: /generate repurposed captions/i })
      .click();

    await expect(page.getByText("Separate draft caption")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /save as new draft/i }),
    ).toBeVisible();
  });
});
