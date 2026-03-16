import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks } from "./fixtures";

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();
  });

  test("navigate to Create page", async ({ page }) => {
    await page.getByRole("link", { name: /create/i }).first().click();
    await expect(
      page.getByRole("heading", { name: "Create & Generate" }),
    ).toBeVisible();
  });

  test("navigate to Drafts page", async ({ page }) => {
    await page.getByRole("link", { name: /drafts/i }).first().click();
    await expect(
      page.getByRole("heading", { name: "Review Drafts" }),
    ).toBeVisible();
  });

  test("navigate to Calendar page", async ({ page }) => {
    await page.getByRole("link", { name: /calendar/i }).first().click();
    await expect(
      page.getByRole("heading", { name: "Content Calendar" }),
    ).toBeVisible();
  });

  test("navigate to Suggestions page", async ({ page }) => {
    await page.getByRole("link", { name: /suggestions/i }).first().click();
    await expect(
      page.getByRole("heading", { name: "Content Suggestions" }),
    ).toBeVisible();
  });

  test("navigate to Health page", async ({ page }) => {
    await page.getByRole("link", { name: /health/i }).first().click();
    await expect(
      page.getByRole("heading", { name: "System Health" }),
    ).toBeVisible();
  });

  test("sidebar shows all navigation items", async ({ page }) => {
    const nav = page.getByTestId("sidebar-nav");
    await expect(nav.getByText("Dashboard")).toBeVisible();
    await expect(nav.getByText("Create")).toBeVisible();
    await expect(nav.getByText("Drafts")).toBeVisible();
    await expect(nav.getByText("Calendar")).toBeVisible();
    await expect(nav.getByText("Suggestions")).toBeVisible();
    await expect(nav.getByText("Health")).toBeVisible();
  });

  test("sidebar shows branding", async ({ page }) => {
    await expect(page.getByText("Gita Valley")).toBeVisible();
    await expect(page.getByText("Content Hub")).toBeVisible();
  });
});
