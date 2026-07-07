import { useState, type FormEvent } from "react";
import { Sprout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SessionExpiryOverlayProps {
  onResume: (password: string) => Promise<void>;
}

/**
 * Full-viewport re-auth overlay shown when the 1-hour session lapses
 * mid-work. The routes underneath stay mounted so unsaved drafts survive —
 * staff sign back in and pick up exactly where they left off.
 */
export function SessionExpiryOverlay({ onResume }: SessionExpiryOverlayProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!password.trim() || isSubmitting) return;

    setError("");
    setIsSubmitting(true);
    try {
      await onResume(password);
      // Parent unmounts this overlay when auth is restored.
    } catch (err) {
      setError(
        err instanceof Error && err.message
          ? err.message
          : "That didn't work — try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-rested-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{
        background: "color-mix(in oklab, var(--surface-page) 55%, transparent)",
        backdropFilter: "blur(1.5px)",
      }}
    >
      <div
        className="w-[340px] rounded-2xl border-hair bg-card p-5"
        style={{ boxShadow: "var(--shadow-lg)" }}
      >
        <div className="mb-1 flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-sage-50 text-sage-600">
            <Sprout size={15} strokeWidth={1.75} aria-hidden="true" />
          </span>
          <div id="session-rested-title" className="t-title ink">
            Your session rested.
          </div>
        </div>
        <p className="t-caption ink-muted">
          Sessions close after an hour of quiet. Your draft is safe on this
          device — sign back in to pick it up.
        </p>
        <form onSubmit={handleSubmit}>
          <Input
            type="password"
            placeholder="Farm password"
            aria-label="Farm password"
            aria-invalid={error ? true : undefined}
            autoComplete="current-password"
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isSubmitting}
            className="fr mt-3 h-10 bg-card"
          />
          {error && (
            <div role="alert" className="t-caption mt-1.5 text-red-700">
              {error}
            </div>
          )}
          <Button
            type="submit"
            className="fr mt-2.5 w-full justify-center"
            disabled={isSubmitting || !password.trim()}
          >
            Resume where I left off
          </Button>
        </form>
      </div>
    </div>
  );
}
