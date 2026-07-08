/**
 * Single source of truth for app navigation.
 * Consumed by Sidebar (desktop rail), BottomNav (mobile), and CommandPalette.
 */
import {
  Activity,
  BookOpen,
  Calendar,
  ClipboardCheck,
  Image,
  LayoutTemplate,
  Lightbulb,
  Settings,
  Sparkles,
  Sunrise,
  type LucideIcon,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Which live badge (if any) this item displays. */
  badge?: "drafts";
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: "/", label: "Today", icon: Sunrise },
  { to: "/create", label: "Compose", icon: Sparkles },
  { to: "/drafts", label: "Drafts", icon: ClipboardCheck, badge: "drafts" },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/suggestions", label: "Suggestions", icon: Lightbulb },
  { to: "/templates", label: "Templates", icon: LayoutTemplate },
  { to: "/media", label: "Media", icon: Image },
  { to: "/knowledge", label: "Knowledge", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/health", label: "Health", icon: Activity },
];

/**
 * Count of drafts awaiting review — rendered as a cream badge on the
 * Drafts nav item. Deduped across Sidebar and BottomNav by query key.
 */
export function useDraftsBadgeCount(): number {
  const { data } = useQuery({
    queryKey: ["drafts", "badge-count"],
    queryFn: () => api.getDrafts(),
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });
  if (!data) return 0;
  return data.filter((d) => d.status === "pending_approval").length;
}
