import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { BottomNav } from "./BottomNav";
import { CommandPalette } from "./CommandPalette";

export function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="surface-page flex min-h-svh">
      <Sidebar onOpenPalette={() => setPaletteOpen(true)} />
      <main
        data-testid="page-content"
        className="surface-page flex-1 overflow-auto pb-16 md:pb-0"
      >
        <Outlet />
      </main>
      <BottomNav />
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </div>
  );
}
