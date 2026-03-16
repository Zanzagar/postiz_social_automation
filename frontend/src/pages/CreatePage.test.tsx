import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { CreatePage } from "./CreatePage";

// Mock api + streaming
vi.mock("@/lib/api", () => ({
  api: {
    uploadFile: vi.fn(),
    reprompt: vi.fn(),
    sendToPostiz: vi.fn(),
  },
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

import { api, fetchGenerateStream } from "@/lib/api";
const mockGenerate = vi.mocked(fetchGenerateStream);
const mockSendToPostiz = vi.mocked(api.sendToPostiz);

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
  });

  it("renders form fields", () => {
    renderCreate();
    expect(screen.getByLabelText(/raw text/i)).toBeInTheDocument();
    expect(screen.getByText(/platforms/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate/i })).toBeInTheDocument();
  });

  it("requires raw text and at least one platform", async () => {
    const user = userEvent.setup();
    renderCreate();
    await user.click(screen.getByRole("button", { name: /generate/i }));
    // Should show validation - generate should not have been called
    expect(mockGenerate).not.toHaveBeenCalled();
  });

  it("calls generate stream when form is valid", async () => {
    const user = userEvent.setup();
    // Mock the async generator
    async function* fakeStream() {
      yield { status: "generating", message: "Working on Instagram..." };
      yield { status: "done", captions: { instagram: "Test caption" } };
    }
    mockGenerate.mockReturnValue(fakeStream());

    renderCreate();

    await user.type(screen.getByLabelText(/raw text/i), "Post about the farm");
    await user.click(screen.getByLabelText(/instagram/i));
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith(
        expect.objectContaining({
          raw_text: "Post about the farm",
          platforms: ["instagram"],
        }),
      );
    });
  });

  it("shows generated captions after stream completes", async () => {
    const user = userEvent.setup();
    async function* fakeStream() {
      yield { status: "done", captions: { instagram: "Generated IG caption" } };
    }
    mockGenerate.mockReturnValue(fakeStream());

    renderCreate();

    await user.type(screen.getByLabelText(/raw text/i), "Post about cows");
    await user.click(screen.getByLabelText(/instagram/i));
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByText("Generated IG caption")).toBeInTheDocument();
    });
  });

  it("shows send to postiz button after generation", async () => {
    const user = userEvent.setup();
    async function* fakeStream() {
      yield { status: "done", captions: { instagram: "Caption" } };
    }
    mockGenerate.mockReturnValue(fakeStream());
    mockSendToPostiz.mockResolvedValue({ draft_ids: ["d1"], platforms: ["instagram"] });

    renderCreate();

    await user.type(screen.getByLabelText(/raw text/i), "Content");
    await user.click(screen.getByLabelText(/instagram/i));
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /send to postiz/i })).toBeInTheDocument();
    });
  });
});
