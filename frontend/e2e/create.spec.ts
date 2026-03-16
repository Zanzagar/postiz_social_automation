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
    await expect(page.getByLabel("Raw Text")).toBeVisible();
    await expect(page.getByText("Platforms")).toBeVisible();
    await expect(page.getByLabel("Schedule Date")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /generate captions/i }),
    ).toBeVisible();
  });

  test("shows character count that updates", async ({ page }) => {
    await expect(page.getByText("0/2000")).toBeVisible();
    await page.getByLabel("Raw Text").fill("Hello world");
    await expect(page.getByText("11/2000")).toBeVisible();
  });

  test("shows all platform checkboxes", async ({ page }) => {
    await expect(page.getByLabel("Instagram")).toBeVisible();
    await expect(page.getByLabel("Facebook")).toBeVisible();
    await expect(page.getByLabel("TikTok")).toBeVisible();
    await expect(page.getByLabel("Threads")).toBeVisible();
    await expect(page.getByLabel("LinkedIn")).toBeVisible();
  });

  test("shows validation error without text and platforms", async ({
    page,
  }) => {
    await page.getByRole("button", { name: /generate captions/i }).click();
    await expect(page.getByRole("alert")).toContainText(
      /enter text and select at least one platform/i,
    );
  });

  test("shows upload zone and media URL input", async ({ page }) => {
    await expect(page.getByText("Drop image/video or click")).toBeVisible();
    await expect(page.getByLabel("Or paste Google Drive URL")).toBeVisible();
  });

  test("generate captions flow with SSE", async ({ page }) => {
    await page.route("**/api/generate", (route) => {
      const sseBody = [
        'data: {"status":"generating","message":"Analyzing content..."}\n\n',
        'data: {"status":"generating","message":"Writing captions..."}\n\n',
        'data: {"status":"done","captions":{"instagram":"Test IG caption for kirtan","facebook":"Test FB caption for kirtan"}}\n\n',
      ].join("");

      return route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        body: sseBody,
      });
    });

    await page.getByLabel("Raw Text").fill("Morning kirtan at the temple");
    await page.getByLabel("Instagram").click();
    await page.getByLabel("Facebook").click();

    await page.getByRole("button", { name: /generate captions/i }).click();

    // Check for unique caption text (not platform names which appear in checkboxes too)
    await expect(page.getByText("Test IG caption for kirtan")).toBeVisible();
    await expect(page.getByText("Test FB caption for kirtan")).toBeVisible();
  });

  test("caption cards show re-prompt and send controls", async ({ page }) => {
    await page.route("**/api/generate", (route) =>
      route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        body: 'data: {"status":"done","captions":{"instagram":"Test caption for controls"}}\n\n',
      }),
    );

    await page.getByLabel("Raw Text").fill("Test content");
    await page.getByLabel("Instagram").click();
    await page.getByRole("button", { name: /generate captions/i }).click();

    await expect(page.getByText("Test caption for controls")).toBeVisible();
    await expect(
      page.getByPlaceholder(/feedback for regeneration/i),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /send to postiz/i }),
    ).toBeVisible();
  });

  test("send to Postiz shows success message", async ({ page }) => {
    await page.route("**/api/generate", (route) =>
      route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        body: 'data: {"status":"done","captions":{"instagram":"Caption to send"}}\n\n',
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

    await page.getByLabel("Raw Text").fill("Test");
    await page.getByLabel("Instagram").click();
    await page.getByRole("button", { name: /generate captions/i }).click();
    await expect(page.getByText("Caption to send")).toBeVisible();

    await page.getByRole("button", { name: /send to postiz/i }).click();
    await expect(page.getByText(/sent to postiz/i)).toBeVisible();
  });

  test("inline caption editing", async ({ page }) => {
    await page.route("**/api/generate", (route) =>
      route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        body: 'data: {"status":"done","captions":{"instagram":"Original caption"}}\n\n',
      }),
    );

    await page.getByLabel("Raw Text").fill("Test");
    await page.getByLabel("Instagram").click();
    await page.getByRole("button", { name: /generate captions/i }).click();
    await expect(page.getByText("Original caption")).toBeVisible();

    const captionTextarea = page.locator("textarea").last();
    await captionTextarea.fill("Edited caption text");
    await expect(captionTextarea).toHaveValue("Edited caption text");
  });
});
