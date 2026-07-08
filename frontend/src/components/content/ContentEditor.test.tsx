import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ContentEditor } from "./ContentEditor";
import type { ContentRow } from "@/lib/api";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    iterate: vi.fn(),
    getIterations: vi.fn(),
    editDraft: vi.fn(),
    getContentRow: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockIterate = vi.mocked(api.iterate);
const mockGetIterations = vi.mocked(api.getIterations);
vi.mocked(api.editDraft);

const sampleRow: ContentRow = {
  row_number: 1,
  date: "2026-03-20",
  content_pillar: "spiritual_education",
  raw_text: "About cow protection at Gita Valley",
  media_url: null,
  platforms: { instagram: true, facebook: true },
  status: "draft",
  captions: {
    instagram: "IG caption about cow protection 🐄",
    facebook: "FB caption about cow protection",
  },
  feedback: null,
  postiz_ids: null,
  posted_at: null,
  error_msg: null,
  source: "manual",
  auto_publish_at: null,
  require_review: false,
  held_at: null,
  alt_text: null,
};

function renderEditor(
  props: Partial<React.ComponentProps<typeof ContentEditor>> = {},
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const defaultProps = {
    contentRow: sampleRow,
    mode: "refine" as const,
    isOpen: true,
    onClose: vi.fn(),
    onSave: vi.fn(),
  };
  return {
    ...render(
      <QueryClientProvider client={qc}>
        <ContentEditor {...defaultProps} {...props} />
      </QueryClientProvider>,
    ),
    onClose: props.onClose ?? defaultProps.onClose,
    onSave: props.onSave ?? defaultProps.onSave,
  };
}

describe("ContentEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetIterations.mockResolvedValue([]);
  });

  // --- Mode rendering ---

  it("renders refine mode with correct title", () => {
    renderEditor({ mode: "refine" });
    expect(screen.getByText(/refine content/i)).toBeInTheDocument();
  });

  it("renders create mode with correct title", () => {
    renderEditor({ mode: "create" });
    expect(screen.getByText(/create content/i)).toBeInTheDocument();
  });

  it("renders repurpose mode with correct title", () => {
    renderEditor({ mode: "repurpose" });
    expect(screen.getByText(/repurpose content/i)).toBeInTheDocument();
  });

  // --- Platform tabs ---

  it("shows tabs for each platform in captions", () => {
    renderEditor();
    expect(screen.getByRole("tab", { name: /instagram/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /facebook/i })).toBeInTheDocument();
  });

  it("shows caption text in active tab", () => {
    renderEditor();
    // First tab (instagram) should be active by default
    expect(
      screen.getByDisplayValue("IG caption about cow protection 🐄"),
    ).toBeInTheDocument();
  });

  // --- Iteration ---

  it("calls iterate API when iterate button is clicked", async () => {
    const user = userEvent.setup();
    mockIterate.mockResolvedValue({ caption: "Improved IG caption", iteration_id: 1 });

    renderEditor();

    const instructionInput = screen.getByPlaceholderText(/instruction/i);
    await user.type(instructionInput, "Make it shorter");
    await user.click(screen.getByRole("button", { name: /iterate/i }));

    await waitFor(() => {
      expect(mockIterate).toHaveBeenCalledWith(
        expect.objectContaining({
          content_row_id: 1,
          platform: "instagram",
          instruction: "Make it shorter",
        }),
      );
    });
  });

  it("updates caption after successful iteration", async () => {
    const user = userEvent.setup();
    mockIterate.mockResolvedValue({ caption: "Improved IG caption", iteration_id: 1 });

    renderEditor();

    const instructionInput = screen.getByPlaceholderText(/instruction/i);
    await user.type(instructionInput, "Make it shorter");
    await user.click(screen.getByRole("button", { name: /iterate/i }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Improved IG caption")).toBeInTheDocument();
    });
  });

  // --- History ---

  it("loads iteration history on open", async () => {
    mockGetIterations.mockResolvedValue([
      {
        id: 1,
        content_row_id: 1,
        platform: "instagram",
        old_caption: "Original",
        new_caption: "Refined",
        refinement_instruction: "Make shorter",
        mode: "refine",
        created_by: null,
        created_at: "2026-03-17T12:00:00",
      },
    ]);

    renderEditor();

    await waitFor(() => {
      expect(mockGetIterations).toHaveBeenCalledWith(1);
    });
  });

  // --- Close ---

  it("calls onClose when dialog is dismissed", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderEditor({ onClose });

    // Click the footer Close button (variant="outline", not the X icon)
    const closeButtons = screen.getAllByRole("button", { name: /close/i });
    // The footer Close is the outline variant button (last one)
    const footerClose = closeButtons[closeButtons.length - 1];
    await user.click(footerClose);
    expect(onClose).toHaveBeenCalled();
  });

  // --- Not rendered when closed ---

  it("does not render content when isOpen is false", () => {
    renderEditor({ isOpen: false });
    expect(screen.queryByText(/refine content/i)).not.toBeInTheDocument();
  });
});
