import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { CreatePage } from "./CreatePage";

// Mock api + request
vi.mock("@/lib/api", () => ({
  api: {
    uploadFile: vi.fn(),
    reprompt: vi.fn(),
    sendToPostiz: vi.fn(),
    getTemplates: vi.fn(),
    generateFromTemplate: vi.fn(),
    iterate: vi.fn(),
    getIterations: vi.fn(),
    editDraft: vi.fn(),
  },
  request: vi.fn(),
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

import { api, request } from "@/lib/api";
const mockRequest = vi.mocked(request);
const mockSendToPostiz = vi.mocked(api.sendToPostiz);
const mockGetTemplates = vi.mocked(api.getTemplates);
const mockGenerateFromTemplate = vi.mocked(api.generateFromTemplate);
const mockIterate = vi.mocked(api.iterate);

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

const sampleTemplates = [
  {
    id: 1,
    name: "Weekly Farm Update",
    pillar: "community",
    platform_instructions: {},
    raw_text_template: "This week at {{location}}: {{topic}}",
    variables: [
      { name: "location", type: "text" },
      { name: "topic", type: "text" },
    ],
    schedule_pattern: null,
    default_segment_id: null,
    created_at: "2026-03-17T12:00:00",
    updated_at: null,
  },
];

describe("CreatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetTemplates.mockResolvedValue([]);
    vi.mocked(api.getIterations).mockResolvedValue([]);
  });

  it("renders form fields", () => {
    renderCreate();
    expect(screen.getByLabelText(/what do you want to post about/i)).toBeInTheDocument();
    expect(screen.getByText(/platforms/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate/i })).toBeInTheDocument();
  });

  it("requires raw text and at least one platform", async () => {
    const user = userEvent.setup();
    renderCreate();
    await user.click(screen.getByRole("button", { name: /generate/i }));
    // Should show validation - request should not have been called
    expect(mockRequest).not.toHaveBeenCalled();
  });

  it("calls generate-sync endpoint when form is valid", async () => {
    const user = userEvent.setup();
    mockRequest.mockResolvedValue({ captions: { instagram: "Test caption" } });

    renderCreate();

    await user.type(screen.getByLabelText(/what do you want to post about/i), "Post about the farm");
    await user.click(screen.getByLabelText(/instagram/i));
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "/api/generate-sync",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });
  });

  it("shows generated captions after request completes", async () => {
    const user = userEvent.setup();
    mockRequest.mockResolvedValue({ captions: { instagram: "Generated IG caption" } });

    renderCreate();

    await user.type(screen.getByLabelText(/what do you want to post about/i), "Post about cows");
    await user.click(screen.getByLabelText(/instagram/i));
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByText("Generated IG caption")).toBeInTheDocument();
    });
  });

  it("shows send to postiz button after generation", async () => {
    const user = userEvent.setup();
    mockRequest.mockResolvedValue({ captions: { instagram: "Caption" } });
    mockSendToPostiz.mockResolvedValue({ draft_ids: ["d1"], platforms: ["instagram"] });

    renderCreate();

    await user.type(screen.getByLabelText(/what do you want to post about/i), "Content");
    await user.click(screen.getByLabelText(/instagram/i));
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /send to postiz/i })).toBeInTheDocument();
    });
  });

  // --- Template selector ---

  it("shows template selector when templates are available", async () => {
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    renderCreate();

    await waitFor(() => {
      expect(screen.getByText(/template/i)).toBeInTheDocument();
    });
  });

  it("shows variable inputs when a template is selected", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    renderCreate();

    // Switch to template tab
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /use a template/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("tab", { name: /use a template/i }));

    await waitFor(() => {
      expect(screen.getByText("Weekly Farm Update")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Weekly Farm Update"));

    await waitFor(() => {
      expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/topic/i)).toBeInTheDocument();
    });
  });

  it("shows template preview when template is selected", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    renderCreate();

    // Switch to template tab
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /use a template/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("tab", { name: /use a template/i }));

    await waitFor(() => {
      expect(screen.getByText("Weekly Farm Update")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Weekly Farm Update"));

    await waitFor(() => {
      expect(screen.getByText(/fill in the fields/i)).toBeInTheDocument();
    });
  });

  // --- Inline iteration after generation ---

  it("shows per-platform iterate button after generation", async () => {
    const user = userEvent.setup();
    mockRequest.mockResolvedValue({
      captions: { instagram: "IG caption" },
      row_id: 42,
    });

    renderCreate();

    await user.type(screen.getByLabelText(/what do you want to post about/i), "Content");
    await user.click(screen.getByLabelText(/instagram/i));
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/instruction/i)).toBeInTheDocument();
    });
  });
});
