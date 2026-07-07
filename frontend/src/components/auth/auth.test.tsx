import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionExpiryOverlay } from "./SessionExpiryOverlay";

describe("SessionExpiryOverlay", () => {
  it("renders a modal dialog with the rested-session copy", () => {
    render(<SessionExpiryOverlay onResume={vi.fn()} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveTextContent("Your session rested.");
    expect(dialog).toHaveTextContent(
      "Sessions close after an hour of quiet. Your draft is safe on this device — sign back in to pick it up.",
    );
    expect(screen.getByLabelText("Farm password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Resume where I left off" }),
    ).toBeInTheDocument();
  });

  it("submits the typed password to onResume", async () => {
    const onResume = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<SessionExpiryOverlay onResume={onResume} />);

    await user.type(screen.getByLabelText("Farm password"), "meadow");
    await user.click(
      screen.getByRole("button", { name: "Resume where I left off" }),
    );

    await waitFor(() => {
      expect(onResume).toHaveBeenCalledWith("meadow");
    });
  });

  it("does not submit an empty password", async () => {
    const onResume = vi.fn();
    const user = userEvent.setup();
    render(<SessionExpiryOverlay onResume={onResume} />);

    await user.click(
      screen.getByRole("button", { name: "Resume where I left off" }),
    );
    expect(onResume).not.toHaveBeenCalled();
  });

  it("shows an alert when onResume rejects", async () => {
    const onResume = vi
      .fn()
      .mockRejectedValue(new Error("Incorrect password."));
    const user = userEvent.setup();
    render(<SessionExpiryOverlay onResume={onResume} />);

    await user.type(screen.getByLabelText("Farm password"), "wrong");
    await user.click(
      screen.getByRole("button", { name: "Resume where I left off" }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Incorrect password.");
  });
});
