import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CreatePage } from "./CreatePage";
import type { IterationRecord, Pillar } from "@/lib/api";
import type { CreateDraft } from "@/hooks/useLocalDraft";

vi.mock("@/lib/api", () => ({
  api: {
    getPillars: vi.fn(),
    getTemplates: vi.fn(),
    getFestivals: vi.fn(),
    uploadFile: vi.fn(),
    iterate: vi.fn(),
    getIterations: vi.fn(),
    revertCaption: vi.fn(),
    editDraft: vi.fn(),
    sendToPostiz: vi.fn(),
    setAltText: vi.fn(),
  },
  request: vi.fn(),
  fetchGenerateStream: vi.fn(),
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

import { api, fetchGenerateStream, request } from "@/lib/api";

const mockFetchGenerateStream = vi.mocked(fetchGenerateStream);
const mockRequest = vi.mocked(request);

const samplePillars: Pillar[] = [
  {
    id: 1,
    name: "Cow Life",
    description: null,
    color: "#4a7c59",
    is_active: true,
    sort_order: 0,
  },
  {
    id: 2,
    name: "Community",
    description: null,
    color: "#b08968",
    is_active: true,
    sort_order: 1,
  },
];

const initialIteration: IterationRecord = {
  id: 1,
  content_row_id: 42,
  platform: "instagram",
  old_caption: null,
  new_caption: "First draft caption",
  refinement_instruction: null,
  mode: "generate",
  created_by: null,
  created_at: "2026-07-06T10:00:00Z",
};

function seedRefineDraft(overrides: Partial<CreateDraft> = {}) {
  localStorage.setItem(
    "gv-draft-create",
    JSON.stringify({
      seed: "Tabby met the new calves this morning",
      platforms: ["instagram", "threads"],
      pillar: "Cow Life",
      scheduledDate: "2026-07-10",
      scheduledTime: "08:00",
      mediaUrl: "",
      altText: "",
      stage: "refine",
      rowId: 42,
      captions: {
        instagram: "First draft caption",
        threads: "Threads draft caption",
      },
      ...overrides,
    }),
  );
}

function renderCreate() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CreatePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(api.getPillars).mockResolvedValue(samplePillars);
    vi.mocked(api.getTemplates).mockResolvedValue([]);
    vi.mocked(api.getFestivals).mockResolvedValue([]);
    vi.mocked(api.getIterations).mockResolvedValue([]);
  });

  it("gates Generate captions until a seed and at least one platform are set", async () => {
    const user = userEvent.setup();
    renderCreate();

    const generate = screen.getByRole("button", { name: /generate captions/i });
    expect(generate).toBeDisabled();

    await user.type(
      screen.getByLabelText(/the seed of an idea/i),
      "Sparkle greeted the visitors",
    );
    expect(generate).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Instagram" }));
    expect(generate).toBeEnabled();
  });

  it("streams generation progressively and advances to Refine", async () => {
    const user = userEvent.setup();
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });

    mockFetchGenerateStream.mockImplementation(async function* () {
      yield { status: "generating" } as const;
      await gate;
      yield {
        status: "platform_done",
        platform: "instagram",
        caption: "IG caption about Tabby #farm",
      } as const;
      yield {
        status: "done",
        row_id: 42,
        captions: { instagram: "IG caption about Tabby #farm" },
      } as const;
    });

    renderCreate();
    await user.type(screen.getByLabelText(/the seed of an idea/i), "Tabby update");
    await user.click(screen.getByRole("button", { name: "Instagram" }));
    await user.click(screen.getByRole("button", { name: /generate captions/i }));

    // Generate stage is live: heading + writing indicator while stream is open
    expect(screen.getByText(/shaping each voice/i)).toBeInTheDocument();
    expect(screen.getByText(/writing…/i)).toBeInTheDocument();
    expect(mockFetchGenerateStream).toHaveBeenCalledWith(
      expect.objectContaining({
        raw_text: "Tabby update",
        platforms: ["instagram"],
      }),
    );

    release();

    // platform_done reveals the caption for that platform
    await waitFor(() => {
      expect(screen.getByText(/IG caption about Tabby #farm/)).toBeInTheDocument();
    });

    // done event auto-advances to Refine (~600ms later)
    await waitFor(
      () => {
        expect(screen.getByText(/conversation with claude/i)).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it("shows the stream error and retries via the sync fallback", async () => {
    const user = userEvent.setup();
    mockFetchGenerateStream.mockImplementation(async function* () {
      yield { status: "error", message: "Claude timed out" } as const;
    });
    mockRequest.mockResolvedValue({
      captions: { instagram: "Sync caption" },
      row_id: 7,
    });

    renderCreate();
    await user.type(screen.getByLabelText(/the seed of an idea/i), "Dennis in the barn");
    await user.click(screen.getByRole("button", { name: "Instagram" }));
    await user.click(screen.getByRole("button", { name: /generate captions/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/claude timed out/i);
    });

    await user.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "/api/generate-sync",
        expect.objectContaining({ method: "POST" }),
      );
      expect(screen.getByText(/conversation with claude/i)).toBeInTheDocument();
    });
  });

  it("restores an in-progress compose draft from localStorage", async () => {
    localStorage.setItem(
      "gv-draft-create",
      JSON.stringify({
        seed: "Daring Denise found the clover patch",
        platforms: ["instagram", "facebook"],
        pillar: "Cow Life",
        stage: "compose",
      }),
    );

    renderCreate();

    expect(screen.getByLabelText(/the seed of an idea/i)).toHaveValue(
      "Daring Denise found the clover patch",
    );
    expect(screen.getByRole("button", { name: "Instagram" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Facebook" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "TikTok" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("refines a caption through the Conversation with Claude", async () => {
    const user = userEvent.setup();
    seedRefineDraft();
    vi.mocked(api.getIterations).mockResolvedValue([initialIteration]);
    vi.mocked(api.iterate).mockResolvedValue({
      caption: "Shorter caption",
      iteration_id: 2,
    });

    renderCreate();

    await waitFor(() => {
      expect(screen.getByLabelText("Instagram caption")).toHaveValue("First draft caption");
    });

    // Iteration history renders
    expect(await screen.findByText(/claude · initial draft/i)).toBeInTheDocument();

    // Quick chip fills the instruction, Refine calls the API
    await user.click(screen.getByRole("button", { name: "Shorter" }));
    expect(screen.getByLabelText(/refinement instruction/i)).toHaveValue("Shorter");

    await user.click(screen.getByRole("button", { name: "Refine" }));

    await waitFor(() => {
      expect(api.iterate).toHaveBeenCalledWith({
        content_row_id: 42,
        platform: "instagram",
        instruction: "Shorter",
        mode: "refine",
      });
      expect(screen.getByLabelText("Instagram caption")).toHaveValue("Shorter caption");
    });

    // History refetched after the refinement
    expect(api.getIterations).toHaveBeenCalledTimes(2);
  });

  it("warns that Threads takes no hashtags", async () => {
    seedRefineDraft({
      platforms: ["threads"],
      captions: { threads: "Morning in the pasture #farm #cows" },
    });

    renderCreate();

    await waitFor(() => {
      expect(screen.getByText(/threads convention is none/i)).toBeInTheDocument();
    });
  });

  it("disables Send to Postiz when media has no alt text", async () => {
    seedRefineDraft({ mediaUrl: "https://example.com/cow.jpg", altText: "" });

    renderCreate();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /send to postiz/i })).toBeDisabled();
    });
    expect(screen.getByText("NO ALT")).toBeInTheDocument();
    expect(
      screen.getByText(/add alt text to your image before publishing/i),
    ).toBeInTheDocument();
  });

  it("sends to Postiz and clears the local draft", async () => {
    const user = userEvent.setup();
    seedRefineDraft();
    vi.mocked(api.sendToPostiz).mockResolvedValue({
      draft_ids: ["a", "b"],
      platforms: ["instagram", "threads"],
    });

    renderCreate();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /send to postiz/i })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: /send to postiz/i }));

    await waitFor(() => {
      expect(api.sendToPostiz).toHaveBeenCalledWith({
        captions: {
          instagram: "First draft caption",
          threads: "Threads draft caption",
        },
        media_url: null,
        scheduled_at: "2026-07-10",
      });
      expect(screen.getByRole("status")).toHaveTextContent(/sent to postiz: 2 draft/i);
    });
    expect(localStorage.getItem("gv-draft-create")).toBeNull();
  });
});
