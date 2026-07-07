import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Calendar, LayoutTemplate, Search, Sparkles, type LucideIcon } from "lucide-react";
import { NAV_ITEMS } from "./nav-items";

interface Command {
  label: string;
  to: string;
  icon: LucideIcon;
  hint?: string;
}

interface CommandGroup {
  group: string;
  items: Command[];
}

const COMMAND_GROUPS: CommandGroup[] = [
  {
    group: "Create",
    items: [
      { label: "New post from an idea…", to: "/create", icon: Sparkles, hint: "C" },
      { label: "Use a template", to: "/templates", icon: LayoutTemplate, hint: "T" },
      { label: "Schedule a batch", to: "/templates", icon: Calendar, hint: "B" },
    ],
  },
  {
    group: "Go to",
    items: NAV_ITEMS.map((n) => ({
      label: n.label,
      to: n.to,
      icon: n.icon,
      hint: `G ${n.label.charAt(0).toUpperCase()}`,
    })),
  },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return COMMAND_GROUPS;
    return COMMAND_GROUPS.map((g) => ({
      ...g,
      items: g.items.filter((c) => c.label.toLowerCase().includes(q)),
    })).filter((g) => g.items.length > 0);
  }, [query]);

  const run = (command: Command) => {
    navigate(command.to);
    setQuery("");
    onClose();
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setQuery("");
      onClose();
    }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const first = filtered[0]?.items[0];
      if (first) run(first);
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={handleOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-sage-900/30 backdrop-blur-[2px]" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="bg-card border-hair anim-in fixed top-24 left-1/2 z-40 w-[560px] max-w-[90%] -translate-x-1/2 overflow-hidden rounded-2xl shadow-2xl outline-none"
        >
          <DialogPrimitive.Title className="sr-only">
            Command palette
          </DialogPrimitive.Title>
          <div className="border-hair-b flex h-12 items-center gap-2 px-4">
            <Search
              size={16}
              strokeWidth={1.75}
              aria-hidden="true"
              className="ink-muted"
            />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Type a command or search the farm…"
              aria-label="Type a command or search the farm"
              className="t-ui ink flex-1 bg-transparent outline-none"
            />
            <span className="bg-warm t-micro ink-muted rounded px-1.5 py-0.5 font-mono">
              Esc
            </span>
          </div>
          <div className="max-h-[400px] overflow-y-auto py-2">
            {filtered.length === 0 && (
              <div className="t-body-sm ink-muted px-4 py-3">
                No commands match
              </div>
            )}
            {filtered.map((g) => (
              <div key={g.group} className="mb-1">
                <div className="t-label ink-muted px-4 py-1.5">{g.group}</div>
                {g.items.map((it) => {
                  const Icon = it.icon;
                  return (
                    <button
                      key={`${g.group}-${it.label}`}
                      type="button"
                      onClick={() => run(it)}
                      className="fr t-body flex w-full items-center gap-3 px-4 py-2 hover:bg-sage-500/10"
                    >
                      <Icon
                        size={15}
                        strokeWidth={1.75}
                        aria-hidden="true"
                        className="text-sage-600"
                      />
                      <span className="ink flex-1 text-left">{it.label}</span>
                      {it.hint && (
                        <span className="t-caption ink-muted font-mono">
                          {it.hint}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
