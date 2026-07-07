import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ContentRow } from "@/lib/api";
import { DraftRow } from "./DraftRow";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

function row(overrides: Partial<ContentRow> = {}): ContentRow {
  return {
    row_number: 1,
    date: "2026-07-08",
    content_pillar: "Cow Life",
    raw_text: "Sample text",
    media_url: null,
    platforms: { instagram: true },
    status: "draft",
    captions: {},
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: "manual",
    auto_publish_at: null,
    require_review: false,
    held_at: null,
    alt_text: null,
    ...overrides,
  };
}

describe("DraftRow keyboard accessibility", () => {
  it("exposes the row as a focusable button", () => {
    render(<DraftRow draft={row()} onOpen={() => {}} />);
    const rowEl = screen.getByRole("button", { name: "Sample text" });
    expect(rowEl).toHaveAttribute("tabindex", "0");
  });

  it("triggers onOpen with Enter", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<DraftRow draft={row()} onOpen={onOpen} />);
    screen.getByRole("button", { name: "Sample text" }).focus();
    await user.keyboard("{Enter}");
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("triggers onOpen with Space", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<DraftRow draft={row()} onOpen={onOpen} />);
    screen.getByRole("button", { name: "Sample text" }).focus();
    await user.keyboard(" ");
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("still triggers onOpen on click", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<DraftRow draft={row()} onOpen={onOpen} />);
    await user.click(screen.getByRole("button", { name: "Sample text" }));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("does not fire onOpen when an inner action button is activated", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<DraftRow draft={row()} onOpen={onOpen} />);
    const more = screen.getByRole("button", { name: "More actions" });
    await user.click(more);
    more.focus();
    await user.keyboard("{Enter}");
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("does not fire onOpen when the select checkbox is toggled", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    const onToggleSelect = vi.fn();
    render(
      <DraftRow
        draft={row()}
        selectable
        onToggleSelect={onToggleSelect}
        onOpen={onOpen}
      />,
    );
    await user.click(screen.getByRole("checkbox", { name: /Select/ }));
    expect(onToggleSelect).toHaveBeenCalledTimes(1);
    expect(onOpen).not.toHaveBeenCalled();
  });
});
