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

  // Regression: the overlay used to be a plain fixed div with role="dialog"
  // but no real modality — no focus trap, no aria-hidden on the app beneath,
  // and keyboard users could tab into the dimmed background.
  describe("modality", () => {
    it("moves initial focus to the password input", () => {
      render(<SessionExpiryOverlay onResume={vi.fn()} />);

      expect(screen.getByLabelText("Farm password")).toHaveFocus();
    });

    it("traps focus: Tab cycles within the dialog", async () => {
      const user = userEvent.setup();
      render(
        <>
          <button type="button">Background action</button>
          <SessionExpiryOverlay onResume={vi.fn()} />
        </>,
      );

      const input = screen.getByLabelText("Farm password");
      // Type so the submit button is enabled (disabled buttons aren't tabbable)
      await user.type(input, "meadow");
      expect(input).toHaveFocus();

      await user.tab();
      expect(
        screen.getByRole("button", { name: "Resume where I left off" }),
      ).toHaveFocus();

      // Tab from the last tabbable wraps back inside the dialog,
      // never escaping to the background button.
      await user.tab();
      expect(input).toHaveFocus();
    });

    it("does not close on Escape", async () => {
      const user = userEvent.setup();
      render(<SessionExpiryOverlay onResume={vi.fn()} />);

      await user.keyboard("{Escape}");

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByLabelText("Farm password")).toBeInTheDocument();
    });

    it("hides the app beneath from the accessibility tree while open", () => {
      render(
        <>
          <button type="button">Background action</button>
          <SessionExpiryOverlay onResume={vi.fn()} />
        </>,
      );

      // Still in the DOM (routes stay mounted, drafts survive)...
      const background = screen.getByText("Background action");
      // ...but aria-hidden, so invisible to assistive tech / role queries.
      expect(background.closest('[aria-hidden="true"]')).not.toBeNull();
      expect(
        screen.queryByRole("button", { name: "Background action" }),
      ).not.toBeInTheDocument();
    });
  });
});
