import { StrictMode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, api: { ...actual.api, publishNow: vi.fn() } };
});
vi.mock("sonner", () => ({ toast: { success: vi.fn(), warning: vi.fn(), error: vi.fn() } }));

import { api, ApiError } from "@/lib/api";
import { PublishModal } from "@/components/publish/PublishModal";

describe("PublishModal under React StrictMode (regression: result must deliver)", () => {
  beforeEach(() => vi.clearAllMocks());
  it("shows the error banner when publishNow rejects (fires exactly once)", async () => {
    vi.mocked(api.publishNow).mockRejectedValue(new ApiError(502, "Postiz error: 401"));
    const qc = new QueryClient();
    render(
      <StrictMode>
        <QueryClientProvider client={qc}>
          <PublishModal rowId={3} platforms={["instagram"]} title="t" onClose={() => {}} />
        </QueryClientProvider>
      </StrictMode>,
    );
    const alert = await screen.findByRole("alert");
    // Friendly copy in the banner; the raw backend detail lives in title.
    expect(alert).toHaveTextContent(
      "Couldn't reach Postiz — check the connection on the Health page.",
    );
    expect(alert).toHaveAttribute("title", "Postiz error: 401");
    expect(api.publishNow).toHaveBeenCalledTimes(1);
  });
});
