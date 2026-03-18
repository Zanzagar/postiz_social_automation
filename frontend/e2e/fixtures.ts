import { type Page } from "@playwright/test";

// --- Mock JWT Token ---
// Payload: { sub: "admin", exp: 9999999999 } (expires ~2286, never in tests)
function base64url(obj: object): string {
  return Buffer.from(JSON.stringify(obj))
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

export const MOCK_TOKEN = [
  base64url({ alg: "HS256", typ: "JWT" }),
  base64url({ sub: "admin", exp: 9999999999 }),
  "test-signature",
].join(".");

// --- Mock API Data ---

export const mockDrafts = [
  {
    row_number: 1,
    date: "2026-03-20",
    content_pillar: "Spiritual Education",
    raw_text:
      "Join us for morning kirtan at the temple. Experience the transformative power of chanting.",
    media_url: "https://drive.google.com/test/image1.jpg",
    platforms: {
      instagram: true,
      facebook: true,
      tiktok: false,
      threads: false,
      linkedin: false,
    },
    status: "draft",
    captions: {
      instagram: "Join us for morning kirtan at the temple...",
      facebook:
        "Experience the transformative power of chanting at Gita Valley...",
    },
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "sheet",
  },
  {
    row_number: 2,
    date: "2026-03-21",
    content_pillar: "Farm & Community",
    raw_text:
      "Fresh organic vegetables from our garden. Farm to table, blessed by devotion.",
    media_url: null,
    platforms: {
      instagram: true,
      facebook: false,
      tiktok: true,
      threads: false,
      linkedin: false,
    },
    status: "draft",
    captions: {
      instagram: "Fresh from the garden...",
      tiktok: "Farm fresh veggies, blessed by devotion",
    },
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "sheet",
  },
];

export const mockCalendar = {
  entries: [
    {
      row_number: 1,
      date: "2026-03-20",
      content_pillar: "Spiritual Education",
      raw_text: "Join us for morning kirtan at the temple.",
      status: "scheduled",
      platforms: { instagram: true, facebook: true },
      captions: { instagram: "Join us...", facebook: "Experience..." },
    },
    {
      row_number: 3,
      date: "2026-03-20",
      content_pillar: "Events",
      raw_text: "Spring festival celebration this weekend.",
      status: "draft",
      platforms: { instagram: true, tiktok: true },
      captions: { instagram: "Spring festival...", tiktok: "Festival vibes..." },
    },
    {
      row_number: 4,
      date: "2026-03-22",
      content_pillar: "Behind the Scenes",
      raw_text: "A day in the life at the farm.",
      status: "posted",
      platforms: { instagram: true },
      captions: { instagram: "A beautiful day..." },
    },
  ],
  total: 3,
};

export const mockSuggestions = [
  {
    suggested_date: "2026-03-25",
    content_idea: "Showcase the new greenhouse construction",
    suggested_pillar: "Farm & Community",
    rationale:
      "Community members have been asking about the new greenhouse project. Visual progress updates drive engagement.",
    media_suggestion: "Photo of the greenhouse frame with workers",
    status: "pending",
  },
  {
    suggested_date: "2026-03-27",
    content_idea: "Bhagavad Gita verse of the week",
    suggested_pillar: "Spiritual Education",
    rationale:
      "Weekly scripture posts consistently get the highest engagement rates.",
    media_suggestion: "Graphic with verse text overlay on nature background",
    status: "pending",
  },
];

export const mockHealth = {
  services: [
    {
      name: "Postiz",
      status: "healthy",
      message: "Connected",
      last_checked: "2026-03-16T15:00:00Z",
    },
    {
      name: "Google Sheets",
      status: "healthy",
      message: "Accessible",
      last_checked: "2026-03-16T15:00:00Z",
    },
    {
      name: "Content Engine",
      status: "degraded",
      message: "High latency",
      last_checked: "2026-03-16T14:55:00Z",
    },
  ],
  errors: [],
};

export const mockIntegrations = [
  { id: "int-1", platform: "instagram", name: "Gita Valley IG" },
  { id: "int-2", platform: "facebook", name: "Gita Valley FB" },
];

// --- Helper Functions ---

/**
 * Set up authenticated state by injecting token into localStorage
 * and mocking the /api/auth/me endpoint.
 */
export async function setupAuth(page: Page): Promise<void> {
  await page.addInitScript((token) => {
    localStorage.setItem("gv_token", token);
  }, MOCK_TOKEN);

  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ authenticated: true, sub: "admin" }),
    }),
  );
}

/**
 * Set up all API mocks with standard data.
 */
export async function setupApiMocks(page: Page): Promise<void> {
  await page.route("**/api/drafts", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockDrafts),
      });
    }
    return route.continue();
  });

  await page.route("**/api/calendar", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockCalendar),
    }),
  );

  await page.route("**/api/suggestions", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockSuggestions),
    }),
  );

  await page.route("**/api/health", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockHealth),
    }),
  );

  await page.route("**/api/integrations", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockIntegrations),
    }),
  );

  await page.route("**/api/templates", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "[]",
    }),
  );

  await page.route("**/api/settings/publish", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        enabled: false,
        delay_hours: 24,
        platforms: {},
        pillar_overrides: {},
      }),
    }),
  );
}

/**
 * Set up empty API mocks for testing empty states.
 */
export async function setupEmptyApiMocks(page: Page): Promise<void> {
  await page.route("**/api/drafts", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/calendar", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ entries: [], total: 0 }),
    }),
  );
  await page.route("**/api/suggestions", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/health", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ services: [], errors: [] }),
    }),
  );
  await page.route("**/api/integrations", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/templates", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/settings/publish", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        enabled: false,
        delay_hours: 24,
        platforms: {},
        pillar_overrides: {},
      }),
    }),
  );
}
