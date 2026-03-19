import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { TemplatesPage } from "./TemplatesPage";
import type { Template } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getTemplates: vi.fn(),
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockGetTemplates = vi.mocked(api.getTemplates);
const mockCreateTemplate = vi.mocked(api.createTemplate);
const mockDeleteTemplate = vi.mocked(api.deleteTemplate);

const sampleTemplates: Template[] = [
  {
    id: 1,
    name: "Weekly Farm Update",
    pillar: "farm",
    platform_instructions: {},
    raw_text_template: "This week at {{location}}: {{topic}}",
    variables: [
      { name: "location", type: "text" },
      { name: "topic", type: "text" },
    ],
    schedule_pattern: "weekly",
    default_segment_id: null,
    created_at: "2026-03-17T12:00:00",
    updated_at: null,
  },
  {
    id: 2,
    name: "Festival Announcement",
    pillar: "events",
    platform_instructions: {},
    raw_text_template: "Join us for {{festival}} on {{date}}!",
    variables: [
      { name: "festival", type: "text" },
      { name: "date", type: "text" },
    ],
    schedule_pattern: null,
    default_segment_id: null,
    created_at: "2026-03-17T12:00:00",
    updated_at: null,
  },
];

function renderTemplates() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <TemplatesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TemplatesPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading state", () => {
    mockGetTemplates.mockReturnValue(new Promise(() => {}));
    renderTemplates();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders template cards", async () => {
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    renderTemplates();
    await waitFor(() => {
      expect(screen.getByText("Weekly Farm Update")).toBeInTheDocument();
      expect(screen.getByText("Festival Announcement")).toBeInTheDocument();
    });
  });

  it("shows empty state when no templates", async () => {
    mockGetTemplates.mockResolvedValue([]);
    renderTemplates();
    await waitFor(() => {
      expect(screen.getByText(/no templates/i)).toBeInTheDocument();
    });
  });

  it("shows variable count on cards", async () => {
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    renderTemplates();
    await waitFor(() => {
      expect(screen.getAllByText(/2 variables/i)).toHaveLength(2);
    });
  });

  it("opens create template dialog", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue([]);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText(/no templates/i)).toBeInTheDocument();
    });

    const createButtons = screen.getAllByRole("button", { name: /create template/i });
    await user.click(createButtons[0]);

    await waitFor(() => {
      expect(screen.getByLabelText(/template name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/post template/i)).toBeInTheDocument();
    });
  });

  it("creates a template via the dialog", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue([]);
    mockCreateTemplate.mockResolvedValue(sampleTemplates[0]);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: /create template/i }).length).toBeGreaterThan(0);
    });

    const createButtons = screen.getAllByRole("button", { name: /create template/i });
    await user.click(createButtons[0]);

    await waitFor(() => {
      expect(screen.getByLabelText(/template name/i)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/template name/i), "Weekly Farm Update");
    // Use paste to avoid userEvent interpreting { as special key
    const textarea = screen.getByLabelText(/post template/i);
    await user.click(textarea);
    await user.paste("This week: {{topic}}");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(mockCreateTemplate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Weekly Farm Update",
          raw_text_template: "This week: {{topic}}",
        }),
      );
    });
  });

  it("deletes a template when delete button clicked and confirmed", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    mockDeleteTemplate.mockResolvedValue({ deleted: true });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText("Weekly Farm Update")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(mockDeleteTemplate).toHaveBeenCalledWith(1);
    });
  });
});
