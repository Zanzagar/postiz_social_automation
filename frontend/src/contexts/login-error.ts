/**
 * Structured login failure.
 *
 * The shared api.ts request() helper swallows 401 bodies (it dispatches
 * `gv:session-expired` and throws a generic error), so login goes through a
 * direct fetch to preserve the backend's attempts-remaining payload.
 */
export class LoginError extends Error {
  readonly status: number;
  /** From the 401 detail JSON — null when the backend sent a plain string. */
  readonly attemptsRemaining: number | null;
  /** Parsed from the 429 lockout message — null for non-lockout errors. */
  readonly retrySeconds: number | null;

  constructor(
    status: number,
    message: string,
    opts: { attemptsRemaining?: number | null; retrySeconds?: number | null } = {},
  ) {
    super(message);
    this.name = "LoginError";
    this.status = status;
    this.attemptsRemaining = opts.attemptsRemaining ?? null;
    this.retrySeconds = opts.retrySeconds ?? null;
  }
}
