import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Clock } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { LoginError } from "@/contexts/login-error";
import { GVMark } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

interface LockoutCardProps {
  remainingSeconds: number;
}

function LockoutCard({ remainingSeconds }: LockoutCardProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-cream-300 bg-cream-100 p-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-cream-300/70 text-cream-ink-deep">
        <Clock size={16} strokeWidth={1.75} aria-hidden="true" />
      </div>
      <div className="flex-1">
        <div className="t-body font-semibold text-cream-ink-deep">
          Too many tries — the gate is resting.
        </div>
        <p className="t-caption mt-0.5 text-cream-ink">
          Try again in{" "}
          <span className="font-mono font-semibold">
            {formatCountdown(remainingSeconds)}
          </span>
          . If you've lost the password, ask whoever tends the server.
        </p>
      </div>
    </div>
  );
}

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [wrongPassword, setWrongPassword] = useState(false);
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(
    null,
  );
  const [genericError, setGenericError] = useState("");
  const [lockUntil, setLockUntil] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Lockout countdown — ticks every second until the gate reopens.
  useEffect(() => {
    if (lockUntil == null) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [lockUntil]);

  const lockRemaining =
    lockUntil != null ? Math.max(0, Math.ceil((lockUntil - now) / 1000)) : 0;
  const isLocked = lockUntil != null && lockRemaining > 0;

  useEffect(() => {
    if (lockUntil != null && lockRemaining <= 0) {
      setLockUntil(null);
    }
  }, [lockUntil, lockRemaining]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!password.trim() || isSubmitting || isLocked) return;

    setWrongPassword(false);
    setGenericError("");
    setIsSubmitting(true);
    try {
      await login(password);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof LoginError && err.status === 401) {
        setWrongPassword(true);
        setAttemptsRemaining(err.attemptsRemaining);
      } else if (err instanceof LoginError && err.status === 429) {
        const seconds = err.retrySeconds ?? 300;
        setNow(Date.now());
        setLockUntil(Date.now() + seconds * 1000);
      } else if (err instanceof LoginError) {
        setGenericError(err.message);
      } else {
        setGenericError("Something went wrong — try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-svh grid-cols-1 md:grid-cols-[54%_46%]">
      {/* Brand side */}
      <div
        className="relative hidden flex-col justify-between overflow-hidden p-14 text-cream-100 md:flex"
        style={{
          background:
            "radial-gradient(120% 90% at 15% 10%, #2d4a35 0%, #1e3224 55%, #101a13 100%)",
        }}
      >
        <div
          className="absolute inset-0 opacity-[0.35]"
          aria-hidden="true"
          style={{
            background:
              "radial-gradient(circle at 80% 85%, rgba(230,196,110,.14) 0, transparent 45%), radial-gradient(circle at 30% 70%, rgba(124,191,141,.10) 0, transparent 50%)",
          }}
        />
        <div className="relative flex items-center gap-3">
          <GVMark size={40} tone="cream" />
          <div>
            <div className="t-h2 leading-none text-cream-100">Gita Valley</div>
            <div className="t-label mt-1 text-cream-300/90">
              Cultivating Soil and Soul
            </div>
          </div>
        </div>
        <div className="relative max-w-md">
          <div className="t-display leading-[1.15] text-cream-50">
            The pasture keeps its own time.
            <br />
            The posts can too.
          </div>
          <p className="t-body mt-4 max-w-sm text-cream-200/90">
            Eighty-five cows, four hundred and thirty acres, one story — told a
            little every day.
          </p>
        </div>
        <div className="t-micro relative flex items-center justify-between text-cream-300/70">
          <span>Port Royal, Pennsylvania</span>
          <span>North America's only slaughter-free certified dairy</span>
        </div>
      </div>

      {/* Form side */}
      <div className="surface-page flex items-center justify-center px-6 md:px-14">
        <div className="w-full max-w-[360px]">
          <h1 className="t-h1 ink">Welcome back to the pasture</h1>
          <p className="t-caption ink-muted mt-1.5">
            Sign in to tend today's posts.
          </p>
          <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="farm-pw"
                className="t-label ink-muted mb-1.5 block"
              >
                Farm password
              </label>
              <Input
                id="farm-pw"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                autoComplete="current-password"
                autoFocus
                aria-invalid={wrongPassword || undefined}
                disabled={isSubmitting || isLocked}
                className={`fr h-11 bg-card ${
                  wrongPassword
                    ? "border-red-300 focus:border-red-400 focus:ring-red-500/20"
                    : ""
                }`}
              />
              {wrongPassword && (
                <div role="alert" className="t-caption mt-1.5 text-red-700">
                  {attemptsRemaining != null
                    ? `That's not it — ${attemptsRemaining} tries remaining before the gate rests.`
                    : "That's not it — try again."}
                </div>
              )}
              {genericError && (
                <div role="alert" className="t-caption mt-1.5 text-red-700">
                  {genericError}
                </div>
              )}
            </div>

            {isLocked && <LockoutCard remainingSeconds={lockRemaining} />}

            <Button
              type="submit"
              size="lg"
              className="fr w-full justify-center"
              disabled={isSubmitting || isLocked || !password.trim()}
            >
              Open the gate
            </Button>
          </form>
          <div
            className="mt-6 space-y-1.5 pt-5"
            style={{
              borderTop:
                "1px solid color-mix(in oklab, var(--ink) 10%, transparent)",
            }}
          >
            <p className="t-caption ink-muted">
              One shared password for the whole team today — named accounts
              arrive with Phase 4.
            </p>
            <p className="t-micro ink-muted opacity-80">
              Sessions rest after an hour of quiet. Unsaved drafts stay safe on
              this device.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
