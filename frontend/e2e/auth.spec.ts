import { test, expect } from "@playwright/test";
import { setupAuth, setupApiMocks, MOCK_TOKEN } from "./fixtures";

test.describe("Authentication", () => {
  test("redirects to login when not authenticated", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("shows branded login form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("Gita Valley")).toBeVisible();
    await expect(page.getByText("Cultivating Soil and Soul")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /sign in/i }),
    ).toBeVisible();
  });

  test("sign in button disabled when password empty", async ({ page }) => {
    await page.goto("/login");
    await expect(
      page.getByRole("button", { name: /sign in/i }),
    ).toBeDisabled();
  });

  test("shows error on wrong password", async ({ page }) => {
    // Use 403 to avoid the generic 401 handler which redirects + throws "Unauthorized"
    await page.route("**/api/auth/login", (route) =>
      route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Incorrect password" }),
      }),
    );

    await page.goto("/login");
    await page.getByLabel("Password").fill("wrong-password");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByRole("alert")).toContainText(
      /incorrect password/i,
    );
  });

  test("successful login redirects to dashboard", async ({ page }) => {
    await page.route("**/api/auth/login", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: MOCK_TOKEN,
          token_type: "bearer",
        }),
      }),
    );
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ authenticated: true, sub: "admin" }),
      }),
    );
    await setupApiMocks(page);

    await page.goto("/login");
    await page.getByLabel("Password").fill("correct-password");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(
      page.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();
  });

  test("redirects to dashboard when already authenticated", async ({
    page,
  }) => {
    await setupAuth(page);
    await setupApiMocks(page);

    await page.goto("/login");
    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();
  });

  test("logout clears session and redirects to login", async ({ page }) => {
    await setupAuth(page);
    await setupApiMocks(page);

    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();

    await page.getByTestId("sidebar-logout").click();
    await expect(page).toHaveURL(/\/login/);

    const token = await page.evaluate(() => localStorage.getItem("gv_token"));
    expect(token).toBeNull();
  });
});
