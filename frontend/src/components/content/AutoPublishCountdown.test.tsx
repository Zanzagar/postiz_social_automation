import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { AutoPublishCountdown } from "./AutoPublishCountdown";

describe("AutoPublishCountdown", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-17T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns null when publishAt is null", () => {
    const { container } = render(<AutoPublishCountdown publishAt={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows hours and minutes for future publish time", () => {
    render(<AutoPublishCountdown publishAt="2026-03-17T14:30:00Z" />);
    expect(screen.getByText(/auto-publish/i)).toBeInTheDocument();
    expect(screen.getByText(/2h 30m/i)).toBeInTheDocument();
  });

  it("shows minutes only when less than 1 hour", () => {
    render(<AutoPublishCountdown publishAt="2026-03-17T12:25:00Z" />);
    expect(screen.getByText(/25m/)).toBeInTheDocument();
  });

  it("shows publishing state when time has passed", () => {
    render(<AutoPublishCountdown publishAt="2026-03-17T11:00:00Z" />);
    expect(screen.getByText(/auto-publish now/i)).toBeInTheDocument();
  });
});
