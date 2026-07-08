import { NavLink } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { ExternalLink, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS, useDraftsBadgeCount } from "./nav-items";

const mainItems = NAV_ITEMS.slice(0, 4);
const moreItems = NAV_ITEMS.slice(4);

export function BottomNav() {
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const draftsCount = useDraftsBadgeCount();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
    }
    if (moreOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [moreOpen]);

  return (
    <nav
      data-testid="bottom-nav"
      className="bg-warm fixed right-0 bottom-0 left-0 z-50 pb-[env(safe-area-inset-bottom)] md:hidden"
      style={{
        borderTop: "1px solid color-mix(in oklab, var(--ink) 12%, transparent)",
      }}
    >
      <div className="flex items-center justify-around">
        {mainItems.map(({ to, label, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "fr t-micro relative flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-0.5 px-2 py-1.5 transition-colors",
                isActive ? "font-medium text-sage-600" : "ink-muted",
              )
            }
          >
            <span className="relative">
              <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
              {badge === "drafts" && draftsCount > 0 && (
                <span className="t-micro absolute -top-1.5 -right-2.5 rounded-full bg-cream-300 px-1 py-px font-semibold text-cream-ink">
                  {draftsCount}
                </span>
              )}
            </span>
            {label}
          </NavLink>
        ))}

        {/* More dropdown */}
        <div ref={moreRef} className="relative">
          <button
            type="button"
            onClick={() => setMoreOpen(!moreOpen)}
            className="fr t-micro ink-muted flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-0.5 px-2 py-1.5 transition-colors"
          >
            <MoreHorizontal size={20} strokeWidth={1.75} aria-hidden="true" />
            More
          </button>

          {moreOpen && (
            <div className="bg-card border-hair absolute right-0 bottom-full mb-2 w-40 rounded-lg shadow-lg">
              <a
                href="https://postiz.sethpc.xyz"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setMoreOpen(false)}
                className="fr t-ui ink flex items-center gap-2 px-3 py-2.5 transition-colors hover:bg-sage-500/10"
              >
                <ExternalLink size={16} strokeWidth={1.75} aria-hidden="true" />
                Postiz Admin
              </a>
              {moreItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMoreOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "fr t-ui flex items-center gap-2 px-3 py-2.5 transition-colors",
                      isActive
                        ? "font-medium text-sage-600"
                        : "ink hover:bg-sage-500/10",
                    )
                  }
                >
                  <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
