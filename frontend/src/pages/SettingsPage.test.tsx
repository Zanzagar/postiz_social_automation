import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SettingsPage } from "./SettingsPage";
import type { Pillar, PlatformPublishConfig } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getPublishConfig: vi.fn(),
    updatePublishConfig: vi.fn(),
    getPillars: vi.fn(),
    createPillar: vi.fn(),
    updatePillar: vi.fn(),
    deletePillar: vi.fn(),
    getVoiceRules: vi.fn(),
    updateVoiceRules: vi.fn(),
  },
  ApiError: class extends Error {
    status: number;
    detail: string;
    constructor(s: number, d: string) {
      super(d);
      this.status = s;
      this.detail = d;
    }
  },
}));

import { api } from "@/lib/api";
const mockGetConfig = vi.mocked(api.getPublishConfig);
const mockUpdateConfig = vi.mocked(api.updatePublishConfig);
const mockGetPillars = vi.mocked(api.getPillars);
const mockCreatePillar = vi.mocked(api.createPillar);
const mockUpdatePillar = vi.mocked(api.updatePillar);
const mockGetVoiceRules = vi.mocked(api.getVoiceRules);
const mockUpdateVoiceRules = vi.mocked(api.updateVoiceRules);

function makeConfig(
  overrides: Partial<PlatformPublishConfig>[] = [],
): { platforms: PlatformPublishConfig[] } {
  const base: PlatformPublishConfig[] = [
    { platform: "instagram", enabled: true, delay_hours: 2, pillar_overrides: {} },
    { platform: "facebook", enabled: true, delay_hours: 2, pillar_overrides: {} },
    { platform: "tiktok", enabled: false, delay_hours: 2, pillar_overrides: {} },
  ];
  return {
    platforms: base.map((b) => ({
      ...b,
      ...overrides.find((o) => o.platform === b.platform),
    })),
  };
}

const samplePillars: Pillar[] = [
  {
    id: 1,
    name: "Cow Life",
    description: "Tabby, Dennis, Sparkle and the herd",
    color: "#4a7c59",
    is_active: true,
    sort_order: 1,
  },
  {
    id: 2,
    name: "Spiritual",
    description: null,
    color: "#e6c46e",
    is_active: true,
    sort_order: 2,
  },
  {
    id: 3,
    name: "Retired Pillar",
    description: null,
    color: null,
    is_active: false,
    sort_order: 3,
  },
];

function renderSettings() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetConfig.mockResolvedValue(makeConfig());
  mockGetPillars.mockResolvedValue(samplePillars);
  mockGetVoiceRules.mockResolvedValue({
    rules: ["Keep posts under 60 words"],
    summary: "",
  });
  mockUpdateConfig.mockImplementation((platforms) =>
    Promise.resolve({ platforms }),
  );
});

describe("SettingsPage rail tabs", () => {
  it("renders a vertical tablist with all four sections", async () => {
    renderSettings();
    const tablist = screen.getByRole("tablist", { name: /settings sections/i });
    expect(tablist).toHaveAttribute("aria-orientation", "vertical");
    const tabs = within(tablist).getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual([
      "Publishing",
      "Brand voice",
      "Pillars",
      "Platforms",
    ]);
    expect(screen.getByRole("tab", { name: "Publishing" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("switches sections when a tab is clicked", async () => {
    const user = userEvent.setup();
    renderSettings();

    // Publishing is the default section
    await screen.findByText("Release by platform");

    await user.click(screen.getByRole("tab", { name: "Pillars" }));
    expect(await screen.findByText("Content pillars")).toBeInTheDocument();
    expect(screen.queryByText("Release by platform")).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Brand voice" }));
    expect(await screen.findByText("Voice rules")).toBeInTheDocument();
    expect(screen.getByText(/never 'gita nagari'/i)).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Platforms" }));
    expect(await screen.findByText("Connected platforms")).toBeInTheDocument();
    expect(screen.getByText("gita.valley")).toBeInTheDocument();
  });
});

describe("Publishing section", () => {
  it("loads publish config and reflects enabled state per platform", async () => {
    renderSettings();
    expect(
      await screen.findByRole("switch", { name: "Auto-release on Instagram" }),
    ).toBeChecked();
    expect(
      screen.getByRole("switch", { name: "Auto-release on TikTok" }),
    ).not.toBeChecked();
    // disabled platform shows its note, delay select disabled
    expect(
      screen.getByText("Video needs eyes — always review."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: "Release delay for TikTok" }),
    ).toBeDisabled();
  });

  it("persists an auto-release toggle change", async () => {
    const user = userEvent.setup();
    renderSettings();
    const toggle = await screen.findByRole("switch", {
      name: "Auto-release on TikTok",
    });
    await user.click(toggle);

    await waitFor(() => expect(mockUpdateConfig).toHaveBeenCalledTimes(1));
    const payload = mockUpdateConfig.mock.calls[0][0];
    expect(payload.find((c) => c.platform === "tiktok")).toMatchObject({
      enabled: true,
      delay_hours: 2,
    });
    // other platforms untouched
    expect(payload.find((c) => c.platform === "instagram")).toMatchObject({
      enabled: true,
    });
  });

  it("persists a delay change mapped to delay_hours", async () => {
    const user = userEvent.setup();
    renderSettings();
    const select = await screen.findByRole("combobox", {
      name: "Release delay for Instagram",
    });
    await user.selectOptions(select, "After 4 hours");

    await waitFor(() => expect(mockUpdateConfig).toHaveBeenCalledTimes(1));
    const payload = mockUpdateConfig.mock.calls[0][0];
    expect(payload.find((c) => c.platform === "instagram")).toMatchObject({
      delay_hours: 4,
    });
  });

  it("offers the four delay choices including immediate release", async () => {
    renderSettings();
    const select = await screen.findByRole("combobox", {
      name: "Release delay for Instagram",
    });
    const options = within(select).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual([
      "Immediately on approval",
      "After 1 hour",
      "After 2 hours",
      "After 4 hours",
    ]);
  });

  it("holding a pillar writes pillar_overrides on every platform", async () => {
    const user = userEvent.setup();
    renderSettings();
    const chip = await screen.findByRole("button", { name: /spiritual/i });
    expect(chip).toHaveAttribute("aria-pressed", "false");
    await user.click(chip);

    await waitFor(() => expect(mockUpdateConfig).toHaveBeenCalledTimes(1));
    const payload = mockUpdateConfig.mock.calls[0][0];
    expect(payload).toHaveLength(3);
    for (const config of payload) {
      expect(config.pillar_overrides).toEqual({ Spiritual: false });
    }
  });

  it("releasing a held pillar removes the override everywhere", async () => {
    mockGetConfig.mockResolvedValue(
      makeConfig([
        { platform: "instagram", pillar_overrides: { Spiritual: false } },
        { platform: "facebook", pillar_overrides: { Spiritual: false } },
        { platform: "tiktok", pillar_overrides: { Spiritual: false } },
      ]),
    );
    const user = userEvent.setup();
    renderSettings();

    const chip = await screen.findByRole("button", { name: /spiritual/i });
    expect(chip).toHaveAttribute("aria-pressed", "true");
    await user.click(chip);

    await waitFor(() => expect(mockUpdateConfig).toHaveBeenCalledTimes(1));
    const payload = mockUpdateConfig.mock.calls[0][0];
    for (const config of payload) {
      expect(config.pillar_overrides).toEqual({});
    }
  });

  it("only lists active pillars as exception chips", async () => {
    renderSettings();
    await screen.findByRole("button", { name: /cow life/i });
    expect(
      screen.queryByRole("button", { name: /retired pillar/i }),
    ).not.toBeInTheDocument();
  });

  it("seeds default rows from the platform catalog when the backend returns none", async () => {
    // Regression: {platforms: []} used to render the card header with an empty body.
    mockGetConfig.mockResolvedValue({ platforms: [] });
    const user = userEvent.setup();
    renderSettings();

    // All five catalog platforms render as editable rows, off by default
    const instagram = await screen.findByRole("switch", {
      name: "Auto-release on Instagram",
    });
    expect(instagram).not.toBeChecked();
    for (const label of ["Facebook", "TikTok", "Threads", "LinkedIn"]) {
      expect(
        screen.getByRole("switch", { name: `Auto-release on ${label}` }),
      ).not.toBeChecked();
    }

    // First change saves the full seeded set with defaults
    await user.click(instagram);
    await waitFor(() => expect(mockUpdateConfig).toHaveBeenCalledTimes(1));
    const payload = mockUpdateConfig.mock.calls[0][0];
    expect(payload).toHaveLength(5);
    expect(payload.find((c) => c.platform === "instagram")).toMatchObject({
      enabled: true,
      delay_hours: 2,
    });
    expect(payload.find((c) => c.platform === "linkedin")).toMatchObject({
      enabled: false,
      delay_hours: 2,
      pillar_overrides: {},
    });
  });

  it("shows the release explainer and per-post override demo", async () => {
    renderSettings();
    expect(await screen.findByText("How release works")).toBeInTheDocument();
    expect(
      screen.getByText(/nothing releases while held/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "Require review for this post" }),
    ).toBeInTheDocument();
  });
});

describe("Pillars section CRUD", () => {
  async function openPillars(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole("tab", { name: "Pillars" }));
    await screen.findByText("Content pillars");
  }

  it("creates a new pillar", async () => {
    mockCreatePillar.mockResolvedValue(samplePillars[0]);
    const user = userEvent.setup();
    renderSettings();
    await openPillars(user);

    await user.click(screen.getByRole("button", { name: /add pillar/i }));
    await user.type(
      screen.getByLabelText("New pillar name"),
      "Kitchen",
    );
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() =>
      expect(mockCreatePillar).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Kitchen" }),
      ),
    );
  });

  it("toggles a pillar active state", async () => {
    mockUpdatePillar.mockResolvedValue(samplePillars[0]);
    const user = userEvent.setup();
    renderSettings();
    await openPillars(user);

    await user.click(screen.getByRole("switch", { name: "Cow Life active" }));
    await waitFor(() =>
      expect(mockUpdatePillar).toHaveBeenCalledWith(1, { is_active: false }),
    );
  });

  it("edits a pillar name", async () => {
    mockUpdatePillar.mockResolvedValue(samplePillars[1]);
    const user = userEvent.setup();
    renderSettings();
    await openPillars(user);

    await user.click(screen.getByRole("button", { name: "Edit Spiritual" }));
    const nameInput = screen.getByLabelText("Edit pillar name");
    await user.clear(nameInput);
    await user.type(nameInput, "Spiritual Life");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() =>
      expect(mockUpdatePillar).toHaveBeenCalledWith(
        2,
        expect.objectContaining({ name: "Spiritual Life" }),
      ),
    );
  });
});

describe("Brand voice section", () => {
  it("adds and saves voice rules", async () => {
    mockUpdateVoiceRules.mockResolvedValue({ rules: [], summary: "" });
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole("tab", { name: "Brand voice" }));
    expect(
      await screen.findByText("Keep posts under 60 words"),
    ).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("New voice rule"),
      "Mention Daring Denise when she is in the photo",
    );
    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await user.click(screen.getByRole("button", { name: /save rules/i }));

    await waitFor(() =>
      expect(mockUpdateVoiceRules).toHaveBeenCalledWith([
        "Keep posts under 60 words",
        "Mention Daring Denise when she is in the photo",
      ]),
    );
  });
});
