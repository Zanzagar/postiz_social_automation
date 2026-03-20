import { NavLink } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  LayoutDashboard,
  PenSquare,
  FileCheck,
  CalendarDays,
  Lightbulb,
  FileText,
  Settings,
  Activity,
  BookOpen,
  LogOut,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/create", label: "Create", icon: PenSquare },
  { to: "/drafts", label: "Drafts", icon: FileCheck },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/suggestions", label: "Suggestions", icon: Lightbulb },
  { to: "/templates", label: "Templates", icon: FileText },
  { to: "/knowledge", label: "Knowledge", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/health", label: "Health", icon: Activity },
];

export function Sidebar() {
  const { logout } = useAuth();

  return (
    <aside className="hidden md:flex md:w-60 md:flex-col md:border-r md:border-sidebar-border md:bg-sidebar">
      <div className="flex h-full flex-col">
        {/* Branding */}
        <div className="border-b border-sidebar-border px-4 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sage-500 text-sm font-bold text-white">
              GV
            </div>
            <div>
              <h2 className="text-base font-semibold text-sidebar-foreground">
                Gita Valley
              </h2>
              <p className="text-xs text-muted-foreground">Content Hub</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav data-testid="sidebar-nav" className="flex-1 space-y-1 px-3 py-4">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              data-active="false"
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50",
                ].join(" ")
              }
              // Set data-active for test querying
              ref={(el) => {
                if (el) {
                  const isActive = el.classList.contains("bg-sidebar-accent");
                  el.setAttribute("data-active", String(isActive));
                }
              }}
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Postiz Admin */}
        <div className="px-3">
          <a
            href="https://postiz.sethpc.xyz"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent/50"
          >
            <ExternalLink className="h-4 w-4" />
            Postiz Admin
          </a>
        </div>

        {/* Logout */}
        <div className="border-t border-sidebar-border p-3">
          <Button
            variant="ghost"
            data-testid="sidebar-logout"
            onClick={logout}
            className="w-full justify-start gap-3 text-muted-foreground hover:text-destructive"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </div>
    </aside>
  );
}
