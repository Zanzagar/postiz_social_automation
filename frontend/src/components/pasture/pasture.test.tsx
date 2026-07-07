import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  Chip,
  CountdownChip,
  GVSheet,
  PillarChip,
  PlatformDots,
  SegmentedControl,
  StatusPill,
  Toggle,
} from "./index";

describe("CountdownChip", () => {
  it("renders label and remaining while counting", () => {
    render(
      <CountdownChip label="Releases 4:30 PM" remaining="in 2h 14m" onToggle={() => {}} />,
    );
    expect(screen.getByText("Releases 4:30 PM")).toBeInTheDocument();
    expect(screen.getByText("in 2h 14m")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Pause and hold for review" }),
    ).toHaveTextContent("Hold");
  });

  it("calls onToggle when Hold is clicked", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<CountdownChip label="Releases 4:30 PM" remaining="in 2h" onToggle={onToggle} />);

    await user.click(screen.getByRole("button", { name: "Pause and hold for review" }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("shows 'Held for review' and Resume when paused", () => {
    render(<CountdownChip paused onToggle={() => {}} />);
    expect(screen.getByText("Held for review")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resume auto-release" })).toHaveTextContent(
      "Resume",
    );
    // remaining is hidden while held
    expect(screen.queryByText("in 1h 24m")).not.toBeInTheDocument();
  });
});

describe("Toggle", () => {
  it("renders a switch with aria-checked reflecting checked state", () => {
    const { rerender } = render(
      <Toggle checked={false} onChange={() => {}} aria-label="Auto-publish" />,
    );
    const sw = screen.getByRole("switch", { name: "Auto-publish" });
    expect(sw).toHaveAttribute("aria-checked", "false");

    rerender(<Toggle checked onChange={() => {}} aria-label="Auto-publish" />);
    expect(screen.getByRole("switch", { name: "Auto-publish" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("calls onChange with the flipped value on click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Toggle checked={false} onChange={onChange} aria-label="Auto-publish" />);

    await user.click(screen.getByRole("switch"));
    expect(onChange).toHaveBeenCalledWith(true);
  });
});

describe("SegmentedControl", () => {
  it("renders a radiogroup and selects on click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SegmentedControl
        options={["week", "month", "list"]}
        value="week"
        onChange={onChange}
        aria-label="Calendar view"
      />,
    );

    expect(screen.getByRole("radiogroup", { name: "Calendar view" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "week" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: "month" })).toHaveAttribute(
      "aria-checked",
      "false",
    );

    await user.click(screen.getByRole("radio", { name: "month" }));
    expect(onChange).toHaveBeenCalledWith("month");
  });
});

describe("Chip", () => {
  it("renders a removable chip with an accessible Remove button", async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    render(
      <Chip tone="sage" removable onRemove={onRemove}>
        #FarmFeast
      </Chip>,
    );

    expect(screen.getByText("#FarmFeast")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove" }));
    expect(onRemove).toHaveBeenCalledTimes(1);
  });
});

describe("PillarChip", () => {
  it("renders the pillar name", () => {
    render(<PillarChip pillar={{ name: "Cow Life" }} />);
    expect(screen.getByText("Cow Life")).toBeInTheDocument();
  });
});

describe("PlatformDots", () => {
  it("renders one dot per platform id", () => {
    const { container } = render(<PlatformDots ids={["instagram", "facebook"]} />);
    expect(container.querySelectorAll("span[aria-hidden='true']").length).toBeGreaterThanOrEqual(
      2,
    );
  });
});

describe("GVSheet", () => {
  it("renders the title as an accessible dialog", () => {
    render(
      <GVSheet title="Edit post" onClose={() => {}}>
        <p>Body content</p>
      </GVSheet>,
    );
    expect(screen.getByRole("dialog", { name: "Edit post" })).toBeInTheDocument();
    expect(screen.getByText("Body content")).toBeInTheDocument();
  });

  it("calls onClose when Escape is pressed", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <GVSheet title="Edit post" onClose={onClose}>
        <p>Body</p>
      </GVSheet>,
    );

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose from the Close button", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <GVSheet title="Edit post" onClose={onClose}>
        <p>Body</p>
      </GVSheet>,
    );

    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("StatusPill", () => {
  it("maps pending_approval to 'Needs review'", () => {
    render(<StatusPill status="pending_approval" />);
    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });

  it("maps backend statuses to labels", () => {
    const { rerender } = render(<StatusPill status="posted" />);
    expect(screen.getByText("Posted")).toBeInTheDocument();
    rerender(<StatusPill status="error" />);
    expect(screen.getByText("Error")).toBeInTheDocument();
    rerender(<StatusPill status="template" />);
    expect(screen.getByText("Template")).toBeInTheDocument();
  });

  it("falls back to Draft for unknown statuses", () => {
    render(<StatusPill status="???" />);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });
});
