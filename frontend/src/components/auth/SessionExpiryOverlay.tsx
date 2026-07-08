import { useRef, useState, type FormEvent } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Sprout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SessionExpiryOverlayProps {
  onResume: (password: string) => Promise<void>;
}

/**
 * Full-viewport re-auth modal shown when the 1-hour session lapses
 * mid-work. The routes underneath stay mounted so unsaved drafts survive —
 * staff sign back in and pick up exactly where they left off.
 *
 * Built on Radix Dialog so we get a real focus trap and aria-hidden on the
 * app beneath. It is deliberately NON-dismissable: Escape and outside
 * clicks are swallowed — the only way out is re-authenticating (the parent
 * unmounts this overlay once auth is restored).
 */
export function SessionExpiryOverlay({ onResume }: SessionExpiryOverlayProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const passwordRef = useRef<HTMLInputElement>(null);

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
    <DialogPrimitive.Root open>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50"
          style={{
            background:
              "color-mix(in oklab, var(--surface-page) 55%, transparent)",
            backdropFilter: "blur(1.5px)",
          }}
        />
        <DialogPrimitive.Content
          // Radix omits aria-modal by default; it's accurate here because
          // Radix also aria-hides everything outside the portal while open.
          aria-modal="true"
          className="border-hair bg-card fixed top-1/2 left-1/2 z-50 w-[340px] -translate-x-1/2 -translate-y-1/2 rounded-2xl p-5 outline-none"
          style={{ boxShadow: "var(--shadow-lg)" }}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            passwordRef.current?.focus();
          }}
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <div className="mb-1 flex items-center gap-2.5">
            <span className="bg-sage-50 text-sage-600 flex h-8 w-8 items-center justify-center rounded-full">
              <Sprout size={15} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <DialogPrimitive.Title className="t-title ink">
              Your session rested.
            </DialogPrimitive.Title>
          </div>
          <DialogPrimitive.Description className="t-caption ink-muted">
            Sessions close after an hour of quiet. Your draft is safe on this
            device — sign back in to pick it up.
          </DialogPrimitive.Description>
          <form onSubmit={handleSubmit}>
            <Input
              ref={passwordRef}
              type="password"
              placeholder="Farm password"
              aria-label="Farm password"
              aria-invalid={error ? true : undefined}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
              className="fr bg-card mt-3 h-10"
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
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
