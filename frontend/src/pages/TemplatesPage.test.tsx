import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { TemplatesPage } from "./TemplatesPage";
import type { ContentRow, Template } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getTemplates: vi.fn(),
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
    generateFromTemplate: vi.fn(),
    batchGenerateFromTemplate: vi.fn(),
    getPillars: vi.fn(),
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
const mockGetTemplates = vi.mocked(api.getTemplates);
const mockCreateTemplate = vi.mocked(api.createTemplate);
const mockUpdateTemplate = vi.mocked(api.updateTemplate);
const mockDeleteTemplate = vi.mocked(api.deleteTemplate);
const mockGenerateFromTemplate = vi.mocked(api.generateFromTemplate);
const mockBatchGenerate = vi.mocked(api.batchGenerateFromTemplate);
const mockGetPillars = vi.mocked(api.getPillars);

const sampleTemplates: Template[] = [
  {
    id: 1,
    name: "Weekly cow spotlight",
    pillar: "Cow Life",
    platform_instructions: { instagram: "", facebook: "" },
    raw_text_template: "This week we introduce {{cow_name}} — {{trait}}.",
    variables: [
      { name: "cow_name", type: "text" },
      { name: "trait", type: "text" },
    ],
    schedule_pattern: "weekly:thursday",
    schedule_time: null,
    default_segment_id: null,
    created_at: "2026-03-17T12:00:00",
    updated_at: null,
  },
  {
    id: 2,
    name: "Festival feast invite",
    pillar: null,
    platform_instructions: {},
    raw_text_template: "Tomorrow is {{festival}} at Gita Valley — feast on {{date}}.",
    variables: [
      { name: "festival", type: "text" },
      { name: "date", type: "text" },
    ],
    schedule_pattern: null,
    schedule_time: null,
    default_segment_id: null,
    created_at: "2026-03-17T12:00:00",
    updated_at: null,
  },
];

const sampleDraft: ContentRow = {
  row_number: 5,
  date: "2026-07-10",
  content_pillar: "Cow Life",
  raw_text: "This week we introduce Tabby",
  media_url: null,
  platforms: { instagram: true },
  status: "draft",
  captions: {},
  feedback: null,
  postiz_ids: null,
  posted_at: null,
  error_msg: null,
  source: "template",
  auto_publish_at: null,
  require_review: false,
  held_at: null,
  alt_text: null,
};

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

/** Paste text into the editor body (userEvent treats "{{" as special keys). */
async function pasteBody(user: ReturnType<typeof userEvent.setup>, text: string) {
  const textarea = screen.getByLabelText(/body/i);
  await user.click(textarea);
  await user.paste(text);
}

describe("TemplatesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetPillars.mockResolvedValue([
      { id: 1, name: "Cow Life", description: null, is_active: true, sort_order: 0 },
      { id: 2, name: "Festivals", description: null, is_active: true, sort_order: 1 },
    ]);
  });

  it("shows page header and loading skeleton while fetching", () => {
    mockGetTemplates.mockReturnValue(new Promise(() => {}));
    renderTemplates();
    expect(
      screen.getByRole("heading", { name: /reusable vessels/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Weekly cow spotlight")).not.toBeInTheDocument();
  });

  it("shows empty state when no templates", async () => {
    mockGetTemplates.mockResolvedValue([]);
    renderTemplates();
    await waitFor(() => {
      expect(screen.getByText(/no vessels yet/i)).toBeInTheDocument();
    });
  });

  it("renders browse cards with schedule, preview, and variable chips", async () => {
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText("Weekly cow spotlight")).toBeInTheDocument();
    });
    expect(screen.getByText("Festival feast invite")).toBeInTheDocument();
    // Schedule labels formatted from schedule_pattern
    expect(screen.getByText("Every Thursday")).toBeInTheDocument();
    expect(screen.getByText("Manual")).toBeInTheDocument();
    // Variable mono chips
    expect(screen.getByText("{{cow_name}}")).toBeInTheDocument();
    expect(screen.getByText("{{trait}}")).toBeInTheDocument();
    // Preview box highlights variables as inline chips (name without braces)
    expect(screen.getByText("cow_name")).toBeInTheDocument();
    expect(screen.getByText(/this week we introduce/i)).toBeInTheDocument();
    // Use buttons
    expect(screen.getAllByRole("button", { name: /use →/i })).toHaveLength(2);
  });

  it("deletes a template after confirmation", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    mockDeleteTemplate.mockResolvedValue({ deleted: true });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText("Weekly cow spotlight")).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole("button", { name: /delete weekly cow spotlight/i }),
    );

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(mockDeleteTemplate).toHaveBeenCalledWith(1);
    });
  });

  it("editor parses {{variables}} from the body into the variables table", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue([]);
    renderTemplates();

    await user.click(screen.getByRole("button", { name: /new template/i }));
    await pasteBody(user, "Meet {{cow_name}} — {{trait}}. Again, {{cow_name}}!");

    // Unique variables, in order of first appearance
    expect(screen.getByLabelText("Description for cow_name")).toBeInTheDocument();
    expect(screen.getByLabelText("Description for trait")).toBeInTheDocument();
    expect(screen.getAllByLabelText(/description for/i)).toHaveLength(2);
  });

  it("preview filled substitutes sample values into the body", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue([]);
    renderTemplates();

    await user.click(screen.getByRole("button", { name: /new template/i }));
    await pasteBody(user, "This week we introduce {{cow_name}} — {{trait}}.");
    await user.click(screen.getByRole("button", { name: /preview filled/i }));

    expect(
      screen.getByText(/this week we introduce Lakshmi/i),
    ).toBeInTheDocument();
    // Toggle back to edit
    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    expect(screen.getByLabelText(/body/i)).toBeInTheDocument();
  });

  it("creates a template with schedule_pattern, pillar, platforms, and parsed variables", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue([]);
    mockCreateTemplate.mockResolvedValue(sampleTemplates[0]);
    renderTemplates();

    await user.click(screen.getByRole("button", { name: /new template/i }));

    await user.type(screen.getByLabelText(/template name/i), "Weekly cow spotlight");
    await user.selectOptions(screen.getByLabelText(/trigger/i), "weekly:thursday");
    await pasteBody(user, "This week we introduce {{cow_name}} — {{trait}}.");

    // Pillar chip picker (dynamic pillars)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Cow Life" })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Cow Life" }));
    // Platform picker
    await user.click(screen.getByRole("button", { name: "Instagram" }));

    await user.click(screen.getByRole("button", { name: /save template/i }));

    await waitFor(() => {
      expect(mockCreateTemplate).toHaveBeenCalledWith({
        name: "Weekly cow spotlight",
        pillar: "Cow Life",
        raw_text_template: "This week we introduce {{cow_name}} — {{trait}}.",
        schedule_pattern: "weekly:thursday",
        platform_instructions: { instagram: "" },
        variables: [
          { name: "cow_name", type: "text" },
          { name: "trait", type: "text" },
        ],
      });
    });
  });

  it("edits an existing template and sends the update payload", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    mockUpdateTemplate.mockResolvedValue(sampleTemplates[0]);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText("Weekly cow spotlight")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Weekly cow spotlight" }));

    const nameInput = screen.getByLabelText(/template name/i);
    expect(nameInput).toHaveValue("Weekly cow spotlight");

    await user.clear(nameInput);
    await user.type(nameInput, "Thursday cow spotlight");
    await user.click(screen.getByRole("button", { name: /save template/i }));

    await waitFor(() => {
      expect(mockUpdateTemplate).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          name: "Thursday cow spotlight",
          schedule_pattern: "weekly:thursday",
          raw_text_template: "This week we introduce {{cow_name}} — {{trait}}.",
        }),
      );
    });
  });

  it("use flow collects variable values and calls generateFromTemplate", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    mockGenerateFromTemplate.mockResolvedValue(sampleDraft);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText("Weekly cow spotlight")).toBeInTheDocument();
    });
    await user.click(screen.getAllByRole("button", { name: /use →/i })[0]);

    const sheet = await screen.findByRole("dialog");
    await user.type(within(sheet).getByLabelText("{{cow_name}}"), "Tabby");
    await user.type(within(sheet).getByLabelText("{{trait}}"), "the boldest of the herd");
    fireEvent.change(within(sheet).getByLabelText(/scheduled date/i), {
      target: { value: "2026-07-10" },
    });
    await user.click(within(sheet).getByRole("button", { name: /create draft/i }));

    await waitFor(() => {
      expect(mockGenerateFromTemplate).toHaveBeenCalledWith(1, {
        variable_values: {
          cow_name: "Tabby",
          trait: "the boldest of the herd",
        },
        platforms: ["instagram", "facebook"],
        scheduled_date: "2026-07-10",
        scheduled_time: undefined,
      });
    });
    expect(await within(sheet).findByRole("status")).toHaveTextContent(
      /draft created/i,
    );
  });

  it("batch mode for weekly templates calls batchGenerateFromTemplate and shows the shells note", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    mockBatchGenerate.mockResolvedValue({ created: 3, drafts: [] });
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText("Weekly cow spotlight")).toBeInTheDocument();
    });
    await user.click(screen.getAllByRole("button", { name: /use →/i })[0]);

    const sheet = await screen.findByRole("dialog");
    // Weekly template offers the batch mode switch
    await user.click(within(sheet).getByRole("radio", { name: /weekly batch/i }));

    const weeksInput = within(sheet).getByLabelText(/weeks/i);
    fireEvent.change(weeksInput, { target: { value: "3" } });

    await user.click(
      within(sheet).getByRole("button", { name: /create 3 draft shells/i }),
    );

    await waitFor(() => {
      expect(mockBatchGenerate).toHaveBeenCalledWith(1, {
        variable_values: {},
        platforms: ["instagram", "facebook"],
        weeks: 3,
        scheduled_time: undefined,
      });
    });
    expect(await within(sheet).findByRole("status")).toHaveTextContent(
      "3 draft shells created — staff fill each before generating.",
    );
  });

  it("non-weekly templates do not offer batch mode", async () => {
    const user = userEvent.setup();
    mockGetTemplates.mockResolvedValue(sampleTemplates);
    renderTemplates();

    await waitFor(() => {
      expect(screen.getByText("Festival feast invite")).toBeInTheDocument();
    });
    await user.click(screen.getAllByRole("button", { name: /use →/i })[1]);

    const sheet = await screen.findByRole("dialog");
    expect(
      within(sheet).queryByRole("radio", { name: /weekly batch/i }),
    ).not.toBeInTheDocument();
    expect(within(sheet).getByLabelText(/scheduled date/i)).toBeInTheDocument();
  });
});
