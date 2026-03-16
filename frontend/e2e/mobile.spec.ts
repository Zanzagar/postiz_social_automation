import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks } from "./fixtures";

test.describe("Mobile Responsive", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);
  });

  test("shows bottom nav on mobile", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("bottom-nav")).toBeVisible();
  });

  test("hides sidebar on mobile", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("sidebar-nav")).not.toBeVisible();
  });

  test("bottom nav has main navigation items", async ({ page }) => {
    await page.goto("/");
    const bottomNav = page.getByTestId("bottom-nav");
    await expect(bottomNav.getByText("Home")).toBeVisible();
    await expect(bottomNav.getByText("Create")).toBeVisible();
    await expect(bottomNav.getByText("Drafts")).toBeVisible();
    await expect(bottomNav.getByText("Calendar")).toBeVisible();
    await expect(bottomNav.getByText("More")).toBeVisible();
  });

  test("More menu shows Suggestions and Health", async ({ page }) => {
    await page.goto("/");
    const bottomNav = page.getByTestId("bottom-nav");
    await bottomNav.getByText("More").click();
    // Scope to bottom-nav to avoid matching sidebar items (hidden but in DOM)
    await expect(bottomNav.getByText("Suggestions")).toBeVisible();
    await expect(bottomNav.getByText("Health")).toBeVisible();
  });

  test("navigate via bottom nav to Create", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("bottom-nav").getByText("Create").click();
    await expect(
      page.getByRole("heading", { name: "Create & Generate" }),
    ).toBeVisible();
  });

  test("navigate via bottom nav to Drafts", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("bottom-nav").getByText("Drafts").click();
    await expect(
      page.getByRole("heading", { name: "Review Drafts" }),
    ).toBeVisible();
  });

  test("navigate to Suggestions via More menu", async ({ page }) => {
    await page.goto("/");
    const bottomNav = page.getByTestId("bottom-nav");
    await bottomNav.getByText("More").click();
    await bottomNav.getByText("Suggestions").click();
    await expect(
      page.getByRole("heading", { name: "Content Suggestions" }),
    ).toBeVisible();
  });

  test("navigate to Health via More menu", async ({ page }) => {
    await page.goto("/");
    const bottomNav = page.getByTestId("bottom-nav");
    await bottomNav.getByText("More").click();
    await bottomNav.getByText("Health").click();
    await expect(
      page.getByRole("heading", { name: "System Health" }),
    ).toBeVisible();
  });

  test("More menu closes on outside click", async ({ page }) => {
    await page.goto("/");
    const bottomNav = page.getByTestId("bottom-nav");
    await bottomNav.getByText("More").click();
    await expect(bottomNav.getByText("Suggestions")).toBeVisible();

    // Click outside the more menu
    await page.getByRole("heading", { name: "Dashboard" }).click();
    await expect(bottomNav.getByText("Suggestions")).not.toBeVisible();
  });
});
