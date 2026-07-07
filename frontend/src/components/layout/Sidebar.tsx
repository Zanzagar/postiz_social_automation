import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, LogOut, Search } from "lucide-react";
import { GVMark } from "@/components/pasture";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { NAV_ITEMS, useDraftsBadgeCount } from "./nav-items";

interface SidebarProps {
  onOpenPalette: () => void;
}

export function Sidebar({ onOpenPalette }: SidebarProps) {
  const { logout } = useAuth();
  const draftsCount = useDraftsBadgeCount();

  return (
    <aside
      className="relative hidden w-[264px] shrink-0 flex-col md:flex"
      style={{
        borderRight:
          "1px solid color-mix(in oklab, var(--ink) 12%, transparent)",
        background:
          "linear-gradient(to bottom, var(--surface-warm), var(--surface-warm-2))",
      }}
    >
      <div className="paper pointer-events-none absolute inset-0" />

      {/* Branding */}
      <div className="border-hair-b relative px-5 pt-5 pb-4">
        <div className="flex items-center gap-2.5">
          <GVMark size={36} />
          <div>
            <div className="t-title-sm ink font-serif leading-tight font-semibold">
              Gita Valley
            </div>
            <div className="t-caption ink-muted italic">
              Cultivating Soil and Soul
            </div>
          </div>
        </div>
      </div>

      {/* Command palette trigger */}
      <div className="border-hair-b relative px-3 py-3">
        <button
          type="button"
          onClick={onOpenPalette}
          className="fr bg-card border-hair t-body-sm ink-muted flex h-8 w-full items-center gap-2 rounded-lg px-2.5 hover:brightness-105"
        >
          <Search size={13} strokeWidth={1.75} aria-hidden="true" />
          <span>Search or run command…</span>
          <span className="bg-card border-hair t-micro ink-muted ml-auto rounded px-1.5 py-0.5 font-mono">
            ⌘K
          </span>
        </button>
      </div>

      {/* Navigation */}
      <nav data-testid="sidebar-nav" className="relative flex-1 space-y-0.5 p-3">
        <div className="t-label ink-muted px-2.5 pt-1 pb-1.5">Workspace</div>
        {NAV_ITEMS.map(({ to, label, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "fr t-ui flex h-8 w-full items-center gap-2.5 rounded-lg px-2.5 transition",
                isActive
                  ? "bg-sage-500 font-medium text-white shadow-sm"
                  : "ink hover:bg-sage-500/10",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={15} strokeWidth={1.75} aria-hidden="true" />
                <span className="flex-1 text-left">{label}</span>
                {badge === "drafts" && draftsCount > 0 && (
                  <span
                    className={cn(
                      "t-micro rounded-full px-1.5 py-0.5 font-semibold",
                      isActive
                        ? "bg-white/25 text-white"
                        : "bg-cream-300 text-cream-ink",
                    )}
                  >
                    {draftsCount}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Health footer */}
      <div
        className="relative p-3"
        style={{
          borderTop:
            "1px solid color-mix(in oklab, var(--ink) 12%, transparent)",
        }}
      >
        <HealthFooterCard />
        <a
          href="https://postiz.sethpc.xyz"
          target="_blank"
          rel="noopener noreferrer"
          className="fr t-body-sm ink-muted mt-2 flex h-8 w-full items-center gap-2 rounded-lg px-2.5 hover:bg-sage-500/10"
        >
          <ExternalLink size={13} strokeWidth={1.75} aria-hidden="true" />
          Postiz Admin
        </a>
        <button
          type="button"
          data-testid="sidebar-logout"
          onClick={logout}
          className="fr t-body-sm ink-muted flex h-8 w-full items-center gap-2 rounded-lg px-2.5 hover:bg-sage-500/10"
        >
          <LogOut size={13} strokeWidth={1.75} aria-hidden="true" />
          Sign out
        </button>
      </div>
    </aside>
  );
}

const HEALTHY_STATUSES = new Set(["ok", "healthy", "up", "connected"]);

function HealthFooterCard() {
  const { data } = useQuery({
    queryKey: ["health", "sidebar"],
    queryFn: () => api.getHealth(),
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  });

  const services = data?.services ?? [];
  const healthy =
    services.length === 0 ||
    services.every((s) => HEALTHY_STATUSES.has(s.status.toLowerCase()));

  return (
    <div className="bg-card border-hair rounded-xl p-3">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "pulse-dot h-2 w-2 rounded-full",
            healthy ? "bg-sage-500" : "bg-terra-500",
          )}
        />
        <span className="t-body-sm ink font-medium">
          {healthy ? "All systems healthy" : "Needs attention"}
        </span>
      </div>
      <div className="t-caption ink-muted mt-1">Postiz · Claude · Drive</div>
    </div>
  );
}
