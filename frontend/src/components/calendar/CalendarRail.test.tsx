import { render, screen } from "@testing-library/react";
import { addDays } from "date-fns";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CalendarRail } from "./CalendarRail";
import type { Festival } from "@/lib/api";

// System time frozen to Wed 2026-07-08 (same convention as CalendarPage.test.tsx)
// so "in N days" math is deterministic.
const weekDays = Array.from({ length: 7 }, (_, i) =>
  addDays(new Date("2026-07-06T00:00:00"), i),
);

const festivals: Festival[] = [
  {
    name: "Guru Purnima",
    date: "2026-07-18",
    significance: "Honoring the guru",
    suggested_content_angles: ["Feast day — plan 2 posts", "Second angle"],
    topic: "festival",
    content_pillar: "Community",
  },
  {
    name: "Balarama Purnima",
    date: "2026-08-28",
    significance: "Appearance of Lord Balarama, the divine plow-holder",
    suggested_content_angles: [],
    topic: "festival",
    content_pillar: "Community",
  },
];

function renderRail(f: Festival[] = festivals) {
  return render(
    <CalendarRail
      entriesByDate={{}}
      weekDays={weekDays}
      colorFor={() => "#4a7c59"}
      festivals={f}
    />,
  );
}

describe("CalendarRail", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-07-08T09:00:00"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps the festival name and days-until line intact", () => {
    renderRail();
    expect(screen.getByText("Guru Purnima")).toBeInTheDocument();
    // Jul 18 is 10 days after the frozen Jul 8
    expect(screen.getByText(/in 10 days/i)).toBeInTheDocument();
  });

  it("shows the first suggested content angle as a muted note line", () => {
    renderRail();
    expect(screen.getByText("Feast day — plan 2 posts")).toBeInTheDocument();
    // Only the FIRST angle renders; significance is not shown when angles exist.
    expect(screen.queryByText("Second angle")).not.toBeInTheDocument();
    expect(screen.queryByText("Honoring the guru")).not.toBeInTheDocument();
  });

  it("falls back to the significance when no content angles exist", () => {
    renderRail();
    expect(
      screen.getByText("Appearance of Lord Balarama, the divine plow-holder"),
    ).toBeInTheDocument();
  });
});
