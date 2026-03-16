import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  PenSquare,
  FileCheck,
  CalendarDays,
  MoreHorizontal,
} from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { Lightbulb, Activity, ExternalLink } from "lucide-react";

const mainItems = [
  { to: "/", label: "Home", icon: LayoutDashboard },
  { to: "/create", label: "Create", icon: PenSquare },
  { to: "/drafts", label: "Drafts", icon: FileCheck },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
];

const moreItems = [
  { to: "/suggestions", label: "Suggestions", icon: Lightbulb },
  { to: "/health", label: "Health", icon: Activity },
];

export function BottomNav() {
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

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
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-background pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      <div className="flex items-center justify-around">
        {mainItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              [
                "flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-0.5 px-2 py-1.5 text-[10px] transition-colors",
                isActive
                  ? "text-sage-600 font-medium"
                  : "text-muted-foreground",
              ].join(" ")
            }
          >
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}

        {/* More dropdown */}
        <div ref={moreRef} className="relative">
          <button
            onClick={() => setMoreOpen(!moreOpen)}
            className="flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-0.5 px-2 py-1.5 text-[10px] text-muted-foreground transition-colors"
          >
            <MoreHorizontal className="h-5 w-5" />
            More
          </button>

          {moreOpen && (
            <div className="absolute bottom-full right-0 mb-2 w-40 rounded-lg border border-border bg-background shadow-lg">
              <a
                href="https://postiz.sethpc.xyz"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setMoreOpen(false)}
                className="flex items-center gap-2 px-3 py-2.5 text-sm text-foreground transition-colors hover:bg-muted"
              >
                <ExternalLink className="h-4 w-4" />
                Postiz Admin
              </a>
              {moreItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMoreOpen(false)}
                  className={({ isActive }) =>
                    [
                      "flex items-center gap-2 px-3 py-2.5 text-sm transition-colors",
                      isActive
                        ? "text-sage-600 font-medium"
                        : "text-foreground hover:bg-muted",
                    ].join(" ")
                  }
                >
                  <Icon className="h-4 w-4" />
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
