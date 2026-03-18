import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks } from "./fixtures";

test.describe("Create Page", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/create");
    await expect(
      page.getByRole("heading", { name: "Create & Generate" }),
    ).toBeVisible();
  });

  test("shows all form elements", async ({ page }) => {
    await expect(page.getByText("Media")).toBeVisible();
    await expect(
      page.getByLabel(/what do you want to post/i),
    ).toBeVisible();
    await expect(page.getByText("Platforms")).toBeVisible();
    await expect(page.getByLabel("Date")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /generate ai captions/i }),
    ).toBeVisible();
  });

  test("shows character count that updates", async ({ page }) => {
    await expect(page.getByText("0/2000")).toBeVisible();
    await page.getByLabel(/what do you want to post/i).fill("Hello world");
    await expect(page.getByText("11/2000")).toBeVisible();
  });

  test("shows all platform checkboxes", async ({ page }) => {
    await expect(page.getByLabel("Instagram")).toBeVisible();
    await expect(page.getByLabel("Facebook")).toBeVisible();
    await expect(page.getByLabel("TikTok")).toBeVisible();
    await expect(page.getByLabel("Threads")).toBeVisible();
    await expect(page.getByLabel("LinkedIn")).toBeVisible();
  });

  test("generate button disabled without platforms selected", async ({
    page,
  }) => {
    await expect(
      page.getByRole("button", { name: /generate ai captions/i }),
    ).toBeDisabled();
  });

  test("shows upload zone and media URL input", async ({ page }) => {
    await expect(page.getByText("Drop image/video or click")).toBeVisible();
    await expect(page.getByLabel("Or paste Google Drive URL")).toBeVisible();
  });

  test("generate captions flow", async ({ page }) => {
    await page.route("**/api/generate-sync", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          captions: {
            instagram: "Test IG caption for kirtan",
            facebook: "Test FB caption for kirtan",
          },
          row_id: 1,
        }),
      }),
    );

    await page
      .getByLabel(/what do you want to post/i)
      .fill("Morning kirtan at the temple");
    await page.getByLabel("Instagram").click();
    await page.getByLabel("Facebook").click();

    await page.getByRole("button", { name: /generate ai captions/i }).click();

    await expect(page.getByText("Test IG caption for kirtan")).toBeVisible();
    await expect(page.getByText("Test FB caption for kirtan")).toBeVisible();
  });

  test("caption cards show iteration and send controls", async ({ page }) => {
    await page.route("**/api/generate-sync", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          captions: { instagram: "Test caption for controls" },
          row_id: 1,
        }),
      }),
    );

    await page.getByLabel(/what do you want to post/i).fill("Test content");
    await page.getByLabel("Instagram").click();
    await page.getByRole("button", { name: /generate ai captions/i }).click();

    await expect(page.getByText("Test caption for controls")).toBeVisible();
    await expect(
      page.getByPlaceholder(/iteration instruction/i),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /send to postiz/i }),
    ).toBeVisible();
  });

  test("send to Postiz shows success message", async ({ page }) => {
    await page.route("**/api/generate-sync", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          captions: { instagram: "Caption to send" },
          row_id: 1,
        }),
      }),
    );
    await page.route("**/api/send-to-postiz", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          draft_ids: ["d1"],
          platforms: ["instagram"],
        }),
      }),
    );

    await page.getByLabel(/what do you want to post/i).fill("Test");
    await page.getByLabel("Instagram").click();
    await page.getByRole("button", { name: /generate ai captions/i }).click();
    await expect(page.getByText("Caption to send")).toBeVisible();

    await page.getByRole("button", { name: /send to postiz/i }).click();
    await expect(page.getByText(/sent to postiz/i)).toBeVisible();
  });

  test("inline caption editing", async ({ page }) => {
    await page.route("**/api/generate-sync", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          captions: { instagram: "Original caption" },
          row_id: 1,
        }),
      }),
    );

    await page.getByLabel(/what do you want to post/i).fill("Test");
    await page.getByLabel("Instagram").click();
    await page.getByRole("button", { name: /generate ai captions/i }).click();
    await expect(page.getByText("Original caption")).toBeVisible();

    // The caption textarea in the result card
    const captionTextarea = page.locator(
      "textarea.font-mono",
    );
    await captionTextarea.fill("Edited caption text");
    await expect(captionTextarea).toHaveValue("Edited caption text");
  });
});
