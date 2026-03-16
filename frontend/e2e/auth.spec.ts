import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("redirects to login when not authenticated", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("shows login form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("Gita Valley")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("shows error on wrong password", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Password").fill("wrong-password");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/incorrect password/i)).toBeVisible();
  });

  test("login and redirect to dashboard", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Password").fill(process.env.TEST_PASSWORD ?? "test");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText("Dashboard")).toBeVisible();
  });
});
